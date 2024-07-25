from io import IOBase
import os
import random
import signal
import subprocess
from typing import (
  Any,
  Callable,
  Dict,
  Literal,
  Optional,
  Sequence,
  Type,
  Tuple,
  TYPE_CHECKING,
  cast,
)

import click
import shellescape

from deployfish.types import SupportsCache, SupportsModel, SupportsService
from deployfish.config import get_config

from .aws import get_boto3_session
if TYPE_CHECKING:
    from .models import (  # noqa:F401
        Instance,
        InvokedTask,
        SSHTunnel,
    )


def build_sigint_handler(p: subprocess.Popen) -> Callable:
    """
    This builds a signal handler for catching SIGINT (Control-C) while we are
    exec'ed into a FARGATE container.  We want that signal to go to the remote
    process and not be turned into KeyboardInterrupt here in our python process.
    If we don't forward SIGINT, we kill our python process but leave the remote
    ECS Exec shell running.

    Use this like so:

    .. code-block:: python

        p = subprocess.Popen(cmd, shell=True)
        # Register our handler
        signal.signal(signal.SIGINT, build_sigint_handler(p))
        # Wait for our subprocess to die
        p.wait()
        # Restore the default behavior of SIGINT
        signal.signal(signal.SIGINT, signal.SIG_DFL)

    Args:
        p: the subprcess object running our interactive session

    Returns:
        A function suitable for registering with :py:func:`signal.signal`.
    """
    def sigint_handler(signum, frame):
        p.send_signal(signal.SIGINT)
    return sigint_handler


class AbstractSSHProvider:
    """
    Abstract class that provides the methods that ``SSHMixin`` will use to
    stablish tunnels, interactive ssh sessions, non-interactive commands over
    ssh and docker execs.

    Args:
        instance: the instance through which we will ssh

    Keyword Args:
        verbose: if ``True``, use verbose flags for the ssh command
    """

    def __init__(self, instance: "Instance", verbose: bool = False) -> None:
        assert instance is not None, \
            '{}.instance must not be None'.format(self.__class__.__name__)
        assert instance.__class__.__name__ == 'Instance', \
            '{}.instance must be an Instance object'.format(self.__class__.__name__)
        #: The instance through which we will ssh
        self.instance = instance
        #: If the caller specified ``verbose=True``, we send SSH the ``-vv`` flag.
        self.ssh_verbose_flag = '-vv' if verbose else ''

    def ssh(self, command: str = None) -> str:
        """
        Return a shell command suitable for establish an interactive ssh session.

        Args:
            command: run this instead of starting an interactive shell.

        Returns:
            A shell command suitable for establishing an interactive ssh session
            or running a command on the remote instance.
        """
        raise NotImplementedError

    def ssh_command(self, command: str) -> str:
        """
        Return a shell command suitable for running a command-line command via
        ssh on :py:attr:`instance`.

        .. note::

            Remove this in favor of just calling self.ssh(command) directly.

        Args:
            command: the command to run on the remote instance

        Returns:
            A shell command suitable for running a command-line command via ssh
        """
        return self.ssh(command)

    def docker_exec(self) -> str:
        """
        Return a shell command suitable for establishing a "docker exec" session
        into a container running on :py:attr:`instance`.

        Returns:
            A shell command suitable for establishing a "docker exec" session
        """
        # FIXME: the "head -1" here crudely handles the case where we have
        # multiple instances of the same container running on the same container
        # instance.  But this eliminates the possibility of execing into the
        # 2nd, 3rd, etc. containers
        return '/usr/bin/docker exec -it $(/usr/bin/docker ps --filter "name=ecs-{}-[0-9]+-{}" -q | head -1) bash'

    def tunnel(self, local_port: int, target_host: str, host_port: int) -> str:
        """
        Return a shell command suitable for establishing an ssh tunnel through
        :py:attr:`self.instance`.

        Args:
            local_port: let the port on our side of the tunnel be this
            target_host: the hostname/IP address of the host to connect to on
                the remote side of the tunnel
            host_port: the port on the remote host to which to connect the tunnel

        Returns:
            A shell command suitable for establishing an ssh tunnel
        """
        raise NotImplementedError

    def push(self, filename: str, run: bool = False) -> str:
        """
        Return a shell command suitable for uploading a file through an ssh
        tunnel to :py:attr:`self.instance`.

        Args:
            filename: the name of the local file to upload
            run: if ``True``, execute the uploaded file as a shell script

        Returns:
            The command to run to upload the file
        """
        raise NotImplementedError


