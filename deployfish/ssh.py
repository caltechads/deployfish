import os
import random
import string
import subprocess
from tempfile import NamedTemporaryFile


class SSMProvider():

    def __init__(self, service):
        self.service = service
        self.host_instance = self.service.host_instance

    def ok_to_run(self):
        if self.service.host_instance:
            return True
        return False

    def get_ssh_command(self, verbose_flag, instance=None):
        if instance:
            host_instance = instance.id
        else:
            host_instance = self.host_instance
        cmd = 'ssh -t {} ec2-user@{}'.format(verbose_flag, host_instance)
        return cmd

    def get_docker_exec_sub_command(self):
        cmd = '\'/usr/bin/docker exec -it `/usr/bin/docker ps --filter "name=ecs-{}*" -q` bash \''
        return cmd

    def get_tunnel_command(self, host, local_port, host_port, ecs_host, verbose=False):
        if verbose:
            verbose_flag = '-vv'
        else:
            verbose_flag = ''
        cmd = 'ssh {} -N -L {}:{}:{} {}'.format(verbose_flag, local_port, host, host_port, ecs_host)
        return cmd

    def push_command(self, name, run=False):
        if run:
            return '"cat > {};bash {};rm {}"'.format(name, name, name)
        return '"cat > {}"'.format(name)


class BastionProvider():

    def __init__(self, service):
        self.service = service

    def ok_to_run(self):
        if self.service.host_ip and self.service.bastion:
            return True
        return False

    def get_ssh_command(self, verbose_flag, instance=None):
        if instance:
            ssh_host_ip = instance.ip
        else:
            ssh_host_ip = self.service.host_ip
        cmd = 'ssh {} -o StrictHostKeyChecking=no -A -t ec2-user@{} ssh {} -o StrictHostKeyChecking=no -A -t {}'.format(
            verbose_flag,
            self.service.bastion,
            verbose_flag,
            ssh_host_ip
        )
        return cmd

    def get_docker_exec_sub_command(self):
        cmd = "\"/usr/bin/docker exec -it '\$(/usr/bin/docker ps --filter \"name=ecs-{}*\" -q)' bash\""
        return cmd

    def get_tunnel_command(self, host, local_port, host_port, ecs_host, verbose=False):
        if verbose:
            verbose_flag = '-vv'
        else:
            verbose_flag = ''
        interim_port = random.randrange(10000, 64000, 1)
        host_ip, bastion = self.service._get_host_bastion(ecs_host)
        cmd = 'ssh {} -L {}:localhost:{} ec2-user@{} ssh -L {}:{}:{}  {}'.format(
            verbose_flag,
            local_port,
            interim_port,
            bastion,
            interim_port,
            host,
            host_port,
            host_ip
        )
        return cmd

    def push_command(self, name, run=False):
        if run:
            return '"cat \> {}\;bash {}\;rm {}"'.format(name, name, name)
        return '"cat \> {}"'.format(name)


