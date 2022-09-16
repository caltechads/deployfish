from datetime import datetime
import os
import time
from typing import Type, cast

from cement import ex
from cement.utils.version import get_version_banner
import click

from deployfish import get_version
from deployfish.controllers.service import ECSService, ECSServiceDockerExec, ECSServiceSSH, ECSServiceSecrets
from deployfish.controllers.utils import handle_model_exceptions
from deployfish.core.models import Model, Service, StandaloneTask
from deployfish.ext.ext_df_argparse import DeployfishArgparseController as Controller
from deployfish.types import SupportsModelWithSecrets


VERSION_BANNER = """
deployfish-%s: Manage the lifecycle of AWS ECS services
---
%s
""" % (get_version(), get_version_banner())


def filename_envvar(s):
    if 'DEPLOYFISH_CONFIG_FILE' in os.environ:
        return os.environ['DEPLOYFISH_CONFIG_FILE']
    return s


def maybe_rename_existing_file(env_file: str, obj: SupportsModelWithSecrets) -> None:
    """
    Look at the filesystem path ``env_file``.  If a file exists at that path, rename it
    to ``env_file.YYYY-MM-DDTHH:MM:SS``.

    Args:
        env_file: the full path to the file to write
        obj: the object from deployfish.yml that uses ``env_file``
    """
    if os.path.exists(env_file):
        new_filename = "{}.{}".format(env_file, datetime.now().strftime('%Y-%m-%dT%H:%M:%S'))
        while os.path.exists(new_filename):
            time.sleep(1)
            new_filename = "{}.{}".format(env_file, datetime.now().strftime('%Y-%m-%dT%H:%M:%S'))
        os.rename(env_file, new_filename)
        click.secho('{}("{}"): renamed existing env_file to {}'.format(
            obj.__class__.__name__,
            obj.name,
            new_filename
        ), fg='yellow')


class Base(Controller):
    class Meta:
        label = 'base'

        # text displayed at the top of --help output
        description = 'deployfish: Manage the lifecycle of AWS ECS services'

        # controller level arguments. ex: 'deploy --version'
        arguments = [
            ### add a version banner
            (['-v', '--version'], {'action' : 'version', 'version' : VERSION_BANNER}),
            (
                ['-f', '--filename'],
                {
                    'dest': 'deployfish_filename',
                    'action': 'store',
                    'default': 'deployfish.yml',
                    'help': 'Path to the deployfish config file',
                    'type': filename_envvar
                }
            ),
            (
                ['--no-use-aws-section'],
                {
                    'action' : 'store_true',
                    'dest': 'no_use_aws_section',
                    'default': False,
                    'help': 'Ignore the aws: section in deployfish.yml'
                }
            ),
            (
                ['-e', '--env_file'],
                {
                    'dest': 'env_file',
                    'action': 'store',
                    'default': None,
                    'help': 'Path to an environment file to use for ${env.VAR} replacements'
                }
            ),
            (
                ['-t', '--tfe_token'],
                {
                    'dest': 'tfe_token',
                    'action': 'store',
                    'default': None,
                    'help': 'Terraform Enterprise API Token'
                }
            ),
            (
                ['--ignore-missing-environment'],
                {
                    'dest': 'ignore_missing_environment',
                    'action': 'store_true',
                    'default': False,
                    'help': "Don't stop processing deployfish.yml if we can't dereference an ${env.VAR}"
                }
            ),
        ]


    def _default(self):
        """Default action if no sub-command is passed."""
        self.app.args.print_help()


class BaseService(ECSService):

    class Meta:
        label = "base-service"
        stacked_on = "base"
        stacked_type = "embedded"


class BaseServiceSecrets(ECSServiceSecrets):

    class Meta:
        label = "base-config"
        aliases = ['config']
        aliases_only = True
        stacked_on = "base"
        stacked_type = "nested"

    def _write_env_file(self, env_file: str, name: str, model: Type[Model]) -> None:
        """
        Write the environment file to its appropriate place in the file system.  If that file already
        exists, move it out of the way before writing a new one.

        Args:
            env_file: the full path to the file to write
            name: the name of the Model object in deployfish.yml
            model: the type of the Model object named by ``name``
        """
        loader = self.loader(self)
        raw = loader.get_object_from_deployfish(
            name,
            model=model,
            factory_kwargs={'load_secrets': False}
        )
        assert hasattr(raw, 'secrets_prefix'), f'Models of type "{raw.__class__.__name__} do not have secrets.'
        obj = cast(SupportsModelWithSecrets, raw)
        maybe_rename_existing_file(env_file, obj)
        contents = self.export_environment_secrets(obj)
        with open(env_file, "w", encoding='utf-8') as fd:
            fd.write(contents)
            click.secho('{}("{}"): exported live secrets to env_file {}'.format(
                obj.__class__.__name__,
                obj.name,
                env_file
            ), fg='green')


    @ex(help="Download data for all env_files defined in deployfish.yml sections")
    @handle_model_exceptions
    def sync(self):
        """
        For each standalone task and service, if the task/service has an "env_file:" defined,
        export the ${{env.VAR}} related secrets to that "env_file:".  Save a backup copy of the
        existing "env_file:".
        """
        # Always ignore missing environment here -- the whole purpose of the command is to
        # fix missing environment variables
        self.app.pargs.ignore_missing_environment = True
        config = self.app.raw_deployfish_config
        services = {item['name']: item['env_file'] for item in config.services if 'env_file' in item}
        tasks = {item['name']: item['env_file'] for item in config.tasks if 'env_file' in item}
        for service, env_file in list(services.items()):
            self._write_env_file(env_file, service, Service)
        for task, env_file in list(tasks.items()):
            self._write_env_file(env_file, task, StandaloneTask)


class BaseServiceSSH(ECSServiceSSH):

    class Meta:
        label = "base-ssh"
        stacked_on = "base"


class BaseServiceDockerExec(ECSServiceDockerExec):

    class Meta:
        label = "base-exec"
        stacked_on = "base"
