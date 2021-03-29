import botocore

from ..ssh import SSHMixin
from .abstract import Manager, Model

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

    def save(self, obj):
        self.asg.update_auto_scaling_group(**obj.render_for_update())

    def delete(self, pk):
        raise AutoscalingGroup.ReadOnly('Cannot delete Autoscaling Groups with deployfish')


class InstanceManager(Manager):

    service = 'ec2'

    def get(self, pk, **kwargs):
        kwargs = {}
        if pk.startswith('Name:'):
            kwargs['Filter'] = []
            kwargs['Filter'].append({'Name': 'tag:Name', 'Values': [pk.split(':')[1]]})
            if 'VpcId' in kwargs:
                kwargs['Filter'].append({'Name': 'vpc-id', 'Values': [kwargs['VpcId']]})
        else:
            kwargs['InstanceIds'] = [pk]
        try:
            response = self.client.describe_instances(**kwargs)
        except botocore.exceptions.ClientError:
            if kwargs:
                msg = 'No instance matching "{}" with filters {} exists in AWS'.format(
                    pk,
                    ', '.join(["{}={}" for k, v in kwargs.items()])
                )
            else:
                msg = 'No instance matching "{}" exists in AWS'.format(pk)
            raise Instance.DoesNotExist(msg)
        return Instance(response['Reservations'][0]['Instances'][0])

    def save(self, obj):
        self.asg.update_auto_scaling_group(**obj.render_for_update())

    def delete(self, pk):
        raise AutoscalingGroup.ReadOnly('Cannot delete Autoscaling Groups with deployfish')


# ----------------------------------------
# Models
# ----------------------------------------

class AutoscalingGroup(Model):

    objects = AutoscalingGroupManager()

    @property
    def pk(self):
        return self.data['AutoScalingGroupName']

    @property
    def name(self):
        return self.data['AutoScalingGroupName']

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
                    count = min_size
                if count > max_size:
                    count = max_size
            self.data['MinSize'] = min_size
            self.data['MaxSize'] = max_size
            self.data['DesiredCount'] = count
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


class Instance(SSHMixin, Model):

    objects = InstanceManager()

    def get_tag_value(self, tag_name):
        if not hasattr(self, '_tags'):
            self._tags = {}
            for tag in self.data['Tags']:
                self._tags[tag['Key']] = tag['Value']
        return self._tags[tag_name]

    @property
    def pk(self):
        return self.data['InstanceId']

    @property
    def name(self):
        return self.get_tag_value('Name')

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
            return self.get_cached('bastion', self.objects.get, ['Name:bastion*'], {'VpcId': self.data['VpcId']})
        except self.DoesNotExist:
            self.cache['bastion'] = None
            return None

    @property
    def autoscaling_group(self):
        if 'autoscaling_group' not in self.cache:
            try:
                autoscalinggroup_name = self.get_tag_value('aws:autoscaling:groupName')
            except KeyError:
                self.cache['autoscaling_group'] = None
            else:
                self.cache['autoscaling_group'] = AutoscalingGroup.objects.get(autoscalinggroup_name)
        return self.cache['autoscaling_group']