class SSH():

    def __init__(self, service, ssm=False):
        self.service = service
        self.service._search_hosts()

        if ssm:
            self.provider = SSMProvider(service)
        else:
            self.provider = BastionProvider(service)

    def __is_or_has_file(self, data):
        """
        Figure out if we have been given a file-like object as one of the inputs to the function that called this.
        Is a bit clunky because 'file' doesn't exist as a bare-word type check in Python 3 and built in file objects
        are not instances of io.<anything> in Python 2

        https://stackoverflow.com/questions/1661262/check-if-object-is-file-like-in-python
        Returns:
            Boolean - True if we have a file-like object
        """
        if (hasattr(data, 'file')):
            data = data.file

        try:
            # This is an error in Python 3, but we catch that error and do the py3 equivalent.
            # noinspection PyUnresolvedReferences
            return isinstance(data, file)
        except NameError:
            from io import IOBase
            return isinstance(data, IOBase)

    def push_remote_text_file(self, input_data=None, run=False, file_output=False, instance=None):
        """
        Push a text file to the current remote ECS cluster instance and optionally run it.

        :param input_data: Input data to send. Either string or file.
        :param run: Boolean that indicates if the text file should be run.
        :param file_output: Boolean that indicates if the output should be saved.
        :param instance
        :return: tuple - success, output
        """
        if self.__is_or_has_file(input_data):
            path, name = os.path.split(input_data.name)
        else:
            name = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))

        cmd = self.provider.push_command(name, run)

        with_output = True
        if file_output:
            with_output = NamedTemporaryFile(delete=False)
            output_filename = with_output.name

        success, output = self.ssh(command=cmd, with_output=with_output, input_data=input_data, instance=instance)
        if file_output:
            # output_filename will always be bound, because we don't run this code until we bound it earlier.
            # noinspection PyUnboundLocalVariable
            output = output_filename
        return success, output

    def run_remote_script(self, lines, file_output=False, instance=None):
        """
        Run a script on the current remote ECS cluster instance.

        :param lines: list of lines of the script.
        :param file_output: Boolean that indicates if the output should be saved.
        :param instance
        :return: tuple - success, output
        """
        data = '\n'.join(lines)
        return self.push_remote_text_file(input_data=data, run=True, file_output=file_output, instance=instance)

    def _run_command_with_io(self, cmd, output_file=None, input_data=None):
        success = True

        if output_file:
            stdout = output_file
        else:
            stdout = subprocess.PIPE

        input_string = None
        if input_data:
            if self.__is_or_has_file(input_data):
                stdin = input_data
            else:
                stdin = subprocess.PIPE
                input_string = input_data
        else:
            stdin = None

        try:
            p = subprocess.Popen(cmd, stdout=stdout, stdin=stdin, shell=True, universal_newlines=True)
            output, errors = p.communicate(input_string)
        except subprocess.CalledProcessError as err:
            success = False
            # output = "{}\n{}".format(err.cmd, err.output)
            output = err.output

        return success, output

    def cluster_run(self, cmd):
        """
        Run a command on each of the ECS cluster machines.

        :param cmd: Linux command to run.

        :return: list of tuples
        """
        instances = self.service.get_instances()
        responses = []
        for instance in instances:
            success, output = self.run_remote_script(cmd, instance=instance)
            responses.append((success, output))
        return responses

    def ssh(self, command=None, is_running=False, with_output=False, input_data=None, verbose=False, instance=None):
        """
        :param is_running: only complete the ssh if a task from our service is
                           actually running in the cluster
        :type is_running: boolean
        """

        if is_running and not self.service.is_running:
            return

        if self.provider.ok_to_run():
            if verbose:
                verbose_flag = "-vv"
            else:
                verbose_flag = "-q"
            cmd = self.provider.get_ssh_command(verbose_flag, instance)
            if command:
                cmd = "{} {}".format(cmd, command)

            if with_output:
                if self.__is_or_has_file(with_output):
                    output_file = with_output
                else:
                    output_file = None
                return self._run_command_with_io(cmd, output_file=output_file, input_data=input_data)

            subprocess.call(cmd, shell=True)

    def docker_exec(self, verbose=False):
        """
        Exec into a running Docker container.
        """
        command = self.provider.get_docker_exec_sub_command()
        command = command.format(self.service.family)
        self.ssh(command, is_running=True, verbose=verbose)

    def tunnel(self, host, local_port, host_port, verbose=False):
        """
        Open tunnel to remote system.

        :param host:
        :param local_port:
        :param host_port:
        :param verbose:
        """
        hosts = self.service._get_cluster_hosts()
        ecs_host = hosts[list(hosts.keys())[0]]
        cmd = self.provider.get_tunnel_command(
            host,
            local_port,
            host_port,
            ecs_host,
            verbose=verbose
        )
        subprocess.call(cmd, shell=True)


class SSHConfig():

    def __init__(self, service, config):
        self.service = service
        self.proxy = 'bastion'
        ssh_yml = config.get_global_config('ssh')
        if ssh_yml:
            if 'proxy' in ssh_yml:
                self.proxy = ssh_yml['proxy']
        if 'ssh' in service.yml:
            if 'proxy' in service.yml['ssh']:
                self.proxy = service.yml['ssh']['proxy']

    def get_ssh(self):
        ssh = SSH(self.service, self.proxy == 'ssm')
        return ssh
