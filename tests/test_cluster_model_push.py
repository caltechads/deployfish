"""ECS Cluster model coverage."""

from unittest.mock import MagicMock

import pytest
from deployfish.core.models.ec2 import AutoscalingGroup
from deployfish.core.models.ecs import Cluster

CLUSTER_DATA = {
    "clusterName": "foobar-cluster",
    "clusterArn": "arn:aws:ecs:us-west-2:123:cluster/foobar-cluster",
    "defaultCapacityProviderStrategy": [{"capacityProvider": "FARGATE", "weight": 1}],
}

EC2_CLUSTER_DATA = {
    **CLUSTER_DATA,
    "defaultCapacityProviderStrategy": [
        {"capacityProvider": "EC2-capacity", "weight": 1}
    ],
}


class TestClusterModelPush:
    def test_cluster_type_fargate(self) -> None:
        cluster = Cluster(CLUSTER_DATA)
        assert cluster.cluster_type == "FARGATE"

    def test_cluster_type_ec2(self) -> None:
        cluster = Cluster(EC2_CLUSTER_DATA)
        assert cluster.cluster_type == "EC2"

    def test_scale_ec2_delegates_to_asg(self) -> None:
        cluster = Cluster(EC2_CLUSTER_DATA)
        asg = MagicMock(spec=AutoscalingGroup)
        cluster.cache["autoscaling_group"] = asg
        cluster.scale(3, force=True)
        asg.scale.assert_called_once_with(3, force=True)

    def test_scale_fargate_raises(self) -> None:
        cluster = Cluster(CLUSTER_DATA)
        with pytest.raises(Cluster.OperationFailed, match="FARGATE"):
            cluster.scale(1)
