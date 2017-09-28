#!/usr/bin/env python
from __future__ import print_function

import importlib
import pkg_resources
import os
import random
import subprocess
import sys


import click

from deployfish.config import Config
from deployfish.aws.ecs import Service
from deployfish.aws.systems_manager import ParameterStore
from deployfish.cli import cli


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
        click.secho('      type              : {}'.format(service.load_balancer['type']), fg="cyan")
        if service.load_balancer['type'] == 'elb':
            click.secho('      load_balancer_id  : {}'.format(service.load_balancer['load_balancer_name']), fg="cyan")
        else:
            click.secho('      target_group_arn  : {}'.format(service.load_balancer['target_group_arn']), fg="cyan")
        click.secho('      container_name    : {}'.format(service.load_balancer['container_name']), fg="cyan")
        click.secho('      container_port    : {}'.format(service.load_balancer['container_port']), fg="cyan")
    if service.scaling:
        click.secho('    application_scaling:', fg="cyan")
        click.secho('      min_capacity      : {}'.format(service.scaling.MinCapacity), fg="cyan")
        click.secho('      max_capacity      : {}'.format(service.scaling.MaxCapacity), fg="cyan")
        click.secho('      role_arn          : {}'.format(service.scaling.RoleARN), fg="cyan")
        click.secho('      resource_id       : {}'.format(service.scaling.resource_id), fg="cyan")


def print_task_definition(task_definition, indent="  "):
    if task_definition.arn:
        click.secho('{}    arn               : {}'.format(indent, task_definition.arn), fg="cyan")
    click.secho('{}    family            : {}'.format(indent, task_definition.family), fg="cyan")
    click.secho('{}    network_mode      : {}'.format(indent, task_definition.networkMode), fg="cyan")
    if task_definition.taskRoleArn:
        click.secho('{}    task_role_arn     : {}'.format(indent, task_definition.taskRoleArn), fg="cyan")
    click.secho('{}    containers:'.format(indent), fg="cyan")
    for c in task_definition.containers:
        click.secho('{}      {}:'.format(indent, c.name), fg="cyan")
        click.secho('{}        image         : {}'.format(indent, c.image), fg="cyan")
        click.secho('{}        cpu           : {}'.format(indent, c.cpu), fg="cyan")
        click.secho('{}        memory        : {}'.format(indent, c.memory), fg="cyan")
        if c.portMappings:
            for p in c.portMappings:
                click.secho('{}        port          : {}'.format(indent, p), fg="cyan")
        if c.extraHosts:
            for h in c.extraHosts:
                click.secho('{}        extra_host    : {}'.format(indent, h), fg="cyan")


def print_sorted_parameters(parameters):  # NOQA
    creates = []
    updates = []
    deletes = []
    nochanges = []
    notexists = []
    for parameter in parameters:
        if parameter.should_exist:
            if not parameter.exists:
                if not parameter.is_external:
                    creates.append(parameter)
                else:
                    notexists.append(parameter)
            elif parameter.needs_update:
                updates.append(parameter)
            else:
                nochanges.append(parameter)
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
    if nochanges:
        click.echo('\n  Already correct in AWS:')
        for p in nochanges:
            click.secho("    {}".format(str(p)), fg="white")
    if notexists:
        click.echo('\n  External parameters that do not exist in AWS:')
        for p in notexists:
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
                    click.secho('Updating MinCount on AutoscalingGroup "{}" to {}.'.format(service.serviceName, count), fg="white")
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
                    click.secho('Updating MaxCount on AutoscalingGroup "{}" to {}.'.format(service.serviceName, count), fg="white")
            click.secho('Updating DesiredCount on AutoscalingGroup "{}" to {}.'.format(service.serviceName, count), fg="white")
            service.asg.scale(count, force=force_asg)


