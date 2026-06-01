from unittest.mock import MagicMock

from deployfish.core.models.ecs import Service


def _cluster_paginator(client: MagicMock, clusters: list[str]) -> MagicMock:
    paginator = MagicMock()
    paginator.paginate.return_value = [{"clusterArns": [f"arn:aws:ecs:1:cluster/{name}" for name in clusters]}]
    return paginator


def _service_paginator(client: MagicMock, services: list[str]) -> MagicMock:
    paginator = MagicMock()
    paginator.paginate.return_value = [{"serviceArns": services}]
    return paginator


class TestServiceManagerList:
    def test_list_services_in_cluster(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        client.exceptions.ClusterNotFoundException = type(
            "ClusterNotFoundException",
            (Exception,),
            {},
        )
        cluster_paginator = _cluster_paginator(client, ["foobar-cluster"])
        service_paginator = _service_paginator(client, ["foobar-test"])
        client.get_paginator.side_effect = [cluster_paginator, service_paginator]
        service_data = {
            "serviceName": "foobar-test",
            "clusterArn": "arn:aws:ecs:1:cluster/foobar-cluster",
            "status": "ACTIVE",
            "taskDefinition": "arn:1",
            "desiredCount": 1,
            "runningCount": 1,
        }
        client.describe_services.return_value = {"services": [service_data]}
        services = Service.objects.list(cluster_name="foobar-*")
        assert len(services) == 1
        assert services[0].name == "foobar-test"

    def test_list_filters_by_launch_type(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        client.exceptions.ClusterNotFoundException = type(
            "ClusterNotFoundException",
            (Exception,),
            {},
        )
        cluster_paginator = _cluster_paginator(client, ["c1"])
        service_paginator = _service_paginator(client, [])
        client.get_paginator.side_effect = [cluster_paginator, service_paginator]
        client.describe_services.return_value = {"services": []}
        services = Service.objects.list(launch_type="FARGATE")
        assert services == []
