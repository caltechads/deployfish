"""
Command group: deploy cluster COMMAND

This file contains the commands that act on an ECS cluster.
"""
import click

from ..config import needs_config
from ..ssh import SSHConfig

from .cli import cli
from .misc import FriendlyServiceFactory


@cli.group(short_help="Manage the AWS ECS cluster")
def cluster():
    pass


@cluster.command('info', short_help="Show info about the individual systems in the cluster")
@click.pass_context
@click.argument('service_name')
@needs_config
def cluster_info(ctx, service_name):
    """
    Show information about the individual EC2 systems in the ECS cluster running
    SERVICE_NAME.
    """
    service = FriendlyServiceFactory.new(service_name, config=ctx.obj['CONFIG'])
    instances = service.get_instance_data()
    for index, reservation in enumerate(instances):
        click.echo(click.style("Instance {}".format(index + 1), bold=True))
        instance = reservation['Instances'][0]
        print("\tInstance: {}".format(instance['InstanceId']))
        print("\tIP: {}".format(instance['PrivateIpAddress']))
        print("\tType: {}".format(instance['InstanceType']))
        for tag in instance['Tags']:
            print("\t{}: {}".format(tag['Key'], tag['Value']))
        print("")


@cluster.command('run', short_help="Run a command on the individual systems in the cluster")
@click.pass_context
@click.argument('service_name')
@needs_config
def cluster_run(ctx, service_name):
    """
    Run a command on each of the individual EC2 systems in the ECS cluster running
    SERVICE_NAME.
    """
    command = click.prompt('Command to run')
    service = FriendlyServiceFactory.new(service_name, config=ctx.obj['CONFIG'])
    ssh = SSHConfig(service, config=ctx.obj['CONFIG']).get_ssh()
    responses = ssh.cluster_run([command])
    for index, response in enumerate(responses):
        click.echo(click.style("Instance {}".format(index + 1), bold=True))
        click.echo("Success: {}".format(response[0]))
        click.echo(response[1])


@cluster.command('ssh', short_help="SSH to individual systems in the cluster")
@click.pass_context
@click.argument('service_name')
@needs_config
def cluster_ssh(ctx, service_name):
    """
    SSH to the specified EC2 system in the ECS cluster running SERVICE_NAME.
    """
    service = FriendlyServiceFactory.new(service_name, config=ctx.obj['CONFIG'])
    instances = service.get_instances()
    for index, instance in enumerate(instances):
        click.echo("Instance {}: {} ({})".format(index + 1, instance.name, instance.id))

    choice = click.prompt("Which instance to ssh to?", type=int)
    if choice > len(instances) or choice < 1:
        click.echo("That is not a valid instance.")
        return

    instance = instances[choice - 1]
    ssh = SSHConfig(service, config=ctx.obj['CONFIG']).get_ssh()
    ssh.ssh(instance=instance)
