from unittest.mock import MagicMock

import pytest
from deployfish.core.models.elb import ClassicLoadBalancer


def _paginate(client: MagicMock, pages: list[dict]) -> None:
    paginator = MagicMock()
    client.get_paginator.return_value = paginator
    paginator.paginate.return_value = pages


LB_DATA = {
    "LoadBalancerName": "classic-lb",
    "DNSName": "classic.example.com",
    "VpcId": "vpc-123",
    "Scheme": "internet-facing",
    "ListenerDescriptions": [],
    "Instances": [],
}


class TestClassicLoadBalancerManager:
    def test_get_load_balancer(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        _paginate(client, [{"LoadBalancerDescriptions": [LB_DATA]}])
        lb = ClassicLoadBalancer.objects.get("classic-lb")
        assert lb.name == "classic-lb"

    def test_list_filters_by_name(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        other = {**LB_DATA, "LoadBalancerName": "other-lb"}
        _paginate(client, [{"LoadBalancerDescriptions": [LB_DATA, other]}])
        lbs = ClassicLoadBalancer.objects.list(name="classic-*")
        assert len(lbs) == 1

    def test_get_raises_when_not_found(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        _paginate(client, [{"LoadBalancerDescriptions": []}])
        with pytest.raises(IndexError):
            ClassicLoadBalancer.objects.get("missing")
