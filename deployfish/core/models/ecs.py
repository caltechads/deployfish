from copy import copy
from typing import List

from ..ssh import DockerMixin, SSHMixin

from .abstract import Manager, Model, LazyAttributeMixin
from .ec2 import Instance, AutoscalingGroup
from .events import EventScheduleRule
from .secrets import SecretsMixin, Secret
from .appscaling import ScalableTarget
from .service_discovery import ServiceDiscoveryService


# ----------------------------------------
# Managers
# ----------------------------------------

class TaskDefinitionManager(Manager):

    service = 'ecs'

    def get(self, pk):
        # type: (str) -> TaskDefinition
        try:
            response = self.client.describe_task_definition(taskDefinition=pk)
        except self.client.exceptions.ClientException:
            raise TaskDefinition.DoesNotExist(
                'No task definition matching "{}" exists in AWS'.format(pk)
            )
        data = response['taskDefinition']
        containers = [ContainerDefinition(d) for d in data.pop('containerDefinitions')]
        return TaskDefinition(data, containers=containers)

    def list(self, family):
        # type: (str) -> List[TaskDefinition]
        paginator = self.client.get_paginator('list_task_definitions')
        response_iterator = paginator.paginate(familyPrefix=family, sort='ASC')
        task_definition_arns = []
        for response in response_iterator:
            task_definition_arns.extend(response['taskDefinitionArns'])
        return [self.get(arn) for arn in task_definition_arns]

    def save(self, obj):
        # type: (TaskDefinition) -> None
        response = self.client.register_task_definition(**obj.render())
        return response['taskDefinition']['taskDefinitionArn']

    def delete(sef, obj):
        # type: (TaskDefinition) -> None
        raise TaskDefinition.ReadOnly('deployfish will not delete existing task definitions.')


class StandaloneTaskManager(Manager):

    service = 'ecs'

    def get(self, pk):
        """
        :param name str: the 'name' key from the task definition in 'tasks:'
        """
        # Need these things out of AWS
        #
        #  * Most recent task definition: what will be run if we do `deploy task run`
        #  * Any scheduled task.  Note this may have a different task definition
        #  * TODO: a populated ParameterStore built out of the secrets in the first container's container definition
        data = {
            'name': pk,
            'cluster': None,
            'count': None,
            'launchType': None,
        }
        # This will give us the most recent versision of a task definition whose family is `name`
        task_definition = None
        if TaskDefinition.objects.exists(pk):
            task_definition = TaskDefinition.objects.get(pk)
        else:
            raise self.DoesNotExist('No TaskDefintion for Task(pk="{}") exists in AWS'.format(pk))
        schedule = None
        if EventScheduleRule.objects.exists(pk):
            schedule = EventScheduleRule.objects.get(pk)
        return StandaloneTask(data, task_definition=task_definition, schedule=schedule)

    def save(self, obj):
        # type: (TaskDefinition) -> None
        arn = obj.task_definition.create()
        if obj.schedule:
            obj.schedule.set_task_definition_arn(arn)
            obj.arn = obj.schedule.save()
        else:
            # delete any schedule we currently have
            if EventScheduleRule.objects.exists(obj.pk):
                EventScheduleRule.objects.delete(obj)

    def delete(self, obj):
        # type: (TaskDefinition) -> None
        # What should happen here?  Delete all task definitions?
        # delete any schedule we currently have
        if EventScheduleRule.objects.exists(obj.pk):
            EventScheduleRule.objects.delete(obj.pk)

    def run(self, obj, wait=False, create=False):
        # type: (TaskDefinition, bool, bool) -> None
        if create:
            self.save(obj)
        # Run the latest ACTIVE task definition in our family.  If `create` was True, this will be the one we just
        # registered
        obj.data['taskDefinition'] = obj.task_definition.pk
        response = self.client.run_task(**obj.render())
        if wait:
            waiter = self.client.get_waiter('tasks_stopped')
            # poll every 6 seconds, maximum of 100 polls
            waiter.wait(
                cluster=obj.data['cluster'],
                tasks=[t['taskArn'] for t in response['tasks']]
            )


