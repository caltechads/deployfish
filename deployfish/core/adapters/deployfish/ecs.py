from copy import copy
import os
import re
import shlex

from deployfish.core.models import (
    EventScheduleRule,
    ScalableTarget,
    ServiceDiscoveryService,
    TaskDefinition,
)
from deployfish.config import get_config
from deployfish.core.aws import get_boto3_session
from deployfish.core.models.mixins import TaskDefinitionFARGATEMixin

from ..abstract import Adapter
from .mixins import SSHConfigMixin
from .secrets import SecretsMixin


# ------------------------
# Mixins
# ------------------------

class VpcConfigurationMixin:

    def get_vpc_configuration(self, source=None):
        data = {}
        if not source:
            source = self.data.get('vpc_configuration', None)
        if source:
            data['subnets'] = source['subnets']
            if 'security_groups' in source:
                data['securityGroups'] = source['security_groups']
            if 'public_ip' in source:
                data['assignPublicIp'] = source['public_ip']
        return data


# ------------------------
# Abstract Adapters
# ------------------------

class AbstractTaskAdapter(VpcConfigurationMixin, Adapter):

    def is_fargate(self, data):
        if 'requiresCompatibilities' in self.data and self.data['requiresCompatibilities'] == ['FARGATE']:
            return True
        return False

    def get_schedule_data(self, data, task_definition):
        """
        Construct the dict that will be given as input for configuring an EventScheduleRule and EventTarget for our
        helper task.

        The EventScheduleRule.new() factory method expects this struct:

           {
              'name': the name for the schedule
              'schedule': the schedule expression
              'schedule_role': the ARN of the role EventBridge will use to execute our task definition
              'cluster': the name of the cluster in which to run our tasks
              'count': (optional) the number of tasks to run
              'launch_type': (optional): "FARGATE" or "EC2"
              'platform_version': (optional)
              'group': (optional) task group
              'vpc_configuration': { (optional)
                'subnets': list of subnet ids
                'security_groups': list of security group ids
                'public_ip': bool: assign a public ip to our containers?
              }
        }


        :param data dict(str, *): the output of self.get_data()
        :param task_definition TaskDefinition:  the task definition to schedule

        :rtype: dict(str, *): data appropriate for configuring an EventScheduleRule and Event Target
        """
        schedule_data = {}
        schedule_data['name'] = task_definition.data['family']
        schedule_data['schedule'] = data['schedule']
        if 'schedule_role' in data:
            schedule_data['schedule_role'] = data['schedule_role']
        schedule_data['cluster'] = data['cluster']
        if 'count' not in schedule_data:
            schedule_data['count'] = 1
        if 'launchType' in data:
            schedule_data['launch_type'] = data['launchType']
        if schedule_data.get('launch_type', 'EC2') == 'FARGATE':
            if 'platformVersion' in data:
                schedule_data['platform_version'] = data['platformVersion']
        if 'group' in data:
            schedule_data['group'] = data['group']
        if 'networkConfiguration' in data:
            vc = data['networkConfiguration']['awsvpcConfiguration']
            schedule_data['vpc_configuration'] = {}
            if 'subnets' in vc:
                schedule_data['vpc_configuration']['subnets'] = vc['subnets']
            if 'securityGroups' in vc:
                schedule_data['vpc_configuration']['security_groups'] = vc['securityGroups']
            if 'allowPublicIp' in vc:
                schedule_data['vpc_configuration']['public_ip'] = vc['allowPublicIp'] == 'ENABLED'
        return schedule_data

    def update_container_logging(self, data, task_definition):
        """
        FARGATE tasks can only use these logging drivers: awslogs, splunk, awsfirelens.   Examine each
        container in our task definition and if (a) there is no logging stanza or (b) the logging driver
        is not valid, replace the logging stanza with one that writes the logs to awslogs.
        """
        if task_definition.is_fargate():
            for container in task_definition.containers:
                if 'logConfiguration' in container.data:
                    lc = container.data['logConfiguration']
                    if lc['logDriver'] in ['awslogs', 'splunk', 'awsfirelens']:
                        continue
                # the log configuration needs to be fixed
                try:
                    region_name = get_boto3_session().region_name
                except AttributeError:
                    region_name = os.environ.get('AWS_DEFAULT_REGION', 'us-west-2')
                if 'service' in data:
                    log_group = '/{}/{}'.format(*data['service'].split(':'))
                else:
                    log_group = '/{}/standalone-tasks'.format(data['cluster'])
                lc = {
                    'logDriver': 'awslogs',
                    'options': {
                        'awslogs-create-group': "true",
                        'awslogs-region': region_name,
                        'awslogs-group': log_group,
                        'awslogs-stream-prefix': data['name']
                    }

                }
                # FIXME: probably should log a warning to the user or something
                container.data['logConfiguration'] = lc


# ------------------------
# Adapters
# ------------------------


