import fnmatch
from typing import List, Sequence, Dict, Any, Optional

from .abstract import Manager, Model
from .ec2 import Instance
from .mixins import TagsMixin


# ----------------------------------------
# Managers
# ----------------------------------------


class LoadBalancerManager(Manager):

    service = 'elbv2'

    def get(self, pk: str, **_) -> "LoadBalancer":
        instances = self.get_many([pk])
        if len(instances) > 1:
            raise LoadBalancer.MultipleObjectsReturned(f"Got more than one load balancer when searching for pk={pk}")
        return instances[0]

    def get_many(self, pks: List[str], **kwargs) -> Sequence["LoadBalancer"]:
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
            raise LoadBalancer.DoesNotExist(str(e))
        return [LoadBalancer(lb) for lb in lbs]

    def list(
        self,
        vpc_id: str = None,
        lb_type: str = 'any',
        scheme: str = 'any',
        name: str = None
    ) -> Sequence["LoadBalancer"]:
        paginator = self.client.get_paginator('describe_load_balancers')
        response_iterator = paginator.paginate()
        lb_data = []
        for response in response_iterator:
            lb_data.extend(response['LoadBalancers'])
        lbs = []
        for lb in lb_data:
            if name and not fnmatch.fnmatch(lb['LoadBalancerName'], name):
                continue
            if vpc_id and lb['VpcId'] != vpc_id:
                continue
            if scheme not in ['any', lb['Scheme']]:
                continue
            if lb_type not in ['any', lb['Type']]:
                continue
            lbs.append(LoadBalancer(lb))
        return lbs

    def get_tags(self, arn: str) -> List[Dict[str, str]]:
        try:
            response = self.client.describe_tags(ResourceArns=[arn])
        except self.client.exceptions.LoadBalancerNotFoundException as e:
            raise LoadBalancer.DoesNotExist(str(e))
        return response['TagDescriptions']['Tags']


class LoadBalancerListenerManager(Manager):

    service = 'elbv2'

    def get(self, pk: str, **_) -> "LoadBalancerListener":
        try:
            response = self.client.describe_listeners(
                ListenerArns=[pk]
            )
        except self.client.exceptions.ListenerNotFoundException as e:
            raise LoadBalancerListener.DoesNotExist(str(e))
        return LoadBalancerListener(response['Listeners'][0])

    def list(self, load_balancer: str) -> Sequence["LoadBalancerListener"]:
        paginator = self.client.get_paginator('describe_listeners')
        kwargs = {}
        if load_balancer:
            if not load_balancer.startswith('arn:'):
                # This is a load balancer name
                lb = LoadBalancer.objects.get(load_balancer)
                load_balancer = lb.arn
            kwargs['LoadBalancerArn'] = load_balancer
        response_iterator = paginator.paginate(**kwargs)
        listeners = []
        try:
            for response in response_iterator:
                listeners.extend(response['Listeners'])
        except self.client.exceptions.LoadBalancerNotFoundException as e:
            raise LoadBalancer.DoesNotExist(str(e))
        return [LoadBalancerListener(listener) for listener in listeners]

    def get_tags(self, arn: str) -> List[Dict[str, str]]:
        try:
            response = self.client.describe_tags(ResourceArns=[arn])
        except self.client.exceptions.LoadBalancerNotFoundException as e:
            raise LoadBalancer.DoesNotExist(str(e))
        return response['TagDescriptions']['Tags']


