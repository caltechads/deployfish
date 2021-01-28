#!/usr/bin/env python
from __future__ import print_function

import importlib
import pkg_resources
import os
import subprocess
import sys

import click

from deployfish.config import Config, needs_config
from deployfish.aws.ecs import Service, Task
from deployfish.aws.systems_manager import ParameterStore, UnboundParameterFactory, WILDCARD_RE
from deployfish.cli import cli
from deployfish.ssh import SSHConfig


class FriendlyServiceFactory:
    """
    This is a wrapper for ``Service`` that prints a friendly message when we're given a service or environment name that
    doesn't exist.
    """

    @staticmethod
    def new(service_name, config=None):
        try:
            return Service(service_name, config=config)
        except KeyError:
            print(config.raw)
            click.secho('No service or environment named "{}"'.format(service_name), fg='red')
            print()
            config.info()
            sys.exit(1)


def print_service_info(service):
    click.secho('    service_name        : {}'.format(service.serviceName), fg="cyan")
    click.secho('    cluster_name        : {}'.format(service.clusterName), fg="cyan")
    click.secho('    count               : {}'.format(service.count), fg="cyan")
    if service.asg.exists():
        click.secho('    autoscaling group:', fg="cyan")
        click.secho('      name              : {}'.format(service.asg.name), fg="cyan")
        click.secho('      count             : {}'.format(service.asg.count), fg="cyan")
        click.secho('      min_size          : {}'.format(service.asg.min), fg="cyan")
        click.secho('      max_size          : {}'.format(service.asg.max), fg="cyan")
    if service.load_balancer:
        click.secho('    load_balancer:', fg="cyan")
        click.secho('      service_role_arn  : {}'.format(service.roleArn), fg="cyan")
        lb = service.load_balancer
        if isinstance(lb, dict):
            if service.load_balancer['type'] == 'elb':
                click.secho('      load_balancer_id  : {}'.format(lb['load_balancer_name']), fg="cyan")
            else:
                click.secho('      target_group_arn  : {}'.format(lb['target_group_arn']), fg="cyan")
            click.secho('      container_name    : {}'.format(lb['container_name']), fg="cyan")
            click.secho('      container_port    : {}'.format(lb['container_port']), fg="cyan")
        else:
            for tg in lb:
                click.secho('      target_group_arn  : {}'.format(tg['target_group_arn']), fg="cyan")
                click.secho('        container_name    : {}'.format(tg['container_name']), fg="cyan")
                click.secho('        container_port    : {}'.format(tg['container_port']), fg="cyan")
    if service.scaling:
        click.secho('    application_scaling:', fg="cyan")
        click.secho('      min_capacity      : {}'.format(service.scaling.MinCapacity), fg="cyan")
        click.secho('      max_capacity      : {}'.format(service.scaling.MaxCapacity), fg="cyan")
        click.secho('      role_arn          : {}'.format(service.scaling.RoleARN), fg="cyan")
        click.secho('      resource_id       : {}'.format(service.scaling.resource_id), fg="cyan")


def print_task_definition(task_definition, indent="  "):
    if task_definition.arn:
        click.secho('{}    arn                      : {}'.format(indent, task_definition.arn), fg="cyan")
    click.secho('{}    family                   : {}'.format(indent, task_definition.family), fg="cyan")
    click.secho('{}    network_mode             : {}'.format(indent, task_definition.networkMode), fg="cyan")
    if task_definition.taskRoleArn:
        click.secho('{}    task_role_arn            : {}'.format(indent, task_definition.taskRoleArn), fg="cyan")
    click.secho('{}    containers:'.format(indent), fg="cyan")
    for c in task_definition.containers:
        click.secho('{}      {}:'.format(indent, c.name), fg="cyan")
        click.secho('{}        image                : {}'.format(indent, c.image), fg="cyan")
        click.secho('{}        cpu                  : {}'.format(indent, c.cpu), fg="cyan")
        if c.memory:
            click.secho('{}        memory               : {}'.format(indent, c.memory), fg="cyan")
        if c.memoryReservation:
            click.secho('{}        memoryReservation    : {}'.format(indent, c.memory), fg="cyan")
        if c.portMappings:
            for p in c.portMappings:
                click.secho('{}        port                 : {}'.format(indent, p), fg="cyan")
        if c.extraHosts:
            for h in c.extraHosts:
                click.secho('{}        extra_host           : {}'.format(indent, h), fg="cyan")


