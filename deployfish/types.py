#!/usr/bin/env python

import sys
from collections.abc import Callable, Sequence
from typing import (
    TYPE_CHECKING,
    Any,
    Optional,
)

if sys.version_info >= (3, 8):
    from typing import Protocol
else:
    from typing import Protocol

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

    @property
    def ssh_targets(self) -> Sequence["Instance"]:
        ...

    @property
    def ssh_target(self) -> Optional["Instance"]:
        ...

    @property
    def ssh_proxy_type(self) -> str:
        ...

class SupportsTunnel(Protocol):

    @property
    def tunnel_targets(self) -> Sequence["Instance"]:
        ...

    @property
    def tunnel_target(self) -> Optional["Instance"]:
        ...

    @property
    def ssh_tunnels(self) -> Sequence["SSHTunnel"]:
        ...

    def tunnel(self, tunnel: "SSHTunnel", verbose: bool = False, tunnel_target: "Instance" = None) -> None:
        ...

class SupportsExec(Protocol):

    @property
    def exec_enabled(self) -> bool:
        ...


class SupportsNetworking(SupportsSSH, SupportsTunnel, Protocol):
    pass


class SupportsCache(Protocol):

    cache: dict[str, Any]

    def get_cached(
        self,
        key: str,
        populator: Callable,
        args: list[Any],
        kwargs: dict[str, Any] = None
    ) -> Any:
        ...

class SupportsSecrets(Protocol):

    @property
    def secrets(self) -> dict[str, "Secret"]:
        ...

    @property
    def secrets_prefix(self) -> str:
        ...

    def reload_secrets(self) -> None:
        ...

    def write_secrets(self) -> None:
        ...

    def diff_secrets(self, other: Sequence["Secret"], ignore_external: bool = False) -> dict[str, Any]:
        ...


class SupportsModel(Protocol):

    objects: "Manager"
    config_section: str
    data: dict[str, Any]

    @property
    def pk(self) -> str:
        ...

    @property
    def name(self) -> str:
        ...

    @property
    def arn(self) -> str | None:
        ...

class SupportsTaskDefinition(SupportsModel, Protocol):

    containers: list["ContainerDefinition"]


class SupportsNetworkedModel(SupportsModel, SupportsNetworking, Protocol):
    pass

class SupportsSSHModel(SupportsModel, SupportsSSH, Protocol):
    pass

class SupportsTunnelModel(SupportsModel, SupportsSSH, SupportsTunnel, Protocol):
    pass

class SupportsExecModel(SupportsModel, SupportsSSH, SupportsExec, Protocol):
    pass

class SupportsModelWithSecrets(SupportsModel, SupportsSecrets, Protocol):
    pass

class SupportsService(
    SupportsModel,
    SupportsSSH,
    SupportsTunnel,
    SupportsSecrets,
    Protocol
):

    @property
    def exec_enabled(self) -> bool:
        ...

    @property
    def cluster(self) -> "Cluster":
        ...

    @property
    def task_definition(self) -> "TaskDefinition":
        ...

    @property
    def running_tasks(self) -> Sequence["InvokedTask"]:
        ...


class SupportsModelClass(Protocol):

    model: type["Model"]


class SupportsRendering(Protocol):

    datetime_format: str | None
    date_format: str | None
    float_precision: str | None
