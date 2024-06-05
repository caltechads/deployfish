.. _api_architecture:

Architecture
============

We are using ``cement`` for the CLI, ``click`` for the colorful outputs, and ``jinja2`` for templates.

:py:mod:`deployfish.main`
    Our :py:class:`deployfish.main.DeployfishApp` class is a subclass of `cement.App` and is responsible for setting up
    the application. You'll find configurations for extensions, templates, handlers, hooks, etc.

:py:mod:`deployfish.config`

    :py:meth:`deployfish.config.set_app` saves the :py:class:`deployfish.main.DeployfishApp` instance in the
    ``MAIN_APP``.

    :py:meth:`deployfish.config.get_config` returns :py:meth:`deployfish.config.DeployfishConfig.deployfish_config`,
    which returns the :py:class:`deployfish.config.Config` object. It's usually used to access the ``deployfish.yml``
    configurations.

    :py:class:`deployfish.config.Config` is provides access to the raw data from ``deployfish.yml`` and the interpolated
    data as `dict`.

:py:mod:`deployfish.controllers`

    In cement, the controllers are responsible for running the commands. They call the appropriate methods in the
    models, which create the appropriate models. They are registered as handlers in
    :py:data:`deployfish.main.DeployfishApp.handlers`. When ``app.run()`` is called, ``DeployfishApp`` will forward the
    controls to the first controller listed in ``handlers``. All controllers will have access to ``DeployfishApp``
    through its own ``app`` attribute. To expose commands using ``@ex`` decorator for the controller's methods. The
    commands will render results using the ``app.render`` method and will need context data and template paths.

    .. note::

        For rendering templates, our models will have ``render`` methods to

    Additional info can be found at `cement controllers overview`_ and `cement controllers`_.

    .. note::

        We subclass :py:meth:`cement.ext.ext_arparse.ArgparseController`, which is the default ``Controller`` class in
        cement, so that we can override the help messages for sub commands for controllers.

    Besides commands, controllers will contain settings for ``model``, ``loader``, and template rendering settings.

    The commands in controllers are what calls their repective loaders to get their models. These models can be built
    based on the data from the ``deployfish.yml`` file or from AWS.

:py:mod:`deployfish.core.loaders`

    Loaders are responsible for creating models from AWS or from a ``deployfish.yml`` file. They are registered with a
    controller and called within commands. Loader will create the model and return it to the controller.

    :py:meth:`deployfish.core.loaders.ObjectLoader.get_object_from_aws` is the method that creates the model from AWS.

    :py:meth:`deployfish.core.loaders.ObjectLoader.get_object_from_deployfish` is the method that creates the model
    from the ``deployfish.yml`` file. It specifically uses ``Model.new`` to pass data from ``deployfish.yml`` to the
    model.

    :py:meth:`deployfish.core.loaders.ObjectLoader.factory` returns the model needed for
    ``get_object_from_deployfish``. If model does not get passed in, it will use the model set in the associated
    controller. The ``factory`` will extract the specific data from ``deployfish_config`` and pass it to ``Model.new``
    and return it.

:py:mod:`deployfish.core.models`

    Models will contain the data and methods needed to interact with AWS. On creation, loaders will pass in data either
    from AWS or from the ``deployfish.yml`` file. ``Model.new`` will pass that data to its adapter through the
    ``adapt`` class method, which will return the data needed to create the model. The ``new`` method will then return
    the model by providing ``Model.__init__`` with the data from the adapter. Usually this means that ``data`` gets
    stored in the model's own ``data`` attribute.

    When models are created, the ``Model.objects`` attribute is assigned a subclass of
    :py:class:`deployfish.core.models.abstract.Manager` class, that will help with managing the model instance.
    Managers will have methods like ``save`` and ``delete`` that will interact with AWS, and they will also have
    methods like ``list`` that will return the model instances.

    .. note::

        Check if there are overrides to the ``save`` method for individual models that change how they save.

    Models will also have various ``render`` methods to organize and curate data for template display purposes or
    saving to AWS.

:py:mod:`deployfish.core.adapters`

    Adapters are responsible for creating the data needed to create models. They are used in the ``Model.new`` method.
    The meat of the adapter can be found in subclasses of ``Adapter.convert`` method (which should always be overrided).

    Please read the :doc:`adapters` documentation to get an idea of how ``deployfish.yml`` gets translated to models.
    Examples are also given in the documentation.


.. _`cement controllers overview`: https://docs.builtoncement.com/getting-started/framework-overview#controllers
.. _`cement controllers`: https://docs.builtoncement.com/core-foundation/controllers
