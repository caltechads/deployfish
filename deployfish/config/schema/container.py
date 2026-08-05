"""
Pydantic models describing the shape of a ``deployfish.yml`` container
definition stanza. These validate and reshape input only -- the boto3-shaped
output dict is still assembled by hand in
:py:class:`deployfish.core.adapters.deployfish.ecs.container.ContainerDefinitionAdapter`.
"""

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

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
