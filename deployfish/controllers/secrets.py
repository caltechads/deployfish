from typing import Type, cast

from cement import ex, shell
import click

from deployfish.core.adapters.deployfish.secrets import parse_secret_string
from deployfish.core.loaders import ObjectLoader
from deployfish.core.models import Model, Secret
from deployfish.ext.ext_df_argparse import DeployfishArgparseController as Controller
from deployfish.types import SupportsModelWithSecrets

from .utils import handle_model_exceptions


class ObjectSecretsController(Controller):

    class Meta:
        label = 'secrets-base'

    model: Type[Model] = Model
    loader: Type[ObjectLoader] = ObjectLoader

    show_template: str = 'detail--secrets.jinja2'
    diff_template: str = 'detail--secrets--diff.jinja2'

    def export_environment_secrets(self, obj: SupportsModelWithSecrets) -> str:
        """
        Iterate through the secrets listed in our object's ``config:`` section
        in deployfish.yml.  Find all the entries which have ``${env.VAR}``
        interpolations, retrieve their live values from AWS SSM Parameter Store, and
        return the contents of a suitable ``.env`` file.

        Args:
            obj: an instance of ``self.model``

        Returns:
            The contents of an ``.env`` file that reflects what is in AWS SSM Parameter Store.
        """

        # get the configuration for our object from deployfish.yml
        config = self.app.deployfish_config
        item = config.get_raw_section_item(self.model.config_section, obj.name)
        env_vars = {}
        # iterate through the config: list, and save all secrets that start with
        # "${env.""
        for secret_def in item['config']:
            if '=' not in secret_def:
                # This is an external parameter spec
                continue
            key, kwargs = parse_secret_string(secret_def)
            value = kwargs['Value'].strip()
            if value.startswith('${env.'):
                env_var = value[6:-1]
                env_vars[key] = env_var
        # Load their values form AWS
        secrets = Secret.objects.list(obj.secrets_prefix)
        lines = []
        for secret in secrets:
            if secret.secret_name in env_vars:
                lines.append("{}={}".format(env_vars[secret.secret_name], secret.value))
        lines = sorted(lines)
        return '\n'.join(lines)


    @ex(
        help="Show all AWS SSM Parameter Store secrets for an object as they exist in AWS",
        arguments=[
            (['pk'], { 'help' : 'The primary key for the object in AWS'})
        ],
    )
    @handle_model_exceptions
    def show(self):
        loader = self.loader(self)
        raw = loader.get_object_from_aws(self.app.pargs.pk)
        assert hasattr(raw, 'secrets_prefix'), f'Models of type "{raw.__class__.__name__} do not have secrets.'
        obj = cast(SupportsModelWithSecrets, raw)
        obj.reload_secrets()
        self.app.render({'obj': obj.secrets}, template=self.show_template)

    @ex(
        help="Diff AWS SSM Parameter Store secrets vs those in deployfish.yml for an object.",
        arguments=[
            (['pk'], { 'help' : 'The primary key for the object in AWS'})
        ],
    )
    @handle_model_exceptions
    def diff(self):
        """
        Diff secrets against what is currently in AWS Systems Manager Parameter
        Store.  They can be different because we changed ``deployfish.yml``, or
        we changed our ``.env`` file, or we update terraform.
        """
        loader = self.loader(self)
        raw = loader.get_object_from_deployfish(self.app.pargs.pk)
        assert hasattr(raw, 'secrets_prefix'), f'Models of type "{raw.__class__.__name__} do not have secrets.'
        obj = cast(SupportsModelWithSecrets, raw)
        other = Secret.objects.list(obj.secrets_prefix)
        title = '\nDiffing secrets for {}(pk="{}"):'.format(self.model.__name__, obj.pk)
        self.app.print(title)
        self.app.print("=" * len(title))
        changes = obj.diff_secrets(other, ignore_external=True)
        if not changes:
            self.app.print(
                click.style(
                    'The AWS secrets for {}("{}") are up to date.\n'.format(self.model.__name__, obj.pk),
                    fg='green'
                )
            )
        self.app.render({'obj': changes}, template=self.diff_template)

    @ex(
        help="Show all AWS SSM Parameter Store secrets for an object",
        arguments=[
            (['pk'], { 'help' : 'The primary key for the object in AWS'}),
            (
                ['--force'],
                {
                    'help' : "Don't do a diff before writing the secrets, just write them.",
                    'action': 'store_true',
                    'default': False,
                    'dest': 'force'
                }
            ),
        ]
    )
    @handle_model_exceptions
    def write(self):
        """
        Write secrets to AWS Systems Manager Parameter Store.
        """
        loader = self.loader(self)
        raw = loader.get_object_from_deployfish(self.app.pargs.pk)
        assert hasattr(raw, 'secrets_prefix'), f'Models of type "{raw.__class__.__name__} do not have secrets.'
        obj = cast(SupportsModelWithSecrets, raw)
        other = Secret.objects.list(obj.secrets_prefix)
        if not self.app.pargs.force:
            changes = obj.diff_secrets(other, ignore_external=True)
            if not changes:
                self.app.print(
                    click.style(
                        '\nABORTED: The AWS secrets for {}("{}") are up to date.\n'.format(self.model.__name__, obj.pk),
                        fg='green'
                    )
                )
                return
            self.app.print(
                click.style('\nChanges to be applied to secrets for {}("{}"):\n'.format(self.model.__name__, obj.pk))
            )
            self.app.render({'obj': changes}, template=self.diff_template)
            self.app.print(click.style("\nIf you really want to do this, answer \"yes\" to the question below.\n"))
            p = shell.Prompt("Apply the above changes to AWS?")
            value = p.prompt()
            if value != 'yes':
                self.app.print(
                    click.style(
                        '\nABORTED: not updating secrets for {}({}).'.format(self.model.__name__, obj.pk),
                        fg='green'
                    )
                )
                return
        self.app.print('Writing secrets ...')
        obj.write_secrets()
        self.app.print('Done.')
        obj.reload_secrets()
        self.app.render({'obj': obj.secrets}, template=self.show_template)

    @ex(
        help="Export the AWS SSM Parameter Store secrets vs those in deployfish.yml",
        arguments=[
            (['pk'], { 'help' : 'The primary key for the object in AWS'})
        ]
    )
    @handle_model_exceptions
    def export(self):
        """
        Extract AWS SSM Parameter Store secrets for a object in AWS and print
        them to stdout in the proper format for use in a deployfish.yml "``env_file:``".
        We will specifically only export the secrets that in deployfish.yml have their
        values defined as ``${env.VAR}`` interpolations, as these are what should go in your
        "``env_file``:".
        """
        assert hasattr(self.model, 'secrets_prefix'), f'Models of type "{self.model.__name__} do not have secrets.'
        loader = self.loader(self)
        obj = loader.get_object_from_deployfish(self.app.pargs.pk)
        self.app.print(self.export_environment_secrets(obj))
