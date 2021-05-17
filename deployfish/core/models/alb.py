import fnmatch

from .abstract import Manager, Model
from .ec2 import Instance
from .mixins import TagsMixin


# ----------------------------------------
# Managers
# ----------------------------------------


class ApplicationLoadBalancerManager(Manager):

    service = 'elbv2'

    def get(self, pk):
        # hint: (str["{load_balancer_name}", "{load_balancer_arn}"])
        instances = self.get_many([pk])
        if len(instances) > 1:
            raise ApplicationLoadBalancer.MultipleObjectsReturned(
                "Got more than one load balancer when searching for pk={}".format(
                    pk,
                    ", ".join([instance.pk for instance in instances])
                )
            )
        return instances[0]

    def get_many(self, pks):
        # hint: (list[str["{load balancer name}", "{load balancer arn}"]])
        arns = []
        names = []
        kwargs = {}
        for pk in pks:
            if pk.startswith('arn:'):
                arns.append(pk)
            else:
                names.append(pk)
        if names:
            kwargs['Names'] = names
        if arns:
            kwargs['LoadBalancerArns'] = arns
        paginator = self.client.get_paginator('describe_load_balancers')
        response_iterator = paginator.paginate(**kwargs)
        lbs = []
        try:
            for response in response_iterator:
                lbs.extend(response['LoadBalancers'])
        except self.client.exceptions.LoadBalancerNotFoundException as e:
            raise ApplicationLoadBalancer.DoesNotExist(str(e))
        return [ApplicationLoadBalancer(lb) for lb in lbs if lb['Type'] == 'application']

    def list(self, vpc_id=None, scheme='any', name=None):
        # hint: (str["{vpc_id}"], choice[internet-facing|internal|any], str["{load_balancer_name:glob}"])
        paginator = self.client.get_paginator('describe_load_balancers')
        response_iterator = paginator.paginate()
        lb_data = []
        for response in response_iterator:
            lb_data.extend(response['LoadBalancers'])
        albs = []
        for lb in lb_data:
            if name and not fnmatch.fnmatch(lb['LoadBalancerName'], name):
                continue
            if vpc_id and lb['VpcId'] != vpc_id:
                continue
            if scheme != 'any' and lb['Scheme'] != scheme:
                continue
            albs.append(ApplicationLoadBalancer(lb))
        return albs

    def get_tags(self, arn):
        try:
            response = self.client.describe_tags(ResourceArns=[arn])
        except self.client.exceptions.LoadBalancerNotFoundException as e:
            raise ApplicationLoadBalancer.DoesNotExist(str(e))
        return response['TagDescriptions']['Tags']

    def save(self, obj):
        raise ApplicationLoadBalancer.ReadOnly('Cannot modify Application Load Balancers with deployfish')

    def delete(self, pk):
        raise ApplicationLoadBalancer.ReadOnly('Cannot modify Application Load Balancers with deployfish')


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

    def list(self, load_balancer=None):
        # hint: (str["{load_balancer_arn}","{load_balancer_name}"])
        paginator = self.client.get_paginator('describe_listeners')
        kwargs = {}
        if not load_balancer.startswith('arn:'):
            # This is a load balancer name
            lb = ApplicationLoadBalancer.objects.get(load_balancer)
            load_balancer = lb.arn
        if load_balancer:
            kwargs['LoadBalancerArn'] = load_balancer
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

    def __init__(self):
        super(LoadBalancerListenerRuleManager, self).__init__()
        self.cache = {'load_balancers': {}}

    def get(self, pk):
        # hint: (str["{listener_arn}"])
        return self.get_many([pk])[0]

    def get_many(self, pks):
        # hint: (list(str["{rule_arn}"]))
        paginator = self.client.get_paginator('describe_rules')
        response_iterator = paginator.paginate(RuleArns=pks)
        rules = []
        for response in response_iterator:
            rules.extend(response['Rules'])
        return [LoadBalancerListenerRule(rule) for rule in rules]

    def __get_rules_for_load_balancer(self, load_balancer_pk):
        if load_balancer_pk not in self.cache['load_balancers']:
            lb = ApplicationLoadBalancer.objects.get(load_balancer_pk)
            listener_arns = [listener.arn for listener in lb.listeners]
            rule_objects = []
            for arn in listener_arns:
                rule_objects.extend(self.list(listener_arn=arn))
            self.cache['load_balancers'][load_balancer_pk] = rule_objects
        return self.cache['load_balancers'][load_balancer_pk]

    def __get_rules_for_target_group(self, target_group_arn):
        tg = TargetGroup.objects.get(target_group_arn)
        load_balancer_pk = tg.data['LoadBalancerArns'][0]
        rule_objects = self.__get_rules_for_load_balancer(load_balancer_pk)
        matched_rules = []
        for obj in rule_objects:
            for action in obj.data['Actions']:
                if action['Type'] == 'forward' and action['TargetGroupArn'] == target_group_arn:
                    # I'm making an important assumption here that the relevant target group is the one attached
                    # to the first 'forward' action on the rule, and that we only have one TargetGroup -- we're
                    # not using a weighted ForwardConfig with a list of TargetGroupArns.
                    #
                    # If we ever start doing green/blue deployments with two services attached to the same
                    # listener rule, we'll need to fix this.
                    matched_rules.append(obj)
        return matched_rules

    def list(self, listener_arn=None, load_balancer_pk=None, target_group_arn=None):
        # hint: (str["{listener_arn}"], str["{load_balancer_arn}","{load_balancer_name}"], str["{target_group_arn}"])
        options = [listener_arn, load_balancer_pk, target_group_arn]
        if sum(x is not None for x in options) > 1:
            raise LoadBalancerListener.OperationFailed(
                'Use only one of "listener_arn", "load_balancer_pk", or "target_group_arn".'
            )
        kwargs = {}
        if target_group_arn:
            return self.__get_rules_for_target_group(target_group_arn)
        elif load_balancer_pk:
            return self.__get_rules_for_load_balancer(load_balancer_pk)
        elif listener_arn:
            kwargs['ListenerArn'] = listener_arn
            paginator = self.client.get_paginator('describe_rules')
            response_iterator = paginator.paginate(**kwargs)
            rules = []
            for response in response_iterator:
                rules.extend(response['Rules'])
            return [LoadBalancerListenerRule(rule, listener_arn=listener_arn) for rule in rules]

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
        # hint: (list[str["{target_group_arn}","{target_group_name}"]])
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

    def list(self, load_balancer=None):
        # hint: (str["{load_balancer_arn}","{load_balancer_name}"])
        kwargs = {}
        if not load_balancer.startswith('arn:'):
            # This is a load balancer name
            lb = ApplicationLoadBalancer.objects.get(load_balancer)
            load_balancer = lb.arn
        if load_balancer:
            kwargs['LoadBalancerArn'] = load_balancer
        paginator = self.client.get_paginator('describe_target_groups')
        response_iterator = paginator.paginate(**kwargs)
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
        raise LoadBalancerListener.ReadOnly('Cannot modify TargetGroups with deployfish')

    def delete(self, pk):
        raise LoadBalancerListener.ReadOnly('Cannot modify TargetGroups with deployfish')


