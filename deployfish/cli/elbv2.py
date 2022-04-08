from .adapters import (
    ClickLoadBalancerAdapter,
    ClickLoadBalancerListenerAdapter,
    ClickTargetGroupAdapter
)
from .cli import cli


lb_group = ClickLoadBalancerAdapter.add_command_group(cli, 'lbs')
lb_list = ClickLoadBalancerAdapter.add_list_click_command(lb_group)
lb_info = ClickLoadBalancerAdapter.add_info_click_command(lb_group)
lb_exists = ClickLoadBalancerAdapter.add_exists_click_command(lb_group)

listener_group = ClickLoadBalancerListenerAdapter.add_command_group(lb_group, 'listeners')
listener_list = ClickLoadBalancerListenerAdapter.add_list_click_command(listener_group)
listener_info = ClickLoadBalancerListenerAdapter.add_info_click_command(listener_group)
listener_exists = ClickLoadBalancerListenerAdapter.add_exists_click_command(listener_group)

target_group_group = ClickTargetGroupAdapter.add_command_group(lb_group, 'target-groups')
target_group_list = ClickTargetGroupAdapter.add_list_click_command(target_group_group)
target_group_info = ClickTargetGroupAdapter.add_info_click_command(target_group_group)
target_group_exists = ClickTargetGroupAdapter.add_exists_click_command(target_group_group)