def print_sorted_parameters(parameters):  # NOQA
    creates = []
    updates = []
    deletes = []
    no_changes = []
    not_exists = []
    for parameter in parameters:
        if parameter.should_exist:
            if not parameter.exists:
                if not parameter.is_external:
                    creates.append(parameter)
                else:
                    not_exists.append(parameter)
            elif parameter.needs_update:
                updates.append(parameter)
            else:
                no_changes.append(parameter)
        else:
            deletes.append(parameter)
    if creates:
        click.echo('  Needs creating:')
        for p in creates:
            click.secho("    {}".format(str(p)), fg="green")
    if updates:
        click.echo('\n  Needs updating:')
        for p in updates:
            click.secho("    {}".format(str(p)), fg="cyan")
    if deletes:
        click.echo('\n  Needs deleting:')
        for p in deletes:
            click.secho("    {}".format(str(p)), fg="red")
    if no_changes:
        click.echo('\n  Already correct in AWS:')
        for p in no_changes:
            click.secho("    {}".format(str(p)), fg="white")
    if not_exists:
        click.echo('\n  External parameters that do not exist in AWS:')
        for p in not_exists:
            click.secho("    {}".format(str(p)), fg="red")


def load_local_click_modules():
    for point in pkg_resources.iter_entry_points(group='deployfish.command.plugins'):
        importlib.import_module(point.module_name)


