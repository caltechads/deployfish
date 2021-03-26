import botocore
import json
import os
import os.path
import re
import shlex

from copy import copy
from jsondiff import diff

from deployfish.aws import get_boto3_session
from deployfish.aws.cloudwatch import CloudwatchLogsTailer
from deployfish.aws.systems_manager import ParameterStore
from deployfish.exc import DeployfishYamlSchemaException


class TaskDefinitionAWSLogsCloudwatchLogsTailer(CloudwatchLogsTailer):

    class InvalidLogDriver(Exception):
        pass

    def __init__(self, task_definition, invocation_arn, sleep=5):
        log_config = task_definition.containers[0].data['logConfiguration']
        if not log_config['driver'] == 'awslogs':
            raise self.InvalidLogDriver(
                'The logging driver on the TaskDefinition is "{}"; can only tail on type "awslogs"'.format(
                    log_config['driver']
                )
            )
        stream_prefix = log_config['options']['awslogs-stream-prefix']
        log_group = log_config['options']['awslogs-group']
        container_name = task_definition.containers[0].name
        task_id = invocation_arn.split(':')[-1][5:]
        stream = "{}/{}/{}".format(stream_prefix, container_name, task_id)
        super(TaskDefinitionAWSLogsCloudwatchLogsTailer, self).__init__(log_group, stream, sleep=sleep)




# ----------------------------------------
# Adapters
# ----------------------------------------

