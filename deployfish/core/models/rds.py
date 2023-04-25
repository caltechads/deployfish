# -*- coding: utf-8 -*-
import json
from typing import List, Sequence, Optional, cast

from .abstract import Manager, Model
from .ec2 import VPC, Subnet, SecurityGroup
from .secrets_manager import SMSecret
from .mixins import TagsManagerMixin, TagsMixin


# ----------------------------------------
# Managers
# ----------------------------------------


class RDSManager(TagsManagerMixin, Manager):

    service: str = 'rds'

    def get(self, pk: str, **_) -> "RDSInstance":
        try:
            response = self.client.describe_db_instances(DBInstanceIdentifier=pk)
        except self.client.exceptions.DBInstanceNotFoundFault:
            raise RDSInstance.DoesNotExist(
                f'No RDSInstance with id "{pk}" exists in AWS'
            )
        return RDSInstance(response['DBInstances'][0])

    def list(self) -> Sequence["RDSInstance"]:
        response = self.client.describe_db_instances()
        return [RDSInstance(group) for group in response['DBInstances']]


# ----------------------------------------
# Models
# ----------------------------------------

class RDSInstance(TagsMixin, Model):

    objects = RDSManager()

    @property
    def pk(self) -> str:
        return self.data['DBInstanceIdentifier']

    @property
    def name(self) -> str:
        return self.data['DBInstanceIdentifier']

    @property
    def arn(self) -> str:
        return self.data['DBInstanceArn']

    @property
    def status(self) -> str:
        return self.data['DBInstanceStatus']

    @property
    def engine(self) -> str:
        """
        Returns:
            The engine for this RDS instance (e.g. "mysql")
        """
        return self.data['Engine']

    @property
    def version(self) -> str:
        """
        Returns:
            The version of the engine for this RDS instance.
        """
        return self.data['EngineVersion']

    @property
    def hostname(self) -> str:
        """
        Returns:
            The hostname of the db endpoint
        """
        return self.data['Endpoint']['Address']

    @property
    def port(self) -> int:
        """
        Returns:
            The port for this RDS instance (e.g. "mysql")
        """
        return self.data['Endpoint']['Port']

    @property
    def root_user(self) -> str:
        """
        Returns:
            The username of the root user for this instance.
        """
        return self.data['MasterUsername']

    @property
    def secret_enabled(self) -> bool:
        return self.secret_arn is not None

    @property
    def secret_arn(self) -> Optional[str]:
        """
        Returns:
            The ARN of the Secrets Manager Secret used to store the password
            for our root user.  If the RDS does not use Secrets Manager for this,
            return ``None``.
        """
        try:
            return self.data['MasterUserSecret']['SecretArn']
        except KeyError:
            return None

    @property
    def root_password(self) -> str:
        if self.secret_enabled:
            if 'root_password' not in self.cache:
                secret = SMSecret.objects.get(cast(str, self.secret_arn))
                self.cache['root_password'] = secret.value
            return json.loads(self.cache['root_password'])['password']
        raise self.OperationFailed(
            f'RDSInstance({self.pk}) does not have a secrets manager backed password'
        )

    @property
    def secret_status(self) -> Optional[str]:
        """
        Return one of these strings, or ``None``:

        * ``creating`` - The secret is being created.
        * ``active`` - The secret is available for normal use and rotation.
        * ``rotating`` - The secret is being rotated.
        * ``impaired`` - The secret can be used to access database credentials, but it
            can't be rotated.

        Returns:
            The status of the Secrets Manager Secret used to store the password
            for our root user.  If the RDS does not use Secrets Manager for this,
            return ``None``.
        """
        try:
            return self.data['MasterUserSecret']['SecretArn']
        except KeyError:
            return None

    @property
    def multi_az(self) -> bool:
        """
        Returns:
            ``True`` if this is a Multi-AZ RDS, ``False`` if not.
        """
        return self.data['MultiAZ']

    @property
    def subnets(self) -> List[Subnet]:
        if 'subnets' not in self.cache:
            self.cache['subnets'] = []
            for subnet in self.data['DBSubnetGroup']['Subnets']:
                self.cache['subnets'].append(Subnet.objects.get(pk=subnet['SubnetIdentifier']))
        return self.cache['subnets']

    @property
    def security_groups(self) -> List[SecurityGroup]:
        if 'security_groups' not in self.cache:
            self.cache['security_groups'] = []
            for group in self.data['VpcSecurityGroups']:
                self.cache['security_groups'].append(
                    SecurityGroup.objects.get(pk=group['VpcSecurityGroupId'])
                )

        return self.cache['security_groups']

    # ------------------------------
    # Related objects
    # ------------------------------

    @property
    def vpc(self) -> VPC:
        if 'vpc' not in self.cache:
            self.cache['vpc'] = VPC.objects.get(self.data['DBSubnetGroup']['VpcId'])
        return self.cache['vpc']
