from __future__ import print_function

import string
import sys

import click

import deployfish


@click.group(invoke_without_command=True)
@click.option('--filename', '-f', default='deployfish.yml', help="Path to the config file. Default: ./deployfish.yml")
@click.option('--env_file', '-e', help="Path to the optional environment file.")
@click.option('--version/--no-version', '-v', default=False, help="Print the current version and exit.")
@click.pass_context
def cli(ctx, filename, env_file, version):
    """
    Run and maintain ECS services.
    """
    ctx.obj['CONFIG_FILE'] = filename
    ctx.obj['ENV_FILE'] = env_file

    if version:
        print(deployfish.__version__)
        sys.exit(0)
