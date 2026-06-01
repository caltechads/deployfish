from unittest.mock import MagicMock, patch

from deployfish.controllers.cluster import ECSCluster
from deployfish.core.loaders import ObjectLoader
from deployfish.core.models.ecs import Cluster

from tests.controller_helpers import bind_controller, bind_loader_factory


class TestECSClusterControllerExtended:
    def test_exists_shows_present(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSCluster(), cement_app)
        cement_app.pargs.pk = "foobar-cluster"
        loader = bind_loader_factory(controller, ObjectLoader(controller))
        cluster = Cluster({"clusterName": "foobar-cluster", "clusterArn": "arn:1"})
        with patch.object(loader, "get_object_from_aws", return_value=cluster):
            with patch("deployfish.controllers.crud.click.secho") as secho:
                controller.exists()
        secho.assert_called_once()

    def test_info_renders_cluster(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSCluster(), cement_app)
        cement_app.pargs.pk = "foobar-cluster"
        cluster = Cluster({"clusterName": "foobar-cluster", "clusterArn": "arn:1"})
        loader = bind_loader_factory(controller, ObjectLoader(controller))
        with patch.object(loader, "get_object_from_aws", return_value=cluster):
            controller.info()
        cement_app.render.assert_called_once()
