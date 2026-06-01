from unittest.mock import MagicMock, patch

from deployfish.controllers.cluster import ECSCluster
from deployfish.controllers.logs import LogsCloudWatchLogGroup
from deployfish.core.models.cloudwatchlogs import CloudWatchLogGroup

from tests.controller_helpers import bind_controller


class TestECSClusterController:
    def test_list_renders_clusters(self, cement_app: MagicMock) -> None:
        from deployfish.core.models.ecs import Cluster

        controller = bind_controller(ECSCluster(), cement_app)
        with patch.object(Cluster.objects, "list", return_value=[]):
            controller.list()
        cement_app.print.assert_called_once()


class TestLogsController:
    def test_log_group_list_renders(self, cement_app: MagicMock) -> None:
        controller = bind_controller(LogsCloudWatchLogGroup(), cement_app)
        cement_app.pargs.prefix = None
        with patch.object(CloudWatchLogGroup.objects, "list", return_value=[]):
            controller.list()
        cement_app.print.assert_called_once()
