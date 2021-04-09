from functools import wraps
import sys

import click
from tabulate import tabulate

from deployfish.config import get_config
from deployfish.exceptions import RenderException, ObjectReadOnly, ObjectDoesNotExist, ConfigProcessingFailed
from deployfish.typing import FunctionTypeCommentParser
from deployfish.core.models import SSHTunnel, Secret

from ..renderers import (
    TableRenderer,
    JSONRenderer,
    TemplateRenderer
)


# ========================
# Decorators
# ========================

def handle_model_exceptions(func):

    @wraps(func)
    def inner(self, *args, **kwargs):
        try:
            obj = func(self, *args, **kwargs)
        except self.model.DoesNotExist as e:
            raise RenderException(click.style(str(e), fg='red'))
        except self.model.MultipleObjectsReturned as e:
            raise RenderException(click.style(str(e), fg='red'))
        except self.model.OperationFailed as e:
            lines = []
            lines.append(click.style(e.msg, fg='red'))
            for k, v in e.errors.items():
                lines.append(click.style(k + ':', fg='yellow'))
                if isinstance(v, list):
                    for error in v:
                        lines.append(click.style('    ' + error, fg='white'))
                else:
                    lines.append(click.style('    ' + v, fg='white'))
                raise RenderException('\n'.join(lines))
        except self.DeployfishObjectDoesNotExist as e:
            config = get_config()
            lines = []
            lines.append(click.style('ERROR: could not find a {} identified by "{}" in deployfish.yml\n'.format(
                self.model.__name__,
                e.name
            ), fg='red'))
            lines.append(click.style('Available {}:'.format(e.section), fg='cyan'))
            for item in config.get_section(e.section):
                lines.append('  {}'.format(item['name']))
            lines.append(click.style('\nAvailable environments:', fg='cyan'))
            for item in config.get_section(e.section):
                if 'environment' in item:
                    lines.append('  {}'.format(item['environment']))
            raise RenderException('\n'.join(lines))
        return obj
    return inner


def print_render_exception(func):

    @wraps(func)
    def inner(*args, **kwargs):
        try:
            retval = func(*args, **kwargs)
        except RenderException as e:
            click.echo(e.msg)
            sys.exit(e.exit_code)
        return retval
    return inner


# ====================
# Command mixins
# ====================


# CRUD

class ClickListObjectsCommandMixin(object):

    list_ordering = None
    list_result_columns = {}
    list_renderer_classes = {
        'table': TableRenderer,
        'json': JSONRenderer
    }

    @classmethod
    def list_display_option_kwargs(cls):
        """
        Return the appropriate kwargs for `click.option('--display', **kwargs)` for the renderer options we've defined
        for the list endpoint.

        :rtype: dict
        """
        render_types = list(cls.list_renderer_classes.keys())
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
    def add_list_click_command(cls, command_group):
        """
        Build a fully specified click command for listing objects, and add it to the click command group
        `command_group`.  Return the properly wrapped function object.

        :param command_group function: the click command group function to use to register our click command

        :rtype: function
        """
        def list_objects(ctx, *args, **kwargs):
            if cls.model.config_section is not None:
                try:
                    ctx.obj['config'] = get_config(**ctx.obj)
                except ConfigProcessingFailed as e:
                    ctx.obj['config'] = e
            ctx.obj['adapter'] = cls()
            display = kwargs.pop('display')
            click.secho(ctx.obj['adapter'].list(display, **kwargs))
        args, kwargs = FunctionTypeCommentParser().parse(cls.model.objects.list)
        list_objects.__doc__ = """
List {object_name} objects in AWS, possibly with filters.
""".format(
            object_name=cls.model.__name__,
            required_args=cls.get_required_args(args),
            command_group_name=command_group.name
        )

        function = print_render_exception(list_objects)
        function = click.pass_context(function)
        for key, kwarg in kwargs.items():
            function = cls.add_option(key, kwarg, function)
        function = click.option('--display', **cls.list_display_option_kwargs())(function)
        for key, arg in args.items():
            function = cls.add_argument(key, arg, function)
        function = command_group.command(
            'list',
            short_help='List {object_name} objects in AWS, possibly with filters.'.format(
                object_name=cls.model.__name__
            )
        )(function)
        return function

    @handle_model_exceptions
    def list(self, display, **kwargs):
        assert display in self.list_renderer_classes, \
            '{}.list(): "{}" is not a valid list rendering option'.format(
                self.__class__.__name__,
                display
            )
        results = self.model.objects.list(**kwargs)
        if not results:
            return('No results.')
        else:
            if display == 'table':
                results = self.list_renderer_classes[display](
                    self.list_result_columns,
                    ordering=self.list_ordering
                ).render(results)
            else:
                results = self.list_renderer_classes[display]().render(results)
            results = '\n' + results + '\n'
            return results


