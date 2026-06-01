"""ContainerInstance manager readonly and model coverage."""

from unittest.mock import MagicMock

import pytest
from deployfish.core.models.ecs import Cluster, ContainerInstance

CI_DATA = {
    "containerInstanceArn": "arn:aws:ecs:us-west-2:123:container-instance/abc",
    "ec2InstanceId": "i-abc123",
}


class TestContainerInstanceManager:
    def test_save_and_delete_raise_read_only(self) -> None:
        ci = ContainerInstance(CI_DATA, cluster="foobar-cluster")
        with pytest.raises(Cluster.ReadOnly):
            ContainerInstance.objects.save(ci)
        with pytest.raises(Cluster.ReadOnly):
            ContainerInstance.objects.delete(ci)

    def test_list_raises_cluster_not_found(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        exc = type("ClusterNotFoundException", (Exception,), {})
        client.exceptions.ClusterNotFoundException = exc
        client.list_container_instances.side_effect = exc("missing")
        with pytest.raises(Cluster.DoesNotExist):
            ContainerInstance.objects.list("missing-cluster")
