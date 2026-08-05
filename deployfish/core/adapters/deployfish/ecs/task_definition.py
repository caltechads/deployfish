from copy import copy
from typing import Any

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

        """
        super().__init__(data)
        #: Secrets.
        self.secrets = secrets or []
        #: Extra environment.
        self.extra_environment = extra_environment or {}
        #: Partial.
        self.partial = partial

    def get_volumes(self) -> list[dict[str, Any]]:
        """
        In the YAML, volume definitions look like this::

            volumes:
              - name: 'string'
                path: 'string'
                config:
                  scope: 'task' | 'shared'
                  autoprovision: true | false
                  driver: 'string'
                  driverOpts:
                      'string': 'string'
                  labels:
                      'string': 'string'
                efs_config:
                  file_system_id: 'string'
                  root_directory: 'string'

        .. note::

            People can only actually specify one of ``path``, ``config`` or
            ``efs_config`` -- they're mutually exclusive.  And ``path`` is not
            available for FARGATE tasks.


        Convert that to to the same structure that
        :py:meth:`describe_task_definition` returns for that info::

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

        .. warning::

            Old-style container definitions in deployfish.yml could be specified
            entirely in the container's own `volumes:` section.

        Returns:
            A list of volume definitions for this task definition.

        """
        volume_names = set()
        volumes = []
        volumes_data = self.data.get("volumes", [])
        for v in volumes_data:
            if v["name"] in volume_names:
                continue
            v_dict = {"name": v["name"]}
            if not self.only_one_is_True(
                [x in v for x in ["path", "config", "efs_config"]]
            ):
                msg = (
                    'When defining volumes, specify only one of "path", "config" or '
                    '"efs_config"'
                )
                raise self.SchemaException(msg)
            if "path" in v:
                v_dict["host"] = {}
                v_dict["host"]["sourcePath"] = v["path"]
            elif "config" in v:
                v_dict["dockerVolumeConfiguration"] = copy(v["config"])
            elif "efs_config" in v:
                try:
                    v_dict["efsVolumeConfiguration"] = {
                        "fileSystemId": v["efs_config"]["file_system_id"]
                    }
                except KeyError as e:
                    raise self.SchemaException(str(e)) from e
                if "root_directory" in v["efs_config"]:
                    v_dict["efsVolumeConfiguration"]["rootDirectory"] = v["efs_config"][
                        "root_directory"
                    ]
            volumes.append(v_dict)
            volume_names.add(v_dict["name"])
        return volumes

    def convert(self) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        :rtype: dict(str, Any), dict(str, Any)

        Returns:
            Operation result.

        """
        data: dict[str, Any] = {}
        self.set(data, "family")
        self.set(data, "network_mode", dest_key="networkMode", default="bridge")
        launch_type = self.data.get("launch_type", "EC2")
        if launch_type == "FARGATE":
            data["requiresCompatibilities"] = ["FARGATE"]
        if self.data.get("runtime_platform", None):
            data["runtimePlatform"] = {}
            data["runtimePlatform"]["cpuArchitecture"] = self.data[
                "runtime_platform"
            ].get("cpu_architecture", "X86_64")
            data["runtimePlatform"]["operatingSystemFamily"] = self.data[
                "runtime_platform"
            ].get("operating_system_family", "LINUX")
        if self.data.get("placementConstraints", None):
            data["placementConstraints"] = self.data["placementConstraints"]
        readonly_root_filesystem = self.data.get("readonly_root_filesystem")
        self.set(data, "task_role_arn", dest_key="taskRoleArn", optional=True)
        self.set(data, "execution_role", dest_key="executionRoleArn", optional=True)
        if not self.partial and (
            launch_type == "FARGATE" and not data["executionRoleArn"]
        ):
            msg = 'If your launch_type is "FARGATE", you must supply "execution_role"'
            raise self.SchemaException(msg)
        data["volumes"] = self.get_volumes()
        containers_data = []
        if self.partial:
            containers = self.data.get("containers", [])
        else:
            try:
                containers = self.data["containers"]
            except KeyError as e:
                msg = "You must define at least one container in your task definition"
                raise self.SchemaException(msg) from e
        for container_definition in containers:
            containers_data.append(  # noqa: PERF401
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
