from .adapters import ClickServiceAdapter, ClickServiceSecretsAdapter, ClickServiceTasksAdapter

from .cli import cli

service_group = ClickServiceAdapter.add_command_group(cli, 'service')
service_create = ClickServiceAdapter.add_create_click_command(service_group)
service_update = ClickServiceAdapter.add_update_click_command(service_group)
service_list = ClickServiceAdapter.add_list_click_command(service_group)
service_info = ClickServiceAdapter.add_info_click_command(service_group)
service_exists = ClickServiceAdapter.add_exists_click_command(service_group)
service_delete = ClickServiceAdapter.add_delete_click_command(service_group)
service_ssh = ClickServiceAdapter.add_ssh_click_command(service_group)
service_exec = ClickServiceAdapter.add_exec_click_command(service_group)
service_tunnel = ClickServiceAdapter.add_tunnel_click_command(service_group)
service_scale = ClickServiceAdapter.add_scale_service_click_command(service_group)
service_restart = ClickServiceAdapter.add_restart_service_click_command(service_group)
service_update_related_tasks = ClickServiceAdapter.add_update_related_tasks_click_command(service_group)

service_secrets_group = ClickServiceSecretsAdapter.add_command_group(
    service_group,
    'config',
    short_help='Manage AWS Parameter Store secrets for a Service'
)
service_secrets_diff = ClickServiceSecretsAdapter.add_diff_secrets_command(service_secrets_group)
service_secrets_show = ClickServiceSecretsAdapter.add_show_secrets_command(service_secrets_group)
service_secrets_write = ClickServiceSecretsAdapter.add_write_secrets_command(service_secrets_group)
service_secrets_export = ClickServiceSecretsAdapter.add_export_secrets_command(service_secrets_group)

service_command_group = ClickServiceTasksAdapter.add_command_group(
    service_group,
    'commands',
    short_help='Manage Commands (ServiceHelperTasks) for a Service'
)
service_command_list = ClickServiceTasksAdapter.add_list_helper_tasks_click_command(service_command_group)
service_command_info = ClickServiceTasksAdapter.add_helper_task_info_click_command(service_command_group)
service_command_run = ClickServiceTasksAdapter.add_run_helper_task_click_command(service_command_group)
service_command_update = ClickServiceTasksAdapter.add_update_helper_tasks_click_command(service_command_group)


@service_command_group.group('logs', help='Describe service and command logs')
def service_tasks_logs():
    pass


service_tasks_tail = ClickServiceTasksAdapter.add_tail_logs_click_command(service_tasks_logs)
service_tasks_list = ClickServiceTasksAdapter.add_list_logs_click_command(service_tasks_logs)
