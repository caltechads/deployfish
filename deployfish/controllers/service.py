import argparse
from datetime import datetime
import os
from typing import Type, Dict, cast

import botocore
from cement import ex
import click
from deployfish.controllers.network import ObjectDockerExecController, ObjectSSHController
from deployfish.controllers.secrets import ObjectSecretsController
from deployfish.controllers.tunnel import ObjectTunnelController
from deployfish.controllers.utils import handle_model_exceptions
from deployfish.core.loaders import ObjectLoader, ServiceLoader
from deployfish.ext.ext_df_argparse import DeployfishArgparseController as Controller

from deployfish.core.models import (
    Model,
    Service,
    StandaloneTask
)
from deployfish.core.waiters.hooks.ecs import ECSDeploymentStatusWaiterHook
from deployfish.renderers.table import TableRenderer

from .crud import CrudBase

def valid_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        msg = "not a valid date: {0!r}".format(s)
        raise argparse.ArgumentTypeError(msg)


class ECSService(CrudBase):

    class Meta:
        label = 'service'
        description = 'Work with ECS Service objects'
        help = 'Work with ECS Service objects'
        stacked_type = 'nested'

    model: Type[Model] = Service
    loader: Type[ObjectLoader] = ServiceLoader

    help_overrides: Dict[str, str] = {
        'info': 'Show details about an ECS Service object from AWS',
        'create': 'Create an ECS Service in AWS from what is in deployfish.yml',
        'update': 'Update an ECS Service in AWS from what is in deployfish.yml',
        'delete': 'Delete an ECS Service from AWS'
    }

    info_template: str = 'detail--service.jinja2'

    list_ordering: str = 'Service'
    list_result_columns: Dict[str, str] = {
        'Service': 'serviceName',
        'Cluster': 'cluster__name',
        'Version': 'version',
        'D': 'desiredCount',
        'R': 'runningCount',
        'P': 'pendingCount',
        'Updated': 'last_updated',
    }

    create_template: str = "detail--service--short.jinja2"
    update_template = delete_template = create_template

    # -------------------------
    # running_tasks()
    # -------------------------

    running_tasks_ordering: str = 'Instance'
    running_tasks_result_columns: Dict[str, str] = {
        'Instance': 'instanceName',
        'Instance ID': 'instanceId',
        'AZ': 'availabilityZone',
        'Family': 'taskDefinition__family_revision',
        'Launch Type': 'launchType',
        'created': 'createdAt'
    }

    def service_waiter(self, obj: Model, **kwargs) -> None:
        kwargs['WaiterHooks'] = [ECSDeploymentStatusWaiterHook(obj)]
        timeout_minutes = os.environ.get('DEPLOYFISH_SERVICE_UPDATE_TIMEOUT', 15)
        kwargs['WaiterConfig'] = {
            'Delay': 10,
            'MaxAttempts': timeout_minutes * 6
        }
        kwargs['services'] = [obj.name]
        kwargs['cluster'] = obj.data['cluster']
        self.wait('services_stable', **kwargs)

    create_waiter = service_waiter
    update_waiter = service_waiter

    @ex(
        help="Show about an existing ECS Service in AWS",
        arguments=[
            (['pk'], { 'help' : 'The primary key for the ECS Service'}),
            (
                ['--includes'],
                {
                    'help': 'Include optional information not normally shown.',
                    'action': 'store',
                    'default': None,
                    'choices': ['secrets', 'deployments'],
                    'dest': 'includes',
                    'nargs': "+"
                }
            ),
            (
                ['--excludes'],
                {
                    'help': 'Exclude optional information normally shown.',
                    'action': 'store',
                    'default': None,
                    'choices': ['events'],
                    'dest': 'excludes',
                    'nargs': "+"
                }
            )
        ],
    )
    @handle_model_exceptions
    def info(self):
        loader = self.loader(self)
        obj = loader.get_object_from_aws(self.app.pargs.pk)
        context = {
            'obj': obj,
            'includes': self.app.pargs.includes if self.app.pargs.includes else [],
            'excludes': self.app.pargs.excludes if self.app.pargs.excludes else [],
        }
        self.app.render(context, template=self.info_template)


    @ex(
        help="List ECS Services from AWS",
        arguments=[
            (
                ['--cluster-name'],
                {
                    'help': 'Filter by cluster name, with globs. Ex: "foo*", "*foo"',
                    'action': 'store',
                    'default': None,
                    'dest': 'cluster_name'
                }
            ),
            (
                ['--service-name'],
                {
                    'help': 'Filter by service name, with globs. Ex: "foo*", "*foo"',
                    'action': 'store',
                    'default': None,
                    'dest': 'service_name'
                }
            ),
            (
                ['--launch-type'],
                {
                    'help': 'Filter by launch type.',
                    'action': 'store',
                    'default': 'any',
                    'choices': ['any', 'EC2', 'FARGATE'],
                    'dest': 'launch_type'
                }
            ),
            (
                ['--scheduling-strategy'],
                {
                    'help': 'Filter by scheduling strategy',
                    'action': 'store',
                    'default': 'any',
                    'choices': ['any', 'REPLICA', 'DAEMON'],
                    'dest': 'scheduling_strategy'
                }
            ),
            (
                ['--updated-since'],
                {
                    'help': 'Filter by services updated since YYYY-MM-DD',
                    'action': 'store',
                    'default': None,
                    'dest': 'updated_since',
                    'type': valid_date
                }
            ),
        ]
    )
    @handle_model_exceptions
    def list(self):
        results = self.model.objects.list(
            cluster_name=self.app.pargs.cluster_name,
            service_name=self.app.pargs.service_name,
            launch_type=self.app.pargs.launch_type,
            scheduling_strategy=self.app.pargs.scheduling_strategy,
            updated_since=self.app.pargs.updated_since
        )
        self.render_list(results)

    def delete_waiter(self, obj: Model, **kwargs) -> None:
        kwargs['WaiterHooks'] = [ECSDeploymentStatusWaiterHook(obj)]
        kwargs['services'] = [obj.name]
        kwargs['cluster'] = obj.data['cluster']
        try:
            self.wait('services_inactive', **kwargs)
        except botocore.exceptions.WaiterError as e:
            if "DRAINING" not in str(e):
                # If we have tasks in "DRAINING" state, We have unstable containers -- perhaps the service is in
                # trouble.   In this case, we ignore the error because the containers will die soon
                raise

    def scale_services_waiter(self, obj: Service, **kwargs) -> None:
        """
        Show periodic updates while we change desired count for a service.
        """
        kwargs['WaiterHooks'] = [ECSDeploymentStatusWaiterHook(obj)]
        kwargs['services'] = [obj.name]
        kwargs['cluster'] = obj.data['cluster']
        self.wait('services_stable', **kwargs)

    @ex(
        help='Change the number of tasks for an ECS Service in AWS',
        arguments=[
            (['pk'], {'help': 'The primary key for the ECS Service'}),
            (
                ['count'],
                {
                    'help': 'Set the number of tasks for the service to this',
                    'type': int
                }
            ),
        ]
    )
    @handle_model_exceptions
    def scale(self):
        """
        Change desired count for a service.
        """
        loader = self.loader(self)
        obj = loader.get_object_from_aws(self.app.pargs.pk)
        obj = cast(Service, obj)
        count = self.app.pargs.count
        click.secho('Updating desiredCount to "{}" on Service(pk="{}")'.format(count, obj.pk))
        for _ in self.app.hook.run('pre_service_scale', self.app, obj, count):
            pass
        obj.scale(count)
        self.scale_services_waiter(obj)  # type: ignore
        self.app.print(
            click.style('\n\nScaled {}("{}") to {} tasks.'.format(self.model.__name__, obj.pk, count), fg='green')
        )
        for _ in self.app.hook.run('post_service_scale', self.app, obj, count):
            pass


    @ex(
        help='Restart the running tasks for a Service in AWS',
        arguments=[
            (['pk'], {'help': 'The primary key for the ECS Service'}),
            (
                ['--hard'],
                {
                    'help': 'Kill off all the tasks at once instead of iterating through them',
                    'default': False,
                    'action': 'store_true',
                    'dest': 'hard'
                }
            )
        ]
    )
    @handle_model_exceptions
    def restart(self):
        loader = self.loader(self)
        obj = loader.get_object_from_aws(self.app.pargs.pk)
        obj = cast(Service, obj)
        obj.restart(hard=self.app.pargs.hard, waiter_hooks=[ECSDeploymentStatusWaiterHook(obj)])
        return click.style('\n\nRestarted tasks for {}("{}").'.format(self.model.__name__, obj.pk), fg='green')

    @ex(
        help='List the running tasks for an ECS Service in AWS.',
        arguments=[
            (['pk'], {'help': 'The primary key for the ECS Service'}),
        ]
    )
    @handle_model_exceptions
    def running_tasks(self):
        loader = self.loader(self)
        obj = loader.get_object_from_aws(self.app.pargs.pk)
        results = obj.running_tasks
        renderer = TableRenderer(
            columns=self.running_tasks_result_columns,
            ordering=self.running_tasks_ordering
        )
        self.app.print(renderer.render(results))


