"""
Command group: No group; miscellaneous top level commands related to ECS services.

This file contains commands that act on ECS services (creating, examining, updating, etc.).

.. note::

    There's not command group for this (e.g. `deploy service COMMAND`) because deployfish originally only dealt with ECS
    services and we did not think ahead to imagine all the ways we'd expand this tool.
"""

import sys

import click
from ..config import needs_config

from .cli import cli
from .misc import (
    ClickServiceAdapter,
    ClickServiceEntrypoint,
    FriendlyServiceFactory,
)


@cli.command('create', short_help="Create a service in AWS")
@click.pass_context
@click.argument('service_name')
@click.option('--update-configs/--no-update-configs', default=False, help="Update our config parameters in AWS")
@click.option('--dry-run/--no-dry-run', default=False, help="Don't actually create the service")
@click.option(
    '--wait/--no-wait',
    default=True,
    help="Don't exit until the service is created and all its tasks are running"
)
@click.option('--asg/--no-asg', default=True, help="Scale your ASG to fit our service count")
@click.option(
    '--force-asg/--no-force-asg',
    default=False,
    help="Force your ASG to scale outside of its MinCount or MaxCount"
)
@click.option(
    '--timeout',
    default=600,
    help="Retry the service stability check until this many seconds has passed. Default: 600."
)
@needs_config
def create(ctx, service_name, update_configs, dry_run, wait, asg, force_asg, timeout):
    """
    Create a new ECS service named SERVICE_NAME.
    """
    service = FriendlyServiceFactory.new(service_name, config=ctx.obj['CONFIG'])
    adapter = ClickServiceAdapter(service)
    print()
    if service.exists():
        click.secho('Service "{}" already exists!'.format(service.serviceName), fg='red')
        sys.exit(1)
    click.secho(adapter.render(state='desired'))
    parameters = service.get_config()
    if update_configs:
        if len(parameters) > 0:
            click.secho('\nUpdating service config parameters like so:', fg='white')
            click.secho(adapter.parameters.diff())
        else:
            click.secho('\nService has no config parameters defined: SKIPPING', fg='white')
    else:
        if parameters:
            click.secho('\nService has config parameters defined: SKIPPING', fg='red')
            if dry_run:
                click.secho(
                    '    Either run create with the --update-configs flag or do "deploy config write {}"'.format(
                        service_name
                    )
                )
            else:
                click.secho('    To update them in AWS, do "deploy config write {}"'.format(service_name))
    if not dry_run:
        if asg:
            try:
                adapter.scale_asg(force=force_asg)
            except adapter.ASGScaleException as e:
                click.secho(str(e))
                sys.exit(1)
        service.create()
        if wait:
            try:
                adapter.wait(timeout)
            except adapter.TimeoutException as e:
                click.secho(str(e))
                sys.exit(1)


@cli.command('info', short_help="Print current AWS info about a service")
@click.pass_context
@click.argument('service_name')
@needs_config
def info(ctx, service_name):
    """
    Show current AWS information about this service and its task definition
    """
    service = FriendlyServiceFactory.new(service_name, config=ctx.obj['CONFIG'])
    adapter = ClickServiceAdapter(service)
    print()
    if service.exists():
        click.secho(adapter.render())
    else:
        click.secho('"{}" service is not in AWS yet.'.format(service.serviceName), fg="white")


@cli.command('related-tasks', short_help="List the one-off tasks associated with this service")
@click.pass_context
@click.argument('service_name')
@needs_config
def related_tasks(ctx, service_name):
    """
    List any one off tasks associated with the ECS service identified by SERVICE_NAME.
    """
    service = FriendlyServiceFactory.new(service_name, config=ctx.obj['CONFIG'])
    for task in ctx.obj['CONFIG'].tasks:
        if 'service' in task and task['service'] == service.serviceName:
            print(task['name'])


@cli.command('version', short_help='Print image tag of live service')
@click.pass_context
@click.argument('service_name')
@needs_config
def version(ctx, service_name):
    """Print the tag of the image in the first container on the service"""
    service = FriendlyServiceFactory.new(service_name, config=ctx.obj['CONFIG'])
    print(service.version())


@cli.command('update', short_help='Update task definition for a service')
@click.pass_context
@click.argument('service_name')
@click.option('--dry-run/--no-dry-run', default=False, help="Don't actually create a new task definition")
@click.option(
    '--wait/--no-wait',
    default=True,
    help="Don't exit until all tasks are running the new task definition revision"
)
@click.option(
    '--timeout',
    default=600,
    help="Retry the service stability check until this many seconds has passed. Default: 600."
)
@needs_config
def update(ctx, service_name, dry_run, wait, timeout):
    """
    Update the our ECS service in AWS from what is in deployfish.yml.  This means these things:

    \b
        * Update the task definition
        * Update the scaling policies (if any)
        * Update the helper tasks (if any)

    These things can only be changed by deleting and recreating the service:

    \b
        * service name
        * cluster name
        * load balancer/target groups

    If you want to update the desiredCount on the service, use "deploy scale".
    """
    service = FriendlyServiceFactory.new(service_name, config=ctx.obj['CONFIG'])
    adapter = ClickServiceAdapter(service)
    print()
    title = 'Updating "{}" service:'.format(service.serviceName)
    click.secho(title, fg="white")
    click.secho('=' * len(title), fg="white")
    click.secho('\nCurrent task definition:', fg="yellow")
    click.secho(adapter.indent(adapter.active_task_definition.render()))
    click.secho('\nNew task definition:', fg="yellow")
    click.secho(adapter.indent(adapter.desired_task_definition.render()))
    print()
    click.secho(adapter.render_helper_tasks(state='desired'))
    if service.scaling and service.scaling.needs_update():
        click.secho('\nUpdating "{}" application scaling'.format(service.serviceName), fg='white')
    if not dry_run:
        service.update()
        if wait:
            try:
                adapter.wait(timeout)
            except adapter.TimeoutException as e:
                click.secho(str(e))
                sys.exit(1)


