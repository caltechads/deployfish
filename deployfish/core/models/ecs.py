from copy import deepcopy
import fnmatch
import re
import textwrap

from deployfish.core.aws import get_boto3_session
from deployfish.core.ssh import DockerMixin, SSHMixin
from deployfish.core.utils import is_fnmatch_filter

from .abstract import Manager, Model, LazyAttributeMixin
from .alb import TargetGroup
from .ec2 import Instance, AutoscalingGroup
from .efs import EFSFileSystem
from .elb import ClassicLoadBalancer
from .events import EventScheduleRule
from .mixins import TaskDefinitionFARGATEMixin, TagsMixin
from .secrets import SecretsMixin, Secret
from .appscaling import ScalableTarget
from .service_discovery import ServiceDiscoveryService

# ----------------------------------------
# Helpers
# ----------------------------------------


class TaskTagImporter(object):
    """
        Task related tags we need to read from a task definition associated with a StandaloneTask or ServiceHelperTask
        in AWS:

            'deployfish:service': the pk of the service associated with this task, if any
            'deployfish:command': if this is a ServiceHelperTask, this is the human name of the command
            'deployfish:cluster': the cluster in which to run this task
            'deployfish:desiredCount': how many tasks to run

        If self.data['capacityProviderStrategy'] is not defined:

            'deployfish:launchType': EC2 or FARGATE

            If self.data['launchType'] is FARGATE:

                'deployfish:platformVersion': the platform version, defaults to LATEST

        If self.data['capacityProviderStrategy'] is defined:

            'deployfish:capacityProviderStrategy.0': "provider={provider_name}[;weight={weight}][;base={base}]"
            'deployfish:capacityProviderStrategy.1': "provider={provider_name}[;weight={weight}][;base={base}]"
            ...

            weight and base are only added to the value if they were provided

        If self.data['placementConstraints'] is defined:

            if a constraint is a "memberOf" constraint:

                'deployfish:placementConstraint.0': the expression

                If the expression is longer than 255 chars, it will be split into multiple tags like so:

                    'deployfish:placementConstraint.0.0': the expression part 1
                    'deployfish:placementConstraint.0.1': the expression part 2

            if a constraint is a "distinctInstance" constraint:

                'deployfish:placementConstraint.0': 'distinctInstance'

        If self.data['placementStrategy'] is defined:

                'deployfish:placementStrategy.0': "field={field};type={type}"
                'deployfish:placementStrategy.1': "field={field};type={type}"
                ...

        If self.data['networkConfiguration'] is defined:

                'deployfish:vpc:subnet.0': "subnet-0"
                'deployfish:vpc:subnet.1': "subnet-1"
                ...
                'deployfish:vpc:securityGroup.0': "sg-0"
                'deployfish:vpc:securityGroup.1': "sg-1"
                ...
                'deployfish:vpc:allowPublicIp': "ENABLED" or "DISABLED"

        """

    CAPACITY_PROVIDER_STRATEGY_RE = re.compile(
        r'provider=(?P<provider>[^;]*)(;weight=(?P<weight>[^;]*))?(;base=(?P<base>.*))?'
    )
    PLACEMENT_CONSTRAINT_TAG_RE = re.compile(
        r'deployfish:placementConstraint.(?P<index>[0-9]+)(.(?P<part>[0-9]+))?'
    )
    PLACEMENT_STRATEGY_RE = re.compile(
        r'field=(?P<field>[^;]+);type=(?P<type>.*)'
    )

    def __init__(self):
        self.data = {}

    def __convert_capacityProviderStrategy(self, key, value):
        """
        Capacity Provider Strategies are stored in tags like::

            'deployfish:capacityProviderStrategy.0': "provider={provider_name}[;weight={weight}][;base={base}]"
            'deployfish:capacityProviderStrategy.1': "provider={provider_name}[;weight={weight}][;base={base}]"

        `provider` is required, but `weight` and `base` are optional.
        """
        if 'capacityProviderStrategy' not in self.data:
            self.data['capacityProviderStrategy'] = []
        m = self.CAPACITY_PROVIDER_STRATEGY_RE.s(value)
        if m:
            cp = {'capacityProvider': m.group('provider')}
            if m.group('weight'):
                cp['weight'] = int(m.group('weight'))
            if m.group('base'):
                cp['base'] = int(m.group('base'))
            self.data['capacityProviderStrategy'].append(cp)

    def __convert_placementConstraint(self, key, value):
        """
        If a constraint is a "memberOf" constraint:

            'deployfish:placementConstraint.0': the expression

            If the expression is longer than 255 chars, it will be split into multiple tags like so:

                'deployfish:placementConstraint.0.0': the expression part 1
                'deployfish:placementConstraint.0.1': the expression part 2

        if a constraint is a "distinctInstance" constraint:

            'deployfish:placementConstraint.0': 'distinctInstance'
    """
        if 'placementConstraints' not in self.data:
            self.data['placementConstraints'] = []
        m = self.PLACEMENT_CONSTRAINT_TAG_RE.search(key)
        index = int(m.group('index'))
        if value == 'distinctInstance':
            self.data['placementConstraints'].append({'type': value})
        else:
            try:
                entry = self.data['placementConstraints'][index]
            except IndexError:
                entry = {'type': 'memberOf', 'expression': value}
            else:
                entry['expression'] += value

    def __convert_placementStrategy(self, key, value):
        """
        placementStrategy is stored in tags as:

            'deployfish:placementStrategy.0': "field={field};type={type}"
            'deployfish:placementStrategy.1': "field={field};type={type}"
        """
        if 'placementStrategy' not in self.data:
            self.data['placementStrategy'] = {}
        m = self.PLACEMENT_STRATEGY_RE.search(value)
        if m:
            self.data['placementStrategy'].append({
                'field': m.group('field'),
                'type': m.group('type')
            })

    def __convert_awsvpcConfiguration(self, key, value):
        if 'networkConfiguration' not in self.data:
            self.data['networkConfiguration'] = {}
            self.data['networkConfiguration']['awsvpcConfiguration'] = {}
        vpc = self.data['networkConfiguration']['awsvpcConfiguration']
        if 'subnet' in key:
            if 'subnets' not in vpc:
                vpc['subnets'] = []
            vpc['subnets'].append(value)
        if 'securityGroup' in key:
            if 'securityGroups' not in vpc:
                vpc['securityGroups'] = []
            vpc['securityGroups'].append(value)
        if 'allowPublicIp' in key:
            vpc['allowPublicIp'] = value

    def convert(self, tag_list):
        """
        Take ``tag_list``, a tag data structure from AWS that looks like::

            tags = [
                {
                    'name': 'tag_name',
                    'value': 'tag_value'
                }
            ]

        and convert that to the `data` dict for a StandaloneTask or ServiceHelperTask.

        :param tag_list list(dict(str, str)): list of tags from AWS

        :rtype: dict(str, *)
        """
        tag_list = sorted(tag_list, key=lambda x: x['key'])
        # sort the tags so that the .0 .1 .2, etc tags get processed in the proper order
        tags = {tag['key']: tag['value'] for tag in tag_list}
        for key, value in tags.items():
            if key == 'deployfish:service':
                self.data['service'] = value
            elif key == 'deployfish:type':
                self.data['task_type'] = value
            elif key == 'deployfish:desiredCount':
                self.data['count'] = int(value)
            elif key == 'deployfish:task-name':
                self.data['name'] = value
            elif key == 'deployfish:cluster':
                self.data['cluster'] = value
            elif key == 'deployfish:launchType':
                self.data['launchType'] = value
            elif key == 'deployfish:platformVersion':
                self.data['platformVersion'] = value
            elif key.startswith('deployfish:capacityProviderStrategy'):
                self.__convert_capacityProviderStrategy(key, value)
            elif key.startswith('deployfish:placementConstraint'):
                self.__convert_placementConstraint(key, value)
            elif key.startswith('deployfish:placementStrategy'):
                self.__convert_placementStrategy(key, value)
            elif key.startswith('deployfish:vpc'):
                self.__convert_awsvpcConfiguration(key, value)
        return self.data


