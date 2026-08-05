"""
Pydantic models describing the shape of a ``deployfish.yml`` container
definition stanza. These validate and reshape input only -- the boto3-shaped
output dict is still assembled by hand in
:py:class:`deployfish.core.adapters.deployfish.ecs.container.ContainerDefinitionAdapter`.
"""

import re
import shlex
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator

#: Matches ``"hostPort[:containerPort[/protocol]]"`` port mapping strings.
_PORTS_RE = re.compile(
    r"(?P<hostPort>\d+)(:(?P<containerPort>\d+)(/(?P<protocol>udp|tcp))?)?"
)
#: Matches characters not allowed in an auto-generated volume name.
_MOUNT_RE = re.compile("[^A-Za-z0-9_-]")


class PortMapping(BaseModel):
    """
    A single container port mapping.

    Args:
        host_port: the host port, if any.
        container_port: the container port.
        protocol: ``"tcp"`` or ``"udp"``.

    """

    #: Pydantic model configuration.
    model_config = ConfigDict(extra="forbid")

    #: The host port, if this mapping specifies one.
    host_port: int | None = None
    #: The container port.
    container_port: int
    #: The protocol -- ``"tcp"`` or ``"udp"``.
    protocol: str = "tcp"

    @classmethod
    def parse(cls, raw: int | str) -> "PortMapping":
        """
        Parse a ``deployfish.yml`` ports entry, which may be a bare port
        number or a ``"hostPort[:containerPort[/protocol]]"`` string.

        Args:
            raw: the raw ports list entry.

        Raises:
            ValueError: if ``raw`` is not a valid port mapping.

        Returns:
            The parsed ``PortMapping``.

        """
        text = str(raw)
        match = _PORTS_RE.search(text)
        if not match:
            msg = f"{raw} is not a valid port mapping"
            raise ValueError(msg)
        if not match.group("containerPort"):
            # A bare port number is the container port, not the host port.
            return cls(container_port=int(match.group("hostPort")))
        protocol = match.group("protocol") or "tcp"
        return cls(
            host_port=int(match.group("hostPort")),
            container_port=int(match.group("containerPort")),
            protocol=protocol,
        )


class Ulimit(BaseModel):
    """
    A single container ulimit.

    Args:
        soft: the soft limit.
        hard: the hard limit.

    """

    #: Pydantic model configuration.
    model_config = ConfigDict(extra="forbid")

    #: The soft limit.
    soft: int
    #: The hard limit.
    hard: int

    @model_validator(mode="before")
    @classmethod
    def _normalize_scalar_or_dict(cls, data: Any) -> Any:
        """
        Accept either a bare scalar (``soft == hard``) or a
        ``{"soft": ..., "hard": ...}`` dict.

        Args:
            data: the raw ulimit value.

        Returns:
            A dict with ``soft`` and ``hard`` keys.

        """
        if isinstance(data, dict):
            return data
        return {"soft": data, "hard": data}


class ExtraHost(BaseModel):
    """
    A single ``/etc/hosts`` entry to add to the container.

    Args:
        hostname: the hostname.
        ip_address: the IP address.

    """

    #: Pydantic model configuration.
    model_config = ConfigDict(extra="forbid")

    #: The hostname.
    hostname: str
    #: The IP address.
    ip_address: str

    @classmethod
    def parse(cls, raw: str) -> "ExtraHost":
        """
        Parse a ``"hostname:ip_address"`` extra_hosts entry.

        Args:
            raw: the raw extra_hosts list entry.

        Returns:
            The parsed ``ExtraHost``.

        """
        hostname, ip_address = raw.split(":")
        return cls(hostname=hostname, ip_address=ip_address)


class LoggingConfig(BaseModel):
    """
    A container's logging configuration.

    Args:
        driver: the log driver.
        options: log driver options.

    """

    #: Pydantic model configuration.
    model_config = ConfigDict(extra="forbid")

    #: The log driver.
    driver: str = Field(...)
    #: Log driver options.
    options: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _require_driver(cls, data: Any) -> Any:
        """
        Raise a clear, specific error when ``driver`` is missing, instead of
        Pydantic's generic "field required" message.

        Args:
            data: the raw logging block.

        Raises:
            ValueError: if ``driver`` is missing.

        Returns:
            ``data`` unchanged.

        """
        if isinstance(data, dict) and "driver" not in data:
            msg = 'logging: block must contain "driver"'
            raise ValueError(msg)
        return data


class TmpfsMount(BaseModel):
    """
    A single tmpfs mount for a container.

    Args:
        container_path: the container path to mount.
        size: the size, in MiB.
        mount_options: mount options.

    """

    #: Pydantic model configuration.
    model_config = ConfigDict(extra="forbid")

    #: The container path to mount.
    container_path: str
    #: The size, in MiB.
    size: int
    #: Mount options.
    mount_options: list[str] = Field(default_factory=list)


