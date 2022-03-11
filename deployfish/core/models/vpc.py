import fnmatch

import botocore

from .abstract import Manager, Model
from .mixins import TagsMixin


# ----------------------------------------
# Managers
# ----------------------------------------


class VPCManager(Manager):

    service = 'ec2'

    def get(self, pk):
        # hint: (str["{vpc_id}", "{vpc_name}"])
        instances = self.get_many([pk])
        if len(instances) > 1:
            raise VPC.MultipleObjectsReturned(
                "Got more than one VPC when searching for pk={}".format(
                    pk,
                    ", ".join([instance.pk for instance in instances])
                )
            )
        return instances[0]

    def get_many(self, pks):
        # hint: (list[str["{vpc_id}", "{vpc_name}"]])
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
        return [VPC(data) for data in vpcs]

    def list(self, name=None):
        # hint: (str["{vpc_name:glob}"])
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

    def save(self, obj):
        raise VPC.ReadOnly('Cannot modify VPCs with deployfish')

    def delete(self, pk):
        raise VPC.ReadOnly('Cannot modify VPCs with deployfish')


class SubnetManager(Manager):

    service = 'ec2'

    def get(self, pk):
        # hint: (str["{subnet_id}"])
        try:
            response = self.client.describe_subnets(SubnetIds=[pk])
        except botocore.exceptions.ClientError as e:
            if 'InvalidSubnetId.NotFound' in str(e):
                raise Subnet.DoesNotExist(str(e))
        return Subnet(response['Subnets'][0])

    def list(self, vpc_id=None):
        # hint: (str["{vpc_id}"])
        paginator = self.client.get_paginator('describe_subnets')
        kwargs = {}
        if vpc_id:
            kwargs['Filters'] = [{'Name': 'vpc-id', 'Values': [vpc_id]}]
        response_iterator = paginator.paginate(**kwargs)
        subnets = []
        for response in response_iterator:
            subnets.extend(response['Subnets'])
        return [Subnet(subnet) for subnet in subnets]

    def get_tags(self, pks):
        # hint: (list[str["{subnet_id}"]])
        response = self.client.describe_tags(
            Filters=[{
                'Name': 'resource-id',
                'Values': [pks]
            }]
        )
        return response['Tags']

    def save(self, obj):
        raise Subnet.ReadOnly('Cannot modify Subnets with deployfish')

    def delete(self, pk):
        raise Subnet.ReadOnly('wannot modify Subnets with deployfish')


class SecurityGroupManager(Manager):

    service = 'ec2'

    def get(self, pk):
        # hint: (str["{security_group_id}"])
        if pk.startswith('sg-'):
            kwargs = {'GroupIds': [pk]}
        else:
            kwargs = {'GroupNames': [pk]}
        try:
            response = self.client.describe_security_groups(**kwargs)
        except botocore.exceptions.ClientError as e:
            if 'InvalidGroup.NotFound' in str(e):
                raise SecurityGroup.DoesNotExist(str(e))
        return SecurityGroup(response['SecurityGroups'][0])

    def list(self, vpc_id=None):
        # hint: (str["{vpc_id}"])
        paginator = self.client.get_paginator('describe_security_groups')
        kwargs = {}
        if vpc_id:
            kwargs['Filters'] = [{'Name': 'vpc-id', 'Values': [vpc_id]}]
        response_iterator = paginator.paginate(**kwargs)
        security_groups = []
        for response in response_iterator:
            security_groups.extend(response['SecurityGroups'])
        return [SecurityGroup(security_group) for security_group in security_groups]

    def save(self, obj):
        raise Subnet.ReadOnly('Cannot modify SecurityGroups with deployfish')

    def delete(self, pk):
        raise Subnet.ReadOnly('Cannot modify SecurityGroups with deployfish')


# ----------------------------------------
# Models
# ----------------------------------------

class VPC(TagsMixin, Model):

    objects = VPCManager()

    @property
    def pk(self):
        return self.data['VpcId']

    @property
    def name(self):
        return self.tags['Name']

    @property
    def arn(self):
        return None

    @property
    def cidr_block(self):
        return self.data['CidrBlock']


class Subnet(TagsMixin, Model):

    objects = SubnetManager()

    @property
    def pk(self):
        return self.data['SubnetId']

    @property
    def name(self):
        return self.tags['Name']

    @property
    def arn(self):
        return None

    @property
    def cidr_block(self):
        return self.data['CidrBlock']

    @property
    def available_ips(self):
        return self.data['AvailableIpAddressCount']

    @property
    def vpc(self):
        if 'vpc' not in self.cache:
            self.cache['vpc'] = VPC.objects.get(self.data['VpcId'])
        return self.cache['vpc']

    @property
    def tags(self):
        if 'tags' not in self.cache:
            self.cache['tags'] = {}
            for tag in self.objects.get_tags(self.pk):
                self.cache['tags'][tag['Key']] = tag['Value']
        return self.cache['tags']


class SecurityGroup(TagsMixin, Model):

    objects = SecurityGroupManager()

    @property
    def pk(self):
        return self.data['GroupId']

    @property
    def name(self):
        return self.data['GroupName']

    @property
    def description(self):
        return self.data['Description']

    @property
    def arn(self):
        return None

    @property
    def vpc(self):
        if 'vpc' not in self.cache:
            self.cache['vpc'] = VPC.objects.get(self.data['VpcId'])
        return self.cache['vpc']

    @property
    def tags(self):
        if 'tags' not in self.cache:
            self.cache['tags'] = {}
            for tag in self.data['Tags']:
                self.cache['tags'][tag['Key']] = tag['Value']
        return self.cache['tags']
