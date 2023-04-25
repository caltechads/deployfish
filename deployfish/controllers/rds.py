import argparse
from typing import Type, Dict, cast

from cement import ex
import click
from deployfish.core.models import (
    Model,
    RDSInstance
)

from .crud import ReadOnlyCrudBase
from .utils import handle_model_exceptions


class RDSRDSInstance(ReadOnlyCrudBase):

    class Meta:
        label = 'rds'
        description = 'Work with RDS Instances'
        help = 'Work with RDS Instances'
        stacked_type = 'nested'

    model: Type[Model] = RDSInstance

    help_overrides: Dict[str, str] = {
        'info': 'Show details about an RDS Instance from AWS',
        'list': 'List RDS Instances in AWS',
    }

    info_template: str = 'detail--rdsinstance.jinja2'

    list_ordering: str = 'Name'
    list_result_columns: Dict[str, str] = {
        'Name': 'DBInstanceIdentifier',
        'VPC': 'vpc__name',
        'Engine': 'Engine',
        'Version': 'EngineVersion',
        'Mult AZ': 'multi_az',
        'Hostname': 'hostname',
        'Root User': 'root_user'
    }

    @ex(
        help='Get the root credentials for an RDS Instance.',
        arguments=[(['pk'], {'help': 'The name of the RDS Instance in AWS'})],
        description="""
Print the username and password for the root user if the RDS instance
identified by {pk} is Secrets Manager enabled.  If the instance is
not Secrets Manager enabled, just print the username of the root user.

The {pk} is the name of the RDS instance.
""",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    @handle_model_exceptions
    def credentials(self) -> None:
        loader = self.loader(self)
        obj = loader.get_object_from_aws(self.app.pargs.pk)
        obj = cast(RDSInstance, obj)
        if obj.secret_enabled:
            self.app.print(f'Username: {obj.root_user}')
            self.app.print(f'Password: {obj.root_password}')
        else:
            self.app.print(f'Username: {obj.root_user}')
            self.app.print(click.style('Password is not in AWS Secrets Manager', fg='red'))
