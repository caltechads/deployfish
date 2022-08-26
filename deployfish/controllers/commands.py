import argparse
from typing import Any, Type, Sequence, Dict, cast

from cement import ex
import click

from deployfish.core.loaders import ObjectLoader, ServiceLoader
from deployfish.core.models import (
    InvokedTask,
    Model,
    Service,
    ServiceHelperTask
)
from deployfish.core.waiters.hooks.ecs import ECSTaskStatusHook
from deployfish.ext.ext_df_argparse import DeployfishArgparseController as Controller
from deployfish.renderers.table import TableRenderer

from .logs import list_log_streams, tail_task_logs
from .utils import handle_model_exceptions


def get_task(obj: Service, name: str) -> ServiceHelperTask:
    """
    Return the ``ServiceHelperTask`` whose related to ``obj`` whose command name matches
    ``name``.

    Args:
        obj: A Service Model object
        name: the name of a command on obj

    Raises:
        ServiceHelperTask.DoesNotExist: no command named ``name`` exists on ``obj``

    Returns:
        The ``ServiceHelperTask`` object
    """
    task = None
    for t in obj.helper_tasks:
        if t.command == name:
            task = t
            break
    if not task:
        lines = []
        lines.append(click.style('No command named "{}" exists on Service("{}").\n'.format(name, obj.pk), fg='red'))
        lines.append(click.style('Available helper tasks:\n', fg='cyan'))
        lines.append(
            TableRenderer({
                'Service': 'serviceName',
                'Name': 'name',
                'Revision': 'family_revision',
                'Version': 'version',
                'Launch Type': 'launchType',
                'Schedule': 'schedule_expression'
            }, ordering='Name').render(obj.helper_tasks)
        )
        raise ServiceHelperTask.DoesNotExist('\n'.join(lines))
    return task


