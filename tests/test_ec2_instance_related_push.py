"""EC2 Instance related-object property coverage."""

from unittest.mock import MagicMock, patch

from deployfish.core.models.ec2 import VPC, AutoscalingGroup, Instance, Subnet

INSTANCE_DATA = {
    "InstanceId": "i-abc123",
    "PrivateIpAddress": "10.0.0.5",
    "PublicDnsName": "",
    "PrivateDnsName": "ip-10-0-0-5.internal",
    "VpcId": "vpc-123",
    "SubnetId": "subnet-abc",
    "Tags": [{"Key": "Name", "Value": "worker"}],
}


class TestInstanceRelatedObjects:
    def test_subnet_and_vpc_properties(self) -> None:
        instance = Instance(INSTANCE_DATA)
        subnet = MagicMock(spec=Subnet)
        subnet.vpc = MagicMock(spec=VPC)
        with patch.object(Subnet.objects, "get", return_value=subnet):
            assert instance.subnet is subnet
            assert instance.vpc is subnet.vpc

    def test_bastion_and_provisioner_delegate_to_vpc(self) -> None:
        instance = Instance(INSTANCE_DATA)
        bastion = MagicMock()
        provisioner = MagicMock()
        vpc = MagicMock()
        vpc.bastion = bastion
        vpc.provisioner = provisioner
        with patch.object(Instance, "vpc", vpc):
            assert instance.bastion is bastion
            assert instance.provisioner is provisioner

    def test_autoscaling_group_cached(self) -> None:
        data = {
            **INSTANCE_DATA,
            "Tags": [
                {"Key": "Name", "Value": "worker"},
                {"Key": "aws:autoscaling:groupName", "Value": "ecs-asg"},
            ],
        }
        instance = Instance(data)
        asg = MagicMock(spec=AutoscalingGroup)
        with patch.object(
            AutoscalingGroup.objects, "get", return_value=asg
        ) as get_mock:
            assert instance.autoscaling_group is asg
            assert instance.autoscaling_group is asg
        get_mock.assert_called_once_with("ecs-asg")