def manage_asg_count(service, count, asg, force_asg):
    if asg:
        if service.asg.exists():
            if count < service.asg.min:
                if not force_asg:
                    click.secho('Service count {} is less than min_size of {} on AutoscalingGroup "{}".'.format(
                        count,
                        service.asg.min,
                        service.asg.name
                    ), fg='red')
                    click.secho('\nEither:')
                    click.secho('  (1) use --force-asg to also reduce AutoscalingGroup min_size to {}'.format(count))
                    click.secho('  (2) specify service count >= {}'.format(service.asg.min))
                    click.secho('  (3) use --no-asg to not change the AutoscalingGroup size')
                    sys.exit(1)
                else:
                    click.secho(
                        'Updating MinCount on AutoscalingGroup "{}" to {}.'.format(service.serviceName, count),
                        fg="white"
                    )
            if count > service.asg.max:
                if not force_asg:
                    click.secho('Service count {} is greater than max_size of {} on AutoscalingGroup "{}".'.format(
                        count,
                        service.asg.max,
                        service.asg.name
                    ), fg='red')
                    click.secho('\nEither:')
                    click.secho('  (1) use --force-asg to also increase AutoscalingGroup max_size to {}'.format(count))
                    click.secho('  (2) specify service count <= {}'.format(service.asg.max))
                    sys.exit(1)
                else:
                    click.secho(
                        'Updating MaxCount on AutoscalingGroup "{}" to {}.'.format(service.serviceName, count),
                        fg="white"
                    )
            click.secho('Updating DesiredCount on AutoscalingGroup "{}" to {}.'.format(
                service.serviceName,
                count
            ), fg="white")
            service.asg.scale(count, force=force_asg)


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
    print()
    if service.exists():
        click.secho('Service "{}" already exists!'.format(service.serviceName), fg='red')
        sys.exit(1)
    click.secho('Creating service with these attributes:', fg='white')
    click.secho('  Service info:', fg="green")
    print_service_info(service)
    click.secho('    Task Definition:', fg='green')
    print_task_definition(service.desired_task_definition)
    if service.tasks:
        click.secho('\nCreating these helper tasks:', fg='white')
        for key, value in service.tasks.items():
            click.secho("  {}".format(key), fg='green')
            print_task_definition(value.desired_task_definition)
    parameters = service.get_config()
    if update_configs:
        if len(parameters) > 0:
            click.secho('\nUpdating service config parameters like so:', fg='white')
            print_sorted_parameters(parameters)
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
        manage_asg_count(service, service.count, asg, force_asg)
        service.create()
        if wait:
            click.secho("\n  Waiting until the service is stable ...", fg='white')
            if service.wait_until_stable(timeout):
                click.secho("  Done.", fg='white')
            else:
                click.secho("  FAILURE: the service failed to start.", fg='red')
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
    print()
    if service.exists():
        click.secho('"{}" service live info:'.format(service.serviceName), fg="white")
        click.secho('  Service info:', fg="green")
        print_service_info(service)
        click.secho('  Task Definition:', fg="green")
        print_task_definition(service.active_task_definition)
        if service.tasks:
            click.secho('\n"{}" helper tasks:'.format(service.serviceName), fg='white')
            for key, value in service.tasks.items():
                click.secho("  {}".format(key), fg='green')
                print_task_definition(value.active_task_definition)
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
    Update the our ECS service from what is in deployfish.yml.  This means two things:

    \b
        * Update the task definition
        * Update the scaling policies (if any)

    These things can only be changed by deleting and recreating the service:

    \b
        * service name
        * cluster name
        * load balancer

    If you want to update the desiredCount on the service, use "deploy scale".
    """
    service = FriendlyServiceFactory.new(service_name, config=ctx.obj['CONFIG'])
    print()
    click.secho('Updating "{}" service:'.format(service.serviceName), fg="white")
    click.secho('  Current task definition:', fg="yellow")
    print_task_definition(service.active_task_definition)
    click.secho('\n  New task definition:', fg="green")
    print_task_definition(service.desired_task_definition)
    if service.tasks:
        click.secho('\nUpdating "{}" helper tasks to:'.format(service.serviceName), fg='white')
        for key, value in service.tasks.items():
            click.secho("  {}".format(key), fg='green')
            print_task_definition(value.desired_task_definition)
    if service.scaling and service.scaling.needs_update():
        click.secho('\nUpdating "{}" application scaling'.format(service.serviceName), fg='white')
    if not dry_run:
        service.update()
        if wait:
            click.secho("\n  Waiting until the service is stable with our new task def ...", fg='white')
            if service.wait_until_stable(timeout):
                click.secho("  Done.", fg='white')
            else:
                click.secho("  FAILURE: the service failed to start.", fg='red')
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
@click.option('--dry-run/--no-dry-run', default=False, help="Don't actually scale the service")
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
def scale(ctx, service_name, count, dry_run, wait, asg, force_asg, timeout):
    """
    Set the desired count for service SERVICE_NAME to COUNT.
    """
    service = FriendlyServiceFactory.new(service_name, config=ctx.obj['CONFIG'])
    print()
    manage_asg_count(service, count, asg, force_asg)
    click.secho('Updating desiredCount on "{}" service in cluster "{}" to {}.'.format(
        service.serviceName,
        service.clusterName,
        count
    ), fg="white")
    if not dry_run:
        service.scale(count)
        if wait:
            click.secho("  Waiting until the service is stable with our new count ...", fg='cyan')
            if service.wait_until_stable(timeout):
                click.secho("  Done.", fg='white')
            else:
                click.secho("  FAILURE: the service failed to start.", fg='red')
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
    print()
    click.secho('Deleting service "{}":'.format(service.serviceName), fg="white")
    click.secho('  Service info:', fg="green")
    print_service_info(service)
    click.secho('  Task Definition info:', fg="green")
    print_task_definition(service.active_task_definition)
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

    instance = instances[choice-1]
    ssh = SSHConfig(service, config=ctx.obj['CONFIG']).get_ssh()
    ssh.ssh(instance=instance)

    # instance_data = service.get_instance_data()
    # instances = []
    # for index, reservation in enumerate(instance_data):
    #     instances.append(reservation['Instances'][0])

    # for index, instance in enumerate(instances):
    #     name = ''
    #     for tag in instance['Tags']:
    #         if tag['Key'] == 'Name':
    #             name = tag['Value']
    #     click.echo("Instance {}: {} ({})".format(index + 1, name, instance['InstanceId']))

    # instance = click.prompt("Which instance to ssh to?", type=int)
    # if instance > len(instances) or instance < 1:
    #     click.echo("That is not a valid instance.")
    #     return
    # host_instance = instances[instance-1]['InstanceId']
    # host_ip = instances[instance-1]['PrivateIpAddress']
    # ssh = SSHConfig(service, config=ctx.obj['CONFIG']).get_ssh()
    # ssh.ssh(host=host_instance, host_ip=host_ip)


@cli.group(short_help="Manage AWS Parameter Store values")
def config():
    pass


@config.command('show', short_help="Show the config parameters as they are currently set in AWS")
@click.pass_context
@click.argument('service_name')
@click.option('--diff/--no-diff', default=False, help="Diff our local copies of our parameters against what is in AWS")
@click.option('--to-env-file/--no-to-env-file', default=False, help="Write our output in --env_file compatible format")
@needs_config
def show_config(ctx, service_name, diff, to_env_file):
    """
    If the service SERVICE_NAME has a "config:" section defined, print a list of
    all parameters for the service and the values they currently have in AWS.
    """
    service = FriendlyServiceFactory.new(service_name, config=ctx.obj['CONFIG'])
    if not to_env_file:
        if diff:
            click.secho('Diff between local and AWS parameters for service "{}":'.format(service_name), fg='white')
        else:
            click.secho('Live values of parameters for service "{}":'.format(service_name), fg='white')
    parameters = service.get_config()
    if len(parameters) == 0:
        click.secho("  No parameters found.")
    else:
        if diff:
            print_sorted_parameters(parameters)
        else:
            for p in parameters:
                if p.exists:
                    if p.should_exist:
                        if to_env_file:
                            print("{}={}".format(p.key, p.aws_value))
                        else:
                            click.secho("  {}".format(p.display(p.key, p.aws_value)))
                else:
                    if not to_env_file:
                        click.secho("  {}".format(p.display(p.key, "[NOT IN AWS]")), fg="red")


@config.command('write', short_help="Write the config parameters to AWS System Manager Parameter Store")
@click.pass_context
@click.argument('service_name')
@click.option('--dry-run/--no-dry-run', default=False, help="Don't actually run the task")
@needs_config
def write_config(ctx, service_name, dry_run):
    """
    If the service SERVICE_NAME has a "config:" section defined, write
    all of the parameters for the service to AWS Parameter Store.
    """
    service = FriendlyServiceFactory.new(service_name, config=ctx.obj['CONFIG'])
    parameters = service.get_config()
    if len(parameters) == 0:
        click.secho('No parameters found for service "{}":'.format(service_name), fg='white')
    else:
        if not dry_run:
            click.secho('Updating parameters for service "{}":'.format(service_name), fg='white')
        else:
            click.secho('Would update parameters for service "{}" like so:'.format(service_name), fg='white')
    print_sorted_parameters(parameters)
    if not dry_run:
        service.write_config()
    else:
        click.echo('\nDRY RUN: not making changes in AWS')


def _entrypoint(ctx, section, section_name, cluster_name, parameter_prefix, command, dry_run):
    if section_name and cluster_name:
        # The only thing we need out of Config is the names of any config:
        # section variables we might have.  We don't need to do interpolation
        # in the config: section, because we retrieve the values from Parameter
        # Store, and we don't want to use any aws: section that might be in the
        # deployfish.yml to configure our boto3 session because we want to defer
        # to the IAM ECS Task Role.
        config = Config(
            filename=ctx.obj['CONFIG_FILE'],
            interpolate=False,
            use_aws_section=False
        )
        try:
            section_yml = config.get_section_item(section, section_name)
        except KeyError:
            click.echo("Our container's deployfish config file '{}' does not have section '{}' in '{}'".format(
                ctx.obj['CONFIG_FILE'] or 'deployfish.yml',
                section_name,
                section
            ))
            sys.exit(1)
        parameter_store = []
        if 'config' in section_yml:
            parameter_name = parameter_prefix + section_name
            parameter_store = ParameterStore(parameter_name, cluster_name, yml=section_yml['config'])
            parameter_store.populate()
        if not dry_run:
            for param in parameter_store:
                if param.exists:
                    if param.should_exist:
                        os.environ[param.key] = param.aws_value
                    else:
                        print(
                            "event='deploy.entrypoint.parameter.ignored.not_in_deployfish_yml' "
                            "section='{}' parameter='{}'".format(section_name, param.name)
                        )
                else:
                    print("event='deploy.entrypoint.parameter.ignored.not_in_aws' section='{}' parameter='{}'".format(
                        section_name, param.name
                    ))
        else:
            exists = []
            not_exists = []
            for param in parameter_store:
                if param.exists:
                    exists.append(param)
                else:
                    not_exists.append(param)
            click.secho("Would have set these environment variables:", fg="cyan")
            for param in exists:
                click.echo('  {}={}'.format(param.key, param.aws_value))
            click.secho("\nThese parameters are not in AWS:", fg="red")
            for param in not_exists:
                click.echo('  {}'.format(param.key))
    if dry_run:
        click.secho('\n\nCOMMAND: {}'.format(command))
    else:
        subprocess.call(command)


@cli.command('entrypoint', short_help="Use for a Docker entrypoint", context_settings=dict(ignore_unknown_options=True))
@click.pass_context
@click.argument('command', nargs=-1)
@click.option(
    '--dry-run/--no-dry-run',
    default=False,
    help="Don't actually run the task, but print what we would have done"
)
def entrypoint(ctx, command, dry_run):
    """
    Use this as the entrypoint for your containers.

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
    service_name = os.environ.get('DEPLOYFISH_SERVICE_NAME', None)
    cluster_name = os.environ.get('DEPLOYFISH_CLUSTER_NAME', None)
    _entrypoint(ctx, "services", service_name, cluster_name, "", command, dry_run)