class ECSServiceCommands(Controller):

    class Meta:
        label = 'commands'
        description = 'Work with Helper Tasks for an ECS Service'
        help = 'Work with Helper Takss for an ECS Service'
        stacked_on = 'service'
        stacked_type = 'nested'

    model: Type[Model] = Service
    loader: Type[ObjectLoader] = ServiceLoader

    # --------------------
    # .info() related vars
    # --------------------
    # Which template should we use when showing .info() output?
    info_template: str = 'detail--servicehelpertask.jinja2'

    # --------------------
    # .list() related vars
    # --------------------
    # The name of the column HEADER by which to order the output table
    list_ordering: str = 'Command Name'
    # Configuration for TableRenderer.  See the help for deployfish.renderers.table.TableRenderer
    # for instructions.
    list_result_columns: Dict[str, Any] = {
        'Command Name': 'command',
        'Disabled?': 'schedule_disabled',
        'Revision': 'family_revision',
        'Version': 'version',
        'Launch Type': 'launchType',
        'Schedule': 'schedule_expression'
    }

    def wait(self, operation: str, **kwargs) -> None:
        """
        Build a ``deployfish.core.waiters.HookedWaiter`` for the operation named
        ``operation`` and with configuration ``kwargs``, and then run it.

        ``operation`` can be any waiter operation that boto3 supports for ``self.model`` type objects.
        """
        waiter = self.model.objects.get_waiter(operation)
        waiter.wait(**kwargs)

    # Info

    @ex(
        help='Show info about a command for an ECS Service in AWS',
        arguments=[
            (['pk'], { 'help' : 'The primary key for the ECS Service in AWS'}),
            (['command'], { 'help' : 'The command name'}),
            (
                ['--includes'],
                {
                    'help': 'Include optional information not normally shown.',
                    'action': 'store',
                    'default': None,
                    'choices': ['secrets'],
                    'dest': 'includes',
                    'nargs': "+"
                }
            )
        ],
        description="""
Show info about a command associated with a Service that exists in AWS.
"""
    )
    @handle_model_exceptions
    def info(self) -> None:
        """
        Show info about a ServiceHelperTask object associated with a Service that exists in AWS.
        """
        loader = self.loader(self)
        obj = loader.get_object_from_aws(self.app.pargs.pk)
        obj = cast(Service, obj)
        task = get_task(obj, self.app.pargs.command)
        context = {
            'obj': task,
            'includes': self.app.pargs.includes if self.app.pargs.includes is not None else {}
        }
        self.app.render(context, template=self.info_template)

    # List

    @ex(
        help='List the available commands for a Service in AWS.',
        arguments=[
            (['pk'], { 'help' : 'The primary key for the ECS Service in AWS'})
        ]
    )
    @handle_model_exceptions
    def list(self) -> None:
        """
        List the helper tasks associated with a Service in AWS.
        """
        loader = self.loader(self)
        obj = loader.get_object_from_aws(self.app.pargs.pk)
        obj = cast(Service, obj)
        tasks = obj.helper_tasks
        renderer = TableRenderer(
            columns=self.list_result_columns,
            ordering=self.list_ordering
        )
        self.app.print(renderer.render(tasks))

    # Update

    @ex(
        help='Update command defintions in AWS independently of their Service',
        arguments=[
            (['pk'], { 'help' : 'The primary key for the ECS Service in AWS'})
        ],
        description="""
Update all the Service's ServiceHelperTasks in AWS independently of the Service,
and return the new task defintiion family:revision for each.

This command exists because while we normally update ServiceHelperTasks
automatically when their Service is updated, sometimes we want to update a
ServiceHelperTask without touching the Service.  For example, when we want to
run our database migrations before updating the code for the Service.

NOTE: The ServiceHelperTasks you write with this command won't be directly
associated with the live Service in AWS, like they would when doing "deploy
service update".  So to run these tasks, use the family:revision returned by
this command with "deploy task run" instead of running them with 
"deploy service commands run".
""",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    @handle_model_exceptions
    def update(self) -> None:
        """
        Update command defintions in AWS independently of their Service.
        """
        loader = self.loader(self)
        obj = loader.get_object_from_deployfish(
            self.app.pargs.pk,
            factory_kwargs={'load_secrets': False}
        )
        obj = cast(Service, obj)
        self.app.print(
            click.style(f'\n\nUpdating ServiceHelperTasks associated with Service("{obj.pk}"):\n', fg='yellow')
        )
        for task in obj.helper_tasks:
            click.secho('UPDATE: {} -> '.format(task.command), nl=False)
            arn = task.save()
            family_revision = arn.rsplit('/')[1]
            self.app.print(family_revision)
        self.app.print(click.style('\nDone.', fg='yellow'))

    # Enable

    @ex(
        help='Enable the schedule for a command for a Service.',
        arguments=[
            (['pk'], { 'help' : 'The primary key for the ECS Service in AWS'}),
            (['command'], { 'help' : 'The command name'}),
        ],
        description="""
If a command for a Service has a schedule rule and that rule is currently
disabled in AWS, enable it.
"""
    )
    @handle_model_exceptions
    def enable(self) -> None:
        """
        If a command for a Service has a schedule rule and that rule is currently
        disabled in AWS, enable it.
        """
        loader = self.loader(self)
        obj = loader.get_object_from_aws(self.app.pargs.pk)
        obj = cast(Service, obj)
        command = get_task(obj, self.app.pargs.command)
        if command.schedule is None:
            raise ServiceHelperTask.OperationFailed(
                f'ABORT: Command "{command.name}" on Service("{obj.pk}") has no schedule; '
                'enabling only affects schedules.'
            )
        command.enable_schedule()
        if command.schedule.enabled:
            self.app.print(
                click.style(f'Schedule for command "{command.name}" on Service("{obj.pk}") is now ENABLED.', fg='green')
            )
            self.app.print(f'Schedule: {command.schedule_expression}')
        else:
            self.app.print(
                click.style(f'Schedule for command "{command.name}" on Service("{obj.pk}") is now DISABLED.', fg='red')
            )

    # Disable

    @ex(
        help='Disable the schedule for a command for a Service.',
        arguments=[
            (['pk'], { 'help' : 'The primary key for the ECS Service in AWS'}),
            (['command'], { 'help' : 'The command name'}),
        ],
        description="""
If a command for a Service has a schedule rule and that rule is currently
enabled in AWS, disable it.
"""
    )
    @handle_model_exceptions
    def disable(self) -> None:
        """
        If a command for a Service has a schedule rule and that rule is currently
        enabled in AWS, disable it.
        """
        loader = self.loader(self)
        obj = loader.get_object_from_aws(self.app.pargs.pk)
        obj = cast(Service, obj)
        command = get_task(obj, self.app.pargs.command)
        if command.schedule is None:
            raise ServiceHelperTask.OperationFailed(
                f'ABORT: Command "{command.name}" on Service("{obj.pk}") has no schedule; '
                'disabling only affects schedules.'
            )
        command.disable_schedule()
        if command.schedule.enabled:
            self.app.print(
                click.style(f'Schedule for command "{command.name}" on Service("{obj.pk}") is now ENABLED.', fg='green')
            )
            self.app.print(f'Schedule: {command.schedule_expression}')
        else:
            self.app.print(
                click.style(f'Schedule for command "{command.name}" on Service("{obj.pk}") is now DISABLED.', fg='red')
            )



    # Run

    def run_task_waiter(self, tasks: Sequence[InvokedTask], **kwargs) -> None:
        kwargs['WaiterHooks'] = [ECSTaskStatusHook(tasks)]
        kwargs['tasks'] = [t.arn for t in tasks]
        kwargs['cluster'] = tasks[0].cluster_name
        self.wait('tasks_stopped', **kwargs)

    @ex(
        help='Run one of a service\'s helper tasks',
        arguments=[
            (['pk'], { 'help' : 'The primary key for the ECS Service in AWS'}),
            (['command'], { 'help' : 'The command name'}),
            (
                ['--wait'],
                {
                    'help': 'Wait until the command finshes.',
                    'action': 'store_true',
                    'default': False,
                    'dest': 'wait',
                }
            )
        ],
        description="""
Run a command associated with a Service that exists in AWS.
"""
    )
    @handle_model_exceptions
    def run(self) -> None:
        """
        Show info about a ServiceHelperTask object associated with a Service that exists in AWS.
        """
        loader = self.loader(self)
        obj = loader.get_object_from_aws(self.app.pargs.pk)
        obj = cast(Service, obj)
        command = get_task(obj, self.app.pargs.command)
        tasks = command.run()
        lines = []
        for task in tasks:
            lines.append(click.style('\nStarted task: {}:{}\n'.format(command.data['cluster'], task.arn), fg='green'))
        self.app.print('\n'.join(lines))
        if self.app.pargs.wait:
            self.run_task_waiter(tasks)  # type: ignore


class ECSServiceCommandLogs(Controller):

    class Meta:
        label = 'command-logs'
        aliases = ['logs']
        description = 'Work with logs for commands for an ECS Service'
        help = 'Work with logs for commands for an ECS Service'
        stacked_on = 'commands'
        stacked_type = 'nested'

    model: Type[Model] = Service
    loader: Type[ObjectLoader] = ServiceLoader

    # tail

    @ex(
        help='Tail logs for a ServiceHelperTask.',
        arguments=[
            (['pk'], { 'help' : 'The primary key for the ECS Service in AWS'}),
            (['command'], { 'help' : 'The command name'}),
            (
                ['--mark'],
                {
                    'help': 'Print out a line every --sleep seconds.',
                    'action': 'store_true',
                    'default': False,
                    'dest': 'mark',
                }
            ),
            (
                ['--sleep'],
                {
                    'help': 'Sleep for this many seconds between polling Cloudwatch Logs for new messages.',
                    'type': int,
                    'default': 10,
                    'dest': 'sleep',
                }
            ),
            (
                ['--filter-pattern'],
                {
                    'help': 'Return only messages matching this filter.',
                    'default': None,
                    'dest': 'filter_pattern',
                }
            ),
        ],
        description="""
If a command for a Service uses "awslogs" as its logDriver, tail the logs for that command.

For --filter-pattern syntax , see
https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/FilterAndPatternSyntax.html
""",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    @handle_model_exceptions
    def tail(self) -> None:
        """
        If a ServiceHelperTask uses "awslogs" as its logDriver, tail the logs for that ServiceHelperTask.
        """
        loader = self.loader(self)
        obj = loader.get_object_from_aws(self.app.pargs.pk)
        obj = cast(Service, obj)
        command = get_task(obj, self.app.pargs.command)
        tail_task_logs(
            self.app,
            command,
            sleep=self.app.pargs.sleep,
            mark=self.app.pargs.mark,
            filter_pattern=self.app.pargs.filter_pattern
        )

    # list

    @ex(
        help='List log streams for a ServiceHelperTask.',
        arguments=[
            (['pk'], { 'help' : 'The primary key for the ECS Service in AWS'}),
            (['command'], { 'help' : 'The command name'}),
            (
                ['--limit'],
                {
                    'help': 'Limit the number of streams listed.',
                    'default': None,
                    'type': int,
                    'dest': 'limit',
                }
            ),
        ],
        description="""
If a command for a Service uses "awslogs" as its logDriver, list the available
log streams for that StandaloneTask.

This can be useful when you have a command with a schedule to look at the dates on 
the streams to ensure that your command is actually running periodically.
""",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    @handle_model_exceptions
    def list(self) -> None:
        """
        If a ServiceHelperTask uses "awslogs" as its logDriver, tail the logs
        for that ServiceHelperTask.
        """
        loader = self.loader(self)
        obj = loader.get_object_from_aws(self.app.pargs.pk)
        obj = cast(Service, obj)
        command = get_task(obj, self.app.pargs.command)
        list_log_streams(self.app, command, limit=self.app.pargs.limit)
