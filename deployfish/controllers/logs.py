import argparse
from typing import Type, Dict, Union, cast

from cement import App, ex
import click

from deployfish.core.models import (
    Model,
    Task,
    TaskDefinition,
    CloudWatchLogGroup,
    CloudWatchLogStream
)
from deployfish.ext.ext_df_argparse import DeployfishArgparseController as Controller
from deployfish.renderers.table import TableRenderer

from .crud import ReadOnlyCrudBase
from .utils import handle_model_exceptions


def tail_task_logs(
    app: App,
    obj: Task,
    sleep: int = 10,
    mark: bool = False,
    filter_pattern: str = None
) -> None:
    """
    Tail the logs for a Task of Task subclass to stdout.   How this actually
    works is that we poll the log group for the task, filter for the log stream
    name for the task and print to stdout any messages which have arrived since
    the last poll.  We sleep for ``sleep`` seconds between polls.

    Args:
        app: the top level Cement App.  We use this to access app.print()
        obj: the task object

    Keyword Arguments:
        sleep: sleep for this many seconds between polls.
        mark: if ``True``, print a line every ``sleep`` seconds.  This helps us see that
              we actually are looking at the logs, even if there are no new logs
        filter_pattern:  filter the log lines according to this pattern.

    Note:
        See (CloudWatch Log Filter Patterns|https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/FilterAndPatternSyntax.html)_ for info on how to format the ``filter_pattern``.
    """
    lc = cast(TaskDefinition, obj.task_definition).logging
    if lc['logDriver'] != 'awslogs':
        raise obj.OperationFailed(
            'Task log driver is "{}"; we can only tail "awslogs"'.format(lc['logDriver'])
        )
    group = CloudWatchLogGroup.objects.get(lc['options']['awslogs-group'])
    stream_prefix = lc['options']['awslogs-stream-prefix']
    tailer = group.get_event_tailer(
        stream_prefix=stream_prefix,
        sleep=sleep,
        filter_pattern=filter_pattern)
    for page in tailer:
        for event in page:
            app.print("{}  {}".format(
                click.style(event['timestamp'].strftime('%Y-%m-%d %H:%M:%S.%f'), fg='cyan'),
                event['message'].strip()
            ))
        if mark:
            app.print(click.style(
                "==============================  mark  ===================================",
                fg="yellow"
            ))


def list_log_streams(app: App, obj: Task, limit=None) -> None:
    """
    Build a table of all available log streams for a Task and print it to stdout.

    Args:
        app: the top level Cement App.  We use this to access app.print()
        obj: the task object

    Keyword Arguments:
        limit: limit the number of streams to the ``limit`` most recent ones
    """
    lc = cast(TaskDefinition, obj.task_definition).logging
    if lc['logDriver'] != 'awslogs':
        raise obj.OperationFailed(
            'Task log driver is "{}"; we can only tail "awslogs"'.format(lc['logDriver'])
        )
    group = CloudWatchLogGroup.objects.get(lc['options']['awslogs-group'])
    stream_prefix = lc['options']['awslogs-stream-prefix']
    streams = group.log_streams(stream_prefix=stream_prefix, maxitems=limit)
    columns = {
        'Stream Name': 'logStreamName',
        'Created': {'key': 'creationTime', 'datatype': 'timestamp'},
        'Last Event': {
            'key': 'lastEventTimestamp',
            'datatype': 'timestamp',
            'default': ''
        },
    }
    app.print(TableRenderer(columns, ordering='-Created').render(streams))


class Logs(Controller):

    class Meta:
        label = 'logs'
        description = 'Work with CloudWatch Logs'
        help = 'Work with CloudWatch Logs'
        stacked_type = 'nested'