@cli.command('create', short_help="Create a service in AWS")
@click.pass_context
@click.argument('service_name')
@click.option('--update-configs/--no-update-configs', default=False, help="Update our config parameters in AWS")
@click.option('--dry-run/--no-dry-run', default=False, help="Don't actually create the service")
@click.option('--wait/--no-wait', default=True, help="Don't exit until the service is created and all its tasks are running")
@click.option('--asg/--no-asg', default=True, help="Scale your ASG to fit our service count")
@click.option('--force-asg/--no-force-asg', default=False, help="Force your ASG to scale outside of its MinCount or MaxCount")
def create(ctx, service_name, update_configs, dry_run, wait, asg, force_asg):
    """
    Create a new ECS service named SERVICE_NAME.
    """
    service = Service(yml=Config(filename=ctx.obj['CONFIG_FILE'], env_file=ctx.obj['ENV_FILE']).get_service(service_name))
    print
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
                click.secho('    Either run create with the --update-configs flag or do "deploy config write {}"'.format(service_name))
            else:
                click.secho('    To update them in AWS, do "deploy config write {}"'.format(service_name))
    if not dry_run:
        manage_asg_count(service, service.count, asg, force_asg)
        service.create()
        if wait:
            click.secho("\n  Waiting until the service is stable ...", fg='white')
            if service.wait_until_stable():
                click.secho("  Done.", fg='white')
            else:
                click.secho("  FAILURE: the service failed to start.", fg='red')
                sys.exit(1)


@cli.command('info', short_help="Print current AWS info about a service")
@click.pass_context
@click.argument('service_name')
def info(ctx, service_name):
    """
    Show current AWS information about this service and its task definition
    """
    service = Service(yml=Config(filename=ctx.obj['CONFIG_FILE'], env_file=ctx.obj['ENV_FILE']).get_service(service_name))
    print
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


@cli.command('version', short_help='Print image tag of live service')
@click.pass_context
@click.argument('service_name')
def version(ctx, service_name):
    """Print the tag of the image in the first container on the service"""
    service = Service(yml=Config(filename=ctx.obj['CONFIG_FILE'], env_file=ctx.obj['ENV_FILE']).get_service(service_name))
    print(service.version())


@cli.command('update', short_help='Update task defintion for a service')
@click.pass_context
@click.argument('service_name')
@click.option('--dry-run/--no-dry-run', default=False, help="Don't actually create a new task definition")
@click.option('--wait/--no-wait', default=True, help="Don't exit until all tasks are running the new task definition revision")
def update(ctx, service_name, dry_run, wait):
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
    service = Service(yml=Config(filename=ctx.obj['CONFIG_FILE'], env_file=ctx.obj['ENV_FILE']).get_service(service_name))
    print
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
            if service.wait_until_stable():
                click.secho("  Done.", fg='white')
            else:
                click.secho("  FAILURE: the service failed to start.", fg='red')
                sys.exit(1)


@cli.command('restart', short_help="Restart all tasks in service")
@click.pass_context
@click.argument('service_name')
@click.option('--hard/--no-hard', default=False, help="Kill off all tasks immediately instead of one by one")
def restart(ctx, service_name, hard):
    """
    Restart all tasks in the service SERVICE_NAME by killing them off one by
    one.  Kill each task and wait for it to be replaced before killing the next
    one off.
    """
    service = Service(yml=Config(filename=ctx.obj['CONFIG_FILE'], env_file=ctx.obj['ENV_FILE']).get_service(service_name))
    print
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
@click.option('--force-asg/--no-force-asg', default=False, help="Force your ASG to scale outside of its MinCount or MaxCount")
def scale(ctx, service_name, count, dry_run, wait, asg, force_asg):
    """
    Set the desired count for service SERVICE_NAME to COUNT.
    """
    service = Service(yml=Config(filename=ctx.obj['CONFIG_FILE'], env_file=ctx.obj['ENV_FILE']).get_service(service_name))
    print
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
            if service.wait_until_stable():
                click.secho("  Done.", fg='white')
            else:
                click.secho("  FAILURE: the service failed to start.", fg='red')
                sys.exit(1)


@cli.command('delete', short_help="Delete a service from AWS")
@click.pass_context
@click.argument('service_name')
@click.option('--dry-run/--no-dry-run', default=False, help="Don't actually delete the service")
def delete(ctx, service_name, dry_run):
    """
    Delete the service SERVICE_NAME from AWS.
    """
    service = Service(yml=Config(filename=ctx.obj['CONFIG_FILE'], env_file=ctx.obj['ENV_FILE']).get_service(service_name))
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
            service.wait_until_stable()
            print("  All containers dead.")
            service.delete()
            print("  Deleted service {} from cluster {}.".format(service.serviceName, service.clusterName))
        else:
            click.echo("\nNot deleting service \"{}\"".format(service.serviceName))


