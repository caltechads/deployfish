from collections.abc import Sequence
from copy import copy
from typing import Any, cast

from .abstract import Manager, Model

# ----------------------------------------
# Managers
# ----------------------------------------


class EventTargetManager(Manager):
    """
    Model event target manager behavior.
    """

    #: Service.
    service = "events"

    def get(self, pk: str, **kwargs) -> "EventTarget":
        """
        Get.

        Args:
            pk: pk.

        Keyword Args:
            kwargs: kwargs.

        Returns:
            Operation result.

        """
        rule: EventScheduleRule | None = kwargs.get("rule")
        if not rule:
            msg = '"rule" kwarg is required'
            raise ValueError(msg)
        if not pk.startswith("deployfish-"):
            pk = "deployfish-" + pk
        response = self.client.list_targets_by_rule(Rule=rule.pk)
        data = {}
        for target in response["Targets"]:
            if target["Id"] == pk:
                data = target
                break
        if not data:
            msg = (
                f'No EventTarget for name="{pk}" in AWS on '
                f'EventScheduleRule(pk="{rule.pk}")'
            )
            raise EventTarget.DoesNotExist(msg)
        return EventTarget(data, rule=rule.data)

    def list(self, rule: "EventScheduleRule") -> Sequence["EventTarget"]:
        """
        List.

        Args:
            rule: rule.

        Returns:
            Operation result.

        """
        response = self.client.list_targets_by_rule(Rule=rule.pk)
        return [EventTarget(target, rule=rule) for target in response["Targets"]]

    def delete(self, obj: Model, **_) -> None:
        """
        Delete.

        Args:
            obj: obj.

        Keyword Args:
            _: .

        """
        obj = cast("EventTarget", obj)
        if obj.rule:
            self.client.remove_targets(Rule=obj.rule.pk, Ids=[obj.pk])

    def save(self, obj: Model, **_) -> None:
        """
        Save.

        Args:
            obj: obj.

        Keyword Args:
            _: .

        """
        obj = cast("EventTarget", obj)
        if obj.rule:
            self.client.put_targets(Rule=obj.rule.pk, Targets=[obj.render()])


class EventScheduleRuleManager(Manager):
    """
    Model event schedule rule manager behavior.
    """

    #: Service.
    service = "events"

    def get(self, pk: str, **_) -> "EventScheduleRule":
        """
        Get.

        Args:
            pk: pk.

        Keyword Args:
            _: .

        Returns:
            Operation result.

        """
        if not pk.startswith("deployfish-"):
            pk = "deployfish-" + pk
        response = self.client.list_rules(NamePrefix=pk, Limit=1)
        if not response["Rules"]:
            msg = f'No EventScheduleRule for name="{pk}" exists in AWS'
            raise EventScheduleRule.DoesNotExist(msg)
        data = response["Rules"][0]
        rule = EventScheduleRule(data)
        rule.target = EventTarget.objects.get(pk, rule=rule)
        return rule

    def list(self) -> Sequence["EventScheduleRule"]:
        """
        List.

        Returns:
            Operation result.

        """
        paginator = self.client.get_paginator("list_rules")
        response_iterator = paginator.paginate(NamePrefix="deployfish-")
        rules = []
        for response in response_iterator:
            for data in response["Rules"]:
                rule = EventScheduleRule(data)
                rule.target = EventTarget.objects.get(rule.pk, rule=rule)
                rules.append(rule)
        return rules

    def save(self, obj: Model, **_) -> str:
        """
        Save.

        Args:
            obj: obj.

        Keyword Args:
            _: .

        Returns:
            Operation result.

        """
        obj = cast("EventScheduleRule", obj)
        if self.exists(obj.pk):
            for target in EventTarget.objects.list(obj):
                EventTarget.objects.delete(target)
        response = self.client.put_rule(**obj.render())
        if obj.target:
            obj.target.save()
        return response["RuleArn"]

    def delete(self, obj: Model, **_) -> None:
        """
        Delete.

        Args:
            obj: obj.

        Keyword Args:
            _: .

        """
        obj = cast("EventScheduleRule", obj)
        if self.exists(obj.pk):
            for target in EventTarget.objects.list(obj):
                EventTarget.objects.delete(target)
            self.client.delete_rule(Name=obj.pk)

    def enable(self, obj: "EventScheduleRule") -> None:
        """
        If ``obj`` is disabled, change its state of "ENABLED". Otherwise, do nothing.

        Args:
            obj: the rule to enable

        """
        if not obj.enabled:
            self.client.enable_rule(
                Name=obj.name, EventBusName=obj.data["EventBusName"]
            )

    def disable(self, obj: "EventScheduleRule") -> None:
        """
        If ``obj`` is enabled, change the its state to "DISABLED". Otherwise, do
        nothing.

        Args:
            obj: the rule to disable

        """
        if obj.enabled:
            self.client.disable_rule(
                Name=obj.name, EventBusName=obj.data["EventBusName"]
            )