class LoadBalancerListenerRuleManager(Manager):

    service = 'elbv2'

    def __init__(self):
        super().__init__()
        self.cache: Dict[str, Dict[str, Any]] = {'load_balancers': {}}

    def get(self, pk: str, **_) -> "LoadBalancerListenerRule":
        return self.get_many([pk])[0]

    def get_many(self, pks: List[str], **_) -> Sequence["LoadBalancerListenerRule"]:
        paginator = self.client.get_paginator('describe_rules')
        response_iterator = paginator.paginate(RuleArns=pks)
        rules = []
        for response in response_iterator:
            rules.extend(response['Rules'])
        return [LoadBalancerListenerRule(rule) for rule in rules]

    def __get_rules_for_load_balancer(self, load_balancer_pk: str) -> Sequence["LoadBalancerListenerRule"]:
        if load_balancer_pk not in self.cache['load_balancers']:
            lb = LoadBalancer.objects.get(load_balancer_pk)
            listener_arns = [listener.arn for listener in lb.listeners]
            rule_objects: List["LoadBalancerListenerRule"] = []
            for arn in listener_arns:
                rule_objects.extend(self.list(listener_arn=arn))
            self.cache['load_balancers'][load_balancer_pk] = rule_objects
        return self.cache['load_balancers'][load_balancer_pk]

    def __get_rules_for_target_group(self, target_group_arn: str) -> Sequence["LoadBalancerListenerRule"]:
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

    def list(
        self,
        listener_arn: str = None,
        load_balancer_pk: str = None,
        target_group_arn: str = None
    ) -> Sequence["LoadBalancerListenerRule"]:
        options = [listener_arn, load_balancer_pk, target_group_arn]
        if sum(x is not None for x in options) > 1:
            raise LoadBalancerListener.OperationFailed(
                'Use only one of "listener_arn", "load_balancer_pk", or "target_group_arn".'
            )
        kwargs = {}
        rules: Sequence["LoadBalancerListenerRule"] = []
        if target_group_arn:
            rules = self.__get_rules_for_target_group(target_group_arn)
        elif load_balancer_pk:
            rules = self.__get_rules_for_load_balancer(load_balancer_pk)
        elif listener_arn:
            kwargs['ListenerArn'] = listener_arn
            paginator = self.client.get_paginator('describe_rules')
            response_iterator = paginator.paginate(**kwargs)
            rules_data = []
            for response in response_iterator:
                rules_data.extend(response['Rules'])
            rules = [LoadBalancerListenerRule(d, listener_arn=listener_arn) for d in rules_data]
        return rules

    def get_tags(self, arn: str) -> List[Dict[str, str]]:
        try:
            response = self.client.describe_tags(ResourceArns=[arn])
        except self.client.exceptions.LoadBalancerNotFoundException as e:
            raise LoadBalancer.DoesNotExist(str(e))
        return response['TagDescriptions']['Tags']


class TargetGroupManager(Manager):

    service = 'elbv2'

    def get(self, pk: str, **_) -> "TargetGroup":
        return self.get_many([pk])[0]

    def get_many(self, pks: List[str], **kwargs) -> Sequence["TargetGroup"]:
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
            raise LoadBalancer.DoesNotExist(str(e))
        except self.client.exceptions.TargetGroupNotFoundException as e:
            raise TargetGroup.DoesNotExist(str(e))
        return [TargetGroup(tg) for tg in tgs]

    def list(self, load_balancer: str = None) -> Sequence["TargetGroup"]:
        kwargs = {}
        if load_balancer:
            if not load_balancer.startswith('arn:'):
                # This is a load balancer name
                lb = LoadBalancer.objects.get(load_balancer)
                load_balancer = lb.arn
            kwargs['LoadBalancerArn'] = load_balancer
        paginator = self.client.get_paginator('describe_target_groups')
        response_iterator = paginator.paginate(**kwargs)
        tgs = []
        try:
            for response in response_iterator:
                tgs.extend(response['TargetGroups'])
        except self.client.exceptions.LoadBalancerNotFoundException as e:
            raise LoadBalancer.DoesNotExist(str(e))
        return [TargetGroup(tg) for tg in tgs]

    def get_tags(self, arn: str) -> List[Dict[str, str]]:
        try:
            response = self.client.describe_tags(ResourceArns=[arn])
        except self.client.exceptions.LoadBalancerNotFoundException as e:
            raise LoadBalancer.DoesNotExist(str(e))
        return response['TagDescriptions']['Tags']


class TargetGroupTargetManager(Manager):

    service = 'elbv2'

    def list(self, target_group_arn: str) -> Sequence['TargetGroupTarget']:
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


# ----------------------------------------
# Models
# ----------------------------------------

class LoadBalancer(TagsMixin, Model):

    objects = LoadBalancerManager()

    # ---------------------
    # Model overrides
    # ---------------------

    @property
    def pk(self) -> str:
        return self.arn

    @property
    def name(self) -> str:
        return self.data['LoadBalancerName']

    @property
    def arn(self) -> str:
        return self.data['LoadBalancerArn']

    # ---------------------------------
    # LoadBalancer-specific properties
    # ---------------------------------

    @property
    def lb_type(self) -> str:
        alb_type = "Unknown"
        if self.data['Type'] == 'application':
            alb_type = "ALB"
        elif self.data['Type'] == 'network':
            alb_type = "NLB"
        return alb_type

    @property
    def scheme(self) -> str:
        return self.data['Scheme']

    @property
    def hostname(self) -> str:
        return self.data['DNSName']

    # ------------------------------
    # Related objects
    # ------------------------------

    @property
    def listeners(self) -> Sequence["LoadBalancerListener"]:
        if 'listeners' not in self.cache:
            self.cache['listeners'] = LoadBalancerListener.objects.list(load_balancer=self.arn)
        return self.cache['listeners']

    @property
    def target_groups(self) -> Sequence["TargetGroup"]:
        if 'target_groups' not in self.cache:
            self.cache['target_groups'] = TargetGroup.objects.list(load_balancer=self.data['LoadBalancerArn'])
        return self.cache['target_groups']


