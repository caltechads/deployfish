from copy import copy
import re
import shlex

from deployfish.core.models import (
    EventScheduleRule,
    ScalableTarget,
    ServiceDiscoveryService,
    TaskDefinition,
)

from .mixins import DeployfishYamlAdapter
from .secrets import SecretsMixin


# ------------------------
# Mixins
# ------------------------

class VpcConfigurationMixin:

    def get_vpc_configuration(self):
        data = {}
        source = self.data.get('vpc_configuration', None)
        if source:
            data['subnets'] = source['subnets']
            if 'security_groups' in source:
                data['securityGroups'] = source['security_groups']
            if 'public_ip' in source:
                data['assignPublicIp'] = 'ENABLED' if source['public_ip'] else 'DISABLED'
        return data


# ------------------------
# Adapters
# ------------------------


class TaskDefinitionAdapter(DeployfishYamlAdapter):
    """
    Convert our deployfish YAML definition of our task definition to the same format that
    boto3.client('ecs').describe_task_definition() returns, but translate all container info
    into ContainerDefinitions.
    """

    def __init__(self, data, secrets=None, extra_environment=None):
        super(TaskDefinitionAdapter, self).__init__(data)
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
        volumes_data = self.data.get('volumes', [])
        for v in volumes_data:
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
        data['family'] = self.data['family']
        data['networkMode'] = self.data.get('network_mode', 'bridge')
        if 'cpu' in self.data:
            data['cpu'] = int(self.data['cpu'])
        if 'memory' in self.data:
            data['memory'] = int(self.data['memory'])
        launch_type = self.data.get('launch_type', 'EC2')
        if launch_type == 'FARGATE':
            data['requiresCompatibilities'] = ['FARGATE']
        if 'task_role_arn' in self.data:
            data['taskRoleArn'] = self.data['task_role_arn']
        if 'execution_role' in self.data:
            data['executionRoleArn'] = self.data['execution_role']
        if launch_type == 'FARGATE' and not data['executionRoleArn']:
            raise self.SchemaException(
                'If your launch_type is "FARGATE", you must supply "execution_role"'
            )
        data['volumes'] = self.get_volumes()
        containers_data = []
        for container_definition in self.data['containers']:
            containers_data.append(
                ContainerDefinitionAdapter(
                    container_definition,
                    data,
                    secrets=self.secrets,
                    extra_environment=self.extra_environment
                ).convert()
            )

        return data, {'containers': containers_data}


class ContainerDefinitionAdapter(DeployfishYamlAdapter):
    """
    Convert our deployfish YAML definition of our containers to the same format that
    boto3.client('ecs').describe_task_definition() returns for container definitions.
    """

    PORTS_RE = re.compile(r'(?P<hostPort>\d+)(:(?P<containerPort>\d+)(/(?P<protocol>udp|tcp))?)?')
    MOUNT_RE = re.compile('[^A-Za-z0-9_-]')

    def __init__(self, data, task_definition_data=None, secrets=None, extra_environment=None):
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
        data['name'] = self.data['name']
        data['image'] = self.data['image']
        data['essential'] = True
        try:
            data['cpu'] = int(self.data.get('cpu', 256))
        except ValueError:
            raise self.SchemaExeption('"cpu" must be an integer')
        if 'memoryReservation' in self.data:
            try:
                data['memoryReservation'] = int(self.data['memoryReservation'])
            except ValueError:
                raise self.SchemaExeption('"memoryReservation" must be an integer')
        if 'memory' in self.data:
            try:
                memory = int(self.data['memory'])
            except ValueError:
                raise self.SchemaExeption('"memory" must be an integer')
        elif data['memoryReservation'] is None:
            memory = 512
        data['memory'] = memory
        if 'ports' in self.data:
            data['portMappings'] = self.get_ports()
        if 'command' in self.data:
            command = self.data.get('command', None)
            command = shlex.split(command) if command else None
            data['command'] = command
        if 'entrypoint' in self.data:
            entrypoint = self.data.get('entrypoint', None)
            entrypoint = shlex.split(entrypoint) if entrypoint else None
            data['entryPoint'] = entrypoint
        if 'ulimits' in self.data:
            data['ulimits'] = self.get_ulimits()
        if 'environment' in self.data:
            data['environment'] = self.get_environment()
        if 'volumes' in self.data:
            data['mountPoints'] = self.get_mountPoints()
        if 'links' in self.data:
            data['links'] = self.data.get['links']
        if 'dockerLabels' in self.data:
            data['dockerLabels'] = self.get_dockerLabels()
        if 'logging' in self.data:
            data['logConfiguration'] = self.get_logConfiguration()
        if 'extra_hosts' in self.data:
            data['extraHosts'] = self.get_extraHosts()
        if 'cap_add' in self.data or 'cap_drop' in self.data:
            data['linuxCapabilities'] = self.get_linuxCapabilities()
        if self.secrets:
            data['secrets'] = self.get_secrets()

        return data


