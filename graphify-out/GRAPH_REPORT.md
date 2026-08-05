# Graph Report - pydantic-container-adapter  (2026-08-05)

## Corpus Check
- 215 files · ~144,436 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4479 nodes · 9428 edges · 225 communities (161 shown, 64 thin omitted)
- Extraction: 80% EXTRACTED · 20% INFERRED · 0% AMBIGUOUS · INFERRED: 1916 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f4810351`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- models/ecs.py
- Manager
- test_config_schema_container.py
- Instance
- TaskTagImporter
- handle_model_exceptions
- ObjectLoader
- ObjectDockerExecController
- DeployfishArgparseController
- bind_controller
- SupportsModel
- deployfish/controllers/__init__.py
- check_napoleon_gate.py
- TaskDefinition
- TestStandaloneTaskAdapter_schedule_FARGATE
- TaskDefinitionFARGATEMixin
- TargetGroupTableRenderer
- Config
- ext_df_jinja2.py
- ._get_command_specific_data
- .new
- Cluster
- ECSServiceCommands
- ServiceHelperTaskAdapter
- ObjectReadOnly
- CloudWatchLogGroup
- EFSFileSystem
- ContainerDefinitionAdapter
- exceptions.py
- schema/container.py
- StandaloneTaskAdapter
- .new
- Annotator
- ServiceAdapter
- LoadBalancerListener
- ClassicLoadBalancerTarget
- partial_model
- Any
- test_ssh_main_controller_push.py
- ECSServiceScalingPolicyAdapter
- DeployfishCementPluginHandler
- Parameter Store Secrets Tutorial
- Adapter
- LoadBalancer
- Controllers
- Adapters
- get_boto3_session
- setter
- SecretAdapter
- parse_secret_string
- ECSDeploymentStatusWaiterHook
- .convert
- TestContainerDefinitionInput
- Quality Gate Recovery Master Plan
- _DockerHost
- MySQLDatabase
- _service_from_yml
- conftest.py
- utils/mixins.py
- AbstractWaiterHook
- AutoscalingGroup
- ecs/__init__.py
- TaskDefinitionAdapter
- GitMixin
- slack/hooks.py
- Models and Managers
- .get
- EventTarget
- TerraformS3State
- create_hooked_waiter_with_client
- ECSCluster
- Any
- ServiceDiscoveryNamespace
- StandaloneTask
- EnvironmentConfigProcessor
- Model
- .parse
- .annotate
- TableRenderer
- commands.py
- test_elbv2_managers.py
- _SecretsHost
- .__process
- ECSTaskStatusHook
- establish_tunnel
- File Structure
- CloudwatchAlarmManager
- .get_many
- Basic ECS Services Example
- Python Dependencies
- TestContainerDefinitionAdapterComprehensive
- EventScheduleRuleManager
- _event_timestamp_to_utc
- .annotate
- .convert
- .__call__
- .major_server_version
- Installation
- test_elbv2_coverage_push.py
- TestPortMapping
- .render_for_update
- CodeNameVersionMixin
- mysql/__init__.py
- TestServiceRelatedObjects
- TestServiceHelperTaskAdapter_schedule_EC2
- TestServiceHelperTaskAdapter_schedule_FARGATE
- TestStandaloneTaskAdapter_schedule_EC2
- DeployfishJinja2TemplateHandler
- Application Scaling Example
- MySQLDatabaseManager
- .render_mysql_command
- _service_without_appscaling
- TestServiceProperties
- deployfish/events.py
- Service
- .__init__
- Secret
- .convert
- deployfish-mysql plugin
- Modular Plugin Architecture
- .import_tags
- TestServiceDiscoveryServiceModelPush
- TestServiceSSHNetworking
- TestServiceDiscoveryServiceManagerPush
- test_service_discovery_model.py
- CloudWatchLogStreamManager
- .list_all
- .load
- LoadBalancerListenerRule
- table.py
- registry.py
- Tutorial 2 Extended Service
- .__init__
- models/abstract.py
- _paginate
- .convert
- .list_all
- .arn
- .create
- .parse
- .display_deployments
- Interpolation Test Config
- SupportsSecrets
- TestServiceManagerSaveUpdate
- TestServiceRestart
- TestServiceDiscoveryExtended
- Replace hand-rolled Adapter dict-mutation with Pydantic models
- TestServiceHelperTaskNew
- TestSSHMixinHelpers
- .__init__
- mysql section in deployfish.yml
- DeployfishApp (cement.App subclass)
- TestServiceRenderForDiff
- Multi-Container Task Example
- Terraform Interpolate Test
- TestServiceUpdateAppscaling
- TestServiceSave
- test_elb_managers.py
- .name
- test_service_manager_list.py
- .reload_secrets
- .get_cached
- ECS service configuration example
- Renderers
- Autoscaling Group Example
- Volume Mounts Example
- test CI job
- AGENTS.md
- .__iter__
- .__init__
- .__iter__
- .tags
- .value
- .load
- .render_for_validate
- .secret
- .service
- Sphinx
- deployfish.core.models.abstract
- Parameter Store Example
- napoleon-gate documentation enforcement
- California Institute of Technology
- deploy-complete.bash
- core/adapters/deployfish/__init__.py
- .__init__
- Config and Config Processors
- deployfish.main
- No Load Balancer Example
- TestServiceManagerCreate
- .log_streams
- .pk
- .pk
- graphify Knowledge Graph Usage Rules
- deployfish.core.loaders
- Lazy Loading from AWS
- Jinja2 ChoiceLoader for Plugins
- Plugin Adapter (convert method)
- 80% Line Coverage Gate
- Glenn Bach
- Katarina Liu
- Contributing Guide
- Adding Resource Attribute Support
- Plugin Config Interpolation Hooks
- uv sync Virtual Environment Setup
- deploy create Command
- deploy scale Command
- env_file Configuration Option
- environment Service Parameter
- application_scaling Block
- aws: Credentials Section
- capacity_provider_strategy
- service_discovery Block
- scale-down policy
- scale-up policy
- deployfish

## God Nodes (most connected - your core abstractions)
1. `Service` - 231 edges
2. `Model` - 176 edges
3. `Instance` - 175 edges
4. `Manager` - 120 edges
5. `TaskDefinition` - 109 edges
6. `Cluster` - 109 edges
7. `InvokedTask` - 95 edges
8. `handle_model_exceptions()` - 81 edges
9. `SchemaException` - 81 edges
10. `ObjectLoader` - 75 edges

## Surprising Connections (you probably didn't know these)
- `pyyaml dependency` --conceptually_related_to--> `Config`  [INFERRED]
  requirements.txt → deployfish/config/config.py
- `terraform section` --conceptually_related_to--> `TerraformStateConfigProcessor`  [INFERRED]
  examples/terraform-basic.yml → deployfish/config/processors/terraform.py
- `terraform section` --conceptually_related_to--> `TerraformStateConfigProcessor`  [INFERRED]
  tests/interpolate.yml → deployfish/config/processors/terraform.py
- `terraform section with {environment} statefile` --conceptually_related_to--> `TerraformStateConfigProcessor`  [INFERRED]
  tests/terraform_interpolate.yml → deployfish/config/processors/terraform.py
- `autoscalinggroup_name` --conceptually_related_to--> `AutoscalingGroup`  [INFERRED]
  examples/asg.yml → deployfish/core/models/ec2.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **deployfish.yml Adapter Modules** — docs_source_api_adapters_abstract_rst_deployfish_core_adapters_abstract, docs_source_api_adapters_mixins_rst_deployfish_core_adapters_deployfish_mixins, docs_source_api_adapters_appscaling_rst_deployfish_core_adapters_deployfish_appscaling, docs_source_api_adapters_cloudwatch_rst_deployfish_core_adapters_deployfish_cloudwatch, docs_source_api_adapters_ecs_rst_deployfish_core_adapters_deployfish_ecs, docs_source_api_adapters_events_rst_deployfish_core_adapters_deployfish_events, docs_source_api_adapters_service_discovery_rst_deployfish_core_adapters_deployfish_service_discovery, docs_source_api_adapters_ssh_rst_deployfish_core_adapters_deployfish_ssh [EXTRACTED 1.00]
- **Advanced Cluster Access Commands** — docs_source_advanced_rst_bastion_host, docs_source_advanced_rst_deploy_cluster, docs_source_advanced_rst_deploy_service_ssh, docs_source_advanced_rst_deploy_service_exec, docs_source_api_adapters_ssh_rst_deployfish_core_adapters_deployfish_ssh [INFERRED 0.85]
- **Deployfish Controllers API Documentation** — docs_source_api_controllers_index_controllers [EXTRACTED 1.00]
- **Elastic Load Balancer Controller Modules** — docs_source_api_controllers_elb_deployfish_controllers_elb, docs_source_api_controllers_elb_deployfish_controllers_elbv2 [EXTRACTED 1.00]
- **Core Models API Documentation** — docs_source_api_models_abstract_abstract, docs_source_api_models_appscaling_application_scaling, docs_source_api_models_abstract_deployfish_core_models_abstract, docs_source_api_models_appscaling_deployfish_core_models_appscaling [EXTRACTED 1.00]
- **AWS service model API documentation pages** — docs_source_api_models_cloudwatch_cloudwatch, docs_source_api_models_cloudwatchlogs_cloudwatch_logs, docs_source_api_models_ec2_elastic_compute_cloud, docs_source_api_models_ecs_elastic_container_service, docs_source_api_models_efs_elastic_file_system, docs_source_api_models_elb_classic_load_balancing, docs_source_api_models_elbv2_application_network_load_balancing, docs_source_api_models_events_events, docs_source_api_models_rds_relational_database_service, docs_source_api_models_secrets_manager_secrets_manager, docs_source_api_models_service_discovery_service_discovery, docs_source_api_models_ssh_ssh [INFERRED 0.85]
- **deployfish renderer modules** — docs_source_api_renderers_deployfish_renderers_abstract, docs_source_api_renderers_deployfish_renderers_table, docs_source_api_renderers_deployfish_renderers_misc [EXTRACTED 1.00]
- **deploy mysql CLI commands** — docs_source_plugins_mysql_deploy_mysql_create, docs_source_plugins_mysql_deploy_mysql_update, docs_source_plugins_mysql_deploy_mysql_validate, docs_source_plugins_mysql_deploy_mysql_dump, docs_source_plugins_mysql_deploy_mysql_load, docs_source_plugins_mysql_deploy_mysql_show_grants [EXTRACTED 1.00]
- **Deployfish MVC-like Architecture Layers** — docs_source_runbook_architecture_deployfishapp, docs_source_runbook_architecture_controllers_layer, docs_source_runbook_architecture_loaders_layer, docs_source_runbook_architecture_models_layer, docs_source_runbook_architecture_adapters_layer, docs_source_runbook_architecture_renderers_layer [EXTRACTED 1.00]
- **Plugin Extension Component Stack** — docs_source_runbook_extending_plugin_adapter, docs_source_runbook_extending_plugin_model_manager, docs_source_runbook_extending_plugin_controller, docs_source_runbook_extending_plugin_hooks, docs_source_runbook_extending_deployfish_cement_plugin_handler [EXTRACTED 1.00]
- **Quality Gate Recovery Phases 1-6** — docs_superpowers_plans_2026_06_01_quality_gate_recovery_master_plan_phase_1_shared_infra, docs_superpowers_plans_2026_06_01_quality_gate_recovery_master_plan_phase_2_test_cleanup, docs_superpowers_plans_2026_06_01_quality_gate_recovery_master_plan_phase_3_ssh_secrets_sd, docs_superpowers_plans_2026_06_01_quality_gate_recovery_master_plan_phase_4_ecs_hotspots, docs_superpowers_plans_2026_06_01_quality_gate_recovery_master_plan_phase_5_napoleon_completion, docs_superpowers_plans_2026_06_01_quality_gate_recovery_master_plan_phase_6_final_verification [EXTRACTED 1.00]
- **ECS Service Configuration Examples** — examples_basic, examples_fargate, examples_no_elb, examples_tutorial_1, examples_tutorial_2 [INFERRED 0.85]
- **Terraform State Integration Pattern** — examples_terraform_basic_terraform, tests_interpolate_terraform, tests_terraform_interpolate_terraform [INFERRED 0.95]
- **Fargate Launch Type Pattern** — examples_fargate_launch_type_fargate, examples_run_task_launch_type_fargate, examples_fargate_vpc_configuration, examples_run_task_vpc_configuration [INFERRED 0.95]

## Communities (225 total, 64 thin omitted)

### Community 0 - "models/ecs.py"
Cohesion: 0.03
Nodes (93): LazyAttributeMixin, Model lazy attribute mixin behavior., Model scalable target behavior. Args: data: data. policies: policies., Pk. Returns: Operation result., Name. Returns: Operation result., ScalableTarget, AbstractTaskManager, ClusterManager (+85 more)

### Community 1 - "Manager"
Cohesion: 0.02
Nodes (71): Manager, Get many. Args: pks: pks. Keyword Args: _: ., Model manager behavior., AutoscalingGroupManager, Model vpcmanager behavior., Model autoscaling group manager behavior., Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., Get many. Args: pks: pks. Keyword Args: kwargs: kwargs. Returns: Operation… (+63 more)

### Community 2 - "test_config_schema_container.py"
Cohesion: 0.15
Nodes (20): ContainerDefinitionInput, ExtraHost, LoggingConfig, PortMapping, BaseModel, A single ``/etc/hosts`` entry to add to the container. Args: hostname: the…, Parse a ``"hostname:ip_address"`` extra_hosts entry. Args: raw: the raw…, A container's logging configuration. Args: driver: the log driver. options: log… (+12 more)

### Community 3 - "Instance"
Cohesion: 0.02
Nodes (99): Instance, InstanceManager, Tags. Returns: Operation result., Model subnet manager behavior., Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., List. Args: vpc_id: vpc id. Returns: Operation result., Model security group manager behavior., Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result. (+91 more)

### Community 4 - "TaskTagImporter"
Cohesion: 0.06
Nodes (23): Task related tags we need to read from a task definition associated with a…, Initialize TaskTagImporter., Capacity Provider Strategies are stored in tags like::…, If a constraint is a "memberOf" constraint: 'deployfish:placementConstraint.0':…, ``placementStrategy`` is stored in tags as:: 'deployfish:placementStrategy.0':…, Handle convert awsvpc configuration. Args: key: key. value: value., Take ``tag_list``, a tag data structure from AWS that looks like:: tags = [ {…, Take ``data``, the configuration struct for a StandaloneTask or… (+15 more)

### Community 5 - "handle_model_exceptions"
Cohesion: 0.04
Nodes (38): ex, ex, ex, get_ssh_target(), App, ex, SSH to a container machine running one of the tasks for an existing Service or…, SSH to a container machine running one of the tasks for an existing Service or… (+30 more)

### Community 6 - "ObjectLoader"
Cohesion: 0.06
Nodes (40): ECSStandaloneTask, Model ecsstandalone task behavior., DeployfishObjectDoesNotExist, DeployfishSectionDoesNotExist, ObjectLoader, ObjectNotManaged, Any, Exception (+32 more)

### Community 7 - "ObjectDockerExecController"
Cohesion: 0.15
Nodes (13): ECSClusterSSH, Meta, Model ecscluster ssh behavior., Meta, ObjectDockerExecController, ObjectSSHController, Controller, Model object docker exec controller behavior. (+5 more)

### Community 8 - "DeployfishArgparseController"
Cohesion: 0.05
Nodes (60): ArgparseController, Parse a date string in the form YYYY-MM-DD and return a datetime. Args: s: s.…, valid_date(), CrudBase, Meta, Controller, ex, Helper method that renders output from self.list() so that we can override… (+52 more)

### Community 9 - "bind_controller"
Cohesion: 0.08
Nodes (26): ECSService, ECSServiceStandaloneTasks, Controller, Valid date. Args: s: s. Returns: Operation result., Model ecsservice standalone tasks behavior., Model ecsservice behavior., valid_date(), bind_controller() (+18 more)

### Community 10 - "SupportsModel"
Cohesion: 0.02
Nodes (88): AbstractSSHProvider, BastionSSHProvider, build_sigint_handler(), DockerMixin, NoRunningTasks, NoSSHTargetAvailable, Any, Exception (+80 more)

### Community 11 - "deployfish/controllers/__init__.py"
Cohesion: 0.07
Nodes (39): Base, BaseService, BaseServiceDockerExec, BaseServiceSecrets, BaseServiceSSH, filename_envvar(), maybe_rename_existing_file(), Meta (+31 more)

### Community 12 - "check_napoleon_gate.py"
Cohesion: 0.07
Nodes (63): AST, _check_file(), _check_function_doc(), _constructor_has_args(), _first_doc_line(), _function_has_args(), _function_has_keyword_args(), _function_uses_return_or_yield() (+55 more)

### Community 13 - "TaskDefinition"
Cohesion: 0.04
Nodes (34): ContainerDefinition, SecretsMixin, An ECS Task Definition. Args: data: data. containers: containers., If this task definition exists in AWS, return our ``<family>:<revision>``…, Name. Returns: Operation result., Launch type. Returns: Operation result., Family. Returns: Operation result., Return the version for the task definition. We're cheating here by just… (+26 more)

### Community 15 - "TaskDefinitionFARGATEMixin"
Cohesion: 0.06
Nodes (28): Any, Model task definition fargatemixin behavior., If this is a FARGATE task definition, return ``True``. Otherwise return…, Return the minimum necessary cpu for our task by summing up 'cpu' from each of…, For FARGATE tasks, task cpu is required and must be one of the values listed in…, For EC2 tasks, set task cpu if 'cpu' is provided, don't set otherwise. If 'cpu'…, Set task cpu requirement, based on whether this is a FARGATE task or an EC2…, Find the minimum necessary memory and maximum necessary memory for our task by… (+20 more)

### Community 16 - "TargetGroupTableRenderer"
Cohesion: 0.14
Nodes (9): Specialized renderer for ECS target groups., Render attached load balancer names. Args: obj: Target group being rendered.…, Render target names. Args: obj: Target group being rendered. _key: Unused…, Render listener protocol/port pairs. Args: obj: Target group being rendered.…, Render backing container protocol/port pair. Args: obj: Target group being…, TargetGroupTableRenderer, TestTargetGroupTableRendererGaps, TestLBListenerTableRenderer (+1 more)

### Community 17 - "Config"
Cohesion: 0.06
Nodes (32): Config, NoSuchSectionError, NoSuchSectionItemError, Any, Session, setter, Initialize config state from a file path or provided payload. Args: filename:…, Returns: The pre-interpolated version of the raw YAML. (+24 more)

### Community 18 - "ext_df_jinja2.py"
Cohesion: 0.10
Nodes (19): color(), fromtimestamp(), lb_listener_table(), load(), Any, Render table for target groups. Args: data: Target-group-like row objects.…, Render table for ELBv2 listeners. Args: data: Listener-like row objects.…, Load template content and register custom filters. Args: *args: Positional… (+11 more)

### Community 19 - "._get_command_specific_data"
Cohesion: 0.14
Nodes (10): Any, Update the deployfish-specific environment variables in the container…, Build a dict that takes info from the service and overlays the generic (not…, Args: data: the ``tasks:`` section from our service definition in…, Change old style command defintions that look like this: tasks: - family:…, Build a dict that takes info from the output of :py:meth:`_get_base_task_data`…, Convert. Returns: Operation result., Set a ``data[data_key]`` on the dict ``data`` by looking at both ``task`` and… (+2 more)

### Community 20 - ".new"
Cohesion: 0.06
Nodes (15): Stable identity key used by baseline filtering., Construct and optionally interpolate a config object. Keyword Args: kwargs:…, Lazy load the deployfish.yml file. We only load it on request because most…, Lazy load the deployfish.yml file into a :py:class:`deployfish.config.Config`…, Path, TestConfigExtended, Path, TestConfigModule (+7 more)

### Community 21 - "Cluster"
Cohesion: 0.03
Nodes (44): Cluster, InvokedTask, DockerMixin, :param pk str: cluster name Args: pk: pk. Keyword Args: _: . Returns: Operation…, :param pk list[str]: list of cluster names Args: pks: pks. Keyword Args: _: .…, A record of a running AWS ECS Task, which means either a task running as part…, Pk. Returns: Operation result., Name. Returns: Operation result. (+36 more)

### Community 22 - "ECSServiceCommands"
Cohesion: 0.06
Nodes (31): ECSServiceCommandLogs, ECSServiceCommands, get_task(), Meta, Controller, ex, Build a ``deployfish.core.waiters.HookedWaiter`` for the operation named…, Show info about a ServiceHelperTask object associated with a Service that… (+23 more)

### Community 23 - "ServiceHelperTaskAdapter"
Cohesion: 0.06
Nodes (8): The problem here is that, unlike all our other adapters, we need to create…, ServiceHelperTaskAdapter, TestServiceHelperTaskAdapterComprehensive, BaseTestServiceHelperTaskAdapter_basic, If we have no vpc_configuration, our network mode should be forced to 'bridge'., Ensure old style command definitions still work: tasks: - family: foobar-test-…, If we have vpc_configuration, our network mode should be forced to 'awsvpc'., TestServiceHelperTaskAdapter_FARGATE

### Community 24 - "ObjectReadOnly"
Cohesion: 0.15
Nodes (22): BaseMultipleObjectsReturned, BaseOperationFailed, DoesNotExist, ImproperlyConfigured, MultipleObjectsReturned, OperationFailed, Delete. Args: obj: obj. Keyword Args: _: ., We tried to get a single object but it does not exist in AWS. (+14 more)

### Community 25 - "CloudWatchLogGroup"
Cohesion: 0.07
Nodes (35): CloudWatchLogGroup, CloudWatchLogGroupTailer, CloudWatchLogStream, CloudWatchLogStreamIterator, CloudWatchLogStreamTailer, An iterator class that allows you to tail live logs from a CloudWatchLogStream.…, Handle iter. Returns: Operation result., An iterator class that allows you to tail live logs from a CloudWatchLogStream.… (+27 more)

### Community 26 - "EFSFileSystem"
Cohesion: 0.10
Nodes (12): EFSFileSystem, Size. Returns: Operation result., State. Returns: Operation result., Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., List. Returns: Operation result., Model efsfile system behavior., Pk. Returns: Operation result., Name. Returns: Operation result. (+4 more)

### Community 27 - "ContainerDefinitionAdapter"
Cohesion: 0.15
Nodes (6): ContainerDefinitionAdapter, Return ``True`` if this container is part of a FARGATE task Returns: Operation…, Convert our deployfish YAML definition of our containers to the same format…, ``deployfish.yml`` environment variables are defined in one of the two…, Golden-master characterization tests for ContainerDefinitionAdapter.convert().…, TestContainerDefinitionAdapterGoldenMaster

### Community 28 - "exceptions.py"
Cohesion: 0.13
Nodes (28): BaseSkipConfigProcessing, AbstractConfigProcessor, ProcessingFailed, A base class for processors for our our ``deployfish.yml`` file. These…, Return all known replacements for ``deployfish.yml`` section name…, SkipConfigProcessing, # TODO: need to deal with multiple matches in the same line, ConfigProcessor (+20 more)

### Community 29 - "schema/container.py"
Cohesion: 0.14
Nodes (15): _normalize_environment(), _normalize_labels(), _parse_extra_hosts(), _parse_ports(), Any, Pydantic models describing the shape of a ``deployfish.yml`` container…, Raise a clear, specific error when ``driver`` is missing, instead of Pydantic's…, Split a shell command string into argv, if given as a string. Args: value: the… (+7 more)

### Community 30 - "StandaloneTaskAdapter"
Cohesion: 0.09
Nodes (8): SecretsMixin, Model standalone task adapter behavior., StandaloneTaskAdapter, Additional coverage for deployfish.core.adapters.deployfish.ecs., TestAbstractTaskAdapterBranches, TestStandaloneTaskAdapterComprehensive, BaseTestStandaloneTaskAdapter_basic, If we have vpc_configuration, our network mode should be forced to 'awsvpc'.

### Community 31 - ".new"
Cohesion: 0.08
Nodes (3): New. Args: obj: obj. source: source. Keyword Args: kwargs: kwargs. Returns:…, TestServiceDeployfishEnvironment, TestService_new

### Community 32 - "Annotator"
Cohesion: 0.08
Nodes (20): Annotator, process_service_update(), Get the authors for the most recent commits. Returns: Operation result., Get the committer for the most recent commits. Returns: Operation result., Get the deployer for the most recent commits. Returns: Operation result., Get the version for the most recent commits. Returns: Operation result., Get the name of the service. Returns: Operation result., Get the name of the service. Returns: Operation result. (+12 more)

### Community 33 - "ServiceAdapter"
Cohesion: 0.06
Nodes (18): Any, SecretsMixin, Update ``data`` with the configuration for the Service itself. This will look…, * Service itself [x] Args: data: data., Build a list of Secret and ExternalSecret objects from our Service's config:…, Handle build task definition. Args: kwargs: kwargs., Handle build application scaling objects. Args: kwargs: kwargs., Handle build service discovery service. Args: kwargs: kwargs. (+10 more)

### Community 34 - "LoadBalancerListener"
Cohesion: 0.07
Nodes (17): LoadBalancerListener, Listeners. Returns: Operation result., Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., Model load balancer listener behavior., Pk. Returns: Operation result., Name. Returns: Operation result., Arn. Returns: Operation result., Port. Returns: Operation result. (+9 more)

### Community 35 - "ClassicLoadBalancerTarget"
Cohesion: 0.06
Nodes (17): ClassicLoadBalancerTarget, Any, List. Args: load_balancer_name: load balancer name. Returns: Operation result., Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., Ssl policy. Returns: Operation result., Model classic load balancer target behavior. Args: data: data. instance:…, Initialize ClassicLoadBalancerTarget. Args: data: data. instance: instance., Pk. Returns: Operation result. (+9 more)

### Community 36 - "partial_model"
Cohesion: 0.16
Nodes (9): partial_model(), BaseModel, Helper for deriving "partial update" Pydantic models, used for the ``partial``…, Build a subclass of ``model`` where every field is optional and defaults to…, field_validator, BaseModel, Tests for deployfish.config.schema._partial.partial_model., TestPartialModel (+1 more)

### Community 37 - "Any"
Cohesion: 0.07
Nodes (18): Any, Get. Args: pk: pk. Keyword Args: _: ., Save. Args: obj: obj. Keyword Args: _: ., Exists. Args: pk: pk. Returns: Operation result., Diff. Args: obj: obj. Returns: Operation result., Needs update. Args: obj: obj. Returns: Operation result., Given an appropriate bit of data `obj` from a data source `source`, return the…, Is a factory method. .. note:: The ``**kwargs`` here is for the Adapter to use,… (+10 more)

### Community 38 - "test_ssh_main_controller_push.py"
Cohesion: 0.05
Nodes (36): App, Store active Cement app for config helpers. Args: app: Cement app whose config…, set_app(), Initialize AbstractSSHProvider. Args: instance: instance. Keyword Args:…, r""" Implement our SSH commands via AWS Systems Manager SSH connections…, Return a shell command suitable for establishing an interactive ssh session. If…, Build a command that will tunnel through an SSM connection to an instance to…, Return a shell command suitable for uploading a file through an ssh tunnel to… (+28 more)

### Community 39 - "ECSServiceScalingPolicyAdapter"
Cohesion: 0.11
Nodes (16): ECSServiceScalableTargetAdapter, ECSServiceScalingPolicyAdapter, Any, .. code-block:: python Args: data: data., Initialize ECSServiceScalableTargetAdapter. Args: data: data. Keyword Args:…, .. code-block:: python Args: data: data., Get resource id. Returns: Operation result., Convert. Returns: Operation result. (+8 more)

### Community 40 - "DeployfishCementPluginHandler"
Cohesion: 0.09
Nodes (18): DeployfishCementPluginHandler, get_deployfish_plugins(), load(), Meta, App, Cement plugin extension module., Load plugin. Args: plugin_name: plugin name., Load a list of plugins. Args: plugins: A list of plugin names to load. (+10 more)

### Community 41 - "Parameter Store Secrets Tutorial"
Cohesion: 0.07
Nodes (30): ECS Lifecycle Management, Terraform State Integration, SecretAdapter, ServiceAdapter, Service.save Creation Flow, TaskDefinitionAdapter, Basic ECS Service Tutorial, hello-world-test Service Example (+22 more)

### Community 42 - "Adapter"
Cohesion: 0.09
Nodes (19): BaseSchemaException, Adapter, Raise this if data in the config source does not validate properly., Return whether exactly one value in ``data`` is truthy. Args: data: Boolean…, Given a dict of data from a data source, convert it appropriate data Args:…, SchemaException, ECSServiceCPUAlarmAdapter, Any (+11 more)

### Community 43 - "LoadBalancer"
Cohesion: 0.07
Nodes (15): LoadBalancer, Get many. Args: pks: pks. Keyword Args: kwargs: kwargs. Returns: Operation…, Model load balancer behavior., Pk. Returns: Operation result., Name. Returns: Operation result., Arn. Returns: Operation result., Lb type. Returns: Operation result., Scheme. Returns: Operation result. (+7 more)

### Community 44 - "Controllers"
Cohesion: 0.09
Nodes (29): Base, deployfish.controllers.base, Cluster, deployfish.controllers.cluster, Commands, deployfish.controllers.commands, Crud, deployfish.controllers.crud (+21 more)

### Community 45 - "Adapters"
Cohesion: 0.09
Nodes (27): Class-Oriented Architecture Preference, sphinx-click, VPC Bastion Host Assumption, deploy cluster command, deploy service exec, deploy service ssh, deployfish.core.adapters.abstract, deployfish.core.adapters.deployfish.appscaling (+19 more)

### Community 46 - "get_boto3_session"
Cohesion: 0.12
Nodes (18): AWSSessionBuilder, build_boto3_session(), ForbiddenAWSAccountId, get_boto3_session(), NoSuchAWSProfile, Any, Exception, Session (+10 more)

### Community 47 - "setter"
Cohesion: 0.07
Nodes (20): setter, Return a dictionary of the secrets (AWS SSM Parameter Store parameters) for…, Secrets. Args: value: value., Secrets. Returns: Operation result., Secrets. Args: value: value., Secrets. Returns: Operation result., Secrets. Args: value: value., Service names are only unique within a cluster, so to fully identify a service… (+12 more)

### Community 48 - "SecretAdapter"
Cohesion: 0.16
Nodes (10): ExternalParameterException, Any, Exception, Model secret adapter behavior. Args: data: data., Initialize SecretAdapter. Args: data: data. Keyword Args: kwargs: kwargs., Is external. Returns: Operation result., Parse an identifier from a deployfish.yml parameter definition that looks like…, Convert. Returns: Operation result. (+2 more)

### Community 49 - "parse_secret_string"
Cohesion: 0.17
Nodes (8): parse_secret_string(), Parse an identifier from a deployfish.yml parameter definition that looks like…, Split. Returns: Operation result., Model secrets mixin behavior., Get secrets. Args: cluster: cluster. name: name. decrypt: decrypt. Returns:…, SecretsMixin, TestParseSecretString, TestSecretsMixinGetSecrets

### Community 50 - "ECSDeploymentStatusWaiterHook"
Cohesion: 0.11
Nodes (10): Service waiter. Args: obj: obj. Keyword Args: kwargs: kwargs., Delete waiter. Args: obj: obj. Keyword Args: kwargs: kwargs., Show periodic updates while we change desired count for a service. Args: obj:…, ECSDeploymentStatusWaiterHook, Success. Args: status: status. response: response. num_attempts: num attempts.…, Failure. Args: status: status. response: response. num_attempts: num attempts.…, for both the 'services_stable' and 'services_inactive' waiters on ECS. Args:…, Timeout. Args: status: status. response: response. num_attempts: num attempts.… (+2 more)

### Community 51 - ".convert"
Cohesion: 0.10
Nodes (12): Any, Add parameter store values to the container's 'secrets' list. The task will…, In ``deployfish.yml``, volumes take one of these two forms:: volumes: -…, ``deployfish.yml`` port mappings look like this:: ports: - "80" - "8443:443" -…, ``deployfish.yml`` docker labels are defined in one of the two following ways::…, Get ulimits. Returns: Operation result., Get log configuration. Returns: Operation result., Get linux parameters. Returns: Operation result. (+4 more)

### Community 53 - "Quality Gate Recovery Master Plan"
Cohesion: 0.11
Nodes (24): Adapter Abstract Base, importer_registry Adapter Registry, Model.new Factory Method, Adapters Layer, Controllers Layer, ObjectLoader Pattern, Models Layer, Renderers Layer (+16 more)

### Community 54 - "_DockerHost"
Cohesion: 0.10
Nodes (5): _DockerHost, Any, DockerMixin, setter, TestDockerMixinPush

### Community 55 - "MySQLDatabase"
Cohesion: 0.09
Nodes (12): MySQLDatabase, self.data here has the following structure: { 'name': 'string', 'service':…, Pk. Returns: Operation result., Name. Returns: Operation result., Ssh target. Returns: Operation result., Ssh targets. Returns: Operation result., Cluster. Returns: Operation result., Update. Args: root_user: root user. root_password: root password. ssh_target:… (+4 more)

### Community 56 - "_service_from_yml"
Cohesion: 0.13
Nodes (8): Coverage for Service render/save paths and related model branches., _service_from_aws(), _service_from_yml(), TestServiceProperties, TestServiceRenderForDiff, TestServiceRenderForDisplay, TestServiceRenderForUpdate, TestServiceSaveFlow

### Community 57 - "conftest.py"
Cohesion: 0.19
Nodes (19): Client. Returns: Operation result., application_scaling_yml(), config_secrets_yml(), fargate_service_yml(), helper_tasks_yml(), minimal_deployfish_yml(), mock_boto3_client(), _mock_boto3_session() (+11 more)

### Community 58 - "utils/mixins.py"
Cohesion: 0.13
Nodes (15): AnnotationMixin, CodebuildMixin, DeployfishDeployMixin, DockerImageNameMixin, DockerMixin, Model annotation mixin behavior., Annotate. Args: context: context., Model codebuild mixin behavior. Args: *args: args. (+7 more)

### Community 59 - "AbstractWaiterHook"
Cohesion: 0.11
Nodes (11): AbstractWaiterHook, Do something when our waiter status is 'timeout'. Args: status: status.…, Initialize AbstractWaiterHook. Args: obj: obj., Mark. Args: status: status. response: response. num_attempts: num attempts.…, Model abstract waiter hook behavior. Args: obj: obj., Do something when our waiter status is 'error'. Args: status: status. response:…, ECSTaskLogsHook, for the 'tasks_stopped'' waiters on ECS. Args: obj: obj. (+3 more)

### Community 60 - "AutoscalingGroup"
Cohesion: 0.07
Nodes (15): AutoscalingGroup, Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., List. Returns: Operation result., Model autoscaling group behavior., Pk. Returns: Operation result., Name. Returns: Operation result., Arn. Returns: Operation result., Autoscaling group. Returns: Operation result. (+7 more)

### Community 61 - "ecs/__init__.py"
Cohesion: 0.13
Nodes (13): AbstractTaskAdapter, Any, When creating :py:class:`deployfish.core.models.ecs.ServiceHelperTask` objects,…, Model vpc configuration mixin behavior., Get vpc configuration. Args: source: source. Returns: Operation result., Model abstract task adapter behavior., Return ``True ``if this task definition is for FARGATE, ``False`` otherwise.…, Construct the dict that will be given as input for configuring an… (+5 more)

### Community 62 - "TaskDefinitionAdapter"
Cohesion: 0.24
Nodes (4): Convert our deployfish YAML definition of our task definition to the same…, TaskDefinitionAdapter, TestTaskDefinitionAdapterComprehensive, TestTaskDefinitionAdapter

### Community 63 - "GitMixin"
Cohesion: 0.15
Nodes (9): GitMixin, Model git mixin behavior. Args: *args: args., Initialize GitMixin. Args: *args: args. Keyword Args: url_type: url type.…, Handle format url. Args: url: url. label: label. Returns: Operation result., Handle build url patterns., Update the `values` dict with: * `previous_version`: the version number for the…, Handle get concise info. Returns: Operation result., Extract info about the git repo. Assume we're in the checked out clone. Args:… (+1 more)

### Community 64 - "slack/hooks.py"
Cohesion: 0.15
Nodes (12): DeployfishMessage, process_service_update(), Initialize ServiceUpdateMessage. Args: app: app. obj: obj. repo_folder: repo…, Add service update. Args: obj: obj., Process service update. Args: app: app. obj: obj. success: success. reason:…, A message from deployfish. Args: app: app. *args: args., Initialize DeployfishMessage. Args: app: app. *args: args. Keyword Args:…, A message indicating that a service has been updated. Args: app: app. obj: obj.… (+4 more)

### Community 65 - "Models and Managers"
Cohesion: 0.11
Nodes (19): CloudWatch, deployfish.core.models.cloudwatch, CloudWatch Logs, deployfish.core.models.cloudwatchlogs, deployfish.core.models.ec2, Elastic Compute Cloud, deployfish.core.models.efs, Elastic File System (+11 more)

### Community 66 - ".get"
Cohesion: 0.02
Nodes (61): Any, List. Args: cluster: cluster. service: service. family: family.…, :param pk str: a string like "{cluster}:{container_instance_id}" Args: pk: pk.…, :param cluster str: the name of an ECS cluster Args: cluster: cluster. Returns:…, :param pk str: cluster name Args: pk: pk. Returns: Operation result., Handle get service and cluster from pk. Args: pk: pk. Returns: Operation result., :param pk str: a string like "{cluster_name}:{service_name}" Args: pk: pk.…, Exists. Args: pk: pk. Returns: Operation result. (+53 more)

### Community 67 - "EventTarget"
Cohesion: 0.06
Nodes (18): EventTarget, Any, Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., List. Returns: Operation result., Get. Args: pk: pk. Keyword Args: kwargs: kwargs. Returns: Operation result., :py:attr:`data` here has the same structure as what is returned by Args: data:…, New. Args: obj: obj. source: source. Keyword Args: kwargs: kwargs. Returns:…, Initialize EventTarget. Args: data: data. rule: rule. (+10 more)

### Community 68 - "TerraformS3State"
Cohesion: 0.07
Nodes (20): Any, Model terraform s3 state behavior. Args: terraform_config: terraform config.…, Initialize TerraformS3State. Args: terraform_config: terraform config. context:…, Retrive our statefile from S3 Args: state_file_url: state file url. profile:…, Handle load pre version 12. Args: tfstate: tfstate., Handle load post version 12. Args: tfstate: tfstate., Load. Args: replacements: replacements., Initialize TerraformEnterpriseState. Args: terraform_config: terraform config.… (+12 more)

### Community 69 - "create_hooked_waiter_with_client"
Cohesion: 0.15
Nodes (9): Get waiter. Args: waiter_name: waiter name. Returns: Operation result., create_hooked_waiter_with_client(), HookedWaiter, :type name: string :param name: The name of the waiter :type config:…, Wait. Keyword Args: kwargs: kwargs., :type waiter_name: str :param waiter_name: The name of the waiter. The name…, A HookedWaiter is almost exactly like a standard boto3 Waiter with one…, TestCreateHookedWaiterWithClient (+1 more)

### Community 70 - "ECSCluster"
Cohesion: 0.20
Nodes (9): ECSCluster, ex, Change desired count for a service., Model ecscluster behavior., Scale the number of instances in an ECS Cluster to match ``count``. ..…, LogsCloudWatchLogGroup, Model logs cloud watch log group behavior., TestECSClusterController (+1 more)

### Community 71 - "Any"
Cohesion: 0.20
Nodes (6): Any, Render for diff. Returns: Operation result., Initialize ServiceDiscoveryService. Args: data: data. Keyword Args: kwargs:…, Render for diff. Returns: Operation result., Render for create. Returns: Operation result., Render for update. Returns: Operation result.

### Community 72 - "ServiceDiscoveryNamespace"
Cohesion: 0.12
Nodes (10): Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., Model service discovery namespace behavior., Pk. Returns: Operation result., Name. Returns: Operation result., Arn. Returns: Operation result., Namespace. Returns: Operation result., List. Keyword Args: private_only: private only. Returns: Operation result., ServiceDiscoveryNamespace (+2 more)

### Community 73 - "StandaloneTask"
Cohesion: 0.04
Nodes (31): ContainerInstance, :param pk str: a string like "{cluster}:{container_instance_id}" Args: pk: pk.…, :param pk str: a string like "{cluster}:{container_instance_id}" Args: pk: pk.…, StandaloneTasks are TaskDefinitions with their own configuration, apart from…, Return the prefix we use to save our AWS Parameter Store Parameters to AWS.…, Model container instance behavior. Args: data: data. cluster: cluster., Pk. Returns: Operation result., Name. Returns: Operation result. (+23 more)

### Community 74 - "EnvironmentConfigProcessor"
Cohesion: 0.19
Nodes (8): EnvironmentConfigProcessor, Any, Replace. Args: obj: obj. key: key. value: value. section_name: section name.…, Model environment config processor behavior. Args: config: config. context:…, Initialize EnvironmentConfigProcessor. Args: config: config. context: context., Handle load env file. Args: filename: filename. Returns: Operation result., Load per item environment. Args: section_name: section name. item_name: item…, TestEnvironmentConfigProcessor

### Community 75 - "Model"
Cohesion: 0.04
Nodes (38): Model, Model model behavior. Args: data: data., Initialize LazyAttributeMixin., Initialize Model. Args: data: data., Exists. Returns: Operation result., Save. Returns: Operation result., Handle str. Returns: Operation result., CloudWatchLogGroupManager (+30 more)

### Community 76 - ".parse"
Cohesion: 0.12
Nodes (8): Deployfish supports putting 'config.KEY' as the value for the host and port…, Host. Returns: Operation result., User. Returns: Operation result., Db. Returns: Operation result., Password. Returns: Operation result., Character set. Returns: Operation result., Collation. Returns: Operation result., Port. Returns: Operation result.

### Community 77 - ".annotate"
Cohesion: 0.14
Nodes (9): GitChangelogMixin, Any, Look through the commits between the current version and the last version…, needs to be used after GitMixin in the inheritance chain., Look through the commits between the current version and the last version…, Annotate. Args: values: values., Annotate. Args: values: values., Annotate. Args: values: values. (+1 more)

### Community 78 - "TableRenderer"
Cohesion: 0.11
Nodes (12): Any, Render byte count into human-readable units. Args: value: Byte count to format.…, Render values using builtin datatype formatting rules. Args: value: Value to…, Reformat one value into a more human-friendly form. Args: obj: Source object…, Render a list of results as an ASCII table. Args: columns: Column configuration…, Render one column value for one row object. Args: obj: Source object for the…, Render all rows into a formatted table string. Args: data: Sequence of row-like…, Initialize table renderer. Args: columns: Column configuration keyed by output… (+4 more)

### Community 79 - "commands.py"
Cohesion: 0.25
Nodes (8): list_log_streams(), App, Tail the logs for a Task of Task subclass to stdout. How this actually works is…, Build a table of all available log streams for a Task and print it to stdout.…, tail_task_logs(), _awslogs_task(), TestListLogStreams, TestTailTaskLogs

### Community 80 - "test_elbv2_managers.py"
Cohesion: 0.19
Nodes (5): _paginate(), TestLoadBalancerListenerManager, TestLoadBalancerListenerRuleManager, TestLoadBalancerManager, TestTargetGroupManager

### Community 81 - "_SecretsHost"
Cohesion: 0.16
Nodes (5): Any, SecretsMixin, _SecretsHost, TestSecretModel, TestSecretsMixinWriteSecrets

### Community 82 - ".__process"
Cohesion: 0.16
Nodes (8): Any, Perform string replacements on ``value``, a string value in our…, Process ``obj``, a value from a key of an item from ``deployfish.yml``, looking…, Process ``obj``, a list value of an item from ``deployfish.yml``, looking for…, Recurse through each key in our dict ``obj`` and process it appropriately. We…, Is the method that :py:class:`ConfigProcessor` will execute as it loops through…, Initialize AbstractConfigProcessor. Args: config: config. context: context., Populate :py:attr:`deployfish_lookups`.

### Community 83 - "ECSTaskStatusHook"
Cohesion: 0.15
Nodes (7): Run task waiter. Args: tasks: tasks. Keyword Args: kwargs: kwargs., ECSTaskStatusHook, for the 'tasks_stopped'' waiters on ECS, and prints the status of our tasks on…, Waiting. Args: status: status. response: response. num_attempts: num attempts.…, Success. Args: status: status. response: response. num_attempts: num attempts.…, Timeout. Args: status: status. response: response. num_attempts: num attempts.…, TestECSTaskStatusHook

### Community 84 - "establish_tunnel"
Cohesion: 0.16
Nodes (10): establish_tunnel(), get_tunnel(), get_tunnel_target(), Actually establish an SSH Tunnel. This does not return until the user manually…, Return an ``Instance`` object through which the user can make an ssh tunnel. If…, Establish an SSH tunnel from our machine through an instance to a host:port in…, If we didn't get a specific tunnel to use, present the user with a list of all…, TestEstablishTunnel (+2 more)

### Community 85 - "File Structure"
Cohesion: 0.14
Nodes (13): File Structure, Global Constraints, Post-pilot follow-up (not part of this plan), Pydantic ContainerDefinitionAdapter Pilot Implementation Plan, Task 1: Golden-master characterization test for `ContainerDefinitionAdapter.convert()`, Task 2: `partial_model()` helper, Task 3: Container sub-models (`PortMapping`, `Ulimit`, `ExtraHost`, `LoggingConfig`, `TmpfsMount`), Task 4: `ContainerDefinitionInput` (+5 more)

### Community 86 - "CloudwatchAlarmManager"
Cohesion: 0.18
Nodes (7): CloudwatchAlarmManager, Arn. Returns: Operation result., Model cloudwatch alarm manager behavior., Get. Args: pk: pk. Keyword Args: kwargs: kwargs. Returns: Operation result., List. Args: cluster: cluster. service: service. Keyword Args: kwargs: kwargs.…, Save. Args: obj: obj. Keyword Args: kwargs: kwargs., Delete. Args: obj: obj. Keyword Args: kwargs: kwargs.

### Community 87 - ".get_many"
Cohesion: 0.18
Nodes (6): datetime, List. Args: cluster_name: cluster name. Returns: Operation result., Get many. Args: pks: pks. Keyword Args: _: . Returns: Operation result., List. Args: cluster_name: cluster name. service_name: service name.…, Timestamp. Returns: Operation result., Last updated. Returns: Operation result.

### Community 88 - "Basic ECS Services Example"
Cohesion: 0.17
Nodes (13): Basic ECS Services Example, load_balancer with target_group_arn, load_balancer with load_balancer_name, my-service-alb (ALB target group), my-service-elb (Classic ELB), network_mode: bridge, services section, task_role_arn IAM role (+5 more)

### Community 89 - "Python Dependencies"
Cohesion: 0.15
Nodes (13): Python Dependencies, boto3 dependency, cement dependency, click dependency, docker dependency, gitpython dependency, jinja2 dependency, jsondiff2 dependency (+5 more)

### Community 91 - "EventScheduleRuleManager"
Cohesion: 0.20
Nodes (6): EventScheduleRuleManager, Model event schedule rule manager behavior., Save. Args: obj: obj. Keyword Args: _: . Returns: Operation result., Delete. Args: obj: obj. Keyword Args: _: ., If ``obj`` is disabled, change its state of "ENABLED". Otherwise, do nothing.…, If ``obj`` is enabled, change the its state to "DISABLED". Otherwise, do…

### Community 92 - "_event_timestamp_to_utc"
Cohesion: 0.20
Nodes (8): _event_timestamp_to_utc(), Any, datetime, Convert CloudWatch millisecond timestamps to aware UTC datetimes. Args:…, Handle next. Returns: Operation result., Handle next. Returns: Operation result., :param start_time datetime: a timezone aware, UTC datetime Args: stream:…, Handle next. Returns: Operation result.

### Community 93 - ".annotate"
Cohesion: 0.20
Nodes (8): ImproperlyConfiguredError, Exception, Path, Process a pyproject.toml file and return the name and version. Raises:…, Extract some stuff from setup.py, if present. If setup.py is present, we'll add…, We programmers improperly configured something., Process a setup.py file and return the name and version. Raises: ValueError: if…, Process a Makefile and return the name and version. Raises: ValueError: if the…

### Community 94 - ".convert"
Cohesion: 0.25
Nodes (5): Any, :rtype: dict(str, Any), dict(str, Any) Returns: Operation result., Initialize TaskDefinitionAdapter. Args: data: data. secrets: secrets.…, In the YAML, volume definitions look like this:: volumes: - name: 'string'…, Copy. Returns: Operation result.

### Community 95 - ".__call__"
Cohesion: 0.17
Nodes (6): Do any necessary cleanup after the waiter iteration has completed and we've…, Args: * 'state': the current state of the waiter. One of 'waiting', 'success',…, Do any necessary setup on the waiter iteration before we've done our per-state…, Do something when our waiter status is 'waiting'. Args: status: status.…, Do something when our waiter status is 'success'. Args: status: status.…, Do something when our waiter status is 'failure'. Args: status: status.…

### Community 96 - ".major_server_version"
Cohesion: 0.17
Nodes (6): Create the database and user for ``obj``, and assign appropriate grants to the…, Update the grants and password for the database user on ``obj``. Args: obj: The…, Return the major.minor version of the MySQL server. Example: If the server…, Server version. Args: ssh_target: ssh target. verbose: verbose. user: user.…, Render for create. Args: root_user: root user. root_password: root password.…, Render for update. Args: root_user: root user. root_password: root password.…

### Community 97 - "Installation"
Cohesion: 0.18
Nodes (12): Deployfish, Developer Guide, User Guide, AWS CLI v2, FARGATE container EXEC, Installation, pip install deployfish, Session Manager plugin (+4 more)

### Community 98 - "test_elbv2_coverage_push.py"
Cohesion: 0.24
Nodes (5): _paginate(), Additional ELBv2 manager coverage., TestLoadBalancerListenerModelPush, TestLoadBalancerManagerPush, TestTargetGroupManagerPush

### Community 100 - ".render_for_update"
Cohesion: 0.20
Nodes (6): Any, Save. Args: obj: obj. Keyword Args: kwargs: kwargs., Scale. Args: count: count. force: force., Render for update. Returns: Operation result., Render for diff. Returns: Operation result., Initialize Instance. Args: data: data.

### Community 101 - "CodeNameVersionMixin"
Cohesion: 0.40
Nodes (4): CodeNameVersionMixin, Model code name version mixin behavior., Path, TestCodeNameVersionMixin

### Community 102 - "mysql/__init__.py"
Cohesion: 0.25
Nodes (8): pre_config_interpolate_add_mysql_section(), App, Add our "mysql" section to the list of sections on which keyword interpolation…, add_template_dir(), load(), App, Add template dir. Args: app: app., Load. Args: app: app.

### Community 106 - "TestStandaloneTaskAdapter_schedule_EC2"
Cohesion: 0.11
Nodes (3): TestStandaloneTaskAdapter_EC2, TestStandaloneTaskAdapter_FARGATE, TestStandaloneTaskAdapter_schedule_EC2

### Community 107 - "DeployfishJinja2TemplateHandler"
Cohesion: 0.17
Nodes (9): DeployfishJinja2OutputHandler, DeployfishJinja2TemplateHandler, Meta, We're subclassing the cement Jinja2OutputHandler here so we can use our own…, Bind custom template handler. Args: app: Cement application instance. Side…, We're subclassing the cement Jinja2TemplateHandler here so we can add some…, Jinja2OutputHandler, Jinja2TemplateHandler (+1 more)

### Community 108 - "Application Scaling Example"
Cohesion: 0.33
Nodes (6): Application Scaling Example, application_scaling, containers list, load_balancer configuration, my-service-scaling ECS service, services section

### Community 109 - "MySQLDatabaseManager"
Cohesion: 0.20
Nodes (5): MySQLDatabaseManager, Model my sqldatabase manager behavior., Use ``mysqldump`` to dump the remote database as SQL to a local file. If…, List the MySQLDatabase objects in the config file. Returns: A list of…, Render for dump. Returns: Operation result.

### Community 110 - ".render_mysql_command"
Cohesion: 0.20
Nodes (5): Return the MySQL version of the MySQL server. Example: If the server version is…, Show the GRANTs for the database user on the remote database. Args: obj: The…, Render mysql command. Args: sql: sql. user: user. password: password. Returns:…, Render for server version. Args: user: user. password: password. Returns:…, Render for show grants. Returns: Operation result.

### Community 113 - "deployfish/events.py"
Cohesion: 0.16
Nodes (11): EventScheduleRuleAdapter, EventTargetAdapter, Any, Get cluster arn. Returns: Operation result., # TODO: use VpcConfigurationMixin for this, Get vpc configuration. Returns: Operation result., Convert. Returns: Operation result., # TODO: Deal with placementConstraints, placementStrategy and… (+3 more)

### Community 114 - "Service"
Cohesion: 0.04
Nodes (37): If this is a FARGATE task definition, return ``True``. Otherwise return…, Model service helper task behavior., Command. Returns: Operation result., Ssh command all instances. Args: cmd: cmd. Returns: Operation result., Model service behavior. Args: data: data., Name. Returns: Operation result., Return the version tag on the container image for the first container in the…, Launch type. Returns: Operation result. (+29 more)

### Community 116 - "Secret"
Cohesion: 0.04
Nodes (43): DecryptionFailed, ExternalSecret, Any, Exception, Diff our list of Secrets against `other`. `other` is either a list of Secrets…, Manage our SSM Parameter Store parameters. This differs from Args: model: model., Initialize SecretManager. Args: model: model. Keyword Args: readonly: readonly., Handle describe parameters. Args: key: key. option: option. Returns: Operation… (+35 more)

### Community 117 - ".convert"
Cohesion: 0.40
Nodes (3): Any, Get task definition. Args: secrets: secrets. Returns: Operation result., Convert. Returns: Operation result.

### Community 118 - "deployfish-mysql plugin"
Cohesion: 0.22
Nodes (9): deploy mysql create, deploy mysql dump, deploy mysql load, deploy mysql show-grants, deploy mysql update, deploy mysql validate, deployfish-mysql plugin, ~/.deployfish.yml (+1 more)

### Community 119 - "Modular Plugin Architecture"
Cohesion: 0.25
Nodes (9): Deployfish Plugin System, deployfish-slack Plugin, ~/.deployfish.yml User Config, deployfish-sqs Plugin, Extensible Custom Modules, Cement Application Plugins, DeployfishCementPluginHandler, Modular Plugin Architecture (+1 more)

### Community 124 - "test_service_discovery_model.py"
Cohesion: 0.28
Nodes (3): _paginate(), TestServiceDiscoveryNamespaceManager, TestServiceDiscoveryServiceManager

### Community 125 - "CloudWatchLogStreamManager"
Cohesion: 0.32
Nodes (5): CloudWatchLogStreamManager, Model cloud watch log stream manager behavior., Handle get group and stream from pk. Args: pk: pk. Returns: Operation result., Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., .. note:: ``log_group_name`` stays required because listing every stream in…

### Community 126 - ".list_all"
Cohesion: 0.29
Nodes (4): List all the ServiceHelperTasks. To do this accurately, we need to: * List all…, List. Args: scheduled_only: scheduled only. Returns: Operation result., List all Tasks (StandaloneTasks and ServiceHelperTasks), filtering by various…, List only the scheduled tasks, filtering by various dimensions. We do this by…

### Community 128 - "LoadBalancerListenerRule"
Cohesion: 0.11
Nodes (10): LoadBalancerListenerRule, Get many. Args: pks: pks. Keyword Args: _: . Returns: Operation result., Model load balancer listener rule behavior. Args: data: data. listener_arn:…, Pk. Returns: Operation result., Name. Returns: Operation result., Arn. Returns: Operation result., Load balancer. Returns: Operation result., Listener. Returns: Operation result. (+2 more)

### Community 129 - "table.py"
Cohesion: 0.11
Nodes (14): is used for click commands, and gets re-raised when we get other exceptions so…, Initialize RenderException. Args: msg: msg. exit_code: exit code., Initialize NoSuchConfigSection. Args: section: section., Initialize NoSuchConfigSectionItem. Args: section: section. name: name., RenderException, AbstractRenderer, Any, Initialize renderer base class. Args: *args: Positional renderer configuration.… (+6 more)

### Community 130 - "registry.py"
Cohesion: 0.22
Nodes (5): AdapterRegistry, Initialize AdapterRegistry., Register a new Adapter class with a model and a source. :param model_name: the…, Return the source -> model Adapter class to use for the source ``source`` and…, A registry of adapters which consume specific data sources to configure…

### Community 131 - "Tutorial 2 Extended Service"
Cohesion: 0.25
Nodes (8): Tutorial 1 Minimal Service, hello-world-test minimal service, services section, Tutorial 2 Extended Service, container command override, container environment variables, hello-world-test with command and env, services section

### Community 133 - "models/abstract.py"
Cohesion: 0.04
Nodes (34): Any, Delete. Args: obj: obj. Keyword Args: _: ., Model scalable target manager behavior., Get a single ScalableTarget. Args: pk: pk. Keyword Args: _: . Returns:…, List. Returns: Operation result., Model scaling policy manager behavior., Save. Args: obj: obj. Keyword Args: _: ., Delete. Args: obj: obj. Keyword Args: _: . (+26 more)

### Community 135 - ".convert"
Cohesion: 0.33
Nodes (4): Any, Initialize adapter with raw source data. Args: data: Raw source data to adapt.…, Copy one source value into output payload. Args: data: Destination payload…, Convert source payload into model constructor inputs. Returns: Tuple of adapted…

### Community 136 - ".list_all"
Cohesion: 0.33
Nodes (4): List all the StandaloneTasks, which means return the list of StandaloneTasks…, Filter ``tasks`` by various dimensions, returning only those tasks that match…, is_fnmatch_filter(), Use this function to determine if a string is a fnmatch filter, which is to say…

### Community 139 - ".parse"
Cohesion: 0.29
Nodes (4): Any, Deployfish supports putting 'config.KEY' as the value for the host and port…, Host. Returns: Operation result., Host port. Returns: Operation result.

### Community 140 - ".display_deployments"
Cohesion: 0.33
Nodes (4): Any, Display deployments. Args: deployments: deployments., Display events. Args: events: events., Waiting. Args: status: status. response: response. num_attempts: num attempts.…

### Community 141 - "Interpolation Test Config"
Cohesion: 0.09
Nodes (18): Any, Initialize ConfigProcessor. Args: config: config. context: context., Terraform Integration Example, {environment}/{service-name}/{cluster-name} replacements, services with terraform values, terraform section, ${terraform.*} string interpolation, terraform.lookups key mappings (+10 more)

### Community 142 - "SupportsSecrets"
Cohesion: 0.12
Nodes (10): Protocol, setter, Model supports secrets behavior., Prefix. Returns: Operation result., Prefix. Args: value: value., Secrets. Returns: Operation result., Value. Returns: Operation result., Value. Args: value: value. (+2 more)

### Community 145 - "TestServiceDiscoveryExtended"
Cohesion: 0.15
Nodes (3): _paginate(), TestServiceDiscoveryExtended, TestSMSecretManager

### Community 148 - "TestSSHMixinHelpers"
Cohesion: 0.27
Nodes (3): Establish an SSH tunnel. Args: tunnel: the tunnel config Keyword Args: verbose:…, _instance(), TestSSHMixinHelpers

### Community 149 - ".__init__"
Cohesion: 0.33
Nodes (3): Initialize ECSTaskStatusHook. Args: obj: obj., Initialize ECSDeploymentStatusWaiterHook. Args: obj: obj., Initialize ECSTaskLogsHook. Args: obj: obj.

### Community 150 - "mysql section in deployfish.yml"
Cohesion: 0.33
Nodes (6): deployfish.core.models.rds, Relational Database Service, deployfish.core.models.ssh, SSH, mysql section in deployfish.yml, AWS SSM Parameter Store

### Community 151 - "DeployfishApp (cement.App subclass)"
Cohesion: 0.33
Nodes (6): Cement CLI Framework, Click Colorful Output, deployfish.config Module, DeployfishApp (cement.App subclass), Jinja2 Templates, Architecture Doc Reference

### Community 153 - "Multi-Container Task Example"
Cohesion: 0.33
Nodes (6): Multi-Container Task Example, container links, three-container task definition, mysql db container with alias, redis sidecar container, services section

### Community 154 - "Terraform Interpolate Test"
Cohesion: 0.40
Nodes (6): Terraform Interpolate Test, foobar-prod service, foobar-qa service, foobar-qa and foobar-prod services, terraform section with {environment} statefile, mysql QA and prod tunnels

### Community 159 - "test_service_manager_list.py"
Cohesion: 0.60
Nodes (3): _cluster_paginator(), _service_paginator(), TestServiceManagerList

### Community 161 - ".get_cached"
Cohesion: 0.40
Nodes (3): Any, Return secret diff summary. Args: other: Secrets to compare against current…, Return cached value or populate and cache it. Args: key: Cache key. populator:…

### Community 162 - "ECS service configuration example"
Cohesion: 0.40
Nodes (5): deployfish.core.models.ecs, Elastic Container Service, Classic Load Balancing, deployfish.core.models.elb, ECS service configuration example

### Community 163 - "Renderers"
Cohesion: 0.40
Nodes (5): deployfish.renderers.abstract, deployfish.renderers.misc, deployfish.renderers.table, Renderers, Reference

### Community 164 - "Autoscaling Group Example"
Cohesion: 0.40
Nodes (5): Autoscaling Group Example, autoscalinggroup_name, load_balancer configuration, my-service ECS service, services section

### Community 165 - "Volume Mounts Example"
Cohesion: 0.40
Nodes (5): Volume Mounts Example, named volume with driver config, services section, host path volume mounts, task-level volumes definition

### Community 166 - "test CI job"
Cohesion: 0.40
Nodes (5): make cov, make test, test CI job, Tests GitHub Actions Workflow, uv package manager

### Community 167 - "AGENTS.md"
Cohesion: 0.20
Nodes (9): AGENTS.md, Architecture (Required), AWS Interaction, Documentation Contract (Required), graphify, Implementation Priority (Required), Post-Implementation Quality Gate (Required), Project Structure (Mandatory) (+1 more)

### Community 169 - ".__init__"
Cohesion: 0.33
Nodes (4): _default_start_time_ms(), Initialize CloudWatchLogGroupTailer. Args: group: group. stream_prefix: stream…, :param start_time datetime: a timezone aware, UTC datetime Args: stream:…, Compute default tail start time in milliseconds. Args: sleep: Polling interval…

### Community 179 - ".service"
Cohesion: 0.50
Nodes (3): setter, Service. Returns: Operation result., Service. Args: value: value.

### Community 180 - "Sphinx"
Cohesion: 0.50
Nodes (4): Sphinx, sphinx_rtd_theme, Read the Docs Configuration, docs/source/conf.py Sphinx configuration

### Community 181 - "deployfish.core.models.abstract"
Cohesion: 0.50
Nodes (4): Abstract, deployfish.core.models.abstract, Application Scaling, deployfish.core.models.appscaling

### Community 182 - "Parameter Store Example"
Cohesion: 0.50
Nodes (4): Parameter Store Example, config section for Parameter Store secrets, my-service with secrets config, services section

### Community 188 - "napoleon-gate documentation enforcement"
Cohesion: 0.67
Nodes (3): Documentation Contract, napoleon-gate documentation enforcement, Post-Implementation Quality Gate

### Community 189 - "California Institute of Technology"
Cohesion: 0.67
Nodes (3): Chris Malek, California Institute of Technology, MIT License

### Community 192 - "core/adapters/deployfish/__init__.py"
Cohesion: 0.18
Nodes (8): Any, Convert. Returns: Operation result., .. code-block:: python { 'namespace': 'local', 'name': 'test', 'dns_records': […, ServiceDiscoveryServiceAdapter, Any, Convert. Returns: Operation result., Model sshtunnel adapter behavior., SSHTunnelAdapter

### Community 193 - ".__init__"
Cohesion: 0.40
Nodes (3): Any, Initialize LoadBalancerListenerRuleManager., Initialize LoadBalancerListenerRule. Args: data: data. listener_arn: listener…

### Community 195 - "Config and Config Processors"
Cohesion: 0.67
Nodes (3): config, config_processors, Config and Config Processors

### Community 196 - "deployfish.main"
Cohesion: 0.67
Nodes (3): Application configuration, deployfish.main, Main

### Community 197 - "No Load Balancer Example"
Cohesion: 0.67
Nodes (3): No Load Balancer Example, service without load balancer, services section

## Knowledge Gaps
- **188 isolated node(s):** `deploy-complete.bash script`, `Meta`, `deployfish`, `Tooling Preflight (Required)`, `Post-Implementation Quality Gate (Required)` (+183 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **64 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Service` connect `Service` to `models/ecs.py`, `Manager`, `Instance`, `Tutorial 2 Extended Service`, `ObjectLoader`, `bind_controller`, `SupportsModel`, `deployfish/controllers/__init__.py`, `TaskDefinition`, `Interpolation Test Config`, `TaskDefinitionFARGATEMixin`, `TestServiceManagerSaveUpdate`, `TestServiceRestart`, `._get_command_specific_data`, `TestServiceHelperTaskNew`, `Cluster`, `ECSServiceCommands`, `ServiceHelperTaskAdapter`, `TestServiceRenderForDiff`, `TestSSHMixinHelpers`, `EFSFileSystem`, `TestServiceUpdateAppscaling`, `TestServiceSave`, `.new`, `.reload_secrets`, `Annotator`, `test_service_manager_list.py`, `Autoscaling Group Example`, `test_ssh_main_controller_push.py`, `setter`, `ECSDeploymentStatusWaiterHook`, `.service`, `_DockerHost`, `_service_from_yml`, `AutoscalingGroup`, `ecs/__init__.py`, `slack/hooks.py`, `.get`, `No Load Balancer Example`, `TestServiceManagerCreate`, `StandaloneTask`, `Model`, `.get_many`, `Basic ECS Services Example`, `Python Dependencies`, `TestServiceRelatedObjects`, `Application Scaling Example`, `_service_without_appscaling`, `TestServiceProperties`, `Secret`, `TestServiceSSHNetworking`?**
  _High betweenness centrality (0.196) - this node is a cross-community bridge._
