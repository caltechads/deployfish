from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any, Literal, Protocol

if TYPE_CHECKING:
    from deployfish.core.models import (
        Cluster,
        ContainerDefinition,
        Instance,
        InvokedTask,
        Manager,
        Model,
        Secret,
        SSHTunnel,
        TaskDefinition,
    )


class SupportsSSH(Protocol):
    """Protocol for models that support SSH access."""

    @property
    def ssh_targets(self) -> Sequence["Instance"]:
        """Return SSH target candidates."""
        ...

    @property
    def ssh_target(self) -> "Instance | None":
        """Return selected SSH target."""
        ...

    @property
    def ssh_proxy_type(self) -> Literal["bastion", "ssm"]:
        """Return proxy backend name."""
        ...


class SupportsTunnel(Protocol):
    """Protocol for models that support SSH tunnels."""

    @property
    def tunnel_targets(self) -> Sequence["Instance"]:
        """Return tunnel target candidates."""
        ...

    @property
    def tunnel_target(self) -> "Instance | None":
        """Return selected tunnel target."""
        ...

    @property
    def ssh_tunnels(self) -> Sequence["SSHTunnel"]:
        """Return declared SSH tunnels."""
        ...

    def tunnel(
        self,
        tunnel: "SSHTunnel",
        verbose: bool = False,  # noqa: FBT001, FBT002
        tunnel_target: "Instance | None" = None,
    ) -> None:
        """
        Open one configured tunnel.

        Args:
            tunnel: Tunnel configuration to open.
            verbose: Whether to print detailed output.
            tunnel_target: Explicit target override.

        """
        ...


class SupportsExec(Protocol):
    """Protocol for models that support ECS exec."""

    @property
    def exec_enabled(self) -> bool:
        """Return whether exec is enabled."""
        ...


class SupportsNetworking(SupportsSSH, SupportsTunnel, Protocol):
    """Protocol for models that support SSH and tunnel workflows."""


class SupportsCache(Protocol):
    """Protocol for objects that cache computed values."""

    #: Per-instance memoization store.
    cache: dict[str, Any]

    def get_cached(
        self,
        key: str,
        populator: Callable[..., Any],
        args: list[Any],
        kwargs: dict[str, Any] | None = None,
    ) -> Any:
        """
        Return cached value or populate and cache it.

        Args:
            key: Cache key.
            populator: Callback used to populate cache on miss.
            args: Positional arguments passed to populator.
            kwargs: Keyword arguments passed to populator.

        """
        ...


class SupportsSecrets(Protocol):
    """Protocol for models that manage externalized secrets."""

    @property
    def secrets(self) -> dict[str, "Secret"]:
        """Return secrets keyed by logical name."""
        ...

    @property
    def secrets_prefix(self) -> str:
        """Return secrets prefix path."""
        ...

    def reload_secrets(self) -> None:
        """Refresh secrets from backing store."""
        ...

    def write_secrets(self) -> None:
        """Persist secrets to backing store."""
        ...

    def diff_secrets(
        self,
        other: Sequence["Secret"] | dict[str, "Secret"],
        ignore_external: bool = False,  # noqa: FBT001, FBT002
    ) -> dict[str, Any]:
        """
        Return secret diff summary.

        Args:
            other: Secrets to compare against current collection.
            ignore_external: Whether to ignore externally managed secrets.

        """
        ...


class SupportsModel(Protocol):
    """Protocol shared by deployfish domain models."""

    #: Manager instance for persistence and lookups.
    objects: "Manager"
    #: deployfish.yml section that owns this model.
    config_section: str
    #: Raw model payload.
    data: dict[str, Any]

    @property
    def pk(self) -> str:
        """Return primary key."""
        ...

    @property
    def name(self) -> str:
        """Return human-readable name."""
        ...

    @property
    def arn(self) -> str | None:
        """Return AWS ARN when available."""
        ...


class SupportsTaskDefinition(SupportsModel, Protocol):
    """Protocol for task definitions."""

    #: Container definitions attached to task definition.
    containers: list["ContainerDefinition"]


class SupportsNetworkedModel(SupportsModel, SupportsNetworking, Protocol):
    """Protocol for network-aware models."""


class SupportsSSHModel(SupportsModel, SupportsSSH, Protocol):
    """Protocol for SSH-capable models."""


class SupportsTunnelModel(SupportsModel, SupportsSSH, SupportsTunnel, Protocol):
    """Protocol for tunnel-capable models."""


class SupportsExecModel(SupportsModel, SupportsSSH, SupportsExec, Protocol):
    """Protocol for exec-capable models."""


class SupportsModelWithSecrets(SupportsModel, SupportsSecrets, Protocol):
    """Protocol for secret-bearing models."""


class SupportsService(
    SupportsModel,
    SupportsSSH,
    SupportsTunnel,
    SupportsSecrets,
    Protocol,
):
    """Protocol for ECS service models."""

    @property
    def exec_enabled(self) -> bool:
        """Return whether ECS exec is enabled."""
        ...

    @property
    def cluster(self) -> "Cluster":
        """Return owning cluster."""
        ...

    @property
    def task_definition(self) -> "TaskDefinition":
        """Return current task definition."""
        ...

    @property
    def running_tasks(self) -> Sequence["InvokedTask"]:
        """Return active invoked tasks."""
        ...


class SupportsModelClass(Protocol):
    """Protocol for controllers/loaders that expose a model class."""

    #: Model class associated with controller/helper.
    model: type["Model"]


class SupportsRendering(Protocol):
    """Protocol for objects that carry render formatting preferences."""

    #: Preferred datetime format string.
    datetime_format: str | None
    #: Preferred date format string.
    date_format: str | None
    #: Preferred float precision.
    float_precision: int | None
