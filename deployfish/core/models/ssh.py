from collections.abc import Sequence
from typing import Any, cast

from deployfish.config import get_config

from .abstract import Manager, Model
from .ec2 import Instance
from .secrets import Secret

# ----------------------------------------
# Managers
# ----------------------------------------


class SSHTunnelManager(Manager):
    """
    Model sshtunnel manager behavior.
    """

    def get(self, pk: str, **_) -> "SSHTunnel":
        """
        Get.

        Args:
            pk: pk.

        Keyword Args:
            _: .

        Returns:
            Operation result.

        """
        config = get_config()
        section = config.get_section("tunnels")
        tunnels = {}
        for tunnel in section:
            tunnels[tunnel["name"]] = tunnel
        if pk in tunnels:
            return cast("SSHTunnel", SSHTunnel.new(tunnels[pk], "deployfish"))
        msg = (
            f'Could not find an ssh tunnel config named "{pk}" indeployfish.yml:tunnels'
        )
        raise SSHTunnel.DoesNotExist(msg)

    def list(
        self, service_name: str | None = None, port: int | None = None
    ) -> Sequence["SSHTunnel"]:
        """
        List.

        Args:
            service_name: service name.
            port: port.

        Returns:
            Operation result.

        """
        config = get_config()
        section = config.get_section("tunnels")
        tunnels = [
            cast("SSHTunnel", SSHTunnel.new(tunnel, "deployfish")) for tunnel in section
        ]
        if service_name:
            tunnels = [
                tunnel for tunnel in tunnels if tunnel.data["service"] == service_name
            ]
        elif port:
            tunnels = [tunnel for tunnel in tunnels if tunnel.data["port"] == port]
        return tunnels


# ----------------------------------------
# Models
# ----------------------------------------


class SSHTunnel(Model):
    """
    self.data here has the following structure:

    .. code-block:: python

        {
            'name': 'string',
            'service': 'string',
            'host': 'string',
            'port': 1234,
            'local_port': 1234,
        }
    """

    #: Objects.
    objects = SSHTunnelManager()
    #: Config section.
    config_section = "tunnels"

    # ---------------------
    # Model overrides
    # ---------------------

    @property
    def pk(self) -> str:
        """
        Pk.

        Returns:
            Operation result.

        """
        return self.data["name"]

    @property
    def name(self) -> str:
        """
        Name.

        Returns:
            Operation result.

        """
        return self.data["name"]

    @property
    def arn(self) -> None:
        """
        Arn.
        """
        return None

    # -----------------------------
    # SSHTunnel-specific properties
    # -----------------------------

    @property
    def local_port(self) -> int:
        """
        Local port.

        Returns:
            Operation result.

        """
        return self.data["local_port"]

    def secret(self, name: str) -> Secret:
        """
        Secret.

        Args:
            name: name.

        Returns:
            Operation result.

        """
        if "secrets" not in self.cache:
            self.cache["secrets"] = {}
        if name not in self.cache["secrets"]:
            if "." not in name:
                full_name = f"{self.service.secrets_prefix}{name}"
            else:
                full_name = name
            self.cache["secrets"][name] = Secret.objects.get(full_name)
        return self.cache["secrets"][name]

    def parse(self, key: str) -> Any:
        """
        Deployfish supports putting 'config.KEY' as the value for the host and port keys
        in self.data

        Parse the value and dereference it from the live secrets for the service if
        necessary.

        Args:
            key: key.

        Returns:
            Operation result.

        """
        if isinstance(self.data[key], str):
            if self.data[key].startswith("config."):
                _, key = self.data[key].split(".")
                try:
                    value = self.secret(key).value
                except Secret.DoesNotExist:
                    msg = f'SSHTunnel(pk="{self.name}"): Service(pk="{self.service.pk}") has no secret named "{key}"'  # noqa: E501
                    raise self.OperationFailed(msg) from None
                return value
        return self.data[key]

    @property
    def host(self) -> str:
        """
        Host.

        Returns:
            Operation result.

        """
        if "host" not in self.cache:
            self.cache["host"] = self.parse("host")
        return self.cache["host"]

    @property
    def host_port(self) -> int:
        """
        Host port.

        Returns:
            Operation result.

        """
        if "host_port" not in self.cache:
            self.cache["host_port"] = self.parse("port")
        return self.cache["host_port"]

    # ------------------------------
    # Related objects
    # ------------------------------

    @property
    def service(self):
        """
        Service.

        Returns:
            Operation result.

        """
        if "service" not in self.cache:
            # Doing this import here to hopefully avoid circular dependencies between this file and ./ecs.py  # noqa: E501
            try:  # noqa: SIM105
                from .ecs import Service
            except ImportError:
                # We already imported this somewhere
                pass
            config = get_config()
            data = config.get_section_item("services", self.data["service"])
            # We actually want the live service here -- no point in tunneling to a service that doesn't  # noqa: E501
            # exist or is out of date with deployfish.yml
            self.cache["service"] = Service.objects.get(
                f"{data['cluster']}:{data['name']}"
            )
        return self.cache["service"]

    @service.setter
    def service(self, value):
        """
        Service.

        Args:
            value: value.

        """
        self.cache["service"] = value

    @property
    def cluster(self):
        """
        Cluster.

        Returns:
            Operation result.

        """
        return self.service.cluster

    # ---------------------
    # Network
    # ---------------------

    @property
    def ssh_target(self) -> Instance:
        """
        Ssh target.

        Returns:
            Operation result.

        """
        return self.service.ssh_target

    @property
    def ssh_targets(self) -> Sequence[Instance]:
        """
        Ssh targets.

        Returns:
            Operation result.

        """
        return self.service.ssh_targets

    @property
    def tunnel_target(self) -> Instance:
        """
        Tunnel target.

        Returns:
            Operation result.

        """
        return self.service.tunnel_target
