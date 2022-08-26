Loading a Model from configuration in deployfish.yml
----------------------------------------------------

Classes derived from `deployfish.core.models.abstract.Model` can be configured from configuration in deployfish.yml.

1. Extract the configuration stanza for your object from deployfish.yml::

   item_config = Config.get_section_item('my_section_name', 'my_item_name')

2. Generate your configued Model subclass instance by doing::

   instance = MyModel.new(item_config, 'deployfish')

``MyModel.new()`` does this:

1. Find the proper ``deployfish.core.adapter.abstract.Adapter`` subclass that will translate between ``item_config`` and
   properly configured ``data`` for ``MyModel`` by looking in the adapter registry
   ``deployfish.registry.importer_registry``.  This registry maps ``Adapter`` subclasses to
   ``deployfish.core.models.abstract.Model`` subclasses.
2. Instantiate the ``Adapter`` subclass, passing in our ``item_config`` to its constructor.
3. Run ``MyAdapter.convert()``.  This will generate ``data``, a dict formatted to look like what boto3's ``describe_*``
   API method would return for the ``MyModel``, and ``kwargs``, extra configuration ``MyModel`` may need in order to
   function properly.
4. Instantiate a ``MyModel`` by doing::

   instance = MyModel.__init__(data)

5. Set any other necessary attributes on ``instance`` from the data we returned above in ``kwargs``.

.. note::

    One of the challenges we have in constructing ``MyModel`` from deployfish.yml is that we need to ensure we can also
    load ``MyModel`` purely from AWS calls.  When loading an object from AWS , we want any dependent objects (e.g. a
    Service's TaskDefinition) to be lazy loaded from AWS in order to reduce the API calls to only the data we need at
    the moment --, this saves the user from having to wait too long.  When loading an object from deployfish.yml
    however, we load all the dependent objects at the same time have to provide them to the Model instance all at once,
    with no lazy loading.

    Largely we do this with @property and @propety.setter properties.   The main @property laods the data from AWS if
    necessary, while the @property.setter circumvents the AWS loading.

1. Create a subclass of `deployfish.core.adapters.abstract.Adapter`
   * The ``.__init__()`` for your subclass will get passed the deployfish.yml configuration for your object, and will store it as `self.data`
   * Override `.convert()` on that subclass to use `self.data` to generate `data`, a dict that replicates what boto3 would return were we to call the `describe_*` method for that object, and `kwargs`, keyword arguments for the object's `.new()` factory method (described below)

...

Loading a Service from deployfish.yml
-------------------------------------

First create all the appropriate objects from the service config in deployfish.yml.


``deployfish.core.adapters.deployfish.ServiceAdapter``, does this, in this order:

1. Build the data necessary for the ``data`` parameter to ``Service.__init__()`` from the service's config.
2. If a ``config:`` section is present in the service's config, load the list of ``Secrets`` from the service's
   ``config:`` section via ``deployfish.core.adapters.deployfish.SecretAdapter`` and
   ``deployfish.core.adapters.deployfish.ExternalSecretAdapter``.
3. Use ``deployfish.core.adapters.deployfish.TaskDefinitionAdapter`` to create a ``TaskDefinition`` from the
   service config.  This needs the ``Secrets`` we created above, if any.
4. If ``application_scaling:`` section is present in the service's config, build the ApplicationScaling objects,
   which are:
   * ``ScalableTarget`` (from ``deployfish.core.adapters.deployfish.ECServiceScalableTargetAdapter``)
   * One or more ``ScalingPolicy`` objects (via ``deployfish.core.adapters.deployfish.ECServiceScalingPolicyAdapter``)
   * One ``CloudwatchAlarm`` per ScalingPolicy (via ``deployfish.core.adapters.deployfish.ECServiceCPUAlarmAdapter``)
* If a ``service_discovery:`` section is present in the service's config, build a ``ServiceDiscoveryService`` object
  (via ``deployfish.core.adapters.deployfish.ServiceDiscoveryServiceAdapter``).
* If a ``tasks:`` section is present in the service's config, build configuration for one or more ``ServiceHelperTasks`` (via
  ``deployfish.core.adapters.deployfish.ServiceHelperTaskAdapter``, but (**important**) loaded in Service.new(), not in
  ``ServiceAdapter.convert()`` -- we need the fully configured ``Service`` object in order to make the helper tasks, and that
  doesn't happen until we get into ``Service.new()``.

Finally the ``Service`` object is configured.

Here's how ``Service.save()`` works when creating a service:

* If we have ``ServiceHelperTasks``, create them in AWS and save their ``family:revisions`` on our ``TaskDefinition``, so that we know which specific revision to run to get the version of the code we want
* Create the ``TaskDefinition`` in AWS, and save its ARN to the Service as ``taskDefinition``
* If we need it, create the ``ServiceDiscoveryService`` in AWS, and save its ARN to the service as ``serviceRegistries[0]['registryArn']``; otherwise delete any ``ServiceDiscoveryService`` associated
  with the ``Service``.
* Create the ``Service`` in AWS
* If we need it, create the ``ScalingTarget``, ``ScalingPolicy`` and ``CloudwatchAlarm`` objects in AWS, otherwise delete any such that exist in AWS