class ClickObjectInfoCommandMixin(object):

    info_renderer_classes = {
        'template': TemplateRenderer,
        'json': JSONRenderer,
    }

    @classmethod
    def info_display_option_kwargs(cls):
        """
        Return the appropriate kwargs for `click.option('--display', **kwargs)` for the renderer options we've defined
        for the retrieve endpoint.

        :rtype: dict
        """
        render_types = list(cls.info_renderer_classes.keys())
        default = render_types[0]
        kwargs = {
            'type': click.Choice(render_types),
            'default': default,
            'help': "Choose how to display a single {} object. Choices: {}.  Default: {}.".format(
                cls.model.__name__,
                ', '.join(render_types),
                default
            )
        }
        return kwargs

    @classmethod
    def add_info_click_command(cls, command_group):
        """
        Build a fully specified click command for retrieving single objects, and add it to the click command group
        `command_group`.  Return the function object.

        :param command_group function: the click command group function to use to register our click command

        :rtype: function
        """
        def retrieve_object(ctx, *args, **kwargs):
            if cls.model.config_section is not None:
                try:
                    ctx.obj['config'] = get_config(**ctx.obj)
                except ConfigProcessingFailed:
                    pass
            ctx.obj['adapter'] = cls()
            click.secho(ctx.obj['adapter'].info(kwargs['identifier'], kwargs['display']))

        args, kwargs = FunctionTypeCommentParser().parse(cls.model.objects.get)
        pk_description = cls.get_pk_description()
        retrieve_object.__doc__ = """
Show info about a {object_name} object that exists in AWS.

{pk_description}

""".format(pk_description=pk_description, object_name=cls.model.__name__)

        function = print_render_exception(retrieve_object)
        function = click.pass_context(function)
        function = click.option('--display', **cls.info_display_option_kwargs())(function)
        function = click.argument('identifier')(function)
        function = command_group.command(
            'info',
            short_help='Show info for a single {} object in AWS'.format(cls.model.__name__)
        )(function)
        return function

    @handle_model_exceptions
    def info(self, pk, display, **kwargs):
        assert display in self.info_renderer_classes, \
            '{}.info(): "{}" is not a valid rendering option'.format(
                self.__class__.__name__,
                display
            )
        obj = self.get_object(pk, needs_config=False, factory_kwargs=self.factory_kwargs.get('info', {}))
        obj.reload_from_db()
        return '\n' + self.info_renderer_classes[display]().render(obj) + '\n'


class ClickObjectExistsCommandMixin(object):

    @classmethod
    def add_exists_click_command(cls, command_group):
        """
        Build a fully specified click command for determining object exists in AWS, and add it to the click command
        group `command_group`.  Return the function object.

        :param command_group function: the click command group function to use to register our click command

        :rtype: function
        """
        def object_exists(ctx, *args, **kwargs):
            if cls.model.config_section is not None:
                try:
                    ctx.obj['config'] = get_config(**ctx.obj)
                except ConfigProcessingFailed:
                    pass
            ctx.obj['adapter'] = cls()
            click.secho(ctx.obj['adapter'].exists(kwargs['identifier']))

        args, kwargs = FunctionTypeCommentParser().parse(cls.model.objects.exists)
        pk_description = cls.get_pk_description()
        object_exists.__doc__ = """
Show info about a {object_name} object that exists in AWS.

{pk_description}

""".format(pk_description=pk_description, object_name=cls.model.__name__)

        function = print_render_exception(object_exists)
        function = click.pass_context(function)
        function = click.argument('identifier')(function)
        function = command_group.command(
            'exists',
            short_help='Show whether a {} object exists in AWS'.format(cls.model.__name__)
        )(function)
        return function

    @handle_model_exceptions
    def exists(self, pk,  **kwargs):
        obj = self.get_object(pk, needs_config=False, factory_kwargs=self.factory_kwargs.get('info', {}))
        if obj.exists:
            return click.style('{}(pk="{}") exists in AWS.'.format(self.model.__name__, pk), fg='green')
        else:
            return click.style('{}(pk="{}") does not exist in AWS.'.format(self.model.__name__, obj.pk), fg='red')