class TaskTagExporter(object):
    """
    Take ``data``, the configuration struct for a StandaloneTask or ServiceHelperTask, and convert it
    to AWS tags to be stored on the task definiition for the task.

    See ``TaskTagImporter`` for the description of how the tags work.
    """

    def __init__(self):
        self.tags = {}

    def __convert_capacityProviderStrategy(self, value):
        """
        The capacityProviderStrategy struct looks like::

            capacityProviderStrategy=[
                {
                    'capacityProvider': 'string',
                    'weight': 123,
                    'base': 123
                },
            ],

        ``weight`` and ``base`` are optional.
        """
        for i, provider in enumerate(value):
            line = "provider={}".format(provider['capacityProvider'])
            if 'weight' in provider:
                line += ";weight={}".format(provider['weight'])
            if 'base' in provider:
                line += ";base={}".format(provider['base'])
            self.tags['deployfish:capacityProvideStrategy.{}'.format(i)] = line

    def __convert_placementConstraints(self, value):
        """
        The placementConstraints struct looks like::

            placementConstraints=[
                {
                    'type': 'distinctInstance'|'memberOf',
                    'expression': 'string'
                },
            ],

        ``expression`` is only present if ``type`` is ``memberOf``, and ``expression`` can be arbitrarily long.
        """
        for i, constraint in enumerate(value):
            if constraint['type'] == 'memberOf':
                expression = constraint['expression']
                if len(expression) < 256:
                    self.tags['deployfish:placementConstraint.{}'.format(i)] = expression
                else:
                    lines = textwrap.wrap(expression, 255)
                    for j, line in lines:
                        self.tags['deployfish:placementConstraint.{}.{}'.format(i, j)] = line
            else:
                self.tags['deployfish:placementConstraint:expression.{}'.format(i)] = 'distinctInstance'

    def __convert_placementStrategy(self, value):
        """
        The placementStrategy struct looks like this::

            placementStrategy=[
                {
                    'type': 'random'|'spread'|'binpack',
                    'field': 'string'
                },
            ],
        """
        for i, strategy in enumerate(value):
            self.tags['deployfish:placementStrategy.{}'.format(i)] = "field={};type={}".format(
                strategy['field'],
                strategy['type']
            )

    def __convert_awsvpcConfiguration(self, value):
        """
        The awsvpcConfiguration struct looks like this::
            'awsvpcConfiguration': {
                'subnets': [
                    'string',
                ],
                'securityGroups': [
                    'string',
                ],
                'assignPublicIp': 'ENABLED'|'DISABLED'
            }
        """
        for i, subnet in enumerate(value['subnets']):
            self.tags['deployfish:vpc:subnet.{}'.format(i)] = subnet
        for i, sg in enumerate(value['securityGroups']):
            self.tags['deployfish:vpc:securityGroup.{}'.format(i)] = sg
        if 'allowPublicIp' in value:
            self.tags['deployfish:vpc:allowPublicIp'] = value['allowPublicIp']

    def convert(self, data, task_type='standalone'):
        """
        Take ``data``, the configuration struct for a StandaloneTask or ServiceHelperTask, and convert it
        to AWS tags to be stored on the task definiition for the task.
        """
        self.tags['deployfish:task-name'] = data['name']
        self.tags['deployfish:type'] = task_type
        if 'service' in data:
            self.tags['deployfish:service'] = data['service']
        self.tags['deployfish:cluster'] = data['cluster']
        if 'group' in data:
            self.tags['deployfish:group'] = data['group']
        if 'count' in data:
            self.tags['deployfish:desiredCount'] = str(data['count'])
        # We can have either launchType or capacityProviderStrategy, but not both
        if 'launchType' in data:
            self.tags['deployfish:launchType'] = data['launchType']
            self.tags['deployfish:platformVersion'] = data.get('platformVersion', 'LATEST')
        elif 'capacityProviderStrategy' in data:
            self.__convert_capacityProviderStrategy(data['capacityProviderStrategy'])
        if 'placementConstraints' in data:
            self.__convert_placementConstraints(data['placementConstraints'])
        if 'placementStrategy' in data:
            self.__convert_placementStrategy(data['placementStrategy'])
        if 'networkConfiguration' in data:
            self.__convert_awsvpcConfiguration(data['networkConfiguration']['awsvpcConfiguration'])
        return self.tags


# ----------------------------------------
# Managers
# ----------------------------------------

class TaskDefinitionManager(Manager):

    service = 'ecs'

    def get(self, pk):
        # hint: (str["{family}:{revision}","{family}","{task_definition_arn}"])
        try:
            response = self.client.describe_task_definition(
                taskDefinition=pk,
                include=['TAGS']
            )
        except self.client.exceptions.ClientException:
            raise TaskDefinition.DoesNotExist(
                'No task definition matching "{}" exists in AWS'.format(pk)
            )
        data = response['taskDefinition']
        # For some reason, tags are not included as part of the task definition, but are alongside it
        if 'tags' in response:
            data['tags'] = response['tags']
        containers = [ContainerDefinition(d) for d in data.pop('containerDefinitions')]
        return TaskDefinition(data, containers=containers)

    def list(self, family):
        # hint: (str)
        paginator = self.client.get_paginator('list_task_definitions')
        response_iterator = paginator.paginate(familyPrefix=family, sort='ASC')
        task_definition_arns = []
        for response in response_iterator:
            task_definition_arns.extend(response['taskDefinitionArns'])
        return [self.get(arn) for arn in task_definition_arns]

    def save(self, obj):
        response = self.client.register_task_definition(**obj.render())
        return response['taskDefinition']['taskDefinitionArn']

    def delete(sef, obj):
        raise TaskDefinition.ReadOnly('deployfish will not delete existing task definitions.')


class AbstractTaskManager(Manager):

    service = 'ecs'
    task_type = None
    model = None

    def get(self, pk):
        # hint: (str["{family}:{revision}","{family}","{task_definition_arn}"])
        task_definition = None
        if TaskDefinition.objects.exists(pk):
            task_definition = TaskDefinition.objects.get(pk)
        else:
            raise self.model.DoesNotExist(
                'No TaskDefintion for {}(pk="{}") exists in AWS'.format(self.model.__name__, pk)
            )
        schedule = None
        if EventScheduleRule.objects.exists(task_definition.family):
            schedule = EventScheduleRule.objects.get(task_definition.family)
            if not schedule.target:
                # This should never happen
                schedule = None
            elif schedule.target.data['EcsParameters']['TaskDefinitionArn'] != task_definition.arn:
                schedule = None
        # Extract the info we need to run the task from tags on the task definition
        data = TaskTagImporter().convert(task_definition.data.get('tags', []))
        return self.model(data, task_definition=task_definition, schedule=schedule)

    def get_many(self, pks):
        # hint: (list[str["{family}:{revision}","{family}","{task_definition_arn}"]])
        tasks = []
        for pk in pks:
            tasks.append(self.get(pk))
        return tasks

    def list(self, scheduled_only=False):
        # hint: (bool)
        if scheduled_only:
            return self.list_scheduled()
        else:
            return self.list_all()

    def list_all(self):
        raise NotImplementedError

    def list_scheduled(self):
        """
        List only the scheduled tasks.  We do this by listing all the deployfish related schedules and building
        the Task objects based on the task definition attached to them.

        .. warning::

            One thing we're assuming here is that the run_task data attached to the EventTarget is the same as that
            saved as tags on the task definition.   Hopefully those two things can only differ if we screwed up
            somewhere.
        """
        rules = EventScheduleRule.objects.list()
        tasks = []
        for rule in rules:
            if rule.target:
                task_definition = TaskDefinition.objects.get(rule.target.data['EcsParameters']['TaskDefinitionArn'])
                data = TaskTagImporter().convert(task_definition.data.get('tags', []))
                if data['task_type'] != self.task_type:
                    continue
                tasks.append(self.model(data, task_definition=task_definition, schedule=rule))
        return tasks

    def save(self, obj):
        # hint: (TaskDefinition)
        """
        Save our StandaloneTask.

            1. Update the tags for the task definition to save our task_run parameters for later
            2. Save the task definition
            3. Deal with task schedules:
                * Unschedule all schedules

        Write the task definition, unschedule any previous versions of our task and schedule this version of it if
        necesary.

        Return the ARN of the task definition we created.

        :param obj StandaloneTask: the task to schedule

        :rtype: str
        """
        # Export the info we need in order to run the task as tags on the task definition
        tags = TaskTagExporter().convert(obj.data, task_type=self.task_type)
        obj.task_definition.tags.update(tags)
        # Save the task definition
        arn = obj.task_definition.save()
        # Delete any schedule we currently have for this task.
        try:
            # We name our EventScheduleRules after the task family, so we send that in
            # as the pk for the .get() here
            rule = EventScheduleRule.objects.get(obj.family)
        except EventScheduleRule.DoesNotExist:
            # There was no existing schedule
            pass
        else:
            rule.delete()
        if obj.schedule:
            # If we have a scedule, schedule the task
            obj.schedule.set_task_definition_arn(arn)
            obj.schedule.save()
        return arn

    def delete(self, obj):
        # What should happen here?  Delete all task definitions?
        # delete any schedule we currently have
        if EventScheduleRule.objects.exists(obj.pk):
            EventScheduleRule.objects.delete(obj.pk)

    def run(self, obj):
        obj.data['taskDefinition'] = obj.task_definition.pk
        response = self.client.run_task(**obj.render())
        return [InvokedTask(data) for data in response['tasks']]

    def enable_schedule(self, pk):
        # hint: (str["{family}:{revision}","{family}","{task_definition_arn}"])
        """
        If the task has a scchedule and the schedule rule is disabled, enable the schedule rule.  Otherwise
        do nothing.

        :param obj pk: the task to enable
        """
        obj = self.get(pk)
        obj.enable_schedule()

    def disable_schedule(self, pk):
        # hint: (str["{family}:{revision}","{family}","{task_definition_arn}"])
        """
        If the task has a scchedule and the schedule rule is enabled, disable the schedule rule.  Otherwise
        do nothing.

        :param obj pk: the task to disable
        """
        obj = self.get(pk)
        obj.disable_schedule()