class SSMSSHProvider(AbstractSSHProvider):
    """
    Implement our SSH commands via AWS Systems Manager SSH connections directly
    to :py:attr:`instance`.

    For SSM ssh to work for your non-default AWS profiles, add a stanza to your
    ``~/.ssh/config`` that looks like this::

        Host *.{the profile name}
            IdentitiesOnly yes
            User ec2-user
            Port 22
            ProxyCommand sh -c "/usr/local/bin/aws-gate ssh-proxy -p {the profile name} -r us-west-2 `echo %h | sed -Ee 's/\.([^.])+$//g'`"

    Where ``{the profile name}`` is the name of your non-default profile.
    """

    def ssh(self, command: str = None) -> str:
        """
        Return a shell command suitable for establishing an interactive ssh session.

        If ``command`` is provided, run that command on the remote instance
        instead of starting an interactive shell.

        If :py:attr:`ssh_verbose_flag` is set, add the ssh verbose flags to the
        command.

        Keyword Args:
            command: A command to run on the remote instance instead of opening an
                interactive session.

        Returns:
            _type_: _description_
        """
        # If the caller specified --verbose, have SSH print everything.
        # Otherwise, have SSH print nothing.
        flags = self.ssh_verbose_flag if self.ssh_verbose_flag else '-q'
        if not command:
            command = ''
        profile_name = get_boto3_session().profile_name
        ssh_target = self.instance.pk
        if profile_name:
            ssh_target = f'{self.instance.pk}.{profile_name}'
        return 'ssh -t {} ec2-user@{} {}'.format(flags, ssh_target, shellescape.quote(command))

    def tunnel(self, local_port: int, target_host: str, host_port: int) -> str:
        """
        Build a command that will tunnel through an SSM connection to an
        instance to get to another resource in the VPC.

        Args:
            local_port: the port on the local host to which to connect the tunnel
            target_host: The hostname/IP address of the target host to which to
                connect the tunnel
            host_port: The port on the target host to which to connect the tunnel

        Returns:
            A shell command suitable for establishing an ssh tunnel
        """
        profile_name = get_boto3_session().profile_name
        ssh_target = self.instance.pk
        if profile_name:
            ssh_target = f'{self.instance.pk}.{profile_name}'
        cmd = 'ssh {} -N -L {}:{}:{} {}'.format(
            self.ssh_verbose_flag,
            local_port,
            target_host,
            host_port,
            ssh_target
        )
        return cmd

    def push(self, filename: str, run: bool = False) -> str:
        """
        Return a shell command suitable for uploading a file through an ssh
        tunnel to :py:attr:`instance`.

        Args:
            filename: the name of the local file to upload
            run: if ``True``, execute the uploaded file as a shell script

        Returns:
            _type_: _description_
        """
        if run:
            return 'cat > {filename};bash {filename};rm {filename}'.format(filename=filename)
        return 'cat > {}'.format(filename)