class ClickCreateObjectCommandMixin(object):

    @classmethod
    def add_create_click_command(cls, command_group):
        """
        Build a fully specified click command for creating objects, and add it to the click command group
        `command_group`.  Return the function object.

        :param command_group function: the click command group function to use to register our click command

        :rtype: function
        """
        if cls.model.config_section is None:
            raise cls.ReadOnly(
                '{} objects are read only. If you want them to be read/write, define the '
                '"config_section" class attribute on the model to be the section in deployfish.yml '
                'where configuration info can be found for them.'
            )

        def create_object(ctx, *args, **kwargs):
            try:
                ctx.obj['config'] = get_config(**ctx.obj)
            except ConfigProcessingFailed as e:
                raise RenderException(str(e))
            ctx.obj['adapter'] = cls()
            click.secho(ctx.obj['adapter'].create(kwargs.pop('name')))

        create_object.__doc__ = "Create a new {object_name} in AWS from your deployfish.yml file.".format(
            object_name=cls.model.__name__
        )
        # Wrap our function with the approriate decorators
        function = print_render_exception(create_object)
        function = click.argument('name')(function)
        function = click.pass_context(function)
        function = command_group.command(
            'create',
            short_help='Create a {} object in AWS from configuration info in deployfish.yml'.format(cls.model.__name__)
        )(function)
        return function

    def create_waiter(self, obj, **kwargs):
        pass

    @handle_model_exceptions
    def create(self, name, **kwargs):
        obj = self.get_object(name, factory_kwargs=self.factory_kwargs.get('create', {}))
        if obj.exists:
            raise RenderException('{}(pk={}) already exists in AWS!'.format(self.model.__name__, obj.pk))
        renderer = TemplateRenderer()
        click.secho('\n\nCreating {}("{}"):\n\n'.format(self.model.__name__, obj.pk), fg='yellow')
        click.secho(renderer.render(obj))
        obj.save()
        self.create_waiter(obj)
        return click.style('\n\nCreated {}("{}").'.format(self.model.__name__, obj.pk), fg='green')


class ClickUpdateObjectCommandMixin(object):

    @classmethod
    def add_update_click_command(cls, command_group):
        """
        Build a fully specified click command for updating objects from what we have in our deployfish.yml file, and add
        it to the click command group `command_group`.  Return the function object.

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
            click.secho(ctx.obj['adapter'].update(kwargs.pop('identifier')))
        update_object.__doc__ = """
Update attributes of an existing a new {object_name} object in AWS from what we have in our deployfish.yml file.
""".format(object_name=cls.model.__name__)

        function = print_render_exception(update_object)
        function = click.pass_context(function)
        function = click.argument('identifier')(function)
        function = command_group.command(
            'update',
            short_help='Update a {} object in AWS from configuration in deployfish.yml'.format(cls.model.__name__)
        )(function)
        return function

    @handle_model_exceptions
    def update(self, identifier, **kwargs):
        obj = self.get_object(identifier, factory_kwargs=self.factory_kwargs.get('update', {}))
        obj.save()
        return click.style('Updated {}("{}"):'.format(self.model.__name__, obj.pk), fg='cyan')


class ClickDeleteObjectCommandMixin(object):

    @classmethod
    def add_delete_click_command(cls, command_group):
        """
        Build a fully specified click command for deleting objects, and add it to the click command group
        `command_group`.  Return the function object.

        If the model's manager is ReadOnly, raise an exception if someone tries to add this command.

        :param command_group function: the click command group function to use to register our click command

        :rtype: function
        """
        if cls.model.config_section is None:
            raise cls.ReadOnly(
                '{} objects are read only. If you want them to be read/write, define the '
                '"config_section" class attribute on the model to be the section in deployfish.yml '
                'where configuration info can be found for them.'
            )

        def delete_object(ctx, *args, **kwargs):
            try:
                ctx.obj['config'] = get_config(**ctx.obj)
            except ConfigProcessingFailed as e:
                raise RenderException(str(e))
            ctx.obj['adapter'] = cls()
            click.secho(ctx.obj['adapter'].delete(kwargs['identifier']))
        delete_object.__doc__ = """
Delete an existing {object_name} object in AWS.

IDENTIFIER is a string that looks like one of:

    * {object_name}.name

    * {object_name}.environment

