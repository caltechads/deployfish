#!/usr/bin/env python
from __future__ import print_function

from datetime import datetime
import json
from copy import copy
import os
import os.path
import random
import re
import shlex
import string
import subprocess
from tempfile import NamedTemporaryFile
import time
import tzlocal

import botocore

from deployfish.aws import get_boto3_session
from deployfish.aws.asg import ASG
from deployfish.aws.appscaling import ApplicationAutoscaling
from deployfish.aws.systems_manager import ParameterStore
from deployfish.aws.service_discovery import ServiceDiscovery


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

    def __init__(self, aws={}, yml={}):
        if aws:
            self.from_aws(aws)

        if yml:
            self.from_yaml(yml)

    def from_aws(self, aws):
        self.driver = aws['logDriver']
        self.options = aws['options']

    def from_yaml(self, yml):
        self.driver = yml['driver']
        self.options = yml['options']

    def render(self):
        return(self.__render())

    def __render(self):
        r = {}
        r['logDriver'] = self.driver
        r['options'] = self.options
        return r


class ContainerDefinition(VolumeMixin):
    """
    Manage one of the container definitions in a `TaskDefinition`.
    """

    def __init__(self, aws={}, yml={}):
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

        if 'logConfiguration' in aws:
            self.logConfiguration = LogConfiguration(aws['logConfiguration'])

        if yml:
            self.from_yaml(yml)

    def __getattr__(self, attr):
        try:
            return self.__getattribute__(attr)
        except AttributeError:
            if attr in ['cpu', 'dockerLabels', 'essential', 'image', 'links', 'memory', 'memoryReservation', 'name']:
                if (not getattr(self, '_' + attr) and self.__aws_container_definition and attr in self.__aws_container_definition):
                    setattr(self, "_" + attr, self.__aws_container_definition[attr])
                return getattr(self, '_' + attr)
            elif attr == 'environment':
                if (not self._environment and self.__aws_container_definition and 'environment' in self.__aws_container_definition):
                    environment = self.__aws_container_definition['environment']
                    for var in environment:
                        self._environment[var['name']] = var['value']
                return self._environment
            elif attr == 'portMappings':
                if (not self._portMappings and self.__aws_container_definition and 'portMappings' in self.__aws_container_definition):
                    ports = self.__aws_container_definition['portMappings']
                    for mapping in ports:
                        self._portMappings.append('{}:{}/{}'.format(mapping['hostPort'], mapping['containerPort'], mapping['protocol']))
                return self._portMappings
            elif attr == 'command':
                if (not self._command and self.__aws_container_definition and 'command' in self.__aws_container_definition):
                    self._command = ' '.join(self.__aws_container_definition['command'])
                return self._command
            elif attr == 'entryPoint':
                if (not self._entryPoint and self.__aws_container_definition and 'entryPoint' in self.__aws_container_definition):
                    self._entryPoint = ' '.join(self.__aws_container_definition['entryPoint'])
                return self._entryPoint
            elif attr == 'ulimits':
                if (not self._ulimits and self.__aws_container_definition and 'ulimits' in self.__aws_container_definition):
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
        if (not self._extraHosts and self.__aws_container_definition and 'extraHosts' in self.__aws_container_definition):
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
        r = {}
        r['name'] = self.name
        r['image'] = self.image
        r['cpu'] = self.cpu
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
                lc = {}
                lc['name'] = limit['name']
                lc['softLimit'] = limit['soft']
                lc['hardLimit'] = limit['hard']
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
                for l in yml['labels']:
                    key, value = l.split('=')
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
                tc_append = {}
                tc_append['containerPath'] = tc['container_path']
                tc_append['size'] = tc['size']
                if 'mount_options' in tc and type(tc['mount_options']) == list:
                    tc_append['mountOptions'] = tc['mount_options']
                self.tmpfs.append(tc_append)

    def __str__(self):
        """
        Pretty print what we would pass to `register_task_definition()` in the
        `containerDefinitions` argument.
        """
        return json.dumps(self.render(), indent=2, sort_keys=True)


