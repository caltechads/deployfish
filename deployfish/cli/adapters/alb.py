from deployfish.core.models import ApplicationLoadBalancer, LoadBalancerListener, TargetGroup

from ..renderers import TargetGroupTableRenderer

from .abstract import ClickModelAdapter


class ClickApplicationLoadBalancerAdapter(ClickModelAdapter):

    model = ApplicationLoadBalancer

    list_ordering = 'Name'
    list_result_columns = {
        'Name': 'name',
        'Scheme': 'scheme',
        'VPC': 'VpcId',
        'Hostname': 'DNSName'
    }


class ClickLoadBalancerListenerAdapter(ClickModelAdapter):

    model = LoadBalancerListener

    list_ordering = 'Load Balancer'
    list_result_columns = {
        'Load Balancer': 'load_balancer__name',
        'Port': 'Port',
        'Protocol': 'Protocol',
        'Rules': {'key': 'rules', 'length': True},
        'ARN': 'arn'
    }


class ClickTargetGroupAdapter(ClickModelAdapter):

    model = TargetGroup

    list_ordering = 'Load Balancers'
    list_result_columns = {
        'Load Balancers': 'load_balancers',
        'Rules': 'rules',
        'Name': 'name',
        'Protocol': 'Protocol',
        'Target Port': 'Port',
        'Targets': 'targets'
    }
    list_renderer_classes = ClickModelAdapter.list_renderer_classes
    list_renderer_classes['table'] = TargetGroupTableRenderer