class TaskDefinitionAdapter(TaskDefinitionFARGATEMixin, Adapter):
    """
    Convert our deployfish YAML definition of our task definition to the same format that
    boto3.client('ecs').describe_task_definition() returns, but translate all container info
    into ContainerDefinitions.
    """

    def __init__(self, data, secrets=None, extra_environment=None, partial=False):
        super(TaskDefinitionAdapter, self).__init__(data)
        self.secrets = secrets if secrets else []
        self.extra_environment = extra_environment if extra_environment else {}
        self.partial = partial

    def get_volumes(self):
        """
        In the YAML, volume definitions look like this:

            volumes:
              - name: 'string'
                path: 'string'
                config:
                  scope: 'task' | 'shared'
                  autoprovision: true | false
                  driver: 'string'
                  driverOpts:
                      'string': 'string'
                  labels:
                      'string': 'string'
                efs_config:
                  file_system_id: 'string'
                  root_directory: 'string'

        .. note::

            People can only actually specify one of 'path', 'config' or 'efs_config' -- they're mutually exclusive.
            And 'path' is not available for FARGATE tasks.


        Convert that to to the same structure that boto3.client('ecs').describe_task_definition() returns for that info:

            [
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
                    'efsVolumeConfiguration': {
                        'fileSystemId': 'string',
                        'rootDirectory': 'string'
                    },
            ]

        .. warning:

            Old-style container definitions in deployfish.yml could be specified entirely in the
            container's own `volumes:` section.


        :rtype: dict
        """
        volume_names = set()
        volumes = []
        volumes_data = self.data.get('volumes', [])
        for v in volumes_data:
            if v['name'] in volume_names:
                continue
            v_dict = {'name': v['name']}
            if not self.only_one_is_True([x in v for x in ['path', 'config', 'efs_config']]):
                raise self.SchemaException(
                    'When defining volumes, specify only one of "path", "config" or "efs_config"'
                )
            if 'path' in v:
                v_dict['host'] = {}
                v_dict['host']['sourcePath'] = v['path']
            elif 'config' in v:
                v_dict['dockerVolumeConfiguration'] = copy(v['config'])
            elif 'efs_config' in v:
                try:
                    v_dict['efsVolumeConfiguration'] = {'fileSystemId': v['efs_config']['file_system_id']}
                except KeyError as e:
                    raise self.SchemaException(str(e))
                if 'root_directory' in v['efs_config']:
                    v_dict['efsVolumeConfiguration']['rootDirectory'] = v['efs_config']['root_directory']
            volumes.append(v_dict)
            volume_names.add(v_dict['name'])
        return volumes

    def convert(self):
        """
        :rtype: dict(str, *), list(ContainerDefinition), dict(str, *)
        """
        data = {}
        self.set(data, 'family')
        self.set(data, 'network_mode', dest_key='networkMode', default='bridge')
        launch_type = self.data.get('launch_type', 'EC2')
        if launch_type == 'FARGATE':
            data['requiresCompatibilities'] = ['FARGATE']
        self.set(data, 'task_role_arn', dest_key='taskRoleArn', optional=True)
        self.set(data, 'execution_role', dest_key='executionRoleArn', optional=True)
        if not self.partial and (launch_type == 'FARGATE' and not data['executionRoleArn']):
            raise self.SchemaException(
                'If your launch_type is "FARGATE", you must supply "execution_role"'
            )
        data['volumes'] = self.get_volumes()
        containers_data = []
        if self.partial:
            containers = self.data.get('containers', [])
        else:
            try:
                containers = self.data['containers']
            except KeyError:
                raise self.SchemaViolation('You must define at least one container in your task definition')
        for container_definition in containers:
            containers_data.append(
                ContainerDefinitionAdapter(
                    container_definition,
                    data,
                    secrets=self.secrets,
                    extra_environment=self.extra_environment,
                    partial=self.partial
                ).convert()
            )
        container_data = [c[0] for c in containers_data]
        self.set_task_cpu(data, container_data)
        self.set_task_memory(data, container_data)

        return data, {'containers': containers_data}


