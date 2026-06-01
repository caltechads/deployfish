from copy import deepcopy
from unittest.mock import MagicMock, patch

import deployfish.core.adapters  # noqa: F401
from deployfish.controllers.service import ECSService
from deployfish.core.models.ecs import Cluster, Service

from tests.controller_helpers import bind_controller, bind_service_loader
from tests.fixtures import SERVICE_YML


class TestReadOnlyCrudController:
    def test_exists_shows_missing(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSService(), cement_app)
        cement_app.pargs.pk = "foobar-cluster:missing"
        loader = bind_service_loader(controller)
        with patch.object(loader, "get_object_from_aws", side_effect=Service.DoesNotExist("nope")):
            with patch("deployfish.controllers.crud.click.secho") as secho:
                controller.exists()
        secho.assert_called_once()

    def test_info_renders_object(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSService(), cement_app)
        cement_app.pargs.pk = "foobar-cluster:foobar-test"
        mock_service = MagicMock()
        loader = bind_service_loader(controller)
        with patch.object(loader, "get_object_from_aws", return_value=mock_service):
            controller.info()
        cement_app.render.assert_called_once()

    def test_list_renders_table(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSService(), cement_app)
        with patch.object(Service.objects, "list", return_value=[]):
            controller.list()
        cement_app.print.assert_called_once()


class TestCrudDelete:
    def test_delete_aborts_on_wrong_name(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSService(), cement_app)
        cement_app.pargs.name = "foobar-test"
        service = Service.new(deepcopy(SERVICE_YML), "deployfish")
        loader = bind_service_loader(controller)
        prompt = MagicMock()
        prompt.prompt.return_value = "wrong-name"
        with patch.object(loader, "get_object_from_deployfish", return_value=service):
            with patch.object(service, "reload_from_db"):
                with patch.object(controller, "delete_waiter"):
                    with patch("deployfish.controllers.crud.shell.Prompt", return_value=prompt):
                        with patch("deployfish.controllers.crud.click.style", side_effect=lambda v, **_: v):
                            controller.delete()
        printed = " ".join(str(call) for call in cement_app.print.call_args_list)
        assert "ABORTED" in printed

    def test_delete_removes_on_matching_name(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSService(), cement_app)
        cement_app.pargs.name = "foobar-test"
        service = Service.new(deepcopy(SERVICE_YML), "deployfish")
        loader = bind_service_loader(controller)
        prompt = MagicMock()
        prompt.prompt.return_value = service.name
        with patch.object(loader, "get_object_from_deployfish", return_value=service):
            with patch.object(service, "reload_from_db"):
                with patch.object(service, "delete") as delete_mock:
                    with patch.object(controller, "delete_waiter"):
                        with patch("deployfish.controllers.crud.shell.Prompt", return_value=prompt):
                            with patch("deployfish.controllers.crud.click.style", side_effect=lambda v, **_: v):
                                controller.delete()
        delete_mock.assert_called_once()


class TestClusterReadOnly:
    def test_cluster_list(self, cement_app: MagicMock) -> None:
        from deployfish.controllers.cluster import ECSCluster

        controller = bind_controller(ECSCluster(), cement_app)
        with patch.object(Cluster.objects, "list", return_value=[]):
            controller.list()
        cement_app.print.assert_called_once()
