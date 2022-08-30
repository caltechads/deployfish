from itertools import cycle
from typing import Optional, List, Sequence, Tuple, Type, cast

from cement import ex, shell, App
import click
from tabulate import tabulate

from deployfish.core.loaders import ObjectLoader
from deployfish.core.models import Model, Instance
from deployfish.ext.ext_df_argparse import DeployfishArgparseController as Controller
from deployfish.types import SupportsSSHModel, SupportsService

from .utils import handle_model_exceptions

def get_ssh_target(app: App, obj: SupportsSSHModel, choose: bool = False) -> Instance:
    """
    Return an ``Instance`` object to which the user can ssh.

    If ``choose`` is ``False``, return the first `Instance`` of the
    available ssh targets for ``obj``.

    If ``choose`` is ``True``, prompt the user to choose one of the
    available ssh targets for this object.

    Args:
        obj: an instance of ``self.model``

    Keyword Arguments:
        choose: if ``True``, prompt the user to choose one of the available instances

    Raises:
        Instance.DoesNotExist: if there are no available ssh targets

    Returns:
        An Instance object.
    """
    assert hasattr(obj, 'ssh_targets'), \
        f'{obj.__class__.__name__} objects do not have the .ssh_targets attribute'
    target = None
    if choose:
        if obj.ssh_targets:
            rows = []
            click.secho('\nAvailable ssh targets:', fg='green')
            click.secho('----------------------\n', fg='green')
            for i, entry in enumerate(obj.ssh_targets):
                rows.append([
                    i + 1,
                    click.style(entry.name, fg='cyan'),
                    entry.pk,
                    entry.ip_address
                ])
            app.print(tabulate(rows, headers=['#', 'Name', 'Instance Id', 'IP']))
            p = shell.Prompt("\nEnter the number of the instance you want: ", default=1)
            choice = p.prompt()
            target = obj.ssh_targets[int(choice) - 1]
    else:
        target = obj.ssh_target
    if not target:
        raise Instance.DoesNotExist(
            '{}(pk="{}") has no ssh targets available'.format(obj.__class__.__name__, obj.pk)
        )
    return target


