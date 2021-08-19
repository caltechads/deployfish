import click

from deployfish.cli.adapters.utils import handle_model_exceptions, print_render_exception
from deployfish.config import get_config
from deployfish.core.models import Cluster, AutoscalingGroup, CloudWatchLogGroup, StandaloneTask
from deployfish.core.waiters.hooks import ECSDeploymentStatusWaiterHook, ECSTaskStatusHook
from deployfish.exceptions import RenderException, ConfigProcessingFailed
from deployfish.typing import FunctionTypeCommentParser

from deployfish.cli.renderers import (
    TableRenderer,
    JSONRenderer,
    TemplateRenderer
)

from .crud import ClickUpdateObjectCommandMixin


class HelperTaskCommandMixin(object):

    def get_task(self, service_pk, task_name):
        obj = self.get_object_from_aws(service_pk)
        task = None
        for t in obj.helper_tasks:
            if t.command == task_name:
                task = t
                break
        if not task:
            lines = []
            lines.append(
                click.style(
                    'No ServiceHelperTask with name "{}" exists on Service("{}").\n'.format(task_name, service_pk),
                    fg='red'
                )
            )
            lines.append(click.style('Available helper tasks:\n', fg='cyan'))
            lines.append(
                TableRenderer({
                    'Service': 'serviceName',
                    'Name': 'name',
                    'Revision': 'family_revision',
                    'Version': 'version',
                    'Launch Type': 'launchType',
                    'Schedule': 'schedule_expression'
                }, ordering='Name').render(obj.helper_tasks)
            )
            raise RenderException('\n'.join(lines))
        return task


# ====================
# Command mixins
# ====================

# Cluster/Service
# ---------------

class ClickListRunningTasksCommandMixin(object):

    list_running_tasks_ordering = None
    list_running_tasks_result_columns = {}
    list_running_tasks_renderer_classes = {
        'table': TableRenderer,
        'detail': TemplateRenderer,
        'json': JSONRenderer
    }

    @classmethod
    def list_running_tasks_display_option_kwargs(cls):
        """
        Return the appropriate kwargs for `click.option('--display', **kwargs)` for the renderer options we've defined
        for the list endpoint.

        :rtype: dict
        """
        render_types = list(cls.list_running_tasks_renderer_classes.keys())
        default = render_types[0]
        kwargs = {
            'type': click.Choice(render_types),
            'default': default,
            'help': "Render method for listing {} objects. Choices: {}.  Default: {}.".format(
                cls.model.__name__,
                ', '.join(render_types),
                default
            )
        }
        return kwargs

    @classmethod
    def add_list_running_tasks_click_command(cls, command_group):
        """
        Build a fully specified click command for listing running tasks for an ECS service or cluster, and add it to the
        click command group `command_group`.  Return the properly wrapped function object.

        :param command_group function: the click command group function to use to register our click command

        :rtype: function
        """
        def list_running_tasks(ctx, *args, **kwargs):
            if cls.model.config_section is not None:
                try:
                    ctx.obj['config'] = get_config(**ctx.obj)
                except ConfigProcessingFailed as e:
                    ctx.obj['config'] = e
            ctx.obj['adapter'] = cls()
            click.secho(ctx.obj['adapter'].list_running_tasks(kwargs['identifier'], kwargs['display']))

        pk_description = cls.get_pk_description()
        list_running_tasks.__doc__ = """
List the running tasks associated with a {object_name} in AWS.

{pk_description}
""".format(
            pk_description=pk_description,
            object_name=cls.model.__name__
        )

        function = print_render_exception(list_running_tasks)
        function = click.pass_context(function)
        function = click.option('--display', **cls.list_running_tasks_display_option_kwargs())(function)
        function = click.argument('identifier')(function)
        function = command_group.command(
            'running-tasks',
            short_help='List the running tasks for a {object_name} in AWS.'.format(
                object_name=cls.model.__name__
            )
        )(function)
        return function

    @handle_model_exceptions
    def list_running_tasks(self, identifier, display):
        assert display in self.list_running_tasks_renderer_classes, \
            'list running tasks: "{}" is not a valid rendering option'.format(
                display
            )
        obj = self.get_object_from_aws(identifier)
        results = obj.running_tasks
        if not results:
            return('No results.')
        else:
            if display == 'table':
                results = self.list_running_tasks_renderer_classes[display](
                    self.list_running_tasks_result_columns,
                    ordering=self.list_running_tasks_ordering
                ).render(results)
            else:
                results = self.list_running_tasks_renderer_classes[display]().render(results)
            results = '\n' + results + '\n'
            return results


# Service
# ---------