""".format(object_name=cls.model.__name__)

        function = print_render_exception(delete_object)
        function = click.pass_context(function)
        function = click.argument('identifier')(function)
        function = command_group.command(
            'delete',
            short_help='Delete a {} object in AWS'.format(cls.model.__name__)
        )(function)
        return function

    def delete_waiter(self, obj, **kwargs):
        pass

    @handle_model_exceptions
    def delete(self, identifier):
        obj = self.get_object(identifier, factory_kwargs=self.factory_kwargs.get('delete', {}))
        obj.reload_from_db()
        click.secho('\nDeleting {}("{}")\n'.format(self.model.__name__, identifier), fg='red')
        renderer = TemplateRenderer()
        click.secho(renderer.render(obj, style='short'))
        click.echo("\nIf you really want to do this, answer \"{}\" to the question below.\n".format(obj.name))
        value = click.prompt("What {} do you want to delete? ".format(self.model.__name__))
        if value == obj.name:
            obj.delete()
        self.delete_waiter(obj)
        return click.style('Deleted {}("{}")'.format(self.model.__name__, identifier), fg='cyan')

# Networking

class GetSSHTargetMixin(object):

    def get_ssh_target(self, obj, choose=False):
        target = None
        if choose:
            if obj.ssh_targets:
                rows = []
                click.secho('\nAvailable ssh targets:', fg='green')
                click.secho('----------------------\n', fg='green')
                for i, target in enumerate(obj.ssh_targets):
                    rows.append([
                        i + 1,
                        click.style(target.tags['Name'], fg='cyan'),
                        target.pk,
                        target.ip_address
                    ])
                click.secho(tabulate(rows, headers=['#', 'Name', 'Instance Id', 'IP']))
                choice = click.prompt('\nEnter the number of the instance you want: ', type=int, default=1)
                target = obj.ssh_targets[choice - 1]
        else:
            target = obj.ssh_target
        if not target:
            raise self.RenderException(
                '{}(pk="{}") has no instances available'.format(self.model.__class__, obj.pk)
            )
        return target


class GetExecTargetMixin(object):

    def get_exec_target(self, obj, choose=False):
        target = None
        container_name = None
        if choose:
            if obj.ssh_targets:
                rows = []
                click.secho('\nAvailable exec targets:', fg='green')
                click.secho('----------------------\n', fg='green')
                number = 1
                choices = []
                for target in obj.ssh_targets:
                    for container_name in obj.container_names:
                        rows.append([
                            number,
                            click.style(target.tags['Name'], fg='cyan'),
                            click.style(container_name, fg='yellow'),
                            target.pk,
                            target.ip_address
                        ])
                        choices.append((target, container_name))
                        number += 1
                click.secho(tabulate(rows, headers=['#', 'Instance', 'Container', 'Instance Id', 'IP']))
                choice = click.prompt('\nEnter the number of the instance you want: ', type=int, default=1)
                target, container_name = choices[choice - 1]
        else:
            target = obj.ssh_target
            container_name = obj.container_name
        if target is None:
            raise self.RenderException(
                '{}(pk="{}") has no instances available'.format(self.model.__class__, obj.pk)
            )
        return target, container_name


class ClickSSHObjectCommandMixin(object):

    @classmethod
    def add_ssh_click_command(cls, command_group):
        """
        Build a fully specified click command for sshing into instances, and add it to the click command group
        `command_group`.  Return the function object.

        :param command_group function: the click command group function to use to register our click command

        :rtype: function
        """
        def ssh_object(ctx, *args, **kwargs):
            if cls.model.config_section is not None:
                try:
                    ctx.obj['config'] = get_config(**ctx.obj)
                except ConfigProcessingFailed:
                    pass
            ctx.obj['adapter'] = cls()
            ctx.obj['adapter'].ssh(kwargs['identifier'], kwargs['choose'], kwargs['verbose'])
        pk_description = cls.get_pk_description()
        ssh_object.__doc__ = """
SSH to an existing {object_name} in AWS.

{pk_description}
""".format(pk_description=pk_description, object_name=cls.model.__name__)

        function = print_render_exception(ssh_object)
        function = click.pass_context(function)
        function = click.option(
            '--verbose/--no-verbose',
            '-v',
            default=False,
            help="Show all SSH output."
        )(function)
        function = click.option(
            '--choose/--no-choose',
            '-v',
            default=False,
            help="Choose from all available targets for ssh, instead of having one chosen automatically."
        )(function)
        function = click.argument('identifier')(function)
        function = command_group.command(
            'ssh',
            short_help='SSH to a {} in AWS'.format(cls.model.__name__)
        )(function)
        return function

    @handle_model_exceptions
    def ssh(self, identifier, choose, verbose):
        obj = self.get_object(
            identifier,
            needs_config=False,
            factory_kwargs=self.factory_kwargs.get('ssh', {})
        )
        target = self.get_ssh_target(obj, choose=choose)
        target.ssh_interactive(verbose=verbose)


class ClickExecObjectCommandMixin(object):

    @classmethod
    def add_exec_click_command(cls, command_group):
        """
        Build a fully specified click command for execing into containers in tasks, and add it to the click command
        group `command_group`.  Return the function object.

        :param command_group function: the click command group function to use to register our click command

        :rtype: function
        """
        def exec_object(ctx, *args, **kwargs):
            if cls.model.config_section is not None:
                try:
                    ctx.obj['config'] = get_config(**ctx.obj)
                except ConfigProcessingFailed:
                    pass
            ctx.obj['adapter'] = cls()
            ctx.obj['adapter'].exec(kwargs['identifier'], kwargs['choose'], kwargs['verbose'])
        pk_description = cls.get_pk_description()
        exec_object.__doc__ = """
Exec into a container in a {object_name} in AWS.