class ContainerDefinitionAdapter(Adapter):
    """
    Convert our deployfish YAML definition of our containers to the same format that
    boto3.client('ecs').describe_task_definition() returns for container definitions.
    """

    PORTS_RE = re.compile(r'(?P<hostPort>\d+)(:(?P<containerPort>\d+)(/(?P<protocol>udp|tcp))?)?')
    MOUNT_RE = re.compile('[^A-Za-z0-9_-]')

    def __init__(self, data, task_definition_data=None, secrets=None, extra_environment=None, partial=False):
        """
        :param data dict(str, *): a deployfish.yml container definition stanza
        :param task_definition_data dict(str, *): TaskDefinition.data from the owning TaskDefinition
        :param secrets Union(ParameterStore, None): (optional) a populated ParameterStore full of secrets
                                                    to add to our container
        """
        super(ContainerDefinitionAdapter, self).__init__(data)
        self.task_definition_data = task_definition_data
        self.secrets = secrets if secrets else []
        self.extra_environment = extra_environment if extra_environment else {}
        self.partial = partial

    def get_secrets(self):
        """
        Add parameter store values to the containers 'secrets' list. The task will fail if we try
        to do this and we don't have an execution role, so we don't pass the secrets if it doesn't
        have an execution role
        """
        return [{'name': s.name, 'valueFrom': s.pk} for s in self.secrets]

    def get_mountPoints(self):
        """
        In deployfish.yml, volumes take one of these two forms:

            volumes:
                - storage:/container/path

        or:

            volumes:
                - /host/path:/container/path
                - /host/path-ro:/container/path-ro:ro

        The first form is the new style volume definition.  The "storage" bit refers to a volume on the task definition
        named "storage", which has all the volume configuration info.

        The second form is the old-style volume definition.  Before we allowed the "volumes:" section in the task
        definition yml, you could define volumes on individual containers and the "volumes" list in the
        register_task_definition() AWS API call would be auto-constructed based on the host and container path.

        To deal with the second form, we need to internally convert to the first form and add a hidden volume
        definition on the task definition, then transform the volume mountpoint to the first form.

        :rtype: list(dict(str, str))
        """

        volume_names = set()
        for v in self.task_definition_data['volumes']:
            volume_names.add(v['name'])

        mountPoints = []
        for v in self.data.get('volumes', []):
            fields = v.split(':')
            host_path = fields[0]
            container_path = fields[1]
            readOnly = False
            if len(fields) == 3:
                readOnly = fields[2] == 'ro'
            name = self.MOUNT_RE.sub('_', host_path)
            name = name[:254] if len(name) > 254 else name
            if name not in volume_names:
                # FIXME: if the host_path doesn't start with a /, ensure that the volume already
                # exists in the task definition, otherwise raise ContainerYamlSchemaException
                # Add this container specific volume to the task definition
                self.task_definition_data['volumes'].append({
                    'name': name,
                    'host': {'sourcePath': host_path}
                })
                volume_names.add(name)
            mountPoints.append(
                {
                    'sourceVolume': name,
                    'containerPath': container_path,
                    'readOnly': readOnly
                }
            )
        return mountPoints

    def get_ports(self):
        """
        deployfish.yml port mappings look like this:

            ports:
                - "80"
                - "8443:443"
                - "8125:8125/udp"

        Convert them to this:

            [
                {"containerPort": 80, "protocol": "tcp"},
                {"containerPort": 443, "hostPort": 8443, "protocol": "tcp"},
                {"containerPort": 8125, "hostPort": 8125, "protocol": "udp"},
            ]
        """
        portMappings = []
        for mapping in self.data.get('ports', []):
            if isinstance(mapping, int):
                mapping = str(mapping)
            m = self.PORTS_RE.search(mapping)
            if m:
                mapping = {}
                if not m.group('containerPort'):
                    mapping['containerPort'] = int(m.group('hostPort'))
                else:
                    mapping['hostPort'] = int(m.group('hostPort'))
                    mapping['containerPort'] = int(m.group('containerPort'))
                protocol = m.group('protocol')
                if not protocol:
                    protocol = 'tcp'
                mapping['protocol'] = protocol
                portMappings.append(mapping)

            else:
                raise self.ContainerYamlSchemaException(
                    '{} is not a valid port mapping'.format(mapping)
                )
        return portMappings

    def get_environment(self):
        """
        deployfish.yml environment variables are defined in one of the two following ways:

            environment:
                - FOO=bar
                - BAZ=bash

        or:

            environment:
                FOO: bar
                BAZ: bash

        Convert them to this, which is what boto3.client('ecs').describe_task_definition() returns.

            [
                {"name": "FOO", "value": "bar"},
                {"name": "BAZ", "value": "bash}
            ]

        :rtype: list(dict(str, str))
        """
        if 'environment' in self.data:
            if isinstance(self.data['environment'], list):
                source_environment = {}
                for env in self.data['environment']:
                    parts = env.split('=')
                    k, v = parts[0], '='.join(parts[1:])
                    source_environment[k] = v
            else:
                source_environment = self.data['environment']
            source_environment.update(self.extra_environment)
            return [{'name': k, 'value': v} for k, v in source_environment.items()]

    def get_dockerLabels(self):
        """
        deployfish.yml environment variables are defined in one of the two following ways:

            labels:
                - FOO=bar
                - BAZ=bash

        or:

            labels:
                FOO: bar
                BAZ: bash

        Convert them to this, which is what boto3.client('ecs').describe_task_definition() returns.

            {
                'FOO': 'bar',
                'BAZ': 'bash'
            {

        :rtype: dict(str, str)
        """
        dockerLabels = {}
        if 'labels' in self.data:
            if type(self.data['labels']) == dict:
                dockerLabels = self.data['labels']
            else:
                for label in self.data['labels']:
                    key, value = label.split('=')
                    dockerLabels[key] = value
        return dockerLabels

    def get_ulimits(self):
        ulimits = []
        for key, value in self.data['ulimits'].items():
            # FIXME: should validate key here maybe
            if type(value) != dict:
                soft = value
                hard = value
            else:
                soft = value['soft']
                hard = value['hard']
            ulimits.append({
                'name': key,
                'softLimit': int(soft),
                'hardLimit': int(hard)
            })
        return ulimits

    def get_logConfiguration(self):
        logConfiguration = {}
        if 'logging' in self.data:
            if 'driver' not in self.data['logging']:
                raise self.ContainerYamlSchemaException('logging: block must contain "driver"')
            logConfiguration['logDriver'] = self.data['logging']['driver']
            if 'options' in self.data['logging']:
                logConfiguration['options'] = self.data['logging']['options']
        return logConfiguration

    def get_linuxCapabilities(self):
        cap_add = self.data.get('cap_add', None)
        cap_drop = self.data.get('cap_drop', None)
        tmpfs = self.data.get('tmpfs', None)
        linuxCapabilities = {}
        if cap_add or cap_drop:
            linuxCapabilities['capabilities'] = {}
            if cap_add:
                linuxCapabilities['capabilities']['add'] = cap_add
            if cap_drop:
                linuxCapabilities['capabilities']['drop'] = cap_drop
        if tmpfs:
            linuxCapabilities['tmpfs'] = []
            for tc in tmpfs:
                tc_append = {
                    'containerPath': tc['container_path'],
                    'size': tc['size']
                }
                if 'mount_options' in tc and type(tc['mount_options']) == list:
                    tc_append['mountOptions'] = tc['mount_options']
                linuxCapabilities['tmpfs'].append(tc_append)
        return linuxCapabilities

    def get_extraHosts(self):
        extraHosts = []
        for host in self.data.get('extra_hosts', []):
            hostname, ip_address = host.split(':')
            extraHosts.append({'hostname': hostname, 'ipAddress': ip_address})
        return extraHosts

    def convert(self):
        data = {}
        self.set(data, 'name')
        self.set(data, 'image')
        self.set(data, 'essential', default=True)
        try:
            self.set(data, 'cpu', default=256, convert=int)
        except ValueError:
            raise self.SchemaExeption('"cpu" must be an integer')
        try:
            self.set(data, 'memoryReservation', optional=True, convert=int)
        except ValueError:
            raise self.SchemaExeption('"memoryReservation" must be an integer')
        try:
            self.set(data, 'memory', optional=True, convert=int)
        except ValueError:
            raise self.SchemaExeption('"memory" must be an integer')
        if data.get('memoryReservation', None) is None and data.get('memory', None) is None:
            if not self.partial:
                data['memory'] = 512
        if 'ports' in self.data:
            data['portMappings'] = self.get_ports()
        self.set(data, 'command', optional=True, convert=shlex.split)
        self.set(data, 'entrypoint', optional=True, convert=shlex.split)
        if 'ulimits' in self.data:
            data['ulimits'] = self.get_ulimits()
        if 'environment' in self.data:
            data['environment'] = self.get_environment()
        if 'volumes' in self.data:
            data['mountPoints'] = self.get_mountPoints()
        self.set(data, 'links', optional=True)
        self.set(data, 'dockerLabels', optional=True)
        if 'logging' in self.data:
            data['logConfiguration'] = self.get_logConfiguration()
        if 'extra_hosts' in self.data:
            data['extraHosts'] = self.get_extraHosts()
        if 'cap_add' in self.data or 'cap_drop' in self.data:
            data['linuxCapabilities'] = self.get_linuxCapabilities()
        if self.secrets:
            data['secrets'] = self.get_secrets()
        kwargs = {}
        kwargs['secrets'] = self.secrets
        return data, kwargs