@cli.command('ssh', short_help="Connect to an ECS cluster machine")
@click.pass_context
@click.argument('service_name')
@click.option('--verbose/--no-verbose', '-v', default=False, help="Show all SSH output.")
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
@click.pass_context
@click.argument('service_name')
@click.option('--verbose/--no-verbose', '-v', default=False, help="Show all SSH output.")
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
@click.pass_context
@click.argument('tunnel_name')
@click.option('--verbose/--no-verbose', '-v', default=False, help="Show all SSH output.")
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


@cli.group(short_help="Manage tasks.")
def task():
    pass


@task.command('run', short_help="Run a task")
@click.pass_context
@click.argument('task_name')
@click.option('--wait/--no-wait', '-w', default=False, help="Wait for log output.")
@needs_config
def task_run(ctx, task_name, wait):
    """
    Run the specified task, and if wait is true, wait for the task to finish and display
    any logs.
    """
    task = Task(task_name, config=ctx.obj['CONFIG'])
    try:
        task.run(wait)
    except Exception as e:
        click.echo("There was an unspecified error running this task.")
        click.echo(str(e))


@task.command('schedule', short_help="Schedule a task")
@click.pass_context
@click.argument('task_name')
@needs_config
def task_schedule(ctx, task_name):
    """
    Schedule the specified task according to the schedule expression defined in the yml file.
    """
    task = Task(task_name, config=ctx.obj['CONFIG'])
    task.schedule()