class ClickScaleInstancesCommandMixin(object):

    @classmethod
    def add_scale_instances_click_command(cls, command_group):
        """
        Build a fully specified click command for scaling ECS clusters or autoscaling groups, and add it to the click
        command group `command_group`.  Return the properly wrapped function object.

        :param command_group function: the click command group function to use to register our click command

        :rtype: function
        """
        def scale_instances(ctx, *args, **kwargs):
            if cls.model.config_section is not None:
                try:
                    ctx.obj['config'] = get_config(**ctx.obj)
                except ConfigProcessingFailed as e:
                    ctx.obj['config'] = e
            ctx.obj['adapter'] = cls()
            click.secho(ctx.obj['adapter'].scale_instances(
                kwargs['identifier'],
                kwargs['count'],
                kwargs['force']
            ))

        pk_description = cls.get_pk_description()
        scale_instances.__doc__ = """
Change the number of instances for an ECS cluster in AWS.

We'll try to detect the name of the autoscaling group by one of two methods:

  * Look for a tag on the cluster named "deployfish:autoscalingGroup"

  * Look for the tag named "aws:autoscalingGroup" on one of the running container instances

{pk_description}

COUNT is an integer.
""".format(pk_description=pk_description)

        function = print_render_exception(scale_instances)
        function = click.pass_context(function)
        function = click.option(
            '--force/--no-force',
            default=False,
            help='Force the Cluster to scale outside its MinCount or MaxCount'.format(
                object_name=cls.model.__name__
            )
        )(function)
        function = click.argument('count', type=int)(function)
        function = click.argument('identifier')(function)
        function = command_group.command(
            'scale',
            short_help='Change the number of instances for a Cluster in AWS.'.format(
                object_name=cls.model.__name__
            )
        )(function)
        return function

    def _scale_instances(self, obj, count, force):
        try:
            obj.scale(count, force=force)
        except Cluster.ImproperlyConfigured as e:
            # We don't have an autoscaling group
            raise RenderException(str(e))
        except AutoscalingGroup.OperationFailed as e:
            msg = str(e)
            if 'MinSize' in msg:
                lines = []
                lines.append(
                    'Desired count {} is less than MinSize of {} on AutoscalingGroup "{}".'.format(
                        count,
                        obj.autoscaling_group.data['MinSize'],
                        obj.autoscaling_group.name
                    )
                )
                lines.append('\nEither:')
                lines.append('  (1) use --force to also reduce AutoscalingGroup MinSize to {}'.format(count))
                lines.append('  (2) specify count >= {}'.format(obj.autoscaling_group.data['MinSize']))
                raise RenderException('\n'.join(lines))
            else:
                lines = []
                lines.append(
                    'Desired count {} is greater than MaxSize of {} on AutoscalingGroup "{}".'.format(
                        count,
                        obj.autoscaling_group.data['MaxSize'],
                        obj.autoscaling_group.name
                    )
                )
                lines.append('\nEither:')
                lines.append('  (1) use --force to also increase AutoscalingGroup MaxSize to {}'.format(count))
                lines.append('  (2) specify count <= {}'.format(obj.autoscaling_group.data['MaxSize']))
                raise RenderException('\n'.join(lines))
        return click.style(
            '\n\nSet count for {}("{}") to {} instances.'.format(self.model.__name__, obj.pk, count),
            fg='green'
        )

    @handle_model_exceptions
    def scale_instances(self, identifier, count, force):
        obj = self.get_object_from_aws(identifier)
        return self._scale_instances(obj, count, force)


class ClickScaleServiceCommandMixin(ClickScaleInstancesCommandMixin):

    @classmethod
    def add_scale_service_click_command(cls, command_group):
        """
        Build a fully specified click command for scaling ECS services, and add it to the click command group
        `command_group`.  Return the properly wrapped function object.

        :param command_group function: the click command group function to use to register our click command

        :rtype: function
        """
        def scale_service(ctx, *args, **kwargs):
            if cls.model.config_section is not None:
                try:
                    ctx.obj['config'] = get_config(**ctx.obj)
                except ConfigProcessingFailed as e:
                    ctx.obj['config'] = e
            ctx.obj['adapter'] = cls()
            click.secho(ctx.obj['adapter'].scale_service(
                kwargs['identifier'],
                kwargs['count'],
                kwargs['asg'],
                kwargs['force_asg'],
            ))

        pk_description = cls.get_pk_description()
        scale_service.__doc__ = """
Change the number of running tasks for a Service in AWS.

{pk_description}

COUNT is an integer.
""".format(pk_description=pk_description)

        function = print_render_exception(scale_service)
        function = click.pass_context(function)
        function = click.option(
            '--force-asg/--no-force-asg',
            default=False,
            help='Force the AutoscalingGroup to scale outside its MinCount or MaxCount'
        )(function)
        function = click.option(
            '--asg/--no-asg',
            default=False,
            help='Scale the AutoscalingGroup for the cluster also'
        )(function)
        function = click.argument('count', type=int)(function)
        function = click.argument('identifier')(function)
        function = command_group.command(
            'scale',
            short_help='Change the number of tasks for a Service in AWS.'.format(
                object_name=cls.model.__name__
            )
        )(function)
        return function

    def scale_services_waiter(self, obj, **kwargs):
        kwargs['WaiterHooks'] = [ECSDeploymentStatusWaiterHook(obj)]
        kwargs['services'] = [obj.name]
        kwargs['cluster'] = obj.data['cluster']
        self.wait('services_stable', **kwargs)

    @handle_model_exceptions
    def scale_service(self, identifier, count, asg, force):
        obj = self.get_object_from_aws(identifier)
        click.secho('Updating desiredCount to "{}" on Service(pk="{}")'.format(count, obj.pk))
        if asg:
            self._scale_instances(obj.cluster, count, force=force)
        obj.scale(count)
        self.scale_services_waiter(obj)
        return click.style('\n\nScaled {}("{}") to {} tasks.'.format(self.model.__name__, obj.pk, count), fg='green')


class ClickRestartServiceCommandMixin(ClickScaleInstancesCommandMixin):

    @classmethod
    def add_restart_service_click_command(cls, command_group):
        """
        Build a fully specified click command for restarting the tasks in ECS services, and add it to the click command
        group `command_group`.  Return the properly wrapped function object.

        :param command_group function: the click command group function to use to register our click command

        :rtype: function
        """
        def restart_service(ctx, *args, **kwargs):
            if cls.model.config_section is not None:
                try:
                    ctx.obj['config'] = get_config(**ctx.obj)
                except ConfigProcessingFailed as e:
                    ctx.obj['config'] = e
            ctx.obj['adapter'] = cls()
            click.secho(ctx.obj['adapter'].restart_service(kwargs['identifier'], kwargs['hard']))

        pk_description = cls.get_pk_description()
        restart_service.__doc__ = """
Iterate through the running tasks for the Service, killing each one and waiting
for its replacement to be healthy before killing the next.

If --hard is passed, kill all tasks simultaneously.  You might use this if your
Service is completely wedged.

{pk_description}
""".format(pk_description=pk_description)

        function = print_render_exception(restart_service)
        function = click.pass_context(function)
        function = click.option(
            '--hard/--no-hard',
            default=False,
            help='Kill off all tasks at once instead of iterating through them'
        )(function)
        function = click.argument('identifier')(function)
        function = command_group.command(
            'restart',
            short_help='Restart the running tasks for a Service in AWS.'.format(
                object_name=cls.model.__name__
            )
        )(function)
        return function

    def scale_services_waiter(self, obj, **kwargs):
        kwargs['WaiterHooks'] = [ECSDeploymentStatusWaiterHook(obj)]
        kwargs['services'] = [obj.name]
        kwargs['cluster'] = obj.data['cluster']
        self.wait('services_stable', **kwargs)

    @handle_model_exceptions
    def restart_service(self, identifier, hard):
        obj = self.get_object_from_aws(identifier)
        obj.restart(hard=hard, waiter_hooks=[ECSDeploymentStatusWaiterHook(obj)])
        return click.style('\n\nRestarted tasks for {}("{}").'.format(self.model.__name__, obj.pk), fg='green')


