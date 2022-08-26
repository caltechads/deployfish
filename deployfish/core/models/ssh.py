from typing import Sequence, cast, Any

from deployfish.config import get_config

from .abstract import Manager, Model
from .secrets import Secret
from .ec2 import Instance


# ----------------------------------------
# Managers
# ----------------------------------------

class SSHTunnelManager(Manager):

    def get(self, pk: str, **_) -> "SSHTunnel":
        config = get_config()
        section = config.get_section('tunnels')
        tunnels = {}
        for tunnel in section:
            tunnels[tunnel['name']] = tunnel
        if pk in tunnels:
            return cast("SSHTunnel", SSHTunnel.new(tunnels[pk], 'deployfish'))
        raise SSHTunnel.DoesNotExist(
            f'Could not find an ssh tunnel config named "{pk}" indeployfish.yml:tunnels'
        )

    def list(self, service_name: str = None, port: int = None) -> Sequence["SSHTunnel"]:
        config = get_config()
        section = config.get_section('tunnels')
        tunnels = [cast("SSHTunnel", SSHTunnel.new(tunnel, 'deployfish')) for tunnel in section]
        if service_name:
            tunnels = [tunnel for tunnel in tunnels if tunnel.data['service'] == service_name]
        elif port:
            tunnels = [tunnel for tunnel in tunnels if tunnel.data['port'] == port]
        return tunnels


# ----------------------------------------
# Models
# ----------------------------------------

class SSHTunnel(Model):
    """
    self.data here has the following structure:

        {
            'name': 'string',
            'service': 'string',
            'host': 'string',
            'port': 1234,
            'local_port': 1234,
        }
    """

    objects = SSHTunnelManager()
    config_section = 'tunnels'

    # ---------------------
    # Model overrides
    # ---------------------

    @property
    def pk(self) -> str:
        return self.data['name']

    @property
    def name(self) -> str:
        return self.data['name']

    @property
    def arn(self) -> None:
        return None

    # -----------------------------
    # SSHTunnel-specific properties
    # -----------------------------

    @property
    def local_port(self) -> int:
        return self.data['local_port']

    def secret(self, name: str) -> Secret:
        if 'secrets' not in self.cache:
            self.cache['secrets'] = {}
        if name not in self.cache['secrets']:
            if "." not in name:
                full_name = f'{self.service.secrets_prefix}{name}'
            else:
                full_name = name
            self.cache['secrets'][name] = Secret.objects.get(full_name)
        return self.cache['secrets'][name]

    def parse(self, key: str) -> Any:
        """
        deployfish supports putting 'config.KEY' as the value for the host and port keys in self.data

        Parse the value and dereference it from the live secrets for the service if necessary.
        """
        if isinstance(self.data[key], str):
            if self.data[key].startswith('config.'):
                _, key = self.data[key].split('.')
                try:
                    value = self.secret(key).value
                except Secret.DoesNotExist:
                    raise self.OperationFailed(
                        'SSHTunnel(pk="{}"): Service(pk="{}") has no secret named "{}"'.format(
                            self.name,
                            self.service.pk,
                            key
                        )
                    )
                return value
        return self.data[key]

    @property
    def host(self) -> str:
        if 'host' not in self.cache:
            self.cache['host'] = self.parse('host')
        return self.cache['host']

    @property
    def host_port(self) -> int:
        if 'host_port' not in self.cache:
            self.cache['host_port'] = self.parse('port')
        return self.cache['host_port']

    # ------------------------------
    # Related objects
    # ------------------------------

    @property
    def service(self):
        if 'service' not in self.cache:
            # Doing this import here to hopefully avoid circular dependencies between this file and ./ecs.py
            try:
                from .ecs import Service
            except ImportError:
                # We already imported this somewhere
                pass
            config = get_config()
            data = config.get_section_item('services', self.data['service'])
            # We actually want the live service here -- no point in tunneling to a service that doesn't
            # exist or is out of date with deployfish.yml
            self.cache['service'] = Service.objects.get(f'{data["cluster"]}:{data["name"]}')
        return self.cache['service']

    @service.setter
    def service(self, value):
        self.cache['service'] = value

    @property
    def cluster(self):
        return self.service.cluster

    # ---------------------
    # Network
    # ---------------------

    @property
    def ssh_target(self) -> Instance:
        return self.service.ssh_target

    @property
    def ssh_targets(self) -> Sequence[Instance]:
        return self.service.ssh_targets

    @property
    def tunnel_target(self) -> Instance:
        return self.service.tunnel_target
