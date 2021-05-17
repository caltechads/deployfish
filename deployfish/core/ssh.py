import os
import random
import subprocess

from deployfish.exceptions import ConfigProcessingFailed
from deployfish.config import get_config


class AbstractSSHProvider(object):

    def __init__(self, instance, verbose=False):
        assert instance is not None, '{}.instance must not be None'.format(self.__class__.__name__)
        assert instance.__class__.__name__ == 'Instance', \
            '{}.instance must be an Instance object'.format(self.__class__.__name__)
        self.instance = instance
        self.verbose = verbose
        self.ssh_verbose_flag = '-vv' if self.verbose else ''

    def ssh(self):
        raise NotImplementedError

    def ssh_command(self, command):
        return '{} {}'.format(self.ssh(), command)

    def docker_exec(self):
        # FIXME: the "head -1" here crudely handles the case where we have multiple instances of the same container
        # running on the same container instance.  But this eliminates the possibility of execing into the 2nd, 3rd,
        # etc. containers
        return '\'/usr/bin/docker exec -it "`/usr/bin/docker ps --filter \"name=ecs-{}-[0-9]+-{}\" -q | head -1`" bash \''

    def tunnel(self):
        raise NotImplementedError

    def push(self):
        raise NotImplementedError


class SSMSSHProvider(AbstractSSHProvider):

    def ssh(self):
        return 'ssh -t {} ec2-user@{}'.format(self.ssh_verbose_flag, self.instance.pk)

    def tunnel(self, local_port, target_host, host_port):
        cmd = 'ssh {} -N -L {}:{}:{} {}'.format(
            self.ssh_verbose_flag,
            local_port,
            target_host,
            host_port,
            self.instance.pk,
        )
        return cmd

    def push(self, filename, run=False):
        if run:
            return '"cat > {filename};bash {filename};rm {filename}"'.format(filename=filename)
        return '"cat > {}"'.format(filename)


class BastionSSHProvider(AbstractSSHProvider):

    def __init__(self, instance, verbose=False):
        super(BastionSSHProvider, self).__init__(instance, verbose=verbose)
        assert self.instance.bastion is not None, \
            '{}.instance has no bastion host'.format(self.__class__.__name__)

    def ssh(self):
        cmd = 'ssh {flags} -o StrictHostKeyChecking=no -A -t ec2-user@{bastion} ssh {flags} -o StrictHostKeyChecking=no -A -t {instance}'.format(   # noqa:E501
            flags=self.ssh_verbose_flag,
            bastion=self.instance.bastion.hostname,
            instance=self.instance.ip_address
        )
        return cmd

    def tunnel(self, local_port, target_host, host_port):
        interim_port = random.randrange(10000, 64000, 1)
        cmd = 'ssh {flags} -L {local_port}:localhost:{interim_port} ec2-user@{bastion} ssh -L {interim_port}:{target_host}:{host_port} {instance}'.format(  # noqa:E501
            flags=self.ssh_verbose_flag,
            local_port=local_port,
            interim_port=interim_port,
            bastion=self.instance.bastion.hostname,
            target_host=target_host,
            host_port=host_port,
            instance=self.instance.ip_address,
        )
        return cmd

    def docker_exec(self):
        # FIXME: the "head -1" here crudely handles the case where we have multiple instances of the same container
        # running on the same container instance.  But this eliminates the possibility of execing into the 2nd, 3rd,
        # etc. containers
        return "\"/usr/bin/docker exec -it '\$(/usr/bin/docker ps --filter \"name=ecs-{}-[0-9]+-{}\" -q | head -1)' bash\""

    def push(self, filename, run=False):
        if run:
            return r'"cat \> {filename}\;bash {filename}\;rm {filename}"'.format(filename=filename)
        return r'"cat \> {}"'.format(filename)