class TargetGroupTargetManager(Manager):

    service = 'elbv2'

    def list(self, target_group_arn):
        try:
            response = self.client.describe_target_health(TargetGroupArn=target_group_arn)
        except self.client.exceptions.TargetGroupNotFoundException:
            raise TargetGroup.DoesNotExist('TargetGroup("{}") does not exist in AWS'.format(target_group_arn))
        targets = []
        for data in response['TargetHealthDescriptions']:
            target_data = data['Target']
            target_data['TargetHealth'] = data['TargetHealth']
            target_data['HealthCheckPort'] = data['HealthCheckPort']
            targets.append(TargetGroupTarget(target_data))
        return targets

    def save(self, obj):
        raise TargetGroupTarget.ReadOnly('Cannot modify TargetGroupTargets.')

    def delete(self, pk):
        raise TargetGroupTarget.ReadOnly('Cannot modify TargetGroupTargets.')


# ----------------------------------------
# Models
# ----------------------------------------

class ApplicationLoadBalancer(TagsMixin, Model):

    objects = ApplicationLoadBalancerManager()

    @property
    def pk(self):
        return self.arn

    @property
    def name(self):
        return self.data['LoadBalancerName']

    @property
    def arn(self):
        return self.data['LoadBalancerArn']

    @property
    def scheme(self):
        return self.data['Scheme']

    @property
    def hostname(self):
        return self.data['DNSName']

    @property
    def listeners(self):
        if 'listeners' not in self.cache:
            self.cache['listeners'] = LoadBalancerListener.objects.list(load_balancer=self.arn)
        return self.cache['listeners']

    @property
    def target_groups(self):
        if 'target_groups' not in self.cache:
            self.cache['target_groups'] = TargetGroup.objects.list(load_balancer=self.data['LoadBalancerArn'])
        return self.cache['target_groups']


