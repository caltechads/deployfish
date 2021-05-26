from .adapters import ClickSSHTunnelAdapter, ClickServiceAdapter, ClickServiceSecretsAdapter
from .cli import cli


tunnel_top = ClickSSHTunnelAdapter.add_tunnel_click_command(cli)

service_create_top = ClickServiceAdapter.add_create_click_command(cli)
service_update_top = ClickServiceAdapter.add_update_click_command(cli)
service_info_top = ClickServiceAdapter.add_info_click_command(cli)
service_delete_top = ClickServiceAdapter.add_delete_click_command(cli)
service_ssh_top = ClickServiceAdapter.add_ssh_click_command(cli)
service_exec_top = ClickServiceAdapter.add_exec_click_command(cli)
service_scale_top = ClickServiceAdapter.add_scale_service_click_command(cli)
service_restart_top = ClickServiceAdapter.add_restart_service_click_command(cli)

service_secrets_group_top = ClickServiceSecretsAdapter.add_command_group(
    cli,
    'config',
    short_help='Manage AWS Parameter Store secrets for a Service'
)
service_secrets_diff_top = ClickServiceSecretsAdapter.add_diff_secrets_command(service_secrets_group_top)
service_secrets_show_top = ClickServiceSecretsAdapter.add_show_secrets_command(service_secrets_group_top)
service_secrets_write_top = ClickServiceSecretsAdapter.add_write_secrets_command(service_secrets_group_top)
service_secrets_export_top = ClickServiceSecretsAdapter.add_export_secrets_command(service_secrets_group_top)
service_secrets_sync_top = ClickServiceSecretsAdapter.add_sync_secrets_command(service_secrets_group_top)
