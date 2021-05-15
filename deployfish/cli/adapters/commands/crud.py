import click

from deployfish.config import get_config
from deployfish.exceptions import RenderException, ConfigProcessingFailed
from deployfish.typing import FunctionTypeCommentParser

from deployfish.cli.adapters.utils import handle_model_exceptions, print_render_exception
from deployfish.cli.renderers import (
    TableRenderer,
    JSONRenderer,
    TemplateRenderer
)


# Command mixins
# ====================

class ClickListObjectsCommandMixin(object):

    list_ordering = None
    list_result_columns = {}
    list_renderer_classes = {
        'table': TableRenderer,
        'json': JSONRenderer
    }

    @classmethod
    def list_display_option_kwargs(cls):
        """
        Return the appropriate kwargs for `click.option('--display', **kwargs)` for the renderer options we've defined
        for the list endpoint.

        :rtype: dict
        """
        render_types = list(cls.list_renderer_classes.keys())
        default = render_types[0]
        kwargs = {
            'type': click.Choice(render_types),
            'default': default,
            'help': "Render method for listing {} objects. Choices: {}.  Default: {}.".format(
                cls.model.__name__,
                ', '.join(render_types),
                default
            )
        }
        return kwargs

    @classmethod
    def add_list_click_command(cls, command_group):
        """
        Build a fully specified click command for listing objects, and add it to the click command group
        `command_group`.  Return the properly wrapped function object.

        :param command_group function: the click command group function to use to register our click command

        :rtype: function
        """
        def list_objects(ctx, *args, **kwargs):
            if cls.model.config_section is not None:
                try:
                    ctx.obj['config'] = get_config(**ctx.obj)
                except ConfigProcessingFailed as e:
                    ctx.obj['config'] = e
            ctx.obj['adapter'] = cls()
            display = kwargs.pop('display')
            click.secho(ctx.obj['adapter'].list(display, **kwargs))
        args, kwargs = FunctionTypeCommentParser().parse(cls.model.objects.list)
        list_objects.__doc__ = """
List {object_name} objects in AWS, possibly with filters.
""".format(
            object_name=cls.model.__name__,
            required_args=cls.get_required_args(args),
            command_group_name=command_group.name
        )

        function = print_render_exception(list_objects)
        function = click.pass_context(function)
        for key, kwarg in kwargs.items():
            function = cls.add_option(key, kwarg, function)
        function = click.option('--display', **cls.list_display_option_kwargs())(function)
        for key, arg in args.items():
            function = cls.add_argument(key, arg, function)
        function = command_group.command(
            'list',
            short_help='List {object_name} objects in AWS, possibly with filters.'.format(
                object_name=cls.model.__name__
            )
        )(function)
        return function

    @handle_model_exceptions
    def list(self, display, **kwargs):
        assert display in self.list_renderer_classes, \
            '{}.list(): "{}" is not a valid list rendering option'.format(
                self.__class__.__name__,
                display
            )
        results = self.model.objects.list(**kwargs)
        if not results:
            return('No results.')
        else:
            if display == 'table':
                results = self.list_renderer_classes[display](
                    self.list_result_columns,
                    ordering=self.list_ordering
                ).render(results)
            else:
                results = self.list_renderer_classes[display]().render(results)
            results = '\n' + results + '\n'
            return results


