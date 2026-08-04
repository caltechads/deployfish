import builtins
import fnmatch
from collections.abc import Sequence
from typing import Any

import botocore

from deployfish.core.ssh import SSHMixin

from .abstract import Manager, Model
from .mixins import TagsManagerMixin, TagsMixin

# ----------------------------------------
# Managers
# ----------------------------------------


class VPCManager(Manager):
    """
    Model vpcmanager behavior.
    """
    #: Service.
    service = "ec2"

    def get(self, pk: str, **_) -> "VPC":
        """
        Get.

        Args:
            pk: pk.

        Keyword Args:
            _: .

        Returns:
            Operation result.
        """
        instances = self.get_many([pk])
        if len(instances) > 1:
            msg = f"Got more than one VPC when searching for pk={pk}"
            raise VPC.MultipleObjectsReturned(msg)
        return instances[0]

    def get_many(self, pks: list[str], **kwargs) -> Sequence["VPC"]:
        """
        Get many.

        Args:
            pks: pks.

        Keyword Args:
            kwargs: kwargs.

        Returns:
            Operation result.
        """
        ids = []
        names = []
        kwargs = {}
        for pk in pks:
            if pk.startswith("vpc-"):
                ids.append(pk)
            else:
                names.append(pk)
        if names:
            kwargs["Filters"] = [{"Name": "tag:Name", "Values": names}]
        if ids:
            kwargs["VpcIds"] = ids
        paginator = self.client.get_paginator("describe_vpcs")
        response_iterator = paginator.paginate(**kwargs)
        vpcs = []
        try:
            for response in response_iterator:
                vpcs.extend(response["Vpcs"])
        except botocore.exceptions.ClientError as e:
            if "InvalidVpcId.NotFound" in str(e):
                raise VPC.DoesNotExist(str(e))
            raise
        return [VPC(data) for data in vpcs]

    def list(self, name: str | None = None) -> Sequence["VPC"]:
        """
        List.

        Args:
            name: name.

        Returns:
            Operation result.
        """
        paginator = self.client.get_paginator("describe_vpcs")
        response_iterator = paginator.paginate()
        vpc_data = []
        for response in response_iterator:
            vpc_data.extend(response["Vpcs"])
        vpcs = []
        for vpc in vpc_data:
            if name:
                vpc_name = None
                for tag in vpc["Tags"]:
                    if tag["Name"] == "Name":
                        vpc_name = tag["Value"]
                if not vpc_name:
                    continue
                if not fnmatch.fnmatch(vpc_name, name):
                    continue
            vpcs.append(VPC(vpc))
        return vpcs


class SubnetManager(Manager):
    """
    Model subnet manager behavior.
    """
    #: Service.
    service = "ec2"

    def get(self, pk: str, **_) -> "Subnet":
        """
        Get.

        Args:
            pk: pk.

        Keyword Args:
            _: .

        Returns:
            Operation result.
        """
        try:
            response = self.client.describe_subnets(SubnetIds=[pk])
        except botocore.exceptions.ClientError as e:
            if "InvalidSubnetID.NotFound" in str(e):
                raise Subnet.DoesNotExist(str(e))
            raise
        return Subnet(response["Subnets"][0])

    def list(self, vpc_id: str | None = None) -> "builtins.list[Subnet]":
        """
        List.

        Args:
            vpc_id: vpc id.

        Returns:
            Operation result.
        """
        paginator = self.client.get_paginator("describe_subnets")
        kwargs = {}
        if vpc_id:
            kwargs["Filters"] = [{"Name": "vpc-id", "Values": [vpc_id]}]
        response_iterator = paginator.paginate(**kwargs)
        subnets = []
        for response in response_iterator:
            subnets.extend(response["Subnets"])
        return [Subnet(subnet) for subnet in subnets]

    def get_tags(self, pk: str) -> builtins.list[dict[str, str]]:
        """
        Get tags.

        Args:
            pk: pk.

        Returns:
            Operation result.
        """
        response = self.client.describe_tags(
            Filters=[{"Name": "resource-id", "Values": [pk]}]
        )
        return response["Tags"]


