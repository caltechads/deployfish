import builtins
import fnmatch
from collections.abc import Sequence
from typing import Any

from .abstract import Manager, Model
from .ec2 import Instance
from .mixins import TagsMixin

# ----------------------------------------
# Managers
# ----------------------------------------


class LoadBalancerManager(Manager):
    """
    Model load balancer manager behavior.
    """

    #: Service.
    service = "elbv2"

    def get(self, pk: str, **_) -> "LoadBalancer":
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
            msg = f"Got more than one load balancer when searching for pk={pk}"
            raise LoadBalancer.MultipleObjectsReturned(msg)
        return instances[0]

    def get_many(self, pks: list[str], **kwargs) -> Sequence["LoadBalancer"]:
        """
        Get many.

        Args:
            pks: pks.

        Keyword Args:
            kwargs: kwargs.

        Returns:
            Operation result.

        """
        arns = []
        names = []
        kwargs = {}
        for pk in pks:
            if pk.startswith("arn:"):
                arns.append(pk)
            else:
                names.append(pk)
        if names:
            kwargs["Names"] = names
        if arns:
            kwargs["LoadBalancerArns"] = arns
        paginator = self.client.get_paginator("describe_load_balancers")
        response_iterator = paginator.paginate(**kwargs)
        lbs = []
        try:
            for response in response_iterator:
                lbs.extend(response["LoadBalancers"])
        except self.client.exceptions.LoadBalancerNotFoundException as e:
            raise LoadBalancer.DoesNotExist(str(e)) from e
        return [LoadBalancer(lb) for lb in lbs]

    def list(
        self,
        vpc_id: str | None = None,
        lb_type: str = "any",
        scheme: str = "any",
        name: str | None = None,
    ) -> Sequence["LoadBalancer"]:
        """
        List.

        Args:
            vpc_id: vpc id.
            lb_type: lb type.
            scheme: scheme.
            name: name.

        Returns:
            Operation result.

        """
        paginator = self.client.get_paginator("describe_load_balancers")
        response_iterator = paginator.paginate()
        lb_data = []
        for response in response_iterator:
            lb_data.extend(response["LoadBalancers"])
        lbs = []
        for lb in lb_data:
            if name and not fnmatch.fnmatch(lb["LoadBalancerName"], name):
                continue
            if vpc_id and lb["VpcId"] != vpc_id:
                continue
            if scheme not in ["any", lb["Scheme"]]:
                continue
            if lb_type not in ["any", lb["Type"]]:
                continue
            lbs.append(LoadBalancer(lb))
        return lbs

    def get_tags(self, arn: str) -> builtins.list[dict[str, str]]:
        """
        Get tags.

        Args:
            arn: arn.

        Returns:
            Operation result.

        """
        try:
            response = self.client.describe_tags(ResourceArns=[arn])
        except self.client.exceptions.LoadBalancerNotFoundException as e:
            raise LoadBalancer.DoesNotExist(str(e)) from e
        return response["TagDescriptions"]["Tags"]


class LoadBalancerListenerManager(Manager):
    """
    Model load balancer listener manager behavior.
    """

    #: Service.
    service = "elbv2"

    def get(self, pk: str, **_) -> "LoadBalancerListener":
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
            response = self.client.describe_listeners(ListenerArns=[pk])
        except self.client.exceptions.ListenerNotFoundException as e:
            raise LoadBalancerListener.DoesNotExist(str(e)) from e
        return LoadBalancerListener(response["Listeners"][0])

    def list(self, load_balancer: str) -> Sequence["LoadBalancerListener"]:
        """
        List.

        Args:
            load_balancer: load balancer.

        Returns:
            Operation result.

        """
        paginator = self.client.get_paginator("describe_listeners")
        kwargs = {}
        if load_balancer:
            if not load_balancer.startswith("arn:"):
                # This is a load balancer name
                lb = LoadBalancer.objects.get(load_balancer)
                load_balancer = lb.arn
            kwargs["LoadBalancerArn"] = load_balancer
        response_iterator = paginator.paginate(**kwargs)
        listeners = []
        try:
            for response in response_iterator:
                listeners.extend(response["Listeners"])
        except self.client.exceptions.LoadBalancerNotFoundException as e:
            raise LoadBalancer.DoesNotExist(str(e)) from e
        return [LoadBalancerListener(listener) for listener in listeners]

    def get_tags(self, arn: str) -> builtins.list[dict[str, str]]:
        """
        Get tags.

        Args:
            arn: arn.

        Returns:
            Operation result.

        """
        try:
            response = self.client.describe_tags(ResourceArns=[arn])
        except self.client.exceptions.LoadBalancerNotFoundException as e:
            raise LoadBalancer.DoesNotExist(str(e)) from e
        return response["TagDescriptions"]["Tags"]