class ClickObjectInfoCommandMixin(object):

    info_includes = []
    info_excludes = []
    info_renderer_classes = {
        'detail': TemplateRenderer,
        'json': JSONRenderer,
    }

    @classmethod
    def info_display_option_kwargs(cls):
        """
        Return the appropriate kwargs for `click.option('--display', **kwargs)` for the renderer options we've defined
        for the retrieve endpoint.

        :rtype: dict
        """
        render_types = list(cls.info_renderer_classes.keys())
        default = render_types[0]
        kwargs = {
            'type': click.Choice(render_types),
            'default': default,
            'help': "Choose how to display a single {} object. Choices: {}.  Default: {}.".format(
                cls.model.__name__,
                ', '.join(render_types),
                default
            )
        }
        return kwargs

    @classmethod
    def info_include_option_kwargs(cls):
        kwargs = {
            'type': click.Choice(cls.info_includes),
            'help': "Detail view only: Include optional information not normally shown. Choices: {}.".format(
                ', '.join(cls.info_includes),
            ),
            'default': None,
            'multiple': True
        }
        return kwargs

    @classmethod
    def info_exclude_option_kwargs(cls):
        kwargs = {
            'type': click.Choice(cls.info_excludes),
            'help': "Detail view only: Exclude information normally shown. Choices: {}.".format(
                ', '.join(cls.info_excludes),
            ),
            'default': None,
            'multiple': True
        }
        return kwargs

    @classmethod
    def add_info_click_command(cls, command_group):
        """
        Build a fully specified click command for retrieving single objects, and add it to the click command group
        `command_group`.  Return the function object.

        :param command_group function: the click command group function to use to register our click command

        :rtype: function
        """
        def retrieve_object(ctx, *args, **kwargs):
            if cls.model.config_section is not None:
                try:
                    ctx.obj['config'] = get_config(**ctx.obj)
                except ConfigProcessingFailed:
                    pass
            ctx.obj['adapter'] = cls()
            click.secho(ctx.obj['adapter'].info(
                kwargs['identifier'],
                kwargs['display'],
                kwargs.get('include', None),
                kwargs.get('exclude', None)
            ))

        args, kwargs = FunctionTypeCommentParser().parse(cls.model.objects.get)
        pk_description = cls.get_pk_description()
        retrieve_object.__doc__ = """
Show info about a {object_name} object that exists in AWS.

{pk_description}

""".format(pk_description=pk_description, object_name=cls.model.__name__)

        function = print_render_exception(retrieve_object)
        function = click.pass_context(function)
        if cls.info_includes:
            function = click.option('--include', **cls.info_include_option_kwargs())(function)
        if cls.info_excludes:
            function = click.option('--exclude', **cls.info_exclude_option_kwargs())(function)
        function = click.option('--display', **cls.info_display_option_kwargs())(function)
        function = click.argument('identifier')(function)
        function = command_group.command(
            'info',
            short_help='Show info for a single {} object in AWS'.format(cls.model.__name__)
        )(function)
        return function

    @handle_model_exceptions
    def info(self, pk, display, include, exclude, **kwargs):
        if include is None:
            include = []
        if exclude is None:
            exclude = []
        assert display in self.info_renderer_classes, \
            '{}.info(): "{}" is not a valid rendering option'.format(
                self.__class__.__name__,
                display
            )
        obj = self.get_object_from_aws(pk)
        context = {
            'includes': include,
            'excludes': exclude
        }
        return '\n' + self.info_renderer_classes[display]().render(obj, context=context) + '\n'


class ClickObjectExistsCommandMixin(object):

    @classmethod
    def add_exists_click_command(cls, command_group):
        """
        Build a fully specified click command for determining object exists in AWS, and add it to the click command
        group `command_group`.  Return the function object.

        :param command_group function: the click command group function to use to register our click command

        :rtype: function
        """
        def object_exists(ctx, *args, **kwargs):
            if cls.model.config_section is not None:
                try:
                    ctx.obj['config'] = get_config(**ctx.obj)
                except ConfigProcessingFailed:
                    pass
            ctx.obj['adapter'] = cls()
            click.secho(ctx.obj['adapter'].exists(kwargs['identifier']))

        args, kwargs = FunctionTypeCommentParser().parse(cls.model.objects.exists)
        pk_description = cls.get_pk_description()
        object_exists.__doc__ = """
Determine whether a {object_name} object exists in AWS or not.

{pk_description}

""".format(pk_description=pk_description, object_name=cls.model.__name__)

        function = print_render_exception(object_exists)
        function = click.pass_context(function)
        function = click.argument('identifier')(function)
        function = command_group.command(
            'exists',
            short_help='Show whether a {} object exists in AWS'.format(cls.model.__name__)
        )(function)
        return function

    @handle_model_exceptions
    def exists(self, pk,  **kwargs):
        try:
            self.get_object_from_aws(pk)
        except self.model.DoesNotExist:
            return click.style('{}(pk="{}") does not exist in AWS.'.format(self.model.__name__, pk), fg='red')
        else:
            return click.style('{}(pk="{}") exists in AWS.'.format(self.model.__name__, pk), fg='green')


class ClickCreateObjectCommandMixin(object):

    @classmethod
    def add_create_click_command(cls, command_group):
        """
        Build a fully specified click command for creating objects, and add it to the click command group
        `command_group`.  Return the function object.

        :param command_group function: the click command group function to use to register our click command

        :rtype: function
        """
        if cls.model.config_section is None:
            raise cls.ReadOnly(
                '{} objects are read only. If you want them to be read/write, define the '
                '"config_section" class attribute on the model to be the section in deployfish.yml '
                'where configuration info can be found for them.'
            )

        def create_object(ctx, *args, **kwargs):
            try:
                ctx.obj['config'] = get_config(**ctx.obj)
            except ConfigProcessingFailed as e:
                raise RenderException(str(e))
            ctx.obj['adapter'] = cls()
            click.secho(ctx.obj['adapter'].create(kwargs.pop('name')))

        create_object.__doc__ = "Create a new {object_name} in AWS from your deployfish.yml file.".format(
            object_name=cls.model.__name__
        )
        # Wrap our function with the approriate decorators
        function = print_render_exception(create_object)
        function = click.argument('name')(function)
        function = click.pass_context(function)
        function = command_group.command(
            'create',
            short_help='Create a {} object in AWS from configuration info in deployfish.yml'.format(cls.model.__name__)
        )(function)
        return function

    def create_waiter(self, obj, **kwargs):
        pass

    @handle_model_exceptions
    def create(self, name, **kwargs):
        obj = self.get_object_from_deployfish(name, factory_kwargs=self.factory_kwargs.get('create', {}))
        if obj.exists:
            raise RenderException('{}(pk={}) already exists in AWS!'.format(self.model.__name__, obj.pk))
        renderer = TemplateRenderer()
        click.secho('\n\nCreating {}("{}"):\n\n'.format(self.model.__name__, obj.pk), fg='yellow')
        click.secho(renderer.render(obj))
        obj.save()
        self.create_waiter(obj)
        return click.style('\n\nCreated {}("{}").'.format(self.model.__name__, obj.pk), fg='green')