class ObjectSSHController(Controller):

    class Meta:
        label = 'ssh-base'

    model: Type[Model] = Model
    loader: Type[ObjectLoader] = ObjectLoader

    COLORS: List[str] = [
        'green',
        'yellow',
        'cyan',
        'magenta',
        'white',
        'bright_green',
        'bright_yellow',
        'bright_cyan',
        'bright_magenta',
        'bright_white'
    ]

    @ex(
        help="SSH into a container machine running one of the tasks for this object.",
        arguments=[
            (['pk'], { 'help' : 'The primary key for the object in AWS'}),
            (
                ["--verbose"],
                {
                    'help': 'Show all SSH output',
                    'default': False,
                    'action': 'store_true',
                    'dest': 'verbose'
                }
            ),
            (
                ["--choose"],
                {
                    'help': 'Choose from all available targets for ssh, instead of having one chosen automatically.',
                    'default': False,
                    'action': 'store_true',
                    'dest': 'choose'
                }
            )
        ]
    )
    @handle_model_exceptions
    def ssh(self):
        """
        SSH to a container machine running one of the tasks for an existing Service or Task in AWS.

        NOTE: this is only available if your Service or Task is of launch type EC2.  You cannot ssh
        to the container machine of a FARGATE Service or task.
        """
        loader = self.loader(self)
        obj = loader.get_object_from_aws(self.app.pargs.pk)
        assert hasattr(obj, 'ssh_target'), f'Objects of type {obj.__class__.__name__} do not support SSH actions'
        target = get_ssh_target(self.app, obj, choose=self.app.pargs.choose)
        target.ssh_interactive(verbose=self.app.pargs.verbose)

    @ex(
        help="Run a shell command on one or all instances related to an object.",
        arguments=[
            (['pk'], { 'help' : 'The primary key for the object in AWS'}),
            (['command'], {
                'help' : 'The primary key for the object in AWS',
                'nargs': '+'
            }),
            (
                ["--verbose"],
                {
                    'help': 'Show all SSH output',
                    'default': False,
                    'action': 'store_true',
                    'dest': 'verbose'
                }
            ),
            (
                ["--choose"],
                {
                    'help': 'Choose from all available targets for ssh, instead of having one chosen automatically.',
                    'default': False,
                    'action': 'store_true',
                    'dest': 'choose'
                }
            ),
            (
                ["--all"],
                {
                    'help': 'Run the shell command on all instances related to our object.',
                    'default': False,
                    'action': 'store_true',
                    'dest': 'all'
                }
            )
        ]
    )
    @handle_model_exceptions
    def run(self):
        """
        SSH to a container machine running one of the tasks for an existing Service or Task in AWS.

        NOTE: this is only available if your Service or Task is of launch type EC2.  You cannot ssh
        to the container machine of a FARGATE Service or task.
        """
        colors_cycle = cycle(self.COLORS)
        loader = self.loader(self)
        obj = loader.get_object_from_aws(self.app.pargs.pk)
        assert hasattr(obj, 'ssh_target'), f'Objects of type {obj.__class__.__name__} do not support SSH actions'
        command = ' '.join(self.app.pargs.command)
        if not self.app.pargs.all:
            targets: Sequence[Instance] = [get_ssh_target(self.app, obj, choose=self.app.pargs.choose)]
        else:
            targets = obj.ssh_targets
        for target in targets:
            color = next(colors_cycle)
            success, output = target.ssh_noninteractive(command, verbose=self.app.pargs.verbose, ssh_target=target)
            if success:
                for line in output.split('\n'):
                    self.app.print('{}: {}'.format(click.style(target.name, fg=color), line))
            else:
                for line in output.split('\n'):
                    line = click.style('ERROR: {}'.format(line), fg='red')
                    self.app.print('{}: {}'.format(click.style(target.name, fg=color), line))


