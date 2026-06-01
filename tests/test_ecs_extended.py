from copy import deepcopy
from unittest.mock import MagicMock, patch

import deployfish.core.adapters  # noqa: F401
from deployfish.core.models.ec2 import Instance, Subnet
from deployfish.core.models.ecs import Cluster, InvokedTask, Service, StandaloneTask
from deployfish.core.models.ssh import SSHTunnel

from tests.fixtures import FARGATE_SERVICE_YML, SERVICE_YML, STANDALONE_TASK_YML


class TestClusterModel:
    def test_cluster_name_property(self) -> None:
        cluster = Cluster(
            {"clusterName": "foobar-cluster", "clusterArn": "arn:cluster:1"}
        )
        assert cluster.name == "foobar-cluster"
        assert cluster.pk == "foobar-cluster"


class TestInvokedTaskModel:
    def test_invoked_task_arn_property(self) -> None:
        task = InvokedTask(
            {
                "taskArn": "arn:aws:ecs:us-west-2:123:task/cluster/abc123",
                "clusterArn": "arn:aws:ecs:us-west-2:123:cluster/foobar-cluster",
                "lastStatus": "RUNNING",
            }
        )
        assert task.arn.endswith("abc123")
        assert task.cluster_name == "foobar-cluster"


class TestStandaloneTaskExtended:
    def test_standalone_task_name_and_cluster(self) -> None:
        task = StandaloneTask.new(deepcopy(STANDALONE_TASK_YML), "deployfish")
        assert task.name == "foobar-test-mytask"
        assert task.data["cluster"] == "foobar-cluster"

    def test_standalone_task_run_delegates_to_objects(self) -> None:
        task = StandaloneTask.new(deepcopy(STANDALONE_TASK_YML), "deployfish")
        invoked = MagicMock()
        with patch.object(
            StandaloneTask.objects, "run", return_value=[invoked]
        ) as run_mock:
            result = task.run()
        run_mock.assert_called_once_with(task)
        assert result == [invoked]


class TestServiceExtended:
    def test_service_render_for_create_includes_cluster(self) -> None:
        service = Service.new(deepcopy(SERVICE_YML), "deployfish")
        data = service.render_for_create()
        assert data["cluster"] == "foobar-cluster"
        assert data["serviceName"] == "foobar-test"

    def test_fargate_service_launch_type(self) -> None:
        service = Service.new(deepcopy(FARGATE_SERVICE_YML), "deployfish")
        assert service.launch_type == "FARGATE"

    def test_service_reload_from_db(self) -> None:
        service = Service.new(deepcopy(SERVICE_YML), "deployfish")
        replacement = Service.new(deepcopy(SERVICE_YML), "deployfish")
        replacement.data["desiredCount"] = 5
        with patch.object(Service.objects, "get", return_value=replacement):
            service.reload_from_db()
        assert service.data["desiredCount"] == 5


class TestEC2Models:
    def test_subnet_pk(self) -> None:
        subnet = Subnet(
            {
                "SubnetId": "subnet-abc",
                "VpcId": "vpc-123",
                "CidrBlock": "10.0.1.0/24",
                "AvailableIpAddressCount": 250,
            }
        )
        assert subnet.pk == "subnet-abc"
        assert subnet.cidr_block == "10.0.1.0/24"
        with patch.object(
            Subnet.objects,
            "get_tags",
            return_value=[{"Key": "Name", "Value": "private-a"}],
        ):
            assert subnet.name == "private-a"

    def test_instance_ip_address(self) -> None:
        instance = Instance(
            {
                "InstanceId": "i-123",
                "PrivateIpAddress": "10.0.0.10",
                "PublicDnsName": "",
                "PrivateDnsName": "ip-10-0-0-10.internal",
                "Tags": [{"Key": "Name", "Value": "worker"}],
            }
        )
        assert instance.ip_address == "10.0.0.10"
        assert instance.name == "worker"


class TestSSHTunnelModel:
    def test_ssh_tunnel_properties(self) -> None:
        tunnel = SSHTunnel(
            {
                "name": "mysql-qa",
                "host": "db.internal",
                "port": 3306,
                "local_port": 13306,
            }
        )
        assert tunnel.name == "mysql-qa"
        assert tunnel.host_port == 3306
        assert tunnel.local_port == 13306
