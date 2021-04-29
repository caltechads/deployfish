from deployfish.config import get_config

from .abstract import Manager, Model
from .secrets import Secret


# ----------------------------------------
# Managers
# ----------------------------------------

class SSHTunnelManager(Manager):

    def get(self, pk):
        # hint: (str["{tunnel_name}"])
        config = get_config()
        section = config.get_section('tunnels')
        tunnels = {}
        for tunnel in section:
            tunnels[tunnel['name']] = tunnel
        if pk in tunnels:
            return SSHTunnel.new(tunnels[pk], 'deployfish')
        else:
            raise SSHTunnel.DoesNotExist(
                'Could not find an ssh tunnel config named "{}" indeployfish.yml:tunnels'.format(pk)
            )

    def list(self, service_name=None, port=None):
        # hint: (str["{service_name}"], int)
        config = get_config()
        section = config.get_section('tunnels')
        tunnels = [SSHTunnel.new(tunnel, 'deployfish') for tunnel in section]
        if service_name:
            tunnels = [tunnel for tunnel in tunnels if tunnel.data['service'] == service_name]
        elif port:
            tunnels = [tunnel for tunnel in tunnels if tunnel.data['port'] == port]
        return tunnels

    def delete(self, obj):
        raise self.ReadOnly('SSH Tunnel objects are read only.')

    def save(self, obj):
        raise self.ReadOnly('SSH Tunnel objects are read only.')


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

    @property
    def pk(self):
        return self.data['name']

    @property
    def name(self):
        return self.data['name']

    @property
    def local_port(self):
        return self.data['local_port']

    def secret(self, name):
        if 'secrets' not in self.cache:
            self.cache['secrets'] = {}
        if name not in self.cache['secrets']:
            if "." not in name:
                full_name = '{}{}'.format(self.service.secrets_prefix, name)
            else:
                full_name = name
            self.cache['secrets'][name] = Secret.objects.get(full_name)
        return self.cache['secrets'][name]

    def parse(self, key):
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
    def host(self):
        if 'host' not in self.cache:
            self.cache['host'] = self.parse('host')
        return self.cache['host']

    @property
    def host_port(self):
        if 'host_port' not in self.cache:
            self.cache['host_port'] = self.parse('port')
        return self.cache['host_port']

    @property
    def ssh_target(self):
        return self.service.ssh_target

    @property
    def ssh_targets(self):
        return self.service.ssh_targets

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
            self.cache['service'] = Service.objects.get('{}:{}'.format(data['cluster'], data['name']))
        return self.cache['service']

    @service.setter
    def service(self, value):
        self.cache['service'] = value

    @property
    def cluster(self):
        return self.service.cluster
