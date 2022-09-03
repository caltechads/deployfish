from typing import Sequence, Type, Optional, Dict, Any

import botocore
from cement import ex, shell
import click

from deployfish.core.models import Model
from deployfish.core.loaders import ObjectLoader
from deployfish.ext.ext_df_argparse import DeployfishArgparseController as Controller
from deployfish.renderers.table import TableRenderer

from .utils import handle_model_exceptions


# ========================
# Controllers
# ========================

class ReadOnlyCrudBase(Controller):

    class Meta:
        label = 'ro-crud-base'

    model: Type[Model] = Model
    loader: Type[ObjectLoader] = ObjectLoader

    # The keys of this dict are method names, and the value is the string
    # with which to replace the "help" string for that method name with
    help_overrides: Dict[str, str] = {}

    # --------------------
    # .info() related vars
    # --------------------
    # Which template should we use when showing .info() output?
    info_template: str = 'detail.jinja2'

    # --------------------
    # .list() related vars
    # --------------------
    # The name of the column HEADER by which to order the output table
    list_ordering: Optional[str] = None
    # Configuration for TableRenderer.  See the help for deployfish.renderers.table.TableRenderer
    # for instructions.
    list_result_columns: Dict[str, Any] = {}

    def _default(self):
        """
        Default action if no sub-command is passed: print the help.
        """
        self.app.args.print_help()

    # Exists

    @ex(
        help='Show whether an object exists in AWS',
        arguments=[
            (['pk'], { 'help' : 'The primary key for the object in AWS'})
        ],
    )
    @handle_model_exceptions
    def exists(self) -> None:
        """
        Show details about a single object in AWS.
        """
        loader = self.loader(self)
        try:
            obj = loader.get_object_from_aws(self.app.pargs.pk)
        except self.model.DoesNotExist:
            click.secho(f'{self.model.__name__}(pk="{self.app.pargs.pk}") does not exist in AWS.', fg='red')
        else:
            click.secho(f'{self.model.__name__}(pk="{obj.pk}") exists in AWS.', fg='green')

    # Info

    @ex(
        help='Show info about an object in AWS',
        arguments=[
            (['pk'], { 'help' : 'The primary key for the object in AWS'})
        ],
    )
    @handle_model_exceptions
    def info(self) -> None:
        """
        Show details about a single object in AWS.
        """
        loader = self.loader(self)
        obj = loader.get_object_from_aws(self.app.pargs.pk)
        self.app.render({'obj': obj}, template=self.info_template)

    # List

    def render_list(self, results: Sequence[Model]) -> None:
        """
        Helper method that renders output from self.list() so that we can override .list() without
        having to re-implement this.


        """
        renderer = TableRenderer(
            columns=self.list_result_columns,
            ordering=self.list_ordering
        )
        self.app.print(renderer.render(results))

    @ex(help='List objects in AWS')
    @handle_model_exceptions
    def list(self):
        """
        List objects in AWS.
        """
        results = self.model.objects.list()
        self.render_list(results)