- **Why does `Model` connect `Model` to `models/ecs.py`, `Manager`, `LoadBalancerListenerRule`, `Instance`, `TaskTagImporter`, `models/abstract.py`, `ObjectLoader`, `DeployfishArgparseController`, `SupportsModel`, `deployfish/controllers/__init__.py`, `TaskDefinition`, `SupportsSecrets`, `TaskDefinitionFARGATEMixin`, `Cluster`, `ObjectReadOnly`, `CloudWatchLogGroup`, `EFSFileSystem`, `LoadBalancerListener`, `ClassicLoadBalancerTarget`, `Any`, `LoadBalancer`, `ECSDeploymentStatusWaiterHook`, `.secret`, `MySQLDatabase`, `AutoscalingGroup`, `.get`, `EventTarget`, `ServiceDiscoveryNamespace`, `StandaloneTask`, `CloudwatchAlarmManager`, `EventScheduleRuleManager`, `.render_for_update`, `Service`, `Secret`, `CloudWatchLogStreamManager`?**
  _High betweenness centrality (0.155) - this node is a cross-community bridge._
- **Why does `SchemaException` connect `models/ecs.py` to `Manager`, `Instance`, `TaskTagImporter`, `DeployfishArgparseController`, `TaskDefinition`, `TestStandaloneTaskAdapter_schedule_FARGATE`, `TaskDefinitionFARGATEMixin`, `Cluster`, `ServiceHelperTaskAdapter`, `ObjectReadOnly`, `ContainerDefinitionAdapter`, `exceptions.py`, `StandaloneTaskAdapter`, `ServiceAdapter`, `Adapter`, `TaskDefinitionAdapter`, `TerraformS3State`, `StandaloneTask`, `TestContainerDefinitionAdapterComprehensive`, `TestServiceHelperTaskAdapter_schedule_EC2`, `TestServiceHelperTaskAdapter_schedule_FARGATE`, `TestStandaloneTaskAdapter_schedule_EC2`, `Service`?**
  _High betweenness centrality (0.136) - this node is a cross-community bridge._
- **Are the 127 inferred relationships involving `Service` (e.g. with `ServiceHelperTaskAdapter` and `LazyAttributeMixin`) actually correct?**
  _`Service` has 127 INFERRED edges - model-reasoned connections that need verification._
- **Are the 92 inferred relationships involving `Model` (e.g. with `MultipleObjectsReturned` and `ObjectDoesNotExist`) actually correct?**
  _`Model` has 92 INFERRED edges - model-reasoned connections that need verification._
- **Are the 85 inferred relationships involving `Instance` (e.g. with `Manager` and `Model`) actually correct?**
  _`Instance` has 85 INFERRED edges - model-reasoned connections that need verification._
- **Are the 92 inferred relationships involving `Manager` (e.g. with `MultipleObjectsReturned` and `ObjectDoesNotExist`) actually correct?**
  _`Manager` has 92 INFERRED edges - model-reasoned connections that need verification._