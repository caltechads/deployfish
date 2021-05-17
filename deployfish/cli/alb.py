from .adapters import (
    ClickApplicationLoadBalancerAdapter,
    ClickLoadBalancerListenerAdapter,
    ClickTargetGroupAdapter
)
from .cli import cli


alb_group = ClickApplicationLoadBalancerAdapter.add_command_group(cli, 'albs')
alb_list = ClickApplicationLoadBalancerAdapter.add_list_click_command(alb_group)
alb_info = ClickApplicationLoadBalancerAdapter.add_info_click_command(alb_group)
alb_exists = ClickApplicationLoadBalancerAdapter.add_exists_click_command(alb_group)

listener_group = ClickLoadBalancerListenerAdapter.add_command_group(alb_group, 'listeners')
listener_list = ClickLoadBalancerListenerAdapter.add_list_click_command(listener_group)
listener_info = ClickLoadBalancerListenerAdapter.add_info_click_command(listener_group)
listener_exists = ClickLoadBalancerListenerAdapter.add_exists_click_command(listener_group)

target_group_group = ClickTargetGroupAdapter.add_command_group(alb_group, 'target-groups')
target_group_list = ClickTargetGroupAdapter.add_list_click_command(target_group_group)
target_group_info = ClickTargetGroupAdapter.add_info_click_command(target_group_group)
target_group_exists = ClickTargetGroupAdapter.add_exists_click_command(target_group_group)
