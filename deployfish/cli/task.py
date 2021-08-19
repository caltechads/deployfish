from .adapters import ClickStandaloneTaskAdapter, ClickStandaloneTaskSecretsAdapter

from .cli import cli

task_group = ClickStandaloneTaskAdapter.add_command_group(cli, 'task')
task_update = ClickStandaloneTaskAdapter.add_update_click_command(task_group)
task_list = ClickStandaloneTaskAdapter.add_list_click_command(task_group)
task_info = ClickStandaloneTaskAdapter.add_info_click_command(task_group)
task_exists = ClickStandaloneTaskAdapter.add_exists_click_command(task_group)
task_run = ClickStandaloneTaskAdapter.add_run_task_click_command(task_group)
task_enable = ClickStandaloneTaskAdapter.add_enable_schedule_click_command(task_group)
task_disable = ClickStandaloneTaskAdapter.add_disable_schedule_click_command(task_group)

task_secrets_group = ClickStandaloneTaskSecretsAdapter.add_command_group(
    task_group,
    'config',
    short_help='Manage AWS Parameter Store secrets for StandaloneTasks'
)
task_secrets_diff = ClickStandaloneTaskSecretsAdapter.add_diff_secrets_command(task_secrets_group)
task_secrets_show = ClickStandaloneTaskSecretsAdapter.add_show_secrets_command(task_secrets_group)
task_secrets_write = ClickStandaloneTaskSecretsAdapter.add_write_secrets_command(task_secrets_group)
task_secrets_export = ClickStandaloneTaskSecretsAdapter.add_export_secrets_command(task_secrets_group)


@task_group.group('logs', help='Work with StandaloneTask logs')
def service_tasks_logs():
    pass


service_tasks_tail = ClickStandaloneTaskAdapter.add_tail_logs_click_command(service_tasks_logs)
service_tasks_list = ClickStandaloneTaskAdapter.add_list_logs_click_command(service_tasks_logs)