{pk_description}
""".format(pk_description=pk_description, object_name=cls.model.__name__)

        function = print_render_exception(exec_object)
        function = click.pass_context(function)
        function = click.option(
            '--verbose/--no-verbose',
            '-v',
            default=False,
            help="Show all SSH output."
        )(function)
        function = click.option(
            '--choose/--no-choose',
            '-v',
            default=False,
            help='Choose from all available targets for "docker exec", instead of having one chosen automatically.'
        )(function)
        function = click.argument('identifier')(function)
        function = command_group.command(
            'exec',
            short_help='Exec into a container in AWS'.format(cls.model.__name__)
        )(function)
        return function

    @handle_model_exceptions
    def exec(self, identifier, choose, verbose):
        obj = self.get_object(
            identifier,
            needs_config=False,
            factory_kwargs=self.factory_kwargs.get('exec', {})
        )
        target, container_name = self.get_exec_target(obj, choose=choose)
        obj.docker_exec(ssh_target=target, container_name=container_name, verbose=verbose)


class ClickTunnelObjectCommandMixin(object):

    @classmethod
    def add_tunnel_click_command(cls, command_group):
        """
        Build a fully specified click command for setting up an SSH tunnel through an instances to another service in
        AWS, and add it to the click command group `command_group`.  Return the function object.

        :param command_group function: the click command group function to use to register our click command

        :rtype: function
        """
        def tunnel_object(ctx, *args, **kwargs):
            if cls.model.config_section is not None:
                try:
                    ctx.obj['config'] = get_config(**ctx.obj)
                except ConfigProcessingFailed:
                    pass
            ctx.obj['adapter'] = cls()
            ctx.obj['adapter'].tunnel(
                kwargs['identifier'],
                kwargs['choose'],
                kwargs.get('local_port', None),
                kwargs.get('host', None),
                kwargs.get('host_port', None),
                kwargs['verbose'],
            )
        pk_description = cls.get_pk_description()
        tunnel_object.__doc__ = """
Create an SSH tunnel through an instance related to a {object_name}.

{pk_description}
""".format(pk_description=pk_description, object_name=cls.model.__name__)

        function = print_render_exception(tunnel_object)
        function = click.pass_context(function)
        function = click.option(
            '--verbose/--no-verbose',
            '-v',
            default=False,
            help="Show all SSH output."
        )(function)
        function = click.option(
            '--choose/--no-choose',
            '-v',
            default=False,
            help="Choose from all available targets for ssh, instead of having one chosen automatically."
        )(function)
        if cls.model != SSHTunnel:
            function = click.option(
                '--local-port',
                '-L',
                default=8888,
                help="For ad-hoc tunnels, set the port number for your end of the tunnel"
            )(function)
            function = click.option(
                '--host',
                '-h',
                default=None,
                help="For ad-hoc tunnels, set the hostname or IP address for the target host at the far end of "
                     "the tunnel."
            )(function)
            function = click.option(
                '--host-port',
                '-h',
                default=None,
                help="For ad-hoc tunnels, set the port number to connect to on the target host at the far end "
                     "of the tunnel."
            )(function)
            function = click.argument('identifier', nargs=-1)(function)
        else:
            function = click.argument('identifier')(function)
        function = command_group.command(
            'tunnel',
            short_help='Create an SSH tunnel through an instance related to a {}'.format(cls.model.__name__)
        )(function)
        return function

    @handle_model_exceptions
    def tunnel(self, identifier, choose, local_port, host, host_port, verbose):
        """
        Establish an SSH tunnel from our machine through a Service instance to a host:port in AWS.

        This is designed to be a multi-homed command so that we can put it at the top level:

            deploy tunnel TUNNEL_NAME

        or under the service group:

            deploy service tunnel SERVICE_NAME TUNNEL_NAME
            deploy service tunnel SERVICE_NAME --local-port=8888 --host=10.2.0.1 --host-port=3306


        Three cases here:

            * We're a command under the `service` command group
              * In this case, identifier is a list with either one or entries
                * If only one entry, that entry is the service name, and we expect the local_port, host and host_port
                  arguments to be defined.
                * If two entries, the first is the service name, and the second is the tunnel name.  We expect
                  local_port, host and host_port to be None
            * We're under the top level `cli` command group
                * In this case, the identifier is a tunnel name, and local_port, host, and host_port are always None.

        :param identifier Union[list(str), str]: either a SERVICE_NAME, TUNNEL_NAME pair, or either SERVICE_NAME
                                                  or TUNNEL_NAME
        :param choose bool: if True, present a list of instances available for tunneling through
        :param local_port int: (optional) the local port to bind our end of the tunnel to
        :param host int: (optional) the host in AWS on the other end of the tunnel
        :param host_port int: (optional) the port on `host` on the other end of the tunnel
        """
        if isinstance(identifier, tuple):
            # We're a command under the `service` command group.
            if identifier:
                object_name = identifier[0]
                tunnel_name = None
                obj = self.get_object(
                    object_name,
                    needs_config=False,
                    factory_kwargs=self.factory_kwargs.get('tunnel', {})
                )
                if len(identifier) > 1:
                    tunnel_name = identifier[1]
                    try:
                        tunnel = obj.ssh_tunnels[tunnel_name]
                    except KeyError:
                        raise RenderException(
                            '{}(pk="{}") has no associated tunnel named "{}"'.format(
                                self.model.__name__,
                                obj.pk,
                                tunnel_name
                            )
                        )
                    except ConfigProcessingFailed as e:
                        raise RenderException(str(e))
                else:
                    if (local_port is None or host is None or host_port is None):
                        raise RenderException(
                            'Either supply the name of a tunnel associated with this {}, or use the --local-port, --host and --host-port flags.'.format(self.model.__name__)  # noqa:E501
                        )
                    obj = self.get_object(
                        object_name,
                        needs_config=False,
                        factory_kwargs=self.factory_kwargs.get('tunnel', {})
                    )
                    tunnel = SSHTunnel({
                        'name': '{}-{}'.format(object_name, host),
                        'service': object_name,
                        'local_port': local_port,
                        'host': host,
                        'port': host_port
                    })
            else:
                raise RenderException('For tunneling, enter at least SERVICE_NAME as the command argument.')
        else:
            # We're a command under the `cli` command group.
            tunnel = self.get_object(identifier)
        if choose:
            target = self.choose_ssh_target(tunnel)
        else:
            target = obj.ssh_target
        target.tunnel(tunnel, verbose=verbose)

# Secrets

class ClickObjectSecretsShowCommandMixin(object):

    show_secrets_ordering = 'Name'
    show_secrets_columns = {
        'Name': 'secret_name',
        'Value': 'value',
        'Encrypted?': 'is_secure',
        'Modified': 'LastModifiedDate',
        'Modified By': 'modified_username'
    }
    show_secrets_renderer_classes = {
        'template': TemplateRenderer,
        'table': TableRenderer,
        'json': JSONRenderer,
    }

    @classmethod
    def show_secrets_display_option_kwargs(cls):
        """
        Return the appropriate kwargs for `click.option('--display', **kwargs)` for the renderer options we've defined
        for the show_secrets command.

        :rtype: dict
        """
        render_types = list(cls.show_secrets_renderer_classes.keys())
        default = render_types[0]
        kwargs = {
            'type': click.Choice(render_types),
            'default': default,
            'help': "Choose how to display secrets for a {} object. Choices: {}.  Default: {}.".format(
                cls.model.__name__,
                ', '.join(render_types),
                default
            )
        }
        return kwargs

    @classmethod
    def add_show_secrets_command(cls, command_group):
        """
        Build a fully specified click command for retrieving secrets from AWS SSM Paramter store and
        displaying their values.

        :param command_group function: the click command group function to use to register our click command

        :rtype: function
        """
        def show_secrets(ctx, *args, **kwargs):
            if cls.model.config_section is not None:
                try:
                    ctx.obj['config'] = get_config(**ctx.obj)
                except ConfigProcessingFailed:
                    pass
            ctx.obj['adapter'] = cls()
            click.secho(ctx.obj['adapter'].show_secrets(kwargs['identifier'], kwargs['display']))
        pk_description = cls.get_pk_description()
        show_secrets.__doc__ = """
