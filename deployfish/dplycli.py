"""
Note: this is only here for backwards compatibility with external deployfish modules
"""

import warnings
import click

from cli.misc import (
    FriendlyServiceFactory,
    ClickServiceAdapter,
    ClickServiceEntrypoint,
    ClickTaskEntrypoint,
    ClickParameterAdapter,
    ClickTaskDefinitionAdapter
)


def print_sorted_parameters(parameters):
    warnings.warn(
        "deployfish.dplcli.print_sorted_paramters(parameters) is deprecated; use "
        "deployfish.cli.misc.ClickParameterAdapter(parameters).diff() instead",
        DeprecationWarning
    )
    adapter = ClickParameterAdapter(parameters)
    click.echo(adapter.diff())


def print_service_info(service):
    warnings.warn(
        "deployfish.dplcli.print_service_info(service) is deprecated; use "
        "deployfish.cli.misc.ClickServiceAdapter(service).render() instead",
        DeprecationWarning
    )
    adapter = ClickServiceAdapter(service)
    click.secho(adapter.render())


def print_task_definition(task_definition, indent="    "):
    warnings.warn(
        "deployfish.dplcli.print_task_definition(task_definition) is deprecated; use "
        "deployfish.cli.misc.ClickTaskDefinitionAdapter(task_definition).render() instead",
        DeprecationWarning
    )
    adapter = ClickTaskDefinitionAdapter(task_definition)
    click.secho(adapter.render())


def _entrypoint(ctx, section, name, cluster_name, parameter_prefix, command, dry_run):
    warnings.warn(
        "deployfish.dplcli._entrypoint() is deprecated; use "
        "either deployfish.cli.misc.ClickServiceEntrypoint().entrypoint() or"
        "deployfish.cli.misc.ClickTaskEntrypoint().entrypoint() instead",
        DeprecationWarning
    )
    # name, cluster_name, parameter_prefix are ignored now, because the adapters
    # figure them out for themselves
    if section == 'services':
        adapter = ClickServiceEntrypoint(ctx.obj['CONFIG_FILE'])
    elif section == 'tasks':
        adapter = ClickTaskEntrypoint(ctx.obj['CONFIG_FILE'])
    adapter.entrypoint(command, dry_run=dry_run)


def manage_asg_count(service, count, asg, force_asg):
    warnings.warn(
        "deployfish.dplcli.manage_asg_count() is deprecated; use "
        "ClickServiceAdapter(service).scale_asg() instead",
        DeprecationWarning
    )
    adapter = ClickServiceAdapter(service)
    adapter.scale_asg(count, force=force_asg)
