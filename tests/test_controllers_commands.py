from copy import deepcopy
from unittest.mock import MagicMock, patch

import deployfish.core.adapters  # noqa: F401
from deployfish.controllers.commands import ECSServiceCommands, get_task
from deployfish.controllers.service import ECSServiceSecrets
from deployfish.core.models.ecs import Service, ServiceHelperTask
from deployfish.core.models.secrets import Secret

from tests.controller_helpers import bind_controller, bind_service_loader
from tests.fixtures import SERVICE_YML_WITH_HELPER_TASKS


class TestECSServiceCommandsController:
    def test_list_prints_helper_tasks(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSServiceCommands(), cement_app)
        cement_app.pargs.pk = "foobar-cluster:foobar-test"
        service = Service.new(deepcopy(SERVICE_YML_WITH_HELPER_TASKS), "deployfish")
        loader = bind_service_loader(controller)
        with patch.object(loader, "get_object_from_aws", return_value=service):
            controller.list()
        cement_app.print.assert_called_once()

    def test_get_task_finds_command(self) -> None:
        service = Service.new(deepcopy(SERVICE_YML_WITH_HELPER_TASKS), "deployfish")
        task = get_task(service, "migrate")
        assert isinstance(task, ServiceHelperTask)
        assert task.command == "migrate"

    def test_get_task_raises_for_unknown_command(self) -> None:
        import pytest

        service = Service.new(deepcopy(SERVICE_YML_WITH_HELPER_TASKS), "deployfish")
        with pytest.raises(ServiceHelperTask.DoesNotExist):
            get_task(service, "nonexistent")


class TestECSServiceSecretsController:
    def test_write_syncs_secrets_when_forced(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSServiceSecrets(), cement_app)
        cement_app.pargs.pk = "foobar-test"
        cement_app.pargs.force = True
        service = Service.new(deepcopy(SERVICE_YML_WITH_HELPER_TASKS), "deployfish")
        loader = bind_service_loader(controller)
        with patch.object(loader, "get_object_from_deployfish", return_value=service):
            with patch.object(Secret.objects, "list", return_value=[]):
                with patch.object(service, "write_secrets") as write_mock:
                    with patch.object(service, "reload_secrets"):
                        controller.write()
        write_mock.assert_called_once()

    def test_diff_reports_up_to_date(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSServiceSecrets(), cement_app)
        cement_app.pargs.pk = "foobar-test"
        service = Service.new(deepcopy(SERVICE_YML_WITH_HELPER_TASKS), "deployfish")
        loader = bind_service_loader(controller)
        with patch.object(loader, "get_object_from_deployfish", return_value=service):
            with patch.object(service, "diff_secrets", return_value={}):
                with patch.object(Secret.objects, "list", return_value=[]):
                    with patch(
                        "deployfish.controllers.secrets.click.style",
                        side_effect=lambda x, **_: x,
                    ):
                        controller.diff()
        cement_app.print.assert_called()

    def test_export_writes_env_file_content(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSServiceSecrets(), cement_app)
        cement_app.pargs.pk = "foobar-test"
        service = Service.new(deepcopy(SERVICE_YML_WITH_HELPER_TASKS), "deployfish")
        loader = bind_service_loader(controller)
        with patch.object(loader, "get_object_from_deployfish", return_value=service):
            with patch.object(
                controller,
                "export_environment_secrets",
                return_value="DJANGO_SECRET_KEY=the_secret_key",
            ):
                controller.export()
        cement_app.print.assert_called_once_with("DJANGO_SECRET_KEY=the_secret_key")