class DeployfishYamlTaskDefinitionAdapter(object):
    """
    Convert our deployfish YAML definition of our task definition to the same format that
    boto3.client('ecs').describe_task_definition() returns, but translate all container info
    into ContainerDefinitions.
    """

    class TaskDefinitionYamlSchemaException(DeployfishYamlSchemaException):
        pass

    def __init__(self, yaml, secrets=None, extra_environment=None):
        self.yaml = yaml
        self.secrets = secrets if secrets else []
        self.extra_environment = extra_environment if extra_environment else {}

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
            ]

        .. warning:

            Old-style container definitions in deployfish.yml could be specified entirely in the
            container's own `volumes:` section.


        :rtype: dict
        """
        volume_names = set()
        volumes = []
        volumes = self.yaml.get('volumes', [])
        for v in self.volumes:
            if v['name'] in volume_names:
                continue
            v_dict = {'name': v['name']}
            if 'path' in v:
                v_dict['host'] = {}
                v_dict['host']['sourcePath'] = v['path']
            elif 'config' in v:
                v_dict['dockerVolumeConfiguration'] = copy(v['config'])
            volumes.append(v_dict)
            volume_names.add(v_dict['name'])
        return volumes

    def convert(self):
        """
        :rtype: dict(str, *), list(ContainerDefinition), dict(str, *)
        """
        data = {}
        data['family'] = self.yaml['family']
        data['networkMode'] = self.yaml.get('network_mode', 'bridge')
        cpu = self.yaml.get('cpu', None)
        data['cpu'] = int(cpu) if cpu else None
        memory = self.yaml.get('memory', None)
        data['cpu'] = int(memory) if memory else None
        launch_type = self.yaml.get('launch_type', 'EC2')
        data['requiresCompatibilities'] = ['FARGATE']
        data['taskRoleArn'] = self.yaml.get('task_role_arn', None)
        data['executionRoleArn'] = self.yaml.get('execution_role', None)
        if launch_type == 'FARGATE' and not data['executionRoleArn']:
            raise self.TaskDefinitionYamlSchemaException(
                'If your launch_type is "FARGATE", you must supply "execution_role"'
            )
        containers = []
        for container_definition in self.yaml['containers']:
            containers.append(
                ContainerDefinition(
                    DeployfishYamlContainerDefinitionAdapter(
                        container_definition,
                        data,
                        secrets=self.secrets,
                        extra_environment=self.extra_environment
                    )
                )
            )

        return data, containers, {}


class AWSTaskDefinitionAdapter(object):

    class DoesNotExist(Exception):
        pass

    def __init__(self, name):
        """
        :param name str: either a family, a family:revision or an ARN, all prefixed with "aws:"
        """
        assert name.startswith('aws:'), 'AWSTaskDefinitionAdapter(name): name should look like "aws:{task_name}"'
        _, self.name = name.split(':')
        self.name = name
        self.client = get_boto3_session().client('ecs')

    def convert(self):
        """
        :rtype: dict(str, *), list(ContainerDefinition), dict(str, *)
        """
        try:
            response = self.client.describe_task_definition(task_definition=self.name)
        except self.client.exceptions.ClientException:
            raise self.DoesNotExist('No task definition matching "{}" was found in AWS'.format(self.name))
        data = response['taskDefinition']
        containers = [ContainerDefinition(d) for d in data.pop('containerDefinitions')]
        kwargs = {}
        kwargs['arn'] = data.pop('taskDefinitionArn')
        kwargs['revision'] = data.pop('revision')
        return data, containers, kwargs


class DeployfishYamlContainerDefinitionAdapter(object):
    """
    Convert our deployfish YAML definition of our containers to the same format that
    boto3.client('ecs').describe_task_definition() returns for container definitions.
    """

    PORTS_RE = re.compile(r'(?P<hostPort>\d+)(:(?P<containerPort>\d+)(/(?P<protocol>udp|tcp))?)?')
    MOUNT_RE = re.compile('[^A-Za-z0-9_-]')

    class ContainerYamlSchemaException(DeployfishYamlSchemaException):
        pass

    def __init__(self, yaml, task_definition_data, secrets=None, extra_environment=None):
        """
        :param yaml dict(str, *): a deployfish.yml container definition stanza
        :param task_definition_data dict(str, *): TaskDefinition.data from the owning TaskDefinition
        :param secrets Union(ParameterStore, None): (optional) a populated ParameterStore full of secrets
                                                    to add to our container
        """
        self.yaml = yaml
        self.task_definition_data = task_definition_data
        self.secrets = secrets if secrets else []
        self.extra_environment = extra_environment if extra_environment else {}

    def get_secrets(self):
        """
        Add parameter store values to the containers 'secrets' list. The task will fail if we try
        to do this and we don't have an execution role, so we don't pass the secrets if it doesn't
        have an execution role
        """
        self.data['secrets'] = [{'name': s.key, 'valueFrom': s.name} for s in self.secrets]

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
        for v in self.yaml.get('volumes', []):
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
        for mapping in self.yaml.get('ports', []):
            m = self.PORTS_RE.search(mapping)
            if m:
                if not m.group('containerPort'):
                    containerPort = int(m.group('hostPort'))
                else:
                    hostPort = int(m.group('hostPort'))
                    containerPort = int(m.group('containerPort'))
                protocol = m.group('protocol')
                if not protocol:
                    protocol = 'tcp'
                portMappings.append(
                    {'containerPort': containerPort, 'hostPort': hostPort, 'protocol': protocol}
                )

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
        if isinstance(self.yaml['environment'], list):
            source_environment = {}
            for env in self.yaml['environment']:
                parts = env.split('=')
                k, v = parts[0], '='.join(parts[1:])
                source_environment[k] = v
        else:
            source_environment = self.yaml['environment']
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
        if type(self.yaml['labels']) == dict:
            dockerLabels = self.yaml['labels']
        else:
            for label in self.yaml['labels']:
                key, value = label.split('=')
                dockerLabels[key] = value
        return dockerLabels

    def get_ulimits(self):
        ulimits = []
        for key, value in self.yaml['ulimits'].items():
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
        if 'logging' in self.yaml:
            if 'driver' not in self.yaml['logging']:
                raise self.ContainerYamlSchemaException('logging: block must contain "driver"')
            logConfiguration['logDriver'] = self.yaml['logging']['driver']
            if 'options' in self.yaml['logging']:
                logConfiguration['options'] = self.yaml['logging']['options']
        return logConfiguration

    def get_linuxCapabilities(self):
        cap_add = self.yaml.get('cap_add', None)
        cap_drop = self.yaml.get('cap_drop', None)
        tmpfs = self.yaml.get('tmpfs', None)
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
        for host in self.yaml.get('extra_hosts', []):
            hostname, ip_address = host.split(':')
            extraHosts.append({'hostname': hostname, 'ipAddress': ip_address})
        return extraHosts

    def convert(self):
        data = {}
        data['name'] = self.yaml['name']
        data['image'] = self.yaml['image']
        data['cpu'] = int(self.yaml.get('cpu', 256))
        data['memoryReservation'] = self.yaml.get('memoryReservation', None)
        memory = self.yaml.get('memory', None)
        memory = int(memory) if memory else None
        if memory is None and data['memoryReservation'] is None:
            memory = 512
        data['memory'] = memory
        data['links'] = self.yaml.get('links', [])
        data['portMappings'] = self.get_ports()
        data['essential'] = True
        command = self.data.get('command', None)
        command = shlex.split(command) if command else None
        data['command'] = command
        entrypoint = self.data.get('entrypoint', None)
        entrypoint = shlex.split(entrypoint) if entrypoint else None
        data['entryPoint'] = entrypoint
        data['ulimits'] = self.get_ulimits()
        data['environment'] = self.get_environment()
        data['mountPoints'] = self.get_mountPoints()
        data['links'] = self.yaml.get('links', None)
        data['dockerLabels'] = self.get_dockerLabels()
        data['logConfiguration'] = self.get_logConfiguration()
        data['extraHosts'] = self.get_extraHosts()
        data['linuxCapabilities'] = self.get_linuxCapabilities()

        return data


# ----------------------------------------
# Managers
# ----------------------------------------

class TaskDefinitionManager(object):

    def __init__(self):
        self.client = get_boto3_session().client('ecs')

    def get(self, identifier):
        try:
            response = self.ecs.describe_task_definition(task_definition=identifier)
        except botocore.exceptions.ClientException:
            raise TaskDefinition.DoesNotExist(
                'No task definition matching "{}" exists in AWS'.format(identifier)
            )
        data = response['taskDefinition']
        arn = data.pop('taskDefinitionArn')
        revision = data.pop('revision')
        containers = [ContainerDefinition(d) for d in data.pop('containerDefinitions')]
        return TaskDefinition(data, containers, arn=arn, revision=revision)

    def diff(self, task_definition):
        aws_task_definition = self.get(task_definition)
        return task_definition.diff(aws_task_definition)

    def needs_update(self, task_definition):
        return self.diff(task_definition) != {}

    def create(self, task_definition):
        response = self.ecs.register_task_definition(**task_definition.render())
        return response['taskDefinition']['taskDefinitionArn']


# ----------------------------------------
# Models
# ----------------------------------------

class TaskDefinition(object):

    adapters = {
        'deployfish.yml': DeployfishYamlTaskDefinitionAdapter,
    }

    objects = TaskDefinitionManager()

    class DoesNotExist(Exception):
        pass

    @staticmethod
    def url(task_def):
        """
        Return the AWS Web Console URL for task definition ``task_def`` as
        Markdown.  Suitable for inserting into a Slack message.

        :param task_def: a "``<family>:<revision>``" identifier for a task
                         definition.  E.g. ``access-caltech-admin:1``
        :type task_def: string

        :rtype: string
        """
        region = os.environ.get('AWS_DEFAULT_REGION', 'us-west-2')
        return u"<https://{}.console.aws.amazon.com/ecs/home?region={}#/taskDefinitions/{}|{}>".format(
            region,
            region,
            re.sub(':', '/', task_def),
            task_def
        )

    @classmethod
    def new(cls, obj, source, secrets=None, extra_environment=None):
        """
        Factory method for TaskDefinition that builds self.data based on the data source.
        """
        data, kwargs = cls.adapters[source](
            obj,
            secrets=secrets,
            extra_environment=extra_environment
        ).convert()
        return cls(data, **kwargs)

    def __init__(self, data, containers, arn=None, revision=None):
        self.ecs = get_boto3_session().client('ecs')
        self.arn = None
        self.revision = None
        self.data = data
        self.containers = containers

    @property
    def exists(self):
        return self.arn is not None

    @property
    def family_revision(self):
        """
        If this task definition exists in AWS, return our ``<family>:<revision>`` string.
        Else, return ``None``.

        :rtype: string or ``None``
        """
        if self.revision:
            return "{}:{}".format(self.data['family'], self.revision)
        return None

    def get_latest_revision(self):
        return self.objects.get(self.data['family']).arn

    def update_task_labels(self, family_revisions):
        self.containers[0].update_task_labels(family_revisions)

    def get_helper_tasks(self):
        return self.containers[0].get_helper_tasks()

    def inject_environment(self, environment):
        for container in self.containers:
            container.inject_environment(environment)

    def render(self):
        data = copy(self.data)
        data['containerDefinitions'] = [c.data for c in sorted(self.containers, key=lambda x: x.name)]
        return data

    def create(self):
        return self.objects.create(self)

    def __eq__(self, other):
        if self.__class__ != other.__class__:
            return False
        return self.render() == other.render()

    def diff(self, other):
        return diff(self.render(), other.render())

    def __str__(self):
        return json.dumps(self.data, indent=2, sort_keys=True)


class ContainerDefinition(object):

    helper_task_prefix = 'edu.caltech.task'

    def __init__(self, data):
        self.ecs = get_boto3_session().client('ecs')
        self.data = data

    @property
    def name(self):
        return self.data.get('name', None)

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
        for key, value in self.dockerLabels.items():
            if key.startswith(self.helper_task_prefix):
                labels[value.split(':')[0]] = value
        return labels

    def inject_environment(self, environment):
        environment = {d['name']: d['value'] for d in self.data.get('environment', [])}
        environment.update(environment)
        self.data['environment'] = [{'name': k, 'value': v} for k, v in environment.items()]

    def diff(self, other):
        # FIXME: maybe don't compare our helper task docker labels here -- they're guaranteed to be different
        # between task definition versions
        return diff(self.data, other.data)

    def __eq__(self, other):
        if self.__class__ != other.__class__:
            return False
        return self.data == other.data

    def __str__(self):
        return json.dumps(self.data, indent=2, sort_keys=True)
