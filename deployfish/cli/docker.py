"""
Command group: No group; miscellaneous top level commands related to networking.

This file contains commands that allow SSHing to individual ECS container instances, tunneling to resources in AWS (e.g.
RDS servers, LDAP servers, etc.) and exec'ing into containers.

.. note::

    This is ONLY for ECS services that run on EC2, not on FARGATE.  You can't currently exec into FARGATE containers.
"""
import click

from ..config import needs_config
from ..ssh import SSHConfig

from .cli import cli
from .misc import FriendlyServiceFactory


@cli.command('ssh', short_help="Connect to an ECS cluster machine")
@click.argument('service_name')
@click.option('--verbose/--no-verbose', '-v', default=False, help="Show all SSH output.")
@click.pass_context
@needs_config
def ssh(ctx, service_name, verbose):
    """
    If the service SERVICE_NAME has any running tasks, randomly choose one of
    the container instances on which one of those tasks is running and ssh into
    it.

    If the service SERVICE_NAME has no running tasks, randomly choose one of
    the container instances in the cluster on which the service is defined.
    """
    service = FriendlyServiceFactory.new(service_name, config=ctx.obj['CONFIG'])
    ssh = SSHConfig(service, config=ctx.obj['CONFIG']).get_ssh()
    ssh.ssh(verbose=verbose)


@cli.command('exec', short_help="Connect to a running container")
@click.argument('service_name')
@click.option('--verbose/--no-verbose', '-v', default=False, help="Show all SSH output.")
@click.pass_context
@needs_config
def docker_exec(ctx, service_name, verbose):
    """
    SSH to an EC2 instance in the cluster defined in the service named SERVICE_NAME, then
    run docker exec on the appropriate container.
    """
    service = FriendlyServiceFactory.new(service_name, config=ctx.obj['CONFIG'])
    ssh = SSHConfig(service, config=ctx.obj['CONFIG']).get_ssh()
    ssh.docker_exec(verbose=verbose)


def _interpolate_tunnel_info(value, service):
    if type(value) == str and value.startswith('config.'):
        param_key = value[7:]
        for param in service.get_config():
            if param.key == param_key:
                try:
                    return param.aws_value
                except ValueError:
                    return param.value
    return value


@cli.command('tunnel', short_help="Tunnel through an ECS cluster machine to the remote host")
@click.argument('tunnel_name')
@click.option('--verbose/--no-verbose', '-v', default=False, help="Show all SSH output.")
@click.pass_context
@needs_config
def tunnel(ctx, tunnel_name, verbose):
    """
    Tunnel through an EC2 instance in the ECS cluster.

    The parameters for this command should be found in a tunnels: top-level section in the yaml file, in the format:

    \b
    tunnels:
      - name: my_tunnel
        service: my_service
        host: config.MY_TUNNEL_DESTINATION_HOST
        port: 3306
        local_port: 8888

    where config.MY_TUNNEL_DESTINATION_HOST is the value of MY_TUNNEL_DESTINATION_HOST
    for this service in the AWS Parameter Store. The host value could also just
    be a hostname.

    """
    config = ctx.obj['CONFIG']
    yml = config.get_section_item('tunnels', tunnel_name)
    service_name = yml['service']

    service = FriendlyServiceFactory.new(service_name, config=config)
    host = _interpolate_tunnel_info(yml['host'], service)
    port = int(_interpolate_tunnel_info(yml['port'], service))
    local_port = int(_interpolate_tunnel_info(yml['local_port'], service))

    ssh = SSHConfig(service, config=config).get_ssh()

    ssh.tunnel(host, local_port, port, verbose=verbose)
