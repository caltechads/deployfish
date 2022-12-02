import fnmatch
from typing import List, Dict, Any, Optional, Sequence

import botocore

from deployfish.core.ssh import SSHMixin
from .abstract import Manager, Model
from .mixins import TagsManagerMixin, TagsMixin


# ----------------------------------------
# Managers
# ----------------------------------------

class VPCManager(Manager):

    service = 'ec2'

    def get(self, pk: str, **_) -> "VPC":
        instances = self.get_many([pk])
        if len(instances) > 1:
            raise VPC.MultipleObjectsReturned("Got more than one VPC when searching for pk={}".format(pk))
        return instances[0]

    def get_many(self, pks: List[str], **kwargs) -> Sequence["VPC"]:
        ids = []
        names = []
        kwargs = {}
        for pk in pks:
            if pk.startswith('vpc-'):
                ids.append(pk)
            else:
                names.append(pk)
        if names:
            kwargs['Filters'] = [{'Name': 'tag:Name', 'Values': names}]
        if ids:
            kwargs['VpcIds'] = ids
        paginator = self.client.get_paginator('describe_vpcs')
        response_iterator = paginator.paginate(**kwargs)
        vpcs = []
        try:
            for response in response_iterator:
                vpcs.extend(response['Vpcs'])
        except botocore.exceptions.ClientError as e:
            if 'InvalidVpcId.NotFound' in str(e):
                raise VPC.DoesNotExist(str(e))
            raise
        return [VPC(data) for data in vpcs]

    def list(self, name: str = None) -> Sequence["VPC"]:
        paginator = self.client.get_paginator('describe_vpcs')
        response_iterator = paginator.paginate()
        vpc_data = []
        for response in response_iterator:
            vpc_data.extend(response['Vpcs'])
        vpcs = []
        for vpc in vpc_data:
            if name:
                vpc_name = None
                for tag in vpc['Tags']:
                    if tag['Name'] == 'Name':
                        vpc_name = tag['Value']
                if not vpc_name:
                    continue
                if not fnmatch.fnmatch(vpc_name, name):
                    continue
            vpcs.append(VPC(vpc))
        return vpcs


class SubnetManager(Manager):

    service = 'ec2'

    def get(self, pk: str, **_) -> "Subnet":
        try:
            response = self.client.describe_subnets(SubnetIds=[pk])
        except botocore.exceptions.ClientError as e:
            if 'InvalidSubnetID.NotFound' in str(e):
                raise Subnet.DoesNotExist(str(e))
            raise
        return Subnet(response['Subnets'][0])

    def list(self, vpc_id: str = None) -> "List[Subnet]":
        paginator = self.client.get_paginator('describe_subnets')
        kwargs = {}
        if vpc_id:
            kwargs['Filters'] = [{'Name': 'vpc-id', 'Values': [vpc_id]}]
        response_iterator = paginator.paginate(**kwargs)
        subnets = []
        for response in response_iterator:
            subnets.extend(response['Subnets'])
        return [Subnet(subnet) for subnet in subnets]

    def get_tags(self, pk: str) -> List[Dict[str, str]]:
        response = self.client.describe_tags(
            Filters=[{
                'Name': 'resource-id',
                'Values': [pk]
            }]
        )
        return response['Tags']


class SecurityGroupManager(Manager):

    service: str = 'ec2'

    def get(self, pk: str, **_) -> "SecurityGroup":
        if pk.startswith('sg-'):
            kwargs = {'GroupIds': [pk]}
        else:
            kwargs = {'GroupNames': [pk]}
        try:
            response = self.client.describe_security_groups(**kwargs)
        except botocore.exceptions.ClientError as e:
            if 'InvalidGroup.NotFound' in str(e):
                raise SecurityGroup.DoesNotExist(str(e))
            raise
        return SecurityGroup(response['SecurityGroups'][0])

    def list(self, vpc_id: str = None) -> List["SecurityGroup"]:
        paginator = self.client.get_paginator('describe_security_groups')
        kwargs = {}
        if vpc_id:
            kwargs['Filters'] = [{'Name': 'vpc-id', 'Values': [vpc_id]}]
        response_iterator = paginator.paginate(**kwargs)
        security_groups = []
        for response in response_iterator:
            security_groups.extend(response['SecurityGroups'])
        return [SecurityGroup(security_group) for security_group in security_groups]


