from unittest.mock import MagicMock, patch

import pytest
from deployfish.core.models.ecs import InvokedTask, StandaloneTask, TaskDefinition


class TestInvokedTaskManagerExtended:
    def test_get_invoked_task(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        task_data = {
            "taskArn": "arn:aws:ecs:us-west-2:123:task/cluster/abc",
            "clusterArn": "arn:aws:ecs:us-west-2:123:cluster/foobar-cluster",
            "lastStatus": "RUNNING",
        }
        client.describe_tasks.return_value = {"tasks": [task_data], "failures": []}
        task = InvokedTask.objects.get(
            "foobar-cluster:arn:aws:ecs:us-west-2:123:task/cluster/abc"
        )
        assert task.data["lastStatus"] == "RUNNING"

    def test_get_raises_when_task_missing(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        client.describe_tasks.return_value = {"tasks": [], "failures": []}
        with pytest.raises(InvokedTask.DoesNotExist):
            InvokedTask.objects.get("foobar-cluster:arn:missing")


class TestStandaloneTaskManagerScheduled:
    def test_list_scheduled_tasks(self, _mock_boto3_session: MagicMock) -> None:
        from deployfish.core.models.events import EventScheduleRule

        rule = MagicMock()
        rule.target = MagicMock()
        rule.target.data = {"EcsParameters": {"TaskDefinitionArn": "arn:task-def:1"}}
        td = TaskDefinition(
            {
                "family": "scheduled-task",
                "revision": 1,
                "taskDefinitionArn": "arn:task-def:1",
                "tags": [
                    {"key": "deployfish:type", "value": "standalone"},
                    {"key": "deployfish:cluster", "value": "foobar-cluster"},
                ],
            },
            containers=[],
        )
        with patch.object(EventScheduleRule.objects, "list", return_value=[rule]):
            with patch.object(TaskDefinition.objects, "get", return_value=td):
                tasks = StandaloneTask.objects.list_scheduled(task_type="standalone")
        assert len(tasks) == 1