class StandaloneTaskAdapter(SecretsMixin, AbstractTaskAdapter):

    def get_task_definition(self, secrets=None):
        deployfish_environment = {
            "DEPLOYFISH_TASK_NAME": self.data['name'],
            "DEPLOYFISH_ENVIRONMENT": self.data.get('environment', 'undefined'),
            "DEPLOYFISH_CLUSTER_NAME": self.data['cluster']
        }
        return TaskDefinition.new(
            self.data,
            'deployfish',
            secrets=secrets,
            extra_environment=deployfish_environment
        )

    def convert(self):
        data = {}
        data['name'] = self.data['name']
        if 'family' not in self.data:
            self.data['family'] = data['name']
        if 'service' in self.data:
            # We actually want the Service.pk here, not just the bare service name, but in deployfish.yml
            # we've allowed people to just name the bare service of things that are in the same deployfish.yml
            data['service'] = self.data['service']
            if ':' not in data['service']:
                config = get_config()
                # This is not a Service.pk
                try:
                    service_data = config.get_section_item('services', data['service'])
                except KeyError:
                    raise self.SchemaException('No service named "{}" exists in deployfish.yml'.format(data['service']))
                data['service'] = '{}:{}'.format(service_data['cluster'], service_data['name'])
        data['cluster'] = self.data.get('cluster', 'default')
        vpc_configuration = self.get_vpc_configuration()
        if vpc_configuration:
            data['networkConfiguration'] = {}
            data['networkConfiguration']['awsvpcConfiguration'] = vpc_configuration
        data['count'] = self.data.get('count', 1)
        data['launchType'] = self.data.get('launch_type', 'EC2')
        if data['launchType'] == 'FARGATE':
            data['platformVersion'] = self.data.get('platform_version', 'LATEST')
        elif 'capacity_provider_strategy' in self.data:
            data['capacityProviderStrategy'] = self.data['capacity_provider_strategy']
        if 'placement_constraints' in self.data:
            data['placementConstraints'] = self.data['placement_constraints']
        if 'placement_strategy' in self.data:
            data['placementStrategy'] = self.data['placement_strategy']
        if 'group' in self.data:
            data['Group'] = self.data['group']
        if 'count' in self.data:
            data['count'] = self.data['count']
        kwargs = {}
        secrets = []
        if 'config' in self.data:
            secrets = self.get_secrets(data['cluster'], 'task-{}'.format(data['name']))
        kwargs['task_definition'] = self.get_task_definition(secrets=secrets)
        self.update_container_logging(data, kwargs['task_definition'])
        if 'networkConfiguration' in data and kwargs['task_definition'].data['networkMode'] != 'awsvpc':
            kwargs['task_definition'].data['networkMode'] = 'awsvpc'
        if 'schedule' in self.data:
            data['schedule'] = self.data['schedule']
            if 'schedule_role' in self.data:
                data['schedule_role'] = self.data['schedule_role']
            if 'schedule_role' not in data:
                raise self.SchemaException(
                    f'''StandaloneTask("{data['name']}"): "schedule_role" is required when you specify a schedule'''
                )
            kwargs['schedule'] = EventScheduleRule.new(
                self.get_schedule_data(data, kwargs['task_definition']),
                'deployfish'
            )
        return data, kwargs


