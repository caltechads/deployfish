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
