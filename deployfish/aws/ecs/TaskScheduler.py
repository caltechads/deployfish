"""
Use the boto3 Target dict structure for intermediate storage.

"""

from copy import copy

from jsondiff import diff

from deployfish.aws import get_boto3_session
from .task_defniition import TaskDefinition


# ----------------------------------------
# Adapters
# ----------------------------------------

class DeployfishYamlTaskEventTargetAdapter(object):

    class ClusterDoesNotExist(Exception):
        pass

    def __init__(self, yaml):
        self.yaml = yaml

    def get_schedule_target_id(self, name):
        return EventTarget.event_target_pattern.format(self.yaml['name'])

    def get_cluster_arn(self):
        kwargs = {}
        if self.yaml['cluster_name'] != 'default':
            kwargs['clusters'] = [self.yaml['cluster_name']]
        response = self.ecs.describe_clusters(**kwargs)
        if response['clusters']:
            return response['clusters'][0]['clusterArn']
        else:
            raise self.ClusterDoesNotExist(
                'ECS Cluster "{}" does not exist in AWS'.format(self.yaml['cluster_name'])
            )

    def get_vpc_configuration(self):
        data = {}
        source = self.yaml.get('vpc_configuration', None)
        if source:
            data['subnets'] = source['subnets']
            if 'security_groups' in source:
                data['securityGroups'] = source['security_groups']
            if 'public_ip' in source:
                data['assignPublicIp'] = 'ENABLED' if source['public_ip'] else 'DISABLED'
        return data

    def convert(self):
        data = {}
        data['Id'] = self.get_schedule_target_id()
        data['Arn'] = self.get_cluster_arn(self)
        data['RoleArn'] = self.yaml['schedule_role']
        ecs = {}
        ecs['TaskCount'] = self.yaml.get('count', 1)
        ecs['LaunchType'] = self.yaml.get('launch_type', 'EC2')
        if ecs['launchType'] == 'FARGATE':
            vpc_configuration = self.get_vpc_configuration()
            if vpc_configuration:
                ecs['networkConfiguration'] = {}
                ecs['networkConfiguration']['awsVpcConfiguration'] = vpc_configuration
            ecs['PlatformVersion'] = self.task.platform_version
        if self.task.group:
            ecs['Group'] = self.task.group
        data['EcsParameters'] = ecs
        return data


class DeployfishYamlTaskEventScheduleRuleAdapter(object):

    def __init__(self, yaml):
        self.yaml = yaml

    @property
    def rule_id(self):
        return EventScheduleRule.event_rule_pattern.format(self.task.taskName)

    def convert(self):
        data = {}
        data['Name'] = EventScheduleRuleManager.event_rule_patter.format(self.yaml['name'])
        data['ScheduleExpression'] = self.yaml['schedule_expression']
        data['State'] = 'ENABLED',
        data['EventPattern'] = None
        data['Description'] = 'Scheduler for task: {}'.format(self.yaml['name'])
        data['RoleArn'] = None
        return self.yaml['name'], data


# ----------------------------------------
# Managers
# ----------------------------------------

class EventTargetManager(object):

    event_target_pattern = "{}-scheduler-target"

    def __init__(self):
        self.client = get_boto3_session().client('events')

    def target_id(self, name):
        return self.event_target_pattern.format(name)

    def get(self, rule, name):
        response = self.client.list_targets_by_rule(Rule=rule.name)
        data = {}
        for target in response['Targets']:
            if target['Id'] == self.target_id(name):
                data = target
                break
        if not data:
            raise EventTarget.DoesNotExist(
                'No EventTarget for name="{}" exists in AWS'.format(name)
            )
        return EventTarget(data, rule=rule.data)


