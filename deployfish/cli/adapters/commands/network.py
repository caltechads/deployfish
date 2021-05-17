import click
from tabulate import tabulate

from deployfish.config import get_config
from deployfish.exceptions import RenderException, ConfigProcessingFailed
from deployfish.core.models import SSHTunnel

from deployfish.cli.adapters.utils import handle_model_exceptions, print_render_exception


# ====================
# Command mixins
# ====================


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
SSH to a container machine running one of the tasks for an existing {object_name} in AWS.

NOTE: this is only available if your {object_name} is of launch type EC2.  You cannot ssh
to the container machine of a FARGATE {object_name}.

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
        obj = self.get_object_from_aws(identifier)
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
        obj = self.get_object_from_aws(identifier)
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
Establish an SSH tunnel from your machine through an instance related to a {object_name} to a target in AWS.

You can do this in two ways:

    * Provide the name of a tunnel from the 'tunnels:' section

    * Specify an ad-hoc tunnel with the --host-port, --local-port and --host flags.  You need to specify all three flags.

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
            function = click.argument('identifier', required=False)(function)
        function = command_group.command(
            'tunnel',
            short_help='Create an SSH tunnel through an instance related to a {}'.format(cls.model.__name__)
        )(function)
        return function

    def get_tunnel(self, obj=None):
        """
        If we didn't get a specific tunnel to use, present the user with a list of all available tunnels,
        possibly limited by what ``obj`` has access to.

        :param obj Any: an object that has a .ssh_tunnels attribute which returns a dict of tunnels where
                        the key is tunnel name and the value is an SSHTunnel object

        :rtype: SSHTunnel
        """
        tunnel = None
        if obj:
            tunnels = obj.ssh_tunnels
        else:
            tunnels = {t.name: t for t in SSHTunnel.objects.list()}
        if tunnels:
            rows = []
            click.secho('\nAvailable tunnels:', fg='green')
            click.secho('-------------------\n', fg='green')
            for i, name in enumerate(tunnels):
                tunnel = tunnels[name]
                rows.append([
                    i + 1,
                    click.style(tunnel.name, fg='cyan'),
                    tunnel.host,
                    tunnel.host_port,
                    tunnel.local_port
                ])
            click.secho(tabulate(rows, headers=['#', 'Name', 'Target', 'Target Port', 'Local Port']))
            choice = click.prompt('\nEnter the number of the tunnel you want: ', type=int, default=1)
            tunnel = tunnels[list(tunnels)[choice - 1]]
        return tunnel

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
            # We're a command under the sub command group like service or cluster
            if identifier:
                object_name = identifier[0]
                tunnel_name = None
                obj = self.get_object_from_deployfish(object_name)
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
                    obj = self.get_object_from_aws(object_name)
                    if (local_port is None or host is None or host_port is None):
                        tunnel = self.get_tunnel(obj)
                    else:
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
            if identifier:
                # We're a command under the `cli` command group.
                tunnel = self.get_object_from_deployfish(identifier)
            else:
                tunnel = self.get_tunnel()
            obj = tunnel
        if choose:
            target = self.get_ssh_target(tunnel)
        else:
            target = obj.ssh_target
        click.secho('\nEstablishing tunnel: {}:{} -> localhost:{}'.format(
            tunnel.host,
            tunnel.host_port,
            tunnel.local_port
        ), fg='yellow')
        if target.ssh_proxy_type == 'bastion':
            bastion = target.bastion
            click.secho('{}: {}'.format(
                click.style('bastion host', fg='red', bold=True),
                bastion.hostname,
            ), fg='cyan')
        click.secho('{}: {} ({})\n'.format(
            click.style('intermediate host', fg='magenta', bold=True),
            target.name,
            target.ip_address,
        ), fg='cyan')
        target.tunnel(tunnel, verbose=verbose)
