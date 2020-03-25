import random
import subprocess


class SSMProvider():

    def __init__(self, service):
        self.service = service

    def ok_to_run(self):
        if self.service.host_instance:
            return True
        return False

    def get_ssh_command(self, verbose_flag):
        cmd = 'ssh -t {} ec2-user@{}'.format(verbose_flag, self.service.host_instance)
        return cmd

    def get_docker_exec_sub_command(self):
        cmd = '\'/usr/bin/docker exec -it `/usr/bin/docker ps --filter "name=ecs-{}*" -q` bash \''
        return cmd

    def get_tunnel_command(self, host, local_port, host_port, ecs_host):
        cmd = 'ssh -N -L {}:{}:{} {}'.format(local_port, host, host_port, ecs_host)
        return cmd


class BastionProvider():

    def __init__(self, service):
        self.service = service

    def ok_to_run(self):
        if self.service.host_ip and self.service.bastion:
            return True
        return False

    def get_ssh_command(self, verbose_flag):
        cmd = 'ssh {} -o StrictHostKeyChecking=no -A -t ec2-user@{} ssh {} -o StrictHostKeyChecking=no -A -t {}'.format(verbose_flag, self.service.bastion, verbose_flag, self.service.host_ip)
        return cmd

    def get_docker_exec_sub_command(self):
        cmd = "\"/usr/bin/docker exec -it '\$(/usr/bin/docker ps --filter \"name=ecs-{}*\" -q)' bash\""
        return cmd

    def get_tunnel_command(self, host, local_port, host_port, ecs_host):
        interim_port = random.randrange(10000, 64000, 1)
        host_ip, bastion = self.service._get_host_bastion(ecs_host)
        cmd = 'ssh -L {}:localhost:{} ec2-user@{} ssh -L {}:{}:{}  {}'.format(local_port, interim_port, bastion, interim_port, host, host_port, host_ip)
        return cmd


class SSH():

    def __init__(self, service, ssm=False):
        self.service = service
        if ssm:
            self.provider = SSMProvider(service)
        else:
            self.provider = BastionProvider(service)

    def __is_or_has_file(self, data):
        '''
        Figure out if we have been given a file-like object as one of the inputs to the function that called this.
        Is a bit clunky because 'file' doesn't exist as a bare-word type check in Python 3 and built in file objects
        are not instances of io.<anything> in Python 2

        https://stackoverflow.com/questions/1661262/check-if-object-is-file-like-in-python
        Returns:
            Boolean - True if we have a file-like object
        '''
        if (hasattr(data, 'file')):
            data = data.file

        try:
            return isinstance(data, file)
        except NameError:
            from io import IOBase
            return isinstance(data, IOBase)

    def _run_command_with_io(self, cmd, output_file=None, input_data=None):
        success = True

        if output_file:
            stdout = output_file
        else:
            stdout = subprocess.PIPE

        if input_data:
            if self.__is_or_has_file(input_data):
                stdin = input_data
                input_string = None
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
            output = "{}\n{}".format(err.cmd, err.output)
            output = err.output

        return success, output

    def ssh(self, command=None, is_running=False, with_output=False, input_data=None, verbose=False):
        """
        :param is_running: only complete the ssh if a task from our service is
                           actually running in the cluster
        :type is_running: boolean
        """
        self.service._search_hosts()

        if is_running and not self.service.is_running:
            return

        if self.provider.ok_to_run():
            if verbose:
                verbose_flag = "-vv"
            else:
                verbose_flag = "-q"
            cmd = self.provider.get_ssh_command(verbose_flag)
            if command:
                cmd = "{} {}".format(cmd, command)
            print(cmd)

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
        # command = '\'/usr/bin/docker exec -it `/usr/bin/docker ps --filter "name=ecs-{}*" -q` bash \''
        command = self.provider.get_docker_exec_sub_command()
        print(command)
        command = command.format(self.service.family)
        self.ssh(command, is_running=True, verbose=verbose)

    def tunnel(self, host, local_port, host_port):
        """
        Open tunnel to remote system.
        :param host:
        :param local_port:
        :param host_port:
        :return:
        """
        hosts = self.service._get_cluster_hosts()
        ecs_host = hosts[list(hosts.keys())[0]]
        cmd = self.provider.get_tunnel_command(host, local_port, host_port, ecs_host)
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
        ssh = SSH(self.service, self.proxy=='ssm')
        return ssh
