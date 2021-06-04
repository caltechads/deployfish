import click

from deployfish.config import get_config
from deployfish.exceptions import RenderException, ObjectReadOnly, ObjectDoesNotExist, ConfigProcessingFailed
from deployfish.typing import FunctionTypeCommentParser

from .commands import (
    GetSSHTargetMixin,
    GetExecTargetMixin,
    SecretsExportMixin,
    ClickCreateObjectCommandMixin,
    ClickDeleteObjectCommandMixin,
    ClickExecObjectCommandMixin,
    ClickListObjectsCommandMixin,
    ClickObjectExistsCommandMixin,
    ClickObjectInfoCommandMixin,
    ClickObjectSecretsDiffCommandMixin,
    ClickObjectSecretsExportCommandMixin,
    ClickObjectSecretsShowCommandMixin,
    ClickObjectSecretsWriteCommandMixin,
    ClickRunCommandCommandMixin,
    ClickSSHObjectCommandMixin,
    ClickSyncSecretsCommandMixin,
    ClickTunnelObjectCommandMixin,
    ClickUpdateObjectCommandMixin,
)


# ====================
# Adapters
# ====================

class ClickBaseModelAdapter(object):

    class DeployfishSectionDoesNotExist(ObjectDoesNotExist):

        def __init__(self, msg, section):
            self.msg = msg
            self.section = section

    class DeployfishObjectDoesNotExist(ObjectDoesNotExist):

        def __init__(self, msg, section, name):
            self.msg = msg
            self.section = section
            self.name = name

    class ObjectNotManaged(Exception):
        pass

    class ReadOnly(ObjectReadOnly):
        pass

    model = None
    factory_kwargs = {}

    # Renderers
    datetime_format = None
    date_format = None
    float_precision = None

    @classmethod
    def add_command_group(cls, parent, name=None, short_help=None):
        """
        Build the command group for our commands for this model.

        :param parent click.group: the click group that should be the parent to this group
        :param name str: (optional) the name for this group.  Default: the lower-cased model name.
        :param short_help str: (optional) the short_help for this group.

        :rtype: function
        """
        def cmdgroup(ctx):
            pass

        cmdgroup = click.pass_context(cmdgroup)
        if not name:
            name = cls.model.__name__.lower()
        if not short_help:
            if cls.model.config_section is not None:
                verb = 'Manage'
            else:
                verb = 'Describe'
            short_help = '{} {} objects in AWS'.format(verb, cls.model.__name__)
        cmdgroup = parent.group(name=name, short_help=short_help)(cmdgroup)
        return cmdgroup

    @classmethod
    def add_argument(cls, name, arg, function):
        """
        Add a click.argument() to a function based on the type hints from the associated method on the model's Manager.

        :param name str: the name of the argument
        :param kwarg dict: the argument configuration extracted from the type hint
        :param function function: the function to which to add the option

        :rtype: function
        """
        arg_type = arg['type']
        if arg_type == 'datetime':
            click_type = click.DateTime()
        else:
            click_type = arg_type
        function = click.argument(name, type=click_type)(function)
        return function

    @classmethod
    def add_option(cls, name, kwarg, function):
        """
        Add a click.option() to a function based on the type hints from the associated method on the model's Manager.

        :param name str: the name of the option.  If the name has underscores, change those to dashes.
        :param kwarg dict: the option configuration extracted from the type hint
        :param function function: the function to which to add the option

        :rtype: function
        """
        arg_type = kwarg['type']
        if arg_type == bool:
            option = "--{name}/--no-{name}".format(name=name.replace('_', '-'))
        else:
            option = "--{}".format(name.replace('_', '-'))
        if arg_type == 'datetime':
            click_type = click.DateTime()
        elif arg_type == 'choice':
            click_type = click.Choice(kwarg['choices'])
        else:
            click_type = arg_type
        help_str = kwarg.get('help_str', "Filter results by {}".format(name))
        if kwarg['default'] is not None:
            help_str += ". Default: {}.".format(kwarg['default'])
        if 'specs' in kwarg:
            formats = ['"{}"'.format(spec) for spec in kwarg['specs']]
            help_str += ". Acceptible value formats: {}".format(', '.join(formats))
        if 'multiple' in kwarg and kwarg['multiple']:
            option_kwargs = {
                'default': [kwarg['default']],
                'help': help_str,
                'multiple': True,
            }
        else:
            option_kwargs = {
                'default': kwarg['default'],
                'help': help_str
            }
        if not isinstance(click_type, str) and arg_type != bool:
            option_kwargs['type'] = click_type
        function = click.option(option, **option_kwargs)(function)
        return function

    @classmethod
    def get_required_args(cls, args):
        required_args = " ".join([arg.upper() for arg in args.keys()])
        if required_args:
            required_args += " "
        return required_args

    @classmethod
    def get_pk_description(cls, name='IDENTIFIER', model=None):
        """
        For click commands that work on a single object, build a description of all the different ways the primary key
        can be constructed by looking at the type hints for the "get" method on the model's Manager.

        For this to work, "get" method should have a hint like this:

            def get(self, pk):
                # hint: (str["{foo}.{bar}","{bar}"])

        The quoted strings inside the `str[]` bit of the hint are suggestions to the user as to what the primary keys
        strings would look like.

        :rtype: str
        """
        if not model:
            model = cls.model
        args, kwargs = FunctionTypeCommentParser().parse(model.objects.get)
        pk_description = ''
        pk_description = "{} is a string that looks like".format(name)
        if 'specs' in args['pk']:
            if len(args['pk']['specs']) > 1 or model.config_section:
                pk_description += " one of:\n\n"
                for spec in args['pk']['specs']:
                    pk_description += '    * {}\n\n'.format(spec)
            else:
                pk_description += ' {}\n\n'.format(args['pk']['specs'][0])
            if model.config_section is not None:
                pk_description += "    * {}.name\n\n".format(model.__name__)
                pk_description += "    * {}.environment\n\n".format(model.__name__)
        return pk_description

    def __init__(self):
        assert self.model is not None, \
            '{}: please set the model class attribute'.format(
                self.__class__.__name__
            )

    def dereference_identifier(self, identifier):
        return identifier

    def get_object_from_aws(self, identifier, model=None):
        if not model:
            model = self.model
        if model.config_section is not None:
            identifier = self.dereference_identifier(identifier)
        try:
            obj = model.objects.get(identifier)
        except model.DoesNotExist as e:
            raise RenderException(str(e))
        return obj

    def get_object_from_deployfish(self, identifier, factory_kwargs=None, model=None):
        if not model:
            model = self.model
        if model.config_section is not None:
            try:
                obj = self.factory(identifier, factory_kwargs, model=model)
            except ConfigProcessingFailed as e:
                raise RenderException(str(e))
        return obj

    def factory(self, identifier, factory_kwargs=None, model=None):
        """
        Load an object from deployfish.yml.  Look in the section named by `self.model.config_section` for the entry
        named `identifier` and return a fully configured self.model object.

        If `factory_kwargs` is provided, pass those on as kwargs to the `self.model.new()` class method.

        :param identifier str: the name of the item to load from the section named by `self.model.config_section`
        :param factory_kwargs dict: kwargs to pass into `self.model.new()`

        :rtype: self.model
        """
        if not model:
            model = self.model
        if not factory_kwargs:
            factory_kwargs = {}
        config = get_config()
        if model.config_section:
            try:
                config.get_section(model.config_section)
            except KeyError:
                raise self.DeployfishSectionDoesNotExist(
                    'No section in deployfish.yml named "{}" \n'.format(model.__name__, identifier),
                    model.config_section
                )
            try:
                data = config.get_section_item(model.config_section, identifier)
                return model.new(data, 'deployfish', **factory_kwargs)
            except KeyError:
                raise self.DeployfishObjectDoesNotExist(
                    'Could not find a {} named "{}" in deployfish.yml\n'.format(model.__name__, identifier),
                    model.config_section,
                    identifier
                )
        else:
            raise self.ObjectNotManaged(
                'deployfish.yml does not manage objects of class {}'.format(model.__class__)
            )

    def wait(self, operation, **kwargs):
        """
        Build a `deployfish.core.waiters.HookedWaiter` for the operation named `operation` and with configuration
        `kwargs`, and then run it.

        `operation` can be any waiter operation that boto3 supports for self.model type objects.
        """
        waiter = self.model.objects.get_waiter(operation)
        waiter.wait(**kwargs)


