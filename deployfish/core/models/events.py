from copy import copy
from typing import Optional, Sequence, cast, Dict, Any

from .abstract import Manager, Model


# ----------------------------------------
# Managers
# ----------------------------------------

class EventTargetManager(Manager):

    service = 'events'

    def get(self, pk: str, **kwargs) -> "EventTarget":
        rule: Optional['EventScheduleRule'] = kwargs.get('rule', None)
        if not rule:
            raise ValueError('"rule" kwarg is required')
        if not pk.startswith('deployfish-'):
            pk = 'deployfish-' + pk
        response = self.client.list_targets_by_rule(Rule=rule.pk)
        data = {}
        for target in response['Targets']:
            if target['Id'] == pk:
                data = target
                break
        if not data:
            raise EventTarget.DoesNotExist(
                f'No EventTarget for name="{pk}" in AWS on EventScheduleRule(pk="{rule.pk}")'
            )
        return EventTarget(data, rule=rule.data)

    def list(self, rule: "EventScheduleRule") -> Sequence["EventTarget"]:
        response = self.client.list_targets_by_rule(Rule=rule.pk)
        targets = []
        for target in response['Targets']:
            targets.append(EventTarget(target, rule=rule))
        return targets

    def delete(self, obj: Model, **_) -> None:
        obj = cast("EventTarget", obj)
        if obj.rule:
            self.client.remove_targets(Rule=obj.rule.pk, Ids=[obj.pk])

    def save(self, obj: Model, **_) -> None:
        obj = cast("EventTarget", obj)
        if obj.rule:
            self.client.put_targets(Rule=obj.rule.pk, Targets=[obj.render()])


class EventScheduleRuleManager(Manager):

    service = 'events'

    def get(self, pk: str, **_) -> "EventScheduleRule":
        if not pk.startswith('deployfish-'):
            pk = 'deployfish-' + pk
        response = self.client.list_rules(NamePrefix=pk, Limit=1)
        if not response['Rules']:
            raise EventScheduleRule.DoesNotExist(
                'No EventScheduleRule for name="{}" exists in AWS'.format(pk)
            )
        data = response['Rules'][0]
        rule = EventScheduleRule(data)
        rule.target = EventTarget.objects.get(pk, rule=rule)
        return rule

    def list(self) -> Sequence['EventScheduleRule']:
        paginator = self.client.get_paginator('list_rules')
        response_iterator = paginator.paginate(NamePrefix="deployfish-")
        rules = []
        for response in response_iterator:
            for data in response['Rules']:
                rule = EventScheduleRule(data)
                rule.target = EventTarget.objects.get(rule.pk, rule=rule)
                rules.append(rule)
        return rules

    def save(self, obj: Model, **_) -> str:
        obj = cast("EventScheduleRule", obj)
        if self.exists(obj.pk):
            for target in EventTarget.objects.list(obj):
                EventTarget.objects.delete(target)
        response = self.client.put_rule(**obj.render())
        if obj.target:
            obj.target.save()
        return response['RuleArn']

    def delete(self, obj: Model, **_) -> None:
        obj = cast("EventScheduleRule", obj)
        if self.exists(obj.pk):
            for target in EventTarget.objects.list(obj):
                EventTarget.objects.delete(target)
            self.client.delete_rule(Name=obj.pk)

    def enable(self, obj: "EventScheduleRule") -> None:
        """
        If `obj` is disabled, change its state of 'ENABLED'. Otherwise, do nothing.

        :param obj EventScheduleRule: the rule to enable
        """
        if not obj.enabled:
            self.client.enable_rule(
                Name=obj.name,
                EventBusName=obj.data['EventBusName']
            )

    def disable(self, obj: "EventScheduleRule") -> None:
        """
        If `obj` is enabled, change the its state to 'DISABLED'. Otherwise, do nothing.

        :param obj EventScheduleRule: the rule to disable
        """
        if obj.enabled:
            self.client.disable_rule(
                Name=obj.name,
                EventBusName=obj.data['EventBusName']
            )


# ----------------------------------------
# Models
# ----------------------------------------

