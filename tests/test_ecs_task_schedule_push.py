"""Task schedule enable/disable coverage."""

from copy import deepcopy
from unittest.mock import MagicMock

import deployfish.core.adapters  # noqa: F401
from deployfish.core.models.ecs import StandaloneTask

from tests.fixtures import STANDALONE_TASK_YML


class TestTaskScheduleActions:
    def test_enable_and_disable_schedule_on_task(self) -> None:
        task = StandaloneTask.new(deepcopy(STANDALONE_TASK_YML), "deployfish")
        schedule = MagicMock()
        task.schedule = schedule
        task.enable_schedule()
        task.disable_schedule()
        schedule.enable.assert_called_once()
        schedule.disable.assert_called_once()

    def test_unschedule_deletes_rule(self) -> None:
        task = StandaloneTask.new(deepcopy(STANDALONE_TASK_YML), "deployfish")
        schedule = MagicMock()
        task.schedule = schedule
        task.unschedule()
        schedule.delete.assert_called_once()