class ClickListServiceRelatedTasksCommandMixin(ClickUpdateObjectCommandMixin):
    @classmethod
    def add_list_related_tasks_click_command(cls, command_group):
        """
        Build a fully specified click command for listing StandaloneTasks related to a Service from what we have in our
        deployfish.yml file, and add it to the click command group `command_group`.  Return the function object.

        :param command_group function: the click command group function to use to register our click command

        :rtype: function
        """
        if cls.model.config_section is None:
            raise cls.ReadOnly(
                '{} objects are read only. If you want them to be read/write, define the '
                '"config_section" class attribute on the model to be the section in deployfish.yml '
                'where configuration info can be found for them.'
            )

        def list_related_tasks(ctx, *args, **kwargs):
            try:
                ctx.obj['config'] = get_config(**ctx.obj)
            except ConfigProcessingFailed as e:
                raise RenderException(str(e))
            ctx.obj['adapter'] = cls()
            ctx.obj['adapter'].list_related_standalone_tasks(kwargs.pop('identifier'))
        list_related_tasks.__doc__ = """
List StandaloneTasks related to a Service from what we have in our deployfish.yml file.

NOTE: This lists tasks defined under the top level 'tasks:' section in deployfish.yml.  ServiceHelperTasks -- those
defined by a 'tasks:' section under the Service definition will not be listed here.

IDENTIFIER is a string that looks like one of:

    * Service.name

    * Service.environment

"""
        function = print_render_exception(list_related_tasks)
        function = click.pass_context(function)
        function = click.argument('identifier')(function)
        function = command_group.command(
            'list-related-tasks',
            short_help='List StandaloneTasks related to a Service from configuration in deployfish.yml'
        )(function)
        return function

    def list_related_standalone_tasks(self, service_identifier, **kwargs):
        service = self.get_object_from_deployfish(
            service_identifier,
            factory_kwargs=self.factory_kwargs.get('list_related_tasks', {})
        )
        config = get_config()
        tasks = []
        for task_data in config.cooked['tasks']:
            if 'service' in task_data:
                if (task_data['service'] == service.pk or task_data['service'] == service.name):
                    tasks.append(task_data['name'])
        tasks.sort()
        if tasks:
            for task in tasks:
                click.echo(task)


class ClickUpdateServiceRelatedTasksCommandMixin(ClickUpdateObjectCommandMixin):
    @classmethod
    def add_update_related_tasks_click_command(cls, command_group):
        """
        Build a fully specified click command for StandaloneTasks related to a Service from what we have in our
        deployfish.yml file, and add it to the click command group `command_group`.  Return the function object.

        :param command_group function: the click command group function to use to register our click command

        :rtype: function
        """
        if cls.model.config_section is None:
            raise cls.ReadOnly(
                '{} objects are read only. If you want them to be read/write, define the '
                '"config_section" class attribute on the model to be the section in deployfish.yml '
                'where configuration info can be found for them.'
            )

        def update_object(ctx, *args, **kwargs):
            try:
                ctx.obj['config'] = get_config(**ctx.obj)
            except ConfigProcessingFailed as e:
                raise RenderException(str(e))
            ctx.obj['adapter'] = cls()
            ctx.obj['adapter'].update_related_standalone_tasks(kwargs.pop('identifier'))
        update_object.__doc__ = """
Update StandaloneTasks related to a Service from what we have in our deployfish.yml file.

NOTE: This handles tasks defined under the top level 'tasks:' section in deployfish.yml.  ServiceHelperTasks -- those
defined by a 'tasks:' section under the Service definition -- get updated automatically when the Service itself is
updated.

IDENTIFIER is a string that looks like one of:

    * Service.name

    * Service.environment

"""
        function = print_render_exception(update_object)
        function = click.pass_context(function)
        function = click.argument('identifier')(function)
        function = command_group.command(
            'update-related-tasks',
            short_help='Update a StandaloneTasks related to a Service from configuration in deployfish.yml'
        )(function)
        return function

    def update_related_standalone_tasks(self, service_identifier, **kwargs):
        service = self.get_object_from_deployfish(
            service_identifier,
            factory_kwargs=self.factory_kwargs.get('update', {})
        )
        config = get_config()
        tasks = []
        for task_data in config.cooked['tasks']:
            if 'service' in task_data:
                if (task_data['service'] == service.pk or task_data['service'] == service.name):
                    tasks.append(task_data['name'])
        if tasks:
            click.secho(
                '\n\nUpdating StandaloneTasks related to {}("{}"):\n'.format(
                    self.model.__name__,
                    service.pk
                ),
                fg='yellow'
            )
            for task in tasks:
                task = self.get_object_from_deployfish(task, model=StandaloneTask)
                arn = task.save()
                family_revision = arn.rsplit('/')[1]
                click.secho('  UPDATED: {} -> {}'.format(task.name, family_revision))
            click.secho('\nDone.', fg='yellow')


# ServiceHelperTasks
# ------------------

