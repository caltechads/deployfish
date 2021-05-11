import fnmatch
import re

from .abstract import Manager, Model
from .ec2 import Instance
from .mixins import TagsMixin

# ----------------------------------------
# Managers
# ----------------------------------------


class ClassicLoadBalancerManager(Manager):

    service = 'elb'

    def get(self, pk):
        # hint: (str["{load_balancer_name}", "{load_balancer_arn}"])
        instances = self.get_many([pk])
        if len(instances) > 1:
            raise ClassicLoadBalancer.MultipleObjectsReturned(
                "Got more than one load balancer when searching for pk={}".format(
                    pk,
                    ", ".join([instance.pk for instance in instances])
                )
            )
        return instances[0]

    def get_many(self, pks):
        # hint: (list[str["{load balancer name}"]])
        kwargs = {'LoadBalancerNames': pks}
        paginator = self.client.get_paginator('describe_load_balancers')
        response_iterator = paginator.paginate(**kwargs)
        lbs = []
        try:
            for response in response_iterator:
                lbs.extend(response['LoadBalancerDescriptions'])
        except self.client.exceptions.AccessPointNotFoundException as e:
            msg = e.args[0]
            m = re.search(r'Cannot find Load Balancer (?P<lbname>[0-9A-Za-z]+)', msg)
            raise ClassicLoadBalancer.DoesNotExist(
                'No Classic Load Balancer with name "{}" exists in AWS'.format(m.group('lbname'))
            )
        return [ClassicLoadBalancer(lb) for lb in lbs]

    def list(self, vpc_id=None, scheme='any', name=None):
        # hint: (str["{vpc_id}"], choice[internet-facing|internal|any], str["{load_balancer_name:glob}"])
        paginator = self.client.get_paginator('describe_load_balancers')
        response_iterator = paginator.paginate()
        lb_data = []
        for response in response_iterator:
            try:
                lb_data.extend(response['LoadBalancerDescriptions'])
            except self.client.exceptions.AccessPointNotFoundException as e:
                msg = e.args[0]
                m = re.search(r'Cannot find Load Balancer (?P<lbname>[0-9A-Za-z]+)', msg)
                raise ClassicLoadBalancer.DoesNotExist(
                    'No Classic Load Balancer with name "{}" exists in AWS'.format(m.group('lbname'))
                )
        albs = []
        for lb in lb_data:
            if name and not fnmatch.fnmatch(lb['LoadBalancerName'], name):
                continue
            if vpc_id and lb['VPCId'] != vpc_id:
                continue
            if scheme != 'any' and lb['Scheme'] != scheme:
                continue
            albs.append(ClassicLoadBalancer(lb))
        return albs

    def get_tags(self, pk):
        response = self.client.describe_tags(LoadBalancerName=pk)
        return response['TagDescriptions']['Tags']

    def save(self, obj):
        raise ClassicLoadBalancer.ReadOnly('Cannot modify Classic Load Balancers with deployfish')

    def delete(self, pk):
        raise ClassicLoadBalancer.ReadOnly('Cannot modify Classic Load Balancers with deployfish')


class ClassicLoadBalancerTargetManager(Manager):

    service = 'elb'

    def list(self, load_balancer_name):
        try:
            response = self.client.describe_instance_health(LoadBalancerName=load_balancer_name)
        except self.client.exceptions.AccessPointNotFoundException:
            raise ClassicLoadBalancer.DoesNotExist(
                'No Classic Load Balancer named "{}" exists in AWS'.format(load_balancer_name)
            )
        targets = []
        for data in response['InstanceStates']:
            instance = Instance.objects.get(data['InstanceId'])
            targets.append(ClassicLoadBalancerTarget(data, instance))
        return targets

    def save(self, obj):
        raise ClassicLoadBalancerTarget.ReadOnly('Cannot modify ClassicLoadBalancerTargets.')

    def delete(self, pk):
        raise ClassicLoadBalancerTarget.ReadOnly('Cannot modify TargetGroupTargets.')


# ----------------------------------------
# Models
# ----------------------------------------

class ClassicLoadBalancer(TagsMixin, Model):

    objects = ClassicLoadBalancerManager()

    @property
    def pk(self):
        return self.name

    @property
    def name(self):
        return self.data['LoadBalancerName']

    @property
    def arn(self):
        return None

    @property
    def scheme(self):
        return self.data['Scheme']

    @property
    def hostname(self):
        return self.data['DNSName']

    @property
    def listeners(self):
        return [l['Listener'] for l in self.data['ListenerDescriptions']]

    @property
    def ssl_certificate_arn(self):
        for listener in self.data['ListenerDescriptions']:
            if 'SSLCertificateId' in listener['Listener'] and listener['Listener']['SSLCertificateId']:
                return listener['Listener']['SSLCertificateId']

    @property
    def ssl_policy(self):
        for listener in self.data['ListenerDescriptions']:
            if 'PolicyNames' in listener and listener['PolicyNames']:
                return listener['PolicyNames'][0]

    @property
    def targets(self):
        return ClassicLoadBalancerTarget.objects.list(self.pk)


class ClassicLoadBalancerTarget(TagsMixin, Model):

    objects = ClassicLoadBalancerTargetManager()

    def __init__(self, data, instance):
        super(ClassicLoadBalancerTarget, self).__init__(data)
        self.instance = instance

    @property
    def pk(self):
        return self.instance.pk

    @property
    def name(self):
        return self.instance.name

    @property
    def arn(self):
        return None

    @property
    def hostname(self):
        return self.instance.hostname

    @property
    def private_hostname(self):
        return self.instance.private_hostname

    @property
    def ip_address(self):
        return self.instance.ip_address

    @property
    def bastion(self):
        return self.instance.bastion

    @property
    def autoscaling_group(self):
        return self.instance.autoscaling_group

    @property
    def ssh_target(self):
        return self.instance

    def render_for_display(self):
        data = self.render()
        data['Instance'] = self.instance.render_for_display()
        return data
