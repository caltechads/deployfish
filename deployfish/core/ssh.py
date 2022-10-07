from io import IOBase
import os
import random
import subprocess
from typing import Dict, Type, Any, Tuple, TYPE_CHECKING, Optional, cast, Sequence

import shellescape

from deployfish.types import SupportsCache, SupportsModel, SupportsService
from deployfish.exceptions import ConfigProcessingFailed
from deployfish.config import get_config

if TYPE_CHECKING:
    from .models import (  # noqa:F401
        Instance,
        InvokedTask,
        SSHTunnel,
    )


class AbstractSSHProvider:
    """
    Abbstract class that provides the methods that ``SSHMixin`` will use to stablish tunnels, interactive
    ssh sessions, non-interactive commands over ssh and docker execs.
    """

    def __init__(self, instance: "Instance", verbose: bool = False) -> None:
        """
        Save the instance through which we will SSH, and whether we set the verbosity of our ssh commands.

        :param instance: The core.models.ec2.Instance through which we will ssh
        :param verbose: If True, use verbose flags for the ssh command
        """
        assert instance is not None, '{}.instance must not be None'.format(self.__class__.__name__)
        assert instance.__class__.__name__ == 'Instance', \
            '{}.instance must be an Instance object'.format(self.__class__.__name__)
        self.instance = instance
        # If the caller specified --verbose, we send SSH the `-vv` flag.
        self.ssh_verbose_flag = '-vv' if verbose else ''

    def ssh(self, command: str = None) -> str:
        """
        Return a shell command suitable for establish an interactive ssh session.

        :param command: run this instead of an interactive shell.
        """
        raise NotImplementedError

    def ssh_command(self, command: str) -> str:
        """
        Return a shell command suitable for running a command-line command via ssh on ``self.instance``.

        .. note::

            Remove this in favor of just calling self.ssh(command) directly.
        """
        return self.ssh(command)

    def docker_exec(self) -> str:
        """
        Return a shell command suitable for establishing a "docker exec" session into a container running on
        ``self.instance``.
        """
        # FIXME: the "head -1" here crudely handles the case where we have multiple instances of the same container
        # running on the same container instance.  But this eliminates the possibility of execing into the 2nd, 3rd,
        # etc. containers
        return "/usr/bin/docker exec -it $(/usr/bin/docker ps --filter 'name=ecs-{}-[0-9]+-{}' -q | head -1) bash"

    def tunnel(self, local_port: int, target_host: str, host_port: int) -> str:
        """
        Return a shell command suitable for establishing an ssh tunnel through ``self.instance``.

        :param local_port: let the port on our side of the tunnel be this
        :param target_host: the hostname/IP address of the host to connect to on the remote side of the tunnel
        :param host_port: the port on the remote host to which to connect the tunnel
        """
        raise NotImplementedError

    def push(self, filename: str, run: bool = False) -> str:
        """
        Return a shell command suitable for uploading a file through an ssh tunnel to ``self.instance``.

        :param filename: the local filename to upload.  The remote file will have the same filename.
        :param run: If True, execute the uploaded file as a shell script.
        """
        raise NotImplementedError


class SSMSSHProvider(AbstractSSHProvider):
    """
    Implement our SSH commands via AWS Systems Manager SSH connections directly to ``self.instance``.
    """

    def ssh(self, command: str = None) -> str:
        # If the caller specified --verbose, have SSH print everything. Otherwise, have SSH print nothing.
        flags = self.ssh_verbose_flag if self.ssh_verbose_flag else '-q'
        if not command:
            command = ''
        return 'ssh -t {} ec2-user@{} {}'.format(flags, self.instance.pk, shellescape.quote(command))

    def tunnel(self, local_port: int, target_host: str, host_port: int) -> str:
        cmd = 'ssh {} -N -L {}:{}:{} {}'.format(
            self.ssh_verbose_flag,
            local_port,
            target_host,
            host_port,
            self.instance.pk,
        )
        return cmd

    def push(self, filename: str, run: bool = False):
        if run:
            return '"cat > {filename};bash {filename};rm {filename}"'.format(filename=filename)
        return '"cat > {}"'.format(filename)


