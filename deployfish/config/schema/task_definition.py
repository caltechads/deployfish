"""
Pydantic models describing the shape of a ``deployfish.yml`` task-definition
stanza. These validate and reshape input only -- the boto3-shaped output dict
is still assembled by hand in
:py:class:`deployfish.core.adapters.deployfish.ecs.task_definition.TaskDefinitionAdapter`.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from deployfish.config.schema._partial import partial_model
from deployfish.config.schema.container import (
    ContainerDefinitionInput,
    ContainerDefinitionOverlayInput,
)


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
        Enforce that exactly one of ``path``, ``config``, and ``efs_config``
        is set.

        Raises:
            ValueError: if zero or more than one of ``path``, ``config``, or
                ``efs_config`` is set.

        Returns:
            ``self``, unchanged.

        """
        specified = sum(
            x is not None for x in (self.path, self.config, self.efs_config)
        )
        if specified != 1:
            msg = (
                'When defining volumes, specify exactly one of "path", '
                '"config" or "efs_config"'
            )
            raise ValueError(msg)
        return self


class RuntimePlatform(BaseModel):
    """
    A task definition's CPU/OS platform requirements.

    Args:
        cpu_architecture: the CPU architecture, e.g. ``"X86_64"``.
        operating_system_family: the OS family, e.g. ``"LINUX"``.

    """

    #: Pydantic model configuration.
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    #: The CPU architecture.
    cpu_architecture: str = Field(default="X86_64", alias="cpuArchitecture")
    #: The OS family.
    operating_system_family: str = Field(
        default="LINUX", alias="operatingSystemFamily"
    )


