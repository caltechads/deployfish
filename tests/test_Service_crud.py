from copy import deepcopy
from unittest.mock import MagicMock, patch

import deployfish.core.adapters  # noqa: F401
from deployfish.core.models.ecs import Service, ServiceHelperTask

from tests.fixtures import (
    SERVICE_YML,
    SERVICE_YML_WITH_HELPER_TASKS,
    SERVICE_YML_WITH_SCALING,
)


class TestServiceRenderForDiff:
    def test_render_for_diff_includes_appscaling(self) -> None:
        service = Service.new(deepcopy(SERVICE_YML_WITH_SCALING), "deployfish")
        diff_data = service.render_for_diff()
        assert "appscaling" in diff_data
        assert diff_data["appscaling"]["MinCapacity"] == 2

    def test_render_for_diff_includes_task_definition(self) -> None:
        service = Service.new(deepcopy(SERVICE_YML), "deployfish")
        service.appscaling = None
        diff_data = service.render_for_diff()
        assert "taskDefinition" in diff_data
        assert diff_data["taskDefinition"]["family"] == "foobar-test"


class TestServiceUpdateAppscaling:
    def test_update_appscaling_saves_when_present(self) -> None:
        service = Service.new(deepcopy(SERVICE_YML_WITH_SCALING), "deployfish")
        with patch.object(service.appscaling, "save") as save_mock:
            service._Service__update_appscaling(None)
        save_mock.assert_called_once()

    def test_update_appscaling_deletes_when_removed(self) -> None:
        service = Service.new(deepcopy(SERVICE_YML), "deployfish")
        service.appscaling = None
        existing = Service.new(deepcopy(SERVICE_YML_WITH_SCALING), "deployfish")
        with patch.object(existing.appscaling, "delete") as delete_mock:
            service._Service__update_appscaling(existing)
        delete_mock.assert_called_once()


class TestServiceSaveHelperTasks:
    def test_save_helper_tasks_tags_task_definition(self) -> None:
        service = Service.new(deepcopy(SERVICE_YML_WITH_HELPER_TASKS), "deployfish")
        with patch.object(
            ServiceHelperTask.objects,
            "save",
            return_value="arn:aws:ecs:task:1",
        ):
            service._Service__save_helper_tasks()
        assert (
            service.task_definition.tags["deployfish:command:migrate"]
            == "arn:aws:ecs:task:1"
        )


class TestServiceScale:
    def test_scale_updates_desired_count(self) -> None:
        service = Service.new(deepcopy(SERVICE_YML), "deployfish")
        with patch.object(Service.objects, "scale") as scale_mock:
            service.scale(3)
        scale_mock.assert_called_once_with(service, 3)


class TestServiceDelete:
    def test_delete_removes_appscaling(self) -> None:
        service = Service.new(deepcopy(SERVICE_YML_WITH_SCALING), "deployfish")
        service.helper_tasks = []
        with patch.object(Service.objects, "exists", return_value=True):
            with patch.object(service, "reload_from_db"):
                service.data["desiredCount"] = 0
                with patch.object(service.appscaling, "delete") as appscaling_delete:
                    with patch.object(Service.objects, "scale"):
                        with patch.object(Service.objects, "get_waiter") as get_waiter:
                            get_waiter.return_value.wait = MagicMock()
                            Service.objects.delete(service)
        appscaling_delete.assert_called_once()