class SSHMixin(object):

    providers = {
        'ssm': SSMSSHProvider,
        'bastion': BastionSSHProvider
    }

    DEFAULT_PROVIDER = 'bastion'

    class NoSSHTargetAvailable(Exception):
        pass

    def __init__(self, *args, **kwargs):
        proxy = self.DEFAULT_PROVIDER
        if not hasattr(self, 'ssh_proxy_type'):
            known_proxy_types = list(self.providers.keys())
            if 'ssh_proxy' in kwargs:
                proxy = kwargs['proxy']
            else:
                try:
                    ssh_config = get_config().get_global_config('ssh')
                except ConfigProcessingFailed:
                    pass
                else:
                    if ssh_config and 'proxy' in ssh_config:
                        proxy = ssh_config['proxy']
            self.ssh_proxy_type = proxy
        assert self.ssh_proxy_type in known_proxy_types, \
            '"{}" is not a known SSH proxy type. Available types: {}'.format(proxy, ', '.join(known_proxy_types))
        super(SSHMixin, self).__init__(*args, **kwargs)

    @property
    def ssh_target(self):
        """
        Return one object associated with this class that an be targeted by .ssh().
        """
        raise NotImplementedError

    @property
    def ssh_targets(self):
        """
        Return all objects associated with this class that an be targeted by .ssh().
        """
        return [self.ssh_target]

    def __is_or_has_file(self, data):
        """
        Return True if `data` is a file-like object, False otherwise.

        ..note ::
            This is a bit clunky because 'file' doesn't exist as a bare-word type check in Python 3 and built in file
            objects are not instances of io.<anything> in Python 2.

            https://stackoverflow.com/questions/1661262/check-if-object-is-file-like-in-python

        :rtype: bool
        """
        if hasattr(data, 'file'):
            data = data.file
        try:
            # This is an error in Python 3, but we catch that error and do the py3 equivalent.
            # noinspection PyUnresolvedReferences
            return isinstance(data, file)
        except NameError:
            from io import IOBase
            return isinstance(data, IOBase)

    def ssh_interactive(self, ssh_target=None, verbose=False):
        if ssh_target is None:
            ssh_target = self.ssh_target
        provider = self.providers[self.ssh_proxy_type](self.ssh_target, verbose=verbose)
        subprocess.call(provider.ssh(), shell=True)

    def ssh_noninteractive(self, command, verbose=False, output=None, input_data=None, ssh_target=None):
        if ssh_target is None:
            ssh_target = self.ssh_target
        stdout = output if self.__is_or_has_file(output) else subprocess.PIPE
        input_string = None
        if input_data:
            if self.__is_or_has_file(input_data):
                stdin = input_data
            else:
                stdin = subprocess.PIPE
                input_string = input_data
        else:
            stdin = None
        provider = self.providers[self.ssh_proxy_type](ssh_target, verbose=verbose)
        if not command.startswith('ssh'):
            command = provider.ssh_command(command)
        try:
            p = subprocess.Popen(
                provider.ssh_command(command),
                stdout=stdout,
                stdin=stdin,
                shell=True,
                universal_newlines=True
            )
            stdout_output, errors = p.communicate(input_string)
            return True, stdout_output
        except subprocess.CalledProcessError as err:
            return False, err.output

    def tunnel(self, tunnel, verbose=False):
        """
        :param tunnel deployfish.core.models.SSHTunnel: the tunnel config
        :param verbose bool: if True, display verbose output from ssh
        """
        provider = self.providers[self.ssh_proxy_type](self.ssh_target, verbose=verbose)
        cmd = provider.tunnel(
            tunnel.local_port,
            tunnel.host,
            tunnel.host_port
        )
        subprocess.call(cmd, shell=True)

    def push_file(self, input_filename, verbose=False):
        provider = self.providers[self.ssh_proxy_type](self.ssh_target, verbose=verbose)
        path, filename = os.path.split(input_filename)
        remote_filename = '/tmp/' + filename
        command = provider.push(remote_filename)
        success, output = self.ssh_noninteractive(
            command,
            input_data=open(input_filename)
        )
        return success, output, remote_filename


class DockerMixin(SSHMixin):

    class NoRunningTasks(Exception):
        pass

    @property
    def container_names(self):
        raise NotImplementedError

    @property
    def container_name(self):
        return self.container_names[0]

    def __init__(self, *args, **kwargs):
        self.provider_type = kwargs.pop('provider_type', 'bastion')
        super(DockerMixin, self).__init__(*args, **kwargs)

    def docker_exec(self, ssh_target=None, container_name=None, verbose=False):
        if ssh_target is None:
            ssh_target = self.ssh_target
        if not container_name:
            container_name = self.container_names[0]
        provider = self.providers[self.ssh_proxy_type](self.ssh_target, verbose=verbose)
        cmd = provider.docker_exec().format(self.task_definition.data['family'], container_name)
        cmd = provider.ssh_command(cmd)
        subprocess.call(cmd, shell=True)
