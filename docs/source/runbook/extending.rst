Extending deployfish
====================

``deployfish`` has a modular architecture that allows you to add subcommands that have access to the internal objects
through the ``deployfish`` library. Please read the `Cement: Application Plugins`_ for an overview. As an example, you
can look at `deployfish-mysql`_.

Below, we'll do a generic overview of how to create a plugin for ``deployfish``, and will assume that you'll be
creating one for an AWS resource which will require an adapter, a controller, and a model to interact with the resource.
Feel free to also just checkout `deployfish-mysql`_, which is a working example.


Creating a plugin
-----------------

Make sure you have `cement`_ installed:

.. code-block:: bash

    pip install cement

Create a new Python package for your plugin:

.. code-block:: bash

    cement generate plugin /path/to/myplugin

Once it's installed, you will need to create a similar directory structure to
match the `deployfish` package:

.. code-block:: bash

    myplugin/
    ├── adapters/
    |   ├── deployfish/
    |   │   ├── __init__.py
    |   │   ├── myplugin.py
    │   ├── __init__.py
    ├── controllers/
    │   ├── __init__.py
    │   └── myplugin.py
    ├── models/
    │   ├── __init__.py
    │   ├──  myplugin.py
    └── templates/
    │   ├── __init__.py
    │   ├── detail--myplugin.jinja2
    ├── __init__.py
    ├── hooks.py
    ├── README.md
    └── requirements.txt

.. note::

    By default, the plugin templates will be placed inside it's own plugin directory. In our example, we're placing the
    templates in the ``myplugin/templates`` directory instead. This path is set in the controller when we setup the
    ``jinja2_env``.

Now you can start adding your plugin's adapters, controllers, models, and templates.


Add an adapter
--------------

Inherit from :py:class:`deployfish.core.adapters.abstract.Adapter` and implement the `convert` method. This method should return a tuple with the data and kwargs that will be passed to the controller to create the object.

.. code-block:: python
    :caption: myplugin/adapters/deployfish/myplugin.py

    from copy import deepcopy

    from deployfish.core.adapters.abstract import Adapter


    class MyPluginAdapter(Adapter):

        def convert(self):
            data = deepcopy(self.data)
            kwargs = {}
            return data, kwargs

Register the adapter with deployfish:

.. code-block:: python
    :caption: myplugin/adapters/deployfish/__init__.py

    from deployfish.registry import importer_registry as registry

    from .myplugin import MyPluginAdapter

    registry.register('MyPlugin', 'deployfish', MyPluginAdapter)


Add a model and manager
-----------------------

The model handles the data while the manager handles the interaction with the AWS API. Model actions that relate to the AWS API should be passed to the manager.

.. code-block:: python
    :caption: myplugin/models/myplugin.py

    import os
    import tempfile
    from typing import Optional, Sequence, Tuple, List, cast

    from deployfish.config import get_config
    from deployfish.core.models import Manager, Model

    class MyPluginManager(Manager):
        """
        Manager should reflect what commands you'll be running against the AWS API.
        """

        def get(self, pk: str, **_) -> Model:
            pass

        def list(self, **_) -> List[Model]:
            pass

        def save(self, pk: str, **_) -> bool:
            pass

        def delete(self, pk: str, **_) -> bool:
            pass

    class MyPlugin(Model):
        """
        Model should be aware of the data structure used by the AWS API.
        """

        objects = MyPluginManager()
        config_section: str = 'myplugin'

        def create(self, **_) -> str:
            pass

        def save(self, **_) -> str:
            pass

        def update(self, **_) -> str:
            pass

        def delete(self, **_) -> str:
            pass

        def render(self) -> Dict[str, Any]:
            pass

        def render_for_display(self) -> Dict[str, Any]:
            pass

        def render_for_diff(self) -> Dict[str, Any]:
            pass

        ...


Add a controllers
-----------------

See :doc:`../api/controllers/index` to pick one to inherit from.

