from copy import copy
import os
import re
import shlex
from typing import Dict, Any, Tuple, List, cast, Optional

from deployfish.core.models import (
    EventScheduleRule,
    ScalableTarget,
    ServiceDiscoveryService,
    TaskDefinition,
)
from deployfish.config import get_config
from deployfish.core.aws import get_boto3_session
from deployfish.core.models.ecs import Service
from deployfish.core.models.secrets import Secret
from deployfish.core.models.mixins import TaskDefinitionFARGATEMixin

from ..abstract import Adapter
from .mixins import SSHConfigMixin
from .secrets import SecretsMixin


# ------------------------
# Mixins
# ------------------------

class VpcConfigurationMixin:

    data: Dict[str, Any]

    def get_vpc_configuration(self, source: Dict[str, Any] = None) -> Dict[str, Any]:
        data: Dict[str, Any] = {}
        if not source:
            source = self.data.get('vpc_configuration', None)
        if source:
            data['subnets'] = source['subnets']
            if 'security_groups' in source:
                data['securityGroups'] = source['security_groups']
            if 'public_ip' in source:
                data['assignPublicIp'] = source['public_ip']
            else:
                data['assignPublicIp'] = 'DISABLED'
        return data


# ------------------------
# Abstract Adapters
# ------------------------

class AbstractTaskAdapter(VpcConfigurationMixin, Adapter):

    def is_fargate(self, _: Dict[str, Any]) -> bool:
        """
        Return ``True ``if this task definition is for FARGATE, ``False``
        otherwise.
        """
        if (
            'requiresCompatibilities' in self.data and
            self.data['requiresCompatibilities'] == ['FARGATE']
        ):
            return True
        return False

    def get_schedule_data(
        self,
        data: Dict[str, Any],
        task_definition: TaskDefinition
    ) -> Dict[str, Any]:
        """
        Construct the dict that will be given as input for configuring an
        :py:class:`deployfish.core.models.events.EventScheduleRule` and
        :py:class:`deployfish.core.models.events.EventTarget` for our helper task.

        The :py:meth:`deployfish.core.models.events.EventScheduleRule.new`
        factory method expects this struct::

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

        Args:
            data: The output of :py:meth:`get_data`
            task_definition: The task definition to schedule

        Returns:
            Data appropriate for configuring an ``EventScheduleRule`` and
            ``EventTarget``
        """
        schedule_data: Dict[str, Any] = {}
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

    def update_container_logging(
        self,
        data: Dict[str, Any],
        task_definition: TaskDefinition
    ) -> None:
        """
        When creating :py:class:`deployfish.core.models.ecs.ServiceHelperTask`
        objects, from a ``deployfish.yml`` service definition, we always create
        the tasks as FARGATE tasks.  To make a ``ServiceHelperTask``, we copy
        the service's task definition and modify it to be a FARGATE task as well
        as with the appropriate overrides from the ``tasks:`` section of the
        service definition.

        However, the service itself may be an EC2 based task.  If so, we may not
        be able to use the same logging configuration for the tasks as we do for
        the service.  This is because FARGATE tasks can only use these logging
        drivers: ``awslogs``, ``splunk``, ``awsfirelens``, while EC2 services
        and tasks have a much longer list of supported logging drivers (e.g.
        ``fluentd``).

        Or, we may not have a logging configuration at all for the service or
        task we want, in which case we need to add one.

        Examine each container in our task definition and if

        * there is no logging stanza at all for the container
        * or the logging driver is not valid for FARGATE

        replace the logging stanza with one that writes the logs to ``awslogs``.

        We'll set the log group to be either ``/<cluster>/<service>`` or
        ``/<cluster>/standalone-tasks`` depending on whether this is a
        ``ServiceHelperTask`` or a ``StandaloneTask``, and set the log
        strem prefix to that of our name

        Args:
            data: the data dict for the container
            task_definition: the
                :py:class:`deployfish.core.models.ecs.TaskDefinition` object that
                owns this container
        """
        if task_definition.is_fargate():
            for container in task_definition.containers:
                if 'logConfiguration' in container.data:
                    lc = container.data['logConfiguration']
                    if lc['logDriver'] in ['awslogs', 'splunk', 'awsfirelens']:
                        continue
                # the log configuration needs to be fixed
                try:
                    region_name: str = cast(str, get_boto3_session().region_name)
                except AttributeError:
                    region_name = os.environ.get('AWS_DEFAULT_REGION', 'us-west-2')
                if 'service' in data:
                    log_group = '/{}/{}'.format(*data['service'].split(':'))
                else:
                    log_group = f"/{data['cluster']}/standalone-tasks"
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