@cli.command('run_task', short_help="Run a one-shot task for our service")
@click.pass_context
@click.argument('service_name')
@click.argument('command')
def run_task(ctx, service_name, command):
    """
    Run the one-off task COMMAND on SERVICE_NAME.
    """
    service = Service(yml=Config(filename=ctx.obj['CONFIG_FILE'], env_file=ctx.obj['ENV_FILE']).get_service(service_name))
    response = service.run_task(command)
    if response:
        print(response)


@cli.group(short_help="Manage the AWS ECS cluster")
def cluster():
    pass


@cluster.command('info', short_help="Show info about the individual systems in the cluster")
@click.pass_context
@click.argument('service_name')
def cluster_info(ctx, service_name):
    """
    Show information about the individual EC2 systems in the ECS cluster running
    SERVICE_NAME.
    """
    service = Service(yml=Config(filename=ctx.obj['CONFIG_FILE'], env_file=ctx.obj['ENV_FILE']).get_service(service_name))
    instances = service.get_instance_data()
    for index, reservation in enumerate(instances):
        click.echo(click.style("Instance {}".format(index + 1), bold=True))
        instance = reservation['Instances'][0]
        print("\tIP: {}".format(instance['PrivateIpAddress']))
        print("\tType: {}".format(instance['InstanceType']))
        for tag in instance['Tags']:
            print("\t{}: {}".format(tag['Key'], tag['Value']))
        print("")


@cluster.command('run', short_help="Run a command on the individual systems in the cluster")
@click.pass_context
@click.argument('service_name')
def cluster_run(ctx, service_name):
    """
    Run a command on each of the individual EC2 systems in the ECS cluster running
    SERVICE_NAME.
    """
    command = click.prompt('Command to run')
    service = Service(
        yml=Config(filename=ctx.obj['CONFIG_FILE'], env_file=ctx.obj['ENV_FILE']).get_service(service_name))
    responses = service.cluster_run([command])
    for index, response in enumerate(responses):
        click.echo(click.style("Instance {}".format(index + 1), bold=True))
        click.echo("Success: {}".format(response[0]))
        click.echo(response[1])


@cluster.command('ssh', short_help="SSH to individual systems in the cluster")
@click.pass_context
@click.argument('service_name')
def cluster_ssh(ctx, service_name):
    """
    SSH to the specified EC2 system in the ECS cluster running SERVICE_NAME.
    """
    service = Service(
        yml=Config(filename=ctx.obj['CONFIG_FILE'], env_file=ctx.obj['ENV_FILE']).get_service(service_name))
    ips = service.get_host_ips()
    for index, ip in enumerate(ips):
        click.echo("Instance {}: {}".format(index+1, ip))

    instance = click.prompt("Which instance to ssh to?", type=int)
    if instance > len(ips):
        click.echo("That is not a valid instance.")
        return
    instance_ip = ips[instance-1]
    service.cluster_ssh(instance_ip)


@cli.group(short_help="Manage AWS Parameter Store values")
def config():
    pass


@config.command('show', short_help="Show the config parameters as they are currently set in AWS")
@click.pass_context
@click.argument('service_name')
@click.option('--diff/--no-diff', default=False, help="Diff our local copies of our parameters against what is in AWS")
@click.option('--to-env-file/--no-to-env-file', default=False, help="Write our output in --env_file compatible format")
def show_config(ctx, service_name, diff, to_env_file):
    """
    If the service SERVICE_NAME has a "config:" section defined, print a list of
    all parameters for the service and the values they currently have in AWS.
    """
    service = Service(yml=Config(filename=ctx.obj['CONFIG_FILE'], env_file=ctx.obj['ENV_FILE']).get_service(service_name))
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
def write_config(ctx, service_name, dry_run):
    """
    If the service SERVICE_NAME has a "config:" section defined, write
    all of the parameters for the service to AWS Parameter Store.
    """
    service = Service(yml=Config(filename=ctx.obj['CONFIG_FILE'], env_file=ctx.obj['ENV_FILE']).get_service(service_name))
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


