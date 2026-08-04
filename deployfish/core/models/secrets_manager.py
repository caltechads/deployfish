import base64
from collections.abc import Sequence

from .abstract import Manager, Model
from .mixins import TagsManagerMixin, TagsMixin

# ----------------------------------------
# Managers
# ----------------------------------------


class SMSecretManager(TagsManagerMixin, Manager):
    """
    Manage our Secrets Manager secrets.   This differs from
    :py:class:`deployfish.core.models.secrets.SecretManager` in that that manager
    manages SSM Parameter Store secrets, not Secrets Manager secrets.
    """

    #: Service.
    service: str = "secretsmanager"

    def get(self, pk: str, **_) -> "SMSecret":
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
            response = self.client.describe_secret(SecretId=pk)
        except self.client.exceptions.ResourceNotFoundException:
            msg = f'No SMSecret with id "{pk}" exists in AWS'
            raise SMSecret.DoesNotExist(msg)
        return SMSecret(response)

    def get_value(self, pk: str) -> str:
        """
        Get value.

        Args:
            pk: pk.

        Returns:
            Operation result.
        """
        try:
            response = self.client.get_secret_value(SecretId=pk)
        except self.client.exceptions.ResourceNotFoundException:
            msg = f'No SMSecret with id "{pk}" exists in AWS'
            raise SMSecret.DoesNotExist(msg)
        except self.client.exceptions.ResourceNotFoundException as e:
            msg = f'Could not decrypt SMSecret("{pk}")'
            raise SMSecret.OperationFailed(msg) from e

        if "SecretBinary" in response:
            # SecretBinary is a base64 encoded bytes array.  We need to decode
            # it back to a utf-8 string.
            return base64.b64decode(response["SecretBinary"]).decode("utf-8")
        return response["SecretString"]

    def list(self) -> Sequence["SMSecret"]:
        """
        List.

        Returns:
            Operation result.
        """
        secrets: list[SMSecret] = []
        paginator = self.client.get_paginator("list_secrets")
        for page in paginator.paginate():
            secrets.extend([SMSecret(secret) for secret in page["SecretList"]])
        return secrets


# ----------------------------------------
# Models
# ----------------------------------------


class SMSecret(TagsMixin, Model):
    """
    Model smsecret behavior.
    """
    #: Objects.
    objects = SMSecretManager()

    @property
    def pk(self) -> str:
        """
        Pk.

        Returns:
            Operation result.
        """
        return self.data["ANR"]

    @property
    def name(self) -> str:
        """
        Name.

        Returns:
            Operation result.
        """
        return self.data["Name"]

    @property
    def arn(self) -> str:
        """
        Arn.

        Returns:
            Operation result.
        """
        return self.data["ARN"]

    @property
    def kms_key_id(self) -> str:
        """
        Kms key id.

        Returns:
            Operation result.
        """
        return self.data["KmsKeyId"]

    @property
    def description(self) -> str | None:
        """
        Description.

        Returns:
            Operation result.
        """
        return self.data.get("Description", None)

    @property
    def rotation_enabled(self) -> bool:
        """
        Rotation enabled.

        Returns:
            Operation result.
        """
        return self.data["RotationEnabled"]

    @property
    def last_rotated(self) -> bool:
        """
        Last rotated.

        Returns:
            Operation result.
        """
        return self.data["LastRotationDate"]

    @property
    def value(self) -> str:
        """
        Value.

        Returns:
            Operation result.
        """
        if "value" not in self.cache:
            self.cache["value"] = self.objects.get_value(self.arn)
        return self.cache["value"]
