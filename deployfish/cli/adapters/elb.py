from deployfish.core.models import ClassicLoadBalancer

from .abstract import ClickModelAdapter


class ClickClassicLoadBalancerAdapter(ClickModelAdapter):

    model = ClassicLoadBalancer

    list_ordering = 'Name'
    list_result_columns = {
        'Name': 'LoadBalancerName',
        'Scheme': 'scheme',
        'VPC': 'VPCId',
        'Hostname': 'DNSName'
    }
