"""
Command group: `deploy config COMMAND`

This file contains the commands that act AWS Paramter Store parameters for an ECS service.

.. note::

    This is ONLY for ECS services.  ECS Task parameters are handled by `deploy task config`
"""
import click

from ..config import needs_config
from .cli import cli
from .misc import (
    FriendlyServiceFactory,
    ClickServiceAdapter,
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
    adapter = ClickServiceAdapter(service)
    if to_env_file:
        click.secho(adapter.parameters.to_env_file())
        return
    if diff:
        click.secho(adapter.parameters.diff())
    else:
        click.secho(adapter.parameters.list())


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
    adapter = ClickServiceAdapter(service)
    click.secho(adapter.parameters.write(dry_run=dry_run))