class TaskDefinitionAdapter(TaskDefinitionFARGATEMixin, Adapter):  # type: ignore
    """
    Convert our deployfish YAML definition of our task definition to the same
    format that :py:meth:`describe_task_definition` returns, but translate all
    container info into :py:class:`deployfish.core.models.ecs.ContainerDefinition`
    objects.

    Args:
        data: The data from deployfish.yml for this task definition

    Keyword Args:
        secrets: A list of :py:class:`deployfish.core.models.ecs.Secret` objects
            that are used by this task definition
        extra_environment: A dict of extra environment variables to add to the
            task definition
        partial: If True, this is a partial task definition, and we should be
            more lenient about what we accept as valid data.
    """

    def __init__(
        self,
        data: Dict[str, Any],
        secrets: List[Secret] = None,
        extra_environment: Dict[str, Any] = None,
        partial: bool = False
    ) -> None:
        super().__init__(data)
        self.secrets = secrets if secrets else []
        self.extra_environment = extra_environment if extra_environment else {}
        self.partial = partial

    def get_volumes(self) -> List[Dict[str, Any]]:
        """
        In the YAML, volume definitions look like this::

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

            People can only actually specify one of ``path``, ``config`` or
            ``efs_config`` -- they're mutually exclusive.  And ``path`` is not
            available for FARGATE tasks.


        Convert that to to the same structure that
        :py:meth:`describe_task_definition` returns for that info::

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

        .. warning::

            Old-style container definitions in deployfish.yml could be specified
            entirely in the container's own `volumes:` section.

        Returns:
            A list of volume definitions for this task definition.
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

    def convert(self) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        :rtype: dict(str, Any), dict(str, Any)
        """
        data: Dict[str, Any] = {}
        self.set(data, 'family')
        self.set(data, 'network_mode', dest_key='networkMode', default='bridge')
        launch_type = self.data.get('launch_type', 'EC2')
        if launch_type == 'FARGATE':
            data['requiresCompatibilities'] = ['FARGATE']
        if self.data.get('runtime_platform', None):
            data['runtimePlatform'] = {}
            data['runtimePlatform']['cpuArchitecture'] = self.data['runtime_platform'].get('cpu_architecture', 'X86_64')
            data['runtimePlatform']['operatingSystemFamily'] = self.data['runtime_platform'].get('operating_system_family', 'LINUX')
        if self.data.get('placementConstraints', None):
            data['placementConstraints'] = self.data['placementConstraints']
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
                raise self.SchemaException(
                    'You must define at least one container in your task definition'
                )
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
    Convert our deployfish YAML definition of our containers to the same format
    that :py:meth:`describe_task_definition` returns for container definitions.

    Args:
        data: a deployfish.yml container definition stanza

    Keyword Args:
        task_definition_data:
            :py:attr:`deployfish.core.models.ecs.TaskDefinition.data` from the
            owning :py:class:`deployfish.core.models.ecs.TaskDefinition`
        secrets: a list of :py:class:`deployfish.core.models.secrets.Secret`
        extra_environment: a dict of extra environment variables to add to the
            container
        partial: if ``True``, we're updating an existing
            :py:class:`deployfish.core.models.ecs.ContainerDefinition`` from a
            partial set of overrides.  Setting this to ``True`` will cause us to
            ignore any missing required fields.
    """

    PORTS_RE = re.compile(r'(?P<hostPort>\d+)(:(?P<containerPort>\d+)(/(?P<protocol>udp|tcp))?)?')
    MOUNT_RE = re.compile('[^A-Za-z0-9_-]')

    def __init__(
        self,
        data: Dict[str, Any],
        task_definition_data: Dict[str, Any] = None,
        secrets: List[Secret] = None,
        extra_environment: Dict[str, Any] = None,
        partial: bool = False
    ) -> None:
        super().__init__(data)
        self.task_definition_data = task_definition_data if task_definition_data else {}
        self.secrets = secrets if secrets else []
        self.extra_environment = extra_environment if extra_environment else {}
        self.partial = partial

    @property
    def is_fargate(self) -> bool:
        """
        Return ``True`` if this container is part of a FARGATE task
        """
        return 'FARGATE' in self.task_definition_data.get('requiresCompatibilities', [])

    def get_secrets(self) -> List[Dict[str, str]]:
        """
        Add parameter store values to the container's 'secrets' list. The task
        will fail if we try to do this and we don't have an execution role, so
        we don't pass the secrets if it doesn't have an execution role.
        """
        return [{'name': s.name, 'valueFrom': s.pk} for s in self.secrets]

    def get_mountPoints(self) -> List[Dict[str, str]]:
        """
        In ``deployfish.yml``, volumes take one of these two forms::

            volumes:
                - storage:/container/path

        or::

            volumes:
                - /host/path:/container/path
                - /host/path-ro:/container/path-ro:ro

        The first form is the new style volume definition.  The "storage" bit
        refers to a volume on the task definition named "storage", which has all
        the volume configuration info.

        The second form is the old-style volume definition.  Before we allowed
        the "volumes:" section in the task definition yml, you could define
        volumes on individual containers and the "volumes" list in the
        :py:meth:`register_task_definition` AWS API call would be
        auto-constructed based on the host and container path.

        To deal with the second form, we need to internally convert to the first
        form and add a hidden volume definition on the task definition, then
        transform the volume mountpoint to the first form.

        Returns:
            A list of dicts, each of which is a mountpoint definition for the
            container.
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
                # FIXME: if the host_path doesn't start with a /, ensure that
                # the volume already exists in the task definition, otherwise
                # raise ContainerYamlSchemaException Add this container specific
                # volume to the task definition
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

    def get_ports(self) -> List[Dict[str, Any]]:
        """
        ``deployfish.yml`` port mappings look like this::

            ports:
                - "80"
                - "8443:443"
                - "8125:8125/udp"

        Convert them to this::

            [
                {"containerPort": 80, "protocol": "tcp"},
                {"containerPort": 443, "hostPort": 8443, "protocol": "tcp"},
                {"containerPort": 8125, "hostPort": 8125, "protocol": "udp"},
            ]

        Returns:
            A list of dicts, each of which is a port mapping definition for the
            container.
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
                raise self.SchemaException(f'{mapping} is not a valid port mapping')
        return portMappings

    def get_environment(self) -> List[Dict[str, str]]:
        """
        ``deployfish.yml`` environment variables are defined in one of the two
        following ways::

            environment:
                - FOO=bar
                - BAZ=bash

        or::

            environment:
                FOO: bar
                BAZ: bash

        Convert them to this, which is what :py:meth:`describe_task_definition`
        returns::

            [
                {"name": "FOO", "value": "bar"},
                {"name": "BAZ", "value": "bash}
            ]

        Returns:
            A list of dicts, each of which is an environment variable definition
        """
        environment: List[Dict[str, str]] = []
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
            environment = [{'name': k, 'value': v} for k, v in list(source_environment.items())]
        return environment

    def get_dockerLabels(self) -> Dict[str, str]:
        """
        ``deployfish.yml`` docker labels are defined in one of the two following
        ways::

            labels:
                - FOO=bar
                - BAZ=bash

        or::

            labels:
                FOO: bar
                BAZ: bash

        Convert them to this, which is what :py:meth:`describe_task_definition`
        returns::

            {
                'FOO': 'bar',
                'BAZ': 'bash'
            {

        Returns:
            A dict of docker labels
        """
        dockerLabels: Dict[str, str] = {}
        if 'labels' in self.data:
            if isinstance(self.data['labels'], dict):
                dockerLabels = self.data['labels']
            else:
                for label in self.data['labels']:
                    key, value = label.split('=')
                    dockerLabels[key] = value
        return dockerLabels

    def get_ulimits(self) -> List[Dict[str, Any]]:
        ulimits = []
        for key, value in list(self.data['ulimits'].items()):
            # FIXME: should validate key here maybe
            if not isinstance(value, dict):
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

    def get_logConfiguration(self) -> Dict[str, Any]:
        logConfiguration: Dict[str, Any] = {}
        if 'logging' in self.data:
            if 'driver' not in self.data['logging']:
                raise self.SchemaException('logging: block must contain "driver"')
            logConfiguration['logDriver'] = self.data['logging']['driver']
            if 'options' in self.data['logging']:
                logConfiguration['options'] = self.data['logging']['options']
        return logConfiguration

    def get_linuxCapabilities(self) -> Dict[str, Any]:
        cap_add = self.data.get('cap_add', None)
        cap_drop = self.data.get('cap_drop', None)
        tmpfs = self.data.get('tmpfs', None)
        linuxCapabilities: Dict[str, Any] = {}
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
                if 'mount_options' in tc and isinstance(tc['mount_options'], list):
                    tc_append['mountOptions'] = tc['mount_options']
                linuxCapabilities['tmpfs'].append(tc_append)
        return linuxCapabilities

    def get_extraHosts(self) -> List[Dict[str, str]]:
        extraHosts: List[Dict[str, str]] = []
        for host in self.data.get('extra_hosts', []):
            hostname, ip_address = host.split(':')
            extraHosts.append({'hostname': hostname, 'ipAddress': ip_address})
        return extraHosts

    def get_cpu(self) -> Optional[int]:
        """
        Get the ``cpu`` value for this container, which is the number of cpu
        units to reserve for the container.    One full CPU is 1024 units.

        * If the task is a FARGATE task, then ``cpu`` is optional.
        * If the task is an EC2 task, then ``cpu`` is required.  If it is not
          present in the ``deployfish.yml`` file, then it defaults to 256.

        If ``cpu`` is specified then the only requirement is that the sum of all
        ``cpu`` values for all containers in the task be lower than the ``cpu``
        value specified in the task definition, if that is present.

        Raises:
            SchemaException: if the ``cpu`` value is greater than the task cpu
                value.

        Returns:
            The ``cpu`` value for this container.
        """

        if self.is_fargate:
            default = None
        else:
            default = 256
        cpu = self.data.get('cpu', default)
        if isinstance(cpu, str):
            cpu = int(cpu)
        if 'cpu' in self.task_definition_data:
            task_cpu = self.task_definition_data['cpu']
            if isinstance(task_cpu, str):
                task_cpu = int(task_cpu)
            if cpu > task_cpu:
                raise self.SchemaException(
                    'container "{}": cpu is greater than the task cpu value'.format(
                        self.data['name']
                    )
                )
        return cpu

    def get_memory(self) -> Optional[int]:
        """
        Get the ``memory`` value for this container, which is the amount
        of memory (in MiB) to allow the container to use.

        * If the task is a FARGATE task, then ``memory`` is optional.
        * If the task is an EC2 task, ``memory`` is required at the container
          level if it is not specified at the task level.

        If ``memory`` is specified then the only requirement is that the sum of all
        ``memory`` values for all containers in the task be lower than the ``memory``
        value specified in the task definition, if that is present.

        Raises:
            SchemaException: if the container memory is greater than the task memory
            SchemaException: if the task is an EC2 task and ``memory`` is not
                specified in container definition the ``deployfish.yml`` file and is
                also not present at the task level in the ``deployfish.yml`` file.

        Returns:
            The ``cpu`` value for this container.
        """
        if self.is_fargate:
            if 'memory' not in self.data:
                return None
        if 'memory' not in self.data:
            if 'memory' in self.task_definition_data:
                return None
            if not self.partial:
                raise self.SchemaException(
                    'container "{}": memory is required for containers if not specified at the task level'.format(
                        self.data['name']
                    )
                )
            return None
        memory = self.data['memory']
        if isinstance(memory, str):
            memory = int(memory)
        if 'memory' in self.task_definition_data:
            task_memory = self.task_definition_data['memory']
            if isinstance(task_memory, str):
                task_memory = int(task_memory)
            if memory > task_memory:
                raise self.SchemaException(
                    'container "{}": memory is greater than task memory'.format(self.data['name'])
                )
        return memory

    def convert(self) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        data: Dict[str, Any] = {}
        self.set(data, 'name')
        self.set(data, 'image')
        self.set(data, 'essential', default=True)
        cpu = self.get_cpu()
        try:
            self.set(data, 'memoryReservation', optional=True, convert=int)
        except ValueError:
            raise self.SchemaException(
                'container "{}": "memoryReservation" must be an integer'.format(
                    self.data['name']
                )
            )
        if cpu is not None:
            data['cpu'] = cpu
        memory = self.get_memory()
        if memory is not None:
            data['memory'] = memory
        # If neither memory nor memoryReservation are specified, and this is not
        # a partial update of a container definition (i.e. we are overriding our
        # parent task definition in a ServiceHelperTask) AND this is not a
        # FARGATE task, then set memory to 512
        memoryReservation = data.get('memoryReservation', None)
        if memoryReservation is None and memory is None:
            if not self.partial:
                if not self.is_fargate:
                    data['memory'] = 512
        if memoryReservation is not None and memory is not None:
            if memoryReservation >= memory:
                raise self.SchemaException(
                    'container "{}": "memoryReservation" must be less than "memory"'.format(
                        self.data['name']
                    )
                )
        if 'ports' in self.data:
            data['portMappings'] = self.get_ports()
        self.set(data, 'command', optional=True, convert=shlex.split)
        self.set(data, 'entrypoint', dest_key='entryPoint', optional=True, convert=shlex.split)
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

    def get_task_definition(self, secrets: List[Secret] = None) -> TaskDefinition:
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

    def convert(self) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        data: Dict[str, Any] = {}
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
                data['service'] = f"{service_data['cluster']}:{service_data['name']}"
        data['cluster'] = self.data.get('cluster', 'default')
        vpc_configuration = self.get_vpc_configuration()
        if vpc_configuration:
            data['networkConfiguration'] = {}
            data['networkConfiguration']['awsvpcConfiguration'] = vpc_configuration
        data['count'] = self.data.get('count', 1)
        data['launchType'] = self.data.get('launch_type', 'EC2')
        if data['launchType'] == 'FARGATE':
            data['platformVersion'] = self.data.get('platform_version', 'LATEST')
        if self.data.get('runtime_platform', None):
            data['runtimePlatform'] = {}
            data['runtimePlatform']['cpuArchitecture'] = self.data['runtime_platform'].get('cpu_architecture', 'X86_64')
            data['runtimePlatform']['operatingSystemFamily'] = self.data['runtime_platform'].get('operating_system_family', 'LINUX')
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
        kwargs: Dict[str, Any] = {}
        secrets: List[Secret] = []
        if 'config' in self.data:
            secrets = self.get_secrets(data['cluster'], f"task-{data['name']}", decrypt=False)
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

    def __init__(self, data: Dict[str, Any], service: Service):
        """
        Args:
            data: the ``tasks:`` section from our service definition in deployfish.yml
            service: the :py:class:`deployfish.core.models.ecs.Service` for
                which we are building helper tasks
        """
        self.data = data
        self.service = service

    def _set(
        self,
        data: Dict[str, Any],
        task: Dict[str, Any],
        yml_key: str,
        data_key: str,
        source: Dict[str, Any] = None
    ) -> None:
        """
        Set a ``data[data_key]`` on the dict ``data`` by looking at both
        ``task`` and ``source``.

        If ``task[yml_key]`` exists, set ``data[data_key]`` to that value.
        Else if ``source[yml_key`]`` exists, set ``data[data_key]`` to THAT value.
        Else if ``source[data_key]`` exists, set ``data[data_key]`` to THAT value.
        Else, do nothing.

        .. note::

            This is called ``_set`` because it overrides Adapter.set(), but has
            different args.

        If ``source`` is ``None``, we set ``source`` to `self.service.data`.
        """
        if not source:
            source = self.service.data
        if yml_key in task:
            data[data_key] = task[yml_key]
        elif yml_key in source:
            data[data_key] = source[yml_key]
        elif data_key in source:
            data[data_key] = source[data_key]

    def get_data(
        self,
        data: Dict[str, Any],
        task: Dict[str, Any],
        source: Dict[str, Any] = None
    ) -> None:
        """
        Construct ``data`` so that it can be used for constructing our
        :py:class:`deployfish.core.models.ecs.ServiceHelperTask` parameters by
        combining data from an existing
        :py:class:`deployfish.core.models.ecs.TaskDefinition` with configuration
        from deployfish.yml.

        Args:
            data: the dict we are building
            task: the task configuration from deployfish.yml

        Keyword Args:
            source: the data from the previous set of Task parameters.  If not
                provided, ``self.service.data``.
        """
        if not source:
            source = self.service.data
        self._set(data, task, 'cluster', 'cluster', source=source)
        if 'vpc_configuration' in task:
            data['networkConfiguration'] = {}
            data['networkConfiguration']['awsvpcConfiguration'] = self.get_vpc_configuration(
                source=task['vpc_configuration']
            )
        elif 'networkConfiguration' in source:
            data['networkConfiguration'] = {}
            data['networkConfiguration']['awsvpcConfiguration'] = source['networkConfiguration']['awsvpcConfiguration']
        self._set(data, task, 'launch_type', 'launchType', source=source)
        if 'launchType' in data and data['launchType'] == 'FARGATE':
            self._set(data, task, 'platform_version', 'platformVersion', source=source)
            if 'platformVersion' not in data:
                data['platformVersion'] = 'LATEST'
        else:
            # capacity_provider_strategy and launch_type are mutually exclusive
            self._set(data, task, 'capacity_provider_strategy', 'capacityProviderStrategy', source=source)
        self._set(data, task, 'placement_constraints', 'placementConstraints', source=source)
        self._set(data, task, 'placement_strategy', 'placementStrategy', source=source)
        self._set(data, task, 'group', 'group', source=source)
        if 'count' in task:
            data['count'] = task['count']
        self._set(data, task, 'schedule', 'schedule', source=source)
        self._set(data, task, 'schedule_role', 'schedule_role', source=source)

    def update_container_environments(
        self,
        task_definition: TaskDefinition,
        extra_environment: Dict[str, str]
    ) -> None:
        """
        Update the deployfish-specific environment variables in the container environment for each
        container in `task_definition`.

        * Remove DEPLOYFISH_SERVICE_NAME
        * Add DEPLOYFISH_TASK_NAME
        * Update DEPLOYFISH_ENVIRONMENT and DEPLOYFISH_CLUSTER_NAME as necessary
        """
        for container in task_definition.containers:
            environment = []
            for var in container.data['environment']:
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

    def _get_base_task_data(
        self,
        task_data: Dict[str, Any],
        service_td: TaskDefinition
    ) -> Tuple[Dict[str, Any], TaskDefinition]:
        """
        Build a dict that takes info from the service and overlays the generic
        (not command specific) task data to build the parameters we'll need when
        running the task.  Also build a new TaskDefinition object that is the
        service's TaskDefinition overlaid with the changes from the generic task
        data.

        Args:
            task_data: the generic helper task data
            service_td: the Service's
                :py:class:`deployfish.core.models.ecs.TaskDefinition` object

        Returns:
            A 2-tuple: dict of parameters for the factory method of
            :py:class:`deployfish.core.models.ecs.ServiceHelperTask`, and the
            new TaskDefinition object
        """
        data_base: Dict[str, Any] = {}
        # first, extract whatever we can from self.service
        self.get_data(data_base, task_data)
        data_base['service'] = self.service.pk
        # This base_td_overlay here should be just the things we want to change
        # from the service's TaskDefinition
        base_td_overlay = TaskDefinition.new(task_data, 'deployfish', partial=True)
        # Then we add the service's TaskDefinition to the base_td_overlay to get the
        # one for the ServiceHelperTask
        base_td = service_td + base_td_overlay
        base_td.data['family'] = task_data.get('family', f"{service_td.data['family']}-tasks")
        # Remove any portMappings fro our task definition -- we don't need them
        # for ephemeral tasks
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

    def _preprocess_task_data(self, task_data: Dict[str, Any], service_td: TaskDefinition) -> None:
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
                    for command_name, command in list(container_data['commands'].items()):
                        task_data['commands'].append({
                            'name': command_name,
                            'containers': [{
                                'name': container_data['name'],
                                'command': command
                            }]
                        })
                    del container_data['commands']

    def _get_command_specific_data(
        self,
        command_data: Dict[str, Any],
        data_base: Dict[str, Any],
        base_td: TaskDefinition
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Build a dict that takes info from the output of
        :py:meth:`_get_base_task_data` and overlays the command specific task data
        to build the parameters we'll need when running the task.  Also build a
        new TaskDefinition object that is the TaskDefinition returned by
        :py:meth:`_get_base_task_data` overlaid with the changes from the command
        specific task data.

        Args:
            commmand: the command specific task data
            data_base: the dict returned by self._get_base_task_data()
            service_td: the TaskDefinition object returned by self._get_base_task_data()

        Returns:
            A 2-tuple: dict of parameters for the factory method of
            :py:class:`deployfish.core.models.ecs.ServiceHelperTask`, and the
            new TaskDefinition object
        """
        data: Dict[str, Any] = {}
        kwargs: Dict[str, Any] = {}
        # Build our new Task data based on the general task overlay we got from
        # self._get_base_task_data()
        self.get_data(data, command_data, source=data_base)
        data['service'] = self.service.pk
        if 'cluster' not in data:
            data['cluster'] = self.service.data['cluster']
        try:
            data['name'] = command_data['name']
        except KeyError:
            raise self.SchemaException(
                'Service(pk="{}"): Each helper task must have a "name" assigned in the "commands" section'.format(
                    self.service.pk
                )
            )
        if 'family' not in command_data:
            # Make the task definition family be named after our command
            command_name = command_data['name'].replace('_', '-')
            command_data['family'] = f"{base_td.data['family']}-{command_name}"
        # Generate our overlay task definition
        command_td_overlay = TaskDefinition.new(command_data, 'deployfish', partial=True)
        # Use that to make our actual task definition
        command_td = base_td + command_td_overlay
        # Update the deployfish specific environment variables in our task definition's containers
        self.update_container_environments(
            command_td,
            {
                'DEPLOYFISH_TASK_NAME': command_data['family'],
                'DEPLOYFISH_CLUSTER_NAME': data['cluster'],
                'DEPLOYFISH_ENVIRONMENT': self.service.deployfish_environment
            }
        )
        kwargs['task_definition'] = command_td
        # See if we need to schedule this command
        if 'schedule' in command_data:
            if 'schedule_role' not in data:
                raise self.SchemaException(
                    f'''ServiceHelperTask("{command_data['name']}") in Service("{self.service.pk}"): '''
                    '"schedule_role" is required when you specify a schedule'
                )
            kwargs['schedule'] = EventScheduleRule.new(self.get_schedule_data(data, command_td), 'deployfish')
        return data, kwargs

    def convert(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:  # type: ignore
        data_list = []
        kwargs_list = []
        service_td = self.service.task_definition.copy()
        if 'tasks' in self.data:
            for task in self.data['tasks']:
                # Preprocess the data to turn the old-style command definitions
                # into the new style definitions
                self._preprocess_task_data(task, service_td)
                data_base, base_td = self._get_base_task_data(task, service_td)
                # Now iterate through each item in task -> commands
                for command in task['commands']:
                    command_data, command_kwargs = self._get_command_specific_data(
                        command,
                        data_base,
                        base_td
                    )
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
    * ECS Exec                   [x]

    Helper Tasks
    ------------

    Helper tasks are overlays for the service's task definition.  Each task listed under the `tasks` section of
    the service consists of general overrides, and then a set of specific command overrides, possibly with schedules.

    .. code-block:: yaml

        services:
            - name: foobar-prod
              ...

              tasks:
                  # general overrides
                - network_mode: bridge
                  task_role_arn: new task role
                  containers:



    """

    def __init__(self, data: Dict[str, Any], **kwargs):
        self.load_secrets: bool = kwargs.pop('load_secrets', True)
        super().__init__(data, **kwargs)

    def get_clientToken(self) -> str:
        return f"token-{self.data['name']}-{self.data['cluster']}"[:35]

    def get_task_definition(self) -> TaskDefinition:
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

    def get_loadBalancers(self) -> List[Dict[str, Any]]:
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

    def __build_Service__data(self, data: Dict[str, Any]) -> None:
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
        if 'healthCheckGracePeriodSeconds' in self.data:
            data['healthCheckGracePeriodSeconds'] = self.data['healthCheckGracePeriodSeconds']
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
        data['enableExecuteCommand'] = self.data.get('enable_exec', False)
        data['enableECSManagedTags'] = True
        if 'propagateTags' in self.data:
            data['propagateTags'] = self.data['propagateTags']

    def __build_Secrets(self) -> List[Secret]:
        """
        Build a list of Secret and ExternalSecret objects from our Service's config: section.

        :rtype: list(Union[Secret, ExternalSecret])
        """
        if self.load_secrets:
            # We only need secret values if we're explicitly showing them
            secrets = self.get_secrets(self.data['cluster'], self.data['name'], decrypt=False)
        else:
            secrets = []
        return secrets

    def __build_TaskDefinition(self, kwargs: Dict[str, Any]) -> None:
        kwargs['task_definition'] = self.get_task_definition()

    def __build_application_scaling_objects(self, kwargs: Dict[str, Any]) -> None:
        if 'application_scaling' in self.data:
            kwargs['appscaling'] = ScalableTarget.new(
                self.data['application_scaling'],
                'deployfish',
                cluster=self.data['cluster'],
                service=self.data['name']
            )

    def __build_ServiceDiscoveryService(self, kwargs: Dict[str, Any]) -> None:
        if 'service_discovery' in self.data:
            if self.data.get('network_mode', 'bridge') == 'awsvpc':
                kwargs['service_discovery'] = ServiceDiscoveryService.new(
                    self.data['service_discovery'],
                    'deployfish',
                )
            else:
                raise self.SchemaException('You must use network_mode of "awsvpc" to enable service discovery')

    def __build_tags(self, kwargs: Dict[str, Any]) -> None:
        tags = {}
        tags['Environment'] = self.data.get('environment', 'test')
        kwargs['tags'] = tags

    def convert(self) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        .. note::

            ServiceHelperTasks are constructed in Service.new(), because
        """
        data, kwargs = super().convert()
        self.__build_Service__data(data)
        self.__build_TaskDefinition(kwargs)
        self.__build_application_scaling_objects(kwargs)
        self.__build_ServiceDiscoveryService(kwargs)
        self.__build_tags(kwargs)
        if 'autoscalinggroup_name' in self.data:
            kwargs['autoscalinggroup_name'] = self.data['autoscalinggroup_name']
        return data, kwargs