Show the AWS SSM Parameter Store secrets associated with a {object_name}.

{pk_description}
""".format(pk_description=pk_description, object_name=cls.model.__name__)

        function = print_render_exception(show_secrets)
        function = click.pass_context(function)
        function = click.option('--display', **cls.show_secrets_display_option_kwargs())(function)
        function = click.argument('identifier')(function)
        function = command_group.command(
            'show',
            short_help='Show AWS SSM Parameter Store secrets for a {}'.format(cls.model.__name__)
        )(function)
        return function

    @handle_model_exceptions
    def show_secrets(self, identifier, display):
        assert display in self.show_secrets_renderer_classes, \
            '{}.show_secrets(): "{}" is not a valid rendering option'.format(
                self.__class__.__name__,
                display
            )
        obj = self.get_object(identifier, needs_config=False)
        obj.reload_secrets()
        click.secho(
            'Live values for AWS SSM Parameter store secrets for {}(pk="{}"):'.format(
                self.model.__name__,
                obj.pk
            )
        )
        if display == 'table':
            results = self.show_secrets_renderer_classes[display](
                self.show_secrets_columns,
                ordering=self.show_secrets_ordering
            ).render(obj.secrets.values())
        elif display == 'template':
            results = self.show_secrets_renderer_classes[display]().render(obj.secrets, template='secrets--detail.tpl')
        else:
            results = self.show_secrets_renderer_classes[display]().render([s.data for s in obj.secrets.values()])
        return '\n' + results + '\n'


class ClickObjectSecretsWriteCommandMixin(object):

    @classmethod
    def add_write_secrets_command(cls, command_group):
        """
        Build a fully specified click command for writing secrets to AWS SSM Paramter store using their values
        from deployfish.yml.

        :param command_group function: the click command group function to use to register our click command

        :rtype: function
        """
        def write_secrets(ctx, *args, **kwargs):
            ctx.obj['config'] = get_config(**ctx.obj)
            ctx.obj['adapter'] = cls()
            click.secho(ctx.obj['adapter'].write_secrets(kwargs['identifier']))

        pk_description = cls.get_pk_description()
        write_secrets.__doc__ = """
