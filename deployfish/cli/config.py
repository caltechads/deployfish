import click

from ..config import needs_config
from .cli import cli
from .misc import (
    FriendlyServiceFactory,
    print_sorted_parameters,
)


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