class AutoscalingGroupManager(Manager):

    service = 'autoscaling'

    def get(self, pk: str, **_) -> "AutoscalingGroup":
        try:
            response = self.client.describe_auto_scaling_groups(
                AutoScalingGroupNames=[pk]
            )
        except botocore.exceptions.ClientError:
            # FIXME: there are other ClientErrors.  This may say we have other
            # issues than the group doesn't exist
            raise AutoscalingGroup.DoesNotExist(
                'No Autoscaling Group named "{}" exists in AWS'.format(pk)
            )
        try:
            return AutoscalingGroup(response['AutoScalingGroups'][0])
        except IndexError:
            raise AutoscalingGroup.DoesNotExist(
                'No Autoscaling Group named "{}" exists in AWS'.format(pk)
            )

    def list(self) -> List["AutoscalingGroup"]:
        response = self.client.describe_auto_scaling_groups()
        return [AutoscalingGroup(group) for group in response['AutoScalingGroups']]

    def save(self, obj: Model, **kwargs) -> None:
        self.client.update_auto_scaling_group(**obj.render_for_update())


class InstanceManager(TagsManagerMixin, Manager):

    service = 'ec2'

    def get(self, pk: str, vpc_id: str = None, **_) -> "Instance":
        instances = self.get_many([pk], vpc_id=vpc_id)
        if len(instances) > 1:
            raise Instance.MultipleObjectsReturned(
                "Got more than one instance when searching for pk={}, vpc_id={}: {}".format(
                    pk,
                    vpc_id,
                    ", ".join([instance.pk for instance in instances])
                )
            )
        return instances[0]

    def get_many(self, pks: List[str], vpc_id: str = None, **_) -> Sequence["Instance"]:
        ec2_kwargs: Dict[str, Any] = {}
        names = []
        for pk in pks:
            if pk.startswith('Name:'):
                names.append(pk.split(':')[1])
            else:
                if 'InstanceIds' not in ec2_kwargs:
                    ec2_kwargs['InstanceIds'] = []
                ec2_kwargs['InstanceIds'].append(pk)
        if names:
            ec2_kwargs['Filters'] = []
            ec2_kwargs['Filters'].append({'Name': 'tag:Name', 'Values': names})
            if vpc_id:
                ec2_kwargs['Filters'].append({'Name': 'vpc-id', 'Values': [vpc_id]})
        paginator = self.client.get_paginator('describe_instances')
        response_iterator = paginator.paginate(**ec2_kwargs)
        instances = []
        try:
            for response in response_iterator:
                for reservation in response['Reservations']:
                    instances.extend(reservation['Instances'])
        except botocore.exceptions.ClientError as e:
            # FIXME: we may get ClientError for other reasons than the instance
            # doesn't exist
            raise Instance.DoesNotExist(str(e))
        return [Instance(instance) for instance in instances]

    def list(
        self,
        vpc_ids: List[str] = None,
        image_ids: List[str] = None,
        instance_types: List[str] = None,
        subnet_ids: List[str] = None,
        tags: List[str] = None,
    ) -> Sequence["Instance"]:
        ec2_kwargs: Dict[str, Any] = {}
        if any([vpc_ids, image_ids, instance_types, subnet_ids, tags]):
            ec2_kwargs['Filters'] = []
            if vpc_ids is not None:
                ec2_kwargs['Filters'].append({'Name': 'vpc-id', 'Values': [vpc_ids]})
            if image_ids is not None:
                ec2_kwargs['Filters'].append({'Name': 'image-id', 'Values': [image_ids]})
            if instance_types is not None:
                ec2_kwargs['Filters'].append({'Name': 'instance-type', 'Values': [instance_types]})
            if subnet_ids is not None:
                ec2_kwargs['Filters'].append({'Name': 'subnet-ids', 'Values': [subnet_ids]})
            if tags is not None:
                for tag in tags:
                    tag_name, tag_value = tag.split(':')
                    ec2_kwargs['Filters'].append({
                        'Name': f'tag:{tag_name}',
                        'Values': [tag_value]
                    })
        paginator = self.client.get_paginator('describe_instances')
        response_iterator = paginator.paginate()
        instances = []
        for response in response_iterator:
            for reservation in response['Reservations']:
                instances.extend(reservation['Instances'])
        return [Instance(instance) for instance in instances]


