from unittest.mock import MagicMock, patch

import pytest
from deployfish.core.models.ecs import ContainerDefinition, TaskDefinition

TASK_DEF_DATA = {
    "family": "foobar-test",
    "revision": 1,
    "taskDefinitionArn": "arn:aws:ecs:us-west-2:123:task-definition/foobar-test:1",
    "containerDefinitions": [
        {
            "name": "foobar",
            "image": "app:1",
            "cpu": 512,
            "memory": 512,
        }
    ],
}


class TestTaskDefinitionManager:
    def test_get_task_definition(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        client.describe_task_definition.return_value = {
            "taskDefinition": TASK_DEF_DATA.copy(),
            "tags": [],
        }
        td = TaskDefinition.objects.get("foobar-test:1")
        assert td.family == "foobar-test"
        assert len(td.containers) == 1

    def test_get_raises_on_client_error(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        client.exceptions.ClientException = type("ClientException", (Exception,), {})
        client.describe_task_definition.side_effect = client.exceptions.ClientException("missing")
        with pytest.raises(TaskDefinition.DoesNotExist):
            TaskDefinition.objects.get("missing:1")

    def test_save_registers_task_definition(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        client.register_task_definition.return_value = {
            "taskDefinition": {"taskDefinitionArn": "arn:new:1"},
        }
        td = TaskDefinition(TASK_DEF_DATA, containers=[ContainerDefinition(TASK_DEF_DATA["containerDefinitions"][0])])
        with patch.object(td, "render", return_value={"family": "foobar-test"}):
            arn = TaskDefinition.objects.save(td)
        assert arn == "arn:new:1"

    def test_delete_raises_read_only(self) -> None:
        td = TaskDefinition(TASK_DEF_DATA, containers=[])
        with pytest.raises(TaskDefinition.ReadOnly):
            TaskDefinition.objects.delete(td)

    def test_list_task_definitions(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        paginator = MagicMock()
        client.get_paginator.return_value = paginator
        paginator.paginate.return_value = [
            {"taskDefinitionArns": ["arn:aws:ecs:us-west-2:123:task-definition/foobar-test:1"]},
        ]
        with patch.object(TaskDefinition.objects, "get") as get_mock:
            get_mock.return_value = TaskDefinition(TASK_DEF_DATA, containers=[])
            results = TaskDefinition.objects.list("foobar-test")
        assert len(results) == 1