class ClickListHelperTasksCommandMixin(object):

    list_helper_tasks_ordering = None
    list_helper_tasks_result_columns = {}
    list_helper_tasks_renderer_classes = {
        'table': TableRenderer,
        'detail': TemplateRenderer,
        'json': JSONRenderer
    }

    @classmethod
    def list_helper_tasks_display_option_kwargs(cls):
        """
        Return the appropriate kwargs for `click.option('--display', **kwargs)` for the renderer options we've defined
        for the list endpoint.

        :rtype: dict
        """
        render_types = list(cls.list_helper_tasks_renderer_classes.keys())
        default = render_types[0]
        kwargs = {
            'type': click.Choice(render_types),
            'default': default,
            'help': "Render method for listing {} objects. Choices: {}.  Default: {}.".format(
                cls.model.__name__,
                ', '.join(render_types),
                default
            )
        }
        return kwargs

    @classmethod
    def add_list_helper_tasks_click_command(cls, command_group):
        """
        Build a fully specified click command for listing helper tasks for an ECS service, and add it to the click
        command group `command_group`.  Return the properly wrapped function object.

        :param command_group function: the click command group function to use to register our click command

        :rtype: function
        """
        def list_helper_tasks(ctx, *args, **kwargs):
            if cls.model.config_section is not None:
                try:
                    ctx.obj['config'] = get_config(**ctx.obj)
                except ConfigProcessingFailed as e:
                    ctx.obj['config'] = e
            ctx.obj['adapter'] = cls()
            click.secho(ctx.obj['adapter'].list_helper_tasks(kwargs['identifier'], kwargs['display']))

        pk_description = cls.get_pk_description()
        list_helper_tasks.__doc__ = """
List the helper tasks associated with a Service in AWS.

{pk_description}
""".format(pk_description=pk_description)

        function = print_render_exception(list_helper_tasks)
        function = click.pass_context(function)
        function = click.option('--display', **cls.list_helper_tasks_display_option_kwargs())(function)
        function = click.argument('identifier')(function)
        function = command_group.command(
            'list',
            short_help='List the helper tasks for a Service in AWS.'.format(
                object_name=cls.model.__name__
            )
        )(function)
        return function

    @handle_model_exceptions
    def list_helper_tasks(self, identifier, display):
        assert display in self.list_helper_tasks_renderer_classes, \
            'list helper tasks: "{}" is not a valid rendering option'.format(
                self.__class__.__name__,
                display
            )
        obj = self.get_object_from_aws(identifier)
        results = obj.helper_tasks
        if not results:
            return('No results.')
        else:
            if display == 'table':
                results = self.list_helper_tasks_renderer_classes[display](
                    self.list_helper_tasks_result_columns,
                    ordering=self.list_helper_tasks_ordering
                ).render(results)
            else:
                results = self.list_helper_tasks_renderer_classes[display]().render(results)
            results = '\n' + results + '\n'
            return results


class ClickHelperTaskInfoCommandMixin(HelperTaskCommandMixin):

    helper_task_info_includes = ['secrets']
    helper_task_info_excludes = []
    helper_task_info_renderer_classes = {
        'detail': TemplateRenderer,
        'json': JSONRenderer,
    }

    @classmethod
    def helper_task_info_display_option_kwargs(cls):
        """
        Return the appropriate kwargs for `click.option('--display', **kwargs)` for the renderer options we've defined
        for the retrieve endpoint.

        :rtype: dict
        """
        render_types = list(cls.helper_task_info_renderer_classes.keys())
        default = render_types[0]
        kwargs = {
            'type': click.Choice(render_types),
            'default': default,
            'help': "Choose how to display a single ServiceHelperTask object. Choices: {}.  Default: {}.".format(
                ', '.join(render_types),
                default
            )
        }
        return kwargs

    @classmethod
    def helper_task_info_include_option_kwargs(cls):
        kwargs = {
            'type': click.Choice(cls.helper_task_info_includes),
            'help': "Detail view only: Include optional information not normally shown. Choices: {}.".format(
                ', '.join(cls.helper_task_info_includes),
            ),
            'default': None,
            'multiple': True
        }
        return kwargs

    @classmethod
    def info_exclude_option_kwargs(cls):
        kwargs = {
            'type': click.Choice(cls.helper_task_info_excludes),
            'help': "Detail view only: Exclude information normally shown. Choices: {}.".format(
                ', '.join(cls.helper_task_info_excludes),
            ),
            'default': None,
            'multiple': True
        }
        return kwargs

    @classmethod
    def add_helper_task_info_click_command(cls, command_group):
        """
        Build a fully specified click command for retrieving single objects, and add it to the click command group
        `command_group`.  Return the function object.

        :param command_group function: the click command group function to use to register our click command

        :rtype: function
        """
        def retrieve_helper_task(ctx, *args, **kwargs):
            if cls.model.config_section is not None:
                try:
                    ctx.obj['config'] = get_config(**ctx.obj)
                except ConfigProcessingFailed:
                    pass
            ctx.obj['adapter'] = cls()
            click.secho(ctx.obj['adapter'].info(
                kwargs['service_identifier'],
                kwargs['helper_task_name'],
                kwargs['display'],
                kwargs.get('include', None),
                kwargs.get('exclude', None)
            ))

        args, kwargs = FunctionTypeCommentParser().parse(cls.model.objects.get)
        pk_description = cls.get_pk_description(name='SERVICE_IDENTIFIER')
        retrieve_helper_task.__doc__ = """
Show info about a ServiceHelperTask object associated with a Service that exists in AWS.

{pk_description}

""".format(pk_description=pk_description, object_name=cls.model.__name__)

        function = print_render_exception(retrieve_helper_task)
        function = click.pass_context(function)
        if cls.helper_task_info_includes:
            function = click.option('--include', **cls.helper_task_info_include_option_kwargs())(function)
        if cls.helper_task_info_excludes:
            function = click.option('--exclude', **cls.helper_task_info_exclude_option_kwargs())(function)
        function = click.option('--display', **cls.helper_task_info_display_option_kwargs())(function)
        function = click.argument('helper_task_name')(function)
        function = click.argument('service_identifier')(function)
        function = command_group.command(
            'info',
            short_help='Show info for a single ServiceHelperTask object in AWS'
        )(function)
        return function

    @handle_model_exceptions
    def info(self, service_pk, task_name, display, include, exclude, **kwargs):
        if include is None:
            include = []
        if exclude is None:
            exclude = []
        assert display in self.helper_task_info_renderer_classes, \
            'ServiceHelperTaskinfo(): "{}" is not a valid rendering option'.format(display)
        task = self.get_task(service_pk, task_name)
        context = {'includes': include, 'excludes': exclude}
        return '\n' + self.helper_task_info_renderer_classes[display]().render(task, context=context) + '\n'