class LoadBalancerListenerRuleManager(Manager):
    """
    Model load balancer listener rule manager behavior.
    """

    #: Service.
    service = "elbv2"

    def __init__(self):
        """
        Initialize LoadBalancerListenerRuleManager.
        """
        super().__init__()
        #: Cache.
        self.cache: dict[str, dict[str, Any]] = {"load_balancers": {}}

    def get(self, pk: str, **_) -> "LoadBalancerListenerRule":
        """
        Get.

        Args:
            pk: pk.

        Keyword Args:
            _: .

        Returns:
            Operation result.

        """
        return self.get_many([pk])[0]

    def get_many(self, pks: list[str], **_) -> Sequence["LoadBalancerListenerRule"]:
        """
        Get many.

        Args:
            pks: pks.

        Keyword Args:
            _: .

        Returns:
            Operation result.

        """
        paginator = self.client.get_paginator("describe_rules")
        response_iterator = paginator.paginate(RuleArns=pks)
        rules = []
        for response in response_iterator:
            rules.extend(response["Rules"])
        return [LoadBalancerListenerRule(rule) for rule in rules]

    def __get_rules_for_load_balancer(
        self, load_balancer_pk: str
    ) -> Sequence["LoadBalancerListenerRule"]:
        """
        Handle get rules for load balancer.

        Args:
            load_balancer_pk: load balancer pk.

        Returns:
            Operation result.

        """
        if load_balancer_pk not in self.cache["load_balancers"]:
            lb = LoadBalancer.objects.get(load_balancer_pk)
            listener_arns = [listener.arn for listener in lb.listeners]
            rule_objects: list[LoadBalancerListenerRule] = []
            for arn in listener_arns:
                rule_objects.extend(self.list(listener_arn=arn))
            self.cache["load_balancers"][load_balancer_pk] = rule_objects
        return self.cache["load_balancers"][load_balancer_pk]

    def __get_rules_for_target_group(
        self, target_group_arn: str
    ) -> Sequence["LoadBalancerListenerRule"]:
        """
        Handle get rules for target group.

        Args:
            target_group_arn: target group arn.

        Returns:
            Operation result.

        """
        tg = TargetGroup.objects.get(target_group_arn)
        load_balancer_pk = tg.data["LoadBalancerArns"][0]
        rule_objects = self.__get_rules_for_load_balancer(load_balancer_pk)
        matched_rules = []
        for obj in rule_objects:
            for action in obj.data["Actions"]:
                if action["Type"] == "forward":
                    if action.get("TargetGroupArn") == target_group_arn:
                        matched_rules.append(obj)
                    elif "ForwardConfig" in action:
                        for target_group in action["ForwardConfig"]["TargetGroups"]:
                            if target_group["TargetGroupArn"] == target_group_arn:
                                matched_rules.append(obj)
                                break
        return matched_rules

    def list(
        self,
        listener_arn: str | None = None,
        load_balancer_pk: str | None = None,
        target_group_arn: str | None = None,
    ) -> Sequence["LoadBalancerListenerRule"]:
        """
        List.

        Args:
            listener_arn: listener arn.
            load_balancer_pk: load balancer pk.
            target_group_arn: target group arn.

        Returns:
            Operation result.

        """
        options = [listener_arn, load_balancer_pk, target_group_arn]
        if sum(x is not None for x in options) > 1:
            msg = (
                'Use only one of "listener_arn", "load_balancer_pk", '
                'or "target_group_arn".'
            )
            raise LoadBalancerListener.OperationFailed(msg)
        kwargs = {}
        rules: Sequence[LoadBalancerListenerRule] = []
        if target_group_arn:
            rules = self.__get_rules_for_target_group(target_group_arn)
        elif load_balancer_pk:
            rules = self.__get_rules_for_load_balancer(load_balancer_pk)
        elif listener_arn:
            kwargs["ListenerArn"] = listener_arn
            paginator = self.client.get_paginator("describe_rules")
            response_iterator = paginator.paginate(**kwargs)
            rules_data = []
            for response in response_iterator:
                rules_data.extend(response["Rules"])
            rules = [
                LoadBalancerListenerRule(d, listener_arn=listener_arn)
                for d in rules_data
            ]
        return rules

    def get_tags(self, arn: str) -> builtins.list[dict[str, str]]:
        """
        Get tags.

        Args:
            arn: arn.

        Returns:
            Operation result.

        """
        try:
            response = self.client.describe_tags(ResourceArns=[arn])
        except self.client.exceptions.LoadBalancerNotFoundException as e:
            raise LoadBalancer.DoesNotExist(str(e)) from e
        return response["TagDescriptions"]["Tags"]


