"""
Command groups:

* `deploy task COMMAND`
* `deploy task config COMMAND`

This file contains commands that act on ECS Tasks (creating, scheduling, updating, etc.).

"""
import sys

import click
from ..config import needs_config

from deployfish.aws.ecs import Task

from .cli import cli
from .misc import (
    ClickParameterAdapter,
    ClickTaskAdapter,
    ClickTaskEntrypoint,
)


@cli.group(short_help="Manage tasks.")
def task():
    pass


@task.command('info', short_help="Show info about a task")
@click.argument('task_name')
@click.pass_context
@needs_config
def task_info(ctx, task_name):
    """
    Run the specified task, and if wait is true, wait for the task to finish and display
    any logs.
    """
    task = Task(task_name, config=ctx.obj['CONFIG'])
    adapter = ClickTaskAdapter(task)
    print()
    click.secho(adapter.render(state='live'))


@task.command('run', short_help="Run a task")
@click.argument('task_name')
@click.option('--wait/--no-wait', '-w', default=False, help="Wait for log output.")
@click.pass_context
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
@click.argument('task_name')
@click.pass_context
@needs_config
def task_schedule(ctx, task_name):
    """
    Schedule the specified task according to the schedule expression defined in the yml file.
    """
    task = Task(task_name, config=ctx.obj['CONFIG'])
    task.schedule()


@task.command('unschedule', short_help="Unschedule a task")
@click.argument('task_name')
@click.pass_context
@needs_config
def task_unschedule(ctx, task_name):
    """
    Unschedule the specified task.
    """
    task = Task(task_name, config=ctx.obj['CONFIG'])
    task.unschedule()


@task.command('update', short_help="Update a task")
@click.argument('task_name')
@click.option('--dry-run/--no-dry-run', default=False, help="Don't actually upate the task")
@click.pass_context
@needs_config
def task_update(ctx, task_name, dry_run):
    """
    Update the task definition for the specified task.
    """
    task = Task(task_name, config=ctx.obj['CONFIG'])
    adapter = ClickTaskAdapter(task)
    click.echo('Updating task "{}":'.format(task.taskName))
    click.echo(adapter.render())
    if not dry_run:
        try:
            task.update()
        except Exception as e:
            click.echo('Task update failed: {}'.format(str(e)), fg='red')
        else:
            click.echo("Task updated.")


@task.group("config", short_help="Manage AWS Parameter Store values")
def task_config():
    pass


@task_config.command('show', short_help="Show the config parameters as they are currently set in AWS")
@click.argument('task_name')
@click.option('--diff/--no-diff', default=False, help="Diff our local copies of our parameters against what is in AWS")
@click.option('--to-env-file/--no-to-env-file', default=False, help="Write our output in --env_file compatible format")
@click.pass_context
@needs_config
def task_show_config(ctx, task_name, diff, to_env_file):
    """
    If the task TASK_NAME has a "config:" section defined, print a list of
    all parameters for the task and the values they currently have in AWS.
    """
    task = Task(task_name, config=ctx.obj['CONFIG'])
    adapter = ClickParameterAdapter(task)
    if to_env_file:
        click.secho('\n'.join(adapter.to_env_file()))
    else:
        if diff:
            click.secho('\n'.join(adapter.diff()))
        else:
            click.secho('\n'.join(adapter.list()))


@task_config.command('write', short_help="Write the config parameters to AWS System Manager Parameter Store")
@click.argument('task_name')
@click.option('--dry-run/--no-dry-run', default=False, help="Don't actually run the task")
@click.pass_context
@needs_config
def task_write_config(ctx, task_name, dry_run):
    """
    If the task TASK_NAME has a "config:" section defined, write
    all of the parameters for the task to AWS Parameter Store.
    """
    task = Task(task_name, config=ctx.obj['CONFIG'])
    click.secho('\n'.join(ClickParameterAdapter(task).write(dry_run=dry_run)))


@task.command(
    'entrypoint',
    short_help="Use for a Docker entrypoint",
    context_settings=dict(ignore_unknown_options=True)
)
@click.argument('command', nargs=-1)
@click.option('--dry-run/--no-dry-run', default=False, help="Just print what environment variables would be set")
@click.pass_context
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
    entrypoint = ClickTaskEntrypoint(config_file=ctx.obj['CONFIG_FILE'])
    try:
        entrypoint.entrypoint(command, dry_run=dry_run)
    except ClickTaskEntrypoint.DoesNotExist as e:
        print(str(e))
        sys.exit(1)