class TaskDefinitionInput(BaseModel):
    """
    Validates and reshapes a ``deployfish.yml`` task-definition stanza,
    including its nested containers. Does not produce the boto3-shaped
    output dict -- see
    :py:class:`deployfish.core.adapters.deployfish.ecs.task_definition.TaskDefinitionAdapter`
    for that.

    Args:
        family: the task definition family name.

    """

    #: Pydantic model configuration.
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    #: The task definition family name.
    family: str
    #: The Docker network mode.
    network_mode: str = "bridge"
    #: The ECS launch type -- ``"EC2"`` or ``"FARGATE"``.
    launch_type: str = "EC2"
    #: CPU/OS platform requirements, if specified.
    runtime_platform: RuntimePlatform | None = None
    #: Placement constraints, passed through unchanged. Note: the
    #: documented/actual yaml key for this is the literal camelCase
    #: ``placementConstraints``, not a snake_case key -- this matches
    #: today's adapter behavior exactly, an existing inconsistency versus
    #: this model's other fields, not something this refactor corrects.
    placement_constraints: list[dict[str, Any]] = Field(
        default_factory=list, alias="placementConstraints"
    )
    #: Whether containers should get a read-only root filesystem by default.
    readonly_root_filesystem: bool | None = None
    #: The IAM role ARN tasks run as.
    task_role_arn: str | None = None
    #: The IAM role ARN ECS uses to pull images / write logs. Required when
    #: ``launch_type`` is ``"FARGATE"``.
    execution_role: str | None = None
    #: Task-definition-level volumes.
    volumes: list[Volume] = Field(default_factory=list)
    #: This task definition's containers.
    containers: list[ContainerDefinitionInput] = Field(default_factory=list)
    #: Task-level CPU units, if specified.
    cpu: int | None = None
    #: Task-level memory (MiB), if specified.
    memory: int | None = None

    @model_validator(mode="before")
    @classmethod
    def _require_containers(cls, data: Any) -> Any:
        """
        Raise a clear, specific error when ``containers`` is missing, instead
        of Pydantic's generic "field required" message. Matches
        ``TaskDefinitionAdapter``'s current message text exactly. Only
        enforced on the strict model -- inherited ``mode="before"``
        validators run for subclasses too, so this must explicitly check
        ``cls`` to avoid also enforcing on ``TaskDefinitionOverlayInput``
        (partial/overlay data), matching today's
        ``if self.partial: containers = self.data.get("containers", [])``
        guard.

        Args:
            data: the raw task-definition stanza.

        Raises:
            ValueError: if ``containers`` is missing on the strict model.

        Returns:
            ``data`` unchanged.

        """
        # Deliberately ``cls is TaskDefinitionInput``, not ``issubclass``/
        # ``isinstance``: this must NOT fire for ``TaskDefinitionOverlayInput``,
        # a real subclass used for partial/overlay data, where ``containers``
        # is legitimately optional.
        if (
            cls is TaskDefinitionInput
            and isinstance(data, dict)
            and "containers" not in data
        ):
            msg = "You must define at least one container in your task definition"
            raise ValueError(msg)
        return data

    @model_validator(mode="after")
    def _validate_volume_names_unique(self) -> "TaskDefinitionInput":
        """
        Reject duplicate volume names.

        Raises:
            ValueError: if two volumes share a name.

        Returns:
            ``self``, unchanged.

        """
        if self.volumes is None:
            return self
        seen: set[str] = set()
        for v in self.volumes:
            if v.name in seen:
                msg = f'duplicate volume name "{v.name}"'
                raise ValueError(msg)
            seen.add(v.name)
        return self

    @model_validator(mode="after")
    def _validate_container_resource_limits(self) -> "TaskDefinitionInput":
        """
        Reject any container whose ``cpu``/``memory`` exceeds this task
        definition's own ``cpu``/``memory``, when both are specified.

        Raises:
            ValueError: if a container's ``cpu`` or ``memory`` exceeds the
                task-level value.

        Returns:
            ``self``, unchanged.

        """
        if self.containers is None:
            return self
        for container in self.containers:
            if (
                self.cpu is not None
                and container.cpu is not None
                and container.cpu > self.cpu
            ):
                msg = (
                    f'container "{container.name}": cpu is greater than the '
                    "task cpu value"
                )
                raise ValueError(msg)
            if (
                self.memory is not None
                and container.memory is not None
                and container.memory > self.memory
            ):
                msg = (
                    f'container "{container.name}": memory is greater than '
                    "task memory"
                )
                raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _validate_fargate_requires_execution_role(self) -> "TaskDefinitionInput":
        """
        Require ``execution_role`` when ``launch_type`` is ``"FARGATE"``.
        Only enforced on the strict model -- ``TaskDefinitionOverlayInput``
        (partial/overlay data) skips this, matching today's
        ``if not self.partial`` guard.

        Raises:
            ValueError: if ``launch_type`` is ``"FARGATE"`` and
                ``execution_role`` is not set.

        Returns:
            ``self``, unchanged.

        """
        # Deliberately ``type(self) is TaskDefinitionInput``, not
        # ``isinstance``: this must NOT fire for ``TaskDefinitionOverlayInput``,
        # a real subclass used for partial/overlay data, which skips this
        # requirement, matching today's ``if not self.partial`` guard.
        if type(self) is TaskDefinitionInput and self.launch_type == "FARGATE":
            if not self.execution_role:
                msg = (
                    'If your launch_type is "FARGATE", you must supply '
                    '"execution_role"'
                )
                raise ValueError(msg)
        return self


#: All-optional variant of TaskDefinitionInput, for partial/overlay
#: construction (e.g. StandaloneTaskAdapter/ServiceHelperTaskAdapter's
#: TaskDefinition.new(..., partial=True) call sites). ``containers`` opts
#: into ContainerDefinitionOverlayInput so partial container overrides
#: (e.g. a command override with no "image") validate correctly.
TaskDefinitionOverlayInput = partial_model(
    TaskDefinitionInput,
    name="TaskDefinitionOverlayInput",
    nested={"containers": ContainerDefinitionOverlayInput},
)