class TargetGroupManager(Manager):
    """
    Model target group manager behavior.
    """

    #: Service.
    service = "elbv2"

    def get(self, pk: str, **_) -> "TargetGroup":
        """
        Get.

        Args:
            pk: pk.

        Keyword Args:
            _: .

        Returns:
            Operation result.

        """
        return self.get_many([pk])[0]

    def get_many(self, pks: list[str], **kwargs) -> Sequence["TargetGroup"]:
        """
        Get many.

        Args:
            pks: pks.

        Keyword Args:
            kwargs: kwargs.

        Returns:
            Operation result.

        """
        kwargs = {}
        for pk in pks:
            if pk.startswith("arn:"):
                if "TargetGroupArns" not in kwargs:
                    kwargs["TargetGroupArns"] = []
                kwargs["TargetGroupArns"].append(pk)
            else:
                if "Names" not in kwargs:
                    kwargs["Names"] = []
                kwargs["Names"].append(pk)
        paginator = self.client.get_paginator("describe_target_groups")
        response_iterator = paginator.paginate(**kwargs)
        tgs = []
        try:
            for response in response_iterator:
                tgs.extend(response["TargetGroups"])
        except self.client.exceptions.LoadBalancerNotFoundException as e:
            raise LoadBalancer.DoesNotExist(str(e)) from e
        except self.client.exceptions.TargetGroupNotFoundException as e:
            raise TargetGroup.DoesNotExist(str(e)) from e
        return [TargetGroup(tg) for tg in tgs]

    def list(self, load_balancer: str | None = None) -> Sequence["TargetGroup"]:
        """
        List.

        Args:
            load_balancer: load balancer.

        Returns:
            Operation result.

        """
        kwargs = {}
        if load_balancer:
            if not load_balancer.startswith("arn:"):
                # This is a load balancer name
                lb = LoadBalancer.objects.get(load_balancer)
                load_balancer = lb.arn
            kwargs["LoadBalancerArn"] = load_balancer
        paginator = self.client.get_paginator("describe_target_groups")
        response_iterator = paginator.paginate(**kwargs)
        tgs = []
        try:
            for response in response_iterator:
                tgs.extend(response["TargetGroups"])
        except self.client.exceptions.LoadBalancerNotFoundException as e:
            raise LoadBalancer.DoesNotExist(str(e)) from e
        return [TargetGroup(tg) for tg in tgs]

    def get_tags(self, arn: str) -> builtins.list[dict[str, str]]:
        """
        Get tags.

        Args:
            arn: arn.

        Returns:
            Operation result.

        """
        try:
            response = self.client.describe_tags(ResourceArns=[arn])
        except self.client.exceptions.LoadBalancerNotFoundException as e:
            raise LoadBalancer.DoesNotExist(str(e)) from e
        return response["TagDescriptions"]["Tags"]