class BastionSSHProvider(AbstractSSHProvider):
    """
    Find the public-facing bastion host in the VPC in which ``self.instance`` lives, and tunnel through that to get to
    our instance.
    """

    def __init__(self, instance: "Instance", verbose: bool = False) -> None:
        super().__init__(instance, verbose=verbose)
        assert self.instance.bastion is not None, \
            '{}.instance has no bastion host'.format(self.__class__.__name__)

    def ssh(self, command: str = None) -> str:
        # If the caller specified --verbose, have SSH print everything. Otherwise, have SSH print nothing.
        flags = self.ssh_verbose_flag if self.ssh_verbose_flag else '-q'
        if not command:
            command = ''
        hop2 = "ssh {flags} -o StrictHostKeyChecking=no -A -t {instance} {command}".format(
            flags=flags,
            instance=self.instance.ip_address,
            command=shellescape.quote(command)
        )
        if not self.instance.bastion:
            raise ValueError('No bastion host found')
        cmd = "ssh {flags} -o StrictHostKeyChecking=no -A -t ec2-user@{bastion} {hop2}".format(
            flags=flags,
            hop2=shellescape.quote(hop2),
            bastion=self.instance.bastion.hostname,
        )
        return cmd

    def tunnel(self, local_port: int, target_host: str, host_port: int) -> str:
        if not self.instance.bastion:
            raise ValueError('No bastion host found')
        interim_port = random.randrange(10000, 64000, 1)
        cmd = ('ssh {flags} -L {local_port}:localhost:{interim_port} ec2-user@{bastion}'
               ' ssh -L {interim_port}:{target_host}:{host_port} {instance}').format(
            flags=self.ssh_verbose_flag,
            local_port=local_port,
            interim_port=interim_port,
            bastion=self.instance.bastion.hostname,
            target_host=target_host,
            host_port=host_port,
            instance=self.instance.ip_address,
        )
        return cmd

    def docker_exec(self) -> str:
        # FIXME: the "head -1" here crudely handles the case where we have multiple instances of the same container
        # running on the same container instance.  But this eliminates the possibility of execing into the 2nd, 3rd,
        # etc. containers
        return "/usr/bin/docker exec -it $(/usr/bin/docker ps --filter 'name=ecs-{}-[0-9]+-{}' -q | head -1) bash"

    def push(self, filename: str, run: bool = False) -> str:
        if run:
            return 'cat > {filename};bash {filename};rm {filename}'.format(filename=filename)
        return 'cat > {}'.format(filename)


class SSHMixin(SupportsCache, SupportsModel):

    providers: Dict[str, Type[AbstractSSHProvider]] = {
        'ssm': SSMSSHProvider,
        'bastion': BastionSSHProvider
    }
    DEFAULT_PROVIDER: str = 'bastion'

    class NoSSHTargetAvailable(Exception):
        pass

    @property
    def ssh_proxy_type(self) -> str:
        proxy: str = self.DEFAULT_PROVIDER
        try:
            ssh_config = get_config().get_global_config('ssh')
        except ConfigProcessingFailed:
            pass
        else:
            if ssh_config and 'proxy' in ssh_config:
                proxy = ssh_config['proxy']
        return proxy

    @property
    def ssh_target(self) -> Optional["Instance"]:
        """
        Return an Instance that an be targeted by .ssh().
        """
        raise NotImplementedError

    @property
    def ssh_targets(self) -> Sequence["Instance"]:
        """
        Return all Instances associated with this class that can be targeted by .ssh().
        """
        if self.ssh_target:
            return [self.ssh_target]
        return []

    @property
    def tunnel_target(self) -> Optional["Instance"]:
        """
        Return an Instance that an be targeted by .tunnel().

        For EC2 backed ECS Tasks, this will be the same as ``self.ssh_target``.
        """
        return self.ssh_target

    @property
    def tunnel_targets(self) -> Sequence["Instance"]:
        """
        Return an list of Instances that an be targeted by .tunnel().

        For EC2 backed ECS Tasks, this will be the same as ``self.ssh_targets``.
        """
        return self.ssh_targets

    def __is_or_has_file(self, data: Any) -> bool:
        """
        Return True if `data` is a file-like object, False otherwise.
        """
        if hasattr(data, 'file'):
            data = data.file
        return isinstance(data, IOBase)

    def ssh_interactive(self, ssh_target: "Instance" = None, verbose: bool = False) -> None:
        """
        Do an interactive SSH session to Instance.  This method will not exit until the user ends the ssh sesison.

        :param ssh_target: the instance to which to ssh
        :param verbose: If True, use the verbose flags for ssh
        """
        if ssh_target is None:
            ssh_target = self.ssh_target
        if ssh_target:
            provider = self.providers[self.ssh_proxy_type](ssh_target, verbose=verbose)
            subprocess.call(provider.ssh(), shell=True)
        else:
            raise self.NoSSHTargetAvailable(f'No ssh targets are available for {self}')

    def ssh_noninteractive(
        self,
        command: str,
        verbose: bool = False,
        output=None,
        input_data=None,
        ssh_target: "Instance" = None
    ) -> Tuple[bool, str]:
        """
        Run a command on ``instance`` via ssh. This method will not exit until the command finishes.

        :param ssh_target: the instance to which to ssh
        :param verbose: If True, use the verbose flags for ssh
        """
        if ssh_target is None:
            ssh_target = self.ssh_target
        if not ssh_target:
            raise self.NoSSHTargetAvailable(f'No ssh targets are available for {self}')
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
        provider: AbstractSSHProvider = self.providers[self.ssh_proxy_type](ssh_target, verbose=verbose)
        if not command.startswith('ssh'):
            command = provider.ssh_command(command)
        try:
            p = subprocess.Popen(
                command,
                stdout=stdout,
                stdin=stdin,
                stderr=stdout,
                shell=True,
                universal_newlines=True
            )
        except subprocess.CalledProcessError as err:
            output = ''
            if err.output:
                output += err.output
            if err.stderr:
                output += err.stderr
            return False, output
        else:
            stdout_output, _ = p.communicate(input_string)
            return p.returncode == 0, stdout_output

    def tunnel(self, tunnel: "SSHTunnel", verbose: bool = False, tunnel_target: "Instance" = None) -> None:
        """
        Establish an SSH tunnel.  This will not exit until the tunnel is closed by the user.

        :param tunnel: the tunnel config
        :param verbose: if True, display verbose output from ssh
        :param tunnel_target: if not None, use this host for our tunnel host
        """
        if not tunnel_target:
            tunnel_target = self.tunnel_target
        if tunnel_target:
            provider = self.providers[self.ssh_proxy_type](tunnel_target, verbose=verbose)
            cmd = provider.tunnel(
                tunnel.local_port,
                tunnel.host,
                tunnel.host_port
            )
            subprocess.call(cmd, shell=True)
        else:
            raise self.NoSSHTargetAvailable(f'No tunnel targets are available for {self}')

    def push_file(
        self,
        input_filename: str,
        verbose: bool = False,
        ssh_target: "Instance" = None
    ) -> Tuple[bool, str, str]:
        """
        Upload a file via ssh to a remote instance.

        If ``ssh_target`` is not provided, use ``self.ssh_target`` instead.

        :param input_filename: the filename of the file on the local system
        :param verbose: if True, display verbose output from ssh
        :param ssh_target: If provided, the Instance object to which to ssh
        """
        if ssh_target is None:
            ssh_target = self.ssh_target
        if ssh_target:
            provider = self.providers[self.ssh_proxy_type](ssh_target, verbose=verbose)
            _, filename = os.path.split(input_filename)
            remote_filename = '/tmp/' + filename
            command = provider.push(remote_filename)
            with open(input_filename, encoding='utf-8') as ifd:
                success, output = self.ssh_noninteractive(
                    command,
                    input_data=ifd,
                    ssh_target=ssh_target
                )
            return success, output, remote_filename
        raise self.NoSSHTargetAvailable(f'No ssh targets are available for {self}')


