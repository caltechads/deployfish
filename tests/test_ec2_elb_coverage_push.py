"""Coverage push for ec2 and classic ELB models."""

from unittest.mock import MagicMock, patch

import botocore
import pytest
from deployfish.core.models.abstract import Model
from deployfish.core.models.ec2 import (
    VPC,
    AutoscalingGroup,
    Instance,
    SecurityGroup,
)
from deployfish.core.models.elb import ClassicLoadBalancer, ClassicLoadBalancerTarget

VPC_DATA = {
    "VpcId": "vpc-123",
    "CidrBlock": "10.0.0.0/16",
    "Tags": [{"Key": "Name", "Value": "main-vpc"}],
}

INSTANCE_DATA = {
    "InstanceId": "i-abc123",
    "PrivateIpAddress": "10.0.1.5",
    "PublicDnsName": "public.example.com",
    "PrivateDnsName": "ip-10-0-1-5.internal",
    "VpcId": "vpc-123",
    "SubnetId": "subnet-abc",
    "State": {"Name": "running"},
    "Tags": [{"Key": "Name", "Value": "worker-1"}],
}


def _paginate(client: MagicMock, pages: list[dict]) -> None:
    paginator = MagicMock()
    client.get_paginator.return_value = paginator
    paginator.paginate.return_value = pages


