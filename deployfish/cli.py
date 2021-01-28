from __future__ import print_function

import os
import sys
import click
import deployfish

DEFAULT_DEPLOYFISH_CONFIG_FILE = 'deployfish.yml'


@click.group(invoke_without_command=True)
@click.option('--filename', '-f', default=None, help="Path to the config file. Default: ./deployfish.yml")
@click.option('--env_file', '-e', help="Path to the optional environment file.")
@click.option(
    '--import_env/--no-import_env',
    '-i',
    default=False,
    help="Whether or not to load environment variables from the host"
)
@click.option('--version/--no-version', '-v', default=False, help="Print the current version and exit.")
@click.option('--tfe_token', '-t', default=None, help="Terraform Enterprise API Token")
@click.option(
    '--use-aws-section/--no-use-aws-section',
    default=True,
    help="Whether or not to obey the 'aws:' section of a deployfish.yml"
)
@click.pass_context
def cli(ctx, filename, env_file, import_env, version, tfe_token, use_aws_section):
    """
    Run and maintain ECS services.

    deploy will look for its config file in one of three places:

        * If the ``-f/--filename`` flag to deploy was used, use that filename.
        * If no ``-f/--filename`` flag was used, use the value from the environment variable ``DEPLOYFISH_CONFIG_FILE``
        * If no ``-f/--filename`` flag was used and `DEPLOYFISH_CONFIG_FILE` does not exist, use ``./deployfish.yml``
    """
    if version:
        print(deployfish.__version__)
        sys.exit(0)

    if not filename:
        if 'DEPLOYFISH_CONFIG_FILE' in os.environ:
            filename = os.environ['DEPLOYFISH_CONFIG_FILE']
        if not filename:
            filename = DEFAULT_DEPLOYFISH_CONFIG_FILE
    ctx.obj['CONFIG_FILE'] = filename
    if not os.path.exists(ctx.obj['CONFIG_FILE']):
        click.echo("ERROR: couldn't find deployfish config file '{}'".format(ctx.obj['CONFIG_FILE']))
        sys.exit(1)
    elif not os.access(ctx.obj['CONFIG_FILE'], os.R_OK):
        click.echo("ERROR: deployfish config file '{}' exists but is not readable".format(ctx.obj['CONFIG_FILE']))
    else:
        if ctx.obj['CONFIG_FILE'] != DEFAULT_DEPLOYFISH_CONFIG_FILE:
            click.echo("Using '{}' as our deployfish config file".format(ctx.obj['CONFIG_FILE']))

    ctx.obj['ENV_FILE'] = env_file
    ctx.obj['IMPORT_ENV'] = import_env
    ctx.obj['TFE_TOKEN'] = tfe_token
    ctx.obj['USE_AWS_SECTION'] = use_aws_section
