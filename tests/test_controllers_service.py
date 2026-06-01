from copy import deepcopy
from unittest.mock import MagicMock, patch

import deployfish.core.adapters  # noqa: F401
from deployfish.controllers.service import ECSService
from deployfish.core.models.ecs import Service

from tests.controller_helpers import bind_controller, bind_service_loader
from tests.fixtures import SERVICE_YML, SERVICE_YML_WITH_SCALING


class TestECSServiceController:
    def test_create_saves_new_service(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSService(), cement_app)
        cement_app.pargs.name = "foobar-test"
        mock_service = MagicMock()
        mock_service.exists = False
        mock_service.pk = "foobar-cluster:foobar-test"
        loader = bind_service_loader(controller)
        with patch.object(
            loader, "get_object_from_deployfish", return_value=mock_service
        ):
            with patch.object(controller, "create_waiter"):
                with patch("deployfish.controllers.crud.click.secho"):
                    controller.create()
        mock_service.save.assert_called_once()

    def test_create_skips_existing_service(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSService(), cement_app)
        cement_app.pargs.name = "foobar-test"
        mock_service = MagicMock()
        mock_service.exists = True
        loader = bind_service_loader(controller)
        with patch.object(
            loader, "get_object_from_deployfish", return_value=mock_service
        ):
            controller.create()
        mock_service.save.assert_not_called()

    def test_plan_renders_diff_with_appscaling(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSService(), cement_app)
        cement_app.pargs.pk = "foobar-cluster:foobar-test"
        df_service = Service.new(deepcopy(SERVICE_YML_WITH_SCALING), "deployfish")
        aws_service = Service.new(deepcopy(SERVICE_YML), "deployfish")
        aws_service.appscaling = None
        loader = bind_service_loader(controller)
        with patch.object(
            loader, "get_object_from_deployfish", return_value=df_service
        ):
            with patch.object(loader, "get_object_from_aws", return_value=aws_service):
                controller.plan()
        cement_app.render.assert_called_once()
        render_context = cement_app.render.call_args[0][0]
        assert "changes" in render_context
        assert (
            cement_app.render.call_args.kwargs["template"] == controller.plan_template
        )

    def test_scale_calls_service_scale(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSService(), cement_app)
        cement_app.pargs.pk = "foobar-cluster:foobar-test"
        cement_app.pargs.count = 3
        mock_service = MagicMock()
        loader = bind_service_loader(controller)
        with patch.object(loader, "get_object_from_aws", return_value=mock_service):
            with patch.object(controller, "scale_services_waiter"):
                with patch("deployfish.controllers.service.click.secho"):
                    controller.scale()
        mock_service.scale.assert_called_once_with(3)

    def test_restart_calls_service_restart(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSService(), cement_app)
        cement_app.pargs.pk = "foobar-cluster:foobar-test"
        cement_app.pargs.hard = False
        mock_service = MagicMock()
        loader = bind_service_loader(controller)
        with patch.object(loader, "get_object_from_aws", return_value=mock_service):
            with patch("deployfish.controllers.service.click.secho"):
                controller.restart()
        mock_service.restart.assert_called_once()

    def test_running_tasks_renders_table(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSService(), cement_app)
        cement_app.pargs.pk = "foobar-cluster:foobar-test"
        mock_service = MagicMock()
        mock_service.running_tasks = []
        loader = bind_service_loader(controller)
        with patch.object(loader, "get_object_from_aws", return_value=mock_service):
            controller.running_tasks()
        cement_app.print.assert_called_once()
