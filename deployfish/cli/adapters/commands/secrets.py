import click

from deployfish.config import get_config
from deployfish.exceptions import ConfigProcessingFailed
from deployfish.core.models import Secret

from deployfish.cli.adapters.utils import handle_model_exceptions, print_render_exception
from deployfish.cli.renderers import (
    TableRenderer,
    JSONRenderer,
    TemplateRenderer
)
from deployfish.core.adapters import parse_secret_string


# ====================
# Renderers
# ====================

class SecretsTableRenderer(TableRenderer):

    def render(self, data):
        found_secrets = [s for s in data if s.arn]
        missing_secrets = [s for s in data if not s.arn]
        table_lines = super(SecretsTableRenderer, self).render(found_secrets)
        lines = []
        lines.append("\n\nThese secrets are not present in AWS SSM Paramter Store:\n")
        for s in missing_secrets:
            lines.append(click.style("  {}".format(s.pk), fg='red'))
        table_lines += '\n'.join(lines)
        return table_lines


# ====================
# Command mixins
# ====================

class ClickObjectSecretsShowCommandMixin(object):

    show_secrets_ordering = 'Name'
    show_secrets_columns = {
        'Name': 'secret_name',
        'Value': 'value',
        'Secure?': 'is_secure',
        'Modified': 'LastModifiedDate',
        'Modified By': 'modified_username'
    }
    show_secrets_renderer_classes = {
        'template': TemplateRenderer,
        'table': SecretsTableRenderer,
        'json': JSONRenderer,
    }

    @classmethod
    def show_secrets_display_option_kwargs(cls):
        """
        Return the appropriate kwargs for `click.option('--display', **kwargs)` for the renderer options we've defined
        for the show_secrets command.

        :rtype: dict
        """
        render_types = list(cls.show_secrets_renderer_classes.keys())
        default = render_types[0]
        kwargs = {
            'type': click.Choice(render_types),
            'default': default,
            'help': "Choose how to display secrets for a {} object. Choices: {}.  Default: {}.".format(
                cls.model.__name__,
                ', '.join(render_types),
                default
            )
        }
        return kwargs

    @classmethod
    def add_show_secrets_command(cls, command_group):
        """
        Build a fully specified click command for retrieving secrets from AWS SSM Paramter store and
        displaying their values.

        :param command_group function: the click command group function to use to register our click command

        :rtype: function
        """
        def show_secrets(ctx, *args, **kwargs):
            if cls.model.config_section is not None:
                try:
                    ctx.obj['config'] = get_config(**ctx.obj)
                except ConfigProcessingFailed:
                    pass
            ctx.obj['adapter'] = cls()
            click.secho(ctx.obj['adapter'].show_secrets(kwargs['identifier'], kwargs['display']))
        pk_description = cls.get_pk_description()
        show_secrets.__doc__ = """
Show the live values of the AWS SSM Parameter Store secrets associated with a {object_name}.

{pk_description}
""".format(pk_description=pk_description, object_name=cls.model.__name__)

        function = print_render_exception(show_secrets)
        function = click.pass_context(function)
        function = click.option('--display', **cls.show_secrets_display_option_kwargs())(function)
        function = click.argument('identifier')(function)
        function = command_group.command(
            'show',
            short_help='Show AWS SSM Parameter Store secrets for a {}'.format(cls.model.__name__)
        )(function)
        return function

    @handle_model_exceptions
    def show_secrets(self, identifier, display):
        assert display in self.show_secrets_renderer_classes, \
            '{}.show_secrets(): "{}" is not a valid rendering option'.format(
                self.__class__.__name__,
                display
            )
        obj = self.get_object_from_aws(identifier)
        obj.reload_secrets()
        click.secho(
            'Live values for AWS SSM Parameter store secrets for {}(pk="{}"):'.format(
                self.model.__name__,
                obj.pk
            )
        )
        if display == 'table':
            results = self.show_secrets_renderer_classes[display](
                self.show_secrets_columns,
                ordering=self.show_secrets_ordering
            ).render(obj.secrets.values())
        elif display == 'template':
            results = self.show_secrets_renderer_classes[display]().render(obj.secrets, template='secrets--detail.tpl')
        else:
            results = self.show_secrets_renderer_classes[display]().render([s.data for s in obj.secrets.values()])
        return '\n' + results + '\n'


class ClickObjectSecretsWriteCommandMixin(object):

    @classmethod
    def add_write_secrets_command(cls, command_group):
        """
        Build a fully specified click command for writing secrets to AWS SSM Paramter store using their values
        from deployfish.yml.

        :param command_group function: the click command group function to use to register our click command

        :rtype: function
        """
        def write_secrets(ctx, *args, **kwargs):
            ctx.obj['config'] = get_config(**ctx.obj)
            ctx.obj['adapter'] = cls()
            click.secho(ctx.obj['adapter'].write_secrets(kwargs['identifier']))

        pk_description = cls.get_pk_description()
        write_secrets.__doc__ = """
Write the AWS SSM Parameter Store secrets associated with a {object_name} to AWS.

{pk_description}
""".format(
            pk_description=pk_description,
            object_name=cls.model.__name__
        )

        function = print_render_exception(write_secrets)
        function = click.pass_context(function)
        function = click.argument('identifier')(function)
        function = command_group.command(
            'write',
            short_help='Write AWS SSM Parameter Store secrets for a {} to AWS'.format(cls.model.__name__)
        )(function)
        return function

    @handle_model_exceptions
    def write_secrets(self, identifier):
        obj = self.get_object_from_deployfish(identifier)
        other = Secret.objects.list(obj.secrets_prefix)
        changes = obj.diff_secrets(other, ignore_external=True)
        if not changes:
            return click.style(
                '\nABORTED: The AWS secrets for {}("{}") are up to date.\n'.format(self.model.__name__, obj.pk),
                fg='green'
            )
        click.echo('\nChanges to be applied to secrets for {}("{}"):\n'.format(self.model.__name__, obj.pk))
        click.echo(
            TemplateRenderer().render(changes, template='secrets--diff.tpl')
        )
        click.echo("\nIf you really want to do this, answer \"yes\" to the question below.\n".format(obj.name))
        value = click.prompt("Apply the above changes to AWS?")
        if value != 'yes':
            return click.style(
                '\nABORTED: not updating secrets for {}({}).'.format(self.model.__name__, obj.pk),
                fg='green'
            )
        click.secho(
            '\nWriting secrets ...'.format(self.model.__name__, obj.pk),
            nl=False
        )
        obj.write_secrets()
        click.secho(' done.\n\n')
        obj.reload_secrets()
        click.secho(
            'Live values for AWS SSM Parameter store secrets for {}(pk="{}"):'.format(
                self.model.__name__,
                obj.pk
            ),
            fg='green'
        )
        return TemplateRenderer().render(obj.secrets, template='secrets--detail.tpl')


