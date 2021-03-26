#!/usr/bin/env python
from __future__ import print_function

import time

from deployfish.aws import get_boto3_session
from deployfish.aws.systems_manager import ParameterStore

from .TaskScheduler import TaskScheduler
from .task_defniition import TaskDefinition


class Task(object):
    """
    An object representing an ECS task.
    """

    def __init__(self, name, service=False, config=None):
        if service:
            yml = config.get_service(name)
        else:
            yml = config.get_task(name)

        self.ecs = get_boto3_session().client('ecs')

        self.taskName = None
        self.clusterName = None
        self.desired_count = 1
        self._launchType = 'EC2'
        self.cluster_specified = False
        self.__defaults()
        self.from_yaml(yml)
        self.from_aws()
        self.scheduler = TaskScheduler(self)

    def __defaults(self):
        self._roleArn = None
        self.schedule_expression = None
        self.schedule_role = None
        self.vpc_configuration = {}
        self.placement_constraints = []
        self.placement_strategy = []
        self.platform_version = "LATEST"
        self.cluster_arn = ''
        self.group = None

    def set_vpc_configuration(self, yml):
        self.vpc_configuration = {
            'subnets': yml['subnets'],
        }
        if 'security_groups' in yml:
            self.vpc_configuration['securityGroups'] = yml['security_groups']

        if 'public_ip' in yml:
            self.vpc_configuration['assignPublicIp'] = yml['public_ip']

    def __render(self, task_definition_id):
        """
        Generate the dict we will pass to boto3's `run_task()`.

        :rtype: dict
        """
        r = {}
        if self.cluster_specified:
            r['cluster'] = self.clusterName
        if self.desired_count:
            r['count'] = self.desired_count
        r['launchType'] = self.launchType
        if self.launchType == 'FARGATE':
            r['networkConfiguration'] = {
                'awsvpcConfiguration': self.vpc_configuration
            }
        r['taskDefinition'] = task_definition_id
        if len(self.placement_constraints) > 0:
            r['placementConstraints'] = self.placement_constraints
        if len(self.placement_strategy) > 0:
            r['placementStrategy'] = self.placement_strategy
        if self.group:
            r['group'] = self.group
        return r

    def _get_cluster_arn(self):
        if self.cluster_specified:
            response = self.ecs.describe_clusters(clusters=[self.clusterName])
            for cluster in response['clusters']:
                self.cluster_arn = cluster['clusterArn']
                return

        response = self.ecs.describe_clusters()
        for cluster in response['clusters']:
            self.cluster_arn = cluster['clusterArn']
            return

    def from_yaml(self, yml):
        """
        Load our task information from the parsed yaml.  ``yml`` should be
        a task level entry from the ``deployfish.yml`` file.

        :param yml: a task level entry from the ``deployfish.yml`` file
        :type yml: dict
        """
        self.taskName = yml['name']
        if 'launch_type' in yml:
            self.launchType = yml['launch_type']
            if self.launchType == 'FARGATE':
                if 'platform_version' in yml:
                    self.platform_version = yml['platform_version']
        self.environment = yml.get('environment', 'undefined')
        self.family = yml['family']
        if 'cluster' in yml:
            self.clusterName = yml['cluster']
            self.cluster_specified = True
        else:
            self.clusterName = 'default'

        if 'vpc_configuration' in yml:
            self.set_vpc_configuration(
                yml['vpc_configuration']
            )
        if 'placement_constraints' in yml:
            self.placementConstraints = yml['placement_constraints']
        if 'placement_strategy' in yml:
            self.placementStrategy = yml['placement_strategy']
        if 'count' in yml:
            self.desired_count = yml['count']
        self.desired_task_definition = TaskDefinition(yml=yml)
        deployfish_environment = {
            "DEPLOYFISH_TASK_NAME": yml['name'],
            "DEPLOYFISH_ENVIRONMENT": yml.get('environment', 'undefined'),
            "DEPLOYFISH_CLUSTER_NAME": self.clusterName
        }
        self.desired_task_definition.inject_environment(deployfish_environment)
        parameters = []
        if 'config' in yml:
            parameters = yml['config']
        self.parameter_store = ParameterStore("task-{}".format(self.taskName), self.clusterName, yml=parameters)
        if 'schedule' in yml:
            self.schedule_expression = yml['schedule']
        if 'schedule_role' in yml:
            self.schedule_role = yml['schedule_role']
        if 'group' in yml:
            self.group = yml['group']

        self._get_cluster_arn()

    def from_aws(self):
        """
        Update our task definition from the most recent version in AWS.
        """
        task_definition_id = self.desired_task_definition.get_latest_revision()
        if task_definition_id:
            self.active_task_definition = TaskDefinition(task_definition_id)
        else:
            self.active_task_definition = None

    def get_config(self):
        """
        Return the ``ParameterStore()`` for our task.

        :rtype: a ``deployfish.systems_manager.ParameterStore`` object
        """
        self.parameter_store.populate()
        return self.parameter_store

    def write_config(self):
        """
        Update the AWS System Manager Parameter Store parameters to match
        what we have defined in our ``deployfish.yml``.
        """
        self.parameter_store.save()

    def __force_register_task_definition(self):
        """
        Prep the parameter store and register the task definition/
        """
        self.parameter_store.populate()
        self.desired_task_definition.set_parameter_store(self.parameter_store)
        self.desired_task_definition.create()
        self.from_aws()

    def register_task_definition(self):
        """
        If our task definition has not been registered, do it here.
        """
        if not self.active_task_definition:
            self.__force_register_task_definition()

    def _get_cloudwatch_logs(self):
        """
        Retrieve and display the logs corresponding to our task until there are no more available.
        """
        if not self.active_task_definition.containers[0].logConfiguration.driver == 'awslogs':
            return

        prefix = self.active_task_definition.containers[0].logConfiguration.options['awslogs-stream-prefix']
        group = self.active_task_definition.containers[0].logConfiguration.options['awslogs-group']
        container = self.active_task_definition.containers[0].name
        task_id = self.taskarn.split(':')[-1][5:]
        stream = "{}/{}/{}".format(prefix, container, task_id)

        log_client = get_boto3_session().client('logs')

        nextToken = None
        kwargs = {
            'logGroupName': group,
            'logStreamName': stream,
            'startFromHead': True
        }

        print("Waiting for logs...\n")
        for i in range(40):
            time.sleep(5)
            response = log_client.get_log_events(**kwargs)
            for event in response['events']:
                print(event['message'])
            token = response['nextForwardToken']
            if token == nextToken:
                return
            nextToken = response['nextForwardToken']
            kwargs['nextToken'] = nextToken

    def _wait_until_stopped(self):
        """
        Inspect and display the status of the task until it has finished.
        """
        if 'tasks' in self.response and len(self.response['tasks']) > 0:
            task = self.response['tasks'][0]
            cluster = task['clusterArn']
            self.taskarn = task['taskArn']
            print("Waiting for task to complete...\n")
            for i in range(40):
                time.sleep(5)
                response = self.ecs.describe_tasks(
                    cluster=cluster,
                    tasks=[self.taskarn]
                )
                if 'tasks' in response and len(response['tasks']) > 0:
                    status = response['tasks'][0]['lastStatus']
                    print("\tCurrent status: {}".format(status))
                    if status == "STOPPED":
                        print("")
                        stopCode = response['tasks'][0]['stopCode']
                        if stopCode == 'TaskFailedToStart':
                            print('Task failed to start.\n')
                            print(response['tasks'][0]['stoppedReason'])
                            success = False
                        else:
                            success = True

                        return success
                else:
                    return False
            print("Timed out after 200 seconds...")

    def run(self, wait):
        """
        Run the task. If wait is specified, show the status and logs from the task.
        :param wait: Should we wait for the task to finish and display any logs
        :type wait: bool
        """
        self.register_task_definition()
        if not self.active_task_definition:
            # problem
            return
        kwargs = self.__render(self.active_task_definition.arn)
        self.response = self.ecs.run_task(**kwargs)
        # print(self.response)
        if wait:
            success = self._wait_until_stopped()
            if success:
                self._get_cloudwatch_logs()

    def schedule(self):
        """
        If a schedule expression is defined in the yml file, schedule the task accordingly via the `TaskScheduler`
        object.
        """
        if not self.schedule_expression:
            return
        self.register_task_definition()
        self.scheduler.schedule()

    def unschedule(self):
        """
        Unschedule the task.
        """
        self.scheduler.unschedule()

    def update(self):
        """
        Update the task definition as appropriate.
        """
        self.__force_register_task_definition()

    def purge(self):
        pass


