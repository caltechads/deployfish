#!/usr/bin/env python
from __future__ import print_function

import botocore
import json
import os
import os.path
import re
import shlex
import time

from copy import copy

from botocore.exceptions import ClientError

from deployfish.aws import get_boto3_session
from deployfish.aws.systems_manager import ParameterStore

from .TaskScheduler import TaskScheduler


class VolumeMixin(object):
    """
    This mixin provides a method that both `TaskDefinition` and
    `ContainerDefinition` use to generate the volume 'name' attribute on the
    `TaskDefinition`.

    Since both `TaskDefinition` and `ContainerDefinition` generate that name in
    the same way, we don't have to name the volume in the `TaskDefinition` and
    pass those names to the `ContainerDefinitions`.
    """

    MOUNT_RE = re.compile('[^A-Za-z0-9_-]')

    def mount_from_host_path(self, host_path):
        """
        Generate an AWS compatible volume name for our `TaskDefinition`.  This
        is the `name` key in the volume definition we supply to
        `register_task_definition()` (example below):

            {
            'name': 'volume_name',
            'host': { 'sourcePath': 'host_path' }
            }

        :param host_path: the absolute path to a folder or file on the container
                          instance
        :type host_path: string

        :rtype: string
        """
        mount = self.MOUNT_RE.sub('_', host_path)
        mount = mount[254] if len(mount) > 254 else mount
        return mount


class LogConfiguration(object):
    """
    Manage the logging configuration in a container definition.
    """

    def __init__(self, aws=None, yml=None):
        if aws:
            self.from_aws(aws or {})

        if yml:
            self.from_yaml(yml or {})

    def from_aws(self, aws):
        self.driver = aws['logDriver']
        self.options = aws['options']

    def from_yaml(self, yml):
        self.driver = yml['driver']
        self.options = yml['options']

    def render(self):
        return(self.__render())

    def __render(self):
        return {'logDriver': self.driver, 'options': self.options}


class Secret(object):
    """
    Simple class to render a parameter store secret in the container definition
    """

    def __init__(self, name, value):
        self.name = name
        self.value = value

    def render(self):
        return {'name': self.name, 'valueFrom': self.value}


class SecretsConverter(object):
    """
    Convert a parameter store to a list of Secret objects
    """

    def __init__(self, parameter_store):
        self.parameter_store = parameter_store
        self.secrets = []
        self.__convert_to_secrets()

    def __convert_to_secrets(self):
        for parameter in self.parameter_store:
            name = parameter.key
            value = parameter.name
            secret = Secret(name, value)
            self.secrets.append(secret)