class TargetGroupTargetManager(Manager):
    """
    Model target group target manager behavior.
    """

    #: Service.
    service = "elbv2"

    def list(self, target_group_arn: str) -> Sequence["TargetGroupTarget"]:
        """
        List.

        Args:
            target_group_arn: target group arn.

        Returns:
            Operation result.

        """
        try:
            response = self.client.describe_target_health(
                TargetGroupArn=target_group_arn
            )
        except self.client.exceptions.TargetGroupNotFoundException as e:
            msg = f'TargetGroup("{target_group_arn}") does not exist in AWS'
            raise TargetGroup.DoesNotExist(msg) from e
        targets = []
        for data in response["TargetHealthDescriptions"]:
            target_data = data["Target"]
            target_data["TargetHealth"] = data["TargetHealth"]
            target_data["HealthCheckPort"] = data["HealthCheckPort"]
            targets.append(TargetGroupTarget(target_data))
        return targets


# ----------------------------------------
# Models
# ----------------------------------------


class LoadBalancer(TagsMixin, Model):
    """
    Model load balancer behavior.
    """

    #: Manager for ELBv2 load balancer records.
    objects = LoadBalancerManager()

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
        return self.arn

    @property
    def name(self) -> str:
        """
        Name.

        Returns:
            Operation result.

        """
        return self.data["LoadBalancerName"]

    @property
    def arn(self) -> str:
        """
        Arn.

        Returns:
            Operation result.

        """
        return self.data["LoadBalancerArn"]

    # ---------------------------------
    # LoadBalancer-specific properties
    # ---------------------------------

    @property
    def lb_type(self) -> str:
        """
        Lb type.

        Returns:
            Operation result.

        """
        alb_type = "Unknown"
        if self.data["Type"] == "application":
            alb_type = "ALB"
        elif self.data["Type"] == "network":
            alb_type = "NLB"
        return alb_type

    @property
    def scheme(self) -> str:
        """
        Scheme.

        Returns:
            Operation result.

        """
        return self.data["Scheme"]

    @property
    def hostname(self) -> str:
        """
        Hostname.

        Returns:
            Operation result.

        """
        return self.data["DNSName"]

    # ------------------------------
    # Related objects
    # ------------------------------

    @property
    def listeners(self) -> Sequence["LoadBalancerListener"]:
        """
        Listeners.

        Returns:
            Operation result.

        """
        if "listeners" not in self.cache:
            self.cache["listeners"] = LoadBalancerListener.objects.list(
                load_balancer=self.arn
            )
        return self.cache["listeners"]

    @property
    def target_groups(self) -> Sequence["TargetGroup"]:
        """
        Target groups.

        Returns:
            Operation result.

        """
        if "target_groups" not in self.cache:
            self.cache["target_groups"] = TargetGroup.objects.list(
                load_balancer=self.data["LoadBalancerArn"]
            )
        return self.cache["target_groups"]


