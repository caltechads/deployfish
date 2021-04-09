from .adapters import ClickSSHTunnelAdapter

from .cli import cli

tunnel_group = ClickSSHTunnelAdapter.add_command_group(cli, 'tunnel')
tunnel_list = ClickSSHTunnelAdapter.add_list_click_command(tunnel_group)
tunnel_info = ClickSSHTunnelAdapter.add_info_click_command(tunnel_group)
tunnel_tunnel = ClickSSHTunnelAdapter.add_tunnel_click_command(tunnel_group)