# ----------------------------------------
# Models
# ----------------------------------------


class EventTarget(Model):
    """
    :py:attr:`data` here has the same structure as what is returned by

    Args:
        data: data.
        rule: rule.

    """

    #: Manager for EventBridge rule targets.
    objects = EventTargetManager()

    @classmethod
    def new(cls, obj: dict[str, Any], source: str, **kwargs) -> "EventTarget":
        """
        New.

        Args:
            obj: obj.
            source: source.

        Keyword Args:
            kwargs: kwargs.

        Returns:
            Operation result.

        """
        rule: EventScheduleRule | None = kwargs.get("rule")
        data, kwargs = cls.adapt(obj, source)
        return cls(data, rule=rule)

    def __init__(
        self, data: dict[str, Any], rule: "EventScheduleRule | None" = None
    ) -> None:
        """
        Initialize EventTarget.

        Args:
            data: data.
            rule: rule.

        """
        super().__init__(data)
        #: Schedule rule that owns this target, if assigned.
        self.rule: EventScheduleRule | None = rule

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
        return self.data["Id"]

    @property
    def arn(self) -> str:
        """
        Arn.

        Returns:
            Operation result.

        """
        return self.data["Arn"]

    def save(self) -> None:
        """
        Save ourselves as a Cloudwatch Events Rule target.

        :rtype: dict
        """
        if not self.rule:
            msg = (
                "EventTarget({}) has no EventScheduleRule associated with it. "
                "Assign one with target.rule = rule"
            )
            raise self.ImproperlyConfigured(msg)
        super().save()

    def delete(self) -> None:
        """
        Delete.
        """
        if not self.rule:
            msg = (
                "EventTarget({}) has no EventScheduleRule associated with it. "
                "Assign one with target.rule = rule"
            )
            raise self.ImproperlyConfigured(msg)
        self.objects.delete(self, rule=self.rule)

    # ----------------------------
    # EventTarget-specific actions
    # ----------------------------

    def set_task_definition_arn(self, arn: str) -> None:
        """
        Set task definition arn.

        Args:
            arn: arn.

        """
        self.data["EcsParameters"]["TaskDefinitionArn"] = arn


class EventScheduleRule(Model):
    """
    AWS cron job that deployfish uses to run ECS tasks periodically.

    Args:
        data: data.

    """

    #: Manager for EventBridge schedule rules.
    objects = EventScheduleRuleManager()

    @classmethod
    def new(cls, obj: dict[str, Any], source: str, **_) -> "EventScheduleRule":
        """
        New.

        Args:
            obj: obj.
            source: source.

        Keyword Args:
            _: .

        Returns:
            Operation result.

        """
        rule = super().new(obj, source)
        rule = cast("EventScheduleRule", rule)
        rule.target = EventTarget.new(obj, source, rule=rule)
        return rule

    def __init__(self, data: dict[str, Any]) -> None:
        """
        Initialize EventScheduleRule.

        Args:
            data: data.

        """
        super().__init__(data)
        #: Target ECS task configuration associated with this rule, if any.
        self.target: EventTarget | None = None

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
        return self.data["Name"]

    @property
    def name(self) -> str:
        """
        Name.

        Returns:
            Operation result.

        """
        return self.data["Name"]

    @property
    def arn(self) -> str:
        """
        Arn.

        Returns:
            Operation result.

        """
        return self.data["Arn"]

    def render_for_diff(self) -> dict[str, Any]:
        """
        .. note::

            Ideally here we would compare the full task definition attached to
            the :py:class:`EventTarget` via its ``taskDefinitionArn`` to the
            task definition we have in deployfish.yml.

        Returns:
            Operation result.

        """
        data = copy(self.data)
        data["Target"] = {}
        if self.target:
            data["Target"] = self.target.render_for_diff()
            if "taskDefinitionArn" in data["Target"]:
                del data["Target"]["taskDefinitionArn"]
        return data

    # -------------------------------------
    # EventScheduleRule-specific properties
    # -------------------------------------

    @property
    def enabled(self) -> bool:
        """
        Enabled.

        Returns:
            Operation result.

        """
        return self.data["State"] == "ENABLED"

    # ----------------------------------
    # EventScheduleRule-specific actions
    # ----------------------------------

    def set_task_definition_arn(self, arn: str) -> None:
        """
        Set task definition arn.

        Args:
            arn: arn.

        """
        if self.target is None:
            msg = f'EventScheduleRule("{self.pk}") has no target configured'
            raise self.ImproperlyConfigured(msg)
        self.target.set_task_definition_arn(arn)

    def enable(self) -> None:
        """
        Enable.
        """
        self.objects.enable(self)
        self.reload_from_db()

    def disable(self) -> None:
        """
        Disable.
        """
        self.objects.disable(self)
        self.reload_from_db()