class LoadBalancerListener(Model):
    """
    Model load balancer listener behavior.
    """

    #: Manager for ELBv2 listener records.
    objects = LoadBalancerListenerManager()

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
        return self.arn

    @property
    def name(self) -> str:
        """
        Name.

        Returns:
            Operation result.

        """
        return f"{self.port} ({self.protocol})"

    @property
    def arn(self) -> str:
        """
        Arn.

        Returns:
            Operation result.

        """
        return self.data["ListenerArn"]

    # ----------------------------------------
    # LoadBalancerListener-specific properties
    # ----------------------------------------

    @property
    def port(self) -> int:
        """
        Port.

        Returns:
            Operation result.

        """
        return self.data["Port"]

    @property
    def protocol(self) -> str:
        """
        Protocol.

        Returns:
            Operation result.

        """
        return self.data["Protocol"]

    @property
    def ssl_certificates(self) -> list[str]:
        """
        Ssl certificates.

        Returns:
            Operation result.

        """
        return [c["CertificateArn"] for c in self.data.get("Certificates")]

    @property
    def ssl_policy(self) -> str:
        """
        Ssl policy.

        Returns:
            Operation result.

        """
        return self.data["SslPolicy"]

    # ------------------------------
    # Related objects
    # ------------------------------

    @property
    def load_balancer(self) -> LoadBalancer:
        """
        Load balancer.

        Returns:
            Operation result.

        """
        if "load_balancer" not in self.cache:
            self.cache["load_balancer"] = LoadBalancer.objects.get(
                self.data["LoadBalancerArn"]
            )
        return self.cache["load_balancer"]

    @property
    def rules(self) -> Sequence["LoadBalancerListenerRule"]:
        """
        Rules.

        Returns:
            Operation result.

        """
        if "rules" not in self.cache:
            self.cache["rules"] = LoadBalancerListenerRule.objects.list(
                listener_arn=self.arn
            )
        return self.cache["rules"]


class LoadBalancerListenerRule(Model):
    """
    Model load balancer listener rule behavior.

    Args:
        data: data.
        listener_arn: listener arn.

    """

    #: Manager for ELBv2 listener rule records.
    objects = LoadBalancerListenerRuleManager()

    def __init__(self, data: dict[str, Any], listener_arn: str | None = None) -> None:
        """
        Initialize LoadBalancerListenerRule.

        Args:
            data: data.
            listener_arn: listener arn.

        """
        super().__init__(data)
        #: Listener ARN used to recover parent listener when payload omits it.
        self.listener_arn: str | None = listener_arn

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
        return self.arn

    @property
    def name(self) -> str:
        """
        Name.

        Returns:
            Operation result.

        """
        return self.arn

    @property
    def arn(self) -> str:
        """
        Arn.

        Returns:
            Operation result.

        """
        return self.data["RuleArn"]

    # ------------------------------
    # Related objects
    # ------------------------------

    @property
    def load_balancer(self) -> LoadBalancer:
        """
        Load balancer.

        Returns:
            Operation result.

        """
        if "load_balancer" not in self.cache:
            self.cache["load_balancer"] = LoadBalancer.objects.get(
                self.data["LoadBalancerArn"]
            )
        return self.cache["load_balancer"]

    @property
    def listener(self) -> LoadBalancerListener | None:
        """
        Listener.

        Returns:
            Operation result.

        """
        if "listener" not in self.cache and self.listener_arn:
            self.cache["listener"] = LoadBalancerListener.objects.get(self.listener_arn)
        else:
            self.cache["listener"] = None
        return self.cache["listener"]

    @property
    def target_group(self) -> "TargetGroup":
        """
        .. note::

            Deployfish assumes relevant target group is attached to first
            ``forward`` action on rule and does not model weighted
            ``ForwardConfig`` target-group lists.

            If one rule forwards to multiple services later, this lookup must
            become more precise.

        Returns:
            Operation result.

        """
        if "target_group" not in self.cache:
            target_group = None
            for action in self.data["Actions"]:
                if action["Type"] == "forward":
                    target_group = TargetGroup.objects.get(action["TargetGroupArn"])
            self.cache["target_group"] = target_group
        return self.cache["target_group"]