class EventScheduleRuleManager(object):

    event_rule_pattern = "{}-scheduler"

    def __init__(self, task):
        self.client = get_boto3_session().client('events')

    def rule_id(self, name):
        return self.event_rule_pattern.format(name)

    def get(self, name):
        response = self.client.list_rules(NamePrefix=self.rule_id(name), Limit=1)
        if not response['Rules']:
            raise EventScheduleRule.DoesNotExist(
                'No EventScheduleRule for name="{}" exists in AWS'.format(name)
            )
        else:
            data = response['Rules'][0]
        rule = EventScheduleRule(data)
        rule.target = EventTargetManager().get(rule, name)
        return rule

    @property
    def exists(self, name):
        try:
            rule = self.get(name)
        except EventScheduleRule.DoesNotExist:
            return False
        except EventTarget.DoesNotExist:
            raise EventScheduleRule.ImproperlyConfigured(
                'Live EventScheduleRule("{}") has no targets!'.format(rule.rule_id)
            )

    def diff(self, rule):  # noqa:F811
        aws_rule = self.get(rule)
        return rule.diff(aws_rule)

    def needs_update(self, rule):
        return self.diff(rule) != {}

    def save(self, rule):
        """
        Create or update an existing AWS Cloudwatch event rule with the task as the target.
        """
        self.desired_rule.save()

    def delete(self):
        """
        Delete the AWS Cloudwatch event rule, with any existing targets.
        """
        if self.active_rule.populated:
            self.active_rule.delete()


# ----------------------------------------
# Models
# ----------------------------------------

class EventTarget(object):
    """
    self.data here has the same structure as what is returned by client('events').list_targets_for_rule():

        {
            'Id': 'string',
            'Arn': 'string',
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

    event_target_pattern = "{}-scheduler-target"
    adapters = {
        'deployfish.yml': DeployfishYamlTaskEventTargetAdapter,
    }

    objects = EventTargetManager()

    class ImproperlyConfigured(Exception):
        pass

    class DoesNotExist(Exception):
        pass

    @classmethod
    def new(cls, obj, source, rule=None, task_definition=None):
        data = cls.adapters[source](obj).convert()
        return cls(data, task_definition, rule=rule)

    def __init__(self, data, task_definition, rule=None):
        self.client = get_boto3_session().client('events')
        self.data = data
        self.task_definition = task_definition
        self.rule = rule

    @property
    def name(self):
        return self.data['Id']

    @property
    def populated(self):
        return self.data != {}

    def delete(self):
        if not self.rule:
            raise self.ImproperlyConfigured(
                'EventTarget({}) has no schedule rule asociated with it.  Assign one with target.rule = rule'
            )

        self.client.remove_targets(Rule=self.rule['Name'], Ids=[self.data['Id']])

    def save(self):
        """
        Save ourselves as a Cloudwatch Events Rule target.

        :rtype: dict
        """
        if not self.rule:
            raise self.ImproperlyConfigured(
                'ScheduleTarget({}) has no schedule rule asociated with it.  Assign one with target.rule = rule'
            )
        self.client.put_targets(Rule=self.rule['Name'], Targets=[self.data])

    def __eq__(self, other):
        if self.__class__ != other.__class__:
            return False
        return self.data == other.data


class EventScheduleRule(object):
    """
    If the task has a schedule defined, manage an ECS cloudwatch event with the corresponding
    schedule, with the task as an event target.
    """

    event_rule_pattern = "{}-scheduler"
    adapters = {
        'deployfish.yml': DeployfishYamlTaskEventScheduleRuleAdapter,
    }

    objects = EventScheduleRuleManager()

    class ImproperlyConfigured(Exception):
        pass

    class DoesNotExist(Exception):
        pass

    @classmethod
    def new(cls, obj, source, task_definition):
        name, data = cls.adapters[source](obj).convert()
        target = EventTarget.new(obj, source, rule=data, task_definition=task_definition)
        return cls(name, data, target=target)

    def __init__(self, name, data, target=None):
        self.client = get_boto3_session().client('events')
        self.name = name
        self.data = data
        self.target = target

    @property
    def rule_id(self):
        return self.data['Id']

    @property
    def populated(self):
        return self.data != {}

    def save(self):
        if self.data:
            self.target.delete()
        else:
            self.client.put_rule(**self.data)
        self.target.save()

    def delete(self):
        if self.data:
            self.target.delete()
            self.client.delete_rule(Name=self.data['Name'])

    def diff(self, other):
        d = copy(self.data)
        d['Target'] = self.target.data
        d_other = copy(other.data)
        d_other['Target'] = other.target.data
        return diff(d, d_other)

    def __eq__(self, other):
        if self.__class__ != other.__class__:
            return False
        return (self.data == other.data) and (self.target.data == other.target.data)
