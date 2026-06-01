from unittest.mock import MagicMock, patch

import pytest
from deployfish.core.models.ec2 import VPC, Instance, SecurityGroup, Subnet


def _paginate(client: MagicMock, pages: list[dict]) -> None:
    paginator = MagicMock()
    client.get_paginator.return_value = paginator
    paginator.paginate.return_value = pages


VPC_DATA = {
    "VpcId": "vpc-123",
    "CidrBlock": "10.0.0.0/16",
    "Tags": [{"Key": "Name", "Value": "main-vpc"}],
}

INSTANCE_DATA = {
    "InstanceId": "i-abc123",
    "PrivateIpAddress": "10.0.1.5",
    "PublicDnsName": "",
    "PrivateDnsName": "ip-10-0-1-5.internal",
    "VpcId": "vpc-123",
    "SubnetId": "subnet-abc",
    "State": {"Name": "running"},
    "Tags": [{"Key": "Name", "Value": "worker-1"}],
}


class TestVPCManager:
    def test_get_vpc(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        _paginate(client, [{"Vpcs": [VPC_DATA]}])
        vpc = VPC.objects.get("vpc-123")
        assert vpc.pk == "vpc-123"

    def test_list_vpcs(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        _paginate(client, [{"Vpcs": [VPC_DATA]}])
        vpcs = VPC.objects.list()
        assert len(vpcs) == 1


class TestInstanceManager:
    def test_get_instance(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        _paginate(client, [{"Reservations": [{"Instances": [INSTANCE_DATA]}]}])
        instance = Instance.objects.get("i-abc123")
        assert instance.pk == "i-abc123"

    def test_get_raises_when_missing(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        _paginate(client, [{"Reservations": []}])
        with pytest.raises(IndexError):
            Instance.objects.get("i-missing")


class TestSubnetManager:
    def test_get_subnet(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        client.describe_subnets.return_value = {
            "Subnets": [
                {
                    "SubnetId": "subnet-abc",
                    "VpcId": "vpc-123",
                    "CidrBlock": "10.0.1.0/24",
                    "AvailableIpAddressCount": 200,
                }
            ],
        }
        with patch.object(
            Subnet.objects,
            "get_tags",
            return_value=[{"Key": "Name", "Value": "private-a"}],
        ):
            subnet = Subnet.objects.get("subnet-abc")
        assert subnet.pk == "subnet-abc"


class TestSecurityGroupManager:
    def test_get_security_group(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        client.describe_security_groups.return_value = {
            "SecurityGroups": [
                {
                    "GroupId": "sg-abc",
                    "GroupName": "app-sg",
                    "VpcId": "vpc-123",
                    "Description": "app",
                }
            ],
        }
        sg = SecurityGroup.objects.get("sg-abc")
        assert sg.name == "app-sg"