class TaskDefinition(VolumeMixin):

    @staticmethod
    def url(task_def):
        """
        Return the AWS Web Console URL for task defintion ``task_def`` as
        Markdown.  Suitable for inserting into a Slack message.

        :param region: the name of a valid AWS region
        :type region: string

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

    def __init__(self, task_definition_id=None, yml={}):
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
                # v here looks like
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
        If this task defitinion exists in AWS, return our ARN.
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
        If this task defitinion exists in AWS, return our ``<family>:<revision>`` string.
        Else, return ``None``.

        :rtype: string or ``None``
        """
        if self.__aws_task_definition:
            return "{}:{}".format(self.family, self.revision)
        else:
            return None

    def __load_volumes_from_aws(self):
        for v in self.__aws_task_definition['volumes']:
            v_dict = {}
            v_dict['name'] = v['name']
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
        if attr in ['family', 'networkMode', 'taskRoleArn', 'requiresCompatibilities', 'executionRoleArn', 'cpu', 'memory']:
            setattr(self, "_" + attr, value)
        else:
            super(TaskDefinition, self).__setattr__(attr, value)

    def __get_task_definition(self, task_definition_id):
        if task_definition_id:
            try:
                response = self.ecs.describe_task_definition(
                    taskDefinition=task_definition_id
                )
            except botocore.exceptions.ClientError:
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
                v_dict = {}
                v_dict['name'] = v['name']
                if 'path' in v:
                    v_dict['host'] = {}
                    v_dict['host']['sourcePath'] = v['path']
                elif 'config' in v:
                    v_dict['dockerVolumeConfiguration'] = copy(v['config'])
                volumes.append(v_dict)
                volume_names.add(v_dict['name'])

        # Now see if there are any old-style definitions.  Before we allowed the "volumes:" section in the task
        # definition yml, you could define volumes on individual containers and the "volumes" list in the
        # register_task_definition() AWS API call would be autoconstructed based on the host and container path.  So do
        # that bit here.
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
        r = {}
        r['family'] = self.family
        r['networkMode'] = self.networkMode
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

    def __str__(self):
        return json.dumps(self.__render(), indent=2, sort_keys=True)


class Task(object):
    """
    This is a batch job that will be run via the ECS RunTask API call.  It runs
    for a short time and then dies.

    The reason this class exists is to enable us to run one-off or periodic
    functions (migrate datbases, clear caches, update search indexes, do
    database backups or restores, etc.) for our services.
    """

    def __init__(self, clusterName, yml={}):
        """
        :param clusterName: the name of the cluster in which we'll run our
                            helper tasks
        :type clusterName: string

        :param yml: the task definition information for the task from our
                    deployfish.yml file
        :type yml: dict
        """
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