class SecurityGroupManager(Manager):
    """
    Model security group manager behavior.
    """
    #: Service.
    service: str = "ec2"

    def get(self, pk: str, **_) -> "SecurityGroup":
        """
        Get.

        Args:
            pk: pk.

        Keyword Args:
            _: .

        Returns:
            Operation result.
        """
        kwargs = {"GroupIds": [pk]} if pk.startswith("sg-") else {"GroupNames": [pk]}
        try:
            response = self.client.describe_security_groups(**kwargs)
        except botocore.exceptions.ClientError as e:
            if "InvalidGroup.NotFound" in str(e):
                raise SecurityGroup.DoesNotExist(str(e))
            raise
        return SecurityGroup(response["SecurityGroups"][0])

    def list(self, vpc_id: str | None = None) -> list["SecurityGroup"]:
        """
        List.

        Args:
            vpc_id: vpc id.

        Returns:
            Operation result.
        """
        paginator = self.client.get_paginator("describe_security_groups")
        kwargs = {}
        if vpc_id:
            kwargs["Filters"] = [{"Name": "vpc-id", "Values": [vpc_id]}]
        response_iterator = paginator.paginate(**kwargs)
        security_groups = []
        for response in response_iterator:
            security_groups.extend(response["SecurityGroups"])
        return [SecurityGroup(security_group) for security_group in security_groups]


class AutoscalingGroupManager(Manager):
    """
    Model autoscaling group manager behavior.
    """
    #: Service.
    service = "autoscaling"

    def get(self, pk: str, **_) -> "AutoscalingGroup":
        """
        Get.

        Args:
            pk: pk.

        Keyword Args:
            _: .

        Returns:
            Operation result.
        """
        try:
            response = self.client.describe_auto_scaling_groups(
                AutoScalingGroupNames=[pk]
            )
        except botocore.exceptions.ClientError:
            # FIXME: there are other ClientErrors.  This may say we have other
            # issues than the group doesn't exist
            msg = f'No Autoscaling Group named "{pk}" exists in AWS'
            raise AutoscalingGroup.DoesNotExist(msg)
        try:
            return AutoscalingGroup(response["AutoScalingGroups"][0])
        except IndexError:
            msg = f'No Autoscaling Group named "{pk}" exists in AWS'
            raise AutoscalingGroup.DoesNotExist(msg)

    def list(self) -> list["AutoscalingGroup"]:
        """
        List.

        Returns:
            Operation result.
        """
        response = self.client.describe_auto_scaling_groups()
        return [AutoscalingGroup(group) for group in response["AutoScalingGroups"]]

    def save(self, obj: Model, **kwargs) -> None:
        """
        Save.

        Args:
            obj: obj.

        Keyword Args:
            kwargs: kwargs.
        """
        self.client.update_auto_scaling_group(**obj.render_for_update())


