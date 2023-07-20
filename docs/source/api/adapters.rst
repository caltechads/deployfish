Adapters and Models
===================

Adapters: Loading a Model from configuration in deployfish.yml
--------------------------------------------------------------

Classes derived from :py:class:`deployfish.core.models.abstract.Model` can be configured
from configuration in ``deployfish.yml``.

#. Extract the configuration stanza for your object from deployfish.yml::

   item_config = Config.get_section_item('my_section_name', 'my_item_name')

#. Generate your configued Model subclass instance by doing::

   instance = MyModel.new(item_config, 'deployfish')

``MyModel.new()`` does this:

#. Find the proper :py:class:`deployfish.core.adapter.abstract.Adapter` subclass that
   will translate between ``item_config`` and properly configured ``data`` for
   ``MyModel`` by looking in the adapter registry
   :py:data:`deployfish.registry.importer_registry`.  This registry maps ``Adapter``
   subclasses to :py:class:`deployfish.core.models.abstract.Model` subclasses.
#. Instantiate the ``Adapter`` subclass, passing in our ``item_config`` to its constructor.
#. Run ``MyAdapter.convert()``.  This will generate ``data``, a dict formatted
   to look like what boto3's ``describe_*`` API method would return for the
   ``MyModel``, and ``kwargs``, extra configuration ``MyModel`` may need in order
   to function properly.
#. Instantiate a ``MyModel`` by doing::

   instance = MyModel.__init__(data)

#. Set any other necessary attributes on ``instance`` from the data we returned
   above in ``kwargs``.

.. note::

    One of the challenges we have in constructing ``MyModel`` from
    ``deployfish.yml`` is that we need to ensure we can also load ``MyModel``
    purely from AWS calls.  When loading an object from AWS , we want any
    dependent objects (e.g. the
    :py:class:`deployfish.core.models.ecs.TaskDefinition` of a
    :py:class:`deployfish.core.models.ecs.Service`) to be lazy loaded from AWS
    in order to reduce the API calls to only the data we need at the moment --,
    this saves the user from having to wait too long.

    When loading an object from ``deployfish.yml`` however, we load all the
    dependent objects at the same time have to provide them to the ``Model``
    instance all at once, with no lazy loading.

    Largely we do this with ``@property`` and ``@property.setter`` decorators.
    The main ``@property`` loads the data from AWS if necessary, while the
    ``@property.setter`` circumvents the AWS loading.

#. Create a subclass of :py:class:`deployfish.core.adapters.abstract.Adapter`
   The ``.__init__()`` for your subclass will get passed the ``deployfish.yml``
   configuration for your object, and will store it as
   :py:attr:`deployfish.core.adapters.abstract.Adapter.data`. Override
   :py:meth:`deployfish.core.adapters.abstract.Adapter.convert` on that subclass
   to use `self.data` to generate `data`, a dict that replicates what boto3
   would return were we to call the `describe_*` method for that object, and
   `kwargs`, keyword arguments for the object's `.new()` factory method
   (described below)

...

Example: Loading a Service from deployfish.yml
----------------------------------------------

First create all the appropriate objects from the service config in
``deployfish.yml``.

The ``Adapter`` that handles parsing the ``services:`` entry for your service is
:py:class:`deployfish.core.adapters.deployfish.ServiceAdapter`.  It does this,
in this order:

#. Build the data necessary for the ``data`` parameter to
   #:py:meth:`deployfish.core.models.ecs.Service.__init__` from the service's config.
#. If a ``config:`` section is present in the service's config, load the list of
   :py:class:`deployfish.core.models.secrets.Secret` objects from the service's
   ``config:`` section via
   :py:class:`deployfish.core.adapters.deployfish.SecretAdapter` and possibly
   :py:class:`deployfish.core.adapters.deployfish.ExternalSecretAdapter`.
#. Use :py:class:`deployfish.core.adapters.deployfish.TaskDefinitionAdapter`` to
   create a :py:class:`deployfish.core.models.ecs.TaskDefinition` from the service
   config.  This needs the secrets we created above, if any.
#. If ``application_scaling:`` section is present in the service's config, build
   the Application Scaling objects, which are:

   * :py:class:`deployfish.core.models.appscaling.ScalableTarget`` (from
     :py:class:`deployfish.core.adapters.appscaling.ECServiceScalableTargetAdapter`)
   * One or more :py:class:`deployfish.core.models.appscaling.ScalingPolicy`
     objects (via :py:class:`deployfish.core.adapters.appscaling.ECServiceScalingPolicyAdapter`)
   * One :py:class:`deployfish.core.models.cloudwatch.CloudwatchAlarm` per
     :py:class:`deployfish.core.models.appscaling.ScalingPolicy`` (via
     :py:class:`deployfish.core.adapters.cloudwatch.ECServiceCPUAlarmAdapter`)

#. If a ``service_discovery:`` section is present in the service's config, build
   a :py:class:`deployfish.core.models.service_discovery.ServiceDiscoveryService`
   object (via
   :py:class:`deployfish.core.adapters.service_discovery.ServiceDiscoveryServiceAdapter`).
#. If a ``tasks:`` section is present in the service's config, build
   configuration for one or more
   :py:class:`deployfish.core.models.ecs.ServiceHelperTask` objects (via
   :py:class:`deployfish.core.adapters.ecs.ServiceHelperTaskAdapter`, but
   (**important**) loaded in :py:meth:`deployfish.core.models.ecs.Service.new`, not in
   :py:meth:`deployfish.core.adapters.ecs.ServiceAdapter.convert` -- we need the
   fully configured ``Service`` object in order to make the helper tasks, and
   that doesn't happen until we get into ``Service.new()``.

Finally the ``Service`` object is configured.

Creating a Service
------------------

Here's how :py:meth:`deployfish.core.models.ecs.Service.save` works when creating a service:

* If we have any :py:class:`deployfish.core.models.ecs.ServiceHelperTask`
  objects, create them in AWS and save their
  ``family:revisions`` on our
  :py:class:`deployfish.core.models.ecs.TaskDefinition`, so that we know which
  specific revision to run to get the version of the code we want.
* Create the :py:class:`deployfish.core.models.ecs.TaskDefinition` in AWS, and
  save its ARN to the ``Service`` as ``taskDefinition``
* If we need it, create the
* :py:class:`deployfish.core.models.service_discovery.ServiceDiscoveryService`
  in AWS, and save its ARN to the service as
  ``serviceRegistries[0]['registryArn']``; otherwise delete any
  ``ServiceDiscoveryService`` associated with the ``Service``.
* Create the ``Service`` in AWS
* If we need it, create the ``ScalingTarget``, ``ScalingPolicy`` and
  ``CloudwatchAlarm`` objects in AWS, otherwise delete any such that exist in AWS

