"""Service and TaskDefinition property coverage."""

from copy import deepcopy
from unittest.mock import MagicMock, patch

import deployfish.core.adapters  # noqa: F401
from deployfish.core.models.ecs import Service
from deployfish.core.models.elb import ClassicLoadBalancer
from deployfish.core.models.elbv2 import TargetGroup
from deployfish.core.models.secrets import Secret

from tests.fixtures import SERVICE_YML


def _service() -> Service:
    service = Service.new(deepcopy(SERVICE_YML), "deployfish")
    service.data["cluster"] = "foobar-cluster"
    service.data["serviceName"] = "foobar-test"
    service.data["taskDefinition"] = "arn:aws:ecs:us-west-2:123:task-definition/foobar-test:1"
    return service


class TestServiceRelatedObjects:
    def test_secrets_prefix_reload_and_setter(self) -> None:
        service = _service()
        assert service.secrets_prefix == "foobar-cluster.foobar-test."
        secret = MagicMock(spec=Secret)
        service.secrets = {"DEBUG": secret}
        assert service.secrets["DEBUG"] is secret
        with patch.object(service.task_definition, "reload_secrets") as reload_mock:
            service.reload_secrets()
        reload_mock.assert_called_once()

    def test_load_balancers_target_group(self) -> None:
        service = _service()
        service.data["loadBalancers"] = [
            {"targetGroupArn": "arn:aws:elasticloadbalancing:us-west-2:123:targetgroup/tg/1"},
        ]
        tg = TargetGroup(
            {
                "TargetGroupArn": "arn:aws:elasticloadbalancing:us-west-2:123:targetgroup/tg/1",
                "TargetGroupName": "tg",
                "Port": 80,
                "Protocol": "HTTP",
                "VpcId": "vpc-1",
            }
        )
        with patch.object(TargetGroup.objects, "get", return_value=tg):
            lbs = service.load_balancers
        assert lbs[0]["TargetGroup"] is tg

    def test_load_balancers_classic(self) -> None:
        service = _service()
        service.data["loadBalancers"] = [{"loadBalancerName": "classic-lb"}]
        clb = ClassicLoadBalancer(
            {
                "LoadBalancerName": "classic-lb",
                "DNSName": "lb.example.com",
                "VpcId": "vpc-1",
                "Scheme": "internet-facing",
            }
        )
        with patch.object(ClassicLoadBalancer.objects, "get", return_value=clb):
            lbs = service.load_balancers
        assert lbs[0]["LoadBalancer"] is clb

    def test_appscaling_property_and_setter(self) -> None:
        from deployfish.core.models.appscaling import ScalableTarget

        service = _service()
        scaling = MagicMock(spec=ScalableTarget)
        with patch.object(
            ScalableTarget.objects,
            "get",
            return_value=scaling,
        ):
            assert service.appscaling is scaling
        service.appscaling = None
        assert service.appscaling is None

    def test_service_discovery_from_registry(self) -> None:
        from deployfish.core.models.service_discovery import ServiceDiscoveryService

        service = _service()
        service.data["serviceRegistries"] = [{"registryArn": "arn:registry:1"}]
        sd = ServiceDiscoveryService(
            {
                "Id": "srv-1",
                "Arn": "arn:registry:1",
                "Name": "api",
                "DNSConfig": {"NamespaceId": "ns-1", "RoutingPolicy": "MULTIVALUE", "DnsRecords": []},
            }
        )
        with patch.object(ServiceDiscoveryService.objects, "get", return_value=sd):
            assert service.service_discovery is sd

    def test_running_tasks_delegates(self) -> None:
        from deployfish.core.models.ecs import InvokedTask

        service = _service()
        invoked = MagicMock(spec=InvokedTask)
        with patch.object(InvokedTask.objects, "list", return_value=[invoked]) as list_mock:
            tasks = service.running_tasks
        list_mock.assert_called_once_with("foobar-cluster", service="foobar-test")
        assert tasks == [invoked]