@task.command('unschedule', short_help="Unschedule a task")
@click.pass_context
@click.argument('task_name')
@needs_config
def task_unschedule(ctx, task_name):
    """
    Unschedule the specified task.
    """
    task = Task(task_name, config=ctx.obj['CONFIG'])
    task.unschedule()


@task.command('update', short_help="Update a task")
@click.pass_context
@click.argument('task_name')
@needs_config
def task_update(ctx, task_name):
    """
    Update the task definition for the specified task.
    """
    task = Task(task_name, config=ctx.obj['CONFIG'])
    try:
        task.update()
    except Exception as e:
        click.echo('Task update failed: {}'.format(str(e)))
    else:
        click.echo("Task updated.")


@task.group("config", short_help="Manage AWS Parameter Store values")
def task_config():
    pass


def _show_config(section, name, diff, to_env_file):
    if not to_env_file:
        if diff:
            click.secho('Diff between local and AWS parameters for section "{}":'.format(name), fg='white')
        else:
            click.secho('Live values of parameters for section "{}":'.format(name), fg='white')
    parameters = section.get_config()
    if len(parameters) == 0:
        click.secho("  No parameters found.")
    else:
        if diff:
            print_sorted_parameters(parameters)
        else:
            for p in parameters:
                if p.exists:
                    if p.should_exist:
                        if to_env_file:
                            print("{}={}".format(p.key, p.aws_value))
                        else:
                            click.secho("  {}".format(p.display(p.key, p.aws_value)))
                else:
                    if not to_env_file:
                        click.secho("  {}".format(p.display(p.key, "[NOT IN AWS]")), fg="red")


