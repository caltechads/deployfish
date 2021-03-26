import random
import subprocess


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
        return '\'/usr/bin/docker exec -it `/usr/bin/docker ps --filter "name=ecs-{}*" -q` bash \''

    def tunnel(self):
        raise NotImplementedError

    def push(self):
        raise NotImplementedError


class SSMSSHProvider(AbstractSSHProvider):

    def ssh(self):
        return 'ssh -t {} ec2-user@{}'.format(self.ssh_verbose_flag, self.instance.id)

    def tunnel(self, local_port, host_port):
        cmd = 'ssh {} -N -L {}:{}:{} {}'.format(
            self.ssh_verbose_flag,
            local_port,
            self.instance.ip_address,
            host_port,
            self.instance.ip_address,
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
        return 'ssh {} -o StrictHostKeyChecking=no -A -t ec2-user@{} ssh {} -o StrictHostKeyChecking=no -A -t {}'.format(
            self.ssh_verbose_flag,
            self.instance.bastion.hostname,
            self.ssh_verbose_flag,
            self.instance.ip_address
        )

    def tunnel(self, local_port, host_port):
        interim_port = random.randrange(10000, 64000, 1)
        cmd = 'ssh {} -L {}:localhost:{} ec2-user@{} ssh -L {}:{}:{}  {}'.format(
            self.ssh_verbose_flag,
            local_port,
            interim_port,
            self.instance.bastion.hostname,
            interim_port,
            self.instance.ip_address,
            host_port
        )
        return cmd

    def push(self, filename, run=False):
        if run:
            return r'"cat \> {filename}\;bash {filename}\;rm {filename}"'.format(filename=filename)
        return r'"cat \> {}"'.format(filename)


class SSHMixin(object):

    providers = {
        'ssm': SSMSSHProvider,
        'bastion': BastionSSHProvider
    }

    class NoSSHTargetAvailable(Exception):
        pass

    def __init__(self, *args, **kwargs):
        self.provider_type = kwargs.pop('provider_type', 'bastion')
        super(SSHMixin, self).__init__(*args, **kwargs)

    @property
    def ssh_target(self):
        raise NotImplementedError

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

    def ssh_interactive(self, verbose=False):
        provider = self.providers(self.ssh_target, verbose=verbose)
        subprocess.call(provider.ssh(), shell=True)

    def ssh_command(self, command, verbose=False, output=False, input_data=None):
        stdout = output if self.__is_or_has_file(output) else subprocess.PIPE
        if input_data:
            if self.__is_or_has_file(input_data):
                stdin = input_data
                input_string = None
            else:
                stdin = subprocess.PIPE
                input_string = input_data
        else:
            stdin = None
        provider = self.providers(self.ssh_target, verbose=verbose)
        try:
            p = subprocess.Popen(
                provider.ssh_command(command),
                stdout=stdout,
                stdin=stdin,
                shell=True,
                universal_newlines=True
            )
            output, errors = p.communicate(input_string)
            return True, output
        except subprocess.CalledProcessError as err:
            return False, err.output

    def tunnel(self, local_port, host_port, verbose=False):
        provider = self.providers(self.ssh_target, verbose=verbose)
        subprocess.call(provider.tunnel(local_port, host_port), shell=True)


class DockerMixin(SSHMixin):

    class NoRunningTasks(Exception):
        pass

    @property
    def ssh_target(self):
        return self.container_instance.ec2_instance

    def __init__(self, *args, **kwargs):
        self.provider_type = kwargs.pop('provider_type', 'bastion')
        super(DockerMixin, self).__init__(*args, **kwargs)

    def docker_exec(self, verbose=True):
        provider = self.providers(self.ssh_target, verbose=verbose)
        self.ssh_command(provider.docker_exec(), verbose=verbose)
