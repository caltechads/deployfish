from __future__ import print_function

import string
import sys

import click

import deployfish


@click.group(invoke_without_command=True)
@click.option('--filename', '-f', default='deployfish.yml', help="Path to the config file. Default: ./deployfish.yml")
@click.option('--env_file', '-e', help="Path to the optional environment file.")
@click.option('--import_env/--no-import_env', '-i', default=False, help="Whether or not to load environment variables from the host" )
@click.option('--version/--no-version', '-v', default=False, help="Print the current version and exit.")
@click.option('--tfe_token', '-t', default=None, help="Terraform Enterprise API Token")
@click.pass_context
def cli(ctx, filename, env_file, import_env, version, tfe_token):
    """
    Run and maintain ECS services.
    """
    ctx.obj['CONFIG_FILE'] = filename
    ctx.obj['ENV_FILE'] = env_file
    ctx.obj['IMPORT_ENV'] = import_env
    ctx.obj['TFE_TOKEN'] = tfe_token

    if version:
        print(deployfish.__version__)
        sys.exit(0)
