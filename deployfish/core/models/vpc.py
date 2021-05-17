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
            if ids.startswith('vpc-'):
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


class LoadBalancerListenerManager(Manager):

    service = 'elbv2'

    def get(self, pk):
        # hint: (str["{listener_arn}"])
        try:
            response = self.client.describe_listeners(
                ListenerArns=[pk]
            )
        except self.client.exceptions.ListenerNotFoundException as e:
            raise LoadBalancerListener.DoesNotExist(str(e))
        return LoadBalancerListener(response['Listeners'][0])

    def list(self, load_balancer_arn=None):
        # hint: (str["{load_balancer_arn}"])
        paginator = self.client.get_paginator('describe_load_balancers')
        kwargs = {}
        if load_balancer_arn:
            kwargs['LoadBalancerArn'] = load_balancer_arn
        response_iterator = paginator.paginate(**kwargs)
        listeners = []
        try:
            for response in response_iterator:
                listeners.extend(response['Listeners'])
        except self.client.exceptions.LoadBalancerNotFoundException as e:
            raise ApplicationLoadBalancer.DoesNotExist(str(e))
        return [LoadBalancerListener(listener) for listener in listeners]

    def get_tags(self, arn):
        try:
            response = self.client.describe_tags(ResourceArns=[arn])
        except self.client.exceptions.LoadBalancerNotFoundException as e:
            raise ApplicationLoadBalancer.DoesNotExist(str(e))
        return response['TagDescriptions']['Tags']

    def save(self, obj):
        raise LoadBalancerListener.ReadOnly('Cannot modify Load Balancer Listeners with deployfish')

    def delete(self, pk):
        raise LoadBalancerListener.ReadOnly('Cannot modify Load Balancer Listeners with deployfish')


class LoadBalancerListenerRuleManager(Manager):

    service = 'elbv2'

    def get(self, pk):
        # hint: (str["{listener_arn}"])
        return self.get_many([pk])[0]

    def get_many(self, pks):
        # hint: (list[str["{rule_arn}"]])
        paginator = self.client.get_paginator('describe_rules')
        response_iterator = paginator.paginate(RuleArns=pks)
        rules = []
        for response in response_iterator:
            rules.extend(response['Rules'])
        return [LoadBalancerListenerRule(rule) for rule in rules]

    def list(self, listener_arn=None, load_balancer_pk=None, target_group_arn=None):
        # hint: (str["{listener_arn}"], str["{load_balancer_arn}","{load_balancer_name}"], str["{target_group_arn}"])
        options = [listener_arn, load_balancer_pk, target_group_arn]
        if sum(x is not None for x in options) < 2:
            raise self.OperationFailed('Use only one of "listener_arn", "load_balancer_pk", or "target_group_arn".')
        kwargs = {}
        if target_group_arn:
            tg = TargetGroup.objects.get(target_group_arn)
            load_balancer_pk = tg.data['LoadBalancerArn']
        if load_balancer_pk:
            lb = ApplicationLoadBalancer.objects.get(load_balancer_pk)
            listener_arns = [listener.arn for listener in lb.listeners]
            rules = []
            for arn in listener_arns:
                rules.extend(self.list(listener_arn=arn))
            return rules
        if listener_arn:
            kwargs['ListenerArn'] = listener_arn
        paginator = self.client.get_paginator('describe_rules')
        response_iterator = paginator.paginate(**kwargs)
        rules = []
        for response in response_iterator:
            rules.extend(response['Rules'])
        if target_group_arn:
            # This is seemingly the only way to find the listener rule that a target group is attached to --
            # * The TargetGroup knows its ApplicationLoadBalancer, but nothing else, so:
            #   * List all LoadBalancerListeners on that ApplicationLoadBalancer
            #   * List all LoadBalancerListenerRules on each of those LoadBalancerListeners
            #   * Look through all those LoadBalancerListenerRules to find those which reference our TargetGroup.
            #   * Return that list of LoadBalancerListenerRules
            rule_objects = []
            for rule in rules:
                for action in rule['Actions']:
                    if action['Type'] == 'forward' and action['TargetGroupArn'] == target_group_arn:
                        # I'm making an important assumption here that the relevant target group is the one attached to
                        # the first 'forward' action on the rule, and that we only have one TargetGroup -- we're not
                        # using a weighted ForwardConfig with a list of TargetGroupArns.
                        #
                        # If we ever start doing green/blue deployments with two services attached to the same listener
                        # rule, we'll need to fix this.
                        rule_objects.append(LoadBalancerListenerRule(rule))
        else:
            rule_objects = [LoadBalancerListenerRule(rule, listener_arn=listener_arn) for rule in rules]
        return rule_objects

    def get_tags(self, arn):
        try:
            response = self.client.describe_tags(ResourceArns=[arn])
        except self.client.exceptions.LoadBalancerNotFoundException as e:
            raise ApplicationLoadBalancer.DoesNotExist(str(e))
        return response['TagDescriptions']['Tags']

    def save(self, obj):
        raise LoadBalancerListener.ReadOnly('Cannot modify Load Balancer Listener Rules with deployfish')

    def delete(self, pk):
        raise LoadBalancerListener.ReadOnly('Cannot modify Load Balancer Listener Rules with deployfish')