class StandaloneTaskManager(AbstractTaskManager):

    task_type = 'standalone'
    # model is set after the StandaloneTask class definition, below

    def list(self, scheduled_only=False, all_revisions=False, task_type='standalone', service_name=None, cluster_name=None, task_name=None):  # noqa:E501
        # hint: (bool, bool, choice[standalone|service_helper|any], str["{service_pk:glob}"], str["{cluster_name:glob}"], str["{task_name:glob}"])
        """
        List all Tasks (StandaloneTasks and ServiceHelperTasks), filtering by various dimensions.

        :param scheduled_only bool: If ``True``, only return Tasks that have EventScheduleRules
        :param all_revisions bool: If ``True`` return every task revision that is a deployfish Task.  Default: return
                                   only the latest revision for each Task
        :param task_type str: If provided, filter results by task type. A choice field: standalone, service_helper, any.
        :param service_name str: If provided, filter results by service_name. This is a glob pattern.
        :param cluster_name str: If provided, filter results by cluster_name. This is a glob pattern.
        :param task_name str: If provided, filter results by task_name. This is a glob pattern.

        Filter ``tasks`` by various dimensions, returning only those tasks that match our filters.

        :rtype: list(Task)
        """
        if task_type == 'any':
            task_type = ['standalone', 'service_helper']
        else:
            task_type = [task_type]
        if scheduled_only:
            return self.list_scheduled(
                service_name=service_name,
                cluster_name=cluster_name,
                task_name=task_name,
                task_type=task_type
            )
        else:
            return self.list_all(
                all_revisions=all_revisions,
                task_type=task_type,
                service_name=service_name,
                task_name=task_name
            )

    def filter_list_results(self, tasks, service_name, cluster_name, task_name):
        """
        Filter ``tasks`` by various dimensions, returning only those tasks that match our filters.

        :param service_name str: If provided, filter results by service_name. This is a glob pattern.
        :param cluster_name str: If provided, filter results by cluster_name. This is a glob pattern.
        :param task_name str: If provided, filter results by task_name. This is a glob pattern.

        :rtype: list(Task)
        """
        if service_name or any(map(is_fnmatch_filter, [cluster_name, task_name])):
            matched_tasks = []
            for task in tasks:
                if service_name:
                    # the service tag is actually a service pk: {cluster_name}:{service_name}
                    if 'service' in task.data:
                        cluster, service = task.data['service'].split(':')
                        if fnmatch.fnmatch(service, service_name):
                            matched_tasks.append(task)
                if cluster_name and is_fnmatch_filter(cluster_name):
                    if fnmatch.fnmatch(task.data['cluster'], cluster_name):
                        matched_tasks.append(task)
                if task_name and is_fnmatch_filter(task_name):
                    if fnmatch.fnmatch(task.data['name'], task_name):
                        matched_tasks.append(task)
            tasks = matched_tasks
        return tasks

    def list_scheduled(self, service_name=None, cluster_name=None, task_type=None, task_name=None):
        """
        List only the scheduled tasks, filtering by various dimensions.  We do this by listing all the deployfish
        related schedules and building the Task objects based on the task definition attached to them.

        .. warning::

            One thing we're assuming here is that the run_task data attached to the EventTarget is the same as that
            saved as tags on the task definition.   Hopefully those two things can only differ if we screwed up
            somewhere.
        """
        tasks = super(StandaloneTaskManager, self).list_scheduled()

        if task_type != 'any':
            new_tasks = []
            for task in tasks:
                if task.data['task_type'] == task_type:
                    new_tasks.append(task)
            tasks = new_tasks
        if any([service_name, cluster_name, task_name]):
            matched_tasks = []
            for task in tasks:
                if service_name:
                    # the service tag is actually a service pk: {cluster_name}:{service_name}
                    cluster, service = task.data['service'].split(':')
                    if fnmatch.fnmatch(service, service_name):
                        matched_tasks.append(task)
                if cluster_name:
                    if fnmatch.fnmatch(task.data['cluster'], cluster_name):
                        matched_tasks.append(task)
                if task_name:
                    if fnmatch.fnmatch(task.data['name'], task_name):
                        matched_tasks.append(task)
            tasks = matched_tasks
        return tasks

    def list_all(self, all_revisions=False, task_type='standalone', service_name=None, cluster_name=None,
                 task_name=None):
        """
        List all the StandaloneTasks, which means return the list of StandaloneTasks that represent the latest revision
        among all families of task definitions which have the tag "deployfish:type" equal to "standalone".

        These will not include the ServiceHelperTasks.

        :param all_revisions bool: If ``True`` return every task revision that is a deployfish Task.  Default: return
                                   only the latest revision for each Task
        :param task_type str: If provided, filter results by task type. A choice field: standalone, service_helper, any.
        :param service_name str: If provided, filter results by service_name. This is a glob pattern.
        :param cluster_name str: If provided, filter results by cluster_name. This is a glob pattern.
        :param task_name str: If provided, filter results by task_name. This is a glob pattern.

        .. note::

            One of the sucky things here is that we need to retrieve all tagged taskDefinition revisions, then figure
            out what families those revisions belong to, and finally get each task individually.  That is a lot of AWS
            API calls.

        :rtype: list(StandaloneTask)
        """
        # For this we'll actually use boto3.client('resourcegroupstaggingapi').get_resources() to filter by tag.  All of
        # our standalone tasks should be tagged, while the service tasks won't be tagged.
        client = get_boto3_session().client('resourcegroupstaggingapi')
        paginator = client.get_paginator('get_resources')
        tag_filters = []
        tag_filters.append({'Key': 'deployfish:type', 'Values': task_type})
        # Because deployfish:service is a {cluster_name}:{service_name}, and we expect people to just give us a bare
        # service name, don't filter by tag on serviice_name at all -- we use self.filter_list_results()
        if cluster_name and not is_fnmatch_filter(cluster_name):
            tag_filters.append({'Key': 'deployfish:cluster', 'Values': cluster_name})
        if task_name and not is_fnmatch_filter(task_name):
            tag_filters.append({'Key': 'deployfish:task-name', 'Values': task_name})
        response_iterator = paginator.paginate(TagFilters=tag_filters, ResourceTypeFilters=['ecs:task-definition'])
        resource_arns = []
        for response in response_iterator:
            for resource in response['ResourceTagMappingList']:
                resource_arns.append(resource['ResourceARN'])
        # Now extract the unique tag families from the resource arns.  We do this because we only want the latest
        # task revision for standalone tasks
        if not all_revisions:
            pks = set()
            for arn in resource_arns:
                # Task definition arns look like:
                #   arn:aws:ecs:us-west-2:467892444047:task-definition/access_admin-test:13
                family = arn.split('/', 1)[1].split(':')[0]
                pks.add(family)
            pks = list(pks)
        else:
            pks = resource_arns
        tasks = []
        for pk in pks:
            tasks.append(self.get(pk))
        tasks = self.filter_list_results(tasks, service_name, cluster_name, task_name)
        return tasks


class ServiceHelperTaskManager(AbstractTaskManager):

    task_type = 'service_helper'
    # model is set after the ServiceHelperTask class definition, below

    def list_all(self):
        """
        List all the ServiceHelperTasks.  To do this accurately, we need to:

            * List all the services
            * Look at the active task definition for the "deployfish:task-name" tags and collect the task
              definition arns
            * Build ServiceHelperTasks based on those arns and return them

        We need to do this instead of just listing all tasks with the tag 'deployfish:type' of 'service_helper' because
        of the fact that we sometimes need to revert our services to previous versions.  In that case, the latest
        version of a task family would not be the correct helper for the service.  We want the version of the task that
        is from the same code version as what the Service is running.

        The drawback is that listing the services takes a long time -- 15-20s, so this is a slow operation.

        :rtype: list(ServiceHelperTask)
        """
        services = Service.objects.list()
        task_definition_arns = []
        for service in services:
            for tag, arn in service.task_definition.tags.items():
                if tag.startswith('deployfish:command:'):
                    task_definition_arns.append(arn)
        return [self.get(arn) for arn in task_definition_arns]


class InvokedTaskManager(Manager):

    """
    Invoked tasks are tasks that either are currently running in ECS, or have
    run and are now stopped.
    """

    service = 'ecs'

    def __get_cluster_and_task_arn_from_pk(self, pk):
        return pk.split(':', 1)

    def get(self, pk):
        # hint: (str["{cluster_name}:{task_arn}"])
        """
        :param name str: a string like '{cluster}:{task_arn}'
        """
        cluster, task_arn = self.__get_cluster_and_task_arn_from_pk(pk)
        try:
            response = self.client.describe_tasks(cluster=cluster, tasks=[task_arn])
        except self.client.exceptions.ClusterNotFoundException:
            raise Cluster.DoesNotExist('No cluster named "{}" exists in AWS'.format(cluster))

        # This will give us the most recent versision of a task definition whose family is `name`
        if not response['tasks']:
            raise InvokedTask.DoesNotExist('No task exists with arn "{}" in cluster "{}"'.format(task_arn, cluster))
        return InvokedTask(response['tasks'][0])

    def list(self, cluster, service=None, family=None, container_instance=None, status='RUNNING'):
        # hint: (str["{cluster_name}"], str, str, str, choice[RUNNING|STOPPED|any])
        kwargs = {}
        kwargs['cluster'] = cluster
        if status != 'any':
            kwargs['desiredStatus'] = status
        if service:
            kwargs['serviceName'] = service
        if family:
            kwargs['family'] = family
        if container_instance:
            kwargs['containerInstance'] = container_instance
        try:
            response = self.client.list_tasks(**kwargs)
        except self.client.exceptions.ClusterNotFoundException:
            raise Cluster.DoesNotExist('No cluster named "{}" exists in AWS'.format(cluster))
        except self.client.exceptions.ServiceNotFoundException:
            raise Service.DoesNotExist('No service named "{}" exists in cluster "{}" in AWS'.format(service, cluster))
        return [self.get('{}:{}'.format(cluster, arn)) for arn in response['taskArns']]

    def save(self, obj):
        raise InvokedTask.ReadOnly('InvokedTasks are not modifiable')

    def delete(self, obj):
        self.client.stop_task(
            cluster=obj.cluster.name,
            task=obj.arn
        )


