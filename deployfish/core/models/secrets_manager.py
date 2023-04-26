# -*- coding: utf-8 -*-
import base64
from typing import List, Sequence, Optional

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

    service: str = 'secretsmanager'

    def get(self, pk: str, **_) -> "SMSecret":
        try:
            response = self.client.describe_secret(SecretId=pk)
        except self.client.exceptions.ResourceNotFoundException:
            raise SMSecret.DoesNotExist(
                f'No SMSecret with id "{pk}" exists in AWS'
            )
        return SMSecret(response)

    def get_value(self, pk: str) -> str:
        try:
            response = self.client.get_secret_value(SecretId=pk)
        except self.client.exceptions.ResourceNotFoundException:
            raise SMSecret.DoesNotExist(
                f'No SMSecret with id "{pk}" exists in AWS'
            )
        except self.client.exceptions.ResourceNotFoundException as e:
            raise SMSecret.OperationFailed(
                f'Could not decrypt SMSecret("{pk}")'
            ) from e

        if 'SecretBinary' in response:
            # SecretBinary is a base64 encoded bytes array.  We need to decode
            # it back to a utf-8 string.
            return base64.b64decode(response['SecretBinary']).decode('utf-8')
        return response['SecretString']

    def list(self) -> Sequence["SMSecret"]:
        secrets: List["SMSecret"] = []
        paginator = self.client.get_paginator('list_secrets')
        for page in paginator.paginate():
            secrets.extend([SMSecret(secret) for secret in page['SecretList']])
        return secrets


# ----------------------------------------
# Models
# ----------------------------------------

class SMSecret(TagsMixin, Model):

    objects = SMSecretManager()

    @property
    def pk(self) -> str:
        return self.data['ANR']

    @property
    def name(self) -> str:
        return self.data['Name']

    @property
    def arn(self) -> str:
        return self.data['ARN']

    @property
    def kms_key_id(self) -> str:
        return self.data['KmsKeyId']

    @property
    def description(self) -> Optional[str]:
        return self.data.get('Description', None)

    @property
    def rotation_enabled(self) -> bool:
        return self.data['RotationEnabled']

    @property
    def last_rotated(self) -> bool:
        return self.data['LastRotationDate']

    @property
    def value(self) -> str:
        if 'value' not in self.cache:
            self.cache['value'] = self.objects.get_value(self.arn)
        return self.cache['value']