class HelperTask(object):
    """
    This is a batch job that will be run via the ECS RunTask API call.  It runs
    for a short time and then dies.

    The reason this class exists is to enable us to run one-off or periodic
    functions (migrate databases, clear caches, update search indexes, do
    database backups or restores, etc.) for our services.
    """

    def __init__(self, clusterName, yml=None):
        """
        :param clusterName: the name of the cluster in which we'll run our
                            helper tasks
        :type clusterName: string

        :param yml: the task definition information for the task from our
                    deployfish.yml file
        :type yml: dict
        """
        if not yml:
            yml = {}
        self.clusterName = clusterName
        self.ecs = get_boto3_session().client('ecs')
        self.commands = {}
        self.from_yaml(yml)
        self.desired_task_definition = TaskDefinition(yml=yml)
        self.active_task_definition = None

    def from_yaml(self, yml):
        if 'commands' in yml:
            for key, value in yml['commands'].items():
                self.commands[key] = value.split()

    def from_aws(self, taskDefinition):
        self.active_task_definition = TaskDefinition(taskDefinition)

    @property
    def family(self):
        """
        Returns the task definition family or base name.

        :return: string
        """
        return self.desired_task_definition.family

    @property
    def family_revision(self):
        """
        Returns the current version of the task definition.

        :return: string
        """
        return self.active_task_definition.family_revision

    def create(self):
        """
        Creates the task definition.

        :return: None
        """
        self.desired_task_definition.create()
        self.from_aws(self.desired_task_definition.arn)

    def run(self, command):
        """
        Runs the task

        :param command: The Docker command to run.
        :return: string - only returns on failure
        """
        response = self.ecs.run_task(
            cluster=self.clusterName,
            taskDefinition=self.active_task_definition.arn,
            overrides={
                'containerOverrides': [
                    {
                        'name': self.active_task_definition.containers[0].name,
                        'command': self.commands[command]
                    }
                ]
            }
        )
        if response['failures']:
            return response['failures'][0]['reason']
        return ""