class ContainerInstanceManager(Manager):

    service = 'ecs'

    def __get_cluster_and_id_from_pk(self, pk):
        if isinstance(pk, ContainerInstance):
            cluster, container_instance_id = pk.pk.split(':', 1)
        else:
            cluster, container_instance_id = pk.split(':', 1)
        return cluster, container_instance_id

    def get(self, pk):
        """
        :param pk str: a string like "{cluster}:{container_instance_id}"
        """
        # This will give us the most recent versision of a task definition whose family is `name`
        cluster, container_instance_id = self.__get_cluster_and_id_from_pk(pk)
        try:
            response = self.client.describe_container_instances(
                cluster=cluster,
                containerInstances=[container_instance_id]
            )
        except self.client.exceptions.ClientException:
            raise ContainerInstance.DoesNotExist(
                'No container instance with id "{}" exists in cluster "{}"'.format(container_instance_id, cluster)
            )
        except self.client.exceptions.ClusterNotFoundException:
            raise Cluster.DoesNotExist(
                'No cluster named "{}" exists in AWS'.format(cluster)
            )
        return ContainerInstance(response['containerInstances'][0], cluster=cluster)

    def exists(self, pk):
        try:
            self.get(pk)
        except (ContainerInstance.DoesNotExist, Cluster.DoesNotExist):
            return False
        return True

    def list(self, cluster):
        try:
            response = self.client.list_container_instances(cluster=cluster)
        except self.client.exceptions.ClusterNotFoundException:
            raise Cluster.DoesNotExist
        return [self.get('{}:{}'.format(cluster, arn)) for arn in response['containerInstanceArns']]

    def save(self, obj):
        raise Cluster.ReadOnly('Container instances cannot be updated from deployfish')

    def delete(self, obj):
        raise Cluster.ReadOnly('Container instances cannot be updated from deployfish')


class ClusterManager(Manager):

    service = 'ecs'

    def get(self, pk):
        # hint: (str["{cluster_name}"])
        """
        :param pk str: cluster name
        """
        response = self.client.describe_clusters(
            clusters=[pk],
            include=['SETTINGS', 'STATISTICS', 'TAGS']
        )
        if response['clusters']:
            data = response['clusters'][0]
        else:
            raise Cluster.DoesNotExist(
                'No cluster named "{}" exists in AWS'.format(pk)
            )
        return Cluster(data)

    def get_many(self, pks):
        response = self.client.describe_clusters(
            clusters=pks,
            include=['SETTINGS', 'STATISTICS', 'TAGS']
        )
        return sorted([Cluster(data) for data in response['clusters']], key=lambda x: x.name)

    def list(self, cluster_name=None):
        # hint: (str["{cluster_name:glob}"])
        paginator = self.client.get_paginator('list_clusters')
        response_iterator = paginator.paginate()
        cluster_arns = []
        for response in response_iterator:
            cluster_arns.extend(response['clusterArns'])
        if cluster_name:
            clusters = {arn.split('/')[1]: arn for arn in cluster_arns}
            cluster_names = fnmatch.filter(list(clusters.keys()), cluster_name)
            cluster_arns = [clusters[name] for name in cluster_names]
        return self.get_many(cluster_arns)

    def exists(self, pk):
        try:
            self.get(pk)
        except Cluster.DoesNotExist:
            return False
        return True

    def save(self, obj):
        raise Cluster.ReadOnly('Clusters cannot be updated from deployfish')

    def delete(self, obj):
        raise Cluster.ReadOnly('Clusters cannot be updated from deployfish')


