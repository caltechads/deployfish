from copy import deepcopy
from unittest.mock import patch

import deployfish.core.adapters  # noqa: F401
from deployfish.core.models.ecs import Service, ServiceHelperTask

from tests.fixtures import SERVICE_YML_WITH_HELPER_TASKS


class TestServiceHelperTaskNew:
    def test_new_returns_one_instance_per_command(self) -> None:
        data = deepcopy(SERVICE_YML_WITH_HELPER_TASKS)
        service = Service.new(data, "deployfish")
        tasks = ServiceHelperTask.new(data, "deployfish", service=service)
        assert len(tasks) == 2
        commands = {task.command for task in tasks}
        assert commands == {"migrate", "update_index"}

    def test_command_property_matches_command_name(self) -> None:
        data = deepcopy(SERVICE_YML_WITH_HELPER_TASKS)
        service = Service.new(data, "deployfish")
        tasks = ServiceHelperTask.new(data, "deployfish", service=service)
        migrate = next(t for t in tasks if t.command == "migrate")
        assert migrate.data["name"] == "migrate"

    def test_service_new_attaches_helper_tasks(self) -> None:
        data = deepcopy(SERVICE_YML_WITH_HELPER_TASKS)
        service = Service.new(data, "deployfish")
        assert len(service.helper_tasks) == 2
        assert "deployfish:command:migrate" in service.task_definition.tags


class TestServiceHelperTaskSave:
    def test_save_registers_task_definition(self) -> None:
        data = deepcopy(SERVICE_YML_WITH_HELPER_TASKS)
        service = Service.new(data, "deployfish")
        task = service.helper_tasks[0]
        with patch.object(
            ServiceHelperTask.objects,
            "save",
            return_value="arn:aws:ecs:task:123",
        ) as save_mock:
            arn = task.save()
        save_mock.assert_called_once_with(task)
        assert arn == "arn:aws:ecs:task:123"