class InvokedTaskManager(Manager):

    """
    Invoked tasks are tasks that either are currently running in ECS, or have
    run and are now stopped.
    """

    service = 'ecs'

    def __get_cluster_and_task_arn_from_pk(self, pk):
        return pk.split(':', 1)

    def get(self, pk):
        # type: (str) -> InvokedTask
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
        # type: (str, bool, bool, str, str) -> List[InvokedTask]
        kwargs = {}
        kwargs['cluster'] = cluster
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
            include=['SETTINGS', 'STATISTICS']
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
            include=['SETTINGS', 'STATISTICS']
        )
        return [Cluster(data) for data in response['clusters']]

    def list(self):
        paginator = self.client.get_paginator('list_clusters')
        response_iterator = paginator.paginate()
        cluster_arns = []
        for response in response_iterator:
            cluster_arns.extend(response['clusterArns'])
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
            response = self.client.describe_services(cluster=cluster, services=[service])
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

    def list(self, cluster_name=None, launch_type=None, scheduling_strategy=None):
        # type: (str, str, str)
        if launch_type not in [None, 'EC2', 'FARGATE']:
            raise self.OperationFailed(
                '{} is not a valid launch_type.  Valid types are: EC2, FARGATE.'.format(launch_type)
            )
        if scheduling_strategy not in [None, 'DAEMON', 'REPLICA']:
            raise self.OperationFailed(
                '{} is not a valid scheduling strategy.  Valid strategies are: DAEMON, REPLICA.'.format(launch_type)
            )
        if not cluster_name:
            paginator = self.client.get_paginator('list_clusters')
            response_iterator = paginator.paginate()
            cluster_arns = []
            for response in response_iterator:
                cluster_arns.extend(response['clusterArns'])
            clusters = [arn.rsplit('/', 1)[1] for arn in cluster_arns]
        else:
            clusters = [cluster_name]
        service_arns = []
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
                    service_arns.extend("{}:{}".format(cluster, arn) for arn in response['serviceArns'])
            except self.client.exceptions.ClusterNotFoundException:
                raise Cluster.DoesNotExist('No cluster with name "{}" exists in AWS'.format(cluster))
        return [self.get(identifier) for identifier in service_arns]

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
            except self.client.ServiceNotActiveException:
                raise Service.DoesNotExist(
                    'Service named "{}" in cluster "{}" in AWS cannot be updated: not ACTIVE'.format(service, cluster)
                )
        else:
            raise Service.DoesNotExist('No service named "{}" exists in cluster "{}" in AWS'.format(service, cluster))

    def delete(self, obj):
        # hint: (deployfish.core.models.Service)
        if self.exists(obj.pk):
            # first scale to 0
            self.scale(obj, 0)
            waiter = self.get_waiter('services_stable')
            service, cluster = self.__get_service_and_cluster_from_pk(obj.pk)
            waiter.wait(cluster=cluster, services=[service])
            # Then delete the service
            self.client.delete_service(cluster=cluster, service=service)

    def scale(self, obj, count):
        self.client.update_service(**obj.render_for_scale(count))


# ----------------------------------------
# Models
# ----------------------------------------

class TaskDefinition(SecretsMixin, Model):

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
    def revision(self):
        return self.data.get('revsion', None)

    @property
    def version(self):
        try:
            return self.containers[0].data['image'].rsplit(':', 1)[1]
        except IndexError:
            return 'latest'

    @property
    def secrets_prefix(self):
        if self.secrets:
            return list(self.secrets.values()[0].prefix)
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
        for c in self.containers:
            c.reload_secrets()

    def update_task_labels(self, family_revisions):
        self.containers[0].update_task_labels(family_revisions)

    def get_helper_tasks(self):
        return self.containers[0].get_helper_tasks()

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
        if 'compatibilities' in data:
            data['requiresCompatibilities'] = data['compatibilities']
            del data['compatibilities']
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
        data = copy(self.data)
        data['containerDefinitions'] = [c.render() for c in sorted(self.containers, key=lambda x: x.name)]
        if 'executionRoleArn' not in data:
            # If we don't have an execution role, we can't write secrets into our task definition.  If we
            # do, the container won't be able to start
            for d in data['containerDefinitions']:
                if 'secrets' in d:
                    del d['secrets']
        return data

    def save(self):
        return self.objects.save(self)