class InstanceManager(TagsManagerMixin, Manager):
    """
    Model instance manager behavior.
    """
    #: Service.
    service = "ec2"

    def get(self, pk: str, vpc_id: str | None = None, **_) -> "Instance":
        """
        Get.

        Args:
            pk: pk.
            vpc_id: vpc id.

        Keyword Args:
            _: .

        Returns:
            Operation result.
        """
        instances = self.get_many([pk], vpc_id=vpc_id)
        if len(instances) > 1:
            msg = "Got more than one instance when searching for pk={}, vpc_id={}: {}".format(
                pk, vpc_id, ", ".join([instance.pk for instance in instances])
            )
            raise Instance.MultipleObjectsReturned(msg)
        return instances[0]

    def get_many(
        self, pks: list[str], vpc_id: str | None = None, **_
    ) -> Sequence["Instance"]:
        """
        Get many.

        Args:
            pks: pks.
            vpc_id: vpc id.

        Keyword Args:
            _: .

        Returns:
            Operation result.
        """
        ec2_kwargs: dict[str, Any] = {}
        names = []
        for pk in pks:
            if pk.startswith("Name:"):
                names.append(pk.split(":")[1])
            else:
                if "InstanceIds" not in ec2_kwargs:
                    ec2_kwargs["InstanceIds"] = []
                ec2_kwargs["InstanceIds"].append(pk)
        if names:
            ec2_kwargs["Filters"] = []
            ec2_kwargs["Filters"].append({"Name": "tag:Name", "Values": names})
            if vpc_id:
                ec2_kwargs["Filters"].append({"Name": "vpc-id", "Values": [vpc_id]})
        paginator = self.client.get_paginator("describe_instances")
        response_iterator = paginator.paginate(**ec2_kwargs)
        instances = []
        try:
            for response in response_iterator:
                for reservation in response["Reservations"]:
                    instances.extend(reservation["Instances"])
        except botocore.exceptions.ClientError as e:
            # FIXME: we may get ClientError for other reasons than the instance
            # doesn't exist
            raise Instance.DoesNotExist(str(e))
        return [Instance(instance) for instance in instances]

    def list(
        self,
        vpc_ids: list[str] | None = None,
        image_ids: list[str] | None = None,
        instance_types: list[str] | None = None,
        subnet_ids: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> Sequence["Instance"]:
        """
        List.

        Args:
            vpc_ids: vpc ids.
            image_ids: image ids.
            instance_types: instance types.
            subnet_ids: subnet ids.
            tags: tags.

        Returns:
            Operation result.
        """
        ec2_kwargs: dict[str, Any] = {}
        if any([vpc_ids, image_ids, instance_types, subnet_ids, tags]):
            ec2_kwargs["Filters"] = []
            if vpc_ids is not None:
                ec2_kwargs["Filters"].append({"Name": "vpc-id", "Values": [vpc_ids]})
            if image_ids is not None:
                ec2_kwargs["Filters"].append(
                    {"Name": "image-id", "Values": [image_ids]}
                )
            if instance_types is not None:
                ec2_kwargs["Filters"].append(
                    {"Name": "instance-type", "Values": [instance_types]}
                )
            if subnet_ids is not None:
                ec2_kwargs["Filters"].append(
                    {"Name": "subnet-ids", "Values": [subnet_ids]}
                )
            if tags is not None:
                for tag in tags:
                    tag_name, tag_value = tag.split(":")
                    ec2_kwargs["Filters"].append(
                        {"Name": f"tag:{tag_name}", "Values": [tag_value]}
                    )
        paginator = self.client.get_paginator("describe_instances")
        response_iterator = paginator.paginate()
        instances = []
        for response in response_iterator:
            for reservation in response["Reservations"]:
                instances.extend(reservation["Instances"])
        return [Instance(instance) for instance in instances]


# ----------------------------------------
# Models
# ----------------------------------------


class AutoscalingGroup(Model):
    """
    Model autoscaling group behavior.
    """
    # FIXME: add SSHMixin, and enable sshing to this autoscaling group

    #: Objects.
    objects = AutoscalingGroupManager()

    @property
    def pk(self) -> str:
        """
        Pk.

        Returns:
            Operation result.
        """
        return self.data["AutoScalingGroupName"]

    @property
    def name(self) -> str:
        """
        Name.

        Returns:
            Operation result.
        """
        return self.data["AutoScalingGroupName"]

    @property
    def arn(self) -> str | None:
        """
        Arn.

        Returns:
            Operation result.
        """
        return self.data.get("AutoScalingGroupARN", None)

    @property
    def autoscaling_group(self) -> "AutoscalingGroup":
        """
        Autoscaling group.

        Returns:
            Operation result.
        """
        return self

    @property
    def instances(self) -> "list[Instance]":
        """
        Instances.

        Returns:
            Operation result.
        """
        return self.get_cached(
            "instances",
            Instance.objects.get_many,
            [instance["InstanceId"] for instance in self.data["Instances"]],
        )

    def scale(self, count: int, force: bool = True) -> None:
        """
        Scale.

        Args:
            count: count.
            force: force.
        """
        if self.objects.exists(self.pk):
            min_size = self.data["MinSize"]
            max_size = self.data["MaxSize"]
            count = max(count, 0)
            if force:
                if count < min_size:
                    min_size = count
                elif count > max_size:
                    max_size = count
            else:
                if count < min_size:
                    msg = 'AutoscalingGroup.scale(): count "{}" is less than MinSize.'
                    raise self.OperationFailed(msg)
                if count > max_size:
                    msg = 'AutoscalingGroup.scale(): count "{}" is greater than than MaxSize.'
                    raise self.OperationFailed(msg)
            self.data["MinSize"] = min_size
            self.data["MaxSize"] = max_size
            self.data["DesiredCapacity"] = count
            self.save()
        else:
            msg = f'No Autoscaling Group named "{self.pk}" exists in AWS'
            raise self.DoesNotExist(msg)

    def render_for_update(self) -> dict[str, Any]:
        """
        Render for update.

        Returns:
            Operation result.
        """
        data = {}
        data["AutoScalingGroupName"] = self.data["AutoScalingGroupName"]
        data["MinSize"] = self.data["MinSize"]
        data["MaxSize"] = self.data["MaxSize"]
        data["DesiredCapacity"] = self.data["DesiredCapacity"]
        return data

    def render_for_diff(self) -> dict[str, Any]:
        """
        Render for diff.

        Returns:
            Operation result.
        """
        return self.render_for_update()


class Instance(TagsMixin, SSHMixin, Model):
    """
    Model instance behavior.

    Args:
        data: data.
    """
    #: Objects.
    objects = InstanceManager()

    def __init__(self, data: dict[str, Any]) -> None:
        """
        Initialize Instance.

        Args:
            data: data.
        """
        super().__init__(data)
        self.import_tags(data["Tags"])

    # ---------------------
    # Model overrides
    # ---------------------

    @property
    def pk(self) -> str:
        """
        Pk.

        Returns:
            Operation result.
        """
        return self.data["InstanceId"]

    @property
    def name(self) -> str:
        """
        Name.

        Returns:
            Operation result.
        """
        return self.tags.get("Name", "")

    @property
    def arn(self) -> None:
        """
        Arn.
        """
        return None

    # ----------------------------
    # Instance-specific properties
    # ----------------------------

    @property
    def hostname(self) -> str:
        """
        Hostname.

        Returns:
            Operation result.
        """
        if self.data["PublicDnsName"] != "":
            return self.data["PublicDnsName"]
        return self.data["PrivateDnsName"]

    @property
    def private_hostname(self) -> str:
        """
        Private hostname.

        Returns:
            Operation result.
        """
        return self.data["PrivateDnsName"]

    @property
    def ip_address(self) -> str:
        """
        Ip address.

        Returns:
            Operation result.
        """
        return self.data["PrivateIpAddress"]

    # ------------------------------
    # Related objects
    # ------------------------------

    @property
    def autoscaling_group(self) -> AutoscalingGroup | None:
        """
        Autoscaling group.

        Returns:
            Operation result.
        """
        if "autoscaling_group" not in self.cache:
            try:
                autoscalinggroup_name = self.tags["aws:autoscaling:groupName"]
            except KeyError:
                self.cache["autoscaling_group"] = None
            else:
                self.cache["autoscaling_group"] = AutoscalingGroup.objects.get(
                    autoscalinggroup_name
                )
        return self.cache["autoscaling_group"]

    @property
    def subnet(self) -> "Subnet":
        """
        Subnet.

        Returns:
            Operation result.
        """
        if "subnet" not in self.cache:
            subnet_id = self.data["SubnetId"]
            self.cache["subnet"] = Subnet.objects.get(pk=subnet_id)
        return self.cache["subnet"]

    @property
    def vpc(self) -> "VPC":
        """
        Vpc.

        Returns:
            Operation result.
        """
        return self.subnet.vpc

    # ----------------------------
    # Networking
    # ----------------------------

    @property
    def ssh_target(self) -> "Instance":
        """
        Ssh target.

        Returns:
            Operation result.
        """
        return self

    @property
    def ssh_targets(self) -> Sequence["Instance"]:
        """
        Ssh targets.

        Returns:
            Operation result.
        """
        return [self]

    @property
    def bastion(self) -> "Instance | None":
        """
        Bastion.

        Returns:
            Operation result.
        """
        return self.vpc.bastion

    @property
    def provisioner(self) -> "Instance | None":
        """
        Provisioner.

        Returns:
            Operation result.
        """
        return self.vpc.provisioner


class VPC(TagsMixin, Model):
    """
    Model vpc behavior.
    """
    #: Objects.
    objects = VPCManager()

    @property
    def pk(self) -> str:
        """
        Pk.

        Returns:
            Operation result.
        """
        return self.data["VpcId"]

    @property
    def name(self) -> str:
        """
        Name.

        Returns:
            Operation result.
        """
        return self.tags["Name"]

    @property
    def arn(self) -> None:
        """
        Arn.
        """
        return None

    @property
    def cidr_block(self) -> str:
        """
        Cidr block.

        Returns:
            Operation result.
        """
        return self.data["CidrBlock"]

    @property
    def bastion(self) -> Instance | None:
        """
        Bastion.

        Returns:
            Operation result.
        """
        try:
            return self.get_cached(
                "bastion", Instance.objects.get, ["Name:bastion*"], {"vpc_id": self.pk}
            )
        except self.DoesNotExist:
            self.cache["bastion"] = None
            return None

    @property
    def provisioner(self) -> Instance | None:
        """
        Provisioner.

        Returns:
            Operation result.
        """
        try:
            return self.get_cached(
                "provisioner",
                Instance.objects.get,
                ["Name:provisioner*"],
                {"vpc_id": self.pk},
            )
        except self.DoesNotExist:
            self.cache["provisioner"] = None
            return None


class Subnet(TagsMixin, Model):
    """
    Model subnet behavior.
    """
    #: Objects.
    objects = SubnetManager()

    # ---------------------
    # Model overrides
    # ---------------------

    @property
    def pk(self) -> str:
        """
        Pk.

        Returns:
            Operation result.
        """
        return self.data["SubnetId"]

    @property
    def name(self) -> str:
        """
        Name.

        Returns:
            Operation result.
        """
        return self.tags["Name"]

    @property
    def arn(self) -> None:
        """
        Arn.
        """
        return None

    # ----------------------------
    # Subnet-specific properties
    # ----------------------------

    @property
    def cidr_block(self) -> str:
        """
        Cidr block.

        Returns:
            Operation result.
        """
        return self.data["CidrBlock"]

    @property
    def available_ips(self) -> int:
        """
        Available ips.

        Returns:
            Operation result.
        """
        return self.data["AvailableIpAddressCount"]

    @property
    def tags(self) -> dict[str, str]:
        """
        Tags.

        Returns:
            Operation result.
        """
        if "tags" not in self.cache:
            self.cache["tags"] = {}
            for tag in self.objects.get_tags(self.pk):
                self.cache["tags"][tag["Key"]] = tag["Value"]
        return self.cache["tags"]

    # ------------------------------
    # Related objects
    # ------------------------------

    @property
    def vpc(self) -> VPC:
        """
        Vpc.

        Returns:
            Operation result.
        """
        if "vpc" not in self.cache:
            self.cache["vpc"] = VPC.objects.get(self.data["VpcId"])
        return self.cache["vpc"]


class SecurityGroup(TagsMixin, Model):
    """
    Model security group behavior.
    """
    #: Objects.
    objects = SecurityGroupManager()

    @property
    def pk(self) -> str:
        """
        Pk.

        Returns:
            Operation result.
        """
        return self.data["GroupId"]

    @property
    def name(self) -> str:
        """
        Name.

        Returns:
            Operation result.
        """
        return self.data["GroupName"]

    @property
    def description(self) -> str:
        """
        Description.

        Returns:
            Operation result.
        """
        return self.data["Description"]

    @property
    def arn(self) -> None:
        """
        Arn.
        """
        return None

    @property
    def vpc(self) -> VPC:
        """
        Vpc.

        Returns:
            Operation result.
        """
        if "vpc" not in self.cache:
            self.cache["vpc"] = VPC.objects.get(self.data["VpcId"])
        return self.cache["vpc"]

    @property
    def tags(self) -> dict[str, str]:
        """
        Tags.

        Returns:
            Operation result.
        """
        if "tags" not in self.cache:
            self.cache["tags"] = {}
            for tag in self.data["Tags"]:
                self.cache["tags"][tag["Key"]] = tag["Value"]
        return self.cache["tags"]