class ClickRunHelperTaskCommandMixin(HelperTaskCommandMixin):

    def run_task_waiter(self, tasks, **kwargs):
        kwargs['WaiterHooks'] = [ECSTaskStatusHook(tasks)]
        kwargs['tasks'] = [t.arn for t in tasks]
        kwargs['cluster'] = tasks[0].cluster_name
        self.wait('tasks_stopped', **kwargs)

    @classmethod
    def add_run_helper_task_click_command(cls, command_group):
        """
        Build a fully specified click command for retrieving single objects, and add it to the click command group
        `command_group`.  Return the function object.

        :param command_group function: the click command group function to use to register our click command

        :rtype: function
        """
        def run_helper_task(ctx, *args, **kwargs):
            if cls.model.config_section is not None:
                try:
                    ctx.obj['config'] = get_config(**ctx.obj)
                except ConfigProcessingFailed:
                    pass
            ctx.obj['adapter'] = cls()
            ctx.obj['adapter'].run_helper_task(
                kwargs['service_identifier'],
                kwargs['helper_task_name'],
                kwargs['wait']
            )

        args, kwargs = FunctionTypeCommentParser().parse(cls.model.objects.get)
        pk_description = cls.get_pk_description(name='SERVICE_IDENTIFIER')
        run_helper_task.__doc__ = """
Run a ServiceHelperTask associated with a Service that exists in AWS.

{pk_description}

""".format(pk_description=pk_description, object_name=cls.model.__name__)

        function = print_render_exception(run_helper_task)
        function = click.pass_context(function)
        function = click.option('--wait/--no-wait', default=False, help='Wait until the command finishes.')(function)
        function = click.argument('helper_task_name')(function)
        function = click.argument('service_identifier')(function)
        function = command_group.command(
            'run',
            short_help='Run info for a single ServiceHelperTask object in AWS'
        )(function)
        return function

    @handle_model_exceptions
    def run_helper_task(self, service_pk, command_name, wait, **kwargs):
        command = self.get_task(service_pk, command_name)
        tasks = command.run()
        lines = []
        for task in tasks:
            lines.append(click.style('\nStarted task: {}:{}\n'.format(command.data['cluster'], task.arn), fg='green'))
        click.secho('\n'.join(lines))
        if wait:
            self.run_task_waiter(tasks)


class ClickTailHelperTaskLogsMixin(HelperTaskCommandMixin):

    @classmethod
    def add_tail_logs_click_command(cls, command_group):
        """
        Build a fully specified click command for tailing the logs for a task, and add it to the click command group
        `command_group`.  Return the function object.

        :param command_group function: the click command group function to use to register our click command

        :rtype: function
        """
        def run_helper_task(ctx, *args, **kwargs):
            if cls.model.config_section is not None:
                try:
                    ctx.obj['config'] = get_config(**ctx.obj)
                except ConfigProcessingFailed:
                    pass
            ctx.obj['adapter'] = cls()
            ctx.obj['adapter'].tail_task_log(
                kwargs['service_identifier'],
                kwargs['helper_task_name'],
                kwargs['sleep'],
                kwargs['filter_pattern'],
                kwargs['mark']
            )

        args, kwargs = FunctionTypeCommentParser().parse(CloudWatchLogGroup.get_event_tailer)
        pk_description = cls.get_pk_description(name='SERVICE_IDENTIFIER')
        run_helper_task.__doc__ = """
If a ServiceHelperTask uses "awslogs" as its logDriver, tail the logs for that ServiceHelperTask.

{pk_description}

""".format(pk_description=pk_description, object_name=cls.model.__name__)

        function = print_render_exception(run_helper_task)
        function = click.pass_context(function)
        function = click.option(
            '--mark/--no-mark',
            default=False,
            help="Print out a line every --sleep seconds.  Use this to know that the log tailer isn't stuck.",
        )(function)
        for key, kwarg in kwargs.items():
            if key != 'stream_prefix':
                function = cls.add_option(key, kwarg, function)
        for key, arg in args.items():
            function = cls.add_argument(key, arg, function)
        function = click.argument('helper_task_name')(function)
        function = click.argument('service_identifier')(function)
        function = command_group.command(
            'tail',
            short_help='Tail logs for a ServiceHelperTask.'
        )(function)
        return function

    @handle_model_exceptions
    def tail_task_log(self, service_pk, command_name, sleep, filter_pattern, mark, **kwargs):
        command = self.get_task(service_pk, command_name)
        lc = command.task_definition.logging
        if lc['logDriver'] != 'awslogs':
            raise RenderException('Task log driver is "{}"; we can only tail "awslogs"'.format(lc['logDriver']))
        group = CloudWatchLogGroup.objects.get(lc['options']['awslogs-group'])
        stream_prefix = lc['options']['awslogs-stream-prefix']
        tailer = group.get_event_tailer(stream_prefix=stream_prefix, sleep=sleep, filter_pattern=filter_pattern)
        for page in tailer:
            for event in page:
                click.secho("{}  {}".format(
                    click.style(event['timestamp'].strftime('%Y-%m-%d %H:%M:%S.%f'), fg='cyan'),
                    event['message'].strip()
                ))
            if mark:
                click.secho("==============================  mark  ===================================", fg="yellow")