class ServiceHelperTaskAdapter(AbstractTaskAdapter):
    """
    The problem here is that, unlike all our other adapters, we need to create many objects out of this.

    Helper tasks are defined in the `tasks` sub-section of the service.

    * `tasks` is a list
    * Each item in that list is comprised of
      * A set of "command" overrides
      * General settings that apply to each of those command overrides

    .. note::

        There's no way to remove a setting from the parent task definition:  you can add or change existing settings.
        If people need to do that, they can use a standalone task.

    deployfish.yml structure::

            services:
              - name: foobar
                family: foobar
                network_mode: host
                task_role_arn: arn:aws:iam:23140983205498:role/task-role
                containers:
                  - name: foo
                    image: foo:1.2.3
                    cpu: 128
                    memory: 256
                    environment:
                        - ENVVAR1=bar
                        - ENVVAR2=baz
                [...]

                tasks:
                    # General overrides/settings that apply to all sub-tasks of this entry
                    # There can be multiple entries if you need separate sets of global settings
                    - family: foobar-helper1
                      network_mode: bridge
                      task_role_arn: arn:aws:iam:23140983205498:role/task-role2
                      launch_type: FARGATE
                      schedule_role: arn:aws:...
                      vpc_configuration:
                        subnets:
                          - subnet-1
                          - subnet-2
                        security_groups:
                          - sg-1
                          - sg-2
                        public_ip: true
                      containers:
                        - name: foo
                          cpu: 256
                          memory: 512
                          logging:
                              driver: awslogs
                      commands:
                        - name: migrate
                          containers:
                            - name: foo
                              command: manage.py migrate
                        - name: update_index
                          schedule: cron(5 * * * ? *)
                          containers:
                            - name: foo
                              command: manage.py update_index
                          command: manage.py update_index


    """

    def __init__(self, data, service):
        """
        :param data dict(str, *): the tasks section from our service
        :param service Service: the Service for which we are building helper tasks
        """
        self.data = data
        self.service = service

    def set(self, data, task, yml_key, data_key, source=None):
        """
        Set a `data[data_key]` on the dict `data` by looking at both `task` and `source`.

        If `task[yml_key]` exists, set `data[data_key]` to that value.
        Else if `source[yml_key]` exists, set `data[data_key]` to THAT value.
        Else if `source[data_key]` exists, set `data[data_key]` to THAT value.
        Else, do nothing.

        If `source` is None, we set source to `self.data`.
        """
        if not source:
            source = self.service.data
        if yml_key in task:
            data[data_key] = task[yml_key]
        elif yml_key in source:
            data[data_key] = source[yml_key]
        elif data_key in source:
            data[data_key] = source[data_key]

    def get_data(self, data, task, source=None):
        """
        Construct `data` so that it can be used for constructing our Task parameters by combining data from an existing
        TaskDefinition with configuration from deployfish.yml.

        :param data dict(str, *): our output dict
        :param task dict(str, *): configuration from deployfish.yml
        :param source Union[dict(str, *), None]: (optional) if provided, the data from  the previous set of Task
                                                 parameters.  If not provided, self.service.data.
        """
        if not source:
            source = self.service.data
        self.set(data, task, 'cluster', 'cluster', source=source)
        if 'vpc_configuration' in task:
            data['networkConfiguration'] = {}
            data['networkConfiguration']['awsvpcConfiguration'] = self.get_vpc_configuration(
                source=task['vpc_configuration']
            )
        elif 'networkConfiguration' in source:
            data['networkConfiguration'] = {}
            data['networkConfiguration']['awsvpcConfiguration'] = source['networkConfiguration']['awsvpcConfiguration']
        self.set(data, task, 'launch_type', 'launchType', source=source)
        if 'launchType' in data and data['launchType'] == 'FARGATE':
            self.set(data, task, 'platform_version', 'platformVersion', source=source)
            if 'platformVersion' not in data:
                data['platformVersion'] = 'LATEST'
        else:
            # capacity_provider_strategy and launch_type are mutually exclusive
            self.set(data, task, 'capacity_provider_strategy', 'capacityProviderStrategy', source=source)
        self.set(data, task, 'placement_constraints', 'placementConstraints', source=source)
        self.set(data, task, 'placement_strategy', 'placementStrategy', source=source)
        self.set(data, task, 'group', 'group', source=source)
        if 'count' in task:
            data['count'] = task['count']
        self.set(data, task, 'schedule', 'schedule', source=source)
        self.set(data, task, 'schedule_role', 'schedule_role', source=source)

    def update_container_environments(self, task_definition, extra_environment):
        """
        Update the deployfish-specific environment variables in the container environment for each
        container in `task_definition`.

        * Remove DEPLOYFISH_SERVICE_NAME
        * Add DEPLOYFISH_TASK_NAME
        * Update DEPLOYFISH_ENVIRONMENT and DEPLOYFISH_CLUSTER_NAME as necessary
        """
        for container in task_definition.containers:
            environment = []
            for i, var in enumerate(container.data['environment']):
                if var['name'] == 'DEPLOYFISH_SERVICE_NAME':
                    environment.append({
                        'name': 'DEPLOYFISH_TASK_NAME',
                        'value': extra_environment['DEPLOYFISH_TASK_NAME']
                    })
                else:
                    if var['name'] in extra_environment:
                        var['value'] = extra_environment[var['name']]
                    environment.append(var)
            container.data['environment'] = environment

    def _get_base_task_data(self, task_data, service_td):
        """
        Build a dict that takes info from the service and overlays the generic (not command specific) task data to build
        the parameters we'll need when running the task.  Also build a new TaskDefinition object that is the service's
        TaskDefinition overlaid with the changes from the generic task data.

        :param task_data dict(str, *): the generic helper task data
        :param service_td TaskDefinition: the Service's TaskDefinition object

        :rtype: tuple(dict(str, *), TaskDefinition)
        """
        data_base = {}
        # first, extract whatever we can from self.service
        self.get_data(data_base, task_data)
        data_base['service'] = self.service.pk
        base_td_overlay = TaskDefinition.new(task_data, 'deployfish', partial=True)
        base_td = service_td + base_td_overlay
        base_td.data['family'] = task_data.get('family', "{}-tasks".format(service_td.data['family']))
        # Remove any portMappings fro our task definition -- we don't need them for ephemeral tasks
        for container in base_td.containers:
            if 'portMappings' in container.data:
                del container.data['portMappings']
        # Automatically set our networkMode
        if 'networkConfiguration' in data_base:
            # We need awsvpc network mode, because we have VPC configuration
            base_td.data['networkMode'] = 'awsvpc'
        else:
            base_td.data['networkMode'] = 'bridge'
        return data_base, base_td

    def _preprocess_task_data(self, task_data, service_td):
        """
        Change old style command defintions that look like this:

            tasks:
              - family: foobar-test-helper
                environment: test
                network_mode: bridge
                task_role_arn: ${terraform.iam_task_role}
                containers:
                  - name: foobar
                    image: ${terraform.ecr_repo_url}:0.1.0
                    cpu: 128
                    memory: 384
                    commands:
                      migrate: ./manage.py migrate
                      update_index: ./manage.py update_index

        to look like this:

            tasks:
              - family: foobar-test-helper
                environment: test
                network_mode: bridge
                task_role_arn: ${terraform.iam_task_role}
                containers:
                  - name: foobar
                    image: ${terraform.ecr_repo_url}:0.1.0
                    cpu: 128
                  memory: 384
                commands:
                  - name: migrate
                    containers:
                      - name: foobar
                        command: ./manage.py migrate
                  - name: update_index
                    containers:
                      - name: foobar
                        command: ./manage.py update_index

        """
        if 'containers' in task_data:
            for container_data in task_data['containers']:
                if 'commands' in container_data:
                    if 'commands' not in task_data:
                        task_data['commands'] = []
                    for command_name, command in container_data['commands'].items():
                        task_data['commands'].append({
                            'name': command_name,
                            'containers': [{
                                'name': container_data['name'],
                                'command': command
                            }]
                        })
                    del container_data['commands']

    def _get_command_specific_data(self, command, data_base, base_td):
        """
        Build a dict that takes info from the output of self._get_base_task_data() and overlays the command specific
        task data to build the parameters we'll need when running the task.  Also build a new TaskDefinition object that
        is the TaskDefinition returned by self._get_base_task_data() overlaid with the changes from the command specific
        task data.

        :param commmand dict(str, *): the command specific task data
        :param data_base dict(str, *): the dict returned by self._get_base_task_data()
        :param service_td TaskDefinition: the TaskDefinition object returned by self._get_base_task_data()

        :rtype: tuple(dict(str, *), TaskDefinition)
        """
        data = {}
        kwargs = {}
        # Build our new Task data based on the general task overlay we got from self._get_base_task_data()
        self.get_data(data, command, source=data_base)
        data['service'] = self.service.pk
        if 'cluster' not in data:
            data['cluster'] = self.service.data['cluster']
        try:
            data['name'] = command['name']
        except KeyError:
            raise self.SchemaException(
                'Service(pk="{}"): Each helper task must have a "name" assigned in the "commands" section'.format(
                    self.service.pk
                )
            )
        if 'family' not in command:
            # Make the task definition family be named after our command
            command['family'] = "{}-{}".format(base_td.data['family'], command['name'].replace('_', '-'))
        # Generate our overlay task definition
        command_td_overlay = TaskDefinition.new(command, 'deployfish', partial=True)
        # Use that to make our actual task definition
        command_td = base_td + command_td_overlay
        # Update the deployfish specific environment variables in our task definition's containers
        self.update_container_environments(
            command_td,
            {
                'DEPLOYFISH_TASK_NAME': command['family'],
                'DEPLOYFISH_CLUSTER_NAME': data['cluster'],
                'DEPLOYFISH_ENVIRONMENT': self.service.deployfish_environment
            }
        )
        kwargs['task_definition'] = command_td
        # See if we need to schedule this command
        if 'schedule' in command:
            if 'schedule_role' not in data:
                raise self.SchemaException(
                    f'''ServiceHelperTask("{command['name']}") in Service("{self.service.pk}"): '''
                    '"schedule_role" is required when you specify a schedule'
                )
            kwargs['schedule'] = EventScheduleRule.new(self.get_schedule_data(data, command_td), 'deployfish')
        return data, kwargs

    def convert(self):
        data_list = []
        kwargs_list = []
        service_td = self.service.task_definition.copy()
        if 'tasks' in self.data:
            for task in self.data['tasks']:
                # Preprocess the data to turn the old-style command definitions into the new style definitions
                self._preprocess_task_data(task, service_td)
                data_base, base_td = self._get_base_task_data(task, service_td)
                # Now iterate through each item in task -> commands
                for command in task['commands']:
                    command_data, command_kwargs = self._get_command_specific_data(command, data_base, base_td)
                    self.update_container_logging(command_data, command_kwargs['task_definition'])
                    data_list.append(command_data)
                    kwargs_list.append(command_kwargs)
        return data_list, kwargs_list