class Service(object):
    """
    An object representing an ECS service.
    """

    @classmethod
    def url(cluster, service):
        """
        Return the AWS Web Console URL for service ``service`` in ECS cluster ``cluster``
        in region ``region`` as Markdown.  Suitable for inserting into a Slack message.

        :param region: the name of a valid AWS region
        :type region: string

        :param cluster: the name of an ECS cluster
        :type cluster: string

        :param service: the name of an ECS service in cluster ``cluster``
        :type service: string

        :rtype: string
        """
        region = os.environ.get('AWS_DEFAULT_REGION', 'us-west-2')
        return u"<https://{}.console.aws.amazon.com/ecs/home?region={}#/clusters/{}/services/{}/tasks|{}>".format(
            region,
            region,
            cluster,
            service,
            service
        )

    def __init__(self, service_name, config=None):
        yml = config.get_service(service_name)
        self.ecs = get_boto3_session().client('ecs')

        self.__aws_service = None

        self.asg = None
        self.scaling = None
        self.serviceDiscovery = None
        self.searched_hosts = False
        self.is_running = False
        self.hosts = None
        self.host_ips = None
        self._serviceName = None
        self._clusterName = None
        self._desired_count = 0
        self._minimumHealthyPercent = None
        self._maximumPercent = None
        self._launchType = 'EC2'
        self.__service_discovery = []
        self.__defaults()
        self.from_yaml(yml)
        self.from_aws()

    def __defaults(self):
        self._roleArn = None
        self.__load_balancer = {}
        self.__vpc_configuration = {}
        self.__placement_constraints = []
        self.__placement_strategy = []
        self.__schedulingStrategy = "REPLICA"

    def __get_service(self):
        """
        If a service named ``self.serviceName`` in a cluster named
        ``self.clusterName`` exists, return its data, else return an
        empty dict.

        :rtype: dict
        """
        response = self.ecs.describe_services(
            cluster=self._clusterName,
            services=[self._serviceName]
        )
        if response['services'] and response['services'][0]['status'] != 'INACTIVE':
            return response['services'][0]
        else:
            return {}

    def __getattr__(self, attr):
        """
        We have this __getattr__ here to access some attributes on the dict that AWS
        returns to us via the ``describe_services()`` call.
        """
        try:
            return self.__getattribute__(attr)
        except AttributeError:
            if attr in [
                'deployments',
                'taskDefinition',
                'clusterArn',
                'desiredCount',
                'runningCount',
                'pendingCount',
                'networkConfiguration',
                'executionRoleArn'
            ]:
                if self.__aws_service:
                    return self.__aws_service[attr]
                return None
            else:
                raise AttributeError

    def exists(self):
        """
        Return ``True`` if our service exists in the specified cluster in AWS,
        ``False`` otherwise.

        :rtype: boolean
        """
        if self.__aws_service:
            return True
        return False

    @property
    def count(self):
        """
        For services yet to be created, return the what we want the task count
        to be when we create the service.

        For services already existing in AWS, return the actual current number
        of running tasks.

        :rtype: int
        """
        if self.__aws_service:
            self._count = self.__aws_service['runningCount']
        return self._count

    @count.setter
    def count(self, count):
        """
        Set the count of tasks this service should run.  Setting this
        has no effect if the service already exists.  Use ``Service.scale()``
        to affect this instead.

        :param count: number of tasks this service should run
        :type count: int
        """
        self._count = count

    @property
    def maximumPercent(self):
        """
        If maximumPercent is defined in deployfish.yml for our service
        return that value.

        If it is not defined in deployfish.yml, but it is defined in AWS, return
        the AWS maximumPercent value.

        Else, return 200.

        :rtype: int
        """
        if not self._maximumPercent:
            if self.__aws_service:
                self._maximumPercent = self.__aws_service['deploymentConfiguration']['maximumPercent']
            else:
                # Give a reasonable default if it was not defined in deployfish.yml
                self._maximumPercent = 200
        return self._maximumPercent

    @maximumPercent.setter
    def maximumPercent(self, maximumPercent):
        """
        Set the maximum percent of tasks this service is allowed to be in the
        RUNNING or PENDING state during a deployment.  Setting this has no
        effect if the service already exists.

        :param maximumPercent: Set the maximum percent of tasks this service is allowed to run
        :type count: int
        """
        self._maximumPercent = maximumPercent

    @property
    def minimumHealthyPercent(self):
        """
        If minimumHealthyPercent is defined in deployfish.yml for our service,
        return that value.

        If it is not defined in deployfish.yml, but it is defined in AWS, return
        the AWS minimumHealthyPercent value.

        Else, return 0.

        :rtype: int
        """
        if not self._minimumHealthyPercent:
            if self.__aws_service:
                self._minimumHealthyPercent = self.__aws_service['deploymentConfiguration']['minimumHealthyPercent']
            else:
                # Give a reasonable default if it was not defined in deployfish.yml
                self._minimumHealthyPercent = 0
        return self._minimumHealthyPercent

    @minimumHealthyPercent.setter
    def minimumHealthyPercent(self, minimumHealthyPercent):
        """
        Set the minimum percent of tasks this service must maintain in the
        RUNNING or PENDING state during a deployment.  Setting this has no
        effect if the service already exists.

        :param maximumPercent: Set the minimum percent of tasks this service must maintain
        :type count: int
        """
        self._minimumHealthyPercent = minimumHealthyPercent

    @property
    def serviceName(self):
        """
        Return the name of our service.

        :rtype: string
        """
        if self.__aws_service:
            self._serviceName = self.__aws_service['serviceName']
        return self._serviceName

    @serviceName.setter
    def serviceName(self, serviceName):
        self._serviceName = serviceName

    @property
    def launchType(self):
        """
        Return the launch type of our service.

        :rtype: string
        """
        if self.__aws_service:
            self._launchType = self.__aws_service['launchType']
        return self._launchType

    @launchType.setter
    def launchType(self, launchType):
        self._launchType = launchType

    @property
    def clusterName(self):
        """
        Return the name of the cluster our service is or will be running in.

        :rtype: string
        """
        if self.__aws_service:
            self._clusterName = os.path.basename(self.__aws_service['clusterArn'])
        return self._clusterName

    @clusterName.setter
    def clusterName(self, clusterName):
        self._clusterName = clusterName

    @property
    def roleArn(self):
        if self.__aws_service:
            self._roleArn = self.__aws_service['roleArn']
        return self._roleArn

    @roleArn.setter
    def roleArn(self, roleArn):
        self._roleArn = roleArn

    @property
    def client_token(self):
        token = 'token-{}-{}'.format(self.serviceName, self.clusterName)
        if len(token) > 36:
            token = token[0:35]
        return token

    @property
    def active_deployment(self):
        for deployment in self.deployments:
            if deployment['taskDefinition'] == self.taskDefinition:
                break
        return deployment

    def kill_task(self, task_arn):
        """
        Kill off one of our tasks.  Do nothing if the task doesn't belong to
        this service.

        :param task_arn: the ARN of an existing task in our service
        :type task_arn: string
        """
        if task_arn in self.task_arns:
            self.ecs.stop_task(
                cluster=self.clusterName,
                task=task_arn
            )

    def restart(self, hard=False):
        """
        Kill off tasks in the our service one by one, letting them be
        replaced by tasks from the same task definition.  This effectively
        "restarts" the tasks.

        :param hard: if True, kill off all running tasks instantly
        :type hard: boolean
        """
        for task_arn in self.task_arns:
            self.kill_task(task_arn)
            if not hard:
                self.wait_until_stable()
        if hard:
            self.wait_until_stable()

    @property
    def task_arns(self):
        """
        Returns a list of taskArns for all tasks currently running in the service.

        :rtype: list ot strings
        """
        response = self.ecs.list_tasks(
            cluster=self.clusterName,
            serviceName=self.serviceName
        )
        return response['taskArns']

    @property
    def load_balancer(self):
        """
        Returns the load balancer, either elb or alb, if it exists.

        :return: dict
        """
        if self.__aws_service:
            if self.__aws_service['loadBalancers']:
                if 'loadBalancerName' in self.__aws_service['loadBalancers'][0]:
                    self.__load_balancer = {
                        'type': 'elb',
                        'load_balancer_name': self.__aws_service['loadBalancers'][0]['loadBalancerName'],
                    }
                else:
                    self.__load_balancer = {
                        'type': 'alb',
                        'target_group_arn': self.__aws_service['loadBalancers'][0]['targetGroupArn'],
                    }
                self.__load_balancer['container_name'] = self.__aws_service['loadBalancers'][0]['containerName']
                self.__load_balancer['container_port'] = self.__aws_service['loadBalancers'][0]['containerPort']
        return self.__load_balancer

    def set_elb(self, load_balancer_name, container_name, container_port):
        self.__load_balancer = {
            'type': 'elb',
            'load_balancer_name': load_balancer_name,
            'container_name': container_name,
            'container_port': container_port
        }

    def set_alb(self, target_group_arn, container_name, container_port):
        self.__load_balancer = {
            'type': 'alb',
            'target_group_arn': target_group_arn,
            'container_name': container_name,
            'container_port': container_port
        }

    @property
    def vpc_configuration(self):
        if self.__aws_service and self.__aws_service['networkConfiguration'] and not self.__vpc_configuration:
            self.__vpc_configuration = self.__aws_service['networkConfiguration']['awsvpcConfiguration']
        return self.__vpc_configuration

    def set_vpc_configuration(self, subnets, security_groups, public_ip):
        self.__vpc_configuration = {
            'subnets': subnets,
            'securityGroups': security_groups,
            'assignPublicIp': public_ip
        }

    @property
    def service_discovery(self):
        if self.__aws_service:
            if self.__aws_service['serviceRegistries']:
                if 'registryArn' in self.__aws_service['serviceRegistries'][0]:
                    self.__service_discovery = self.__aws_service['serviceRegistries']
        return self.__service_discovery

    @service_discovery.setter
    def service_discovery(self, arn):
        self.__service_discovery = [{'registryArn': arn}]

    def version(self):
        if self.active_task_definition:
            if self.load_balancer:
                for c in self.active_task_definition.containers:
                    if c.name == self.load_balancer['container_name']:
                        return c.image.split(":")[1]
            else:
                # Just give the first container's version?
                return self.active_task_definition.containers[0].image.split(":")[1]
        return None

    @property
    def placementConstraints(self):
        if self.__aws_service:
            if self.__aws_service['placementConstraints']:
                self.__placement_constraints = self.__aws_service['placementConstraints']
        return self.__placement_constraints

    @placementConstraints.setter
    def placementConstraints(self, placementConstraints):
        if isinstance(placementConstraints, list):
            self.__placement_constraints = []
            for placement in placementConstraints:
                configDict = {'type': placement['type']}
                if 'expression' in placement:
                    configDict['expression'] = placement['expression']
                self.__placement_constraints.append(configDict)

    @property
    def placementStrategy(self):
        if self.__aws_service:
            if self.__aws_service['placementStrategy']:
                self.__placement_strategy = self.__aws_service['placementStrategy']
        return self.__placement_strategy

    @placementStrategy.setter
    def placementStrategy(self, placementStrategy):
        if isinstance(placementStrategy, list):
            self.__placement_strategy = []
            for placement in placementStrategy:
                configDict = {'type': placement['type']}
                if 'field' in placement:
                    configDict['field'] = placement['field']
                self.__placement_strategy.append(configDict)

    @property
    def schedulingStrategy(self):
        if self.__aws_service:
            if self.__aws_service['schedulingStrategy']:
                self.__schedulingStrategy = self.__aws_service['schedulingStrategy']
        return self.__schedulingStrategy

    @schedulingStrategy.setter
    def schedulingStrategy(self, schedulingStrategy):
        self.__schedulingStrategy = schedulingStrategy

    def __render(self, task_definition_id):
        """
        Generate the dict we will pass to boto3's `create_service()`.

        :rtype: dict
        """
        r = {}
        r['cluster'] = self.clusterName
        r['serviceName'] = self.serviceName
        r['launchType'] = self.launchType
        if self.load_balancer:
            if self.launchType != 'FARGATE':
                r['role'] = self.roleArn
            r['loadBalancers'] = []
            if self.load_balancer['type'] == 'elb':
                r['loadBalancers'].append({
                    'loadBalancerName': self.load_balancer['load_balancer_name'],
                    'containerName': self.load_balancer['container_name'],
                    'containerPort': self.load_balancer['container_port'],
                })
            else:
                r['loadBalancers'].append({
                    'targetGroupArn': self.load_balancer['target_group_arn'],
                    'containerName': self.load_balancer['container_name'],
                    'containerPort': self.load_balancer['container_port'],
                })
        if self.launchType == 'FARGATE':
            r['networkConfiguration'] = {
                'awsvpcConfiguration': self.vpc_configuration
            }
        r['taskDefinition'] = task_definition_id
        if self.schedulingStrategy != "DAEMON":
            r['desiredCount'] = self.count
        r['clientToken'] = self.client_token
        if self.__service_discovery:
            r['serviceRegistries'] = self.__service_discovery
        r['deploymentConfiguration'] = {
            'maximumPercent': self.maximumPercent,
            'minimumHealthyPercent': self.minimumHealthyPercent
        }
        if len(self.placementConstraints) > 0:
            r['placementConstraints'] = self.placementConstraints
        if len(self.placementStrategy) > 0:
            r['placementStrategy'] = self.placementStrategy
        if self.schedulingStrategy:
            r['schedulingStrategy'] = self.schedulingStrategy
        return r

    def from_yaml(self, yml):
        """
        Load our service information from the parsed yaml.  ``yml`` should be
        a service level entry from the ``deployfish.yml`` file.

        :param yml: a service level entry from the ``deployfish.yml`` file
        :type yml: dict
        """
        self.serviceName = yml['name']
        self.clusterName = yml['cluster']
        if 'launch_type' in yml:
            self.launchType = yml['launch_type']
        self.environment = yml.get('environment', 'undefined')
        self.family = yml['family']
        # backwards compatibility for deployfish.yml < 0.16.0
        if 'maximum_percent' in yml:
            self.maximumPercent = yml['maximum_percent']
            self.minimumHealthyPercent = yml['minimum_healthy_percent']
        self.asg = ASG(yml=yml)
        if 'application_scaling' in yml:
            self.scaling = ApplicationAutoscaling(yml['name'], yml['cluster'], yml=yml['application_scaling'])
        if 'load_balancer' in yml:
            if 'service_role_arn' in yml:
                # backwards compatibility for deployfish.yml < 0.3.6
                self.roleArn = yml['service_role_arn']
            else:
                self.roleArn = yml['load_balancer']['service_role_arn']
            if 'load_balancer_name' in yml['load_balancer']:
                self.set_elb(
                    yml['load_balancer']['load_balancer_name'],
                    yml['load_balancer']['container_name'],
                    yml['load_balancer']['container_port'],
                )
            elif 'target_group_arn' in yml['load_balancer']:
                self.set_alb(
                    yml['load_balancer']['target_group_arn'],
                    yml['load_balancer']['container_name'],
                    yml['load_balancer']['container_port'],
                )
        if 'vpc_configuration' in yml:
            self.set_vpc_configuration(
                yml['vpc_configuration']['subnets'],
                yml['vpc_configuration']['security_groups'],
                yml['vpc_configuration']['public_ip'],
            )
        if 'network_mode' in yml:
            if yml['network_mode'] == 'awsvpc' and 'service_discovery' in yml:
                self.serviceDiscovery = ServiceDiscovery(None, yml=yml['service_discovery'])
            elif 'service_discovery' in yml:
                print("Ignoring service discovery config since network mode is not awsvpc")
        if 'placement_constraints' in yml:
            self.placementConstraints = yml['placement_constraints']
        if 'placement_strategy' in yml:
            self.placementStrategy = yml['placement_strategy']
        if 'scheduling_strategy' in yml and yml['scheduling_strategy'] == 'DAEMON':
            self.schedulingStrategy = yml['scheduling_strategy']
            self._count = 'automatically'
            self.maximumPercent = 100
        else:
            self._count = yml['count']
            self._desired_count = self._count
        self.desired_task_definition = TaskDefinition(yml=yml)
        deployfish_environment = {
            "DEPLOYFISH_SERVICE_NAME": yml['name'],
            "DEPLOYFISH_ENVIRONMENT": yml.get('environment', 'undefined'),
            "DEPLOYFISH_CLUSTER_NAME": yml['cluster']
        }
        self.desired_task_definition.inject_environment(deployfish_environment)
        self.tasks = {}
        if 'tasks' in yml:
            for task in yml['tasks']:
                t = Task(yml['cluster'], yml=task)
                self.tasks[t.family] = t
        parameters = []
        if 'config' in yml:
            parameters = yml['config']
        self.parameter_store = ParameterStore(self._serviceName, self._clusterName, yml=parameters)

    def from_aws(self):
        """
        Update our service definition, task definition and tasks from the live
        versions in AWS.
        """
        self.__aws_service = self.__get_service()
        if not self.scaling:
            # This only gets executed if we don't have an "application_scaling"
            # section in our service YAML definition.
            #
            # But we're looking here for an autoscaling setup that we previously
            # had created but which we no longer want
            self.scaling = ApplicationAutoscaling(self.serviceName, self.clusterName)
            if not self.scaling.exists():
                self.scaling = None
        if self.__aws_service:
            self.active_task_definition = TaskDefinition(self.taskDefinition)
            # If we have helper tasks, update them from AWS now
            helpers = self.active_task_definition.get_helper_tasks()
            if helpers:
                for t in self.tasks.values():
                    t.from_aws(helpers[t.family])

            if self.__aws_service['serviceRegistries']:
                self.serviceDiscovery = ServiceDiscovery(self.service_discovery[0]['registryArn'])
            else:
                self.serviceDiscovery = None
        else:
            self.active_task_definition = None

    def __create_tasks_and_task_definition(self):
        """
        Create the new task definition for our service.

        If we have any helper tasks associated with our service, create
        them first, then and pass their information into the service
        task definition.
        """
        family_revisions = []
        for task in self.tasks.values():
            task.create()
            family_revisions.append(task.family_revision)
        self.desired_task_definition.update_task_labels(family_revisions)
        self.desired_task_definition.create()

    def create(self):
        """
        Create the service in AWS.  If necessary, setup Application Scaling afterwards.
        """
        if self.serviceDiscovery is not None:
            if not self.serviceDiscovery.exists():
                self.service_discovery = self.serviceDiscovery.create()
            else:
                print("Service Discovery already exists with this name")
        self.__create_tasks_and_task_definition()
        kwargs = self.__render(self.desired_task_definition.arn)
        self.ecs.create_service(**kwargs)
        if self.scaling:
            self.scaling.create()
        self.__defaults()
        self.from_aws()

    def update(self):
        """
        Update the service and Application Scaling setup (if any).

        If we currently don't have Application Scaling enabled, but we want it now,
        set it up appropriately.

        If we currently do have Application Scaling enabled, but it's setup differently
        than we want it, update it appropriately.

        If we currently do have Application Scaling enabled, but we no longer want it,
        remove Application Scaling.
        """
        self.update_service()
        self.update_scaling()

    def update_service(self):
        """
        Update the taskDefinition and deploymentConfiguration on the service.
        """
        self.__create_tasks_and_task_definition()
        self.ecs.update_service(
            cluster=self.clusterName,
            service=self.serviceName,
            taskDefinition=self.desired_task_definition.arn,
            deploymentConfiguration={
                'maximumPercent': self.maximumPercent,
                'minimumHealthyPercent': self.minimumHealthyPercent
            }
        )
        self.__defaults()
        self.from_aws()

    def update_scaling(self):
        if self.scaling:
            if self.scaling.should_exist():
                if not self.scaling.exists():
                    self.scaling.create()
                else:
                    self.scaling.update()
            else:
                if self.scaling.exists():
                    self.scaling.delete()

    def scale(self, count):
        """
        Update ``desiredCount`` on our service to ``count``.

        :param count: set # of containers on our service to this
        :type count: integer
        """
        self.ecs.update_service(
            cluster=self.clusterName,
            service=self.serviceName,
            desiredCount=count
        )
        self._desired_count = count
        self.__defaults()
        self.from_aws()

    def delete(self):
        """
        Delete the service from AWS, as well as any related Application Scaling
        objects or service discovery objects.
        """

        # We need to delete any autoscaling stuff before deleting the service
        # because we want to delete the cloudwatch alarms associated with our
        # scaling policies.  If we delete the service first, ECS will happily
        # auto-delete the scaling target and scaling polices, but leave the
        # cloudwatch alarms hanging.  Then when we go to remove the scaling,
        # we won't know how to lookup the alarms
        if self.scaling and self.scaling.exists():
            self.scaling.delete()
        if self.serviceDiscovery:
            self.serviceDiscovery.delete()
        if self.exists():
            self.ecs.delete_service(
                cluster=self.clusterName,
                service=self.serviceName,
            )

    def _show_current_status(self):
        response = self.__get_service()
        # print response
        status = response['status']
        events = response['events']
        desired_count = response['desiredCount']
        if status == 'ACTIVE':
            success = True
        else:
            success = False

        deployments = response['deployments']
        if len(deployments) > 1:
            success = False

        print("Deployment Desired Pending Running")
        for deploy in deployments:
            if deploy['desiredCount'] != deploy['runningCount']:
                success = False
            print(deploy['status'], deploy['desiredCount'], deploy['pendingCount'], deploy['runningCount'])

        print("")

        print("Service:")
        for index, event in enumerate(events):
            if index <= 5:
                print(event['message'])

        if self.load_balancer and 'type' in self.load_balancer:
            lbtype = self.load_balancer['type']
        else:
            lbtype = None
        if lbtype == 'elb':
            print("")
            print("Load Balancer")
            elb = get_boto3_session().client('elb')
            response = elb.describe_instance_health(LoadBalancerName=self.load_balancer['load_balancer_name'])
            states = response['InstanceStates']
            if len(states) < desired_count:
                success = False
            for state in states:
                if state['State'] != "InService" or state['Description'] != "N/A":
                    success = False
                print(state['InstanceId'], state['State'], state['Description'])
        elif lbtype == 'alb':
            print("")
            print("Load Balancer")
            alb = get_boto3_session().client('elbv2')
            response = alb.describe_target_health(
                TargetGroupArn=self.load_balancer['target_group_arn']
            )
            if len(response['TargetHealthDescriptions']) < desired_count:
                success = False
            for desc in response['TargetHealthDescriptions']:
                if desc['TargetHealth']['State'] != 'healthy':
                    success = False
                print(desc['Target']['Id'], desc['TargetHealth']['State'], desc['TargetHealth'].get('Description', ''))
        return success

    def wait_until_stable(self):
        """
        Wait until AWS reports the service as "stable".
        """
        tz = tzlocal.get_localzone()
        self.its_run_start_time = datetime.now(tz)

        for i in range(40):
            time.sleep(15)
            success = self._show_current_status()
            if success:
                print("\nDeployment successful.\n")
                return True
            else:
                print("\nDeployment unready\n")

        print('Deployment failed...')

        # waiter = self.ecs.get_waiter('services_stable')
        # waiter.wait(cluster=self.clusterName, services=[self.serviceName])
        return False

    def run_task(self, command):
        """
        Runs the service tasks.

        :param command: Docker command to run.
        :return: ``None``
        """
        for task in self.tasks.values():
            if command in task.commands:
                return task.run(command)
        return None

    def get_config(self):
        """
        Return the ``ParameterStore()`` for our service.

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

    def _get_cluster_hosts(self):
        """
        For our service, return a mapping of ``containerInstanceArn`` to EC2
        ``instance_id`` for all container instances in our cluster.

        :rtype: dict
        """
        hosts = {}
        response = self.ecs.list_container_instances(cluster=self.clusterName)
        response = self.ecs.describe_container_instances(
            cluster=self.clusterName,
            containerInstances=response['containerInstanceArns']
        )
        instances = response['containerInstances']
        for i in instances:
            hosts[i['containerInstanceArn']] = i['ec2InstanceId']
        return hosts

    def _get_running_host(self, hosts=None):
        """
        Return the EC2 instance id for a host in our cluster which is
        running one of our service's tasks.

        :param hosts: (optional) A dict of ``containerInstanceArn`` -> EC2 ``instance_id``
        :type hosts: dict

        :rtype: string
        """
        if not hosts:
            hosts = self._get_cluster_hosts()

        instanceArns = []
        response = self.ecs.list_tasks(cluster=self.clusterName,
                                       family=self.family,
                                       desiredStatus='RUNNING')
        if response['taskArns']:
            response = self.ecs.describe_tasks(cluster=self.clusterName,
                                               tasks=response['taskArns'])
            if response['tasks']:
                task = response['tasks'][0]
                instanceArns.append(task['containerInstanceArn'])

        if instanceArns:
            for instance in instanceArns:
                if instance in hosts:
                    host = hosts[instance]
                    return host
        else:
            return None

    def get_instance_data(self):
        """
        Returns data on the instances in the ECS cluster.

        :return: list
        """
        self._search_hosts()
        instances = self.hosts.values()
        ec2 = get_boto3_session().client('ec2')
        response = ec2.describe_instances(InstanceIds=list(instances))
        if response['Reservations']:
            instances = response['Reservations']
            return instances
        return []

    def get_host_ips(self):
        """
        Returns the IP addresses of the ECS cluster instances.

        :return: list
        """
        if self.host_ips:
            return self.host_ips

        instances = self.get_instance_data()
        self.host_ips = []
        for reservation in instances:
            instance = reservation['Instances'][0]
            self.host_ips.append(instance['PrivateIpAddress'])
        return self.host_ips

    def cluster_run(self, cmd):
        """
        Run a command on each of the ECS cluster machines.

        :param cmd: Linux command to run.

        :return: list of tuples
        """
        ips = self.get_host_ips()
        host_ip = self.host_ip
        responses = []
        for ip in ips:
            self.host_ip = ip
            success, output = self.run_remote_script(cmd)
            responses.append((success, output))
        self.host_ip = host_ip
        return responses

    def cluster_ssh(self, ip):
        """
        SSH into the specified ECS cluster instance.

        :param ip: ECS cluster instance IP address

        :return: ``None``
        """
        self.host_ip = ip
        self.ssh()

    def _get_host_bastion(self, instance_id):
        """
        Given an EC2 ``instance_id`` return the private IP address of
        the instance identified by ``instance_id`` and the public
        DNS name of the bastion host you would use to reach it via ssh.

        :param instance_id: an EC2 instance id
        :type instance_id: string

        :rtype: 2-tuple (instance_private_ip_address, bastion_host_dns_name)
        """
        ip = None
        vpc_id = None
        bastion = ''
        ec2 = get_boto3_session().client('ec2')
        response = ec2.describe_instances(InstanceIds=[instance_id])
        if response['Reservations']:
            instances = response['Reservations'][0]['Instances']
            if instances:
                instance = instances[0]
                vpc_id = instance['VpcId']
                ip = instance['PrivateIpAddress']
        if ip and vpc_id:
            response = ec2.describe_instances(
                Filters=[
                    {
                        'Name': 'tag:Name',
                        'Values': ['bastion*']
                    },
                    {
                        'Name': 'vpc-id',
                        'Values': [vpc_id]
                    }
                ]
            )
            if response['Reservations']:
                instances = response['Reservations'][0]['Instances']
                if instances:
                    instance = instances[0]
                    bastion = instance['PublicDnsName']
        return ip, bastion

    def __is_or_has_file(self, data):
        '''
        Figure out if we have been given a file-like object as one of the inputs to the function that called this.
        Is a bit clunky because 'file' doesn't exist as a bare-word type check in Python 3 and built in file objects
        are not instances of io.<anything> in Python 2

        https://stackoverflow.com/questions/1661262/check-if-object-is-file-like-in-python
        Returns:
            Boolean - True if we have a file-like object
        '''
        if (hasattr(data, 'file')):
            data = data.file

        try:
            return isinstance(data, file)
        except NameError:
            from io import IOBase
            return isinstance(data, IOBase)

    def push_remote_text_file(self, input_data=None, run=False, file_output=False):
        """
        Push a text file to the current remote ECS cluster instance and optionally run it.

        :param input_data: Input data to send. Either string or file.
        :param run: Boolean that indicates if the text file should be run.
        :param file_output: Boolean that indicates if the output should be saved.
        :return: tuple - success, output
        """
        if self.__is_or_has_file(input_data):
            path, name = os.path.split(input_data.name)
        else:
            name = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))

        if run:
            cmd = '"cat \> {}\;bash {}\;rm {}"'.format(name, name, name)
        else:
            cmd = '"cat \> {}"'.format(name)

        with_output = True
        if file_output:
            with_output = NamedTemporaryFile(delete=False)
            output_filename = with_output.name

        success, output = self.ssh(command=cmd, with_output=with_output, input_data=input_data)
        if file_output:
            output = output_filename
        return success, output

    def run_remote_script(self, lines, file_output=False):
        """
        Run a script on the current remote ECS cluster instance.

        :param lines: list of lines of the script.
        :param file_output: Boolean that indicates if the output should be saved.
        :return: tuple - success, output
        """
        data = '\n'.join(lines)
        return self.push_remote_text_file(input_data=data, run=True, file_output=file_output)

    def _run_command_with_io(self, cmd, output_file=None, input_data=None):
        success = True

        if output_file:
            stdout = output_file
        else:
            stdout = subprocess.PIPE

        if input_data:
            if self.__is_or_has_file(input_data):
                stdin = input_data
                input_string = None
            else:
                stdin = subprocess.PIPE
                input_string = input_data
        else:
            stdin = None

        try:
            p = subprocess.Popen(cmd, stdout=stdout, stdin=stdin, shell=True, universal_newlines=True)
            output, errors = p.communicate(input_string)
        except subprocess.CalledProcessError as err:
            success = False
            output = "{}\n{}".format(err.cmd, err.output)
            output = err.output

        return success, output

    def _search_hosts(self):
        if self.searched_hosts:
            return

        self.searched_hosts = True

        hosts = self._get_cluster_hosts()
        running_host = self._get_running_host(hosts)

        if running_host:
            self.is_running = True

        if running_host:
            host = running_host
        else:
            # just grab one
            for k, host in hosts.items():
                break

        self.hosts = hosts
        self.host_ip, self.bastion = self._get_host_bastion(host)

    def ssh(self, command=None, is_running=False, with_output=False, input_data=None, verbose=False):
        """
        :param is_running: only complete the ssh if a task from our service is
                           actually running in the cluster
        :type is_running: boolean
        """
        self._search_hosts()

        if is_running and not self.is_running:
            return

        if self.host_ip and self.bastion:
            if verbose:
                verbose_flag = "-vv"
            else:
                verbose_flag = "-q"
            cmd = 'ssh {} -o StrictHostKeyChecking=no -A -t ec2-user@{} ssh {} -o StrictHostKeyChecking=no -A -t {}'.format(verbose_flag, self.bastion, verbose_flag, self.host_ip)
            if command:
                cmd = "{} {}".format(cmd, command)

            if with_output:
                if self.__is_or_has_file(with_output):
                    output_file = with_output
                else:
                    output_file = None
                return self._run_command_with_io(cmd, output_file=output_file, input_data=input_data)

            subprocess.call(cmd, shell=True)

    def docker_exec(self, verbose=False):
        """
        Exec into a running Docker container.
        """
        command = "\"/usr/bin/docker exec -it '\$(/usr/bin/docker ps --filter \"name=ecs-{}*\" -q)' bash\""
        command = command.format(self.family)
        self.ssh(command, is_running=True, verbose=verbose)

    def tunnel(self, host, local_port, interim_port, host_port):
        """
        Open tunnel to remote system.
        :param host:
        :param local_port:
        :param interim_port:
        :param host_port:
        :return:
        """
        hosts = self._get_cluster_hosts()
        ecs_host = hosts[list(hosts.keys())[0]]
        host_ip, bastion = self._get_host_bastion(ecs_host)

        cmd = 'ssh -L {}:localhost:{} ec2-user@{} ssh -L {}:{}:{}  {}'.format(local_port, interim_port, bastion, interim_port, host, host_port, host_ip)
        subprocess.call(cmd, shell=True)

    def __str__(self):
        return json.dumps(self.__render("to-be-created"), indent=2, sort_keys=True)