.. code-block:: python
    :caption: myplugin/controllers/myplugin.py

    from cement import ex
    import click
    from jinja2 import ChoiceLoader, Environment, PackageLoader

    from deployfish.controllers.crud import ReadOnlyCrudBase
    from myplugin.models.myplugin import MyPlugin

    class MyPluginController(ReadOnlyCrudBase):

        class Meta:
            label = "myplugin"
            description = 'Work with MyPlugin'
            help = 'Work with MyPlugin'
            stacked_type = 'nested'

        model: Type[Model] = MyPlugin

        help_overrides: Dict[str, str] = {
            'exists': 'Show whether a MyPlugin exists in deployfish.yml',
            'list': 'List available MyPlugin from deployfish.yml',
        }

        info_template: str = 'detail--myplugin.jinja2'

        list_ordering: str = 'Name'
        list_result_columns: Dict[str, Any] = {
            'Name': 'name',
        }

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # Set up Jinja2 environment with a ChoiceLoader to load templates from the main application and the plugin
            self.jinja2_env = Environment(
                loader=ChoiceLoader([
                    PackageLoader('deployfish', 'templates'),       # Load templates from the main application
                    PackageLoader('myplugin', 'templates')          # Load templates from the plugin
                ])
            )
            # Import the color and section_title filters from deployfish.ext.ext_df_jinja2 in order to render the templates
            self.jinja2_env.filters['color'] = color
            self.jinja2_env.filters['section_title'] = section_title

        @ex(
            help='Show details about a MyPlugin.',
            arguments=[
                (['pk'], {'help': 'the name of the MyPlugin in deployfish.yml'})
            ],
        )
        @handle_model_exceptions
        def info(self) -> None:
            """
            Show details about a MyPlugin in AWS.
            """
            loader = self.loader(self)
            obj = loader.get_object_from_aws(self.app.pargs.pk)
            # Use the Jinja2 environment to render the template rather than the default Cement renderer that only takes
            # a local template name
            template = self.jinja2_env.get_template(self.info_template)
            self.app.print(template.render(obj=obj))

.. important::

    I order to use macros from the main application, we need to be able to read them. In ``__init__`` method, We set up
    ``jinja2_env`` to with ``ChoiceLoader`` so that Deployfish knows to look for templates in both the main and plugin
    application with their respective ``PackageLoader``.

    Then we need to use this ``jinja2_env`` to render the template in the ``info`` method instead of Deployfish's
    default renderer. This is because ``DeployfishJinja2TemplateHandler`` uses a single ``PackageLoader``, which it inherits from Cement's ``Jinja2TemplateHandler``.

    Since the ``jinja2_env`` is separate from the app's default renderer, your can configure the environment however you want to render your templates. See the `jinja2 API`_ for more information.

.. note::

    We import ``click`` to print coloful outputs for some of our commands. Usage is up to you.


Update template
---------------

In the controller above, we've set the ``info_template`` to ``detail--myplugin.jinja2``. This template should be placed
in the ``myplugin/templates`` directory due to how we setup ``jinja2_env`` in the controller. Edit it however you want
to display the details of the object.


Add a hook
----------

Add our plugin as a processable section when reading in the ``deployfish.yml`` file.

.. code-block:: python
    :caption: myplugin/hooks.py

    from typing import Type, TYPE_CHECKING

    from cement import App

    if TYPE_CHECKING:
        from deployfish.config import Config


    def pre_config_interpolate_add_myplugin_section(app: App, obj: "Type[Config]") -> None:
        """
        Add our "myplugin" section to the list of sections on which keyword interpolation
        will be run

        Args:
            app: our cement app
            obj: the :py:class:`deployfish.config.Config` class
        """
        obj.add_processable_section('myplugin')

Make sure to load it too:

.. code-block:: python
    :caption: myplugin/__init__.py

    import os

    from cement import App

    import myplugin.adapters  # noqa:F401

    from .controllers.myplugin import MyPluginController
    from .hooks import pre_config_interpolate_add_myplugin_section

    __version__ = "0.0.1"


    def add_template_dir(app: App):
        path = os.path.join(os.path.dirname(__file__), 'templates')
        app.add_template_dir(path)


    def load(app: App) -> None:
        app.handler.register(MyPluginController)
        app.hook.register('post_setup', add_template_dir)
        app.hook.register('pre_config_interpolate', pre_config_interpolate_add_myplugin_section)


Install your plugin
-------------------

.. code-block:: bash

    pip install -e /path/to/myplugin


Loading your plugin
-------------------

To load your plugin into deployfish, update or create a ``~/.deployfish.yml`` file with the following content:

.. code-block:: yaml

    plugin.myplugin:
      enabled: true

.. note::

    If you look at our :py:class:`deployfish.main.DeployfishApp.Meta` you'll see ``config_file_suffix = '.yml'`` and ``config_handler = 'yaml'``. Cement will know to look for ``~/.deployfish.yml`` and parse it as YAML.

    Our :py:class:`deployfish.ext.ext_df_plugin.DeployfishCementPluginHandler` will look for any keys that start with ``plugin.`` and look for ``enabled``. If it's set to ``true``, it will load the plugin.


.. _`cement`: https://github.com/datafolklabs/cement
.. _`Cement\: Application Plugins`: https://docs.builtoncement.com/core-foundation/plugins
.. _`deployfish-mysql`: https://github.com/caltechads/deployfish-mysql
.. _`jinja2 API`: https://jinja.palletsprojects.com/en/3.0.x/api/