class ClickReadOnlyModelAdapter(
    GetSSHTargetMixin,
    GetExecTargetMixin,
    ClickListObjectsCommandMixin,
    ClickObjectInfoCommandMixin,
    ClickObjectExistsCommandMixin,
    ClickSSHObjectCommandMixin,
    ClickRunCommandCommandMixin,
    ClickTunnelObjectCommandMixin,
    ClickBaseModelAdapter,
):
    pass


class ClickModelAdapter(
    GetSSHTargetMixin,
    GetExecTargetMixin,
    ClickListObjectsCommandMixin,
    ClickObjectInfoCommandMixin,
    ClickObjectExistsCommandMixin,
    ClickCreateObjectCommandMixin,
    ClickUpdateObjectCommandMixin,
    ClickDeleteObjectCommandMixin,
    ClickSSHObjectCommandMixin,
    ClickRunCommandCommandMixin,
    ClickExecObjectCommandMixin,
    ClickTunnelObjectCommandMixin,
    ClickBaseModelAdapter,
):
    pass


class ClickSecretsAdapter(
    ClickObjectSecretsDiffCommandMixin,
    ClickObjectSecretsShowCommandMixin,
    ClickObjectSecretsWriteCommandMixin,
    ClickObjectSecretsExportCommandMixin,
    ClickSyncSecretsCommandMixin,
    SecretsExportMixin,
    ClickBaseModelAdapter,
):

    @classmethod
    def add_command_group(cls, parent, name=None, short_help=None):
        if not short_help:
            short_help = "Manage AWS SSM Parameter Store secrets for a {}".format(cls.model.__name__)
        return super(ClickSecretsAdapter, cls).add_command_group(parent, name=name, short_help=short_help)
