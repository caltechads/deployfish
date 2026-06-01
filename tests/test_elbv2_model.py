
import deployfish.core.adapters  # noqa: F401
from deployfish.core.models.elbv2 import LoadBalancer, TargetGroup


class TestLoadBalancerModel:
    def test_load_balancer_name_property(self) -> None:
        lb = LoadBalancer(
            {
                "LoadBalancerArn": "arn:aws:elasticloadbalancing:us-west-2:123:loadbalancer/app/test/abc",
                "LoadBalancerName": "test-lb",
                "DNSName": "test-lb.example.com",
                "VpcId": "vpc-123",
                "Type": "application",
                "Scheme": "internet-facing",
            }
        )
        assert lb.name == "test-lb"
        assert lb.hostname == "test-lb.example.com"
        assert lb.lb_type == "ALB"

    def test_load_balancer_scheme_property(self) -> None:
        lb = LoadBalancer(
            {
                "LoadBalancerArn": "arn:1",
                "LoadBalancerName": "internal-lb",
                "DNSName": "internal.example.com",
                "VpcId": "vpc-123",
                "Type": "network",
                "Scheme": "internal",
            }
        )
        assert lb.scheme == "internal"
        assert lb.lb_type == "NLB"


class TestTargetGroupModel:
    def test_target_group_port_and_protocol(self) -> None:
        tg = TargetGroup(
            {
                "TargetGroupArn": "arn:aws:elasticloadbalancing:us-west-2:123:targetgroup/tg/abc",
                "TargetGroupName": "app-tg",
                "Port": 8080,
                "Protocol": "HTTP",
                "VpcId": "vpc-123",
            }
        )
        assert tg.name == "app-tg"
        assert tg.port == 8080
        assert tg.protocol == "HTTP"