class BastionSSHProvider(AbstractSSHProvider):
    """
    Find the public-facing bastion host in the VPC in which :py:attr:`instance`
    lives, and tunnel through that to get to our instance.
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
        # FIXME: the "head -1" here crudely handles the case where we have
        # multiple instances of the same container running on the same container
        # instance.  But this eliminates the possibility of execing into the
        # 2nd, 3rd, etc. containers
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
    DEFAULT_PROVIDER: str = 'ssm'

    class NoSSHTargetAvailable(Exception):
        pass

    @property
    def ssh_proxy_type(self) -> Literal["bastion", "ssm"]:
        """
        Return the type of SSH proxy to use for this object: bastion or ssm.

        Raises:
            ConfigProcessingFailed: if the config file is missing or misconfigured

        Returns:
            "bastion" or "ssm"
        """
        return get_config().ssh_provider_type

    @property
    def ssh_target(self) -> Optional["Instance"]:
        """
        Return an Instance that an be targeted by .ssh().
        """
        raise NotImplementedError

    @property
    def ssh_targets(self) -> Sequence["Instance"]:
        """
        Return all :py:class:`deployfish.core.models.ec2.Instance` objects
        associated with this class that can be targeted by
        :py:meth:`ssh_interactive` or :py:meth:`ssh_noninteractive`.
        """
        if self.ssh_target:
            return [self.ssh_target]
        return []

    @property
    def tunnel_target(self) -> Optional["Instance"]:
        """
        Return an Instance that an be targeted by :py:meth:`tunnel`

        For EC2 backed ECS Tasks, this will be the same as
        :py:meth:`ssh_target`.
        """
        return self.ssh_target

    @property
    def tunnel_targets(self) -> Sequence["Instance"]:
        """
        Return an list of Instances that an be targeted by :py:meth:`tunnel`.

        For EC2 backed ECS Tasks, this will be the same as
        :py:meth`ssh_targets`.
        """
        return self.ssh_targets

    def __is_or_has_file(self, data: Any) -> bool:
        """
        Return ``True`` if ``data`` is a file-like object, ``False`` otherwise.

        Args:
            data: the file-like object to check
        """
        if hasattr(data, 'file'):
            data = data.file
        return isinstance(data, IOBase)

    def ssh_interactive(self, ssh_target: "Instance" = None, verbose: bool = False) -> None:
        """
        Do an interactive SSH session to Instance.  This method will not exit
        until the user ends the ssh sesison.

        Args:
            ssh_target: the instance to which to ssh

        Keyword Args:
            verbose: If ``True``, use the verbose flags for ssh
        """
        if not ssh_target:
            ssh_target = self.ssh_target
        if ssh_target:
            # self.ssh_target can still be None
            provider = self.providers[self.ssh_proxy_type](ssh_target, verbose=verbose)
            subprocess.call(provider.ssh(), shell=True)
        else:
            raise self.NoSSHTargetAvailable(f'No ssh targets are available for {self}')

    def ssh_noninteractive(
        self,
        command: str,
        verbose: bool = False,
        output = None,
        input_data = None,
        ssh_target: "Instance" = None
    ) -> Tuple[bool, str]:
        """
        Run a command on ``ssh_target`` via ssh. This method will not exit until
        the command finishes.

        Args:
            command: the command to run on the remote host

        Keyword Args:
            verbose: If ``True``, use the verbose flags for ssh
            output: a filename or file descriptor to which to write the output.
            input_data: a filename, file descriptor, or string from which to
                read input.
            ssh_target: the instance to which to ssh

        Returns:
            A tuple of (success, output).  ``success`` is a boolean indicating
            whether the command succeeded.  ``output`` is the output of the
            command.
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
        provider: AbstractSSHProvider = self.providers[self.ssh_proxy_type](
            ssh_target,
            verbose=verbose
        )
        if not command.startswith('ssh'):
            # Wrap the command in an ssh command
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
            stdout_output, stderr_output = p.communicate(input_string)
            return p.returncode == 0, f'{stdout_output}\n{stderr_output}'

    def tunnel(
        self,
        tunnel: "SSHTunnel",
        verbose: bool = False,
        tunnel_target: "Instance" = None
    ) -> None:
        """
        Establish an SSH tunnel.  This will not exit until the tunnel is closed by the user.

        Args:
            tunnel: the tunnel config

        Keyword Args:
            verbose: If ``True``, use the verbose flags for ssh
            tunnel_target: If not None, use this host for our tunnel host
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
                    verbose=verbose,
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

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def docker_ssh_exec(
        self,
        ssh_target: "Instance" = None,
        container_name: str = None,
        verbose: bool = False
    ) -> None:
        """
        Exec into a container running on an EC2 backed ECS Service.

        If ``ssh_target`` is not provided, use ``self.ssh_target`` instead.  If
        ``container_name`` is not provided, use the name of the first container
        in the first running task.

        Keyword Args:
            ssh_target: the instance to which to ssh
            container_name: the name of the container to exec into
            verbose: if True, display verbose output from ssh
        """
        if self.running_tasks:
            if ssh_target is None:
                ssh_target = self.running_tasks[0].ssh_target
            if not container_name:
                # Arbitrarily exec into the first container in our object
                container_name = self.running_tasks[0].containers[0].name
        else:
            raise self.NoRunningTasks(
                f'{self.__class__.__name__}(pk={self.pk}) has no running tasks.'
            )
        ssh_target = cast("Instance", ssh_target)
        click.echo(
            f'Connecting to {click.style(ssh_target.name, fg="cyan")} and execing into container {click.style(container_name, fg="cyan")} ...'
        )
        provider = self.providers[self.ssh_proxy_type](ssh_target, verbose=verbose)
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
        Exec into a container using the ECS Exec capability of AWS Systems
        Manager.  This is what we use for FARGATE tasks.

        .. warning::

            In order for ECS Exec to work, you'll need to configure your
            cluster, task role and the system on which you run deployfish as
            described here:
            `<https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs-exec.html>`_.

        If ``task_arn`` is not provided, use the first task listed in the
        running tasks for the object.

        If ``container_name`` is not provided, use the name of the first
        container in the first running task.

        Keyword Args:
            task_arn: the ARN of the particular
                :py:class:`deployfish.core.models.ecs.InvokedTask` that we want to
                exec into
            container_name: the name of the container to exec into
        """
        if self.running_tasks:
            if task_arn is None:
                task_arn = self.running_tasks[0].arn
            if not container_name:
                # Arbitrarily exec into the first container in our object
                container_name = self.running_tasks[0].containers[0].name
        else:
            raise self.NoRunningTasks(f'{self.__class__.__name__}(pk={self.pk}) has no running tasks.')
        profile_name = get_boto3_session().profile_name
        if profile_name:
            cmd = f"aws --profile {profile_name} ecs execute-command"
        else:
            cmd = "aws ecs execute-command"
        cmd += f" --cluster {self.cluster.name} --task={task_arn} --container={container_name}"
        cmd += " --interactive --command \"/bin/sh\""
        p = subprocess.Popen(cmd, shell=True)
        # Catch SIGINT and pass it to our subprocess so we don't die, leaving
        # our ECS Exec session still running
        signal.signal(signal.SIGINT, build_sigint_handler(p))
        # Wait for our subprocess to die
        p.wait()
        # Restore the default behavior of SIGINT
        signal.signal(signal.SIGINT, signal.SIG_DFL)