class CrudBase(ReadOnlyCrudBase):

    class Meta:
        label = 'crud-base'

    model: Type[Model] = Model
    loader: Type[ObjectLoader] = ObjectLoader

    # The keys of this dict are method names, and the value is the string
    # with which to replace the "help" string for that method name with
    help_overrides: Dict[str, str] = {}

    # --------------------
    # .create() related vars
    # --------------------
    # Which template should we use when showing .create() output?
    create_template: str = 'detail.jinja2'
    create_kwargs: Dict[str, Any] = {}

    # --------------------
    # .update() related vars
    # --------------------
    # Which template should we use when showing .update() output?
    update_template: str = 'detail.jinja2'
    update_kwargs: Dict[str, Any] = {}

    # --------------------
    # .update() related vars
    # --------------------
    # Which template should we use when showing .update() output?
    delete_template: str = 'detail.jinja2'
    delete_kwargs: Dict[str, Any] = {}

    def _default(self):
        """
        Default action if no sub-command is passed: print the help.
        """
        self.app.args.print_help()

    def wait(self, operation: str, **kwargs) -> None:
        """
        Build a ``deployfish.core.waiters.HookedWaiter`` for the operation named ``operation`` and with configuration
        ``kwargs``, and then run it.

        ``operation`` can be any waiter operation that boto3 supports for ``self.model`` type objects.
        """
        waiter = self.model.objects.get_waiter(operation)
        waiter.wait(**kwargs)


    # Create

    def create_waiter(self, obj: Model, **_):
        pass

    @ex(
        help="Create an object in AWS",
        arguments=[
            (['name'], {'help': 'The name of the item from deployfish.yml'})
        ]
    )
    @handle_model_exceptions
    def create(self):
        """
        Create an object in AWS from configuration in deployfish.yml.
        """
        loader = self.loader(self)
        obj = loader.get_object_from_deployfish(
            self.app.pargs.name,
            factory_kwargs=self.create_kwargs
        )
        if obj.exists:
            self.app.print(
                click.style('{}(pk={}) already exists in AWS!'.format(self.model.__name__, obj.pk), fg='red')
            )
            return
        for _ in self.app.hook.run('pre_object_create', self.app, obj):
            pass
        click.secho('\n\nCreating {}("{}"):\n\n'.format(self.model.__name__, obj.pk), fg='yellow')
        self.app.render({'obj': obj}, template=self.create_template)
        obj.save()
        try:
            self.create_waiter(obj)
        except botocore.exceptions.WaiterError as e:
            for _ in self.app.hook.run('post_object_create', self.app, obj, success=False, reason=e.kwargs['reason']):
                pass
            raise
        else:
            for _ in self.app.hook.run('post_object_create', self.app):
                pass
        self.app.print(click.style('\n\nCreated {}("{}").'.format(self.model.__name__, obj.pk), fg='green'))

    # Update

    def update_waiter(self, obj: Model, **_):
        pass

    @ex(
        help="Update an object in AWS",
        arguments=[
            (['name'], {'help': 'The name of the item from deployfish.yml'})
        ]
    )
    @handle_model_exceptions
    def update(self):
        """
        Update an object in AWS from configuration in deployfish.yml.
        """
        loader = self.loader(self)
        obj = loader.get_object_from_deployfish(
            self.app.pargs.name,
            factory_kwargs=self.update_kwargs
        )
        self.app.print(
            click.style('\n\nUpdating {}("{}") to this:\n\n'.format(self.model.__name__, obj.pk), fg='yellow')
        )
        self.app.render({'obj': obj}, template=self.update_template)
        obj.save()
        try:
            self.update_waiter(obj)
        except botocore.exceptions.WaiterError as e:
            for _ in self.app.hook.run('post_object_update', self.app, obj, success=False, reason=e.kwargs['reason']):
                pass
            raise
        else:
            for _ in self.app.hook.run('post_object_update', self.app):
                pass
        self.app.print(click.style('\n\nUpdated {}("{}").'.format(self.model.__name__, obj.pk), fg='green'))

    # Delete

    def delete_waiter(self, obj: Model, **_):
        pass

    @ex(
        help="Delete an object from AWS",
        arguments=[
            (['name'], {'help': 'The name of the item from deployfish.yml'})
        ]
    )
    @handle_model_exceptions
    def delete(self):
        """
        Delete an object from AWS by primary key.
        """
        loader = self.loader(self)
        obj = loader.get_object_from_deployfish(
            self.app.pargs.name,
            factory_kwargs=self.delete_kwargs
        )
        obj.reload_from_db()
        self.app.print(click.style('\nDeleting {}("{}")\n'.format(self.model.__name__, obj.pk), fg='red'))
        self.app.render({'obj': obj}, template=self.delete_template)
        self.app.print("\nIf you really want to do this, answer \"{}\" to the question below.\n".format(obj.name))
        p = shell.Prompt("What {} do you want to delete? ".format(self.model.__name__))
        value = p.prompt()
        if value == obj.name:
            obj.delete()
        else:
            self.app.print(click.style('ABORTED: not deleting {}({}).'.format(self.model.__name__, obj.pk)))
        try:
            self.delete_waiter(obj)  # type: ignore
        except botocore.exceptions.WaiterError as e:
            for _ in self.app.hook.run('post_object_delete', self.app, obj, success=False, reason=e.kwargs['reason']):
                pass
            raise
        else:
            for _ in self.app.hook.run('post_object_delete', self.app):
                pass
        self.app.print(click.style('Deleted {}("{}")'.format(self.model.__name__, obj.pk), fg='cyan'))
