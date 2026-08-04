import json
from collections.abc import Sequence
from typing import cast

from .abstract import Manager, Model
from .ec2 import VPC, SecurityGroup, Subnet
from .mixins import TagsManagerMixin, TagsMixin
from .secrets_manager import SMSecret

# ----------------------------------------
# Managers
# ----------------------------------------


class RDSManager(TagsManagerMixin, Manager):
    """
    Model rdsmanager behavior.
    """

    #: Service.
    service: str = "rds"

    def get(self, pk: str, **_) -> "RDSInstance":
        """
        Get.

        Args:
            pk: pk.

        Keyword Args:
            _: .

        Returns:
            Operation result.

        """
        try:
            response = self.client.describe_db_instances(DBInstanceIdentifier=pk)
        except self.client.exceptions.DBInstanceNotFoundFault:
            msg = f'No RDSInstance with id "{pk}" exists in AWS'
            raise RDSInstance.DoesNotExist(msg) from None
        return RDSInstance(response["DBInstances"][0])

    def list(self) -> Sequence["RDSInstance"]:
        """
        List.

        Returns:
            Operation result.

        """
        response = self.client.describe_db_instances()
        return [RDSInstance(group) for group in response["DBInstances"]]


# ----------------------------------------
# Models
# ----------------------------------------


class RDSInstance(TagsMixin, Model):
    """
    Model rdsinstance behavior.
    """

    #: Objects.
    objects = RDSManager()

    @property
    def pk(self) -> str:
        """
        Pk.

        Returns:
            Operation result.

        """
        return self.data["DBInstanceIdentifier"]

    @property
    def name(self) -> str:
        """
        Name.

        Returns:
            Operation result.

        """
        return self.data["DBInstanceIdentifier"]

    @property
    def arn(self) -> str:
        """
        Arn.

        Returns:
            Operation result.

        """
        return self.data["DBInstanceArn"]

    @property
    def status(self) -> str:
        """
        Status.

        Returns:
            Operation result.

        """
        return self.data["DBInstanceStatus"]

    @property
    def engine(self) -> str:
        """
        Returns:
            The engine for this RDS instance (e.g. "mysql")

        """
        return self.data["Engine"]

    @property
    def version(self) -> str:
        """
        Returns:
            The version of the engine for this RDS instance.

        """
        return self.data["EngineVersion"]

    @property
    def hostname(self) -> str:
        """
        Returns:
            The hostname of the db endpoint

        """
        return self.data["Endpoint"]["Address"]

    @property
    def port(self) -> int:
        """
        Returns:
            The port for this RDS instance (e.g. "mysql")

        """
        return self.data["Endpoint"]["Port"]

    @property
    def root_user(self) -> str:
        """
        Returns:
            The username of the root user for this instance.

        """
        return self.data["MasterUsername"]

    @property
    def secret_enabled(self) -> bool:
        """
        Secret enabled.

        Returns:
            Operation result.

        """
        return self.secret_arn is not None

    @property
    def secret_arn(self) -> str | None:
        """
        Returns:
            The ARN of the Secrets Manager Secret used to store the password
            for our root user.  If the RDS does not use Secrets Manager for this,
            return ``None``.

        """
        try:
            return self.data["MasterUserSecret"]["SecretArn"]
        except KeyError:
            return None

    @property
    def root_password(self) -> str:
        """
        Root password.

        Returns:
            Operation result.

        """
        if self.secret_enabled:
            if "root_password" not in self.cache:
                secret = SMSecret.objects.get(cast("str", self.secret_arn))
                self.cache["root_password"] = secret.value
            return json.loads(self.cache["root_password"])["password"]
        msg = f"RDSInstance({self.pk}) does not have a secrets manager backed password"
        raise self.OperationFailed(msg)

    @property
    def secret_status(self) -> str | None:
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
            return self.data["MasterUserSecret"]["SecretArn"]
        except KeyError:
            return None

    @property
    def multi_az(self) -> bool:
        """
        Returns:
            ``True`` if this is a Multi-AZ RDS, ``False`` if not.

        """
        return self.data["MultiAZ"]

    @property
    def subnets(self) -> list[Subnet]:
        """
        Subnets.

        Returns:
            Operation result.

        """
        if "subnets" not in self.cache:
            self.cache["subnets"] = []
            for subnet in self.data["DBSubnetGroup"]["Subnets"]:
                self.cache["subnets"].append(
                    Subnet.objects.get(pk=subnet["SubnetIdentifier"])
                )
        return self.cache["subnets"]

    @property
    def security_groups(self) -> list[SecurityGroup]:
        """
        Security groups.

        Returns:
            Operation result.

        """
        if "security_groups" not in self.cache:
            self.cache["security_groups"] = []
            for group in self.data["VpcSecurityGroups"]:
                self.cache["security_groups"].append(
                    SecurityGroup.objects.get(pk=group["VpcSecurityGroupId"])
                )

        return self.cache["security_groups"]

    # ------------------------------
    # Related objects
    # ------------------------------

    @property
    def vpc(self) -> VPC:
        """
        Vpc.

        Returns:
            Operation result.

        """
        if "vpc" not in self.cache:
            self.cache["vpc"] = VPC.objects.get(self.data["DBSubnetGroup"]["VpcId"])
        return self.cache["vpc"]