class LoadBalancerListener(Model):

    objects = LoadBalancerListenerManager()

    @property
    def pk(self):
        return self.arn

    @property
    def name(self):
        return '{} ({})'.format(self.port, self.protocol)

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
    def ssl_certificates(self):
        return [c['CertificateArn'] for c in self.data.get(self.data['Certificates'])]

    @property
    def ssl_policy(self):
        return self.data['SslPolicy']


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
    def listener(self):
        if 'listener' not in self.cache:
            self.cache['listener'] = LoadBalancerListener.objects.get(self.listener_arn)
        return self.cache['listener']

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


class TargetGroup(Model):

    objects = TargetGroupManager()

    @property
    def pk(self):
        return self.arn

    @property
    def name(self):
        return self.data['TargetGroupName']

    @property
    def arn(self):
        return self.data['TargetGroupArn']

    @property
    def load_balancers(self):
        if 'load_balancers' not in self.cache:
            self.cache['load_balancers'] = ApplicationLoadBalancer.objects.get_many(self.data['LoadBalancerArns'])
        return self.cache['load_balancers']

    @property
    def rules(self):
        """
        .. note::

            The dumb thing here is that you can't ask the target group itself what listener rules it is attached to --
            you have to start at the load balancer, list all the listener rules that
        """
        if 'listener_rules' not in self.cache:
            self.cache['listener_rules'] = LoadBalancerListenerRule.objects.list(target_group_arn=self.arn)
        return self.cache['listener_rules']

    @property
    def listeners(self):
        if 'listeners' not in self.cache:
            listeners = {}
            # First extract the listeners from any rules we have
            for rule in self.rules:
                listeners[rule.listener_arn] = rule.listener
            # Now look through all the listeners on our load balancers to see
            # if we're the default action on any of them
            for lb in self.load_balancers:
                for listener in lb.listeners:
                    if 'DefaultActions' in listener.data:
                        for action in listener.data['DefaultActions']:
                            if action['Type'] == 'forward' and 'TargetGroupArn' in action:
                                listeners[listener.arn] = listener
            self.cache['listeners'] = list(listeners.values())
        return self.cache['listeners']

    @property
    def targets(self):
        return TargetGroupTarget.objects.list(self.arn)

    @property
    def port(self):
        return self.data['Port']

    @property
    def protocol(self):
        return self.data['Protocol']


class TargetGroupTarget(Model):

    objects = TargetGroupTargetManager()

    @property
    def pk(self):
        return self.data['Id']

    @property
    def name(self):
        return self.pk

    @property
    def arn(self):
        return None

    @property
    def target(self):
        if 'target' not in self.cache:
            if self.data['Id'].startswith('i-'):
                # this is an instance
                self.cache['target'] = Instance.objects.get(self.data['Id'])
            else:
                raise self.OperationFailed(
                    'TargetGroupTarget("{}"): currently can\'t defereference targets of this type'.format(self.pk)
                )
        return self.cache['target']

    @property
    def target_group(self):
        if 'target_group' not in self.cache:
            self.cache['target_group'] = TargetGroup.objects.get(self.data['TargetGroupArn'])
        return self.cache['target_group']

    @property
    def health(self):
        return self.data['TargetHealth']