class ClickListHelperTaskLogsMixin(HelperTaskCommandMixin):

    @classmethod
    def add_list_logs_click_command(cls, command_group):
        """
        Build a fully specified click command for listing the log streams for a task, and add it to the click command
        group `command_group`.  Return the function object.

        :param command_group function: the click command group function to use to register our click command

        :rtype: function
        """
        def run_helper_task(ctx, *args, **kwargs):
            if cls.model.config_section is not None:
                try:
                    ctx.obj['config'] = get_config(**ctx.obj)
                except ConfigProcessingFailed:
                    pass
            ctx.obj['adapter'] = cls()
            lines = ctx.obj['adapter'].list_task_logs(
                kwargs['service_identifier'],
                kwargs['helper_task_name'],
                kwargs['limit'],
            )
            if lines.count('\n') > 40:
                click.echo_via_pager(lines)
            else:
                click.echo(lines)

        pk_description = cls.get_pk_description(name='SERVICE_IDENTIFIER')
        run_helper_task.__doc__ = """
If a ServiceHelperTask uses "awslogs" as its logDriver, list the available log streams for that ServiceHelperTask.

{pk_description}

""".format(pk_description=pk_description, object_name=cls.model.__name__)

        function = print_render_exception(run_helper_task)
        function = click.pass_context(function)
        function = click.option(
            '--limit',
            default=None,
            help="Limit the number of streams listed.",
            type=int
        )(function)
        function = click.argument('helper_task_name')(function)
        function = click.argument('service_identifier')(function)
        function = command_group.command(
            'list',
            short_help='List awslogs log streams for a ServiceHelperTask.'
        )(function)
        return function

    @handle_model_exceptions
    def list_task_logs(self, service_pk, command_name, limit, **kwargs):
        command = self.get_task(service_pk, command_name)
        lc = command.task_definition.logging
        if lc['logDriver'] != 'awslogs':
            raise RenderException(
                'Task log driver is "{}"; we can only list "awslogs" log streams'.format(lc['logDriver'])
            )
        group = CloudWatchLogGroup.objects.get(lc['options']['awslogs-group'])
        stream_prefix = lc['options']['awslogs-stream-prefix']
        streams = group.log_streams(stream_prefix=stream_prefix, maxitems=limit)
        columns = {
            'Stream Name': 'logStreamName',
            'Created': {'key': 'creationTime', 'datatype': 'timestamp'},
            'Last Event': {'key': 'lastEventTimestamp', 'datatype': 'timestamp', 'default': ''},
        }
        return '\n' + TableRenderer(columns, ordering='-Created').render(streams) + '\n'


class ClickUpdateHelperTasksCommandMixin(object):

    update_template = None

    @classmethod
    def add_update_helper_tasks_click_command(cls, command_group):
        """
        Build a fully specified click command for updating ServiceHelperTasks without updating the related Service, and
        add it to the click command group `command_group`.  Return the function object.

        :param command_group function: the click command group function to use to register our click command

        :rtype: function
        """
        def update_helper_tasks(ctx, *args, **kwargs):
            try:
                ctx.obj['config'] = get_config(**ctx.obj)
            except ConfigProcessingFailed as e:
                raise RenderException(str(e))
            ctx.obj['adapter'] = cls()
            click.secho(ctx.obj['adapter'].update_helper_tasks(kwargs.pop('service_identifier')))
        update_helper_tasks.__doc__ = """
Update all the Service's ServiceHelperTasks in AWS independently of the Service,
and return the new task defintiion family:revision for each.

This command exists because while we normally update ServiceHelperTasks
automatically when their Service is updated, sometimes we want to update a
ServiceHelperTask without touching the Service.  For example, when we want to
run our database migrations before updating the code for the Service.

NOTE: The ServiceHelperTasks you write with this command won't be directly
associated with the live Service in AWS, like they would when doing "deploy
service update".  So to run these tasks, use the family:revision returned by
this command with "deploy task run" instead of running them with "deploy service
tasks run".

SERVICE_IDENTIFIER is a string that looks like one of:

    * Service.name

    * Service.environment
"""

        function = print_render_exception(update_helper_tasks)
        function = click.pass_context(function)
        function = click.argument('service_identifier')(function)
        function = command_group.command(
            'update',
            short_help='Update ServiceHelperTasks independently of their Service'
        )(function)
        return function

    @handle_model_exceptions
    def update_helper_tasks(self, identifier, **kwargs):
        obj = self.get_object_from_deployfish(identifier)
        click.secho('\n\nUpdating ServiceHelperTasks associated with Service("{}"):\n'.format(obj.pk), fg='yellow')
        for task in obj.helper_tasks:
            click.secho('UPDATE: {} -> '.format(task.command), nl=False)
            arn = task.save()
            family_revision = arn.rsplit('/')[1]
            click.secho(family_revision)
        return click.style('\nDone.', fg='yellow')


class ClickDisableHelperTaskMixin(object):

    @classmethod
    def add_disable_task_schedule_click_command(cls, command_group):
        """
        Build a fully specified click command for disabling the schedule rule for a task, and add it to the click
        command group `command_group`.  Return the function object.

        :param command_group function: the click command group function to use to register our click command

        :rtype: function
        """
        def disable_schedule(ctx, *args, **kwargs):
            if cls.model.config_section is not None:
                try:
                    ctx.obj['config'] = get_config(**ctx.obj)
                except ConfigProcessingFailed:
                    pass
            ctx.obj['adapter'] = cls()
            click.secho(ctx.obj['adapter'].disable_schedule(
                kwargs['service_identifier'],
                kwargs['helper_task_name'],
            ))

        pk_description = cls.get_pk_description(name='SERVICE_IDENTIFIER')
        pk_description = cls.get_pk_description()
        disable_schedule.__doc__ = """
If a ServiceHelperTask in AWS has a schedule rule and that rule is currently enabled, disable it.

{pk_description}

""".format(pk_description=pk_description, object_name=cls.model.__name__)

        function = print_render_exception(disable_schedule)
        function = click.pass_context(function)
        function = click.argument('helper_task_name')(function)
        function = click.argument('service_identifier')(function)
        function = command_group.command(
            'disable',
            short_help='Disable the schedule for a ServiceHelperTask.'
        )(function)
        return function

    @handle_model_exceptions
    def disable_schedule(self, service_pk, command_name, **kwargs):
        command = self.get_task(service_pk, command_name)
        if command.schedule is None:
            return click.style(
                f'ABORT: ServiceHelperTask("{command_name}") has no schedule; disabling only affects schedules.',
                fg='yellow'
            )
        command.disable_schedule()
        if command.schedule.enabled:
            return click.style(f'ServiceHelperTask("{command_name}") state is now ENABLED.', fg='red')
        else:
            return click.style(f'ServiceHelperTask("{command_name}") state is now DISABLED.', fg='green')


