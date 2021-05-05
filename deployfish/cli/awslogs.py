from .adapters import ClickCloudWatchLogGroupAdapter, ClickCloudWatchLogStreamAdapter

from .cli import cli


@cli.group('logs', help='Describe service and task logs')
def logs():
    pass


loggroup_group = ClickCloudWatchLogGroupAdapter.add_command_group(logs, 'awslog-groups')
loggroup_list = ClickCloudWatchLogGroupAdapter.add_list_click_command(loggroup_group)
loggroup_info = ClickCloudWatchLogGroupAdapter.add_info_click_command(loggroup_group)
loggroup_exists = ClickCloudWatchLogGroupAdapter.add_exists_click_command(loggroup_group)
loggroup_tail = ClickCloudWatchLogGroupAdapter.add_tail_group_click_command(loggroup_group)

logstream_group = ClickCloudWatchLogStreamAdapter.add_command_group(logs, 'awslog-streams')
logstream_list = ClickCloudWatchLogStreamAdapter.add_list_click_command(logstream_group)
logstream_info = ClickCloudWatchLogStreamAdapter.add_info_click_command(logstream_group)
logstream_exists = ClickCloudWatchLogStreamAdapter.add_exists_click_command(logstream_group)
logstream_tail = ClickCloudWatchLogStreamAdapter.add_tail_stream_click_command(logstream_group)
