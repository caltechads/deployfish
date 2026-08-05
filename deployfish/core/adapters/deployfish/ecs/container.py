import re
from typing import Any, cast

from pydantic import ValidationError

from deployfish.config.schema.container import (
    ContainerDefinitionInput,
    ContainerDefinitionOverlayInput,
)
from deployfish.core.models.secrets import Secret

from ...abstract import Adapter


class ContainerDefinitionAdapter(Adapter):
    """
    Convert our deployfish YAML definition of our containers to the same format
    that :py:meth:`describe_task_definition` returns for container definitions.

    Args:
        data: a deployfish.yml container definition stanza

    Keyword Args:
        task_definition_data:
            :py:attr:`deployfish.core.models.ecs.TaskDefinition.data` from the
            owning :py:class:`deployfish.core.models.ecs.TaskDefinition`
        secrets: a list of :py:class:`deployfish.core.models.secrets.Secret`
        extra_environment: a dict of extra environment variables to add to the
            container
        partial: if ``True``, we're updating an existing
            :py:class:`deployfish.core.models.ecs.ContainerDefinition`` from a
            partial set of overrides.  Setting this to ``True`` will cause us to
            ignore any missing required fields.

    """

    #: Mount re.
    MOUNT_RE = re.compile("[^A-Za-z0-9_-]")

    def __init__(  # noqa: PLR0913
        self,
        data: dict[str, Any],
        task_definition_data: dict[str, Any] | None = None,
        secrets: list[Secret] | None = None,
        extra_environment: dict[str, Any] | None = None,
        partial: bool = False,  # noqa: FBT001, FBT002
        readonly_root_filesystem: bool | None = None,  # noqa: FBT001
    ) -> None:
        """
        Initialize ContainerDefinitionAdapter.

        Args:
            data: data.
            task_definition_data: task definition data.
            secrets: secrets.
            extra_environment: extra environment.
            partial: partial.
            readonly_root_filesystem: readonly root filesystem.

        Raises:
            SchemaException: if ``data`` does not validate against
                :py:class:`deployfish.config.schema.container.ContainerDefinitionInput`.

        """
        super().__init__(data)
        #: Task definition data.
        self.task_definition_data = task_definition_data or {}
        #: Secrets.
        self.secrets = secrets or []
        #: Extra environment.
        self.extra_environment = extra_environment or {}
        #: Partial.
        self.partial = partial
        #: Readonly root filesystem.
        self.readonly_root_filesystem = readonly_root_filesystem
        #: The validated, reshaped container stanza.
        self._input = self._validate(data)

    def _validate(self, data: dict[str, Any]) -> ContainerDefinitionInput:
        """
        Validate ``data`` against the appropriate input model, translating
        :py:exc:`pydantic.ValidationError` into :py:exc:`self.SchemaException`.

        Args:
            data: the raw container stanza.

        Raises:
            SchemaException: if ``data`` does not validate.

        Returns:
            The validated, reshaped container stanza.

        """
        if self.partial:
            input_model = ContainerDefinitionOverlayInput
        else:
            input_model = ContainerDefinitionInput
        model = cast("type[ContainerDefinitionInput]", input_model)
        try:
            return model.model_validate(data)
        except ValidationError as e:
            errors = "; ".join(
                f'{".".join(str(p) for p in err["loc"])}: {err["msg"]}'
                for err in e.errors()
            )
            msg = f"container definition is invalid: {errors}"
            raise self.SchemaException(msg) from e

    @property
    def is_fargate(self) -> bool:
        """
        Return ``True`` if this container is part of a FARGATE task

        Returns:
            Operation result.

        """
        return "FARGATE" in self.task_definition_data.get("requiresCompatibilities", [])

    def get_secrets(self) -> list[dict[str, str]]:
        """
        Add parameter store values to the container's 'secrets' list. The task
        will fail if we try to do this and we don't have an execution role, so
        we don't pass the secrets if it doesn't have an execution role.

        Returns:
            Operation result.

        """
        return [{"name": s.name, "valueFrom": s.pk} for s in self.secrets]

    def get_mountPoints(self) -> list[dict[str, str]]:  # noqa: N802
        """
        In ``deployfish.yml``, volumes take one of these two forms::

            volumes:
                - storage:/container/path

        or::

            volumes:
                - /host/path:/container/path
                - /host/path-ro:/container/path-ro:ro

        The first form is the new style volume definition.  The "storage" bit
        refers to a volume on the task definition named "storage", which has all
        the volume configuration info.

        The second form is the old-style volume definition.  Before we allowed
        the "volumes:" section in the task definition yml, you could define
        volumes on individual containers and the "volumes" list in the
        :py:meth:`register_task_definition` AWS API call would be
        auto-constructed based on the host and container path.

        To deal with the second form, we need to internally convert to the first
        form and add a hidden volume definition on the task definition, then
        transform the volume mountpoint to the first form.

        Returns:
            A list of dicts, each of which is a mountpoint definition for the
            container.

        """
        volume_names = set()
        for v in self.task_definition_data["volumes"]:
            volume_names.add(v["name"])

        mountPoints: list[dict[str, str]] = []  # noqa: N806
        for v in self._input.volumes:
            fields = v.split(":")
            host_path = fields[0]
            container_path = fields[1]
            readOnly = False  # noqa: N806
            if len(fields) == 3:  # noqa: PLR2004
                readOnly = fields[2] == "ro"  # noqa: N806
            name = self.MOUNT_RE.sub("_", host_path)
            name = name[:254] if len(name) > 254 else name  # noqa: PLR2004
            if name not in volume_names:
                # TODO: if the host_path doesn't start with a /, ensure that
                # the volume already exists in the task definition, otherwise
                # raise ContainerYamlSchemaException Add this container specific
                # volume to the task definition
                self.task_definition_data["volumes"].append(
                    {"name": name, "host": {"sourcePath": host_path}}
                )
                volume_names.add(name)
            mountPoints.append(
                {
                    "sourceVolume": name,
                    "containerPath": container_path,
                    "readOnly": readOnly,
                }
            )
        return mountPoints

    def get_ports(self) -> list[dict[str, Any]]:
        """
        ``deployfish.yml`` port mappings look like this::

            ports:
                - "80"
                - "8443:443"
                - "8125:8125/udp"

        Convert them to this::

            [
                {"containerPort": 80, "protocol": "tcp"},
                {"containerPort": 443, "hostPort": 8443, "protocol": "tcp"},
                {"containerPort": 8125, "hostPort": 8125, "protocol": "udp"},
            ]

        Returns:
            A list of dicts, each of which is a port mapping definition for the
            container.

        """
        port_mappings = []
        for p in self._input.ports:
            mapping: dict[str, Any] = {
                "containerPort": p.container_port,
                "protocol": p.protocol,
            }
            if p.host_port is not None:
                mapping["hostPort"] = p.host_port
            port_mappings.append(mapping)
        return port_mappings

    def get_environment(self) -> list[dict[str, str]]:
        """
        ``deployfish.yml`` environment variables are defined in one of the two
        following ways::

            environment:
                - FOO=bar
                - BAZ=bash

        or::

            environment:
                FOO: bar
                BAZ: bash

        Convert them to this, which is what :py:meth:`describe_task_definition`
        returns::

            [
                {"name": "FOO", "value": "bar"},
                {"name": "BAZ", "value": "bash}
            ]

        Returns:
            A list of dicts, each of which is an environment variable definition

        """
        environment = dict(self._input.environment or {})
        environment.update(self.extra_environment)
        return [{"name": k, "value": v} for k, v in environment.items()]

    def get_dockerLabels(self) -> dict[str, str]:  # noqa: N802
        """
        ``deployfish.yml`` docker labels are defined in one of the two following
        ways::

            labels:
                - FOO=bar
                - BAZ=bash

        or::

            labels:
                FOO: bar
                BAZ: bash

        Convert them to this, which is what :py:meth:`describe_task_definition`
        returns::

            {
                'FOO': 'bar',
                'BAZ': 'bash'
            {

        Returns:
            A dict of docker labels

        """
        return dict(self._input.labels)

    def get_ulimits(self) -> list[dict[str, Any]]:
        """
        Get ulimits.

        Returns:
            Operation result.

        """
        return [
            {"name": name, "softLimit": u.soft, "hardLimit": u.hard}
            for name, u in self._input.ulimits.items()
        ]

    def get_logConfiguration(self) -> dict[str, Any]:  # noqa: N802
        """
        Get log configuration.

        Returns:
            Operation result.

        """
        if self._input.logging is None:
            return {}
        lc: dict[str, Any] = {"logDriver": self._input.logging.driver}
        if self._input.logging.options:
            lc["options"] = self._input.logging.options
        return lc

    def get_linuxParameters(self) -> dict[str, Any]:  # noqa: N802
        """
        Get linux parameters.

        Returns:
            Operation result.

        """
        linux_parameters: dict[str, Any] = {}
        if self._input.cap_add or self._input.cap_drop:
            capabilities: dict[str, Any] = {}
            if self._input.cap_add:
                capabilities["add"] = self._input.cap_add
            if self._input.cap_drop:
                capabilities["drop"] = self._input.cap_drop
            linux_parameters["capabilities"] = capabilities
        if self._input.tmpfs:
            linux_parameters["tmpfs"] = []
            for tc in self._input.tmpfs:
                entry: dict[str, Any] = {
                    "containerPath": tc.container_path,
                    "size": tc.size,
                }
                if tc.mount_options:
                    entry["mountOptions"] = tc.mount_options
                linux_parameters["tmpfs"].append(entry)
        return linux_parameters

    def get_extraHosts(self) -> list[dict[str, str]]:  # noqa: N802
        """
        Get extra hosts.

        Returns:
            Operation result.

        """
        return [
            {"hostname": h.hostname, "ipAddress": h.ip_address}
            for h in self._input.extra_hosts
        ]

    def get_cpu(self) -> int | None:
        """
        Get the ``cpu`` value for this container, which is the number of cpu
        units to reserve for the container.    One full CPU is 1024 units.

        * If the task is a FARGATE task, then ``cpu`` is optional.
        * If the task is an EC2 task, then ``cpu`` is required.  If it is not
          present in the ``deployfish.yml`` file, then it defaults to 256 unless
          this is a partial container overlay, in which case it is omitted so the
          parent container value is preserved.

        If ``cpu`` is specified then the only requirement is that the sum of all
        ``cpu`` values for all containers in the task be lower than the ``cpu``
        value specified in the task definition, if that is present.

        Returns:
            The ``cpu`` value for this container.

        """
        default = None if self.is_fargate or self.partial else 256
        return self._input.cpu if self._input.cpu is not None else default

    def get_memory(self) -> int | None:
        """
        Get the ``memory`` value for this container, which is the amount
        of memory (in MiB) to allow the container to use.

        * If the task is a FARGATE task, then ``memory`` is optional.
        * If the task is an EC2 task, ``memory`` is required at the container
          level if it is not specified at the task level.

        If ``memory`` is specified then the only requirement is that the sum of all
        ``memory`` values for all containers in the task be lower than the ``memory``
        value specified in the task definition, if that is present.

        Raises:
            SchemaException: if the task is an EC2 task and ``memory`` is not
                specified in container definition the ``deployfish.yml`` file and is
                also not present at the task level in the ``deployfish.yml`` file.

        Returns:
            The ``cpu`` value for this container.

        """
        if self.is_fargate:
            if self._input.memory is None:
                return None
        if self._input.memory is None:
            if "memory" in self.task_definition_data:
                return None
            if not self.partial:
                msg = (
                    f'container "{self._input.name}": memory is required for '
                    "containers if not specified at the task level"
                )
                raise self.SchemaException(msg)
            return None
        return self._input.memory

    def convert(self) -> tuple[dict[str, Any], dict[str, Any]]:  # noqa: PLR0912, PLR0915
        """
        Convert.

        Returns:
            Operation result.

        """
        data: dict[str, Any] = {}
        # name/image/essential are Optional on ContainerDefinitionOverlayInput
        # (partial=True); when absent there, Adapter.set()'s old behavior was
        # to omit the key entirely rather than apply a default, so we do the
        # same here. On the strict ContainerDefinitionInput (partial=False)
        # these are never None, so this is equivalent to unconditional
        # assignment in that mode.
        if self._input.name is not None:
            data["name"] = self._input.name
        if self._input.image is not None:
            data["image"] = self._input.image
        if self._input.essential is not None:
            data["essential"] = self._input.essential
        cpu = self.get_cpu()
        if self._input.memory_reservation is not None:
            data["memoryReservation"] = self._input.memory_reservation
        if cpu is not None:
            data["cpu"] = cpu
        memory = self.get_memory()
        if memory is not None:
            data["memory"] = memory
        memoryReservation = data.get("memoryReservation")  # noqa: N806
        if memoryReservation is None and memory is None:
            if not self.partial:
                if not self.is_fargate:
                    data["memory"] = 512
        if memoryReservation is not None and memory is not None:
            if memoryReservation >= memory:
                msg = (
                    f'container "{self._input.name}": "memoryReservation" '
                    'must be less than "memory"'
                )
                raise self.SchemaException(msg)
        if self._input.ports:
            data["portMappings"] = self.get_ports()
        if self._input.command:
            data["command"] = self._input.command
        if self._input.entrypoint:
            data["entryPoint"] = self._input.entrypoint
        if self._input.ulimits:
            data["ulimits"] = self.get_ulimits()
        if self._input.environment:
            data["environment"] = self.get_environment()
        if self._input.volumes:
            data["mountPoints"] = self.get_mountPoints()
        if self._input.links:
            data["links"] = self._input.links
        if self._input.labels:
            data["dockerLabels"] = self.get_dockerLabels()
        if self._input.logging:
            data["logConfiguration"] = self.get_logConfiguration()
        if self._input.extra_hosts:
            data["extraHosts"] = self.get_extraHosts()
        if self._input.cap_add or self._input.cap_drop or self._input.tmpfs:
            data["linuxParameters"] = self.get_linuxParameters()
        if self.secrets:
            data["secrets"] = self.get_secrets()
        if self.readonly_root_filesystem is not None:
            data["readonlyRootFilesystem"] = self.readonly_root_filesystem
        kwargs = {}
        kwargs["secrets"] = self.secrets
        return data, kwargs