Write the AWS SSM Parameter Store secrets associated with a {object_name} to AWS.

{pk_description}
""".format(
            pk_description=pk_description,
            object_name=cls.model.__name__
        )

        function = print_render_exception(write_secrets)
        function = click.pass_context(function)
        function = click.argument('identifier')(function)
        function = command_group.command(
            'write',
            short_help='Write AWS SSM Parameter Store secrets for a {} to AWS'.format(cls.model.__name__)
        )(function)
        return function

    @handle_model_exceptions
    def write_secrets(self, identifier):
        obj = self.get_object(identifier)
        click.secho(
            '\nWriting secrets for {}(pk="{}") to AWS Parameter Store ...'.format(self.model.__name__, obj.pk),
            nl=False
        )
        obj.write_secrets()
        click.secho(' done.\n\n')
        obj.reload_secrets()
        click.secho(
            'Live values for AWS SSM Parameter store secrets for {}(pk="{}"):'.format(
                self.model.__name__,
                obj.pk
            ),
            fg='green'
        )
        return TemplateRenderer().render(obj.secrets, template='secrets--detail.tpl')


class ClickObjectSecretsDiffCommandMixin(object):

    @classmethod
    def add_diff_secrets_command(cls, command_group):
        """
        Build a fully specified click command for diffing secrets between from AWS SSM Paramter store and
        and deployfish.yml.

        :param command_group function: the click command group function to use to register our click command

        :rtype: function
        """
        def diff_secrets(ctx, *args, **kwargs):
            ctx.obj['config'] = get_config(**ctx.obj)
            ctx.obj['adapter'] = cls()
            click.secho(ctx.obj['adapter'].diff_secrets(kwargs['identifier']))

        pk_description = cls.get_pk_description()
        diff_secrets.__doc__ = """
Diff the AWS SSM Parameter Store secrets vs their counterparts in deployfish.yml.

