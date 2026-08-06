from copy import copy
from typing import Any, cast

from pydantic import ValidationError

from deployfish.config.schema.task_definition import (
    TaskDefinitionInput,
    TaskDefinitionOverlayInput,
)
from deployfish.core.models.mixins import TaskDefinitionFARGATEMixin
from deployfish.core.models.secrets import Secret

from ...abstract import Adapter
from .container import ContainerDefinitionAdapter


class TaskDefinitionAdapter(TaskDefinitionFARGATEMixin, Adapter):
    """
    Convert our deployfish YAML definition of our task definition to the same
    format that :py:meth:`describe_task_definition` returns, but translate all
    container info into :py:class:`deployfish.core.models.ecs.ContainerDefinition`
    objects.

    Args:
        data: The data from deployfish.yml for this task definition

    Keyword Args:
        secrets: A list of :py:class:`deployfish.core.models.ecs.Secret` objects
            that are used by this task definition
        extra_environment: A dict of extra environment variables to add to the
            task definition
        partial: If True, this is a partial task definition, and we should be
            more lenient about what we accept as valid data.

    """

    def __init__(
        self,
        data: dict[str, Any],
        secrets: list[Secret] | None = None,
        extra_environment: dict[str, Any] | None = None,
        partial: bool = False,  # noqa: FBT001, FBT002
    ) -> None:
        """
        Initialize TaskDefinitionAdapter.

        Args:
            data: data.
            secrets: secrets.
            extra_environment: extra environment.
            partial: partial.

        Raises:
            SchemaException: if ``data`` does not validate against
                :py:class:`deployfish.config.schema.task_definition.TaskDefinitionInput`.

        """
        super().__init__(data)
        #: Secrets.
        self.secrets = secrets or []
        #: Extra environment.
        self.extra_environment = extra_environment or {}
        #: Partial.
        self.partial = partial
        #: The validated, reshaped task-definition stanza.
        self._input = self._validate(data)

    def _validate(
        self, data: dict[str, Any]
    ) -> TaskDefinitionInput:
        """
        Validate ``data`` against the appropriate input model, translating
        :py:exc:`pydantic.ValidationError` into :py:exc:`self.SchemaException`.

        Args:
            data: the raw task-definition stanza.

        .. note::

            Real callers (e.g. ``ServiceAdapter.get_task_definition()``,
            ``StandaloneTaskAdapter``) hand this adapter the *entire*
            ``deployfish.yml`` service/task stanza, not a pre-trimmed
            task-definition-only subset -- it includes keys like ``name``,
            ``cluster``, ``environment``, ``count``, ``load_balancer``, and
            ``config`` that ``TaskDefinitionInput``/``TaskDefinitionOverlayInput``
            (``extra="forbid"``) know nothing about. The old hand-rolled
            adapter tolerated this by only ever reading the specific keys it
            cared about via :py:meth:`Adapter.set`, silently ignoring
            everything else. To preserve that same leniency without loosening
            the (already-reviewed, unmodifiable) schema's ``extra="forbid"``,
            only keys the input model actually declares (by field name or
            alias) are forwarded to :py:meth:`~pydantic.BaseModel.model_validate`.

        Raises:
            SchemaException: if ``data`` does not validate.

        Returns:
            The validated, reshaped task-definition stanza.

        """
        if self.partial:
            input_model = TaskDefinitionOverlayInput
        else:
            input_model = TaskDefinitionInput
        model = cast("type[TaskDefinitionInput]", input_model)
        known_keys: set[str] = set()
        for field_name, field_info in model.model_fields.items():
            known_keys.add(field_name)
            if field_info.alias:
                known_keys.add(field_info.alias)
        filtered_data = {k: v for k, v in data.items() if k in known_keys}
        try:
            return model.model_validate(filtered_data)
        except ValidationError as e:
            errors = []
            for err in e.errors():
                loc = err["loc"]
                if loc and loc[0] == "containers" and len(loc) > 1:
                    index = loc[1]
                    container_name = f"#{index}"
                    containers = data.get("containers", [])
                    if isinstance(index, int) and index < len(containers):
                        container_name = containers[index].get(
                            "name", f"#{index}"
                        )
                    remainder = ".".join(str(p) for p in loc[2:])
                    label = f'container "{container_name}"'
                    if remainder:
                        label = f"{label}: {remainder}"
                    errors.append(f"{label}: {err['msg']}")
                else:
                    errors.append(f'{".".join(str(p) for p in loc)}: {err["msg"]}')
            msg = f"task definition is invalid: {'; '.join(errors)}"
            raise self.SchemaException(msg) from e

    def get_volumes(self) -> list[dict[str, Any]]:
        """
        Convert this task definition's validated volume declarations to the
        same structure that :py:meth:`describe_task_definition` returns for
        that info::

            [
                {
                    'name': 'string',
                    'host': {
                        'sourcePath': 'string'
                    },
                    'dockerVolumeConfiguration': {
                        'scope': 'task'|'shared',
                        'autoprovision': True|False,
                        'driver': 'string',
                        'driverOpts': {
                            'string': 'string'
                        },
                        'labels': {
                            'string': 'string'
                        }
                    },
                    'efsVolumeConfiguration': {
                        'fileSystemId': 'string',
                        'rootDirectory': 'string'
                    },
            ]

        Returns:
            A list of volume definitions for this task definition.

        """
        volumes: list[dict[str, Any]] = []
        for v in self._input.volumes or []:
            v_dict: dict[str, Any] = {"name": v.name}
            if v.path is not None:
                v_dict["host"] = {"sourcePath": v.path}
            elif v.config is not None:
                v_dict["dockerVolumeConfiguration"] = copy(
                    v.config.model_dump(by_alias=True, exclude_none=True)
                )
            elif v.efs_config is not None:
                efs: dict[str, Any] = {"fileSystemId": v.efs_config.file_system_id}
                if v.efs_config.root_directory is not None:
                    efs["rootDirectory"] = v.efs_config.root_directory
                v_dict["efsVolumeConfiguration"] = efs
            volumes.append(v_dict)
        return volumes

    def convert(self) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        Convert this task definition's validated data to the same structure
        that :py:meth:`describe_task_definition` returns, along with the
        keyword arguments needed to build the task definition's containers.

        Raises:
            SchemaException: if task-level cpu/memory conflict with the
                summed container cpu/memory requirements.

        Returns:
            A 2-tuple of ``(task_definition_data, container_kwargs)``.

        """
        task_input = self._input
        data: dict[str, Any] = {}
        if task_input.family is not None:
            data["family"] = task_input.family
        if task_input.network_mode is not None:
            data["networkMode"] = task_input.network_mode
        launch_type = task_input.launch_type
        if launch_type == "FARGATE":
            data["requiresCompatibilities"] = ["FARGATE"]
        if task_input.runtime_platform is not None:
            data["runtimePlatform"] = {
                "cpuArchitecture": task_input.runtime_platform.cpu_architecture,
                "operatingSystemFamily": (
                    task_input.runtime_platform.operating_system_family
                ),
            }
        if task_input.placement_constraints:
            data["placementConstraints"] = task_input.placement_constraints
        readonly_root_filesystem = task_input.readonly_root_filesystem
        if task_input.task_role_arn is not None:
            data["taskRoleArn"] = task_input.task_role_arn
        if task_input.execution_role is not None:
            data["executionRoleArn"] = task_input.execution_role
        data["volumes"] = self.get_volumes()
        containers_data = []
        for container_definition, _container_input in zip(
            self.data.get("containers", []),
            task_input.containers or [],
            strict=True,
        ):
            containers_data.append(
                ContainerDefinitionAdapter(
                    container_definition,
                    data,
                    secrets=self.secrets,
                    extra_environment=self.extra_environment,
                    partial=self.partial,
                    readonly_root_filesystem=readonly_root_filesystem,
                ).convert()
            )
        container_data = [c[0] for c in containers_data]
        self.set_task_cpu(data, container_data)
        self.set_task_memory(data, container_data)

        return data, {"containers": containers_data}