class DockerMixin(SSHMixin, SupportsService):

    class NoRunningTasks(Exception):
        pass

    @property
    def running_tasks(self) -> Sequence["InvokedTask"]:
        """
        This should return a list of InvokedTask objects.
        """
        raise NotImplementedError

    def __init__(self, *args, provider_type: str = 'bastion', **kwargs) -> None:
        self.provider_type: str = provider_type
        super().__init__(*args, **kwargs)

    def docker_ssh_exec(
        self,
        ssh_target: "Instance" = None,
        container_name: str = None,
        verbose: bool = False
    ) -> None:
        """
        Exec into a container running on an EC2 backed ECS Service.

        If ``ssh_target`` is not provided, use ``self.ssh_target`` instead.
        If ``container_name`` is not provided, use the name of the first container in the first running task.

        :param ssh_target: If provided, the Instance object to which to ssh
        :param container_name: the name of the container to exec into
        :param verbose: if True, display verbose output from ssh
        """
        if self.running_tasks:
            if ssh_target is None:
                ssh_target = self.running_tasks[0].ssh_target
            if not container_name:
                # Arbitrarily exec into the first container in our object
                container_name = self.running_tasks[0].containers[0].name
        else:
            raise self.NoRunningTasks(f'{self.__class__.__name__}(pk={self.pk}) has no running tasks.')
        provider = self.providers[self.ssh_proxy_type](cast("Instance", ssh_target), verbose=verbose)
        cmd = provider.docker_exec().format(
            self.task_definition.data['family'],
            cast(str, container_name).replace('_', '')
        )
        cmd = provider.ssh_command(cmd)
        subprocess.call(cmd, shell=True)

    def docker_ecs_exec(
        self,
        task_arn: str = None,
        container_name: str = None
    ) -> None:
        """
        Exec into a container using the ECS Exec capability of AWS Systems Manager.  This is what we use for FARGATE
        tasks.

        .. warning::
            In order for ECS Exec to work, you'll need to configure your cluster, task role and the system on which you
            run deployfish as described here:
            `<https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs-exec.html>`_.

        If ``ssh_target`` is not provided, use ``self.ssh_target`` instead.
        If ``container_name`` is not provided, use the name of the first container in the first running task.

        :param ssh_target: If provided, the Instance object to which to ssh
        :param container_name: the name of the container to exec into
        """
        if self.running_tasks:
            if task_arn is None:
                task_arn = self.running_tasks[0].arn
            if not container_name:
                # Arbitrarily exec into the first container in our object
                container_name = self.running_tasks[0].containers[0].name
        else:
            raise self.NoRunningTasks(f'{self.__class__.__name__}(pk={self.pk}) has no running tasks.')
        cmd = "aws ecs execute-command"
        cmd += f" --cluster {self.cluster.name} --task={task_arn} --container={container_name}"
        cmd += " --interactive --command \"/bin/sh\""
        subprocess.call(cmd, shell=True)