class ClickUpdateObjectCommandMixin(object):

    update_template = None

    @classmethod
    def add_update_click_command(cls, command_group):
        """
        Build a fully specified click command for updating objects from what we have in our deployfish.yml file, and add
        it to the click command group `command_group`.  Return the function object.

        :param command_group function: the click command group function to use to register our click command

        :rtype: function
        """
        if cls.model.config_section is None:
            raise cls.ReadOnly(
                '{} objects are read only. If you want them to be read/write, define the '
                '"config_section" class attribute on the model to be the section in deployfish.yml '
                'where configuration info can be found for them.'
            )

        def update_object(ctx, *args, **kwargs):
            try:
                ctx.obj['config'] = get_config(**ctx.obj)
            except ConfigProcessingFailed as e:
                raise RenderException(str(e))
            ctx.obj['adapter'] = cls()
            click.secho(ctx.obj['adapter'].update(kwargs.pop('identifier')))
        update_object.__doc__ = """
Update an existing a {object_name} object in AWS from what we have in our deployfish.yml file.

IDENTIFIER is a string that looks like one of:

    * {object_name}.name

    * {object_name}.environment
""".format(object_name=cls.model.__name__)

        function = print_render_exception(update_object)
        function = click.pass_context(function)
        function = click.argument('identifier')(function)
        function = command_group.command(
            'update',
            short_help='Update a {} object in AWS from configuration in deployfish.yml'.format(cls.model.__name__)
        )(function)
        return function

    def update_waiter(self, obj, **kwargs):
        pass

    @handle_model_exceptions
    def update(self, identifier, **kwargs):
        obj = self.get_object_from_deployfish(identifier, factory_kwargs=self.factory_kwargs.get('update', {}))
        renderer = TemplateRenderer()
        click.secho('\n\nUpdating {}("{}") to this:\n\n'.format(self.model.__name__, obj.pk), fg='yellow')
        click.secho(renderer.render(obj, template=self.update_template))
        obj.save()
        self.update_waiter(obj)
        return click.style('Updated {}("{}"):'.format(self.model.__name__, obj.pk), fg='cyan')


class ClickDeleteObjectCommandMixin(object):

    @classmethod
    def add_delete_click_command(cls, command_group):
        """
        Build a fully specified click command for deleting objects, and add it to the click command group
        `command_group`.  Return the function object.

        If the model's manager is ReadOnly, raise an exception if someone tries to add this command.

        :param command_group function: the click command group function to use to register our click command

        :rtype: function
        """
        if cls.model.config_section is None:
            raise cls.ReadOnly(
                '{} objects are read only. If you want them to be read/write, define the '
                '"config_section" class attribute on the model to be the section in deployfish.yml '
                'where configuration info can be found for them.'
            )

        def delete_object(ctx, *args, **kwargs):
            try:
                ctx.obj['config'] = get_config(**ctx.obj)
            except ConfigProcessingFailed as e:
                raise RenderException(str(e))
            ctx.obj['adapter'] = cls()
            click.secho(ctx.obj['adapter'].delete(kwargs['identifier']))
        delete_object.__doc__ = """
Delete an existing {object_name} object in AWS.

IDENTIFIER is a string that looks like one of:

    * {object_name}.name

    * {object_name}.environment

""".format(object_name=cls.model.__name__)

        function = print_render_exception(delete_object)
        function = click.pass_context(function)
        function = click.argument('identifier')(function)
        function = command_group.command(
            'delete',
            short_help='Delete a {} object in AWS'.format(cls.model.__name__)
        )(function)
        return function

    def delete_waiter(self, obj, **kwargs):
        pass

    @handle_model_exceptions
    def delete(self, identifier):
        # FIXME: should we just be doing get_object_from_aws here?  Or do we want the deployfish.yml file as
        # an additional hurdle?
        obj = self.get_object_from_deployfish(identifier, factory_kwargs=self.factory_kwargs.get('delete', {}))
        obj.reload_from_db()
        click.secho('\nDeleting {}("{}")\n'.format(self.model.__name__, identifier), fg='red')
        renderer = TemplateRenderer()
        click.secho(renderer.render(obj, style='short'))
        click.echo("\nIf you really want to do this, answer \"{}\" to the question below.\n".format(obj.name))
        value = click.prompt("What {} do you want to delete? ".format(self.model.__name__))
        if value == obj.name:
            obj.delete()
        else:
            return click.style('ABORTED: not deleting {}({}).'.format(self.model.__name__, obj.pk))
        self.delete_waiter(obj)
        return click.style('Deleted {}("{}")'.format(self.model.__name__, identifier), fg='cyan')
