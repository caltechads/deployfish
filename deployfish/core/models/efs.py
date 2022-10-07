# -*- coding: utf-8 -*-
from typing import Sequence

import botocore

from .abstract import Manager, Model
from .mixins import TagsManagerMixin, TagsMixin


# ----------------------------------------
# Managers
# ----------------------------------------


class EFSFileSystemManager(TagsManagerMixin, Manager):

    service: str = 'efs'

    def get(self, pk: str, **_) -> "EFSFileSystem":
        try:
            response = self.client.describe_file_systems(FileSystemId=pk)
        except botocore.exceptions.ClientError:
            # FIXME: can we get ClientError for reasons other than the filesystem does
            # not exist?
            raise EFSFileSystem.DoesNotExist(
                f'No EFS file system with id "{pk}" exists in AWS'
            )
        return EFSFileSystem(response['FileSystems'][0])

    def list(self) -> Sequence["EFSFileSystem"]:
        response = self.client.describe_file_systems()
        return [EFSFileSystem(group) for group in response['FileSystems']]


# ----------------------------------------
# Models
# ----------------------------------------

class EFSFileSystem(TagsMixin, Model):

    objects = EFSFileSystemManager()

    @property
    def pk(self) -> str:
        return self.data['FileSystemId']

    @property
    def name(self) -> str:
        return self.data['Name']

    @property
    def arn(self) -> str:
        return self.data['FileSystemArn']

    @property
    def size(self) -> int:
        return self.data['SizeInBytes']['Value']

    @property
    def state(self) -> str:
        return self.data['LifeCycleState']