class ObjectDockerExecController(Controller):

    class Meta:
        label = 'exec-base'

    model: Type[Model] = Model
    loader: Type[ObjectLoader] = ObjectLoader

    def get_ssh_exec_target(
        self,
        obj: SupportsService,
        choose: bool = False
    ) -> Tuple[Optional[Instance], Optional[str]]:
        """
        Return an (instance, container_name) tuple suitable for using to exec
        into a particular container on a particular instance.

        .. note::
            This is for EC2 backed services only.  For FARGATE services, use
            ``self.get_ecs_exec_target()``.

        If ``choose`` is ``False``, return (None, None).

        If ``choose`` is ``True``, prompt the user to choose one of the
        available containers for this object.

        Args:
            obj: an instance of ``self.model``

        Keyword Arguments:
            choose: if ``True``, prompt the user to choose one of the available instances

        Returns:
            A 2-Tuple of an ``Instance`` object and container name.  This will
            return (None, None) on purpose if ``choose`` is ``False``, letting
            the object choose its instance and container later.
        """
        assert hasattr(obj, 'ssh_targets'), \
            f'{obj.__class__.__name__} objects do not have the .ssh_targets attribute'
        assert hasattr(obj, 'running_tasks'), \
            f'{obj.__class__.__name__} objects do not have the .running_tasks attribute'
        target = None
        container_name = None
        if choose:
            # Since we're calling get_ssh_exec_target, we can assume that every task has an underlying
            # EC2 instance, even though Task.ssh_target can return None
            running_tasks = sorted(
                obj.running_tasks,
                key=lambda x: cast(Instance, x.ssh_target).tags['Name']
            )
            rows = []
            click.secho('\nAvailable exec targets:', fg='green')
            click.secho('----------------------\n', fg='green')
            number = 1
            choices = []
            for task in running_tasks:
                for container in task.containers:
                    ssh_target = cast(Instance, task.ssh_target)
                    rows.append([
                        number,
                        click.style(ssh_target.tags['Name'], fg='cyan'),
                        click.style(container.name, fg='yellow'),
                        click.style(container.version, fg='yellow'),
                        ssh_target.pk,
                        ssh_target.ip_address
                    ])
                    choices.append((task.ssh_target, container.name))
                    number += 1
            self.app.print(tabulate(rows, headers=['#', 'Instance', 'Container', 'Version', 'Instance Id', 'IP']))
            p = shell.Prompt('\nEnter the number of the container you want: ', default=1)
            choice = p.prompt()
            target, container_name = choices[int(choice) - 1]
        return target, container_name

    def get_ecs_exec_target(self, obj: SupportsService, choose: bool = False) -> Tuple[Optional[str], Optional[str]]:
        """
        Return an (task_arn, container_name) tuple suitable for using to exec
        into a particular container on a particular instance.

        .. note::
            This is for FARGATE tasks only.  For EC2 backed tasks, use ``self.get_ssh_exec_target()``.

        If ``choose`` is ``False``, return (None, None).

        If ``choose`` is ``True``, prompt the user to choose one of the
        available ssh targets for this object, and return an ``Instance`` object
        representing their choice.

        Args:
            obj: an instance of ``self.model``

        Keyword Arguments:
            choose: if ``True``, prompt the user to choose one of the available instances

        Returns:
            A 2-Tuple of an Task ARN and container name.  This will
            return (None, None) on purpose if ``choose`` is ``False``, letting
            the object choose its instance and container later.
        """
        assert hasattr(obj, 'running_tasks'), \
            f'{obj.__class__.__name__} objects do not have the .running_tasks attribute'
        task_arn = None
        container_name = None
        if choose:
            running_tasks = sorted(obj.running_tasks, key=lambda x: x.name)
            rows = []
            click.secho('\nAvailable exec targets:', fg='green')
            click.secho('----------------------\n', fg='green')
            number = 1
            choices = []
            for task in running_tasks:
                for container in task.containers:
                    rows.append([
                        number,
                        click.style(task.pk.split('/')[-1], fg='cyan'),
                        click.style(task.availability_zone, fg='white'),
                        click.style(container.name, fg='yellow'),
                        click.style(container.version, fg='yellow'),
                    ])
                    choices.append((task.arn, container.name))
                    number += 1
            self.app.print(tabulate(rows, headers=['#', 'Task', 'Container', 'Version']))
            p = shell.Prompt('\nEnter the number of the container you want: ', default=1)
            choice = p.prompt()
            task_arn, container_name = choices[int(choice) - 1]
        return task_arn, container_name

    @ex(
        help="Exec into a container in AWS",
        arguments=[
            (['pk'], { 'help' : 'The primary key for the object in AWS'}),
            (
                ["--verbose"],
                {
                    'help': 'Show all SSH output',
                    'default': False,
                    'action': 'store_true',
                    'dest': 'verbose'
                }
            ),
            (
                ["--choose"],
                {
                    'help': 'Choose from all available targets for "docker exec", instead of having one '
                            'chosen automatically.',
                    'default': False,
                    'action': 'store_true',
                    'dest': 'choose'
                }
            )
        ]
    )
    @handle_model_exceptions
    def exec(self):
        """
        SSH to a container machine running one of the tasks for an existing Service or Task in AWS.

        NOTE: this is only available if your Service or Task is of launch type EC2.  You cannot ssh
        to the container machine of a FARGATE Service or task.
        """
        loader = self.loader(self)
        obj = loader.get_object_from_aws(self.app.pargs.pk)
        if obj.exec_enabled:
            task_arn, container_name = self.get_ecs_exec_target(obj, choose=self.app.pargs.choose)
            obj.docker_ecs_exec(task_arn=task_arn, container_name=container_name)
        else:
            target, container_name = self.get_ssh_exec_target(obj, choose=self.app.pargs.choose)
            obj.docker_ssh_exec(
                ssh_target=target,
                container_name=container_name,
                verbose=self.app.pargs.verbose
            )