class EventTarget(Model):
    """
    self.data here has the same structure as what is returned by client('events').list_targets_for_rule():

        {
            'Id': 'string',
            'Arn': 'string',                    # Note: this is the CLUSTER Arn, not the Target arn
            'RoleArn': 'string',
            'Input': 'string',
            'InputPath': 'string',
            'EcsParameters': {
                'TaskDefinitionArn': 'string',
                'TaskCount': 123,
                'LaunchType': 'EC2'|'FARGATE',
                'NetworkConfiguration': {
                    'awsvpcConfiguration': {
                        'Subnets': [
                            'string',
                        ],
                        'SecurityGroups': [
                            'string',
                        ],
                        'AssignPublicIp': 'ENABLED'|'DISABLED'
                    }
                },
                'PlatformVersion': 'string',
                'Group': 'string'
            },
        }
    """

    objects = EventTargetManager()

    @classmethod
    def new(cls, obj: Dict[str, Any], source: str, **kwargs) -> "EventTarget":
        rule: Optional["EventScheduleRule"] = kwargs.get('rule', None)
        data, kwargs = cls.adapt(obj, source)
        return cls(data, rule=rule)

    def __init__(self, data: Dict[str, Any], rule: "EventScheduleRule" = None):
        super().__init__(data)
        self.rule: Optional["EventScheduleRule"] = rule

    # ---------------------
    # Model overrides
    # ---------------------

    @property
    def pk(self) -> str:
        return self.data['Id']

    @property
    def name(self) -> str:
        return self.data['Id']

    @property
    def arn(self) -> str:
        return self.data['Arn']

    def save(self) -> None:
        """
        Save ourselves as a Cloudwatch Events Rule target.

        :rtype: dict
        """
        if not self.rule:
            raise self.ImproperlyConfigured(
                'EventTarget({}) has no EventScheduleRule associated with it.  Assign one with target.rule = rule'
            )
        super().save()

    def delete(self) -> None:
        if not self.rule:
            raise self.ImproperlyConfigured(
                'EventTarget({}) has no EventScheduleRule asociated with it.  Assign one with target.rule = rule'
            )
        self.objects.delete(self, rule=self.rule)

    # ----------------------------
    # EventTarget-specific actions
    # ----------------------------

    def set_task_definition_arn(self, arn: str) -> None:
        self.data['EcsParameters']['TaskDefinitionArn'] = arn


class EventScheduleRule(Model):
    """
    An EventScheduleRule is an AWS cron job.  We use them to run ECS tasks periodically.

    If the task has a schedule defined, manage an ECS cloudwatch event with the corresponding
    schedule, with the task as an event target.
    """

    objects = EventScheduleRuleManager()

    @classmethod
    def new(cls, obj: Dict[str, Any], source: str, **_) -> "EventScheduleRule":
        rule = super().new(obj, source)
        rule = cast("EventScheduleRule", rule)
        rule.target = EventTarget.new(obj, source, rule=rule)
        return rule

    def __init__(self, data):
        super().__init__(data)
        self.target = None

    # ---------------------
    # Model overrides
    # ---------------------

    @property
    def pk(self) -> str:
        return self.data['Name']

    @property
    def name(self) -> str:
        return self.data['Name']

    @property
    def arn(self) -> str:
        return self.data['Arn']

    def render_for_diff(self) -> Dict[str, Any]:
        """

        .. note::

            Ideally here we would compare the full task definition attached to the EventTarget via its taskDefinitionArn
            to the task definition we have in deployfish.yml.
        """
        data = copy(self.data)
        data['Target'] = {}
        if self.target:
            data['Target'] = self.target.render_for_diff()
            if 'taskDefinitionArn' in data['Target']:
                del data['Target']['taskDefinitionArn']
        return data

    # -------------------------------------
    # EventScheduleRule-specific properties
    # -------------------------------------

    @property
    def enabled(self) -> bool:
        return self.data['State'] == 'ENABLED'

    # ----------------------------------
    # EventScheduleRule-specific actions
    # ----------------------------------

    def set_task_definition_arn(self, arn: str) -> None:
        self.target.set_task_definition_arn(arn)

    def enable(self):
        self.objects.enable(self)
        self.reload_from_db()

    def disable(self):
        self.objects.disable(self)
        self.reload_from_db()
