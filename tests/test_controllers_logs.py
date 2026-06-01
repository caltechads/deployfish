from copy import deepcopy
from unittest.mock import MagicMock, patch

import deployfish.core.adapters  # noqa: F401
import pytest
from deployfish.controllers.logs import list_log_streams, tail_task_logs
from deployfish.core.models.ecs import StandaloneTask

from tests.fixtures import STANDALONE_TASK_YML


def _awslogs_task() -> StandaloneTask:
    task = StandaloneTask.new(deepcopy(STANDALONE_TASK_YML), "deployfish")
    task.task_definition.containers[0].data["logConfiguration"] = {
        "logDriver": "awslogs",
        "options": {
            "awslogs-group": "my_log_group",
            "awslogs-stream-prefix": "my_log_stream",
            "awslogs-region": "us-west-2",
        },
    }
    return task


class TestTailTaskLogs:
    def test_tail_streams_log_events(self) -> None:
        app = MagicMock()
        task = _awslogs_task()
        event = {
            "timestamp": MagicMock(
                strftime=MagicMock(return_value="2026-01-01 00:00:00.000000")
            ),
            "message": "hello world\n",
        }
        tailer = iter([[event], []])
        group = MagicMock()
        group.get_event_tailer.return_value = tailer
        with patch(
            "deployfish.controllers.logs.CloudWatchLogGroup.objects.get",
            return_value=group,
        ):
            with patch(
                "deployfish.controllers.logs.click.style", side_effect=lambda v, **_: v
            ):
                tail_task_logs(app, task, sleep=0, mark=True)
        app.print.assert_called()
        group.get_event_tailer.assert_called_once()

    def test_tail_rejects_non_awslogs_driver(self) -> None:
        app = MagicMock()
        task = StandaloneTask.new(deepcopy(STANDALONE_TASK_YML), "deployfish")
        task.task_definition.containers[0].data["logConfiguration"] = {
            "logDriver": "fluentd",
            "options": {},
        }
        with pytest.raises(StandaloneTask.OperationFailed, match="awslogs"):
            tail_task_logs(app, task)


class TestListLogStreams:
    def test_list_log_streams_renders_table(self) -> None:
        app = MagicMock()
        task = _awslogs_task()
        stream = MagicMock()
        stream.logStreamName = "stream-1"
        stream.creationTime = 1000
        stream.lastEventTimestamp = 2000
        group = MagicMock()
        group.log_streams.return_value = [stream]
        with patch(
            "deployfish.controllers.logs.CloudWatchLogGroup.objects.get",
            return_value=group,
        ):
            list_log_streams(app, task, limit=5)
        app.print.assert_called_once()
        group.log_streams.assert_called_once()
