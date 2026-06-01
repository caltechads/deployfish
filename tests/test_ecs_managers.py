from unittest.mock import MagicMock, patch

import pytest
from deployfish.core.models.ecs import Cluster, InvokedTask, Service, StandaloneTask


def _paginate(client: MagicMock, pages: list[dict]) -> None:
    paginator = MagicMock()
    client.get_paginator.return_value = paginator
    paginator.paginate.return_value = pages


CLUSTER_DATA = {
    "clusterName": "foobar-cluster",
    "clusterArn": "arn:aws:ecs:us-west-2:123:cluster/foobar-cluster",
    "status": "ACTIVE",
}

SERVICE_DATA = {
    "serviceName": "foobar-test",
    "clusterArn": "arn:aws:ecs:us-west-2:123:cluster/foobar-cluster",
    "status": "ACTIVE",
    "taskDefinition": "arn:aws:ecs:us-west-2:123:task-definition/foobar-test:1",
    "desiredCount": 1,
    "runningCount": 1,
}


class TestClusterManager:
    def test_get_returns_cluster(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        client.describe_clusters.return_value = {"clusters": [CLUSTER_DATA]}
        cluster = Cluster.objects.get("foobar-cluster")
        assert cluster.name == "foobar-cluster"

    def test_get_raises_when_missing(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        client.describe_clusters.return_value = {"clusters": []}
        with pytest.raises(Cluster.DoesNotExist):
            Cluster.objects.get("missing-cluster")

    def test_exists_false_when_missing(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        client.describe_clusters.return_value = {"clusters": []}
        assert Cluster.objects.exists("missing-cluster") is False

    def test_list_filters_by_glob(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        _paginate(
            client,
            [
                {
                    "clusterArns": [
                        "arn:aws:ecs:us-west-2:123:cluster/foobar-cluster",
                        "arn:aws:ecs:us-west-2:123:cluster/other-cluster",
                    ]
                }
            ],
        )
        client.describe_clusters.return_value = {
            "clusters": [CLUSTER_DATA],
        }
        clusters = Cluster.objects.list("foobar-*")
        assert len(clusters) == 1
        assert clusters[0].name == "foobar-cluster"

    def test_save_raises_read_only(self) -> None:
        cluster = Cluster(CLUSTER_DATA)
        with pytest.raises(Cluster.ReadOnly):
            Cluster.objects.save(cluster)


class TestServiceManager:
    def test_get_returns_service(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        client.describe_services.return_value = {"services": [SERVICE_DATA]}
        service = Service.objects.get("foobar-cluster:foobar-test")
        assert service.data["cluster"] == "foobar-cluster"

    def test_get_raises_when_inactive(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        inactive = {**SERVICE_DATA, "status": "INACTIVE"}
        client.describe_services.return_value = {"services": [inactive]}
        with pytest.raises(Service.DoesNotExist):
            Service.objects.get("foobar-cluster:foobar-test")

    def test_get_raises_when_cluster_missing(
        self, _mock_boto3_session: MagicMock
    ) -> None:
        client = _mock_boto3_session
        exc = type("ClusterNotFoundException", (Exception,), {})
        client.exceptions.ClusterNotFoundException = exc
        client.describe_services.side_effect = exc("cluster missing")
        with pytest.raises(Cluster.DoesNotExist):
            Service.objects.get("missing:foobar-test")

    def test_get_many_chunks_large_service_lists(
        self, _mock_boto3_session: MagicMock
    ) -> None:
        client = _mock_boto3_session
        client.describe_services.return_value = {
            "services": [{**SERVICE_DATA, "serviceName": "svc-0"}],
        }
        pks = [f"foobar-cluster:svc-{index}" for index in range(11)]
        services = Service.objects.get_many(pks)
        assert client.describe_services.call_count == 2
        assert len(services) == 2

    def test_exists_true_when_active(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        client.describe_services.return_value = {"services": [SERVICE_DATA]}
        assert Service.objects.exists("foobar-cluster:foobar-test") is True


class TestInvokedTaskManager:
    def test_list_tasks_returns_invoked_tasks(
        self, _mock_boto3_session: MagicMock
    ) -> None:
        client = _mock_boto3_session
        client.list_tasks.return_value = {
            "taskArns": ["arn:aws:ecs:us-west-2:123:task/cluster/abc"],
        }
        client.describe_tasks.return_value = {
            "tasks": [
                {
                    "taskArn": "arn:aws:ecs:us-west-2:123:task/cluster/abc",
                    "clusterArn": "arn:aws:ecs:us-west-2:123:cluster/foobar-cluster",
                    "lastStatus": "RUNNING",
                }
            ],
        }
        tasks = InvokedTask.objects.list(cluster="foobar-cluster")
        assert len(tasks) == 1
        assert tasks[0].cluster_name == "foobar-cluster"


class TestStandaloneTaskManager:
    def test_run_delegates_to_client(self, _mock_boto3_session: MagicMock) -> None:
        from copy import deepcopy

        import deployfish.core.adapters  # noqa: F401

        client = _mock_boto3_session
        client.run_task.return_value = {
            "tasks": [
                {
                    "taskArn": "arn:aws:ecs:us-west-2:123:task/cluster/run-1",
                    "clusterArn": "arn:aws:ecs:us-west-2:123:cluster/foobar-cluster",
                    "lastStatus": "PENDING",
                }
            ],
        }
        from tests.fixtures import STANDALONE_TASK_YML

        task = StandaloneTask.new(deepcopy(STANDALONE_TASK_YML), "deployfish")
        with patch.object(task, "render", return_value={"cluster": "foobar-cluster"}):
            with patch.object(task, "task_definition", create=True) as td_mock:
                td_mock.pk = "arn:task-def:1"
                results = StandaloneTask.objects.run(task)
        assert len(results) == 1
        client.run_task.assert_called_once()
