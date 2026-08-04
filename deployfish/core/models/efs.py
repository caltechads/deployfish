from collections.abc import Sequence

import botocore

from .abstract import Manager, Model
from .mixins import TagsManagerMixin, TagsMixin

# ----------------------------------------
# Managers
# ----------------------------------------


class EFSFileSystemManager(TagsManagerMixin, Manager):
    """
    Model efsfile system manager behavior.
    """
    #: Service.
    service: str = "efs"

    def get(self, pk: str, **_) -> "EFSFileSystem":
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
            response = self.client.describe_file_systems(FileSystemId=pk)
        except botocore.exceptions.ClientError:
            # FIXME: can we get ClientError for reasons other than the filesystem does
            # not exist?
            msg = f'No EFS file system with id "{pk}" exists in AWS'
            raise EFSFileSystem.DoesNotExist(msg)
        return EFSFileSystem(response["FileSystems"][0])

    def list(self) -> Sequence["EFSFileSystem"]:
        """
        List.

        Returns:
            Operation result.
        """
        response = self.client.describe_file_systems()
        return [EFSFileSystem(group) for group in response["FileSystems"]]


# ----------------------------------------
# Models
# ----------------------------------------


class EFSFileSystem(TagsMixin, Model):
    """
    Model efsfile system behavior.
    """
    #: Objects.
    objects = EFSFileSystemManager()

    @property
    def pk(self) -> str:
        """
        Pk.

        Returns:
            Operation result.
        """
        return self.data["FileSystemId"]

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
        return self.data["FileSystemArn"]

    @property
    def size(self) -> int:
        """
        Size.

        Returns:
            Operation result.
        """
        return self.data["SizeInBytes"]["Value"]

    @property
    def state(self) -> str:
        """
        State.

        Returns:
            Operation result.
        """
        return self.data["LifeCycleState"]