def _split_command(value: Any) -> Any:
    """
    Split a shell command string into argv, if given as a string.

    Args:
        value: the raw ``command``/``entrypoint`` field value.

    Returns:
        The split argv list if ``value`` is a string, otherwise ``value``
        unchanged.

    """
    if isinstance(value, str):
        return shlex.split(value)
    return value


def _parse_ports(value: Any) -> Any:
    """
    Parse each raw ports entry into a PortMapping-constructible dict.

    Args:
        value: the raw ``ports`` field value.

    Returns:
        A list with each entry converted to a ``PortMapping`` if ``value``
        is a list, otherwise ``value`` unchanged.

    """
    if not isinstance(value, list):
        return value
    return [
        PortMapping.parse(v) if not isinstance(v, PortMapping) else v for v in value
    ]


def _normalize_environment(value: Any) -> Any:
    """
    Normalize deployfish.yml's list-of-"K=V"-or-dict environment shape.

    Args:
        value: the raw ``environment`` field value.

    Returns:
        A ``{key: value}`` dict if ``value`` is a list, otherwise ``value``
        unchanged.

    """
    if isinstance(value, list):
        result: dict[str, str] = {}
        for entry in value:
            key, _, val = entry.partition("=")
            result[key] = val
        return result
    return value


def _normalize_labels(value: Any) -> Any:
    """
    Normalize deployfish.yml's list-of-"K=V"-or-dict labels shape.

    Args:
        value: the raw ``labels`` field value.

    Returns:
        A ``{key: value}`` dict if ``value`` is a list, otherwise ``value``
        unchanged.

    """
    if isinstance(value, list):
        result: dict[str, str] = {}
        for entry in value:
            key, val = entry.split("=")
            result[key] = val
        return result
    return value


def _parse_extra_hosts(value: Any) -> Any:
    """
    Parse each raw extra_hosts entry into an ExtraHost-constructible value.

    Args:
        value: the raw ``extra_hosts`` field value.

    Returns:
        A list with each string entry converted to an ``ExtraHost`` if
        ``value`` is a list, otherwise ``value`` unchanged.

    """
    if not isinstance(value, list):
        return value
    return [ExtraHost.parse(v) if isinstance(v, str) else v for v in value]


class ContainerDefinitionInput(BaseModel):
    """
    Validates and reshapes a single ``deployfish.yml`` container definition
    stanza. Does not produce the boto3-shaped output dict -- see
    :py:class:`deployfish.core.adapters.deployfish.ecs.container.ContainerDefinitionAdapter`
    for that.

    Args:
        name: the container name.
        image: the container image.

    """

    #: Pydantic model configuration.
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    #: The container name.
    name: str
    #: The container image.
    image: str
    #: Whether this container is essential to the task.
    essential: bool = True
    #: CPU units to reserve, if specified at the container level.
    cpu: int | None = None
    #: Memory (MiB) to allow, if specified at the container level.
    memory: int | None = None
    #: Soft memory reservation (MiB), if specified.
    memory_reservation: int | None = Field(default=None, alias="memoryReservation")
    #: The container's entrypoint command, if overridden.
    command: Annotated[list[str] | None, BeforeValidator(_split_command)] = None
    #: The container's entrypoint, if overridden.
    entrypoint: Annotated[list[str] | None, BeforeValidator(_split_command)] = None
    #: Legacy container links.
    links: list[str] = Field(default_factory=list)
    #: Port mappings for this container.
    ports: Annotated[list[PortMapping], BeforeValidator(_parse_ports)] = Field(
        default_factory=list
    )
    #: Environment variables for this container.
    environment: Annotated[dict[str, str], BeforeValidator(_normalize_environment)] = (
        Field(default_factory=dict)
    )
    #: Docker labels for this container.
    labels: Annotated[dict[str, str], BeforeValidator(_normalize_labels)] = Field(
        default_factory=dict
    )
    #: Ulimits for this container, keyed by ulimit name.
    ulimits: dict[str, Ulimit] = Field(default_factory=dict)
    #: Logging configuration for this container, if overridden.
    logging: LoggingConfig | None = None
    #: Extra /etc/hosts entries for this container.
    extra_hosts: Annotated[
        list[ExtraHost], BeforeValidator(_parse_extra_hosts)
    ] = Field(default_factory=list)
    #: Linux capabilities to add.
    cap_add: list[str] = Field(default_factory=list)
    #: Linux capabilities to drop.
    cap_drop: list[str] = Field(default_factory=list)
    #: tmpfs mounts for this container.
    tmpfs: list[TmpfsMount] = Field(default_factory=list)
    #: Volume mount specs, in "host:container[:ro]" or "volumeName:container" form.
    volumes: list[str] = Field(default_factory=list)