class ContainerDefinition(SecretsMixin, LazyAttributeMixin):

    helper_task_prefix = 'edu.caltech.task'

    def __init__(self, data):
        super(ContainerDefinition, self).__init__()
        self.data = data

    @property
    def name(self):
        return self.data.get('name', None)

    @property
    def secrets_prefix(self):
        if self.secrets:
            return list(self.secrets.values()[0].prefix)
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

    def update_task_labels(self, family_revisions):
        """)
        If our service has helper tasks (as defined in the `tasks:` section of the deployfish.yml file), we need to
        record the appropriate `<family>:<revision>` of each of our helper tasks for each version of our service.  We do
        that by storing them as docker labels on the first container of the service task definition.

        This method purges any existing helper task related dockerLabels and replaces them with the contents of
        `labels`, a dict for which the key is the docker label key and the value is the docker label value.

        The `family_revisions` list is a list of the `<family>:<revision>` strings for all the helper tasks for the
        service.

        We're storing the task ``<family>:<revision>`` for the helper tasks for our application in the docker labels on
        the container.   All such labels will start with "`edu.caltech.task.`",

        :param family_revisions: dict of `<family>:<revision>` strings
        :type family_revisions: list of strings
        """
        labels = {
            k: v for k, v in self.data.get('dockerLabels', {})
            if not k.startswith(self.helper_task_prefix)
        }
        for revision in family_revisions:
            family = revision.split(':')[0]
            labels['{}.{}.id'.format(self.helper_task_prefix, family)] = revision
        self.data['dockerLabels'] = labels

    def get_helper_tasks(self):
        """
        Return a information about our helper tasks for this task definition.
        This is in the form of a dictionary like so:

            {`<helper_task_family>`: `<helper_task_family>:<revision>`, ...}

        If our service has helper tasks (as defined in the `tasks:` section of the deployfish.yml file), we've recorded
        the appropriate `<family>:<revision>` of each them as docker labels in the container definition of the first
        container in the task definition.

        Those docker labels will be in this form:

            edu.caltech.tasks.<task name>.id=<family>:<revision>

        :rtype: dict of strings
        """
        labels = {}
        for key, value in self.data['dockerLabels'].items():
            if key.startswith(self.helper_task_prefix):
                labels[value.split(':')[0]] = value
        return labels

    def render_for_diff(self):
        data = copy(self.data)
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
        return copy(self.data)