@task_config.command('show', short_help="Show the config parameters as they are currently set in AWS")
@click.pass_context
@click.argument('task_name')
@click.option('--diff/--no-diff', default=False, help="Diff our local copies of our parameters against what is in AWS")
@click.option('--to-env-file/--no-to-env-file', default=False, help="Write our output in --env_file compatible format")
@needs_config
def task_show_config(ctx, task_name, diff, to_env_file):
    """
    If the task TASK_NAME has a "config:" section defined, print a list of
    all parameters for the task and the values they currently have in AWS.
    """
    task = Task(task_name, config=ctx.obj['CONFIG'])
    _show_config(task, task_name, diff, to_env_file)


def _write_config(section, name, dry_run):
    parameters = section.get_config()
    if len(parameters) == 0:
        click.secho('No parameters found for section "{}":'.format(name), fg='white')
    else:
        if not dry_run:
            click.secho('Updating parameters for section "{}":'.format(name), fg='white')
        else:
            click.secho('Would update parameters for section "{}" like so:'.format(name), fg='white')
    print_sorted_parameters(parameters)
    if not dry_run:
        section.write_config()
    else:
        click.echo('\nDRY RUN: not making changes in AWS')


@task_config.command('write', short_help="Write the config parameters to AWS System Manager Parameter Store")
@click.pass_context
@click.argument('task_name')
@click.option('--dry-run/--no-dry-run', default=False, help="Don't actually run the task")
@needs_config
def task_write_config(ctx, task_name, dry_run):
    """
    If the task TASK_NAME has a "config:" section defined, write
    all of the parameters for the task to AWS Parameter Store.
    """
    task = Task(task_name, config=ctx.obj['CONFIG'])
    _write_config(task, task_name, dry_run)


@task.command(
    'entrypoint',
    short_help="Use for a Docker entrypoint",
    context_settings=dict(ignore_unknown_options=True)
)
@click.pass_context
@click.argument('command', nargs=-1)
@click.option(
    '--dry-run/--no-dry-run',
    default=False,
    help="Don't actually run the task, but print what we would have done"
)
def task_entrypoint(ctx, command, dry_run):
    """
    Use this as the entrypoint for your containers.

    It will look in the shell environment for the environment variables
    DEPLOYFISH_TASK_NAME and DEPLOYFISH_CLUSTER_NAME.  If found, it will
    use them to:

    \b
    * download the parameters listed in "config:" section for task
      DEPLOYFISH_TASK_NAME from the AWS System Manager Parameter Store (which
      are prefixed by "${DEPLOYFISH_CLUSTER_NAME}.task-${DEPLOYFISH_SERVICE_NAME}.")
    * set those parameters and their values as environment variables
    * run COMMAND

    If either DEPLOYFISH_TASK_NAME or DEPLOYFISH_CLUSTER_NAME are not in
    the environment, just run COMMAND.

    \b
    NOTE:

        "entrypoint" commands IGNORE any "aws:" section in your config file.
        We're assuming that you're only ever running "deploy entrypoint" inside
        a container in your AWS service.  It should get its credentials
        from the container's IAM ECS Task Role.
    """
    task_name = os.environ.get('DEPLOYFISH_TASK_NAME', None)
    cluster_name = os.environ.get('DEPLOYFISH_CLUSTER_NAME', None)
    _entrypoint(ctx, 'tasks', task_name, cluster_name, "task-", command, dry_run)