class StandaloneTaskAdapter(SecretsMixin, VpcConfigurationMixin, DeployfishYamlAdapter):

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
        data['cluster'] = self.data.get('cluster', 'default')
        vpc_configuration = self.get_vpc_configuration()
        if vpc_configuration:
            data['networkConfiguration'] = {}
            data['networkConfiguration']['awsVpcConfiguration'] = vpc_configuration
        data['count'] = self.yaml.get('count', 1)
        data['launchType'] = self.data.get('launch_type', 'EC2')
        if data['launchType'] == 'FARGATE':
            if 'platform_version' in self.data:
                data['platformVersion'] = self.data['platform_version']
        if 'placement_constraints' in self.data:
            data['placementConstraints'] = self.data['placement_constraints']
        if 'placement_strategy' in self.data:
            data['placementStrategy'] = self.data['placement_strategy']
        if 'group' in self.data:
            data['Group'] = self.data['group']
        kwargs = {}
        secrets = self.get_secrets(data['cluster'], data['name'], prefix='task')
        kwargs['task_definition'] = self.get_task_definition(secrets=secrets)
        if 'schedule' in self.data:
            kwargs['schedule'] = EventScheduleRule.new(self.data, 'deployfish')
        if self.secrets:
            kwargs['secrets'] = secrets
        return data, kwargs


class ServiceAdapter(SecretsMixin, VpcConfigurationMixin, DeployfishYamlAdapter):

    """
    * Service itself             [x]
    * Task definition            [x]
    * Autoscaling Group          [x]  Ignore -- we can detect this automatically
    * Application Autoscaling    [x]
    * Service Discovery          [x]
    * Helper Tasks               [ ]
    """
    def get_clientToken(self):
        return 'token-{}-{}'.format(self.data['name'], self.data['cluster'])

    def get_task_definition(self, secrets=None):
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

    def convert(self):
        data = {}
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
            data['networkConfiguration']['awsVpcConfiguration'] = vpc_configuration
        if 'placement_constraints' in self.data:
            data['placementConstraints'] = self.data['placement_constraints']
        if 'placement_strategy' in self.data:
            data['placementStrategy'] = self.data['placement_strategy']
        if 'maximum_percent' in self.data or 'minimum_healthy_percent' in self.data:
            data['deploymentConfiguration'] = {}
            data['deploymentConfiguration']['maximumPercent'] = int(self.data.get('maximum_percent', 200))
            data['deploymentConfiguration']['minimumHealthyPercent'] = int(
                self.data.get('minimum_healthy_percent', 100)
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

        kwargs = {}
        kwargs['secrets'] = self.get_secrets(self.data['cluster'], self.data['name'])
        kwargs['task_definition'] = self.get_task_definition(secrets=kwargs['secrets'])
        if 'application_scaling' in self.data:
            kwargs['appscaling'] = ScalableTarget.new(
                self.data['application_scaling'],
                'deployfish',
                cluster=self.data['cluster'],
                service=self.data['name']
            )
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

        return data, kwargs