class ContainerDefinition(VolumeMixin):
    """
    Manage one of the container definitions in a `TaskDefinition`.
    """

    def __init__(self, aws=None, yml=None):
        """
        :param aws: an entry from the `containerDefinitions` list in the
                           dictionary returned by `describe_task_definitions()`. If
                           the container has any volumes, this dict will differ from
                           the canonical AWS source in that it will have volume definitions
                           from the task definition added.
        :type aws: dict

        :param yml: a container definition from our deployfish.yml file
        :type yml: dict
        """
        self.ecs = get_boto3_session().client('ecs')
        self.ecr = get_boto3_session().client('ecr')
        self.__aws_container_definition = aws

        self._name = None
        self._cpu = None
        self._image = None
        self._memory = None
        self._memoryReservation = None
        self._command = None
        self._entryPoint = None
        self._essential = True
        self._dockerLabels = {}
        self._volumes = []
        self._extraHosts = []
        self._links = []
        self._ulimits = []
        self._cap_add = []
        self._cap_drop = []
        self._tmpfs = []
        self._environment = {}
        self._portMappings = []
        self.logConfiguration = None
        self.secrets = []

        if aws and 'logConfiguration' in aws:
            self.logConfiguration = LogConfiguration(aws['logConfiguration'])

        if yml:
            self.from_yaml(yml)

    def __getattr__(self, attr):
        try:
            return self.__getattribute__(attr)
        except AttributeError:
            if attr in ['cpu', 'dockerLabels', 'essential', 'image', 'links', 'memory', 'memoryReservation', 'name']:
                if (not getattr(self, '_' + attr) and self.__aws_container_definition
                        and attr in self.__aws_container_definition):
                    setattr(self, "_" + attr, self.__aws_container_definition[attr])
                return getattr(self, '_' + attr)
            elif attr == 'environment':
                if (not self._environment and self.__aws_container_definition
                        and 'environment' in self.__aws_container_definition):
                    environment = self.__aws_container_definition['environment']
                    for var in environment:
                        self._environment[var['name']] = var['value']
                return self._environment
            elif attr == 'portMappings':
                if (not self._portMappings and self.__aws_container_definition
                        and 'portMappings' in self.__aws_container_definition):
                    ports = self.__aws_container_definition['portMappings']
                    for mapping in ports:
                        self._portMappings.append(
                            '{}:{}/{}'.format(mapping['hostPort'], mapping['containerPort'], mapping['protocol'])
                        )
                return self._portMappings
            elif attr == 'command':
                if (not self._command and self.__aws_container_definition
                        and 'command' in self.__aws_container_definition):
                    self._command = ' '.join(self.__aws_container_definition['command'])
                return self._command
            elif attr == 'entryPoint':
                if (not self._entryPoint and self.__aws_container_definition
                        and 'entryPoint' in self.__aws_container_definition):
                    self._entryPoint = ' '.join(self.__aws_container_definition['entryPoint'])
                return self._entryPoint
            elif attr == 'ulimits':
                if (not self._ulimits and self.__aws_container_definition
                        and 'ulimits' in self.__aws_container_definition):
                    for ulimit in self.__aws_container_definition['ulimits']:
                        self._ulimits.append({
                            'name': ulimit['name'],
                            'soft': ulimit['softLimit'],
                            'hard': ulimit['hardLimit'],
                        })
                return self._ulimits
            elif attr == 'cap_add':
                if (not self._cap_add and self.__aws_container_definition):
                    try:
                        self._cap_add = self.__aws_container_definition['linuxParameters']['capabilites']['add']
                    except KeyError:
                        pass
                return self._cap_add
            elif attr == 'cap_drop':
                if (not self._cap_drop and self.__aws_container_definition):
                    try:
                        self._cap_drop = self.__aws_container_definition['linuxParameters']['capabilites']['drop']
                    except KeyError:
                        pass
                return self._cap_drop
            elif attr == 'tmpfs':
                if (not self._tmpfs and self.__aws_container_definition):
                    try:
                        self._tmpfs = self.__aws_container_definition['linuxParameters']['tmpfs']
                    except KeyError:
                        pass
                return self._tmpfs
            else:
                raise AttributeError

    def __setattr__(self, attr, value):
        if attr in [
            'command',
            'cpu',
            'dockerLabels',
            'entryPoint',
            'environment',
            'essential',
            'image',
            'links',
            'memory',
            'memoryReservation',
            'name',
            'ulimits',
            'cap_add',
            'cap_drop',
            'tmpfs',
        ]:
            setattr(self, "_" + attr, value)
        else:
            super(ContainerDefinition, self).__setattr__(attr, value)

    @property
    def extraHosts(self):
        """
        Return a deployfish-formatted version of the container's extra hosts
        (extra lines to add to the ``/etc/hosts`` file for the container).

        We'll return extra hosts definitions that look like this:

            "HOSTNAME:IPADDRESS"

        :rtype: list of strings
        """
        if (not self._extraHosts and self.__aws_container_definition
                and 'extraHosts' in self.__aws_container_definition):
            for eh in self.__aws_container_definition['extraHosts']:
                self._extraHosts.append('{}:{}'.format(eh['hostname'], eh['ipAddress']))
        return self._extraHosts

    @extraHosts.setter
    def extraHosts(self, extraHosts):
        self._extraHosts = extraHosts

    @property
    def volumes(self):
        """
        Return a deployfish-formatted version of the volumes for this
        container.  Volume definitions will always look like one of:

            "HOST:CONTAINER"
            "HOST:CONTAINER:ro"

        where `HOST` is either the path on the container instance to mount
        or a name from the ``volumes`` section of the deployfish.yml `services`
        stanza, and `CONTAINER` is the path in the container on which to mount that.

        :rtype: list of strings
        """

        # self.__aws_container_definition["sourceVolumes"] is not from AWS; it's
        # something we injected in TaskDefinition.from_aws()
        if (not self._volumes and self.__aws_container_definition and 'mountPoints' in self.__aws_container_definition):
            cd = self.__aws_container_definition
            for mp in cd['mountPoints']:
                print('sourceVolumes: {}'.format(cd['sourceVolumes']))
                name = mp['sourceVolume']
                print('name: {}'.format(name))
                volume = "{}:{}".format(
                    cd['sourceVolumes'][name]['host']['sourcePath'],
                    mp['containerPath']
                )
                if mp['readOnly']:
                    volume += ":ro"
                self._volumes.append(volume)
        return self._volumes

    @volumes.setter
    def volumes(self, value):
        self._volumes = value

    def inject_environment(self, environment):
        self.environment.update(environment)

    def __render(self):  # NOQA
        """
        Generate the dict we will pass to boto3's `register_task_definition()`
        in the `containerDefinitions` section.  This will be called by the
        parent `TaskDefinition` when generating the full set of arguments for
        `register_task_definition()`
        """
        r = {
            'name': self.name,
            'image': self.image,
            'cpu': self.cpu
        }
        if self.memory is not None:
            r['memory'] = self.memory
        if self.memoryReservation is not None:
            r['memoryReservation'] = self.memoryReservation
        if self.portMappings:
            r['portMappings'] = []
            for mapping in self.portMappings:
                fields = str(mapping).split(':')
                m = {}
                if len(fields) == 1:
                    m['containerPort'] = int(fields[0])
                    m['protocol'] = 'tcp'
                else:
                    m['hostPort'] = int(fields[0])
                    m['containerPort'] = fields[1]
                    if '/' in m['containerPort']:
                        # 2020-01-27: WTF PyCharm? dict absolutely does define __getitem__.
                        # noinspection PyUnresolvedReferences
                        (port, protocol) = m['containerPort'].split('/')
                        m['containerPort'] = int(port)
                        m['protocol'] = protocol
                    else:
                        m['containerPort'] = int(m['containerPort'])
                        m['protocol'] = 'tcp'
                r['portMappings'].append(m)
        r['essential'] = self.essential
        if self.entryPoint:
            r['entryPoint'] = shlex.split(self.entryPoint)
        if self.command:
            r['command'] = shlex.split(self.command)
        if self.links:
            r['links'] = self.links
        if self.environment:
            r['environment'] = []
            for key, value in self.environment.items():
                r['environment'].append({
                    'name': key,
                    'value': value
                })
        if self.ulimits:
            r['ulimits'] = []
            for limit in self.ulimits:
                lc = {
                    'name': limit['name'],
                    'softLimit': limit['soft'],
                    'hardLimit': limit['hard']
                }
                r['ulimits'].append(lc)
        if self.dockerLabels:
            r['dockerLabels'] = self.dockerLabels
        if self.volumes:
            r['mountPoints'] = []
            for volume in self.volumes:
                v = {}
                fields = volume.split(':')
                v['sourceVolume'] = self.mount_from_host_path(fields[0])
                v['containerPath'] = fields[1]
                if len(fields) == 3:
                    if fields[2] == 'ro':
                        v['readOnly'] = True
                else:
                    v['readOnly'] = False
                r['mountPoints'].append(v)
        if self.extraHosts:
            r['extraHosts'] = []
            for eh in self.extraHosts:
                hostname, ipAddress = eh.split(':')
                r['extraHosts'].append({'hostname': hostname, 'ipAddress': ipAddress})
        if self.logConfiguration:
            r['logConfiguration'] = self.logConfiguration.render()
        if self.cap_add or self.cap_drop or self.tmpfs:
            r['linuxParameters'] = {}
            if self.cap_add or self.cap_drop:
                r['linuxParameters']['capabilities'] = {}
                if self.cap_add:
                    r['linuxParameters']['capabilities']['add'] = self.cap_add
                if self.cap_drop:
                    r['linuxParameters']['capabilities']['drop'] = self.cap_drop
            if self.tmpfs:
                r['linuxParameters']['tmpfs'] = self.tmpfs
        if self.secrets:
            secrets = []
            for secret in self.secrets:
                secrets.append(secret.render())
            r['secrets'] = secrets
        return r

    def update_task_labels(self, family_revisions):
        """
        If our service has helper tasks (as defined in the `tasks:` section of
        the deployfish.yml file), we need to record the appropriate
        `<family>:<revision>` of each of our helper tasks for each version of
        our service.  We do that by storing them as docker labels on the first
        container of the service task definition.

        This method purges any existing helper task related dockerLabels and
        replaces them with the contents of `labels`, a dict for which the key is
        the docker label key and the value is the docker label value.

        The `family_revisions` list is a list of the `<family>:<revision>` strings
        for all the helper tasks for the service.

        We're storing the task ``<family>:<revision>`` for the helper tasks for
        our application in the docker labels on the container.   All such labels
        will start with "`edu.caltech.task.`",

        :param family_revisions: dict of `<family>:<revision>` strings
        :type family_revisions: list of strings
        """
        labels = {}
        for key, value in self.dockerLabels.items():
            if not key.startswith('edu.caltech.task'):
                labels[key] = value
        for revision in family_revisions:
            family = revision.split(':')[0]
            labels['edu.caltech.task.{}.id'.format(family)] = revision
        self.dockerLabels = labels

    def get_helper_tasks(self):
        """
        Return a information about our helper tasks for this task definition.
        This is in the form of a dictionary like so:

            {`<helper_task_family>`: `<helper_task_family>:<revision>`, ...}

        If our service has helper tasks (as defined in the `tasks:` section of
        the deployfish.yml file), we've recorded the appropriate
        `<family>:<revision>` of each them as docker labels in the container
        definition of the first container in the task definition.

        Those docker labels will be in this form:

            edu.caltech.tasks.<task name>.id=<family>:<revision>

        :rtype: dict of strings
        """
        labels = {}
        for key, value in self.dockerLabels.items():
            if key.startswith('edu.caltech.task'):
                labels[value.split(':')[0]] = value
        return labels

    def render(self):
        return(self.__render())

    def from_yaml(self, yml):  # NOQA
        """
        Load this object from data in from a container section of the
        `deployfish.yml` file.

        :param yml: a container section from our deployfish.yml file
        :type yml: dict
        """
        self.name = yml['name']
        self.image = yml['image']
        if 'cpu' in yml:
            self.cpu = yml['cpu']
        else:
            self.cpu = 256  # Give a reasonable default if none was specified
        if 'memory' in yml:
            self.memory = yml['memory']
        if 'memoryReservation' in yml:
            self.memoryReservation = yml['memoryReservation']
        if self.memory is None and self.memoryReservation is None:
            self.memory = 512  # Give a reasonable default if none was specified
        if 'command' in yml:
            self.command = yml['command']
        if 'entrypoint' in yml:
            self.entryPoint = yml['entrypoint']
        if 'ports' in yml:
            self.portMappings = yml['ports']
        if 'ulimits' in yml:
            for key, value in yml['ulimits'].items():
                if type(value) != dict:
                    soft = value
                    hard = value
                else:
                    soft = value['soft']
                    hard = value['hard']
                self.ulimits.append({
                    'name': key,
                    'soft': soft,
                    'hard': hard
                })
        if 'environment' in yml:
            if type(yml['environment']) == dict:
                self.environment = yml['environment']
            else:
                for env in yml['environment']:
                    key, value = env.split('=')[0], '='.join(env.split('=')[1:])
                    self.environment[key] = value
        if 'links' in yml:
            self.links = yml['links']
        if 'labels' in yml:
            if type(yml['labels']) == dict:
                self.dockerLabels = yml['labels']
            else:
                for label in yml['labels']:
                    key, value = label.split('=')
                    self.dockerLabels[key] = value
        if 'volumes' in yml:
            self.volumes = yml['volumes']
        if 'extra_hosts' in yml:
            self.extraHosts = yml['extra_hosts']
        if 'logging' in yml:
            self.logConfiguration = LogConfiguration(yml=yml['logging'])
        if 'cap_add' in yml:
            self.cap_add = yml['cap_add']
        if 'cap_drop' in yml:
            self.cap_drop = yml['cap_drop']
        if 'tmpfs' in yml:
            for tc in yml['tmpfs']:
                tc_append = {
                    'containerPath': tc['container_path'],
                    'size': tc['size']
                }
                if 'mount_options' in tc and type(tc['mount_options']) == list:
                    tc_append['mountOptions'] = tc['mount_options']
                self.tmpfs.append(tc_append)

    def set_parameter_store(self, parameter_store):
        """
        Add parameter store values to the 'secrets' list
        """
        converter = SecretsConverter(parameter_store)
        if converter.secrets:
            self.secrets = converter.secrets

    def __str__(self):
        """
        Pretty print what we would pass to `register_task_definition()` in the
        `containerDefinitions` argument.
        """
        return json.dumps(self.render(), indent=2, sort_keys=True)


