import click

from deployfish.cli.adapters.utils import handle_model_exceptions, print_render_exception
from deployfish.config import get_config
from deployfish.core.models import Cluster, AutoscalingGroup
from deployfish.core.waiters.hooks import ECSDeploymentStatusWaiterHook
from deployfish.exceptions import RenderException, ConfigProcessingFailed


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
        obj = self.get_object(identifier, needs_config=False)
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
        obj = self.get_object(identifier, needs_config=False)
        click.secho('Updating desiredCount to "{}" on Service(pk="{}")'.format(count, obj.pk))
        if asg:
            self._scale_instances(obj.cluster, count, force=force)
        obj.scale(count)
        self.scale_services_waiter(obj)
        return click.style('\n\nScaled {}("{}") to {} tasks.'.format(self.model.__name__, obj.pk, count), fg='green')
