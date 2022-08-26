from typing import Type, Dict

from cement import ex

from deployfish.core.models import (
    Model,
    ClassicLoadBalancer
)

from .crud import ReadOnlyCrudBase
from .utils import handle_model_exceptions


class EC2ClassicLoadBalancer(ReadOnlyCrudBase):

    class Meta:
        label = 'elbs'
        description = 'Work with Classic Load Balancer objects'
        help = 'Work with Classic Load Balancer objects'
        stacked_type = 'nested'

    model: Type[Model] = ClassicLoadBalancer

    help_overrides: Dict[str, str] = {
        'info': 'Show details about an ELB from AWS',
    }

    info_template: str = 'detail--classicloadbalancer.jinja2'

    list_ordering: str = 'Name'
    list_result_columns: Dict[str, str] = {
        'Name': 'LoadBalancerName',
        'Scheme': 'scheme',
        'VPC': 'VPCId',
        'Hostname': 'DNSName'
    }

    @ex(
        help="List Classic Load Balancers in AWS",
        arguments=[
            (
                ['--vpc-id'],
                {
                    'help': 'Filter by VPC ID',
                    'action': 'store',
                    'default': None,
                    'dest': 'vpc_id'
                }
            ),
            (
                ['--name'],
                {
                    'help': 'Filter by load balancer name, with globs. Ex: "foo*", "*foo"',
                    'action': 'store',
                    'default': None,
                    'dest': 'name'
                }
            ),
            (
                ['--scheme'],
                {
                    'help': 'Filter by load balancer scheme.',
                    'action': 'store',
                    'default': 'any',
                    'choices': ['any', 'internet-facing', 'internal'],
                    'dest': 'scheme'
                }
            ),
        ]
    )
    @handle_model_exceptions
    def list(self):
        results = self.model.objects.list(
            vpc_id=self.app.pargs.vpc_id,
            scheme=self.app.pargs.scheme,
            name=self.app.pargs.name
        )
        self.render_list(results)
