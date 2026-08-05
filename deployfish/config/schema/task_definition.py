"""
Pydantic models describing the shape of a ``deployfish.yml`` task-definition
stanza. These validate and reshape input only -- the boto3-shaped output dict
is still assembled by hand in
:py:class:`deployfish.core.adapters.deployfish.ecs.task_definition.TaskDefinitionAdapter`.
"""

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DockerVolumeConfig(BaseModel):
    """
    A Docker-managed volume's configuration.

    Args:
        scope: ``"task"`` or ``"shared"``.
        autoprovision: whether to automatically provision the volume.
        driver: the volume driver name.
        driver_opts: volume driver options.
        labels: labels to apply to the volume.

    """

    #: Pydantic model configuration.
    model_config = ConfigDict(extra="forbid")

    #: ``"task"`` or ``"shared"``.
    scope: str | None = None
    #: Whether to automatically provision the volume.
    autoprovision: bool | None = None
    #: The volume driver name.
    driver: str | None = None
    #: Volume driver options.
    driver_opts: dict[str, str] = Field(default_factory=dict, alias="driverOpts")
    #: Labels to apply to the volume.
    labels: dict[str, str] = Field(default_factory=dict)


class EFSConfig(BaseModel):
    """
    An EFS-backed volume's configuration.

    Args:
        file_system_id: the EFS file system ID.
        root_directory: the root directory within the file system to mount.

    """

    #: Pydantic model configuration.
    model_config = ConfigDict(extra="forbid")

    #: The EFS file system ID.
    file_system_id: str
    #: The root directory within the file system to mount, if not the root.
    root_directory: str | None = None


class Volume(BaseModel):
    """
    A single task-definition-level volume declaration. ``path``, ``config``,
    and ``efs_config`` are mutually exclusive.

    Args:
        name: the volume name, referenced by container mount points.
        path: a host bind-mount path.
        config: a Docker-managed volume configuration.
        efs_config: an EFS-backed volume configuration.

    """

    #: Pydantic model configuration.
    model_config = ConfigDict(extra="forbid")

    #: The volume name, referenced by container mount points.
    name: str
    #: A host bind-mount path.
    path: str | None = None
    #: A Docker-managed volume configuration.
    config: DockerVolumeConfig | None = None
    #: An EFS-backed volume configuration.
    efs_config: EFSConfig | None = None

    @model_validator(mode="after")
    def _mutually_exclusive(self) -> "Volume":
        """
        Enforce that ``path``, ``config``, and ``efs_config`` are mutually
        exclusive.

        Raises:
            ValueError: if more than one of ``path``, ``config``, or
                ``efs_config`` is set.

        Returns:
            ``self``, unchanged.

        """
        specified = sum(
            x is not None for x in (self.path, self.config, self.efs_config)
        )
        if specified > 1:
            msg = (
                'When defining volumes, specify only one of "path", "config" '
                'or "efs_config"'
            )
            raise ValueError(msg)
        return self
