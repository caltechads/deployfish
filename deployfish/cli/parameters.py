"""
Command group: `deploy parameters COMMAND`

This file contains commands that acting on AWS ParameterStore parameters independently of an ECS Task or
ECS service.  Use these commands to manipulate external parameters.
"""
import click

from deployfish.aws.systems_manager import (
    UnboundParameterFactory,
    WILDCARD_RE,
)

from .cli import cli


@cli.group(short_help="Manage SSM Parameter Store Parameters.")
def parameters():
    pass


@parameters.command('show', short_help="Print the values one or more parameters")
@click.pass_context
@click.argument('name')
def show(ctx, name):
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
@click.pass_context
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
def parameters_copy(ctx, from_name, to_name, new_kms_key, overwrite, dry_run):
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
@click.pass_context
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
def parameters_update(ctx, name, new_kms_key, value, force_multiple, dry_run):
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
