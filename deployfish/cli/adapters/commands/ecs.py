import click

from deployfish.cli.adapters.utils import handle_model_exceptions, print_render_exception
from deployfish.config import get_config
from deployfish.core.models import Cluster, AutoscalingGroup
from deployfish.core.waiters.hooks import ECSDeploymentStatusWaiterHook
from deployfish.exceptions import RenderException, ConfigProcessingFailed
from deployfish.typing import FunctionTypeCommentParser

from deployfish.cli.renderers import (
    TableRenderer,
    JSONRenderer,
    TemplateRenderer
)


# Command mixins
# ====================

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
Change the number of instances for a {object_name} in AWS.

{pk_description}

COUNT is an integer.
""".format(pk_description=pk_description, object_name=cls.model.__name__)

        function = print_render_exception(scale_instances)
        function = click.pass_context(function)
        function = click.option(
            '--force/--no-force',
            default=False,
            help='Force the {object_name} to scale outside its MinCount or MaxCount'.format(
                object_name=cls.model.__name__
            )
        )(function)
        function = click.argument('count', type=int)(function)
        function = click.argument('identifier')(function)
        function = command_group.command(
            'scale',
            short_help='Change the number of instances for a {object_name} in AWS.'.format(
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
Restart the running tasks for a Service in AWS.

{pk_description}
""".format(pk_description=pk_description)

        function = print_render_exception(restart_service)
        function = click.pass_context(function)
        function = click.option(
            '--hard/--no-hard',
            default=False,
            help='Force the AutoscalingGroup to scale outside its MinCount or MaxCount'
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


class ClickHelperTaskInfoCommandMixin(object):

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
                    'Name': 'command',
                    'Revision': 'family_revision',
                    'Version': 'version',
                    'Launch Type': 'launchType',
                    'Schedule': 'schedule_expression'
                }, ordering='Name').render(obj.helper_tasks)
            )
            raise RenderException('\n'.join(lines))
        context = {
            'includes': include,
            'excludes': exclude
        }
        print(task)
        return '\n' + self.helper_task_info_renderer_classes[display]().render(task, context=context) + '\n'