@cli.command('restart', short_help="Restart all tasks in service")
@click.pass_context
@click.argument('service_name')
@click.option('--hard/--no-hard', default=False, help="Kill off all tasks immediately instead of one by one")
@needs_config
def restart(ctx, service_name, hard):
    """
    Restart all tasks in the service SERVICE_NAME by killing them off one by
    one.  Kill each task and wait for it to be replaced before killing the next
    one off.
    """
    service = FriendlyServiceFactory.new(service_name, config=ctx.obj['CONFIG'])
    print()
    click.secho('Restarting tasks in "{}" service in cluster "{}"'.format(
        service.serviceName,
        service.clusterName
    ))
    service.restart(hard=hard)


@cli.command('scale', short_help="Adjust # tasks in a service")
@click.pass_context
@click.argument('service_name')
@click.argument('count', type=int)
@click.option('--wait/--no-wait', default=True, help="Don't exit until the service is stable with the new count")
@click.option('--asg/--no-asg', default=True, help="Scale your ASG also")
@click.option(
    '--force-asg/--no-force-asg',
    default=False,
    help="Force your ASG to scale outside of its MinCount or MaxCount"
)
@click.option(
    '--timeout',
    default=600,
    help="Retry the service stability check until this many seconds has passed. Default: 600."
)
@needs_config
def scale(ctx, service_name, count, wait, asg, force_asg, timeout):
    """
    Set the desired count for service SERVICE_NAME to COUNT.
    """
    service = FriendlyServiceFactory.new(service_name, config=ctx.obj['CONFIG'])
    adapter = ClickServiceAdapter(service)
    print()
    adapter.scale_asg(count=count, force=force_asg)
    service.scale(count)
    if wait:
        try:
            adapter.wait(timeout)
        except adapter.TimeoutException as e:
            click.secho(str(e))
            sys.exit(1)


@cli.command('delete', short_help="Delete a service from AWS")
@click.pass_context
@click.argument('service_name')
@click.option('--dry-run/--no-dry-run', default=False, help="Don't actually delete the service")
@click.option(
    '--timeout',
    default=600,
    help="Retry the service stability check until this many seconds has passed. Default: 600."
)
@needs_config
def delete(ctx, service_name, dry_run, timeout):
    """
    Delete the service SERVICE_NAME from AWS.
    """
    service = FriendlyServiceFactory.new(service_name, config=ctx.obj['CONFIG'])
    adapter = ClickServiceAdapter(service)
    print()
    click.secho('Deleting service "{}":'.format(service.serviceName), fg="white")
    if service.exists():
        click.secho(adapter.render())
    else:
        click.secho('"{}" service is not in AWS yet.'.format(service.serviceName), fg="white")
    print()
    if not dry_run:
        click.echo("If you really want to do this, answer \"{}\" to the question below.\n".format(service.serviceName))
        value = click.prompt("What service do you want to delete? ")
        if value == service.serviceName:
            service.scale(0)
            print("  Waiting for our existing containers to die ...")
            service.wait_until_stable(timeout)
            print("  All containers dead.")
            service.delete()
            print("  Deleted service {} from cluster {}.".format(service.serviceName, service.clusterName))
        else:
            click.echo("\nNot deleting service \"{}\"".format(service.serviceName))


@cli.command('run_task', short_help="Run a one-shot task for our service")
@click.pass_context
@click.argument('service_name')
@click.argument('command')
@needs_config
def run_task(ctx, service_name, command):
    """
    Run the one-off task COMMAND on SERVICE_NAME.
    """
    service = FriendlyServiceFactory.new(service_name, config=ctx.obj['CONFIG'])
    response = service.run_task(command)
    if response:
        print(response)


@cli.command(
    'entrypoint',
    short_help="Use for a Docker entrypoint for an ECS service",
    context_settings=dict(ignore_unknown_options=True)
)
@click.pass_context
@click.argument('command', nargs=-1)
@click.option('--dry-run/--no-dry-run', default=False, help="Just print what environment variables would be set")
def entrypoint(ctx, command, dry_run):
    """
    Use this as the entrypoint for your ECS service containers.

    It will look in the shell environment for the environment variables
    DEPLOYFISH_SERVICE_NAME and DEPLOYFISH_CLUSTER_NAME.  If found, it will
    use them to:

    \b
    * download the parameters listed in "config:" section for service
      DEPLOYFISH_SERVICE_NAME from the AWS System Manager Parameter Store (which
      are prefixed by "${DEPLOYFISH_CLUSTER_NAME}.${DEPLOYFISH_SERVICE_NAME}.")
    * set those parameters and their values as environment variables
    * run COMMAND

    If either DEPLOYFISH_SERVICE_NAME or DEPLOYFISH_CLUSTER_NAME are not in
    the environment, just run COMMAND.

    \b
    NOTE:

        "deploy entrypoint" IGNORES any "aws:" section in your config file.
        We're assuming that you're only ever running "deploy entrypoint" inside
        a container in your AWS service.  It should get its credentials
        from the container's IAM ECS Task Role.
    """
    entrypoint = ClickServiceEntrypoint(config_file=ctx.obj['CONFIG_FILE'])
    try:
        entrypoint.entrypoint(command, dry_run=dry_run)
    except ClickServiceEntrypoint.DoesNotExist as e:
        print(str(e))
        sys.exit(1)
