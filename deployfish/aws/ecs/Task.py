#!/usr/bin/env python
from __future__ import print_function

import time

from deployfish.aws import get_boto3_session
from deployfish.aws.systems_manager import ParameterStore

from .TaskScheduler import EventScheduleRule
from .task_defniition import TaskDefinition, TaskDefinitionAWSLogsCloudwatchLogsTailer


# ----------------------------------------
# Adapters
# ----------------------------------------

class DeployfishYamlStandaloneTaskAdapter(object):

    def __init__(self, yaml):
        self.yaml = yaml
        self.secrets = None
        if 'config' in self.yaml:
            self.secrets = ParameterStore("task-{}".format(self.taskName), self.yaml['cluster'], yml=self.yml['config'])

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

    def get_task_definition(self):
        deployfish_environment = {
            "DEPLOYFISH_TASK_NAME": self.yaml['name'],
            "DEPLOYFISH_ENVIRONMENT": self.yaml.get('environment', 'undefined'),
            "DEPLOYFISH_CLUSTER_NAME": self.yaml['cluster']
        }
        return TaskDefinition.new(self.yaml, secrets=self.secrets, extra_environment=deployfish_environment)

    def convert(self):
        task_definition = self.get_task_definition()
        data = {}
        data['name'] = self.yaml['name']
        data['cluster'] = self.yaml.get('cluster', 'default')
        vpc_configuration = self.get_vpc_configuration()
        if vpc_configuration:
            data['networkConfiguration'] = {}
            data['networkConfiguration']['awsVpcConfiguration'] = vpc_configuration
        data['count'] = self.yaml.get('count', 1)
        data['launchType'] = self.yaml.get('launch_type', 'EC2')
        if data['launchType'] == 'FARGATE':
            if 'platform_version' in self.yaml:
                data['platformVersion'] = self.yaml['platform_version']
        if 'placement_constraints' in self.yaml:
            data['placementConstraints'] = self.yaml['placement_constraints']
        if 'placement_strategy' in self.yaml:
            data['placementStrategy'] = self.yaml['placement_strategy']
        if 'group' in self.yaml:
            data['Group'] = self.yaml['group']
        kwargs = {}
        if 'schedule' in self.yaml:
            kwargs['schedule'] = EventScheduleRule.new(self.yaml, 'deployfish.yml', task_definition)
        if self.secrets:
            kwargs['secrets'] = self.secrets
        return data, task_definition, kwargs


# ----------------------------------------
# Managers
# ----------------------------------------

class TaskManager(object):

    def __init__(self):
        self.client = get_boto3_session().client('ecs')

    def get(self, name):
        """
        :param name str: the 'name' key from the task definition in 'tasks:'
        """
        # Need these things out of AWS
        #
        #  * Most recent task definition: what will be run if we do `deploy task run`
        #  * Any scheduled task.  Note this may have a different task definition
        #  * TODO: a populated ParameterStore built out of the secrets in the first container's container definition
        data = {
            'name': name,
            'cluster': None,
            'count': None,
            'launchType': None,
        }
        # This will give us the most recent versision of a task definition whose family is `name`
        task_definition = TaskDefinition.objects.get(name)
        try:
            schedule = EventScheduleRule.objects.get(name)
        except EventScheduleRule.DoesNotExist:
            schedule = None
        return Task(data, task_definition, schedule=schedule)


    def save(self, task, schedule=True):
        task.task_definition.create()
        if schedule and task.schedule:
            task.schedule.save()

    def unschedule(self, task):
        if task.schedule:
            task.schedule.delete()


# ----------------------------------------
# Models
# ----------------------------------------

class Task(object):
    """
    Our Task object here differs from other things we manage (e.g. Service, TaskDefinition) in that
    parts of the configuration are ephemeral -- they don't exist in AWS, but are only used for
    boto3.client('ecs').run_task().

    Task:
        data:
            name: str
            cluster: str
            networkConfiguration: Union(None, dict(str, dict(str, *))
                vpcConfiguration: Union(None, dict(str, *))
                    subnets: List(str)
                    securityGroups: List(str)
                    assignPublicIp: bool
            count: int
            launchType: Enum('EC2', 'FARGATE')
            placementConstraints: ?
            placementStrategy: ?
            group: Union(str, None)
        task_definition: TaskDefinition
        schedule: Union(EventScheduleRule, None)
            data:
                Name
                ScheduleExpression
                State
                EventPattern



    """

    adapters = {
        'deployfish.yml': DeployfishYamlStandaloneTaskAdapter,
    }

    @classmethod
    def new(cls, obj, source):
        data, task_definition, kwargs = cls.adapters[source](obj).convert()
        return cls(data, task_definition, **kwargs)

    def __init__(self, data, task_definition, secrets=None, schedule=None):
        self.data = data
        self.task_definition = task_definition
        self.schedule = schedule
        self.secrets = secrets
        self.ecs = get_boto3_session().client('ecs')

    def get_config(self):
        if self.secrets:
            self.secrets.populate()
        return self.secrets

    def write_config(self):
        self.secrets.save()

    def save(self):
        self.objects.create(self)

    def observe(self, task):
        if task:
            invocation_arn = task['taskArn']
            cluster = task['clusterArn']



    def run(self, wait=False, create=False):
        if create:
            self.objects.save(self, schedule=False)
        # Run the latest ACTIVE task definition in our family.  If `create` was True, this will be the one we just
        # registered
        self.data['taskDefinition'] = self.task_definition.data['family']
        response = self.ecs.run_task(**self.data)
        if wait:
            waiter = self.client.get_waiter('tasks_stopped')
            # poll every 6 seconds, maximum of 100 polls
            waiter.wait(
                cluster=self.data['cluster'],
                tasks=[t['taskArn'] for t in response['tasks']]
            )
            success = self._wait_until_stopped()
            if success:
                self._get_cloudwatch_logs()