# ----------------------------------------
# Models
# ----------------------------------------

class AutoscalingGroup(Model):

    # FIXME: add SSHMixin, and enable sshing to this autoscaling group

    objects = AutoscalingGroupManager()

    @property
    def pk(self) -> str:
        return self.data['AutoScalingGroupName']

    @property
    def name(self) -> str:
        return self.data['AutoScalingGroupName']

    @property
    def arn(self) -> Optional[str]:
        return self.data.get('AutoScalingGroupARN', None)

    @property
    def autoscaling_group(self) -> "AutoscalingGroup":
        return self

    @property
    def instances(self) -> "List[Instance]":
        return self.get_cached(
            'instances',
            Instance.objects.get_many,
            [instance['InstanceId'] for instance in self.data['Instances']]
        )

    def scale(self, count: int, force: bool = True) -> None:
        if self.objects.exists(self.pk):
            min_size = self.data['MinSize']
            max_size = self.data['MaxSize']
            if count < 0:
                count = 0
            if force:
                if count < min_size:
                    min_size = count
                elif count > max_size:
                    max_size = count
            else:
                if count < min_size:
                    raise self.OperationFailed('AutoscalingGroup.scale(): count "{}" is less than MinSize.')
                if count > max_size:
                    raise self.OperationFailed('AutoscalingGroup.scale(): count "{}" is greater than than MaxSize.')
            self.data['MinSize'] = min_size
            self.data['MaxSize'] = max_size
            self.data['DesiredCapacity'] = count
            self.save()
        else:
            raise self.DoesNotExist('No Autoscaling Group named "{}" exists in AWS'.format(self.pk))

    def render_for_update(self) -> Dict[str, Any]:
        data = {}
        data['AutoScalingGroupName'] = self.data['AutoScalingGroupName']
        data['MinSize'] = self.data['MinSize']
        data['MaxSize'] = self.data['MaxSize']
        data['DesiredCapacity'] = self.data['DesiredCapacity']
        return data

    def render_for_diff(self) -> Dict[str, Any]:
        return self.render_for_update()


