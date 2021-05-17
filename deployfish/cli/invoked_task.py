from .adapters import ClickInvokedTaskAdapter

from .cli import cli

invoked_task_group = ClickInvokedTaskAdapter.add_command_group(cli, 'invoked-tasks')
invoked_task_list = ClickInvokedTaskAdapter.add_list_click_command(invoked_task_group)
invoked_task_info = ClickInvokedTaskAdapter.add_info_click_command(invoked_task_group)
invoked_task_exists = ClickInvokedTaskAdapter.add_exists_click_command(invoked_task_group)
invoked_task_exec = ClickInvokedTaskAdapter.add_ssh_click_command(invoked_task_group)
