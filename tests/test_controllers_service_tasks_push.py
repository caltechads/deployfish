"""ECSServiceStandaloneTasks controller coverage."""

from unittest.mock import MagicMock, patch

import deployfish.core.adapters  # noqa: F401
from deployfish.controllers.service import ECSServiceStandaloneTasks
from deployfish.core.models.ecs import StandaloneTask

from tests.controller_helpers import bind_controller, bind_service_loader


class TestECSServiceStandaloneTasksPush:
    def test_list_related_tasks_prints_matches(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSServiceStandaloneTasks(), cement_app)
        cement_app.pargs.pk = "foobar-cluster:foobar-test"
        service = MagicMock()
        service.pk = "foobar-cluster:foobar-test"
        service.name = "foobar-test"
        loader = bind_service_loader(controller)
        cement_app.deployfish_config.cooked = {
            "tasks": [
                {"name": "migrate", "service": "foobar-cluster:foobar-test"},
                {"name": "other", "service": "other-cluster:other"},
            ],
        }
        with patch.object(loader, "get_object_from_deployfish", return_value=service):
            controller.list_related_tasks()
        printed = [str(call.args[0]) for call in cement_app.print.call_args_list]
        assert "migrate" in printed

    def test_update_related_tasks_saves_each_task(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSServiceStandaloneTasks(), cement_app)
        cement_app.pargs.pk = "foobar-test"
        service = MagicMock()
        service.pk = "foobar-cluster:foobar-test"
        service.name = "foobar-test"
        loader = bind_service_loader(controller)
        cement_app.deployfish_config.cooked = {
            "tasks": [{"name": "migrate", "service": "foobar-test"}],
        }
        task = MagicMock(spec=StandaloneTask)
        task.name = "migrate"
        task.save.return_value = "arn:aws:ecs:1:task-definition/migrate:3"
        with patch.object(loader, "get_object_from_deployfish", side_effect=[service, task]):
            with patch("deployfish.controllers.service.click.secho"):
                controller.update_related_tasks()
        task.save.assert_called_once()
