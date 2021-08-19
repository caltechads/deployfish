# -*- coding: utf-8 -*-

import botocore

from .abstract import Manager, Model
from .mixins import TagsManagerMixin, TagsMixin

# ----------------------------------------
# Managers
# ----------------------------------------


class EFSFileSystemManager(TagsManagerMixin, Manager):

    service = 'efs'

    def get(self, pk, **kwargs):
        try:
            response = self.client.describe_file_systems(FileSystemId=pk)
        except botocore.exceptions.ClientError:
            raise EFSFileSystem.DoesNotExist(
                'No EFS file system with id "{}" exists in AWS'.format(pk)
            )
        return EFSFileSystem(response['FileSystems'][0])

    def list(self):
        response = self.client.describe_file_systems()
        return [EFSFileSystem(group) for group in response['FileSystems']]

    def save(self, obj):
        raise EFSFileSystem.ReadOnly('Cannot create or update EFS file systems with deployfish')

    def delete(self, pk):
        raise EFSFileSystem.ReadOnly('Cannot delete EFS file systems with deployfish')


# ----------------------------------------
# Models
# ----------------------------------------

class EFSFileSystem(TagsMixin, Model):

    objects = EFSFileSystemManager()

    @property
    def pk(self):
        return self.data['FileSystemId']

    @property
    def name(self):
        return self.data['Name']

    @property
    def arn(self):
        return self.data['FileSystemArn']

    @property
    def size(self):
        return self.data['SizeInBytes']['Value']

    @property
    def state(self):
        return self.data['LifeCycleState']