class Instance(TagsMixin, SSHMixin, Model):

    objects = InstanceManager()

    def __init__(self, data: Dict[str, Any]) -> None:
        super().__init__(data)
        self.import_tags(data['Tags'])

    # ---------------------
    # Model overrides
    # ---------------------

    @property
    def pk(self) -> str:
        return self.data['InstanceId']

    @property
    def name(self) -> str:
        return self.tags.get('Name', '')

    @property
    def arn(self) -> None:
        return None

    # ----------------------------
    # Instance-specific properties
    # ----------------------------

    @property
    def hostname(self) -> str:
        if self.data['PublicDnsName'] != '':
            return self.data['PublicDnsName']
        return self.data['PrivateDnsName']

    @property
    def private_hostname(self) -> str:
        return self.data['PrivateDnsName']

    @property
    def ip_address(self) -> str:
        return self.data['PrivateIpAddress']

    # ------------------------------
    # Related objects
    # ------------------------------

    @property
    def autoscaling_group(self) -> Optional[AutoscalingGroup]:
        if 'autoscaling_group' not in self.cache:
            try:
                autoscalinggroup_name = self.tags['aws:autoscaling:groupName']
            except KeyError:
                self.cache['autoscaling_group'] = None
            else:
                self.cache['autoscaling_group'] = AutoscalingGroup.objects.get(autoscalinggroup_name)
        return self.cache['autoscaling_group']

    @property
    def subnet(self) -> "Subnet":
        if 'subnet' not in self.cache:
            subnet_id = self.data['SubnetId']
            self.cache['subnet'] = Subnet.objects.get(pk=subnet_id)
        return self.cache['subnet']

    @property
    def vpc(self) -> "VPC":
        return self.subnet.vpc

    # ----------------------------
    # Networking
    # ----------------------------

    @property
    def ssh_target(self) -> "Instance":
        return self

    @property
    def ssh_targets(self) -> Sequence["Instance"]:
        return [self]

    @property
    def bastion(self) -> "Optional[Instance]":
        return self.vpc.bastion

    @property
    def provisioner(self) -> "Optional[Instance]":
        return self.vpc.provisioner


class VPC(TagsMixin, Model):

    objects = VPCManager()

    @property
    def pk(self) -> str:
        return self.data['VpcId']

    @property
    def name(self) -> str:
        return self.tags['Name']

    @property
    def arn(self) -> None:
        return None

    @property
    def cidr_block(self) -> str:
        return self.data['CidrBlock']

    @property
    def bastion(self) -> Optional[Instance]:
        try:
            return self.get_cached(
                'bastion',
                Instance.objects.get,
                ['Name:bastion*'],
                {'vpc_id': self.pk}
            )
        except self.DoesNotExist:
            self.cache['bastion'] = None
            return None

    @property
    def provisioner(self) -> Optional[Instance]:
        try:
            return self.get_cached(
                'provisioner',
                Instance.objects.get,
                ['Name:provisioner*'],
                {'vpc_id': self.pk}
            )
        except self.DoesNotExist:
            self.cache['provisioner'] = None
            return None


class Subnet(TagsMixin, Model):

    objects = SubnetManager()

    # ---------------------
    # Model overrides
    # ---------------------

    @property
    def pk(self) -> str:
        return self.data['SubnetId']

    @property
    def name(self) -> str:
        return self.tags['Name']

    @property
    def arn(self) -> None:
        return None

    # ----------------------------
    # Subnet-specific properties
    # ----------------------------

    @property
    def cidr_block(self) -> str:
        return self.data['CidrBlock']

    @property
    def available_ips(self) -> int:
        return self.data['AvailableIpAddressCount']

    @property
    def tags(self) -> Dict[str, str]:
        if 'tags' not in self.cache:
            self.cache['tags'] = {}
            for tag in self.objects.get_tags(self.pk):
                self.cache['tags'][tag['Key']] = tag['Value']
        return self.cache['tags']

    # ------------------------------
    # Related objects
    # ------------------------------

    @property
    def vpc(self) -> VPC:
        if 'vpc' not in self.cache:
            self.cache['vpc'] = VPC.objects.get(self.data['VpcId'])
        return self.cache['vpc']


class SecurityGroup(TagsMixin, Model):

    objects = SecurityGroupManager()

    @property
    def pk(self) -> str:
        return self.data['GroupId']

    @property
    def name(self) -> str:
        return self.data['GroupName']

    @property
    def description(self) -> str:
        return self.data['Description']

    @property
    def arn(self) -> None:
        return None

    @property
    def vpc(self) -> VPC:
        if 'vpc' not in self.cache:
            self.cache['vpc'] = VPC.objects.get(self.data['VpcId'])
        return self.cache['vpc']

    @property
    def tags(self) -> Dict[str, str]:
        if 'tags' not in self.cache:
            self.cache['tags'] = {}
            for tag in self.data['Tags']:
                self.cache['tags'][tag['Key']] = tag['Value']
        return self.cache['tags']
