import click

from deployfish.typing import FunctionTypeCommentParser
from deployfish.cli.adapters.utils import handle_model_exceptions, print_render_exception


class ClickTailLogStreamCommandMixin(object):

    @classmethod
    def add_tail_stream_click_command(cls, command_group):
        """
        Build a fully specified click command for tailing events from a CloudWatchLogStream, and add it to the click
        command group `command_group`.  Return the function object.

        :param command_group function: the click command group function to use to register our click command

        :rtype: function
        """
        def tail_log_stream(ctx, *args, **kwargs):
            ctx.obj['adapter'] = cls()
            ctx.obj['adapter'].tail_stream(
                kwargs['identifier'],
                kwargs['sleep'],
                kwargs['mark'],
            )

        pk_description = cls.get_pk_description()
        tail_log_stream.__doc__ = """
Eternally tail the events in the named log stream.   You'll need to use ^C to stop this command.

{pk_description}

""".format(pk_description=pk_description, object_name=cls.model.__name__)

        function = print_render_exception(tail_log_stream)
        function = click.pass_context(function)
        function = click.option(
            '--mark/--no-mark',
            default=False,
            help="Print out a line every --sleep seconds.  Use this to know that the log tailer isn't stuck.",
        )(function)
        function = click.option(
            '--sleep',
            default=10,
            help="Sleep this many seconds between polling logs",
            type=int
        )(function)
        function = click.argument('identifier')(function)
        function = command_group.command(
            'tail',
            short_help='Tail events from a CloudWatchLogs stream'
        )(function)
        return function

    @handle_model_exceptions
    def tail_stream(self, pk, sleep, mark, **kwargs):
        stream = self.get_object_from_aws(pk)
        tailer = stream.get_event_tailer(sleep=sleep)
        for page in tailer:
            for event in page:
                click.secho("{}  {}".format(
                    click.style(event['timestamp'].strftime('%Y-%m-%d %H:%M:%S.%f'), fg='cyan'),
                    event['message'].strip()
                ))
            if mark:
                click.secho("==============================  mark  ===================================", fg="yellow")


class ClickTailLogGroupCommandMixin(object):

    @classmethod
    def add_tail_group_click_command(cls, command_group):
        """
        Build a fully specified click command for tailing events from a CloudWatchLogStream, and add it to the click
        command group `command_group`.  Return the function object.

        :param command_group function: the click command group function to use to register our click command

        :rtype: function
        """
        def tail_log_group(ctx, *args, **kwargs):
            ctx.obj['adapter'] = cls()
            ctx.obj['adapter'].tail_group(
                kwargs['identifier'],
                kwargs['stream_prefix'],
                kwargs['sleep'],
                kwargs['filter_pattern'],
                kwargs['mark'],
            )

        args, kwargs = FunctionTypeCommentParser().parse(cls.model.get_event_tailer)
        pk_description = cls.get_pk_description()
        tail_log_group.__doc__ = """
Eternaly tail the events in the named log group, possibly filtering by log stream prefix and filter pattern.   You'll
need to use ^C to stop this command.

{pk_description}

""".format(pk_description=pk_description, object_name=cls.model.__name__)

        function = print_render_exception(tail_log_group)
        function = click.pass_context(function)
        function = click.option(
            '--mark/--no-mark',
            default=False,
            help="Print out a line every --sleep seconds.  Use this to know that the log tailer isn't stuck.",
        )(function)
        for key, kwarg in kwargs.items():
            function = cls.add_option(key, kwarg, function)
        for key, arg in args.items():
            function = cls.add_argument(key, arg, function)
        function = click.argument('identifier')(function)
        function = command_group.command(
            'tail',
            short_help='Tail events from a CloudWatchLogs group'
        )(function)
        return function

    @handle_model_exceptions
    def tail_group(self, pk, stream_prefix, sleep, filter_pattern, mark, **kwargs):
        group = self.get_object_from_aws(pk)
        tailer = group.get_event_tailer(
            stream_prefix=stream_prefix,
            sleep=sleep,
            filter_pattern=filter_pattern
        )
        for page in tailer:
            for event in page:
                click.secho("{}  {}".format(
                    click.style(event['timestamp'].strftime('%Y-%m-%d %H:%M:%S.%f'), fg='cyan'),
                    event['message'].strip()
                ))
            if mark:
                click.secho("==============================  mark  ===================================", fg="yellow")