class ServiceManager(Manager):

    service = 'ecs'

    def __get_service_and_cluster_from_pk(self, pk):
        if isinstance(pk, Service):
            cluster, service = pk.pk.split(':')
        else:
            cluster, service = pk.split(':', 1)
        return service, cluster

    def get(self, pk):
        # hint: (str["{Cluster.name}:{Service.name}"])
        """
        :param pk str: a string like "{cluster_name}:{service_name}"
        """
        # Need these things out of AWS
        #
        #  * Most recent task definition: what will be run if we do `deploy task run`
        #  * Any scheduled task.  Note this may have a different task definition
        #  * TODO: a populated ParameterStore built out of the secrets in the first container's container definition
        # This will give us the most recent versision of a task definition whose family is `name`
        service, cluster = self.__get_service_and_cluster_from_pk(pk)
        try:
            response = self.client.describe_services(cluster=cluster, services=[service], include=['TAGS'])
        except self.client.exceptions.ClusterNotFoundException:
            raise Cluster.DoesNotExist('No cluster with name "{}" exists in AWS'.format(cluster))
        if response['services'] and response['services'][0]['status'] != 'INACTIVE':
            data = response['services'][0]
        else:
            raise Service.DoesNotExist(
                'No service named "{}" in cluster "{}" exists in AWS'.format(service, cluster)
            )
        data['cluster'] = data['clusterArn'].split('/')[-1]
        return Service(data)

    def get_many(self, pks):
        # group pks by cluster
        clusters = {}
        for pk in pks:
            service, cluster = self.__get_service_and_cluster_from_pk(pk)
            if cluster not in clusters:
                clusters[cluster] = []
            clusters[cluster].append(service)
        services = []
        for cluster, service_names in clusters.items():
            # describe_services only accepts 10 or fewer names in the services kwarg, so we have to
            # split them into sub lists of 10 of fewer names and iterate
            if len(service_names) > 10:
                chunks = [service_names[i * 10:(i + 1) * 10] for i in range((len(service_names) + 9) // 10)]
            else:
                chunks = [service_names]
            for chunk in chunks:
                try:
                    response = self.client.describe_services(cluster=cluster, services=chunk, include=['TAGS'])
                except self.client.exceptions.ClusterNotFoundException:
                    raise Cluster.DoesNotExist('No cluster with name "{}" exists in AWS'.format(cluster))
                if response['services']:
                    services.extend([s for s in response['services'] if s['status'] != 'INACTIVE'])
        obj = []
        for data in services:
            data['cluster'] = data['clusterArn'].split('/')[-1]
            obj.append(Service(data))
        return obj

    def exists(self, pk):
        # hint: (str["{cluster_name}:{service_name)"])
        service, cluster = self.__get_service_and_cluster_from_pk(pk)
        try:
            response = self.client.describe_services(cluster=cluster, services=[service])
        except self.client.exceptions.ClusterNotFoundException:
            raise Cluster.DoesNotExist('No cluster with name "{}" exists in AWS'.format(cluster))
        if response['services'] and response['services'][0]['status'] != 'INACTIVE':
            # FIXME: INACTIVE should not be considered the same as non-existant
            return True
        return False

    def list(self, cluster_name=None, service_name=None, launch_type='any', scheduling_strategy='any'):
        # hint: (str["{cluster_name:glob}"], str["{service_name:glob}"], choice[EC2|FARGATE|any], choice[REPLICA|DAEMON|any])
        if launch_type not in ['any', 'EC2', 'FARGATE']:
            raise self.OperationFailed(
                '{} is not a valid launch_type.  Valid types are: EC2, FARGATE.'.format(launch_type)
            )
        if scheduling_strategy not in ['any', 'REPLICA', 'DAEMON']:
            raise self.OperationFailed(
                '{} is not a valid launch_type.  Valid types are: EC2, FARGATE.'.format(launch_type)
            )
        if launch_type == 'any':
            launch_type = None
        if scheduling_strategy not in ['any', 'DAEMON', 'REPLICA']:
            raise self.OperationFailed(
                '{} is not a valid scheduling strategy.  Valid strategies are: DAEMON, REPLICA.'.format(launch_type)
            )
        if scheduling_strategy == 'any':
            scheduling_strategy = None
        paginator = self.client.get_paginator('list_clusters')
        response_iterator = paginator.paginate()
        cluster_arns = []
        for response in response_iterator:
            cluster_arns.extend(response['clusterArns'])
        clusters = [arn.rsplit('/', 1)[1] for arn in cluster_arns]
        if cluster_name:
            clusters = fnmatch.filter(clusters, cluster_name)
        services = []
        for cluster in clusters:
            kwargs = {'cluster': cluster}
            if launch_type:
                kwargs['launchType'] = launch_type
            if scheduling_strategy:
                kwargs['schedulingStrategy'] = scheduling_strategy
            paginator = self.client.get_paginator('list_services')
            response_iterator = paginator.paginate(**kwargs)
            try:
                for response in response_iterator:
                    services.extend("{}:{}".format(cluster, arn) for arn in response['serviceArns'])
            except self.client.exceptions.ClusterNotFoundException:
                raise Cluster.DoesNotExist('No cluster with name "{}" exists in AWS'.format(cluster))
        if service_name:
            services = [arn for arn in services if fnmatch.fnmatch(arn.rsplit('/')[1], service_name)]
        return self.get_many(services)

    def save(self, obj):
        # hint: (deployfish.core.models.Service)
        if self.exists(obj):
            self.update(obj)
        else:
            self.create(obj)

    def create(self, obj):
        # hint: (deployfish.core.models.Service)
        if not self.exists(obj.pk):
            try:
                self.client.create_service(**obj.render_for_create())
            except self.client.exceptions.ClusterNotFoundException:
                raise Cluster.DoesNotExist('No cluster with name "{}" exists in AWS'.format(obj.data['cluster']))

    def update(self, obj):
        # hint: (deployfish.core.models.Service)
        service, cluster = self.__get_service_and_cluster_from_pk(obj.pk)
        if self.exists(obj.pk):
            try:
                self.client.update_service(**obj.render_for_update())
            except self.client.exceptions.ServiceNotActiveException:
                raise Service.OperationFailed(
                    'Service named "{}" in cluster "{}" in AWS cannot be updated: not ACTIVE'.format(service, cluster)
                )
        else:
            raise Service.DoesNotExist('No service named "{}" exists in cluster "{}" in AWS'.format(service, cluster))

    def delete(self, obj):
        # hint: (deployfish.core.models.Service)
        if self.exists(obj.pk):
            if not obj.arn:
                obj.reload_from_db()
            # Delete any ScalingTargets
            if obj.appscaling:
                obj.appscaling.delete()
            # Delete any ServiceDiscoveryService
            if obj.service_discovery:
                obj.service_discovery.delete()
            # Unschedule any scheduled helper tasks
            for task in obj.helper_tasks:
                task.unschedule()
            # first scale to 0
            service, cluster = self.__get_service_and_cluster_from_pk(obj.pk)
            if obj.data['desiredCount'] > 0:
                self.scale(obj, 0)
                waiter = self.get_waiter('services_stable')
                waiter.wait(cluster=cluster, services=[service])
            # Then delete the service
            self.client.delete_service(cluster=cluster, service=service)

    def scale(self, obj, count):
        self.client.update_service(**obj.render_for_scale(count))


# ----------------------------------------
# Models
# ----------------------------------------

class TaskDefinition(TagsMixin, TaskDefinitionFARGATEMixin, SecretsMixin, Model):
    """
    An ECS Task Definition.

    .. note::

        An AWS, the task definition object contains all the configuration for each of the containers that
        will be part of the task, but in deployfish we put container definitions into ``ContainerDefinition``
        objects so that we can work with them more effectively.

    ``TaskDefinition.data`` looks like this::

        'taskDefinitionArn': 'string',                        This will not be present if we loaded from deployfish.yml
        'family': 'string',
        'taskRoleArn': 'string',                              [optional]
        'executionRoleArn': 'string',                         [optional]
        'networkMode': 'bridge'|'host'|'awsvpc'|'none',
        'compatibilities': [
            'EC2'|'FARGATE',
        ],
        'requiresCompatibilities': [                          This will not be present if we loaded from deployfish.yml
            'EC2'|'FARGATE',
        ],
        'status': 'ACTIVE|INACTIVE',
        'cpu': 'string',
        'memory': 'string',
        'revision': 123,                                      This will not be present if we loaded from deployfish.yml
        'volumes': [                                          [optional]
            {
                'name': 'string',
                'host': {
                    'sourcePath': 'string'
                },
                'dockerVolumeConfiguration': {
                    'scope': 'task'|'shared',
                    'autoprovision': True|False,
                    'driver': 'string',
                    'driverOpts': {
                        'string': 'string'
                    },
                    'labels': {
                        'string': 'string'
                    }
                },
            }
        ]
        'tags': [
            {
                'key': 'string',
                'value': 'string'
            }
        ]

    """

    objects = TaskDefinitionManager()

    @classmethod
    def new(cls, obj, source, **kwargs):
        data, kwargs = cls.adapt(obj, source, **kwargs)
        containers = []
        for d, c_kwargs in kwargs['containers']:
            container = ContainerDefinition(d)
            if 'secrets' in c_kwargs:
                container.cache['secrets'] = c_kwargs['secrets']
            containers.append(container)
        return cls(data, containers=containers)

    def __init__(self, data, containers=None):
        super(TaskDefinition, self).__init__(data)
        self.containers = containers

    @property
    def pk(self):
        """
        If this task definition exists in AWS, return our ``<family>:<revision>`` string.
        Else, return just the family.

        :rtype: string or ``None``
        """
        if self.revision:
            return "{}:{}".format(self.data['family'], self.revision)
        else:
            return self.data['family']

    @property
    def name(self):
        return self.pk

    @property
    def arn(self):
        return self.data.get('taskDefinitionArn', None)

    @property
    def family(self):
        return self.data['family']

    @property
    def deployfish_environment(self):
        return self.containers[0].deployfish_environment

    @property
    def revision(self):
        return self.data.get('revsion', None)

    @property
    def version(self):
        """
        Return the version for the task definition.  We're cheating here by just returning the version of the first
        container image, assuming that the first container will be the primary container for the TaskDefinition.

        :rtype: str
        """
        return self.containers[0].version

    @property
    def secrets_prefix(self):
        if self.secrets:
            return self.secrets.values()[0].prefix
        else:
            raise self.ImproperlyConfigured(
                'Can\'t determine secrets prefix for TaskDefinition(pk="{}"): it has no secrets'.format(self.pk)
            )

    @property
    def secrets(self):
        if 'secrets' not in self.cache:
            self.cache['secrets'] = {s.secret_name: s for s in self.containers[0].secrets}
        return self.cache['secrets']

    def reload_secrets(self):
        super(TaskDefinition, self).reload_secrets()
        for c in self.containers:
            c.reload_secrets()

    @property
    def logging(self):
        return self.containers[0].data.get('logConfiguration', None)

    def copy(self):
        data = deepcopy(self.data)
        if 'taskDefinitionArn' in data:
            del data['taskDefinitionArn']
            del data['status']
            del data['revision']
            del data['registeredAt']
            del data['registeredBy']
            if 'compatibilities' in data:
                data['requiresCompatibilities'] = data['compatibilities']
                del data['compatibilities']
            if 'requiresAttributes' in data:
                del data['requiresAttributes']
        else:
            if 'placementConstraints' not in data:
                data['placementConstraints'] = []
            if 'requiresCompatibilities' not in data:
                data['requiresCompatibilities'] = ['EC2']
        containers = [c.copy() for c in self.containers]
        return self.__class__(data, containers=containers)

    def render_for_display(self):
        data = self.render()
        if 'taskDefinitionArn' not in data:
            data['taskDefinitionArn'] = None
            data['status'] = 'NONE'
            data['revision'] = None
            data['registeredAt'] = 'NONE'
            data['registeredBy'] = 'NONE'
            data['requiresAttributes'] = []
            if 'placementConstraints' not in data:
                data['placementConstraints'] = []
            if 'requiresCompatibilities' not in data:
                data['requiresCompatibilities'] = ['EC2']
            data['family_revision'] = data['family']
        else:
            data['family_revision'] = "{}:{}".format(data['family'], data['revision'])
        data['version'] = self.version
        if 'compatibilities' in data:
            data['requiresCompatibilities'] = data['compatibilities']
            del data['compatibilities']
        if 'volumes' in data:
            for volume in data['volumes']:
                if 'efsVolumeConfiguration' in volume:
                    volume['efsVolumeConfiguration']['FileSystem'] = EFSFileSystem.objects.get(
                        volume['efsVolumeConfiguration']['fileSystemId']
                    )
        return data

    def render_for_diff(self):
        data = self.render()
        if 'taskDefinitionArn' in data:
            del data['taskDefinitionArn']
            del data['status']
            del data['revision']
            del data['registeredAt']
            del data['registeredBy']
            if 'compatibilities' in data:
                data['requiresCompatibilities'] = data['compatibilities']
                del data['compatibilities']
            if 'requiresAttributes' in data:
                del data['requiresAttributes']
        else:
            if 'placementConstraints' not in data:
                data['placementConstraints'] = []
            if 'requiresCompatibilities' not in data:
                data['requiresCompatibilities'] = ['EC2']

        return data

    def render(self):
        data = deepcopy(self.data)
        self.autofill_fargate_parameters(data)
        data['containerDefinitions'] = [c.render() for c in sorted(self.containers, key=lambda x: x.name)]
        if 'executionRoleArn' not in data:
            # If we don't have an execution role, we can't write secrets into our task definition, beause without
            # the execution role, the container won't be able to start because it won't have permissions to read
            # the secrets from AWS SSM Paramter Store.
            for d in data['containerDefinitions']:
                if 'secrets' in d:
                    del d['secrets']
        data['tags'] = self.render_tags()
        if not data['tags']:
            del data['tags']
        return data

    def save(self):
        return self.objects.save(self)

    def __add__(self, other):
        new_td = self.copy()
        new_td.data.update(other.data)
        new_td.tags.update(other.tags)
        old_containers = new_td.containers
        other_containers = {c.name: c for c in other.containers}
        new_containers = []
        for container in old_containers:
            if container.name in other_containers:
                new_containers.append(container + other_containers[container.name])
            else:
                new_containers.append(container)
        new_td.containers = new_containers
        # We may have changed this task from a EC2 to FARGATE task, and thus we may need to set
        # our task cpu and memory properly.
        container_data = [c.data for c in new_td.containers]
        new_td.set_task_cpu(new_td.data, container_data)
        new_td.set_task_memory(new_td.data, container_data)
        return new_td


class ContainerDefinition(SecretsMixin, LazyAttributeMixin):

    helper_task_prefix = 'edu.caltech.task'

    def __init__(self, data):
        super(ContainerDefinition, self).__init__()
        self.data = data

    @property
    def name(self):
        return self.data.get('name', None)

    @property
    def version(self):
        try:
            return self.data['image'].rsplit(':', 1)[1]
        except IndexError:
            return 'latest'

    @property
    def secrets_prefix(self):
        if self.secrets:
            return self.secrets.values()[0].prefix
        else:
            raise self.ImproperlyConfigured(
                'Can\'t determine secrets prefix for ContainerDefinition(pk="{}"): it has no secrets'.format(self.pk)
            )

    @property
    def secrets(self):
        if 'secrets' not in self.cache:
            if 'secrets' in self.data:
                # FIXME: should we be splitting these into Secrets and ExternalSecrets so we can do comparisons
                names = [s['valueFrom'] for s in self.data['secrets']]
                self.cache['secrets'] = Secret.objects.get_many(names)
            else:
                self.cache['secrets'] = []
        return self.cache['secrets']

    @property
    def deployfish_environment(self):
        env_dict = {var['name']: var['value'] for var in self.data.get('environment', [])}
        return env_dict.get('DEPLOYFISH_ENVIRONMENT', 'undefined')

    def render_for_diff(self):
        data = deepcopy(self.data)
        if 'environment' in data:
            environment = {x['name']: x['value'] for x in data['environment']}
            data['environment'] = environment
        if 'secrets' in data:
            secrets = {x['name']: x['valueFrom'] for x in data['secrets']}
            data['secrets'] = secrets
        if 'volumesFrom' not in data:
            data['volumesFrom'] = []
        if 'mountPoints' not in data:
            data['mountPoints'] = []
        return data

    def render(self):
        return deepcopy(self.data)

    def copy(self):
        return self.__class__(self.render())

    def __add__(self, other):
        c = self.copy()
        c.data.update(other.data)
        return c


class Task(TagsMixin, Model):
    """
    Tasks are TaskDefinitions with additional on how to run them as tasks.  Tasks can also be scheduled using Cloudwatch
    Events Rules.

    Tasks are odd things compared to all the other Model subclasses we have because they have ephemeral configuration
    associated with them that does not get written to AWS upon save:

        * the config used to actually run the task: cluster, networkConfiguration, launchType, desiredCount, etc.
        * the config we use to de-reference this task back to the service it belongs to, if any: serviceName

    Config we need in order to run the task:

        cluster: what cluster to run the task in
        desiredCount: how many tasks to actually run
        launchType: EC2 or FARGATE
        platformVersion: (optional) only used if launchType == FARGATE
        networkConfiguration.awsvpcConfiguration: If the task definition's networkMode is 'awsvpc', this tells us
            what subnets in which to run the tasks, and which security groups to assign to them
        capacityProviderStrategy: (optional) the capacity provider strategy to use, if any.  This is mutually
            exclusive with launchType
        placementConstraints: (optional) placement constraints for running the task
        placementStrategy: (optional) the placement strategy for running the task
        group: (optional)the task group

    We write these as tags on the task defintiion:

        * Need 5 tags for cluster, count, launchType, platformVersion
        * 1 tag for service pk
        * Capacity provider: 1 per item in list, so maybe max 2
        * placement constraints: 1-4
        * placement strategy: 1-2
        * name 1
        * networkConfiguration 16 subnets, 5 securitygroups, allowPublicIP -- 22 tags
        * Sum: max 37 tags
    """

    objects = None

    def __init__(self, data, task_definition=None, schedule=None):
        super(Task, self).__init__(data)
        self.task_definition = task_definition
        self.schedule = schedule

    @property
    def service(self):
        if 'service' not in self.cache:
            if 'service' in self.data:
                self.cache['service'] = Service.objects.get(self.data['service'])
            else:
                self.cache['service'] = None
        return self.cache['service']

    @property
    def cluster(self):
        if 'cluster' not in self.cache:
            self.cache['cluster'] = Cluster.objects.get(self.data['cluster'])
        return self.cache['cluster']

    @property
    def tags(self):
        return self.task_definition.tags

    @property
    def secrets(self):
        raise NotImplementedError

    @property
    def pk(self):
        return self.task_definition.pk

    @property
    def name(self):
        return self.pk

    @property
    def arn(self):
        return self.task_definition.arn

    @property
    def family(self):
        return self.task_definition.family

    @property
    def version(self):
        return self.task_definition.version

    @property
    def running_tasks(self):
        pass

    def run(self):
        return self.objects.run(self)

    def render(self):
        data = super(Task, self).render()
        if 'name' in data:
            del data['name']
        del data['task_type']
        if 'service' in data:
            del data['service']
        return data

    def schedule(self):
        """
        Schedule the task.
        """
        self.schedule.set_task_definition_arn(self.arn)
        self.schedule.save()

    def unschedule(self):
        if self.schedule:
            self.schedule.delete()

    def enable_schedule(self):
        if self.schedule:
            self.schedule.enable()

    def disable_schedule(self):
        if self.schedule:
            self.schedule.disable()

    def render_for_display(self):
        data = deepcopy(self.data)
        if 'service' in self.data:
            data['serviceName'] = data['service'].split(':')[1]
        else:
            data['serviceName'] = ''
        data.update(self.task_definition.render_for_display())
        data['schedule_expression'] = ''
        data['schedule_disabled'] = ''
        if self.schedule:
            data['schedule_expression'] = self.schedule.data['ScheduleExpression']
            data['schedule_disabled'] = 'DISABLED' if not self.schedule.enabled else ''
        return data


class StandaloneTask(SecretsMixin, Task):
    """
    StandaloneTasks are TaskDefinitions with their own configuration, apart from that of a Service.  They
    are defined in the top level "tasks" section of deployfish.yml.
    """
    config_section = 'tasks'

    objects = StandaloneTaskManager()

    @property
    def secrets_prefix(self):
        """
        Return the prefix we use to save our AWS Parameter Store Parameters to AWS.

        :rtype: str
        """
        return '{}.task-{}.'.format(self.data['cluster'], self.name)

    @property
    def secrets(self):
        if 'secrets' not in self.cache:
            self.cache['secrets'] = self.task_definition.secrets
        return self.cache['secrets']

    def reload_secrets(self):
        """
        Reload our AWS SSM Paramter Store secrets from AWS.
        """
        super().reload_secrets()
        self.task_definition.reload_secrets()


# We need to set the manager model this way to avoid circular references
StandaloneTaskManager.model = StandaloneTask  # noqa:E305


class ServiceHelperTask(Task):

    objects = ServiceHelperTaskManager()

    @classmethod
    def new(cls, obj, source, **kwargs):
        # Services may have many helper tasks, so cls.adapt returns lists
        # of data and kwargs dicts
        data_list, kwargs_list = cls.adapt(obj, source, **kwargs)
        instances = []
        for i, data in enumerate(data_list):
            instances.append(cls(data, **kwargs_list[i]))
        return instances

    @property
    def command(self):
        return self.data['name']

# We need to set the manager model this way to avoid circular references
ServiceHelperTaskManager.model = ServiceHelperTask  # noqa:E305


class InvokedTask(DockerMixin, Model):
    """
    A record of a running AWS ECS Task, which means either a task running as part of a Service, a StandaloneTask or a
    ServiceHelperTask.
    """

    objects = InvokedTaskManager()

    @property
    def pk(self):
        return '{}:{}'.format(self.cluster_name, self.arn)

    @property
    def name(self):
        return self.arn.rsplit('/')[1]

    @property
    def arn(self):
        return self.data['taskArn']

    @property
    def task_definition(self):
        if 'task_definition' not in self.cache:
            self.cache['task_definition'] = TaskDefinition.objects.get(self.data['taskDefinitionArn'])
        return self.cache['task_definition']

    @property
    def containers(self):
        return self.task_definition.containers

    @property
    def instance(self):
        return self.container_instance.ec2_instance

    @property
    def ssh_target(self):
        """
        .. warning::

            If this is a FARGATE task, we won't have a container instance.
        """
        if self.container_instance:
            return self.container_instance.ec2_instance
        else:
            return None

    @property
    def cluster_name(self):
        return self.data['clusterArn'].split('/')[-1]

    @property
    def cluster(self):
        return self.get_cached('cluster', Cluster.objects.get, [self.cluster_name])

    @property
    def container_instance(self):
        # This may not work for FARGATE tasks -- do they return containerInstanceArn?
        try:
            return self.get_cached(
                'container_machine',
                ContainerInstance.objects.get,
                ['{}:{}'.format(self.cluster_name, self.data['containerInstanceArn'])]
            )
        except KeyError:
            # this is a FARGATE task
            return None

    def render_for_display(self):
        data = self.render()
        data['version'] = self.task_definition.version
        data['cluster'] = self.cluster_name
        if self.container_instance:
            data['instanceName'] = self.container_instance.name
            data['instanceId'] = self.container_instance.ec2_instance.pk
        else:
            data['instanceName'] = ''
            data['instanceId'] = ''
        data['taskDefinition'] = self.task_definition.render_for_display()
        return data


class ContainerInstance(SSHMixin, Model):

    objects = ContainerInstanceManager()

    def __init__(self, data, cluster=None):
        super(ContainerInstance, self).__init__(data)
        self.cluster = cluster

    @property
    def pk(self):
        return '{}:{}'.format(self.cluster, self.arn)

    @property
    def name(self):
        return self.ec2_instance.name

    @property
    def arn(self):
        return self.data['containerInstanceArn']

    @property
    def ssh_target(self):
        return self.ec2_instance

    @property
    def ec2_instance(self):
        return self.get_cached('ec2_instance', Instance.objects.get, [self.data['ec2InstanceId']])

    @property
    def autoscaling_group(self):
        return self.ec2_instance.autoscaling_group

    @property
    def running_tasks(self):
        return InvokedTask.objects.list(self.cluster, container_instance=self.arn)

    def get_remaining_resource(self, name):
        for resource in self.data['remainingResources']:
            if resource['name'] == name:
                if resource['type'] == 'LONG':
                    return resource['longValue']
                elif resource['type'] == 'INTEGER':
                    return resource['integerValue']
                elif resource['type'] == 'DOUBLE':
                    return resource['doubleValue']
                elif resource['type'] == 'STRINGSET':
                    return resource['stringSetValue']

    @property
    def free_cpu(self):
        return self.get_remaining_resource('CPU')

    @property
    def free_memory(self):
        return self.get_remaining_resource('MEMORY')


class Cluster(TagsMixin, SSHMixin, Model):
    """
    An ECS cluster.
    """

    objects = ClusterManager()

    @property
    def pk(self):
        return self.data['clusterName']

    @property
    def name(self):
        return self.data['clusterName']

    @property
    def arn(self):
        return self.data['clusterArn']

    @property
    def ssh_target(self):
        if len(self.container_instances) > 0:
            return self.container_instances[0].ec2_instance
        else:
            raise self.NoSSHTargetAvailable('Cluster "{}" has no container instances'.format(self.name))

    @property
    def ssh_targets(self):
        return self.ec2_instances

    @property
    def container_instances(self):
        return self.get_cached('container_instances', ContainerInstance.objects.list, [self.pk])

    @property
    def ec2_instances(self):
        if 'ec2_instances' not in self.cache:
            self.cache['ec2_instances'] = [i.ec2_instance for i in self.container_instances]
        return self.cache['ec2_instances']

    def ssh_command_all_instances(self, cmd):
        responses = []
        for instance in self.ec2_instances:
            success, output = instance.ssh_command(cmd)
            responses.append((success, output))
        return responses

    @property
    def running_tasks(self):
        return InvokedTask.objects.list(self.name)

    @property
    def services(self):
        return self.get_cached('services', Service.objects.list, [self.pk])

    @property
    def autoscaling_group(self):
        if 'autoscaling_group' not in self.cache:
            if 'deployfish:autoscalingGroup' in self.tags:
                self.cache['autoscaling_group'] = AutoscalingGroup.objects.get(self.tags['deployfish:autoscalingGroup'])
            elif len(self.container_instances) > 0:
                self.cache['autoscaling_group'] = self.container_instances[0].autoscaling_group
            else:
                # Try to guess our autoscaling group based on our cluster name
                try:
                    self.cache['autoscaling_group'] = AutoscalingGroup.objects.get(self.name)
                except AutoscalingGroup.DoesNotExist:
                    self.cache['autoscaling_group'] = None
        return self.cache.get('autoscaling_group', None)

    def scale(self, count, force=True):
        if self.autoscaling_group:
            self.autoscaling_group.scale(count, force=force)
        else:
            raise self.OperationFailed(
                'Could not find autoscaling group for Cluster(pk="{}"); ignoring scaling request.'.format(self.pk)
            )


class Service(TagsMixin, DockerMixin, SecretsMixin, Model):

    config_section = 'services'

    objects = ServiceManager()

    @classmethod
    def new(cls, obj, source, **kwargs):
        data, data_kwargs = cls.adapt(obj, source, **kwargs)
        instance = cls(data)
        if 'task_definition' in data_kwargs:
            instance.task_definition = data_kwargs['task_definition']
        if 'appscaling' in data_kwargs:
            instance.appscaling = data_kwargs['appscaling']
        if 'service_discovery' in data_kwargs:
            instance.service_discovery = data_kwargs['service_discovery']
        if 'ssh_proxy_type' in data_kwargs:
            instance.ssh_proxy_type = data_kwargs['ssh_proxy_type']
        if 'autoscalinggroup_name' in data_kwargs:
            instance.autoscalinggroup_name = data_kwargs['autoscalinggroup_name']
        if 'tags' in data_kwargs:
            instance.tags.update(data_kwargs['tags'])
        instance.helper_tasks = ServiceHelperTask.new(obj, source, service=instance)
        return instance

    @property
    def deployfish_environment(self):
        """
        Return our deployfish environment: ("test", "prod", etc.).  Note: not the docker environment, which is a list
        of environment variables to set in the container environment.

        :rtype: str
        """
        return self.tags.get('deployfish:Environment', 'test')

    @property
    def secrets_prefix(self):
        """
        Return the prefix we use to save our AWS Parameter Store Parameters to AWS.

        :rtype: str
        """
        return '{}.{}.'.format(self.data['cluster'], self.name)

    @property
    def secrets(self):
        if 'secrets' not in self.cache:
            self.cache['secrets'] = self.task_definition.secrets
        return self.cache['secrets']

    def reload_secrets(self):
        """
        Reload our AWS SSM Paramter Store secrets from AWS.
        """
        super(Service, self).reload_secrets()
        self.task_definition.reload_secrets()

    @property
    def appscaling(self):
        if 'appscaling' not in self.cache:
            try:
                self.cache['appscaling'] = ScalableTarget.objects.get('service/{}/{}'.format(
                    self.data['cluster'],
                    self.data['serviceName']
                ))
            except ScalableTarget.DoesNotExist:
                self.cache['appscaling'] = None
        return self.cache['appscaling']

    @appscaling.setter
    def appscaling(self, value):
        self.cache['appscaling'] = value

    @property
    def service_discovery(self):
        if 'service_discovery' not in self.cache:
            if 'serviceRegistries' in self.data and self.data['serviceRegistries']:
                pk = self.data['serviceRegistries'][0]['registryArn']
                try:
                    self.cache['service_discovery'] = ServiceDiscoveryService.objects.get(pk)
                except ServiceDiscoveryService.DoesNotExist:
                    self.cache['service_discovery'] = None
            else:
                self.cache['service_discovery'] = None
        return self.cache['service_discovery']

    @service_discovery.setter
    def service_discovery(self, value):
        """
        Save a ServiceDiscoveryService object as self.cache['service_discovery'].  We do this when loading
        configuraiton from deployfish.yml, in Service.new().

        :param value ServiceDiscoveryService: a configured ServiceDiscoveryService object

        .. note::

            The ServiceDiscoveryService we get here may not be saved to AWS yet, so may not
            have an ARN.  We therefore set the `serviceRegistries' key in self.data in self.save(), after
            saving the ServiceDiscoveryService.
        """
        self.cache['service_discovery'] = value

    @property
    def task_definition(self):
        if 'task_definition' not in self.cache:
            self.cache['task_definition'] = TaskDefinition.objects.get(self.data['taskDefinition'])
        return self.cache['task_definition']

    @task_definition.setter
    def task_definition(self, value):
        self.cache['task_definition'] = value

    @property
    def load_balancers(self):
        if 'load_balancers' not in self.cache:
            lbs = []
            for lb in self.data['loadBalancers']:
                data = deepcopy(lb)
                if 'targetGroupArn' in lb:
                    data['TargetGroup'] = TargetGroup.objects.get(data['targetGroupArn'])
                else:
                    data['LoadBalancer'] = ClassicLoadBalancer.objects.get(data['loadBalancerName'])
                lbs.append(data)
            self.cache['load_balancers'] = lbs
        return self.cache['load_balancers']

    @property
    def helper_tasks(self):
        if 'helper_tasks' not in self.cache:
            command_arns = [
                self.task_definition.tags[t]
                for t in self.task_definition.tags
                if t.startswith('deployfish:command:')
            ]
            self.cache['helper_tasks'] = ServiceHelperTask.objects.get_many(command_arns)
        return self.cache['helper_tasks']

    @helper_tasks.setter
    def helper_tasks(self, value):
        self.cache['helper_tasks'] = value

    @property
    def autoscaling_group(self):
        if 'autoscaling_group' in self.cache:
            if hasattr(self, 'autoscalinggroup_name'):
                self.cache['autoscaling_group'] = AutoscalingGroup.objects.get(self.autoscalinggroup_name)
            else:
                self.cache['autoscaling_group'] = self.cluster.autoscaling_group
        return self.cache['autoscaling_group']

    @property
    def containers(self):
        """
        This returns a list of  ``ContainerDefinition`` objects in the ``TaskDefinition`` for the PRIMARY deployment for
        the service.  If you want the list of actual running containers for the service, use
        ``self.running_containers``.
        """
        return self.task_definition.containers

    @property
    def ssh_tunnels(self):
        # We're doing this import here to hopefully avoid circular dependencies between this file and ./ssh.py
        from .ssh import SSHTunnel
        # We actually want the live service here -- no point in tunneling to a service that doesn't
        # exist or is out of date with deployfish.yml
        service = self
        if self.arn is None:
            # if self.arn is None, we got loaded from deployfish.yml
            service = self.objects.get('{}:{}'.format(self.data['cluster'], self.name))
        tunnels = {t.name: t for t in SSHTunnel.objects.list(service_name=self.name)}
        for tunnel in tunnels.values():
            tunnel.service = service
        return tunnels

    @property
    def pk(self):
        return ':'.join([self.data['cluster'], self.data['serviceName']])

    @property
    def name(self):
        return self.data['serviceName']

    @property
    def arn(self):
        return self.data.get('serviceArn', None)

    @property
    def status(self):
        return self.data.get('status', 'UNKNOWN')

    @property
    def events(self):
        return self.data.get('events', [])

    @property
    def deployments(self):
        return self.data.get('deployments', [])

    @property
    def cluster(self):
        return self.get_cached('cluster', Cluster.objects.get, [self.data['cluster']])

    @property
    def version(self):
        return self.task_definition.version

    @property
    def ssh_target(self):
        if self.container_instances:
            return self.container_instances[0].ec2_instance
        else:
            raise self.NoRunningTasks(
                'Service "{}" has no running tasks.'.format(self.data['serviceName'])
            )

    @property
    def ssh_targets(self):
        return [instance.ec2_instance for instance in self.container_instances]

    @property
    def running_tasks(self):
        return InvokedTask.objects.list(self.data['cluster'], service=self.name)

    @property
    def container_instances(self):
        if 'container_instances' not in self.cache:
            self.cache['container_instances'] = [
                task.container_instance for task in self.running_tasks
            ]
        return self.cache['container_instances']

    # Custom actions

    def scale(self, count):
        """
        Set the desiredCount for our service to `count`.

        .. warning::

            This only touches the Service itself.  If you need to scale the cluster also, use self.cluster.scale()
            first.

        :param count int: set the Service's desired count to this.
        """
        self.objects.scale(self, count)

    def restart(self, hard=False, waiter_hooks=None):
        """
        Restart the running tasks for a service.  What this really means is kill off each task in the service and let
        ECS start new ones in their places.

        :param hard bool: if `True`, kill all tasks immediately; if `False`, wait for the service to stabilize after
                          killing each task
        :param waiter_hooks list(AbstractWaiterHook): a list of waiter hooks to use when invoking the 'services_stable'
                          waiter
        """
        if not waiter_hooks:
            waiter_hooks = []
        waiter = self.objects.get_waiter('services_stable')
        for task in self.running_tasks:
            task.delete()
            if not hard:
                waiter.wait(
                    cluster=self.data['cluster'],
                    services=[self.name],
                    WaiterHooks=waiter_hooks
                )
        if hard:
            waiter.wait(
                cluster=self.data['cluster'],
                services=[self.name],
                WaiterHooks=waiter_hooks
            )

    # Renders

    def render_for_update(self):
        """
        Prepare the AWS payload for boto3.client('ecs').update_service().  This will be called by
        ServiceManager.update(), which is in turn called by ServiceManager.save(), which is in its own turn called by
        Service.save().

        .. note::

            We expect that the Service's new task definition will have been saved by Service.save() before this is
            called by ServiceManager.update(), and the ARN of that TaskDefinition will have been saved as
            self.data['taskDefinition'].
        """
        data = {}
        data['service'] = self.data['serviceName']
        data['cluster'] = self.data['cluster']
        # Purposely not setting desiredCount here -- we may be scaled up, so we shouldn't be scaling back to whatever
        # deployfish.yml says lest we underprovision the service inadvertently
        data['taskDefinition'] = self.data['taskDefinition']
        if 'capacityProviderStrategy' in self.data:
            data['capacityProviderStrategy'] = self.data['capacityProviderStrategy']
        else:
            if 'launchType' in self.data and self.data['launchType'] == 'FARGATE':
                data['platformVersion'] = self.data.get('platformVersion', 'LATEST')
        if 'deploymentConfiguration' in self.data:
            data['deploymentConfiguration'] = self.data['deploymentConfiguration']
        if 'networkConfiguration' in self.data:
            data['networkConfiguration'] = self.data['networkConfiguration']
        if 'placementConstraints' in self.data:
            data['placementConstraints'] = self.data['placementConstraints']
        if 'placementStrategy' in self.data:
            data['placementStrategy'] = self.data['placementStrategy']
        # Note: You can't write tags in the update_service() API call, so don't try
        return data

    def render_for_scale(self, count):
        """
        Prepare the payload for boto3.client('ecs').update_service() when all we want to do is change ``desiredCount``.
        This will be called by ServiceManager.scale() which will itself be called by Service.scale().
        """
        data = {}
        data['service'] = self.data['serviceName']
        data['cluster'] = self.data['cluster']
        data['desiredCount'] = count
        return data

    def render_for_create(self):
        data = self.render()
        data['tags'] = self.render_tags()
        if 'serviceArn' in data:
            del data['serviceArn']
            del data['clusterArn']
            del data['createdAt']
            del data['createdBy']
            if 'taskSets' in data:
                del data['taskSets']
            if 'deployments' in data:
                del data['deployments']
            if 'events' in data:
                del data['events']
        return data

    def render_for_diff(self):
        """
        For self.diff() to work correctly, we have to make the data returned by
        boto3.client('ecs').describe_services() and data loaded from deployfish.yml have the same keys.

        This means:

            * Strip any object specific info from the AWS data (ARNs for example)
            * Strip any ephemeral data from the AWS data (events, deployments, desiredCount, etc.)
            * Add keys to the deployfish side that get auto-populated upon service creation, or which
              we don't send and which we just take the defaults
        """
        data = self.render()
        data['tags'] = self.render_tags()
        if 'desiredCount' in data:
            del data['desiredCount']
        if 'role' in data:
            # We loaded this from deployfish.yml, so we need to define some default
            # values that appear when you describe_services on an active service
            data['roleArn'] = data['role']
            del data['role']
            data['status'] = 'ACTIVE'
            data['propagateTags'] = 'NONE'
            data['enableECSManagedTags'] = False
            data['enableExecuteCommand'] = False
            data['healthCheckGracePeriodSeconds'] = 0
            if 'deploymentConfiguration' not in data:
                data['deploymentConfiguration'] = {}
                data['deploymentConfiguration']['maximumPercent'] = 200
                data['deploymentConfiguration']['minimumHealthyPercent'] = 50
            if 'placementConstraints' not in data:
                data['placementConstraints'] = []
            if 'placementStrategy' not in data:
                data['placementStrategy'] = []
        if 'clientToken' in data:
            del data['clientToken']
        if 'createdAt' in data:
            # We loaded this from AWS, so we need to remove some things
            del data['serviceArn']
            del data['clusterArn']
            del data['runningCount']
            del data['pendingCount']
            del data['createdAt']
            if 'serviceRegistries' in data:
                del data['serviceRegistries']
            if 'createdBy' in data:
                del data['createdBy']
            if 'taskSets' in data:
                del data['taskSets']
            if 'deployments' in data:
                del data['deployments']
            if 'events' in data:
                del data['events']
        data['taskDefinition'] = self.task_definition.render_for_diff()
        if self.appscaling:
            data['appscaling'] = self.appscaling.render_for_diff()
        if self.service_discovery:
            data['service_discovery'] = self.service_discovery.render_for_diff()
        return data

    def render_for_display(self):
        data = self.render()
        data['version'] = self.version
        if 'role' in data:
            # We loaded this from deployfish.yml, so we need to define some default
            # values that appear when you describe_services on an active service
            data['roleArn'] = data['role']
            del data['role']
            data['status'] = 'ACTIVE'
            data['propagateTags'] = 'NONE'
            data['enableECSManagedTags'] = False
            data['enableExecuteCommand'] = False
            data['healthCheckGracePeriodSeconds'] = 0
            if 'deploymentConfiguration' not in data:
                data['deploymentConfiguration'] = {}
                data['deploymentConfiguration']['maximumPercent'] = 200
                data['deploymentConfiguration']['minimumHealthyPercent'] = 50
            if 'placementConstraints' not in data:
                data['placementConstraints'] = []
            if 'placementStrategy' not in data:
                data['placementStrategy'] = []
            data['serviceArn'] = 'NONE'
            data['clusterArn'] = 'NONE'
            data['runningCount'] = 'UNKNOWN'
            data['pendingCount'] = 'UNKNOWN'
            data['createdAt'] = 'NONE'
            if 'serviceRegistries' not in data:
                data['serviceRegistries'] = []
            data['createdBy'] = 'NONE'
            data['taskSets'] = []
            data['deployments'] = []
            data['events'] = []
        data['taskDefinition'] = self.task_definition.render_for_display()
        if self.appscaling:
            data['appscaling'] = self.appscaling.render_for_display()
        if self.service_discovery:
            data['service_discovery'] = self.service_discovery.render_for_display()
        return data

    def __update_service_discovery(self, existing):
        if self.service_discovery:
            sd = self.service_discovery.save()
            self.data['serviceRegistries'] = [{
                'registryArn': sd.arn
            }]
        elif existing and existing.service_discovery:
            # ServiceDiscoveryService currently exists for this service, but we no longer want it
            existing.service_discovery.delete()

    def __update_appscaling(self, existing):
        if self.appscaling:
            self.appscaling.save()
        elif existing and existing.appscaling:
            existing.appscaling.delete()

    def __save_helper_tasks(self):
        """
        Save our helper tasks, and save their ARNs as tags on the Service's task definition.
        """
        for task in self.helper_tasks:
            self.task_definition.tags['deployfish:command:{}'.format(task.command)] = task.save()

    def save(self):
        """
        Here's how save works:

            * Save the helper tasks
            * Update the dockerLabels on the first container of our service task definition to name the family:revision
              of the helper tasks
            * Save the service's task definition, and update the service' config with the new ARN
            * Save or remove our service discovery, and update the service's config with the registryArn
            * Save the service itself
            * Add or remove application scaling
        """
        # try to get the data about what is currently in AWS, so we can deal with dependent objects
        # properly (e.g. ServiceDiscoveryService, ServiceHelperTasks, application scaling)
        try:
            existing = Service.objects.get(self.pk)
        except Service.DoesNotExist:
            existing = None

        self.__save_helper_tasks()
        self.data['taskDefinition'] = self.task_definition.save()
        self.__update_service_discovery(existing)
        super(Service, self).save()
        self.__update_appscaling(existing)