class TaskDefinition(VolumeMixin):
    """
    An object representing an ECS task definition.
    """

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

    def __init__(self, task_definition_id=None, yml=None):
        self.ecs = get_boto3_session().client('ecs')

        self.__defaults()
        if task_definition_id:
            self.from_aws(task_definition_id)
        if yml:
            self.from_yaml(yml)

    def __defaults(self):
        self._family = None
        self._taskRoleArn = None
        self._networkMode = 'bridge'
        self._revision = None
        self.containers = []
        self.__aws_task_definition = {}
        self.requiresCompatibilities = []
        self._cpu = None
        self._memory = None
        self._executionRoleArn = None
        self._volumes = []

    def from_aws(self, task_definition_id):
        self.__aws_task_definition = self.__get_task_definition(task_definition_id)
        # In AWS, the task definition knows the "volume name" to host path
        # mapping and stores it in its "volumes" portion of the task definition,
        # and the container definition knows to mount "volume name" on container
        # path, so in order to get the "host_path:container_path" string like
        # what docker-compose uses, we need a bit of info from the task def and
        # a bit from the container def.

        # We'd like the container definition to be able to return
        # "volume_name:container_path", so we inject the "volume name" to host
        # path mapping into the container definition dict from AWS as
        # "sourceVolumes"

        sourceVolumes = {}
        if 'volumes' in self.__aws_task_definition and self.__aws_task_definition['volumes']:
            for v in self.__aws_task_definition['volumes']:
                sourceVolumes[v['name']] = v
                # v here looks like the following:
                #
                # v = {
                #       'name': 'string',
                #       'host': {
                #           'sourcePath': 'string'
                #       },
                #       'dockerVolumeConfiguration': {
                #           'scope': 'task'|'shared',
                #           'autoprovision': True|False,
                #           'driver': 'string',
                #           'driverOpts': {
                #               'string': 'string'
                #           },
                #           'labels': {
                #               'string': 'string'
                #           }
                #       }
                #   }

        self.containers = []
        for cd in self.__aws_task_definition['containerDefinitions']:
            if sourceVolumes:
                cd['sourceVolumes'] = sourceVolumes
            self.containers.append(ContainerDefinition(cd))

    @property
    def arn(self):
        """
        If this task definition exists in AWS, return our ARN.
        Else, return ``None``.

        :rtype: string or ``None``
        """
        if self.__aws_task_definition:
            return self.__aws_task_definition['taskDefinitionArn']
        return None

    @property
    def executionRoleArn(self):
        """
        Return the execution role of our service. Only needed if launchType is FARGATE
        and logDriver is awslogs.

        :rtype: string
        """
        if self.__aws_service:
            self._executionRoleArn = self.__aws_service['executionRoleArn']
        return self._executionRoleArn

    @executionRoleArn.setter
    def executionRoleArn(self, executionRoleArn):
        self._executionRoleArn = executionRoleArn

    @property
    def family_revision(self):
        """
        If this task definition exists in AWS, return our ``<family>:<revision>`` string.
        Else, return ``None``.

        :rtype: string or ``None``
        """
        if self.__aws_task_definition:
            return "{}:{}".format(self.family, self.revision)
        else:
            return None

    def __load_volumes_from_aws(self):
        for v in self.__aws_task_definition['volumes']:
            v_dict = {'name': v['name']}
            if 'host' in v:
                v_dict['path'] = v['host']['sourcePath']
            elif 'dockerVolumeConfiguration' in v:
                dvc = v['dockerVolumeConfiguration']
                v_dict['config'] = {}
                v_dict['config']['scope'] = dvc['scope']
                v_dict['config']['driver'] = dvc['driver']
                if 'autoprovision' in dvc:
                    v_dict['config']['autoprovision'] = dvc['autoprovision']
                if 'driverOpts' in dvc:
                    v_dict['config']['driverOpts'] = dvc['driverOpts']
                if 'labels' in dvc:
                    v_dict['config']['labels'] = dvc['labels']

    def __getattr__(self, attr):
        try:
            return self.__getattribute__(attr)
        except AttributeError:
            if attr in [
                'family',
                'networkMode',
                'taskRoleArn',
                'revision',
                'requiresCompatibilities',
                'executionRoleArn',
                'cpu',
                'memory'
            ]:
                if not getattr(self, "_" + attr) and self.__aws_task_definition and attr in self.__aws_task_definition:
                    setattr(self, "_" + attr, self.__aws_task_definition[attr])
                return getattr(self, "_" + attr)
            elif attr == 'volumes':
                if not self._volumes and self.__aws_task_definition and 'volumes' in self.__aws_task_definition:
                    self.__load_volumes_from_aws()
                return self._volumes
            else:
                raise AttributeError

    def __setattr__(self, attr, value):
        if attr in [
            'family',
            'networkMode',
            'taskRoleArn',
            'requiresCompatibilities',
            'executionRoleArn',
            'cpu',
            'memory'
        ]:
            setattr(self, "_" + attr, value)
        else:
            super(TaskDefinition, self).__setattr__(attr, value)

    def __get_task_definition(self, task_definition_id):
        if task_definition_id:
            try:
                response = self.ecs.describe_task_definition(
                    taskDefinition=task_definition_id
                )
            except ClientError:
                return {}
            else:
                return response['taskDefinition']
        else:
            return {}

    def __get_volumes(self):
        """
        Generate the "volumes" argument for the ``register_task_definition()`` call.

        :rtype: dict
        """
        volume_names = set()
        volumes = []

        # First get the volumes defined in the task definition portion of the yml. These look like:

        # volumes:
        #   - name: 'string'
        #     path: 'string'
        #     config:
        #       scope: 'task' | 'shared'
        #       autoprovision: true | false
        #       driver: 'string'
        #       driverOpts:
        #         'string': 'string'
        #       labels:
        #         'string': 'string'

        if self.volumes:
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

        # Now see if there are any old-style definitions.  Before we allowed the "volumes:" section in the task
        # definition yml, you could define volumes on individual containers and the "volumes" list in the
        # register_task_definition() AWS API call would be auto-constructed based on the host and container path.
        # So do that bit here.
        for c in self.containers:
            for v in c.volumes:
                host_path = v.split(':')[0]
                name = self.mount_from_host_path(host_path)
                if name not in volume_names:
                    volumes.append({
                        'name': name,
                        'host': {'sourcePath': host_path}
                    })
                    volume_names.add(name)
        return volumes

    def __render(self):
        """
        Build the argument list for the ``register_task_definition()`` call.

        :rtype: dict
        """
        r = {
            'family': self.family,
            'networkMode': self.networkMode
        }
        if self.cpu:
            r['cpu'] = str(self.cpu)
            r['memory'] = str(self.memory)
        r['requiresCompatibilities'] = self.requiresCompatibilities
        if self.taskRoleArn:
            r['taskRoleArn'] = self.taskRoleArn
        if self.executionRoleArn:
            r['executionRoleArn'] = self.executionRoleArn
        r['containerDefinitions'] = [c.render() for c in self.containers]
        volumes = self.__get_volumes()
        if volumes:
            r['volumes'] = volumes
        return r

    def render(self):
        return self.__render()

    def update_task_labels(self, family_revisions):
        self.containers[0].update_task_labels(family_revisions)

    def get_helper_tasks(self):
        return self.containers[0].get_helper_tasks()

    def create(self):
        kwargs = self.__render()
        response = self.ecs.register_task_definition(**kwargs)
        self.__defaults()
        self.from_aws(response['taskDefinition']['taskDefinitionArn'])

    def inject_environment(self, environment):
        for container in self.containers:
            container.inject_environment(environment)

    def from_yaml(self, yml):
        self.family = yml['family']
        if 'task_role_arn' in yml:
            self.taskRoleArn = yml['task_role_arn']
        if 'network_mode' in yml:
            self.networkMode = yml['network_mode']
        if 'cpu' in yml:
            self.cpu = yml['cpu']
        if 'memory' in yml:
            self.memory = yml['memory']
        if 'volumes' in yml:
            self.volumes = yml['volumes']
        self.containers = [ContainerDefinition(yml=c_yml) for c_yml in yml['containers']]
        if 'launch_type' in yml and yml['launch_type'] == 'FARGATE':
            self.executionRoleArn = yml['execution_role']
            self.requiresCompatibilities = ['FARGATE']
        else:
            self.executionRoleArn = yml.get('execution_role', None)

    def get_latest_revision(self):
        try:
            response = self.ecs.list_task_definitions(familyPrefix=self.family, sort='DESC', maxResults=1)
        except botocore.exceptions.ClientError:
            return None
        else:
            if 'taskDefinitionArns' in response and len(response['taskDefinitionArns']) > 0:
                return response['taskDefinitionArns'][0]
            else:
                return None

    def set_parameter_store(self, parameter_store):
        """
        Add parameter store values to the containers 'secrets' list. The task will fail if we try
        to do this and we don't have an execution role, so we don't pass the secrets if it doesn't
        have an execution role
        """
        if not self.executionRoleArn:
            return
        for container in self.containers:
            container.set_parameter_store(parameter_store)

    def __str__(self):
        return json.dumps(self.__render(), indent=2, sort_keys=True)


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
