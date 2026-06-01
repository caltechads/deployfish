from unittest.mock import MagicMock, patch

import pytest
from deployfish.core.models.elbv2 import (
    LoadBalancer,
    LoadBalancerListener,
    LoadBalancerListenerRule,
    TargetGroup,
)


def _paginate(client: MagicMock, pages: list[dict]) -> None:
    paginator = MagicMock()
    client.get_paginator.return_value = paginator
    paginator.paginate.return_value = pages


LB_DATA = {
    "LoadBalancerArn": "arn:aws:elasticloadbalancing:us-west-2:123:loadbalancer/app/test/abc",
    "LoadBalancerName": "test-lb",
    "DNSName": "test-lb.example.com",
    "VpcId": "vpc-123",
    "Type": "application",
    "Scheme": "internet-facing",
}

LISTENER_DATA = {
    "ListenerArn": "arn:aws:elasticloadbalancing:us-west-2:123:listener/app/test/abc/def",
    "LoadBalancerArn": LB_DATA["LoadBalancerArn"],
    "Port": 443,
    "Protocol": "HTTPS",
    "DefaultActions": [{"Type": "forward", "TargetGroupArn": "arn:tg/1"}],
}

TG_DATA = {
    "TargetGroupArn": "arn:aws:elasticloadbalancing:us-west-2:123:targetgroup/tg/abc",
    "TargetGroupName": "app-tg",
    "Port": 8080,
    "Protocol": "HTTP",
    "VpcId": "vpc-123",
    "LoadBalancerArns": [LB_DATA["LoadBalancerArn"]],
}


class TestLoadBalancerManager:
    def test_get_by_name(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        _paginate(client, [{"LoadBalancers": [LB_DATA]}])
        lb = LoadBalancer.objects.get("test-lb")
        assert lb.name == "test-lb"

    def test_list_filters_vpc_and_scheme(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        internal = {**LB_DATA, "LoadBalancerName": "internal-lb", "Scheme": "internal"}
        _paginate(client, [{"LoadBalancers": [LB_DATA, internal]}])
        lbs = LoadBalancer.objects.list(vpc_id="vpc-123", scheme="internet-facing")
        assert len(lbs) == 1
        assert lbs[0].scheme == "internet-facing"

    def test_get_tags(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        client.describe_tags.return_value = {
            "TagDescriptions": {"Tags": [{"Key": "Name", "Value": "test-lb"}]},
        }
        tags = LoadBalancer.objects.get_tags(LB_DATA["LoadBalancerArn"])
        assert tags[0]["Value"] == "test-lb"


class TestLoadBalancerListenerManager:
    def test_get_listener(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        client.describe_listeners.return_value = {"Listeners": [LISTENER_DATA]}
        listener = LoadBalancerListener.objects.get(LISTENER_DATA["ListenerArn"])
        assert listener.port == 443

    def test_list_by_load_balancer_name(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        client.exceptions.LoadBalancerNotFoundException = type(
            "LoadBalancerNotFoundException",
            (Exception,),
            {},
        )
        lb = LoadBalancer(LB_DATA)
        _paginate(client, [{"Listeners": [LISTENER_DATA]}])
        with patch.object(LoadBalancer.objects, "get", return_value=lb):
            listeners = LoadBalancerListener.objects.list("test-lb")
        assert len(listeners) == 1


class TestTargetGroupManager:
    def test_get_target_group(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        _paginate(client, [{"TargetGroups": [TG_DATA]}])
        tg = TargetGroup.objects.get("app-tg")
        assert tg.port == 8080

    def test_list_target_groups(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        _paginate(client, [{"TargetGroups": [TG_DATA]}])
        groups = TargetGroup.objects.list()
        assert len(groups) == 1


class TestLoadBalancerListenerRuleManager:
    def test_list_by_listener_arn(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        rule_data = {
            "RuleArn": "arn:rule/1",
            "Priority": "1",
            "Conditions": [],
            "Actions": [{"Type": "forward", "TargetGroupArn": TG_DATA["TargetGroupArn"]}],
        }
        _paginate(client, [{"Rules": [rule_data]}])
        rules = LoadBalancerListenerRule.objects.list(
            listener_arn=LISTENER_DATA["ListenerArn"]
        )
        assert len(rules) == 1

    def test_list_rejects_multiple_filters(self) -> None:
        with pytest.raises(LoadBalancerListener.OperationFailed):
            LoadBalancerListenerRule.objects.list(
                listener_arn="arn:listener/1",
                load_balancer_pk="test-lb",
            )
