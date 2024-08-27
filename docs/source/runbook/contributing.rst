.. _contributing:

Contributing
============

Contributions are welcome, and they are greatly appreciated!


Instructions for contributors
-----------------------------

To contribute to this project, please follow these instructions:

1. Fork the repository on GitHub by navigating to the project's repository page and clicking on the "Fork" button in the top-right corner.

2. Clone your forked repository to your local machine using the following command:

    .. code-block::

        git clone git@github.com:your-username/deployfish.git

    Replace ``your-username`` with your GitHub username.

3. Change into the project's directory:

    .. code-block::

        cd deployfish

4. Install the project with ``pip``:

    .. code-block::

        pip install -e .

    After that, you can make changes to the code and run deployfish commands in another project like normal.


You are now ready to contribute to the project! Make your changes, commit them, and push them to your forked repository. Finally, open a pull request on the original repository to submit your contributions for review.


Where to start contributing
----------------------------

Take a look at :doc:`architecture` and :doc:`adapters` to get an idea how deployfish is structured. A good understanding of `cement`_ and `jinja2`_ are also recommended.


Adding support for a resource attribute
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Resource attributes need to be explicitly supported for them to be properly read from the ``deployfish.yml`` file and
saved into the appropriate AWS resource.

Adding a new attribute will require updating the ``convert`` method for the resource's Adapter class to properly read
the new attribute from your ``deployfish.yml`` file when present.

You will also need to update various render methods to utilize the new attribute. The ``render`` method is
called by other render methods, which you'll need to check what gets overriden within the resource Model class:

* ``render_for_display``
* ``render_for_diff``
* ``render_for_create``
* ``render_for_update``

Make sure to update the attribute appropriately in the render methods and related jinja2 templates to properly save, compute, or display the new attributes.

To make sure that you're saving the values correctly, you can check the data being passed during ``save`` and ``update`` methods in the resource's Model class. The data from the model is usually then passed to the Manager class
where ``boto3`` is used to save or update the resource in AWS.

Then finally, using your test environment, try updating and checking on AWS if the resource was appropriately updated.


Adding a new command
^^^^^^^^^^^^^^^^^^^^

Commands for AWS resources are implemented by subclassing `cement`_'s controllers. However commands can also be done by creating an extensions, like we do for `deployfish-mysql`_ so that if others want to support other databases, they can use that as an example.


Adding command to deployfish
""""""""""""""""""""""""""""

For a supported resource in deployfish, a new method can just be added to their controller and use the ``@ex`` decorator to expose it.

For a new resource, it'll be more extensive, as you'll need to create a new controller, a new adapter, model, and manager.

* Controller should inherit from :py:class:`deployfish.ext.ext_df_argparse.DeployfishArgparseController` or one of its
  various subclasses. Some of the basic controllers are:

    * :py:class:`deployfish.controllers.crud.ReadOnlyCrudBase` adds commands: ``exists``, ``info``, and ``list``
    * :py:class:`deployfish.controllers.crud.CrudBase` adds commands to ``ReadOnlyCrudBase``: ``create``, ``update``,
      and ``delete``
    * :py:class:`deployfish.controllers.network.ObjectSSHController` adds commands: ``ssh``, ``run``, and ``list``
    * :py:class:`deployfish.controllers.secrets.ObjectSecretsController` adds commands: ``show``, ``diff``, ``write``,
      and ``export``
    * :py:class:`deployfish.controllers.tunnel.ObjectTunnelController` adds commands: ``tunnel``, ``list``, and ``info``

  See :doc:`../api/controllers/index` for the full list of available controllers to determine if anything can be used.

  You'll likely want to make changes to ``help_overrides`` so that the inherited descriptions are updated to state what resource you're controller manipulating.

  Add your commands to the controller using the ``@ex`` decorator and print some sort of response. You can use ``click``
  for colorful echoes or reuse some of the available macros if rendering a jinja2 template.

* Adapter should inherit from :py:class:`deployfish.core.adapters.abstract.Adapter` and convert must be implemented to
  convert to return a data structure that can be used by the model. To look up the acceptable data structure, look up
  for the applicable ``describe_*`` method in the `boto3 documentation`_ and see what the response syntax contains.
* Register the new adapter in :py:mod:`deployfish.core.adapters.deployfish.__init__`
* Model should inherit from :py:class:`deployfish.core.models.abstract.Model`, which will make ``adapters`` attribute
  and ``adapt`` method available to the model and run them in ``new`` to return the model instance.

  .. note::

    ``Model.new()`` is only called by ``ObjectLoader`` classes, specifically when ``get_object_from_deployfish``
    method, which calls ``factory``.

  This is where you do all the data manipulation you need for various commands you'll be implementing.


.. _`boto3 documentation`: https://boto3.amazonaws.com/v1/documentation/api/latest/index.html
.. _`cement`: https://docs.builtoncement.com/
.. _`deployfish-mysql`: https://github.com/caltechads/deployfish-mysql
.. _`jinja2`: https://readthedocs.org/projects/jinja/
.. _`pyenv`: https://github.com/pyenv/pyenv
