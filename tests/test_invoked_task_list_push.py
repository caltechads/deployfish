"""InvokedTaskManager list/get coverage."""

from unittest.mock import MagicMock

import pytest
from deployfish.core.models.ecs import Cluster, InvokedTask, Service

TASK_DATA = {
    "taskArn": "arn:aws:ecs:us-west-2:123:task/cluster/abc",
    "clusterArn": "arn:aws:ecs:us-west-2:123:cluster/foobar-cluster",
    "lastStatus": "RUNNING",
}


class TestInvokedTaskManagerList:
    def test_list_with_service_filter(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        client.list_tasks.return_value = {"taskArns": [TASK_DATA["taskArn"]]}
        client.describe_tasks.return_value = {"tasks": [TASK_DATA], "failures": []}
        tasks = InvokedTask.objects.list("foobar-cluster", service="foobar-test")
        client.list_tasks.assert_called_once_with(
            cluster="foobar-cluster",
            desiredStatus="RUNNING",
            serviceName="foobar-test",
        )
        assert len(tasks) == 1

    def test_list_raises_when_service_missing(
        self, _mock_boto3_session: MagicMock
    ) -> None:
        client = _mock_boto3_session
        cluster_exc = type("ClusterNotFoundException", (Exception,), {})
        service_exc = type("ServiceNotFoundException", (Exception,), {})
        client.exceptions.ClusterNotFoundException = cluster_exc
        client.exceptions.ServiceNotFoundException = service_exc
        client.list_tasks.side_effect = service_exc("missing")
        with pytest.raises(Service.DoesNotExist):
            InvokedTask.objects.list("foobar-cluster", service="missing")

    def test_list_raises_when_cluster_missing(
        self, _mock_boto3_session: MagicMock
    ) -> None:
        client = _mock_boto3_session
        cluster_exc = type("ClusterNotFoundException", (Exception,), {})
        service_exc = type("ServiceNotFoundException", (Exception,), {})
        client.exceptions.ClusterNotFoundException = cluster_exc
        client.exceptions.ServiceNotFoundException = service_exc
        client.list_tasks.side_effect = cluster_exc("missing")
        with pytest.raises(Cluster.DoesNotExist):
            InvokedTask.objects.list("missing-cluster")
