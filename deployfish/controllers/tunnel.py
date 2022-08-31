from typing import  Dict, Any, Optional, Type

from cement import ex, shell
import click
from tabulate import tabulate
from deployfish.controllers.crud import ReadOnlyCrudBase
from deployfish.controllers.utils import handle_model_exceptions

from deployfish.core.loaders import ObjectLoader
from deployfish.core.models import Model, Instance, SSHTunnel
from deployfish.ext.ext_df_argparse import DeployfishArgparseController as Controller
from deployfish.types import SupportsTunnelModel

def get_tunnel_target(obj: SupportsTunnelModel, choose: bool = False) -> Instance:
    """
    Return an ``Instance`` object through which the user can make an ssh tunnel.

    If ``choose`` is ``False``, return the first `Instance`` of the
    available tunnel targets for ``obj``.

    If ``choose`` is ``True``, prompt the user to choose one of the
    available tunnel targets for this object.

    Args:
        obj: an instance of ``self.model``

    Keyword Arguments:
        choose: if ``True``, prompt the user to choose one of the available instances

    Raises:
        Instance.DoesNotExist: if there are no available ssh targets

    Returns:
        An Instance object.
    """
    target = None
    if choose:
        if obj.tunnel_targets:
            rows = []
            click.secho('\nAvailable tunnel targets:', fg='green')
            click.secho('--------------------------\n', fg='green')
            for i, target in enumerate(obj.tunnel_targets):
                rows.append([
                    i + 1,
                    click.style(target.name, fg='cyan'),
                    target.pk,
                    target.ip_address
                ])
            click.secho(tabulate(rows, headers=['#', 'Name', 'Instance Id', 'IP']))
            p = shell.Prompt('\nEnter the number of the instance you want: ', type=int, default=1)
            choice = p.prompt()
            target = obj.tunnel_targets[choice - 1]
    else:
        target = obj.tunnel_target
    if not target:
        raise Instance.DoesNotExist(f'{obj.__class__.__name__}(pk="{obj.pk}") has no tunnel targets available')
    return target


def get_tunnel() -> Optional[SSHTunnel]:
    """
    If we didn't get a specific tunnel to use, present the user with a list of all available tunnels,
    possibly limited by what ``obj`` has access to.

    Args:
        obj: an object that has a .ssh_tunnels attribute which returns a dict of tunnels where
                the key is tunnel name and the value is an SSHTunnel object

    Returns:
        An SSHTunnel object
    """
    tunnel: Optional[SSHTunnel] = None
    tunnels = {t.name: t for t in SSHTunnel.objects.list()}
    if tunnels:
        rows = []
        click.secho('\nAvailable tunnels:', fg='green')
        click.secho('-------------------\n', fg='green')
        for i, name in enumerate(tunnels):
            entry = tunnels[name]
            rows.append([
                i + 1,
                click.style(entry.name, fg='cyan'),
                entry.host,
                entry.host_port,
                entry.local_port
            ])
        click.secho(tabulate(rows, headers=['#', 'Name', 'Target', 'Target Port', 'Local Port']))
        choice = click.prompt('\nEnter the number of the tunnel you want: ', type=int, default=1)
        tunnel = tunnels[list(tunnels)[choice - 1]]
    return tunnel


def establish_tunnel(
    tunnel: SSHTunnel,
    obj: SupportsTunnelModel,
    choose: bool = False,
    verbose: bool = False
) -> None:
    """
    Actually establish an SSH Tunnel.  This does not return until the user
    manually terminates the tunnel or until the tunnel itself dies.

    Args:
        tunnel: the SSHTunnel configuration (local_port, host, host_port)
        obj: A ``Model`` object that supports tunneling

    Keyword Arguments:
        choose: if ``True``, prompt the user to choose which instance to tunnel through
        verbose: if ``True``, use verbose flags with ``ssh``

    Raises:
        Instance.DoesNotExist: if we can't find an instance to tunnel through or
            if we are configured to use a bastion host and we can't find one.
    """
    if choose:
        target: Optional[Instance] = get_tunnel_target(obj)
    else:
        target = obj.tunnel_target
    if not target:
        raise Instance.DoesNotExist("Couldn't find an instance to tunnel through.")
    click.secho('\nEstablishing tunnel: {}:{} -> localhost:{}'.format(
        tunnel.host,
        tunnel.host_port,
        tunnel.local_port
    ), fg='yellow')
    if obj.ssh_proxy_type == 'bastion':
        bastion = target.bastion
        if bastion:
            click.secho('{}: {}'.format(
                click.style('bastion host', fg='red', bold=True),
                bastion.hostname,
            ), fg='cyan')
        else:
            raise Instance.DoesNotExist(
                'Current SSH settings require a bastion host, but no bastion host exists in the VPC.'
            )
    click.secho('{}: {} ({})\n'.format(
        click.style('intermediate host', fg='magenta', bold=True),
        target.name,
        target.ip_address,
    ), fg='cyan')
    obj.tunnel(tunnel, verbose=verbose, tunnel_target=target)