class TargetGroupManager(Manager):

    service = 'elbv2'

    def get(self, pk):
        # hint: (str["{target_group_arn}","{target_group_name}"])
        return self.get_many([pk])[0]

    def get_many(self, pks):
        # hint: (lis[(str["{target_group_arn}","{target_group_name}"]])
        kwargs = {}
        for pk in pks:
            if pk.startswith('arn:'):
                if 'TargetGroupArns' not in kwargs:
                    kwargs['TargetGroupArns'] = []
                kwargs['TargetGroupArns'].append(pk)
            else:
                if 'Names' not in kwargs:
                    kwargs['Names'] = []
                kwargs['Names'].append(pk)
        paginator = self.client.get_paginator('describe_target_groups')
        response_iterator = paginator.paginate(**kwargs)
        tgs = []
        try:
            for response in response_iterator:
                tgs.extend(response['TargetGroups'])
        except self.client.exceptions.LoadBalancerNotFoundException as e:
            raise ApplicationLoadBalancer.DoesNotExist(str(e))
        except self.client.exceptions.TargetGroupNotFoundException as e:
            raise TargetGroup.DoesNotExist(str(e))
        return [TargetGroup(tg) for tg in tgs]

    def list(self, load_balancer_arn=None):
        # hint: (str["{load_balancer_arn}"])
        kwargs = {}
        if load_balancer_arn:
            kwargs['LoadBalancerArn'] = load_balancer_arn
        paginator = self.client.get_paginator('describe_target_groups')
        response_iterator = paginator.paginate(LoadBalancerArn=load_balancer_arn)
        tgs = []
        try:
            for response in response_iterator:
                tgs.extend(response['TargetGroups'])
        except self.client.exceptions.LoadBalancerNotFoundException as e:
            raise ApplicationLoadBalancer.DoesNotExist(str(e))
        return [TargetGroup(tg) for tg in tgs]

    def get_tags(self, arn):
        try:
            response = self.client.describe_tags(ResourceArns=[arn])
        except self.client.exceptions.LoadBalancerNotFoundException as e:
            raise ApplicationLoadBalancer.DoesNotExist(str(e))
        return response['TagDescriptions']['Tags']

    def save(self, obj):
        raise LoadBalancerListener.ReadOnly('Cannot modify Load Balancer Listeners with deployfish')

    def delete(self, pk):
        raise LoadBalancerListener.ReadOnly('Cannot modify Load Balancer Listeners with deployfish')


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

    objects = LoadBalancerListenerManager()

    @property
    def pk(self):
        return self.arn

    @property
    def name(self):
        return self.arn

    @property
    def arn(self):
        return self.data['ListenerArn']

    @property
    def load_balancer(self):
        if 'load_balancer' not in self.cache:
            self.cache['load_balancer'] = ApplicationLoadBalancer.objects.get(self.data['LoadBalancerArn'])
        return self.cache['load_balancer']

    @property
    def rules(self):
        if 'rules' not in self.cache:
            self.cache['rules'] = LoadBalancerListenerRule.objects.list(listener_arn=self.arn)
        return self.cache['rules']

    @property
    def port(self):
        return self.data['Port']

    @property
    def protocol(self):
        return self.data['Protocol']

    @property
    def tags(self):
        if 'tags' not in self.cache:
            self.cache['tags'] = {}
            for tag in self.objects.get_tags(self.arn):
                self.cache['tags'][tag['Key']] = tag['Value']
        return self.cache['tags']


class LoadBalancerListenerRule(Model):

    objects = LoadBalancerListenerRuleManager()

    def __init__(self, data, listener_arn=None):
        super(LoadBalancerListenerRule, self).__init__(data)
        self.listener_arn = listener_arn

    @property
    def pk(self):
        return self.arn

    @property
    def name(self):
        return self.arn

    @property
    def arn(self):
        return self.data['RuleArn']

    @property
    def load_balancer(self):
        if 'load_balancer' not in self.cache:
            self.cache['load_balancer'] = ApplicationLoadBalancer.objects.get(self.data['LoadBalancerArn'])
        return self.cache['load_balancer']

    @property
    def target_group(self):
        """
        .. note::

            I'm making an important assumption here that the relevant target group is the one attached to the first
            'forward' action on the rule, and that we only have one TargetGroup -- we're not using a weighted
            ForwardConfig with a list of TargetGroupArns.

            If we ever start doing green/blue deployments with two services attached to the same listener rule, we'll
            need to fix this.
        """
        if 'target_group' not in self.cache:
            target_group = None
            for action in self.data['Actions']:
                if action['Type'] == 'forward':
                    target_group = TargetGroup.objects.get(action['TargetGroupArn'])
            self.cache['target_group'] = target_group
        return self.cache['target_group']

    @property
    def port(self):
        return self.data['Port']

    @property
    def protocol(self):
        return self.data['Protocol']

    @property
    def tags(self):
        if 'tags' not in self.cache:
            self.cache['tags'] = {}
            for tag in self.objects.get_tags(self.arn):
                self.cache['tags'][tag['Key']] = tag['Value']
        return self.cache['tags']


class TargetGroup(Model):

    objects = TargetGroupManager()

    @property
    def pk(self):
        return "{}:{}".format(self.data['LoadBalancerArn'], self.data['ListenerArn'])

    @property
    def name(self):
        return self.pk

    @property
    def arn(self):
        return self.data['ListenerArn']

    @property
    def load_balancer(self):
        if 'load_balancer' not in self.cache:
            self.cache['load_balancer'] = ApplicationLoadBalancer.objects.get(self.data['LoadBalancerArn'])
        return self.cache['load_balancer']

    @property
    def listener_rule(self):
        """
        .. note::

            The dumb thing here is that you can't ask the target group itself what listener rule it is attached to --
            you have to start at the load balancer, list all the listener rules that
        """

    @property
    def port(self):
        return self.data['Port']

    @property
    def protocol(self):
        return self.data['Protocol']

    @property
    def tags(self):
        if 'tags' not in self.cache:
            self.cache['tags'] = {}
            for tag in self.objects.get_tags(self.arn):
                self.cache['tags'][tag['Key']] = tag['Value']
        return self.cache['tags']