{pk_description}
""".format(
            pk_description=pk_description,
            object_name=cls.model.__name__
        )

        function = print_render_exception(diff_secrets)
        function = click.pass_context(function)
        function = click.argument('identifier')(function)
        function = command_group.command(
            'diff',
            short_help='Diff AWS SSM Parameter Store secrets vs those in deployfish.yml for a {}'.format(
                cls.model.__name__
            )
        )(function)
        return function

    @handle_model_exceptions
    def diff_secrets(self, identifier):
        """
        Show the difference between the secrets we have in our deployfish.yml file and what is in AWS.
        """
        obj = self.get_object(identifier)
        other = Secret.objects.list(obj.secrets_prefix)
        title = '\nDiffing secrets for {}(pk="{}"):'.format(self.model.__name__, obj.pk)
        click.echo(title)
        click.echo("=" * len(title))
        return TemplateRenderer().render(obj.diff_secrets(other), template='secrets--diff.tpl')


# ====================
# Adapters
# ====================

class ClickBaseModelAdapter(object):

    class DeployfishObjectDoesNotExist(ObjectDoesNotExist):

        def __init__(self, msg, section, name):
            self.msg = msg
            self.section = section
            self.name = name

    class ObjectNotManaged(Exception):
        pass

    class ReadOnly(ObjectReadOnly):
        pass

    model = None
    factory_kwargs = {}

    # Renderers
    datetime_format = None
    date_format = None
    float_precision = None

    @classmethod
    def add_command_group(cls, parent, name=None, short_help=None):
        """
        Build the command group for our commands for this model.

        If `cls.model.config_section` is not None, this means that we use deployfish.yml to configure this kind of
        object. Ensure the deployfish.config.Config object is constructed properly.

        :param parent click.group: the click group that should be the parent to this group
        :param name str: (optional) the name for this group.  Default: the lower-cased model name.
        :param short_help str: (optional) the short_help for this group.

        :rtype: function
        """
        def cmdgroup(ctx):
            pass

        cmdgroup = click.pass_context(cmdgroup)
        if not name:
            name = cls.model.__name__.lower()
        if not short_help:
            if cls.model.config_section is not None:
                verb = 'Manage'
            else:
                verb = 'Describe'
            short_help = '{} {} objects in AWS'.format(verb, cls.model.__name__)
        cmdgroup = parent.group(name=name, short_help=short_help)(cmdgroup)
        return cmdgroup

    @classmethod
    def add_argument(cls, name, arg, function):
        arg_type = arg['type']
        if arg_type == 'datetime':
            click_type = click.DateTime()
        else:
            click_type = arg_type
        help_str = None
        if 'specs' in arg:
            formats = ['"{}"'.format(spec) for spec in arg['specs']]
            help_str = "Acceptible formats: {}".format(', '.join(formats))
        function = click.argument(name, type=click_type, help=help_str)(function)
        return function

    @classmethod
    def add_option(cls, name, kwarg, function):
        option = "--{}".format(name.replace('_', '-'))
        arg_type = kwarg['type']
        if arg_type == 'datetime':
            click_type = click.DateTime()
        else:
            click_type = arg_type
        help_str = "Filter results by {}".format(name)
        if 'specs' in kwarg:
            formats = ['"{}"'.format(spec) for spec in kwarg['specs']]
            help_str += ". Acceptible value formats: {}".format(', '.join(formats))
        if 'multiple' in kwarg and kwarg['multiple']:
            option_kwargs = {
                'default': [kwarg['default']],
                'help': help_str,
                'multiple': True,
            }
        else:
            option_kwargs = {
                'default': kwarg['default'],
                'help': help_str
            }
        if not isinstance(click_type, str):
            option_kwargs['type'] = click_type
        function = click.option(option, **option_kwargs)(function)
        return function

    @classmethod
    def get_required_args(cls, args):
        required_args = " ".join([arg.upper() for arg in args.keys()])
        if required_args:
            required_args += " "
        return required_args

    @classmethod
    def get_pk_description(cls):
        args, kwargs = FunctionTypeCommentParser().parse(cls.model.objects.get)
        pk_description = ''
        pk_description = "IDENTIFIER is a string that looks like one of:\n\n"
        if 'specs' in args['pk']:
            if len(args['pk']['specs']) > 1:
                pk_description += " one of:\n\n"
                for spec in args['pk']['specs']:
                    pk_description += '    * {}\n\n'.format(spec)
            else:
                pk_description += '    * {}\n\n'.format(args['pk']['specs'][0])
            pk_description += "    * {}.name\n\n".format(cls.model.__name__)
            pk_description += "    * {}.environment\n\n".format(cls.model.__name__)
        return pk_description

    def __init__(self):
        assert self.model is not None, \
            '{}: please set the model class attribute'.format(
                self.__class__.__name__
            )

    def get_object(self, identifier, needs_config=True, failure_message=None, factory_kwargs=None):
        if not failure_message:
            failure_message = '{object_name}.name and {object_name}.environment identifiers cannot be used.'.format(
                object_name=self.model.__name__
            )
        obj = None
        if self.model.config_section is not None:
            try:
                obj = self.factory(identifier, factory_kwargs)
            except ConfigProcessingFailed as e:
                if needs_config:
                    raise RenderException(str(e))
                else:
                    lines = []
                    lines.append(click.style('WARNING: {}'.format(str(e)), fg='yellow'))
                    lines.append(click.style(failure_message, fg='yellow'))
                    click.secho('\n'.join(lines))
        if not obj:
            try:
                obj = self.model.objects.get(identifier)
            except self.model.DoesNotExist as e:
                raise RenderException(str(e))
        return obj

    def factory(self, identifier, factory_kwargs):
        if not factory_kwargs:
            factory_kwargs = {}
        config = get_config()
        if self.model.config_section:
            try:
                data = config.get_section_item(self.model.config_section, identifier)
                return self.model.new(data, 'deployfish', **factory_kwargs)
            except KeyError:
                raise self.DeployfishObjectDoesNotExist(
                    'Could not find a {} named "{}" in deployfish.yml\n'.format(self.model.__name__, identifier)
                )
        else:
            raise self.ObjectNotManaged(
                'deployfish.yml does not manage objects of class {}'.format(self.model.__class__)
            )

    def wait(self, operation, **kwargs):
        waiter = self.model.objects.get_waiter(operation)
        waiter.wait(**kwargs)


class ClickReadOnlyModelAdapter(
    GetSSHTargetMixin,
    GetExecTargetMixin,
    ClickListObjectsCommandMixin,
    ClickObjectInfoCommandMixin,
    ClickObjectExistsCommandMixin,
    ClickSSHObjectCommandMixin,
    ClickTunnelObjectCommandMixin,
    ClickBaseModelAdapter,
):
    pass


class ClickModelAdapter(
    GetSSHTargetMixin,
    GetExecTargetMixin,
    ClickListObjectsCommandMixin,
    ClickObjectInfoCommandMixin,
    ClickObjectExistsCommandMixin,
    ClickCreateObjectCommandMixin,
    ClickUpdateObjectCommandMixin,
    ClickDeleteObjectCommandMixin,
    ClickSSHObjectCommandMixin,
    ClickExecObjectCommandMixin,
    ClickTunnelObjectCommandMixin,
    ClickBaseModelAdapter,
):
    pass


class ClickSecretsAdapter(
    ClickObjectSecretsDiffCommandMixin,
    ClickObjectSecretsShowCommandMixin,
    ClickObjectSecretsWriteCommandMixin,
    ClickBaseModelAdapter,
):

    @classmethod
    def add_command_group(cls, parent, name=None, short_help=None):
        if not short_help:
            short_help = "Manage AWS SSM Parameter Store secrets for a {}".format(cls.model.__name__)
        return super(ClickSecretsAdapter, cls).add_command_group(parent, name=name, short_help=short_help)