class ECSServiceStandaloneTasks(Controller):

    class Meta:
        label = 'service-standalonetasks'
        stacked_on = "service"
        description = 'Work with StandaloneTasks related to ECS Service objects'
        help = 'Work with StandaloneTasks related to ECS Service objects'
        stacked_type = 'embedded'

    model: Type[Model] = Service
    loader: Type[ObjectLoader] = ServiceLoader


    @ex(
        help='List StandaloneTasks related to a Service from configuration in deployfish.yml',
        arguments=[
            (['pk'], {'help': 'The primary key for the ECS Service'}),
        ]
    )
    @handle_model_exceptions
    def list_related_tasks(self):
        """
        List StandaloneTasks related to a Service from what we have in our deployfish.yml file.

        NOTE: This lists tasks defined under the top level 'tasks:' section in
        deployfish.yml.  ServiceHelperTasks -- those defined by a 'tasks:'
        section under the Service definition will not be listed here.

        IDENTIFIER is a string that looks like one of:

            * Service.name

            * Service.environment
        """
        loader = self.loader(self)
        obj = loader.get_object_from_deployfish(
            self.app.pargs.pk,
            factory_kwargs={'load_secrets': False}
        )
        tasks = []
        config = self.app.deployfish_config.cooked
        if 'tasks' in config:
            for task_data in config['tasks']:
                if 'service' in task_data:
                    if (task_data['service'] == obj.pk or task_data['service'] == obj.name):
                        tasks.append(task_data['name'])
            tasks.sort()
        if tasks:
            for task in tasks:
                self.app.print(task)
        else:
            self.app.print('No related tasks.')

    @ex(
        help='Update a StandaloneTasks related to a Service from configuration in deployfish.yml',
        arguments=[
            (['pk'], {'help': 'The primary key for the ECS Service'}),
        ]
    )
    @handle_model_exceptions
    def update_related_tasks(self):
        """
        Update StandaloneTasks related to a Service from what we have in our
        deployfish.yml file.

        NOTE: This handles tasks defined under the top level 'tasks:' section in
        deployfish.yml.  ServiceHelperTasks -- those defined by a 'tasks:'
        section under the Service definition -- get updated automatically when
        the Service itself is updated.

        IDENTIFIER is a string that looks like one of:

            * Service.name

            * Service.environment

        """
        loader = self.loader(self)
        obj = loader.get_object_from_deployfish(
            self.app.pargs.pk,
            factory_kwargs={'load_secrets': False}
        )
        tasks = []
        config = self.app.deployfish_config.cooked
        if 'tasks' in config:
            for task_data in config['tasks']:
                if 'service' in task_data:
                    if (task_data['service'] == obj.pk or task_data['service'] == obj.name):
                        tasks.append(task_data['name'])
            tasks.sort()
        if tasks:
            self.app.print(click.style(f'\n\nUpdating StandaloneTasks related to Service("{obj.pk}"):\n', fg='yellow'))
            for task in tasks:
                task = loader.get_object_from_deployfish(task, model=StandaloneTask)
                arn = task.save()
                family_revision = arn.rsplit('/')[1]
                click.secho('  UPDATED: {} -> {}'.format(task.name, family_revision))
            click.secho('\nDone.', fg='yellow')
        else:
            self.app.print('No related tasks.')