class LogsCloudWatchLogGroup(ReadOnlyCrudBase):

    class Meta:
        label = 'awslog-groups'
        description = 'Work with CloudWatch Log Group objects'
        help = 'Work with CloudWatch Log Group objects'
        stacked_on = 'logs'
        stacked_type = 'nested'

    model: Type[Model] = CloudWatchLogGroup

    help_overrides: Dict[str, str] = {
        'info': 'Show details about a CloudWatch Log Group in AWS',
    }

    info_template: str = 'detail--cloudwatchloggroup.jinja2'

    list_ordering: str = 'Name'
    list_result_columns: Dict[str, Union[str, Dict[str, str]]] = {
        'Name': 'logGroupName',
        'Created': {'key': 'creationTime', 'datatype': 'timestamp'},
        'Retention': {'key': 'retentionInDays', 'default': 'inf'},
        'Size': {'key': 'storedBytes', 'datatype': 'bytes'}
    }

    @ex(
        help="List CloudWatch Log Groups in AWS",
        arguments=[
            (
                ['--prefix'],
                {
                    'help': 'Filter by prefix',
                    'action': 'store',
                    'default': None,
                    'dest': 'prefix'
                }
            ),
        ]
    )
    @handle_model_exceptions
    def list(self):
        results = self.model.objects.list(
            prefix=self.app.pargs.prefix,
        )
        self.render_list(results)

    @ex(
        help='Tail logs for from a CloudWatch Logs Group.',
        arguments=[
            (['name'], { 'help' : 'The name of the CloudWatch Logs Log Group in AWS'}),
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
            (
                ['--stream-prefix'],
                {
                    'help': 'Return only messages from stream names with this prefix .',
                    'default': None,
                    'dest': 'stream_prefix',
                }
            ),
        ],
        description="""
Tail the logs for a CloudWatch Logs Log Group.
""",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    @handle_model_exceptions
    def tail(self) -> None:
        loader = self.loader(self)
        obj = loader.get_object_from_aws(self.app.pargs.name)
        group = cast("CloudWatchLogGroup", obj)
        tailer = group.get_event_tailer(
            stream_prefix=self.app.pargs.stream_prefix,
            sleep=self.app.pargs.sleep,
            filter_pattern=self.app.pargs.filter_pattern
        )
        for page in tailer:
            for event in page:
                self.app.print(
                    click.style("{}  {}".format(
                        click.style(event['timestamp'].strftime('%Y-%m-%d %H:%M:%S.%f'), fg='cyan'),
                        event['message'].strip()
                    ))
                )
            if self.app.pargs.mark:
                self.app.print(
                    click.style(
                        "==============================  mark  ===================================",
                        fg="yellow"
                    )
                )


class LogsCloudWatchLogStream(ReadOnlyCrudBase):

    class Meta:
        label = 'awslog-streams'
        description = 'Work with CloudWatch Log Stream objects'
        help = 'Work with CloudWatch Log Stream objects'
        stacked_on = 'logs'
        stacked_type = 'nested'

    model: Type[Model] = CloudWatchLogStream

    help_overrides: Dict[str, str] = {
        'info': 'Show details about a CloudWatch Log Group in AWS',
    }

    info_template: str = 'detail--cloudwatchlogstream.jinja2'

    list_ordering: str = 'Name'
    list_result_columns: Dict[str, Union[str, Dict[str, str]]] = {
        'Name': 'logStreamName',
        'Group': 'logGroupName',
        'Created': {'key': 'creationTime', 'datatype': 'timestamp'},
        'lastEventTimestamp': {'key': 'lastEventTimestamp', 'datatype': 'timestamp', 'default': ''},
    }


    @ex(
        help="List CloudWatch Log Groups in AWS",
        arguments=[
            (['log_group_name'], {'help': 'The name of the log group whose streams we want to list'}),
            (
                ['--prefix'],
                {
                    'help': 'Filter by prefix',
                    'action': 'store',
                    'default': None,
                    'dest': 'prefix'
                }
            ),
            (
                ['--limit'],
                {
                    'help': 'Limit results to this number',
                    'action': 'store',
                    'type': int,
                    'default': None,
                    'dest': 'limit'
                }
            ),
        ]
    )
    @handle_model_exceptions
    def list(self):
        results = self.model.objects.list(
            self.app.pargs.log_group_name,
            prefix=self.app.pargs.prefix,
            limit=self.app.pargs.limit
        )
        self.render_list(results)

    @ex(
        help='Tail logs for from a CloudWatch Logs Strem.',
        arguments=[
            (['pk'], { 'help' : 'The primary key for the CloudWatch Logs Log Streamin AWS'}),
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
            )
        ],
        description="""
Tail the logs for a CloudWatch Logs Log Stream.

The pk for a log stream is "{log_group_name}:{log_stream_id}"
""",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    @handle_model_exceptions
    def tail(self) -> None:
        loader = self.loader(self)
        obj = loader.get_object_from_aws(self.app.pargs.pk)
        stream = cast("CloudWatchLogStream", obj)
        tailer = stream.get_event_tailer(sleep=self.app.pargs.sleep)
        for page in tailer:
            for event in page:
                self.app.print(click.style("{}  {}".format(
                    click.style(event['timestamp'].strftime('%Y-%m-%d %H:%M:%S.%f'), fg='cyan'),
                    event['message'].strip()
                )))
            if self.app.pargs.mark:
                self.app.print(
                    click.style(
                        "==============================  mark  ===================================",
                        fg="yellow"
                    )
                )