class StandaloneTask(SecretsMixin, Model):
    """
    A Standalone Task from the deployfish.yml 'tasks:` top level section.

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

    objects = StandaloneTaskManager()
    config_section = 'tasks'

    def __init__(self, data, task_definition=None, secrets=None, schedule=None):
        super(StandaloneTask, self).__init__(data, secrets=secrets)
        self.task_definition = task_definition
        self.schedule = schedule

    @property
    def pk(self):
        return self.data['name']

    def run(self, wait=False, create=False):
        self.objects.run(self, wait=wait, create=create)


class InvokedTask(DockerMixin, Model):

    objects = InvokedTaskManager()

    @property
    def pk(self):
        return '{}:{}'.format(self.cluster_name, self.arn)

    @property
    def arn(self):
        return self.data['taskArn']

    @property
    def ssh_target(self):
        return self.container_instance.ec2_instance

    @property
    def cluster_name(self):
        return self.data['clusterArn'].split('/')[-1]

    @property
    def cluster(self):
        return self.get_cached('cluster', Cluster.objects.get, [self.cluster_name])

    @property
    def container_instance(self):
        return self.get_cached(
            'container_machine',
            ContainerInstance.objects.get,
            ['{}:{}'.format(self.cluster_name, self.data['containerInstanceArn'])]
        )


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


class Cluster(SSHMixin, Model):
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
    def services(self):
        return self.get_cached('services', Service.objects.list, [self.pk])

    @property
    def autoscaling_group(self):
        if 'autoscaling_group' not in self.cache:
            if len(self.container_instances) > 0:
                self.cache['autoscaling_group'] = self.container_instances[0].autoscaling_group
        else:
            # Try to guess our autoscaling group based on our cluster name
            try:
                self.cache['autoscaling_group'] = AutoscalingGroup.objects.get(self.name)
            except AutoscalingGroup.DoesNotExist:
                self.cache['autoscaling_group'] = None
        return self.cache['autoscaling_group']

    def scale(self, count, force=True):
        if self.autoscaling_group:
            self.autoscaling_group.scale(count, force=force)
        else:
            raise self.OperationFailed(
                'Could not find autoscaling group for Cluster(pk="{}"); ignoring scaling request.'.format(self.pk)
            )


class Service(DockerMixin, SecretsMixin, Model):

    objects = ServiceManager()
    config_section = 'services'

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
        return instance

    @property
    def secrets_prefix(self):
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
    def container_names(self):
        return [c.name for c in self.task_definition.containers]

    @property
    def ssh_tunnels(self):
        # Doing this import here to hopefully avoid circular dependencies between this file and ./ssh.py
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

    def scale(self, count):
        self.objects.scale(self, count)

    @property
    def autoscaling_group(self):
        if 'autoscaling_group' in self.cache:
            if hasattr(self, 'autoscalinggroup_name'):
                self.cache['autoscaling_group'] = AutoscalingGroup.objects.get(self.autoscalinggroup_name)
            else:
                self.cache['autoscaling_group'] = self.cluster.autoscaling_group
        return self.cache['autoscaling_group']

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
        return self.get_cached(
            'running_tasks',
            InvokedTask.objects.list,
            [self.data['cluster']],
            {'service': self.data['serviceName']}
        )

    @property
    def container_instances(self):
        if 'container_instances' not in self.cache:
            self.cache['container_instances'] = [
                task.container_instance for task in self.running_tasks
            ]
        return self.cache['container_instances']

    def render_for_update(self):
        data = {}
        data['service'] = self.data['serviceName']
        data['cluster'] = self.data['cluster']
        data['desiredCount'] = self.data['desiredCount']
        data['taskDefinition'] = self.data['taskDefinition']
        if 'capacityProviderStrategy' in self.data:
            data['capacityProviderStrategy'] = self.data['capacityProviderStrategy']
        else:
            data['platformVersion'] = self.data.get('platformVersion', 'LATEST')
        if 'deploymentConfiguration' in self.data:
            data['deploymentConfiguration'] = self.data['deploymentConfiguration']
        if 'networkConfiguration' in self.data:
            data['networkConfiguration'] = self.data['networkConfiguration']
        if 'placementConstraints' in self.data:
            data['placementConstraints'] = self.data['placementConstraints']
        if 'placementStrategy' in self.data:
            data['placementStrategy'] = self.data['placementStrategy']
        return data

    def render_for_scale(self, count):
        data = {}
        data['service'] = self.data['serviceName']
        data['cluster'] = self.data['cluster']
        data['desiredCount'] = count
        return data

    def render_for_create(self):
        data = self.render()
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
        data = self.render()
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

    def save(self):
        self.data['taskDefinition'] = self.task_definition.save()
        if self.appscaling:
            self.appscaling.save()
        if self.service_discovery:
            self.data['serviceRegistries'] = [{
                'registryArn': self.service_discovery.save()
            }]
        super(Service, self).save()
        if self.appscaling:
            self.appscaling.save()
