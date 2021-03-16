from __future__ import print_function

import importlib
import pkg_resources
import sys

import click

from deployfish.aws.ecs import Service


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


def _entrypoint(ctx, section, section_name, cluster_name, parameter_prefix, command, dry_run):
    if section_name and cluster_name:
        # The only thing we need out of Config is the names of any config:
        # section variables we might have.  We don't need to do interpolation
        # in the config: section, because we retrieve the values from Parameter
        # Store, and we don't want to use any aws: section that might be in the
        # deployfish.yml to configure our boto3 session because we want to defer
        # to the IAM ECS Task Role.
        config = Config(filename=ctx.obj['CONFIG_FILE'], interpolate=False, use_aws_section=False)
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

