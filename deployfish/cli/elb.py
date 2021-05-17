from .adapters import ClickClassicLoadBalancerAdapter
from .cli import cli


elb_group = ClickClassicLoadBalancerAdapter.add_command_group(cli, 'elbs')
elb_list = ClickClassicLoadBalancerAdapter.add_list_click_command(elb_group)
elb_info = ClickClassicLoadBalancerAdapter.add_info_click_command(elb_group)
elb_exists = ClickClassicLoadBalancerAdapter.add_exists_click_command(elb_group)