@cli.group(short_help="Manage SSM Parameter Store Parameters.")
def parameters():
    pass


@parameters.command('show', short_help="Print the values one or more parameters")
@click.argument('name')
def show(name):
    """
    Print out all parameters that match NAME.   If NAME ends with a '*', do a wildcard search on all parameters that
    begin with the prefix.
    """
    parms = UnboundParameterFactory.new(name)
    parms.sort()
    if not parms:
        print('No parameters found that match "{}"'.format(name))
    else:
        for parm in parms:
            print(parm)


@parameters.command('copy', short_help="Copy the values from one parameter or set of parameters to another")
@click.argument('from_name')
@click.argument('to_name')
@click.option('--new-kms-key', default=None, help="Encrypt the copy with the KMS Key whose alias or ARN is TEXT")
@click.option(
    '--overwrite/--no-overwrite',
    default=False,
    help="Force an overwrite of any existing parameters with the new name. Default: --no-overwrite."
)
@click.option(
    '--dry-run/--no-dry-run',
    default=False,
    help="Don't actually copy.  Default: --no-dry-run."
)
def parameters_copy(from_name, to_name, new_kms_key, overwrite, dry_run):
    """
    If FROM_NAME does not end with a "*", copy a parameter named FROM_NAME to another named TO_NAME.

    If FROM_NAME does end with a '*', do a wildcard search on all parameters that begin with the FROM_NAME, and copy
    those parameters to new ones with the FROM_NAME as prefix replaced with TO_NAME as prefix.
    """
    parms = UnboundParameterFactory.new(from_name)
    if not parms:
        print('No parameters found that match "{}"'.format(from_name))
    else:
        parms.sort()
        print("\nFROM:")
        print("-----------------------------------------------------------------------")
        for parm in parms:
            print(parm)
        m = WILDCARD_RE.search(from_name)
        if m:
            if not to_name.endswith('.'):
                to_name += "."
            for parm in parms:
                parm.prefix = to_name
                if new_kms_key:
                    parm.kms_key_id = new_kms_key
        else:
            for parm in parms:
                parm.name = to_name
        print("\nTO:")
        print("-----------------------------------------------------------------------")
        for parm in parms:
            if not dry_run:
                try:
                    parm.save(overwrite=overwrite)
                except ValueError:
                    pass
                else:
                    print(parm)


@parameters.command('update', short_help="Update the value or KMS Key on one or more parameters")
@click.argument('name')
@click.option('--new-kms-key', default=None, help="Re-encrypt with KMS Key whose alias or ARN matches TEXT")
@click.option('--value', default=None, help="Update the value to TEXT")
@click.option(
    '--force-multiple/--no-force-multiple',
    default=False,
    help="If NAME is a wildcard and you used --value, actually update all matching "
         "parameters to that value. Default: --no-force-multiple."
)
@click.option(
    '--dry-run/--no-dry-run',
    default=False,
    help="Don't actually copy.  Default: --no-dry-run."
)
def parameters_update(name, new_kms_key, value, force_multiple, dry_run):
    """
    Update the parameter that matches NAME with either a new KMS Key ID, a new value, or both.

    If NAME ends with a '*', and you use the --new-kms-key parameter, update the KMS Key ID on on all parameters that
    begin with the prefix.

    If NAME ends with a '*', and you use the --value parameter, don't update the value for all parameters that begin
    with the prefix unless you also specify --force-multiple.
    """
    parms = UnboundParameterFactory.new(name)
    if not parms:
        print('No parameters found that match "{}"'.format(name))
    else:
        parms.sort()
        print("\nBEFORE:")
        print("-----------------------------------------------------------------------")
        for parm in parms:
            print(parm)
        print("\nAFTER:")
        print("-----------------------------------------------------------------------")
        for parm in parms:
            if new_kms_key:
                parm.kms_key_id = new_kms_key
            if len(parms) == 1 or force_multiple:
                if value:
                    parm.value = value
            if not dry_run:
                parm.save(overwrite=True)
            print(parm)


def main():
    load_local_click_modules()
    cli(obj={})


if __name__ == '__main__':
    main()