class ECSServiceSecrets(ObjectSecretsController):

    class Meta:
        label = "config"
        description = "Manage AWS Parameter Store secrets for an ECS Service"
        help = "Manage AWS Parameter Store secrets for an ECS Service"
        stacked_on = "service"
        stacked_type = "nested"

    model: Type[Model] = Service
    loader: Type[ObjectLoader] = ServiceLoader

    help_overrides = {
        'diff': 'Diff AWS SSM Parameter Store secrets vs those in deployfish.yml for an ECS Service',
        'show': 'Show all AWS SSM Parameter Store secrets for an ECS Service as they exist in AWS',
        'write': 'Write AWS SSM Parameter Store secrets for an ECS Service to AWS',
        'export': 'Extract env.VAR variables from AWS SSM Parameter Store secrets for an ECS Service to AWS',
    }


class ECSServiceSSH(ObjectSSHController):

    class Meta:
        label = "service-ssh"
        description = "SSH to instances for an ECS Service"
        help = "SSH to instances for an ECS Service"
        stacked_on = "service"
        stacked_type = "embedded"

    model: Type[Model] = Service
    loader: Type[ObjectLoader] = ServiceLoader

    help_overrides = {
        'ssh': 'SSH to a container instance for an ECS Service',
        'run': 'Run shell commands on container instances for an ECS Service',
    }


class ECSServiceDockerExec(ObjectDockerExecController):

    class Meta:
        label = "service-exec"
        description = "Exec into containers for an ECS Service"
        help = "Exec into containers for an ECS Service"
        stacked_on = "service"
        stacked_type = "embedded"

    model: Type[Model] = Service
    loader: Type[ObjectLoader] = ServiceLoader

    help_overrides = {
        'exec': 'Exec into containers for an ECS Service',
    }


class ECSServiceTunnel(ObjectTunnelController):

    class Meta:
        label = "service-tunnel"
        description = "Establish an ssh tunnel"
        help = "Establish an ssh tunnel"
        stacked_on = "service"
        stacked_type = "embedded"

    model: Type[Model] = Service
    loader: Type[ObjectLoader] = ServiceLoader
