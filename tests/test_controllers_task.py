from copy import deepcopy
from unittest.mock import MagicMock, patch

import deployfish.core.adapters  # noqa: F401
from deployfish.controllers.task import ECSStandaloneTask
from deployfish.core.loaders import ObjectLoader
from deployfish.core.models.ecs import StandaloneTask

from tests.controller_helpers import bind_controller, bind_loader_factory
from tests.fixtures import STANDALONE_TASK_YML


class TestECSStandaloneTaskController:
    def test_create_saves_new_task(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSStandaloneTask(), cement_app)
        cement_app.pargs.name = "foobar-test-mytask"
        mock_task = MagicMock()
        mock_task.exists = False
        loader = bind_loader_factory(controller, ObjectLoader(controller))
        with patch.object(loader, "get_object_from_deployfish", return_value=mock_task):
            with patch.object(controller, "create_waiter"):
                with patch("deployfish.controllers.crud.click.secho"):
                    controller.create()
        mock_task.save.assert_called_once()

    def test_update_saves_existing_task(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSStandaloneTask(), cement_app)
        cement_app.pargs.name = "foobar-test-mytask"
        mock_task = MagicMock()
        loader = bind_loader_factory(controller, ObjectLoader(controller))
        with patch.object(loader, "get_object_from_deployfish", return_value=mock_task):
            with patch.object(controller, "update_waiter"):
                with patch(
                    "deployfish.controllers.crud.click.style",
                    side_effect=lambda value, **_: value,
                ):
                    controller.update()
        mock_task.save.assert_called_once()
        cement_app.render.assert_called_once()

    def test_delete_reports_operation_failed(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSStandaloneTask(), cement_app)
        cement_app.pargs.name = "foobar-test-mytask"
        with patch(
            "deployfish.controllers.task.click.style",
            side_effect=lambda value, **_: value,
        ):
            controller.delete()
        cement_app.print.assert_called_once()
        assert "cannot be deleted" in cement_app.print.call_args[0][0]

    def test_run_invokes_task_run(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSStandaloneTask(), cement_app)
        cement_app.pargs.pk = "foobar-test-mytask:1"
        cement_app.pargs.wait = False
        invoked_task = MagicMock()
        invoked_task.arn = "arn:aws:ecs:us-west-2:123:task/cluster/abc"
        mock_task = MagicMock()
        mock_task.run.return_value = [invoked_task]
        mock_task.data = {"cluster": "foobar-cluster"}
        loader = bind_loader_factory(controller, ObjectLoader(controller))
        with patch.object(loader, "get_object_from_aws", return_value=mock_task):
            with patch(
                "deployfish.controllers.task.click.style",
                side_effect=lambda value, **_: value,
            ):
                controller.run()
        mock_task.run.assert_called_once()
        cement_app.print.assert_called_once()

    def test_enable_schedule(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSStandaloneTask(), cement_app)
        cement_app.pargs.pk = "foobar-test-mytask:1"
        mock_task = StandaloneTask.new(deepcopy(STANDALONE_TASK_YML), "deployfish")
        mock_task.schedule = MagicMock()
        mock_task.schedule.enabled = True
        mock_task.schedule.data = {"ScheduleExpression": "rate(5 minutes)"}
        loader = bind_loader_factory(controller, ObjectLoader(controller))
        with patch.object(loader, "get_object_from_aws", return_value=mock_task):
            with patch.object(mock_task, "enable_schedule") as enable_mock:
                with patch(
                    "deployfish.controllers.task.click.style",
                    side_effect=lambda value, **_: value,
                ):
                    controller.enable()
        enable_mock.assert_called_once()

    def test_disable_schedule(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSStandaloneTask(), cement_app)
        cement_app.pargs.pk = "foobar-test-mytask:1"
        mock_task = StandaloneTask.new(deepcopy(STANDALONE_TASK_YML), "deployfish")
        mock_task.schedule = MagicMock()
        mock_task.schedule.enabled = False
        loader = bind_loader_factory(controller, ObjectLoader(controller))
        with patch.object(loader, "get_object_from_aws", return_value=mock_task):
            with patch.object(mock_task, "disable_schedule") as disable_mock:
                with patch(
                    "deployfish.controllers.task.click.style",
                    side_effect=lambda value, **_: value,
                ):
                    controller.disable()
        disable_mock.assert_called_once()

    def test_plan_renders_task_diff(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSStandaloneTask(), cement_app)
        cement_app.pargs.pk = "foobar-test-mytask:1"
        df_task = StandaloneTask.new(deepcopy(STANDALONE_TASK_YML), "deployfish")
        aws_task = StandaloneTask.new(deepcopy(STANDALONE_TASK_YML), "deployfish")
        loader = bind_loader_factory(controller, ObjectLoader(controller))
        with patch.object(loader, "get_object_from_deployfish", return_value=df_task):
            with patch.object(loader, "get_object_from_aws", return_value=aws_task):
                controller.plan()
        cement_app.render.assert_called_once()