class TargetGroup(Model):
    """
    Model target group behavior.
    """

    #: Manager for ELBv2 target group records.
    objects = TargetGroupManager()

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
        return self.arn

    @property
    def name(self) -> str:
        """
        Name.

        Returns:
            Operation result.

        """
        return self.data["TargetGroupName"]

    @property
    def arn(self) -> str:
        """
        Arn.

        Returns:
            Operation result.

        """
        return self.data["TargetGroupArn"]

    # ----------------------------------------
    # TargetGroup-specific properties
    # ----------------------------------------

    @property
    def port(self) -> int:
        """
        Port.

        Returns:
            Operation result.

        """
        return self.data["Port"]

    @property
    def protocol(self) -> str:
        """
        Protocol.

        Returns:
            Operation result.

        """
        return self.data["Protocol"]

    # ------------------------------
    # Related objects
    # ------------------------------

    @property
    def load_balancers(self) -> Sequence[LoadBalancer]:
        """
        Load balancers.

        Returns:
            Operation result.

        """
        if "load_balancers" not in self.cache:
            self.cache["load_balancers"] = LoadBalancer.objects.get_many(
                self.data["LoadBalancerArns"]
            )
        return self.cache["load_balancers"]

    @property
    def rules(self) -> Sequence[LoadBalancerListenerRule]:
        """
        .. note::

            The dumb thing here is that you can't ask the target group itself
            what listener rules it is attached to -- you have to start at the
            load balancer, list all the listener rules that

        Returns:
            Operation result.

        """
        if "listener_rules" not in self.cache:
            self.cache["listener_rules"] = LoadBalancerListenerRule.objects.list(
                target_group_arn=self.arn
            )
        return self.cache["listener_rules"]

    @property
    def listeners(self) -> Sequence[LoadBalancerListener]:
        """
        Listeners.

        Returns:
            Operation result.

        """
        if "listeners" not in self.cache:
            listeners = {}
            # First extract the listeners from any rules we have
            for rule in self.rules:
                listeners[rule.listener_arn] = rule.listener
            # Now look through all the listeners on our load balancers to see
            # if we're the default action on any of them
            for lb in self.load_balancers:
                for listener in lb.listeners:
                    if "DefaultActions" in listener.data:
                        for action in listener.data["DefaultActions"]:
                            if (
                                action["Type"] == "forward"
                                and "TargetGroupArn" in action
                            ):
                                listeners[listener.arn] = listener
            self.cache["listeners"] = list(listeners.values())
        return self.cache["listeners"]

    @property
    def targets(self) -> Sequence["TargetGroupTarget"]:
        """
        Targets.

        Returns:
            Operation result.

        """
        return TargetGroupTarget.objects.list(self.arn)


class TargetGroupTarget(Model):
    """
    Model target group target behavior.
    """

    #: Objects.
    objects = TargetGroupTargetManager()

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
        return self.data["Id"]

    @property
    def name(self) -> str:
        """
        Name.

        Returns:
            Operation result.

        """
        return self.pk

    @property
    def arn(self) -> None:
        """
        Arn.
        """
        return None

    # ----------------------------------------
    # TargetGroupTarget-specific properties
    # ----------------------------------------

    @property
    def port(self) -> int:
        """
        Port.

        Returns:
            Operation result.

        """
        return self.data["Port"]

    @property
    def health(self) -> str:
        """
        Health.

        Returns:
            Operation result.

        """
        return self.data["TargetHealth"]

    # ------------------------------
    # Related objects
    # ------------------------------

    @property
    def target(self) -> Instance:
        """
        Target.

        Returns:
            Operation result.

        """
        if "target" not in self.cache:
            if self.data["Id"].startswith("i-"):
                # this is an instance
                self.cache["target"] = Instance.objects.get(self.data["Id"])
            else:
                msg = (
                    f'TargetGroupTarget("{self.pk}"): currently cannot '
                    "dereference targets of this type"
                )
                raise self.OperationFailed(msg)
        return self.cache["target"]

    @property
    def target_group(self) -> TargetGroup:
        """
        Target group.

        Returns:
            Operation result.

        """
        if "target_group" not in self.cache:
            self.cache["target_group"] = TargetGroup.objects.get(
                self.data["TargetGroupArn"]
            )
        return self.cache["target_group"]