class LoadBalancerListener(Model):

    objects = LoadBalancerListenerManager()

    # ---------------------
    # Model overrides
    # ---------------------

    @property
    def pk(self) -> str:
        return self.arn

    @property
    def name(self) -> str:
        return f'{self.port} ({self.protocol})'

    @property
    def arn(self) -> str:
        return self.data['ListenerArn']

    # ----------------------------------------
    # LoadBalancerListener-specific properties
    # ----------------------------------------

    @property
    def port(self) -> int:
        return self.data['Port']

    @property
    def protocol(self) -> str:
        return self.data['Protocol']

    @property
    def ssl_certificates(self) -> List[str]:
        return [c['CertificateArn'] for c in self.data.get('Certificates')]

    @property
    def ssl_policy(self) -> str:
        return self.data['SslPolicy']

    # ------------------------------
    # Related objects
    # ------------------------------

    @property
    def load_balancer(self) -> LoadBalancer:
        if 'load_balancer' not in self.cache:
            self.cache['load_balancer'] = LoadBalancer.objects.get(self.data['LoadBalancerArn'])
        return self.cache['load_balancer']

    @property
    def rules(self) -> Sequence["LoadBalancerListenerRule"]:
        if 'rules' not in self.cache:
            self.cache['rules'] = LoadBalancerListenerRule.objects.list(listener_arn=self.arn)
        return self.cache['rules']


class LoadBalancerListenerRule(Model):

    objects = LoadBalancerListenerRuleManager()

    def __init__(self, data: Dict[str, Any], listener_arn: str = None):
        super().__init__(data)
        self.listener_arn: Optional[str] = listener_arn

    # ---------------------
    # Model overrides
    # ---------------------

    @property
    def pk(self) -> str:
        return self.arn

    @property
    def name(self) -> str:
        return self.arn

    @property
    def arn(self) -> str:
        return self.data['RuleArn']

    # ------------------------------
    # Related objects
    # ------------------------------

    @property
    def load_balancer(self) -> LoadBalancer:
        if 'load_balancer' not in self.cache:
            self.cache['load_balancer'] = LoadBalancer.objects.get(self.data['LoadBalancerArn'])
        return self.cache['load_balancer']

    @property
    def listener(self) -> Optional[LoadBalancerListener]:
        if 'listener' not in self.cache and self.listener_arn:
            self.cache['listener'] = LoadBalancerListener.objects.get(self.listener_arn)
        else:
            self.cache['listener'] = None
        return self.cache['listener']

    @property
    def target_group(self) -> "TargetGroup":
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


class TargetGroup(Model):

    objects = TargetGroupManager()

    # ---------------------
    # Model overrides
    # ---------------------

    @property
    def pk(self) -> str:
        return self.arn

    @property
    def name(self) -> str:
        return self.data['TargetGroupName']

    @property
    def arn(self) -> str:
        return self.data['TargetGroupArn']

    # ----------------------------------------
    # TargetGroup-specific properties
    # ----------------------------------------

    @property
    def port(self) -> int:
        return self.data['Port']

    @property
    def protocol(self) -> str:
        return self.data['Protocol']

    # ------------------------------
    # Related objects
    # ------------------------------

    @property
    def load_balancers(self) -> Sequence[LoadBalancer]:
        if 'load_balancers' not in self.cache:
            self.cache['load_balancers'] = LoadBalancer.objects.get_many(self.data['LoadBalancerArns'])
        return self.cache['load_balancers']

    @property
    def rules(self) -> Sequence[LoadBalancerListenerRule]:
        """
        .. note::

            The dumb thing here is that you can't ask the target group itself
            what listener rules it is attached to -- you have to start at the
            load balancer, list all the listener rules that
        """
        if 'listener_rules' not in self.cache:
            self.cache['listener_rules'] = LoadBalancerListenerRule.objects.list(target_group_arn=self.arn)
        return self.cache['listener_rules']

    @property
    def listeners(self) -> Sequence[LoadBalancerListener]:
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
    def targets(self) -> Sequence["TargetGroupTarget"]:
        return TargetGroupTarget.objects.list(self.arn)


class TargetGroupTarget(Model):

    objects = TargetGroupTargetManager()

    # ---------------------
    # Model overrides
    # ---------------------

    @property
    def pk(self) -> str:
        return self.data['Id']

    @property
    def name(self) -> str:
        return self.pk

    @property
    def arn(self) -> None:
        return None

    # ----------------------------------------
    # TargetGroupTarget-specific properties
    # ----------------------------------------

    @property
    def port(self) -> int:
        return self.data['Port']

    @property
    def health(self) -> str:
        return self.data['TargetHealth']

    # ------------------------------
    # Related objects
    # ------------------------------

    @property
    def target(self) -> Instance:
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
    def target_group(self) -> TargetGroup:
        if 'target_group' not in self.cache:
            self.cache['target_group'] = TargetGroup.objects.get(self.data['TargetGroupArn'])
        return self.cache['target_group']
