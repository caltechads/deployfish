from copy import deepcopy
from unittest.mock import MagicMock, patch

import deployfish.core.adapters  # noqa: F401
from deployfish.core.models.ecs import Service, TaskDefinition

from tests.fixtures import SERVICE_YML, SERVICE_YML_WITH_HELPER_TASKS


class TestTaskDefinitionModel:
    def test_family_and_revision(self) -> None:
        td = TaskDefinition(
            {
                "family": "foobar-test",
                "revision": 3,
                "taskDefinitionArn": "arn:aws:ecs:us-west-2:123:task-definition/foobar-test:3",
            }
        )
        assert td.family == "foobar-test"
        assert td.revision == 3
        assert td.pk == "foobar-test:3"


class TestServiceProperties:
    def test_service_name_and_pk(self) -> None:
        service = Service.new(deepcopy(SERVICE_YML), "deployfish")
        service.data["cluster"] = "foobar-cluster"
        service.data["serviceName"] = "foobar-test"
        assert service.name == "foobar-test"
        assert service.pk == "foobar-cluster:foobar-test"

    def test_service_launch_type_ec2_default(self) -> None:
        service = Service.new(deepcopy(SERVICE_YML), "deployfish")
        assert service.launch_type == "EC2"

    def test_helper_tasks_from_yaml(self) -> None:
        service = Service.new(deepcopy(SERVICE_YML_WITH_HELPER_TASKS), "deployfish")
        assert len(service.helper_tasks) >= 1

    def test_task_definition_logging(self) -> None:
        service = Service.new(deepcopy(SERVICE_YML), "deployfish")
        logging = service.task_definition.logging
        assert logging is not None
        assert logging["logDriver"] == "fluentd"

    def test_running_tasks_delegates_to_manager(self) -> None:
        from deployfish.core.models.ecs import InvokedTask

        service = Service.new(deepcopy(SERVICE_YML), "deployfish")
        service.data["cluster"] = "foobar-cluster"
        service.data["serviceName"] = "foobar-test"
        invoked = MagicMock()
        with patch.object(InvokedTask.objects, "list", return_value=[invoked]) as list_mock:
            tasks = service.running_tasks
        list_mock.assert_called_once_with("foobar-cluster", service="foobar-test")
        assert tasks == [invoked]
