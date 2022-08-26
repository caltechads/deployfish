import fnmatch
import re
from typing import List, Sequence, Dict, Optional, Any

from .abstract import Manager, Model
from .ec2 import Instance
from .mixins import TagsMixin

# ----------------------------------------
# Managers
# ----------------------------------------


class ClassicLoadBalancerManager(Manager):

    service = 'elb'

    def get(self, pk: str, **_) -> "ClassicLoadBalancer":
        instances = self.get_many([pk])
        if len(instances) > 1:
            raise ClassicLoadBalancer.MultipleObjectsReturned(
                "Got more than one load balancer when searching for pk={}".format(pk)
            )
        return instances[0]

    def get_many(self, pks: List[str], **kwargs) -> Sequence["ClassicLoadBalancer"]:
        kwargs = {'LoadBalancerNames': pks}
        paginator = self.client.get_paginator('describe_load_balancers')
        response_iterator = paginator.paginate(**kwargs)
        lbs = []
        try:
            for response in response_iterator:
                lbs.extend(response['LoadBalancerDescriptions'])
        except self.client.exceptions.AccessPointNotFoundException as e:
            msg = e.args[0]
            lbname = "Unknown"
            m = re.search(r'Cannot find Load Balancer (?P<lbname>[0-9A-Za-z]+)', msg)
            if m:
                lbname = m.group('lbname')
            raise ClassicLoadBalancer.DoesNotExist(
                'No Classic Load Balancer with name "{}" exists in AWS'.format(lbname)
            )
        return [ClassicLoadBalancer(lb) for lb in lbs]

    def list(
        self,
        vpc_id: str = None,
        scheme: str = 'any',
        name: str = None
    ) -> Sequence["ClassicLoadBalancer"]:
        paginator = self.client.get_paginator('describe_load_balancers')
        response_iterator = paginator.paginate()
        lb_data = []
        for response in response_iterator:
            try:
                lb_data.extend(response['LoadBalancerDescriptions'])
            except self.client.exceptions.AccessPointNotFoundException as e:
                msg = e.args[0]
                lbname = "Unknown"
                m = re.search(r'Cannot find Load Balancer (?P<lbname>[0-9A-Za-z]+)', msg)
                if m:
                    lbname = m.group('lbname')
                raise ClassicLoadBalancer.DoesNotExist(
                    'No Classic Load Balancer with name "{}" exists in AWS'.format(lbname)
                )
        lbs = []
        for lb in lb_data:
            if name and not fnmatch.fnmatch(lb['LoadBalancerName'], name):
                continue
            if vpc_id and lb['VPCId'] != vpc_id:
                continue
            if scheme not in ['any', lb['Scheme']]:
                continue
            lbs.append(ClassicLoadBalancer(lb))
        return lbs

    def get_tags(self, pk: str) -> List[Dict[str, str]]:
        response = self.client.describe_tags(LoadBalancerName=pk)
        return response['TagDescriptions']['Tags']


class ClassicLoadBalancerTargetManager(Manager):

    service = 'elb'

    def list(self, load_balancer_name: str) -> Sequence["ClassicLoadBalancerTarget"]:
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


# ----------------------------------------
# Models
# ----------------------------------------

class ClassicLoadBalancer(TagsMixin, Model):

    objects = ClassicLoadBalancerManager()

    lb_type: str = 'Classic (ELB)'

    # ---------------------
    # Model overrides
    # ---------------------

    @property
    def pk(self) -> str:
        return self.name

    @property
    def name(self) -> str:
        return self.data['LoadBalancerName']

    @property
    def arn(self) -> None:
        return None

    # ---------------------------------------
    # ClassicLoadBalancer-specific properties
    # ---------------------------------------

    @property
    def scheme(self) -> str:
        return self.data['Scheme']

    @property
    def hostname(self) -> str:
        return self.data['DNSName']

    @property
    def listeners(self) -> List[str]:
        return [listener['Listener'] for listener in self.data['ListenerDescriptions']]

    @property
    def ssl_certificate_arn(self) -> Optional[str]:
        cert_id = None
        for listener in self.data['ListenerDescriptions']:
            if 'SSLCertificateId' in listener['Listener'] and listener['Listener']['SSLCertificateId']:
                cert_id = listener['Listener']['SSLCertificateId']
        return cert_id

    @property
    def ssl_policy(self) -> Optional[str]:
        cert_id = None
        for listener in self.data['ListenerDescriptions']:
            if 'PolicyNames' in listener and listener['PolicyNames']:
                cert_id = listener['PolicyNames'][0]
        return cert_id

    @property
    def targets(self) -> Sequence["ClassicLoadBalancerTarget"]:
        return ClassicLoadBalancerTarget.objects.list(self.pk)


class ClassicLoadBalancerTarget(TagsMixin, Model):

    objects = ClassicLoadBalancerTargetManager()

    def __init__(self, data: Dict[str, Any], instance: Instance) -> None:
        super().__init__(data)
        self.instance: Instance = instance

    # ---------------------
    # Model overrides
    # ---------------------

    @property
    def pk(self) -> str:
        return self.instance.pk

    @property
    def name(self) -> str:
        return self.instance.name

    @property
    def arn(self) -> None:
        return None

    # ---------------------------------------------
    # ClassicLoadBalancerTarget-specific properties
    # ---------------------------------------------

    @property
    def hostname(self) -> str:
        return self.instance.hostname

    @property
    def private_hostname(self) -> str:
        return self.instance.private_hostname

    @property
    def ip_address(self) -> str:
        return self.instance.ip_address

    @property
    def bastion(self) -> Optional[Instance]:
        return self.instance.bastion

    @property
    def provisioner(self) -> Optional[Instance]:
        return self.instance.provisioner

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
