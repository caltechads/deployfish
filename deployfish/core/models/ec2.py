import botocore

from deployfish.core.ssh import SSHMixin
from .abstract import Manager, Model
from .mixins import TagsManagerMixin, TagsMixin

# ----------------------------------------
# Managers
# ----------------------------------------


class AutoscalingGroupManager(Manager):

    service = 'autoscaling'

    def get(self, pk, **kwargs):
        try:
            response = self.client.describe_auto_scaling_groups(
                AutoScalingGroupNames=[pk]
            )
        except botocore.exceptions.ClientError:
            raise AutoscalingGroup.DoesNotExist(
                'No Autoscaling Group named "{}" exists in AWS'.format(pk)
            )
        return AutoscalingGroup(response['AutoScalingGroups'][0])

    def list(self):
        response = self.client.describe_auto_scaling_groups()
        return [AutoscalingGroup(group) for group in response['AutoScalingGroups']]

    def save(self, obj):
        self.client.update_auto_scaling_group(**obj.render_for_update())

    def delete(self, pk):
        raise AutoscalingGroup.ReadOnly('Cannot delete Autoscaling Groups with deployfish')


class InstanceManager(TagsManagerMixin, Manager):

    service = 'ec2'

    def get(self, pk, vpc_id=None):
        # hint: (str["{Instance.id}", "Name:{instance name tag}"], str)
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

    def get_many(self, pks, vpc_id=None):
        # hint: (list[str["{Instance.id}", "Name:{instance name tag}"]], str)
        ec2_kwargs = {}
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
            raise Instance.DoesNotExist(str(e))
        return [Instance(instance) for instance in instances]

    def list(self, vpc_ids=None, image_ids=None, instance_types=None, subnet_ids=None, tags=None):
        # hint: (list[str], list[str], list[str], list[str], list[str["{tagName}:{tagValue}"])
        ec2_kwargs = {}
        if any(vpc_ids, image_ids, instance_types, subnet_ids, tags):
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
                    ec2_kwargs['Filters'].append({'Name': 'tag:{}'.format(tag_name), 'Values': [tag_value]})
        paginator = self.client.get_paginator('describe_instances')
        response_iterator = paginator.paginate()
        instances = []
        for response in response_iterator:
            for reservation in response['Reservations']:
                instances.extend(reservation['Instances'])
        return [Instance(instance) for instance in instances]

    def save(self, obj):
        raise InstanceManager.ReadOnly('Cannot modify EC2 Instances with deployfish')

    def delete(self, pk):
        raise InstanceManager.ReadOnly('Cannot modify EC2 Instances with deployfish')


# ----------------------------------------
# Models
# ----------------------------------------

class AutoscalingGroup(Model):

    # FIXME: add SSHMixin, and enable sshing to this autoscaling group

    objects = AutoscalingGroupManager()

    @property
    def pk(self):
        return self.data['AutoScalingGroupName']

    @property
    def name(self):
        return self.data['AutoScalingGroupName']

    @property
    def autoscaling_group(self):
        return self

    @property
    def instances(self):
        return self.get_cached(
            'instances',
            Instance.objects.get_many,
            [instance['InstanceId'] for instance in self.data['Instances']]
        )

    def scale(self, count, force=True):
        if self.objects.exists(self.pk):
            min_size = self.data['MinSize']
            max_size = self.data['MaxSize']
            if count < 0:
                count = 0
            if force:
                if count < self.min:
                    min_size = count
                elif count > self.max:
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

    def render_for_update(self):
        data = {}
        data['AutoScalingGroupName'] = self.data['AutoScalingGroupName']
        data['MinSize'] = self.data['MinSize']
        data['MaxSize'] = self.data['MaxSize']
        data['DesiredCapacity'] = self.data['DesiredCapacity']
        return data

    def render_for_diff(self):
        return self.render_for_update()


class Instance(TagsMixin, SSHMixin, Model):

    objects = InstanceManager()

    def __init__(self, data):
        super(Instance, self).__init__(data)
        self.import_tags(data['Tags'])

    @property
    def pk(self):
        return self.data['InstanceId']

    @property
    def name(self):
        return self.tags.get('Name', None)

    @property
    def arn(self):
        return None

    @property
    def ssh_target(self):
        return self

    @property
    def hostname(self):
        if self.data['PublicDnsName'] != '':
            return self.data['PublicDnsName']
        return self.data['PrivateDnsName']

    @property
    def private_hostname(self):
        return self.data['PrivateDnsName']

    @property
    def ip_address(self):
        return self.data['PrivateIpAddress']

    @property
    def bastion(self):
        try:
            return self.get_cached('bastion', self.objects.get, ['Name:bastion*'], {'vpc_id': self.data['VpcId']})
        except self.DoesNotExist:
            self.cache['bastion'] = None
            return None

    @property
    def autoscaling_group(self):
        if 'autoscaling_group' not in self.cache:
            try:
                autoscalinggroup_name = self.tags['aws:autoscaling:groupName']
            except KeyError:
                self.cache['autoscaling_group'] = None
            else:
                self.cache['autoscaling_group'] = AutoscalingGroup.objects.get(autoscalinggroup_name)
        return self.cache['autoscaling_group']
