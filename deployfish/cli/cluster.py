from .adapters import ClickClusterAdapter

from .cli import cli

cluster_group = ClickClusterAdapter.add_command_group(cli, 'cluster')
cluster_list = ClickClusterAdapter.add_list_click_command(cluster_group)
cluster_info = ClickClusterAdapter.add_info_click_command(cluster_group)
cluster_exists = ClickClusterAdapter.add_exists_click_command(cluster_group)
cluster_ssh = ClickClusterAdapter.add_ssh_click_command(cluster_group)
cluster_tunnel = ClickClusterAdapter.add_tunnel_click_command(cluster_group)
cluster_scale = ClickClusterAdapter.add_scale_instances_click_command(cluster_group)