@cli.command('entrypoint', short_help="Use for a Docker entrypoint", context_settings=dict(ignore_unknown_options=True))
@click.pass_context
@click.argument('command', nargs=-1)
@click.option('--dry-run/--no-dry-run', default=False, help="Don't actually run the task, but print what we would have done")
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
    the environment, just run COMMMAND.
    """
    service_name = os.environ.get('DEPLOYFISH_SERVICE_NAME', None)
    cluster_name = os.environ.get('DEPLOYFISH_CLUSTER_NAME', None)
    if service_name and cluster_name:
        service_yml = Config(filename=ctx.obj['CONFIG_FILE'], interpolate=False).get_service(service_name)
        parameter_store = []
        if 'config' in service_yml:
            parameter_store = ParameterStore(service_name, cluster_name, yml=service_yml['config'])
            parameter_store.populate()
        if not dry_run:
            for param in parameter_store:
                if param.exists:
                    if param.should_exist:
                        os.environ[param.key] = param.aws_value
                    else:
                        print("event='deploy.entrypoint.parameter.ignored.not_in_deployfish_yml' service='{}' parameter='{}'".format(service_name, param.name))
                else:
                    print("event='deploy.entrypoint.parameter.ignored.not_in_aws' service='{}' parameter='{}'".format(service_name, param.name))
        else:
            exists = []
            notexists = []
            for param in parameter_store:
                if param.exists:
                    exists.append(param)
                else:
                    notexists.append(param)
            click.secho("Would have set these environment variables:", fg="cyan")
            for param in exists:
                click.echo('  {}={}'.format(param.key, param.aws_value))
            click.secho("\nThese parameters are not in AWS:", fg="red")
            for param in notexists:
                click.echo('  {}'.format(param.key))
    if dry_run:
        click.secho('\n\nCOMMAND: {}'.format(command))
    else:
        subprocess.call(command)


@cli.command('ssh', short_help="Connect to an ECS cluster machine")
@click.pass_context
@click.argument('service_name')
@click.option('--verbose/--no-verbose', '-v', default=False, help="Show all SSH output.")
def ssh(ctx, service_name, verbose):
    """
    If the service SERVICE_NAME has any running tasks, randomly choose one of
    the container instances on which one of those tasks is running and ssh into
    it.

    If the service SERVICE_NAME has no running tasks, randomly choose one of
    the container instances in the cluster on which the service is defined.
    """
    service = Service(yml=Config(filename=ctx.obj['CONFIG_FILE'], env_file=ctx.obj['ENV_FILE']).get_service(service_name))
    service.ssh(verbose=verbose)


@cli.command('exec', short_help="Connect to a running container")
@click.pass_context
@click.argument('service_name')
def docker_exec(ctx, service_name):
    """
    SSH to an EC2 instance in the cluster defined in the service named SERVICE_NAME, then
    run docker exec on the appropriate container.
    """
    service = Service(yml=Config(filename=ctx.obj['CONFIG_FILE'], env_file=ctx.obj['ENV_FILE']).get_service(service_name))
    service.docker_exec()

def _interpolate_tunnel_info(value, service):
    if type(value) == str and value.startswith('config.'):
        param_key = value[7:]
        for param in service.get_config():
            if param.key == param_key:
                try:
                    return param.aws_value
                except:
                    return param.value
    return value


@cli.command('tunnel', short_help="Tunnel through an ECS cluster machine to the remote host")
@click.pass_context
@click.argument('tunnel_name')
def tunnel(ctx, tunnel_name):
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
    config = Config(filename=ctx.obj['CONFIG_FILE'], env_file=ctx.obj['ENV_FILE'])
    yml = config.get_category_item('tunnels', tunnel_name)
    service_name = yml['service']


    service = Service(yml=config.get_service(service_name))
    host = _interpolate_tunnel_info(yml['host'], service)
    port = int(_interpolate_tunnel_info(yml['port'], service))
    local_port = int(_interpolate_tunnel_info(yml['local_port'], service))

    interim_port = random.randrange(10000, 64000, 1)

    service.tunnel(host, local_port, interim_port, port)


def main():
    load_local_click_modules()
    cli(obj={})


if __name__ == '__main__':
    main()