class ClickEnableHelperTaskMixin(object):

    @classmethod
    def add_enable_task_schedule_click_command(cls, command_group):
        """
        Build a fully specified click command for enabling the schedule rule for a task, and add it to the click
        command group `command_group`.  Return the function object.

        :param command_group function: the click command group function to use to register our click command

        :rtype: function
        """
        def enable_schedule(ctx, *args, **kwargs):
            if cls.model.config_section is not None:
                try:
                    ctx.obj['config'] = get_config(**ctx.obj)
                except ConfigProcessingFailed:
                    pass
            ctx.obj['adapter'] = cls()
            click.secho(ctx.obj['adapter'].enable_schedule(
                kwargs['service_identifier'],
                kwargs['helper_task_name'],
            ))

        pk_description = cls.get_pk_description(name='SERVICE_IDENTIFIER')
        enable_schedule.__doc__ = """
If a ServiceHelperTask in AWS has a schedule rule and that rule is currently disabled, enable it.

{pk_description}

""".format(pk_description=pk_description, object_name=cls.model.__name__)

        function = print_render_exception(enable_schedule)
        function = click.pass_context(function)
        function = click.argument('helper_task_name')(function)
        function = click.argument('service_identifier')(function)
        function = command_group.command(
            'enable',
            short_help='Enable the schedule for a ServiceHelperTask.'
        )(function)
        return function

    @handle_model_exceptions
    def enable_schedule(self, service_pk, command_name, **kwargs):
        command = self.get_task(service_pk, command_name)
        if command.schedule is None:
            return click.style(
                f'ABORT: ServiceHelperTask("{command_name}") has no schedule; enabling only affects schedules.',
                fg='yellow'
            )
        command.enable_schedule()
        if command.schedule.enabled:
            return click.style(f'ServiceHelperTask("{command_name}") state is now ENABLED.', fg='green')
        else:
            return click.style(f'ServiceHelperTask("{command_name}") state is now DISABLED.', fg='red')


# StandaloneTasks
# ---------------

class ClickRunStandaloneTaskCommandMixin(object):

    def run_task_waiter(self, tasks, **kwargs):
        kwargs['WaiterHooks'] = [ECSTaskStatusHook(tasks)]
        kwargs['tasks'] = [t.arn for t in tasks]
        kwargs['cluster'] = tasks[0].cluster_name
        self.wait('tasks_stopped', **kwargs)

    @classmethod
    def add_run_task_click_command(cls, command_group):
        """
        Build a fully specified click command for retrieving single objects, and add it to the click command group
        `command_group`.  Return the function object.

        :param command_group function: the click command group function to use to register our click command

        :rtype: function
        """
        def run_task(ctx, *args, **kwargs):
            if cls.model.config_section is not None:
                try:
                    ctx.obj['config'] = get_config(**ctx.obj)
                except ConfigProcessingFailed:
                    pass
            ctx.obj['adapter'] = cls()
            ctx.obj['adapter'].run_task(
                kwargs['identifier'],
                kwargs['wait']
            )

        args, kwargs = FunctionTypeCommentParser().parse(cls.model.objects.get)
        pk_description = cls.get_pk_description()
        run_task.__doc__ = """
Run a StandaloneTask that exists in AWS.

{pk_description}

""".format(pk_description=pk_description, object_name=cls.model.__name__)

        function = print_render_exception(run_task)
        function = click.pass_context(function)
        function = click.option('--wait/--no-wait', default=False, help='Wait until the command finishes.')(function)
        function = click.argument('identifier')(function)
        function = command_group.command(
            'run',
            short_help='Run info for a single StandaloneTask object in AWS'
        )(function)
        return function

    @handle_model_exceptions
    def run_task(self, pk, wait, **kwargs):
        standalone_task = self.get_object_from_aws(pk)
        tasks = standalone_task.run()
        lines = []
        for task in tasks:
            lines.append(
                click.style('\nStarted task: {}:{}\n'.format(standalone_task.data['cluster'], task.arn), fg='green')
            )
        click.secho('\n'.join(lines))
        if wait:
            self.run_task_waiter(tasks)


class ClickTailStandaloneTaskLogsMixin(object):

    @classmethod
    def add_tail_logs_click_command(cls, command_group):
        """
        Build a fully specified click command for tailing the logs for a task, and add it to the click command group
        `command_group`.  Return the function object.

        :param command_group function: the click command group function to use to register our click command

        :rtype: function
        """
        def tail_task_log(ctx, *args, **kwargs):
            if cls.model.config_section is not None:
                try:
                    ctx.obj['config'] = get_config(**ctx.obj)
                except ConfigProcessingFailed:
                    pass
            ctx.obj['adapter'] = cls()
            ctx.obj['adapter'].tail_task_log(
                kwargs['identifier'],
                kwargs['sleep'],
                kwargs['filter_pattern'],
                kwargs['mark']
            )

        args, kwargs = FunctionTypeCommentParser().parse(CloudWatchLogGroup.get_event_tailer)
        pk_description = cls.get_pk_description()
        tail_task_log.__doc__ = """
If a StandaloneTask uses "awslogs" as its logDriver, tail the logs for that StandaloneTask.

{pk_description}

""".format(pk_description=pk_description, object_name=cls.model.__name__)

        function = print_render_exception(tail_task_log)
        function = click.pass_context(function)
        function = click.option(
            '--mark/--no-mark',
            default=False,
            help="Print out a line every --sleep seconds.  Use this to know that the log tailer isn't stuck.",
        )(function)
        for key, kwarg in kwargs.items():
            if key != 'stream_prefix':
                function = cls.add_option(key, kwarg, function)
        for key, arg in args.items():
            function = cls.add_argument(key, arg, function)
        function = click.argument('identifier')(function)
        function = command_group.command(
            'tail',
            short_help='Tail logs for a StandaloneTask.'
        )(function)
        return function

    @handle_model_exceptions
    def tail_task_log(self, pk, sleep, filter_pattern, mark, **kwargs):
        standalone_task = self.get_object_from_aws(pk)
        lc = standalone_task.task_definition.logging
        if lc['logDriver'] != 'awslogs':
            raise RenderException('Task log driver is "{}"; we can only tail "awslogs"'.format(lc['logDriver']))
        group = CloudWatchLogGroup.objects.get(lc['options']['awslogs-group'])
        stream_prefix = lc['options']['awslogs-stream-prefix']
        tailer = group.get_event_tailer(stream_prefix=stream_prefix, sleep=sleep, filter_pattern=filter_pattern)
        for page in tailer:
            for event in page:
                click.secho("{}  {}".format(
                    click.style(event['timestamp'].strftime('%Y-%m-%d %H:%M:%S.%f'), fg='cyan'),
                    event['message'].strip()
                ))
            if mark:
                click.secho("==============================  mark  ===================================", fg="yellow")


