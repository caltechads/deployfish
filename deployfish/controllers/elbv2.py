from typing import Type, Dict, Any

from cement import ex

from deployfish.core.models import (
    Model,
    LoadBalancer
)
from deployfish.core.models.elbv2 import LoadBalancerListener, TargetGroup

from .crud import ReadOnlyCrudBase
from .utils import handle_model_exceptions


class EC2LoadBalancer(ReadOnlyCrudBase):

    class Meta:
        label = 'lbs'
        description = 'Work with Load Balancer objects'
        help = 'Work with Load Balancer objects'
        stacked_type = 'nested'

    model: Type[Model] = LoadBalancer

    help_overrides: Dict[str, str] = {
        'info': 'Show details about an ALB or NLB from AWS',
    }

    info_template: str = 'detail--loadbalancer.jinja2'

    list_ordering: str = 'Name'
    list_result_columns: Dict[str, Any] = {
        'Name': 'name',
        'Type': 'lb_type',
        'Scheme': 'scheme',
        'VPC': 'VpcId',
        'Hostname': 'DNSName'
    }


    @ex(
        help="List Load Balancers in AWS",
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
                ['--type'],
                {
                    'help': 'Filter by load balancer type.',
                    'action': 'store',
                    'default': 'any',
                    'choices': ['any', 'application', 'network'],
                    'dest': 'lb_type'
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
            lb_type=self.app.pargs.lb_type,
            scheme=self.app.pargs.scheme,
            name=self.app.pargs.name
        )
        self.render_list(results)


class EC2LoadBalancerListener(ReadOnlyCrudBase):

    class Meta:
        label = 'listeners'
        description = 'Work with Load Balancer Listener objects'
        help = 'Work with Load Balancer Listener objects'
        stacked_on = 'lbs'
        stacked_type = 'nested'

    model: Type[Model] = LoadBalancerListener

    help_overrides: Dict[str, str] = {
        'info': 'Show details about an Load Balancer Listener in AWS',
    }

    info_template: str = 'detail--loadbalancerlistener.jinja2'

    list_ordering: str = 'Load Balancer'
    list_result_columns: Dict[str, Any] = {
        'Load Balancer': 'load_balancer__name',
        'Port': 'Port',
        'Protocol': 'Protocol',
        'Rules': {'key': 'rules', 'length': True},
        'ARN': 'arn'
    }


    @ex(
        help="List Load Balancer Listeners in AWS",
        arguments=[
            (['load_balancer'], {'help': 'Load balancer name or ARN'})
        ]
    )
    @handle_model_exceptions
    def list(self):
        results = self.model.objects.list(self.app.pargs.load_balancer)
        self.render_list(results)


class EC2LoadBalancerTargetGroup(ReadOnlyCrudBase):

    class Meta:
        label = 'target-groups'
        description = 'Work with Load Balancer Target Group objects'
        help = 'Work with Load Balancer Target Group objects'
        stacked_on = 'lbs'
        stacked_type = 'nested'

    model: Type[Model] = TargetGroup

    help_overrides: Dict[str, str] = {
        'info': 'Show details about an Load Balancer Target Group in AWS',
    }

    info_template: str = 'detail--targetgroup.jinja2'

    list_ordering: str = 'Name'
    list_result_columns: Dict[str, Any] = {
        'Name': 'name',
        'Load Balancers': 'load_balancers',
        'Rules': 'rules',
        'Protocol': 'Protocol',
        'Target Port': 'Port',
        'Targets': 'targets'
    }


    @ex(
        help="List Load Balancer Target Groups in AWS",
        arguments=[
            (
                ['--load-balancer'],
                {
                    'help': 'Filter by load balancer name or ARN"',
                    'action': 'store',
                    'default': None,
                    'dest': 'load_balancer'
                }
            ),
        ]
    )
    @handle_model_exceptions
    def list(self):
        results = self.model.objects.list(
            load_balancer=self.app.pargs.load_balancer
        )
        self.render_list(results)