class ClickObjectSecretsDiffCommandMixin(object):

    @classmethod
    def add_diff_secrets_command(cls, command_group):
        """
        Build a fully specified click command for diffing secrets between from AWS SSM Paramter store and
        and deployfish.yml.

        :param command_group function: the click command group function to use to register our click command

        :rtype: function
        """
        def diff_secrets(ctx, *args, **kwargs):
            ctx.obj['config'] = get_config(**ctx.obj)
            ctx.obj['adapter'] = cls()
            click.secho(ctx.obj['adapter'].diff_secrets(kwargs['identifier']))

        pk_description = cls.get_pk_description()
        diff_secrets.__doc__ = """
Diff the AWS SSM Parameter Store secrets against their counterparts in deployfish.yml.

{pk_description}
""".format(
            pk_description=pk_description,
            object_name=cls.model.__name__
        )

        function = print_render_exception(diff_secrets)
        function = click.pass_context(function)
        function = click.argument('identifier')(function)
        function = command_group.command(
            'diff',
            short_help='Diff AWS SSM Parameter Store secrets vs those in deployfish.yml for a {}'.format(
                cls.model.__name__
            )
        )(function)
        return function

    @handle_model_exceptions
    def diff_secrets(self, identifier):
        """
        Show the difference between the secrets we have in our deployfish.yml file and what is in AWS.
        """
        obj = self.get_object_from_deployfish(identifier)
        other = Secret.objects.list(obj.secrets_prefix)
        title = '\nDiffing secrets for {}(pk="{}"):'.format(self.model.__name__, obj.pk)
        click.echo(title)
        click.echo("=" * len(title))
        print()
        changes = obj.diff_secrets(other, ignore_external=True)
        if not changes:
            return click.style(
                'The AWS secrets for {}("{}") are up to date.\n'.format(self.model.__name__, obj.pk),
                fg='green'
            )
        else:
            return TemplateRenderer().render(changes, template='secrets--diff.tpl')


class ClickObjectSecretsExportCommandMixin(object):

    @classmethod
    def add_export_secrets_command(cls, command_group):
        """
        Build a fully specified click command for exporting the ${env.VAR} related secrets between from AWS SSM Paramter
        store and and deployfish.yml.

        :param command_group function: the click command group function to use to register our click command

        :rtype: function
        """
        def diff_secrets(ctx, *args, **kwargs):
            ctx.obj['config'] = get_config(**ctx.obj)
            ctx.obj['adapter'] = cls()
            click.secho(ctx.obj['adapter'].export_secrets(kwargs['identifier'], ctx.obj['config']))

        pk_description = cls.get_pk_description()
        diff_secrets.__doc__ = """
Extract AWS SSM Parameter Store secrets for a {object_name} in AWS and print
them to stdout in the proper format for use in a deployfish.yml "env_file:".
We will specifically only export the secrets that in deployfish.yml have their
values defined as ${{env.VAR}} interpolations, as these are what should go in your
"env_file:".

{pk_description}
""".format(
            pk_description=pk_description,
            object_name=cls.model.__name__
        )

        function = print_render_exception(diff_secrets)
        function = click.pass_context(function)
        function = click.argument('identifier')(function)
        function = command_group.command(
            'export',
            short_help='Export the AWS SSM Parameter Store secrets vs those in deployfish.yml for a {}'.format(
                cls.model.__name__
            )
        )(function)
        return function

    @handle_model_exceptions
    def export_secrets(self, identifier, config):
        """
        Extract AWS SSM Parameter Store secrets for a {object_name} in AWS and print them to stdout in the proper format
        for use in a deployfish.yml "env_file:".  We will specifically only export the secrets that in deployfish.yml
        have their values defined as ${env.VAR} interpolations, as these are what should go in your "env_file:".
        """
        obj = self.get_object_from_deployfish(identifier)
        item = config.get_raw_section_item(self.model.config_section, obj.name)
        env_vars = {}
        for secret_def in item['config']:
            key, kwargs = parse_secret_string(secret_def)
            value = kwargs['Value'].strip()
            if value.startswith('${env.'):
                env_var = value[6:-1]
                env_vars[key] = env_var
        secrets = Secret.objects.list(obj.secrets_prefix)
        lines = []
        for secret in secrets:
            if secret.secret_name in env_vars:
                lines.append("{}={}".format(env_vars[secret.secret_name], secret.value))
        return '\n'.join(lines)
