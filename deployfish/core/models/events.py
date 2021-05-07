from copy import copy

from .abstract import Manager, Model


# ----------------------------------------
# Managers
# ----------------------------------------

class EventTargetManager(Manager):

    service = 'events'

    def get(self, pk, rule=None):
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
                'No EventTarget for name="{}" in AWS on EventScheduleRule(pk="{}")'.format(pk, pk)
            )
        return EventTarget(data, rule=rule.data)

    def list(self, rule=None):
        response = self.client.list_targets_by_rule(Rule=rule.pk)
        targets = []
        for target in response['Targets']:
            targets.append(EventTarget(target, rule=rule))
        return targets

    def delete(self, obj):
        self.client.remove_targets(Rule=obj.rule.pk, Ids=[obj.pk])

    def save(self, obj):
        self.client.put_targets(Rule=obj.rule.pk, Targets=[obj.render()])


class EventScheduleRuleManager(Manager):

    service = 'events'

    def get(self, pk):
        if not pk.startswith('deployfish-'):
            pk = 'deployfish-' + pk
        response = self.client.list_rules(NamePrefix=pk, Limit=1)
        if not response['Rules']:
            raise EventScheduleRule.DoesNotExist(
                'No EventScheduleRule for name="{}" exists in AWS'.format(pk)
            )
        else:
            data = response['Rules'][0]
        rule = EventScheduleRule(data)
        rule.target = EventTarget.objects.get(pk, rule=rule)
        return rule

    def list(self):
        paginator = self.client.get_paginator('list_rules')
        response_iterator = paginator.paginate(NamePrefix="deployfish-")
        rules = []
        for response in response_iterator:
            for data in response['Rules']:
                rule = EventScheduleRule(data)
                rule.target = EventTarget.objects.get(rule.pk, rule=rule)
                rules.append(rule)
        return rules

    def save(self, obj):
        if self.exists(obj.pk):
            for target in EventTarget.objects.list(rule=obj):
                EventTarget.objects.delete(target)
        response = self.client.put_rule(**obj.render())
        if obj.target:
            obj.target.save()
        return response['RuleArn']

    def delete(self, obj):
        if self.exists(obj.pk):
            for target in EventTarget.objects.list(rule=obj):
                EventTarget.objects.delete(target)
            self.client.delete_rule(Name=obj.pk)


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
    def new(cls, obj, source, rule=None):
        data, kwargs = cls.adapt(obj, source)
        return cls(data, rule=rule)

    def __init__(self, data, rule=None):
        super(EventTarget, self).__init__(data)
        self.rule = rule

    @property
    def pk(self):
        return self.data['Id']

    @property
    def name(self):
        return self.data['Id']

    @property
    def arn(self):
        return self.data['Arn']

    def delete(self):
        if not self.rule:
            raise self.ImproperlyConfigured(
                'EventTarget({}) has no EventScheduleRule asociated with it.  Assign one with target.rule = rule'
            )
        self.objects.delete(self.pk, rule=self.rule)

    def save(self):
        """
        Save ourselves as a Cloudwatch Events Rule target.

        :rtype: dict
        """
        if not self.rule:
            raise self.ImproperlyConfigured(
                'EventTarget({}) has no EventScheduleRule associated with it.  Assign one with target.rule = rule'
            )
        super(EventTarget, self).save()

    def set_task_definition_arn(self, arn):
        self.data['EcsParameters']['TaskDefinitionArn'] = arn


class EventScheduleRule(Model):
    """
    An EventScheduleRule is an AWS cron job.  We use them to run ECS tasks periodically.

    If the task has a schedule defined, manage an ECS cloudwatch event with the corresponding
    schedule, with the task as an event target.
    """

    objects = EventScheduleRuleManager()

    @classmethod
    def new(cls, obj, source):
        rule = super(EventScheduleRule, cls).new(obj, source)
        rule.target = EventTarget.new(obj, source, rule=rule)
        return rule

    def __init__(self, data):
        super(EventScheduleRule, self).__init__(data)
        self.target = None

    @property
    def pk(self):
        return self.data['Name']

    @property
    def name(self):
        return self.data['Name']

    @property
    def arn(self):
        return self.data['Arn']

    def set_task_definition_arn(self, arn):
        self.target.set_task_definition_arn(arn)

    def render_for_diff(self):
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