class ServiceAdapter(SSHConfigMixin, SecretsMixin, VpcConfigurationMixin, Adapter):
    """
    * Service itself             [x]
    * Task definition            [x]
    * Autoscaling Group          [x]
    * Application Autoscaling    [x]
    * Service Discovery          [x]

    Helper Tasks
    ------------

    Helper tasks are overlays for the service's task definition.  Each task listed under the `tasks` section of
    the service consists of general overrides, and then a set of specific command overrides, possibly with schedules.

        services:
            - name: foobar-prod
              ...

              tasks:
                  # general overrides
                - network_mode: bridge
                  task_role_arn: new task role
                  containers:



    """

    def __init__(self, data, **kwargs):
        self.load_secrets = kwargs.pop('load_secrets', True)
        super(ServiceAdapter, self).__init__(data, **kwargs)

    def get_clientToken(self):
        return 'token-{}-{}'.format(self.data['name'], self.data['cluster'])[:35]

    def get_task_definition(self):
        secrets = self.__build_Secrets()
        deployfish_environment = {
            "DEPLOYFISH_SERVICE_NAME": self.data['name'],
            "DEPLOYFISH_ENVIRONMENT": self.data.get('environment', 'undefined'),
            "DEPLOYFISH_CLUSTER_NAME": self.data['cluster']
        }
        return TaskDefinition.new(
            self.data,
            'deployfish',
            secrets=secrets,
            extra_environment=deployfish_environment
        )

    def get_loadBalancers(self):
        loadBalancers = []
        if 'target_groups' in self.data['load_balancer']:
            # If we want the service to register itself with multiple target groups,
            # the "load_balancer" section will have a list entry named "target_groups".
            # Each item in the target_group_list will be a dict with keys "target_group_arn",
            # "container_name" and "container_port"
            for group in self.data['load_balancer']['target_groups']:
                lb_data = {
                    'targetGroupArn': group['target_group_arn'],
                    'containerName': group['container_name'],
                    'containerPort': int(group['container_port'])
                }
                loadBalancers.append(lb_data)
        else:
            # We either have just one target group, or we're using an ELB
            group = self.data['load_balancer']
            if 'load_balancer_name' in group:
                # ELB
                loadBalancers.append({
                    'loadBalancerName': group['load_balancer_name'],
                    'containerName': group['container_name'],
                    'containerPort': int(group['container_port'])
                })
            elif 'target_group_arn' in self.data['load_balancer']:
                loadBalancers.append({
                    'targetGroupArn': group['target_group_arn'],
                    'containerName': group['container_name'],
                    'containerPort': int(group['container_port'])
                })
        return loadBalancers

    def __build_Service__data(self, data):
        """
        Update ``data`` with the configuration for the Service itself.  This will look like the
        dict that ``boto3.client('ecs').create_service()`` needs.

        :rtype: dict(str, *)
        """
        data['cluster'] = self.data['cluster']
        data['serviceName'] = self.data['name']
        if 'load_balancer' in self.data:
            if 'service_role_arn' in self.data:
                # backwards compatibility for deployfish.yml < 0.3.6
                data['role'] = self.data['service_role_arn']
            elif 'load_balancer' in self.data and 'service_role_arn' in self.data['load_balancer']:
                data['role'] = self.data['load_balancer']['service_role_arn']
            data['loadBalancers'] = self.get_loadBalancers()
        if 'capacity_provider_strategy' in self.data:
            data['capacityProviderStrategy'] = self.data['capacity_provider_strategy']
        else:
            # capacity_provider_strategy and launch_type are mutually exclusive
            data['launchType'] = self.data.get('launch_type', 'EC2')
            if data['launchType'] == 'FARGATE':
                data['platformVersion'] = 'LATEST'
        vpc_configuration = self.get_vpc_configuration()
        if vpc_configuration:
            data['networkConfiguration'] = {}
            data['networkConfiguration']['awsvpcConfiguration'] = vpc_configuration
        if 'placement_constraints' in self.data:
            data['placementConstraints'] = self.data['placement_constraints']
        if 'placement_strategy' in self.data:
            data['placementStrategy'] = self.data['placement_strategy']
        data['deploymentConfiguration'] = {}
        data['deploymentConfiguration']['maximumPercent'] = int(self.data.get('maximum_percent', 200))
        data['deploymentConfiguration']['minimumHealthyPercent'] = int(
            self.data.get('minimum_healthy_percent', 50)
        )
        data['schedulingStrategy'] = self.data.get('scheduling_strategy', 'REPLICA')
        if data['schedulingStrategy'] == 'DAEMON':
            data['desiredCount'] = 'automatically'
            if 'deploymentConfiguration' not in data:
                data['deploymentConfiguration'] = {}
            data['deploymentConfiguration']['maximumPercent'] = 100
        else:
            data['desiredCount'] = self.data['count']
        data['clientToken'] = self.get_clientToken()

    def __build_Secrets(self):
        """
        Build a list of Secret and ExternalSecret objects from our Service's config: section.

        :rtype: list(Union[Secret, ExternalSecret])
        """
        if self.load_secrets:
            secrets = self.get_secrets(self.data['cluster'], self.data['name'])
        else:
            secrets = []
        return secrets

    def __build_TaskDefinition(self, kwargs):
        kwargs['task_definition'] = self.get_task_definition()

    def __build_application_scaling_objects(self, kwargs):
        if 'application_scaling' in self.data:
            kwargs['appscaling'] = ScalableTarget.new(
                self.data['application_scaling'],
                'deployfish',
                cluster=self.data['cluster'],
                service=self.data['name']
            )

    def __build_ServiceDiscoveryService(self, kwargs):
        if 'service_discovery' in self.data:
            if self.data.get('network_mode', 'bridge') == 'awsvpc':
                kwargs['service_discovery'] = ServiceDiscoveryService.new(
                    self.data['service_discovery'],
                    'deployfish',
                )
            else:
                raise self.SchemaException(
                    'You must use network_mode of "awsvpc" to enable service discovery'.format(self.data['name'])
                )

    def __build_tags(self, kwargs):
        tags = {}
        tags['Environment'] = self.data.get('environment', 'test')
        kwargs['tags'] = tags

    def convert(self):
        """
        .. note::

            ServiceHelperTasks are constructed in Service.new(), because
        """
        data, kwargs = super(ServiceAdapter, self).convert()
        self.__build_Service__data(data)
        self.__build_TaskDefinition(kwargs)
        self.__build_application_scaling_objects(kwargs)
        self.__build_ServiceDiscoveryService(kwargs)
        self.__build_tags(kwargs)
        if 'autoscalinggroup_name' in self.data:
            kwargs['autoscalinggroup_name'] = self.data['autoscalinggroup_name']
        return data, kwargs
