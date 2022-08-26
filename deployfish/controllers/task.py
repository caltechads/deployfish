import argparse
from typing import Any, Sequence, Type, Dict, cast

from cement import ex
import click

from deployfish.core.loaders import ObjectLoader
from deployfish.core.models import (
    InvokedTask,
    Model,
    StandaloneTask
)
from deployfish.core.waiters.hooks.ecs import ECSTaskStatusHook
from deployfish.ext.ext_df_argparse import DeployfishArgparseController as Controller

from .crud import CrudBase
from .logs import tail_task_logs, list_log_streams
from .secrets import ObjectSecretsController
from .utils import handle_model_exceptions


class ECSStandaloneTask(CrudBase):

    class Meta:
        label = 'task'
        description = 'Work with ECS Standalone Task objects'
        help = 'Work with ECS Standalone Task objects'
        stacked_type = 'nested'

    model: Type[Model] = StandaloneTask
    help_overrides: Dict[str, str] = {
        'info': 'Show details about an ECS Standalone Task object from AWS',
        'create': 'Create an ECS StandaloneTask in AWS from what is in deployfish.yml',
        'update': 'Update an ECS StandaloneTask in AWS from what is in deployfish.yml',
        'delete': 'Delete an ECS StandaloneTask from AWS'
    }

    info_template: str = 'detail--standalonetask.jinja2'

    # --------------------
    # .list() related vars
    # --------------------
    list_ordering: str = 'Name'
    list_result_columns: Dict[str, Any] = {
        'Name': 'name',
        'Disabled?': 'schedule_disabled',
        'Service': {'key': 'serviceName', 'default': ''},
        'Cluster': 'cluster__name',
        'Launch Type': 'launchType',
        'Revision': 'revision',
        'Version': 'version',
        'Schedule': 'schedule_expression'
    }

    # --------------------
    # .update() related vars
    # --------------------
    update_template: str = 'detail--standalonetask--short.jinja2'

    @ex(
        help="Show about an existing ECS Standalone Task in AWS",
        arguments=[
            (['pk'], { 'help' : 'The primary key for the ECS Service'}),
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
    )
    @handle_model_exceptions
    def info(self):
        loader = self.loader(self)
        obj = loader.get_object_from_aws(self.app.pargs.pk)
        context = {
            'obj': obj,
            'includes': self.app.pargs.includes if self.app.pargs.includes else [],
            'excludes': self.app.pargs.excludes if self.app.pargs.excludes else [],
        }
        self.app.render(context, template=self.info_template)

    @ex(
        help="List ECS StandaloneTasks in AWS",
        arguments=[
            (
                ['--cluster-name'],
                {
                    'help': 'Filter by cluster name, with globs. Ex: "foo*", "*foo"',
                    'default': None,
                    'dest': 'cluster_name'
                }
            ),
            (
                ['--service-name'],
                {
                    'help': 'Filter by service name, with globs. Ex: "foo*", "*foo"',
                    'default': None,
                    'dest': 'service_name'
                }
            ),
            (
                ['--task-name'],
                {
                    'help': 'Filter by task name, with globs. Ex: "foo*", "*foo"',
                    'default': None,
                    'dest': 'task_name'
                }
            ),
            (
                ['--task-type'],
                {
                    'help': 'Filter by task type.',
                    'default': 'standalone',
                    'choices': ['any', 'standalone', 'service_helper'],
                    'dest': 'task_type'
                }
            ),
            (
                ['--scheduled-only'],
                {
                    'help': 'Only list tasks that have schedules',
                    'action': 'store_true',
                    'default': False,
                    'dest': 'scheduled_only'
                }
            ),
            (
                ['--all-revisions'],
                {
                    'help': 'List all revisions instead of only the most recent one per family.',
                    'action': 'store_true',
                    'default': False,
                    'dest': 'all_revisions',
                }
            ),
        ]
    )
    @handle_model_exceptions
    def list(self):
        results = self.model.objects.list(
            scheduled_only=self.app.pargs.scheduled_only,
            all_revisions=self.app.pargs.all_revisions,
            task_type=self.app.pargs.task_type,
            cluster_name=self.app.pargs.cluster_name,
            service_name=self.app.pargs.service_name,
            task_name=self.app.pargs.task_name
        )
        self.render_list(results)

    # Create

    @ex(
        help="Create an object in AWS",
        arguments=[
            (['name'], {'help': 'The name of the item from deployfish.yml'})
        ]
    )
    @handle_model_exceptions
    def create(self):
        self.update()

    # Delete

    @ex(
        help="Delete an object from AWS",
        arguments=[
            (['name'], {'help': 'The name of the item from deployfish.yml'})
        ]
    )
    @handle_model_exceptions
    def delete(self):
        """
        Delete an object from AWS by primary key.
        """
        raise StandaloneTask.OperationFailed('StandaloneTasks cannot be deleted.')

    # Enable

    @ex(
        help='Enable the schedule for a Standalone Task.',
        arguments=[
            (['pk'], { 'help' : 'The primary key for the StandaloneTask in AWS'}),
        ],
        description="""
If a StandaloneTask has a schedule rule and that rule is currently disabled in AWS, enable it.
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
        obj = cast(StandaloneTask, obj)
        if obj.schedule is None:
            raise StandaloneTask.OperationFailed(
                f'ABORT: StandaloneTask("{obj.name}") has no schedule; '
                'enabling only affects schedules.'
            )
        obj.enable_schedule()
        if obj.schedule.enabled:
            self.app.print(
                click.style(f'Schedule for StandaloneTask("{obj.name}") now ENABLED.', fg='green')
            )
            self.app.print(f'Schedule: {obj.schedule_expression}')
        else:
            self.app.print(
                click.style(f'Schedule for StandaloneTask("{obj.name}") is now DISABLED.', fg='red')
            )

    # Disable

    @ex(
        help='Disable the schedule for a command for a StandaloneTask.',
        arguments=[
            (['pk'], { 'help' : 'The primary key for the ECS StandaloneTask in AWS'}),
        ],
        description="""
If a StandaloneTask has a schedule rule and that rule is currently enabled in AWS, disable it.
"""
    )
    @handle_model_exceptions
    def disable(self) -> None:
        """
        If a StandaloneTask has a schedule rule and that rule is currently enabled in AWS, disable it.
        """
        loader = self.loader(self)
        obj = loader.get_object_from_aws(self.app.pargs.pk)
        obj = cast(StandaloneTask, obj)
        if obj.schedule is None:
            raise StandaloneTask.OperationFailed(
                f'ABORT: StandaloneTask("{obj.name}") has no schedule; '
                'disabling only affects schedules.'
            )
        obj.disable_schedule()
        if obj.schedule.enabled:
            self.app.print(
                click.style(f'Schedule for StandaloneTask("{obj.name}") now ENABLED.', fg='green')
            )
            self.app.print(f'Schedule: {obj.schedule_expression}')
        else:
            self.app.print(
                click.style(f'Schedule for StandaloneTask("{obj.name}") is now DISABLED.', fg='red')
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
            (['pk'], { 'help' : 'The primary key for the StandaloneTask in AWS'}),
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
Run a StandaloneTask that exists in AWS.
"""
    )
    @handle_model_exceptions
    def run(self) -> None:
        """
        Run a StandaloneTask.
        """
        loader = self.loader(self)
        obj = loader.get_object_from_aws(self.app.pargs.pk)
        standalone_task = cast(StandaloneTask, obj)
        tasks = standalone_task.run()
        lines = []
        for task in tasks:
            lines.append(
                click.style('\nStarted task: {}:{}\n'.format(standalone_task.data['cluster'], task.arn), fg='green')
            )
        self.app.print('\n'.join(lines))
        if self.app.pargs.wait:
            self.run_task_waiter(tasks)


class ECSStandaloneTaskSecrets(ObjectSecretsController):

    class Meta:
        label = 'task-secrets'
        aliases = ['config']
        stacked_on = 'task'
        description = 'Work with ECS Standalone Task Secrets'
        help = 'Work with ECS Standalone Task Secrets'
        stacked_type = 'nested'

    model: Type[Model] = StandaloneTask


class ECSStandaloneTaskLogs(Controller):

    class Meta:
        label = 'task-logs'
        aliases = ['logs']
        description = 'Work with logs for an ECS StandaloneTask'
        help = 'Work with logs for an ECS StandaloneTask'
        stacked_on = 'task'
        stacked_type = 'nested'

    model: Type[Model] = StandaloneTask
    loader: Type[ObjectLoader] = ObjectLoader

    # tail

    @ex(
        help='Tail logs for a StandaloneTask.',
        arguments=[
            (['pk'], { 'help' : 'The primary key for the ECS StandaloneTask in AWS'}),
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
If a StandaloneTask uses "awslogs" as its logDriver, tail the logs for that command.

For --filter-pattern syntax , see
https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/FilterAndPatternSyntax.html
""",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    @handle_model_exceptions
    def tail(self) -> None:
        """
        If a StandaloneTask uses "awslogs" as its logDriver, tail the logs for that ServiceHelperTask.
        """
        loader = self.loader(self)
        obj = loader.get_object_from_aws(self.app.pargs.pk)
        obj = cast(StandaloneTask, obj)
        tail_task_logs(
            self.app,
            obj,
            sleep=self.app.pargs.sleep,
            mark=self.app.pargs.mark,
            filter_pattern=self.app.pargs.filter_pattern
        )

    # list

    @ex(
        help='List log streams for a StandaloneTask.',
        arguments=[
            (['pk'], { 'help' : 'The primary key for the ECS StandaloneTask in AWS'}),
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
If a command for a StandaloneTask uses "awslogs" as its logDriver, list the available
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
        obj = cast(StandaloneTask, obj)
        list_log_streams(self.app, obj, limit=self.app.pargs.limit)
