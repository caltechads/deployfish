from copy import deepcopy
from unittest.mock import MagicMock, PropertyMock, patch

import deployfish.core.adapters  # noqa: F401
import pytest
from deployfish.core.models.ecs import Service
from deployfish.core.ssh import DockerMixin

from tests.fixtures import SERVICE_YML, SERVICE_YML_WITH_SCALING


class TestServiceSave:
    def test_save_orchestrates_helper_tasks_task_def_service_discovery_appscaling(
        self,
    ) -> None:
        service = Service.new(deepcopy(SERVICE_YML_WITH_SCALING), "deployfish")
        existing = MagicMock()
        with patch.object(Service.objects, "get", return_value=existing):
            with patch.object(service, "_Service__save_helper_tasks") as save_helpers:
                with patch.object(
                    service.task_definition, "save", return_value="arn:aws:ecs:task:1"
                ) as save_task_def:
                    with patch.object(
                        service, "_Service__update_service_discovery"
                    ) as update_sd:
                        with patch.object(Service.objects, "save") as objects_save:
                            with patch.object(
                                service, "_Service__update_appscaling"
                            ) as update_appscaling:
                                service.save()
        save_helpers.assert_called_once()
        save_task_def.assert_called_once()
        update_sd.assert_called_once_with(existing)
        objects_save.assert_called_once_with(service)
        update_appscaling.assert_called_once_with(existing)
        assert service.data["taskDefinition"] == "arn:aws:ecs:task:1"

    def test_save_handles_no_existing_service(self) -> None:
        service = Service.new(deepcopy(SERVICE_YML), "deployfish")
        with patch.object(Service.objects, "get", side_effect=Service.DoesNotExist):
            with patch.object(service, "_Service__save_helper_tasks"):
                with patch.object(
                    service.task_definition, "save", return_value="arn:aws:ecs:task:2"
                ):
                    with patch.object(service, "_Service__update_service_discovery") as update_sd:
                        with patch.object(Service.objects, "save"):
                            with patch.object(service, "_Service__update_appscaling") as update_appscaling:
                                service.save()
        update_sd.assert_called_once_with(None)
        update_appscaling.assert_called_once_with(None)


class TestServiceRestart:
    def test_restart_soft_waits_after_each_task_delete(self) -> None:
        service = Service.new(deepcopy(SERVICE_YML), "deployfish")
        task_one = MagicMock()
        task_two = MagicMock()
        waiter = MagicMock()
        with patch.object(
            Service,
            "running_tasks",
            new_callable=PropertyMock,
            return_value=[task_one, task_two],
        ), patch.object(Service.objects, "get_waiter", return_value=waiter):
            service.restart(hard=False)
        task_one.delete.assert_called_once()
        task_two.delete.assert_called_once()
        assert waiter.wait.call_count == 2

    def test_restart_hard_waits_once_at_end(self) -> None:
        service = Service.new(deepcopy(SERVICE_YML), "deployfish")
        task_one = MagicMock()
        task_two = MagicMock()
        waiter = MagicMock()
        with patch.object(
            Service,
            "running_tasks",
            new_callable=PropertyMock,
            return_value=[task_one, task_two],
        ), patch.object(Service.objects, "get_waiter", return_value=waiter):
            service.restart(hard=True)
        task_one.delete.assert_called_once()
        task_two.delete.assert_called_once()
        waiter.wait.assert_called_once()

    def test_restart_raises_when_no_running_tasks(self) -> None:
        service = Service.new(deepcopy(SERVICE_YML), "deployfish")
        with patch.object(Service, "running_tasks", new_callable=PropertyMock, return_value=[]):
            with pytest.raises(DockerMixin.NoRunningTasks):
                service.restart()


class TestServiceDeployfishEnvironment:
    def test_deployfish_environment_prefers_deployfish_tag(self) -> None:
        service = Service.new(deepcopy(SERVICE_YML), "deployfish")
        service._tags = {"deployfish:Environment": "prod", "Environment": "test"}
        assert service.deployfish_environment == "prod"

    def test_deployfish_environment_falls_back_to_environment_tag(self) -> None:
        service = Service.new(deepcopy(SERVICE_YML), "deployfish")
        service._tags = {"Environment": "staging"}
        assert service.deployfish_environment == "staging"

    def test_deployfish_environment_defaults_to_test(self) -> None:
        service = Service.new(deepcopy(SERVICE_YML), "deployfish")
        service._tags = {}
        assert service.deployfish_environment == "test"