class ClickListStandaloneTaskLogsMixin(object):

    @classmethod
    def add_list_logs_click_command(cls, command_group):
        """
        Build a fully specified click command for listing the log streams for a task, and add it to the click command
        group `command_group`.  Return the function object.

        :param command_group function: the click command group function to use to register our click command

        :rtype: function
        """
        def list_task_logs(ctx, *args, **kwargs):
            if cls.model.config_section is not None:
                try:
                    ctx.obj['config'] = get_config(**ctx.obj)
                except ConfigProcessingFailed:
                    pass
            ctx.obj['adapter'] = cls()
            lines = ctx.obj['adapter'].list_task_logs(
                kwargs['identifier'],
                kwargs['limit'],
            )
            if lines.count('\n') > 40:
                click.echo_via_pager(lines)
            else:
                click.echo(lines)

        pk_description = cls.get_pk_description()
        list_task_logs.__doc__ = """
If a StandaloneTask uses "awslogs" as its logDriver, list the available log streams for that StandaloneTask.

{pk_description}

""".format(pk_description=pk_description, object_name=cls.model.__name__)

        function = print_render_exception(list_task_logs)
        function = click.pass_context(function)
        function = click.option(
            '--limit',
            default=None,
            help="Limit the number of streams listed.",
            type=int
        )(function)
        function = click.argument('identifier')(function)
        function = command_group.command(
            'list',
            short_help='List awslogs log streams for a StandaloneTask.'
        )(function)
        return function

    @handle_model_exceptions
    def list_task_logs(self, pk, limit, **kwargs):
        standalone_task = self.get_object_from_aws(pk)
        lc = standalone_task.task_definition.logging
        if lc['logDriver'] != 'awslogs':
            raise RenderException(
                'Task log driver is "{}"; we can only list "awslogs" log streams'.format(lc['logDriver'])
            )
        group = CloudWatchLogGroup.objects.get(lc['options']['awslogs-group'])
        stream_prefix = lc['options']['awslogs-stream-prefix']
        streams = group.log_streams(stream_prefix=stream_prefix, maxitems=limit)
        columns = {
            'Stream Name': 'logStreamName',
            'Created': {'key': 'creationTime', 'datatype': 'timestamp'},
            'Last Event': {'key': 'lastEventTimestamp', 'datatype': 'timestamp', 'default': ''},
        }
        return '\n' + TableRenderer(columns, ordering='-Created').render(streams) + '\n'


class ClickDisableStandaloneTaskMixin(object):

    @classmethod
    def add_disable_schedule_click_command(cls, command_group):
        """
        Build a fully specified click command for disabling the schedule rule for a task, and add it to the click
        command group `command_group`.  Return the function object.

        :param command_group function: the click command group function to use to register our click command

        :rtype: function
        """
        def disable_schedule(ctx, *args, **kwargs):
            if cls.model.config_section is not None:
                try:
                    ctx.obj['config'] = get_config(**ctx.obj)
                except ConfigProcessingFailed:
                    pass
            ctx.obj['adapter'] = cls()
            click.secho(ctx.obj['adapter'].disable_schedule(kwargs['identifier']))

        pk_description = cls.get_pk_description()
        disable_schedule.__doc__ = """
If a StandaloneTask in AWS has a schedule rule and that rule is currently enabled, disable it.

{pk_description}

""".format(pk_description=pk_description, object_name=cls.model.__name__)

        function = print_render_exception(disable_schedule)
        function = click.pass_context(function)
        function = click.argument('identifier')(function)
        function = command_group.command(
            'disable',
            short_help='Disable the schedule for a StandaloneTask.'
        )(function)
        return function

    @handle_model_exceptions
    def disable_schedule(self, pk, **kwargs):
        obj = self.get_object_from_aws(pk)
        if obj.schedule is None:
            return click.style(
                f'ABORT: StandaloneTask("{pk}") has no schedule; disabling only affects schedules.',
                fg='yellow'
            )
        obj.disable_schedule()
        if obj.schedule.enabled:
            return click.style(f'StandaloneTask("{pk}") state is now ENABLED.', fg='red')
        else:
            return click.style(f'StandaloneTask("{pk}") state is now DISABLED.', fg='green')


class ClickEnableStandaloneTaskMixin(object):

    @classmethod
    def add_enable_schedule_click_command(cls, command_group):
        """
        Build a fully specified click command for enabling the schedule rule for a task, and add it to the click
        command group `command_group`.  Return the function object.

        :param command_group function: the click command group function to use to register our click command

        :rtype: function
        """
        def enable_schedule(ctx, *args, **kwargs):
            if cls.model.config_section is not None:
                try:
                    ctx.obj['config'] = get_config(**ctx.obj)
                except ConfigProcessingFailed:
                    pass
            ctx.obj['adapter'] = cls()
            lines = ctx.obj['adapter'].enable_schedule(
                kwargs['identifier'],
            )
            if lines.count('\n') > 40:
                click.echo_via_pager(lines)
            else:
                click.echo(lines)

        pk_description = cls.get_pk_description()
        enable_schedule.__doc__ = """
If a StandaloneTask in AWS has a schedule rule and that rule is currently disabled, enable it.

{pk_description}

""".format(pk_description=pk_description, object_name=cls.model.__name__)

        function = print_render_exception(enable_schedule)
        function = click.pass_context(function)
        function = click.argument('identifier')(function)
        function = command_group.command(
            'enable',
            short_help='Enable the schedule for a StandaloneTask.'
        )(function)
        return function

    @handle_model_exceptions
    def enable_schedule(self, pk, **kwargs):
        obj = self.get_object_from_aws(pk)
        if obj.schedule is None:
            return click.style(
                f'ABORT: StandaloneTask("{pk}") has no schedule; enabling only affects schedules.',
                fg='yellow'
            )
        obj.enable_schedule()
        if obj.schedule.enabled:
            return click.style(f'StandaloneTask("{pk}") state is now ENABLED.', fg='green')
        else:
            return click.style(f'StandaloneTask("{pk}") state is now DISABLED.', fg='red')
