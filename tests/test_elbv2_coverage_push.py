"""Additional ELBv2 manager coverage."""

from unittest.mock import MagicMock

import deployfish.core.adapters  # noqa: F401
from deployfish.core.models.elbv2 import (
    LoadBalancer,
    LoadBalancerListener,
    TargetGroup,
)

LB_ARN = "arn:aws:elasticloadbalancing:us-west-2:123:loadbalancer/app/test/abc"
TG_ARN = "arn:aws:elasticloadbalancing:us-west-2:123:targetgroup/tg/abc"

LB_DATA = {
    "LoadBalancerArn": LB_ARN,
    "LoadBalancerName": "test-lb",
    "DNSName": "test-lb.example.com",
    "VpcId": "vpc-123",
    "Type": "application",
    "Scheme": "internet-facing",
    "AvailabilityZones": [{"ZoneName": "us-west-2a", "SubnetId": "subnet-1"}],
}

TG_DATA = {
    "TargetGroupArn": TG_ARN,
    "TargetGroupName": "app-tg",
    "Port": 8080,
    "Protocol": "HTTP",
    "VpcId": "vpc-123",
    "HealthCheckProtocol": "HTTP",
    "HealthCheckPath": "/health",
}


def _paginate(client: MagicMock, pages: list[dict]) -> None:
    paginator = MagicMock()
    client.get_paginator.return_value = paginator
    paginator.paginate.return_value = pages


class TestLoadBalancerManagerPush:
    def test_get_by_name(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        _paginate(client, [{"LoadBalancers": [LB_DATA]}])
        lb = LoadBalancer.objects.get("test-lb")
        assert lb.name == "test-lb"

    def test_get_many_by_arn(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        _paginate(client, [{"LoadBalancers": [LB_DATA]}])
        lbs = LoadBalancer.objects.get_many([LB_ARN])
        assert len(lbs) == 1

    def test_list_filters_scheme_and_name(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        _paginate(client, [{"LoadBalancers": [LB_DATA]}])
        lbs = LoadBalancer.objects.list(name="test-*", scheme="internet-facing", vpc_id="vpc-123")
        assert len(lbs) == 1

class TestTargetGroupManagerPush:
    def test_get_target_group(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        _paginate(client, [{"TargetGroups": [TG_DATA]}])
        tg = TargetGroup.objects.get(TG_ARN)
        assert tg.port == 8080

    def test_get_many(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        _paginate(client, [{"TargetGroups": [TG_DATA]}])
        groups = TargetGroup.objects.get_many([TG_ARN])
        assert len(groups) == 1


class TestLoadBalancerListenerModelPush:
    def test_listener_properties(self) -> None:
        listener = LoadBalancerListener(
            {
                "ListenerArn": "arn:aws:elasticloadbalancing:us-west-2:123:listener/app/test/abc/def",
                "LoadBalancerArn": LB_ARN,
                "Port": 443,
                "Protocol": "HTTPS",
                "DefaultActions": [{"Type": "forward", "TargetGroupArn": TG_ARN}],
            }
        )
        assert listener.port == 443
        assert listener.protocol == "HTTPS"