class TestVPCManagerGaps:
    def test_get_by_name_via_tags(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        _paginate(client, [{"Vpcs": [VPC_DATA]}])
        vpc = VPC.objects.get("main-vpc")
        assert vpc.pk == "vpc-123"

    def test_get_many_by_name_filter(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        _paginate(client, [{"Vpcs": [VPC_DATA]}])
        vpcs = VPC.objects.get_many(["main-vpc"])
        assert len(vpcs) == 1

    def test_list_filters_by_name_glob(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        named_vpc = {
            **VPC_DATA,
            "Tags": [{"Name": "Name", "Value": "main-vpc"}],
        }
        other_vpc = {
            **VPC_DATA,
            "VpcId": "vpc-456",
            "Tags": [{"Name": "Name", "Value": "other"}],
        }
        with patch.object(VPC, "__init__", Model.__init__):
            _paginate(client, [{"Vpcs": [named_vpc, other_vpc]}])
            vpcs = VPC.objects.list(name="main*")
        assert len(vpcs) == 1

    def test_list_skips_unnamed_when_filtering(
        self, _mock_boto3_session: MagicMock
    ) -> None:
        client = _mock_boto3_session
        no_name = {**VPC_DATA, "VpcId": "vpc-noname", "Tags": []}
        _paginate(client, [{"Vpcs": [no_name]}])
        vpcs = VPC.objects.list(name="main*")
        assert vpcs == []


class TestSecurityGroupManagerGaps:
    def test_get_by_group_name(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        client.describe_security_groups.return_value = {
            "SecurityGroups": [
                {"GroupId": "sg-abc", "GroupName": "default", "VpcId": "vpc-123"}
            ],
        }
        sg = SecurityGroup.objects.get("default")
        assert sg.pk == "sg-abc"

    def test_get_raises_not_found(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        exc = botocore.exceptions.ClientError(
            {"Error": {"Code": "InvalidGroup.NotFound", "Message": "not found"}},
            "DescribeSecurityGroups",
        )
        client.describe_security_groups.side_effect = exc
        with pytest.raises(SecurityGroup.DoesNotExist):
            SecurityGroup.objects.get("sg-missing")

    def test_list_filters_by_vpc(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        _paginate(
            client,
            [{"SecurityGroups": [{"GroupId": "sg-1", "VpcId": "vpc-123"}]}],
        )
        groups = SecurityGroup.objects.list(vpc_id="vpc-123")
        assert len(groups) == 1


class TestInstanceManagerGaps:
    def test_get_many_by_name_prefix(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        _paginate(client, [{"Reservations": [{"Instances": [INSTANCE_DATA]}]}])
        instances = Instance.objects.get_many(["Name:worker-1"], vpc_id="vpc-123")
        assert len(instances) == 1

    def test_get_multiple_raises(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        _paginate(
            client,
            [
                {
                    "Reservations": [
                        {
                            "Instances": [
                                INSTANCE_DATA,
                                {**INSTANCE_DATA, "InstanceId": "i-2"},
                            ]
                        }
                    ]
                }
            ],
        )
        with pytest.raises(Instance.MultipleObjectsReturned):
            Instance.objects.get("i-abc123")

    def test_list_with_filters(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        _paginate(client, [{"Reservations": [{"Instances": [INSTANCE_DATA]}]}])
        instances = Instance.objects.list(
            vpc_ids=["vpc-123"],
            tags=["Name:worker-1"],
        )
        assert len(instances) == 1


class TestAutoscalingGroupManager:
    ASG_DATA = {
        "AutoScalingGroupName": "ecs-asg",
        "AutoScalingGroupARN": "arn:asg:1",
        "MinSize": 1,
        "MaxSize": 4,
        "DesiredCapacity": 2,
        "Instances": [{"InstanceId": "i-abc123"}],
    }

    def test_get_and_list(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        client.describe_auto_scaling_groups.return_value = {
            "AutoScalingGroups": [self.ASG_DATA]
        }
        asg = AutoscalingGroup.objects.get("ecs-asg")
        assert asg.name == "ecs-asg"
        listed = AutoscalingGroup.objects.list()
        assert len(listed) == 1

    def test_get_raises_when_missing(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        exc = botocore.exceptions.ClientError(
            {"Error": {"Code": "ValidationError", "Message": "not found"}},
            "DescribeAutoScalingGroups",
        )
        client.describe_auto_scaling_groups.side_effect = exc
        with pytest.raises(AutoscalingGroup.DoesNotExist):
            AutoscalingGroup.objects.get("missing")

    def test_save_calls_update(self, _mock_boto3_session: MagicMock) -> None:
        asg = AutoscalingGroup(self.ASG_DATA)
        AutoscalingGroup.objects.save(asg)
        _mock_boto3_session.update_auto_scaling_group.assert_called_once()


class TestInstanceModelProperties:
    def test_hostname_uses_public_dns(self) -> None:
        instance = Instance(INSTANCE_DATA)
        assert instance.hostname == "public.example.com"

    def test_autoscaling_group_from_tag(self) -> None:
        data = {
            **INSTANCE_DATA,
            "Tags": [
                {"Key": "Name", "Value": "worker"},
                {"Key": "aws:autoscaling:groupName", "Value": "ecs-asg"},
            ],
        }
        instance = Instance(data)
        asg = MagicMock()
        with patch.object(AutoscalingGroup.objects, "get", return_value=asg):
            assert instance.autoscaling_group is asg

    def test_autoscaling_group_none_without_tag(self) -> None:
        instance = Instance(INSTANCE_DATA)
        assert instance.autoscaling_group is None


class TestClassicLoadBalancerManager:
    LB_DATA = {
        "LoadBalancerName": "my-elb",
        "VPCId": "vpc-123",
        "Scheme": "internet-facing",
        "DNSName": "my-elb.example.com",
    }

    def test_get_many_and_list_filters(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        _paginate(client, [{"LoadBalancerDescriptions": [self.LB_DATA]}])
        lb = ClassicLoadBalancer.objects.get("my-elb")
        assert lb.pk == "my-elb"
        listed = ClassicLoadBalancer.objects.list(
            name="my-*", vpc_id="vpc-123", scheme="internet-facing"
        )
        assert len(listed) == 1

    def test_target_list(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        client.describe_instance_health.return_value = {
            "InstanceStates": [{"InstanceId": "i-abc123", "State": "InService"}],
        }
        instance = Instance(INSTANCE_DATA)
        with patch.object(Instance.objects, "get", return_value=instance):
            targets = ClassicLoadBalancerTarget.objects.list("my-elb")
        assert len(targets) == 1
        assert targets[0].instance.pk == "i-abc123"