class BaseTunnel(Controller):

    class Meta:
        label = 'base-tunnel'
        description = "Establish an ssh tunnel"
        help = "Establish an ssh tunnel"
        stacked_on = "base"
        stacked_type = "embedded"

    model: Type[Model] = SSHTunnel
    loader: Type[ObjectLoader] = ObjectLoader

    @ex(
        help="Establish an ssh tunnel.",
        arguments=[
            (['tunnel_name'], {
                'help': 'The "name" for the tunnel in deployfish.yml',
                'nargs': '?',
                'default': None
            }),
            (
                ["--verbose"],
                {
                    'help': 'Show all SSH output',
                    'default': False,
                    'action': 'store_true',
                    'dest': 'verbose'
                }
            ),
            (
                ["--choose"],
                {
                    'help': 'Choose from all available targets for ssh, instead of having one chosen automatically.',
                    'default': False,
                    'action': 'store_true',
                    'dest': 'choose'
                }
            ),
        ]
    )
    def tunnel(self):
        """
        Establish an SSH tunnel from our machine through an instance to a host:port in AWS.
        """
        # We have to do this bit here to load the deployfish.config.Config
        # object so that SSHTunnelManager can get to it later.
        _ = self.app.deployfish_config
        if self.app.pargs.tunnel_name:
            loader = self.loader(self)
            tunnel = loader.get_object_from_deployfish(self.app.pargs.tunnel_name)
        else:
            tunnel = get_tunnel()
        obj = tunnel.service
        establish_tunnel(tunnel, obj, choose=self.app.pargs.choose, verbose=self.app.pargs.verbose)


class ObjectTunnelController(Controller):

    class Meta:
        label = 'tunnel-base'

    model: Type[Model] = Model
    loader: Type[ObjectLoader] = ObjectLoader

    @ex(
        help="Establish an ssh tunnel.",
        arguments=[
            (['pk'], { 'help' : 'The primary key for the object in AWS'}),
            (['tunnel_name'], { 'help' : 'The name of the tunnel to use'}),
            (
                ["--verbose"],
                {
                    'help': 'Show all SSH output',
                    'default': False,
                    'action': 'store_true',
                    'dest': 'verbose'
                }
            ),
            (
                ["--choose"],
                {
                    'help': 'Choose from all available targets for ssh, instead of having one chosen automatically.',
                    'default': False,
                    'action': 'store_true',
                    'dest': 'choose'
                }
            ),
        ]
    )
    @handle_model_exceptions
    def tunnel(self):
        """
        Establish an SSH tunnel from our machine through an instance to a host:port in AWS.
        """
        loader = self.loader(self)
        obj = loader.get_object_from_deployfish(self.app.pargs.pk)
        try:
            tunnel = obj.ssh_tunnels[self.app.pargs.tunnel_name]
        except KeyError:
            raise SSHTunnel.DoesNotExist(
                f'{self.model.__name__}(pk="{obj.pk}") has no associated tunnel named "{self.app.pargs.tunnel_name}"'
            )
        establish_tunnel(tunnel, obj, choose=self.app.pargs.choose, verbose=self.app.pargs.verbose)


class Tunnels(ReadOnlyCrudBase):

    class Meta:
        label = 'tunnels'
        description = 'Work with SSH Tunnel objects'
        help = 'Work with SSH Tunnel objects'
        stacked_type = 'nested'

    model: Type[Model] = SSHTunnel

    info_template: str = 'detail--sshtunnel.jinja2'

    list_ordering: str = 'Name'
    list_result_columns: Dict[str, Any] = {
        'Name': 'name',
        'Service': 'service__name',
        'Cluster': 'cluster__name',
        'Local Port': 'local_port',
        'Host': 'host',
        'Host Port': 'host_port'
    }

    @ex(
        help="List available SSH Tunnels",
        arguments=[
            (
                ['--service-name'],
                {
                    'help': 'Filter by service name',
                    'action': 'store',
                    'default': None,
                    'dest': 'service_name'
                }
            ),
            (
                ['--port'],
                {
                    'help': 'Filter by port.',
                    'action': 'store',
                    'default': None,
                    'dest': 'port'
                }
            ),
        ]
    )
    @handle_model_exceptions
    def list(self):
        results = self.model.objects.list(
            service_name=self.app.pargs.service_name,
            port=self.app.pargs.port,
        )
        self.render_list(results)
