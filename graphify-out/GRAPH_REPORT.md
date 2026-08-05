# Graph Report - deployfish  (2026-08-04)

## Corpus Check
- 208 files · ~134,126 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4352 nodes · 9205 edges · 237 communities (181 shown, 56 thin omitted)
- Extraction: 80% EXTRACTED · 20% INFERRED · 0% AMBIGUOUS · INFERRED: 1872 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `83126caa`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- models/ecs.py
- Model
- SSMSSHProvider
- Instance
- TaskTagImporter
- handle_model_exceptions
- ObjectLoader
- TestServiceManagerUpdateSave
- TableRenderer
- bind_controller
- SupportsModel
- main.py
- check_napoleon_gate.py
- ContainerDefinition
- SchemaException
- TaskDefinitionFARGATEMixin
- TargetGroupTableRenderer
- Config
- ext_df_jinja2.py
- ._get_command_specific_data
- .new
- Cluster
- ECSServiceSSH
- ServiceHelperTaskAdapter
- ObjectDoesNotExist
- CloudWatchLogGroup
- RDSInstance
- .get
- ConfigProcessingFailed
- ex
- StandaloneTaskAdapter
- .new
- Annotator
- ServiceAdapter
- LoadBalancerListener
- ClassicLoadBalancerTarget
- get_task
- Any
- DeployfishApp
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
- VPC
- ECSDeploymentStatusWaiterHook
- ContainerDefinitionAdapter
- ScalingPolicy
- Quality Gate Recovery Master Plan
- _DockerHost
- MySQLDatabase
- _service_from_yml
- conftest.py
- utils/mixins.py
- AbstractWaiterHook
- .get
- ecs/__init__.py
- TaskDefinitionAdapter
- GitMixin
- slack/hooks.py
- Models and Managers
- .get
- EventTarget
- TerraformS3State
- create_hooked_waiter_with_client
- TargetGroupTarget
- Any
- ServiceDiscoveryNamespace
- Service
- .__init__
- ServiceDiscoveryServiceManager
- .parse
- .annotate
- Any
- RDSManager
- test_elbv2_managers.py
- _SecretsHost
- .__process
- ECSTaskStatusHook
- establish_tunnel
- .convert
- CloudwatchAlarmManager
- NoReturn
- Basic ECS Services Example
- Python Dependencies
- TestContainerDefinitionAdapterComprehensive
- test_core_ssh.py
- _event_timestamp_to_utc
- .annotate
- .render
- .__call__
- .major_server_version
- Installation
- test_elbv2_coverage_push.py
- DockerMixin
- .render_for_update
- CodeNameVersionMixin
- mysql/__init__.py
- TestServiceRelatedObjects
- TestServiceHelperTaskAdapter_schedule_EC2
- TestServiceHelperTaskAdapter_schedule_FARGATE
- TestStandaloneTaskAdapter_schedule_EC2
- DeployfishJinja2TemplateHandler
- .kms_key_id
- MySQLDatabaseManager
- .render_mysql_command
- _service_without_appscaling
- _SecretsHost
- .convert
- .is_fargate
- BastionSSHProvider
- SecretManager
- ScalingPolicyManager
- deployfish-mysql plugin
- Modular Plugin Architecture
- Interpolation Test Config
- SSHMixin
- test_ecs_service_render.py
- TestServiceDiscoveryServiceManagerPush
- test_service_discovery_model.py
- CloudWatchLogStreamManager
- .list_all
- .get_many
- LoadBalancerListenerRule
- table.py
- AdapterRegistry
- Tutorial 2 Extended Service
- .ssh_noninteractive
- CloudwatchAlarm
- _paginate
- .convert
- .list_all
- Any
- Any
- .parse
- .display_deployments
- Terraform Integration Example
- SupportsSecrets
- TestServiceManagerSaveUpdate
- .save
- TestServiceDiscoveryExtended
- ScalableTargetManager
- TestServiceHelperTaskNew
- NoSSHTargetAvailable
- .__init__
- mysql section in deployfish.yml
- DeployfishApp (cement.App subclass)
- test_cloudwatchlogs_manager.py
- Multi-Container Task Example
- Terraform Interpolate Test
- test_appscaling_model.py
- _paginate
- test_elb_managers.py
- .render_for_create
- test_service_manager_list.py
- .reload_secrets
- .get_cached
- ECS service configuration example
- Renderers
- Autoscaling Group Example
- Volume Mounts Example
- test CI job
- AGENTS.md
- CloudWatchLogGroupManager
- .__init__
- .get
- .__init__
- .tags
- SMSecret
- TestTaskDefinitionManager
- .dump
- .load
- .render_for_validate
- .secret
- .service
- Sphinx
- deployfish.core.models.abstract
- Parameter Store Example
- test_secrets_external_push.py
- .get_event_tailer
- .get
- SchemaException
- set_app
- napoleon-gate documentation enforcement
- California Institute of Technology
- .copy
- deploy-complete.bash
- .convert
- .__init__
- .render_for_diff
- Config and Config Processors
- deployfish.main
- No Load Balancer Example
- test_ecs_cluster_task_push.py
- .arn
- .log_streams
- .pk
- .__iter__
- .pk
- graphify Knowledge Graph Usage Rules
- deployfish.core.loaders
- Lazy Loading from AWS
- Jinja2 ChoiceLoader for Plugins
- Plugin Adapter (convert method)
- 80% Line Coverage Gate
- TestSecretModel
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
9. `SchemaException` - 79 edges
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

## Communities (237 total, 56 thin omitted)

### Community 0 - "models/ecs.py"
Cohesion: 0.02
Nodes (103): LazyAttributeMixin, Model lazy attribute mixin behavior., Model scalable target behavior. Args: data: data. policies: policies., Pk. Returns: Operation result., Name. Returns: Operation result., ScalableTarget, Tags. Returns: Operation result., Model security group behavior. (+95 more)

### Community 1 - "Model"
Cohesion: 0.03
Nodes (93): Manager, Model, Get many. Args: pks: pks. Keyword Args: _: ., Model model behavior. Args: data: data., Exists. Returns: Operation result., Save. Returns: Operation result., Handle str. Returns: Operation result., Model manager behavior. (+85 more)

### Community 2 - "SSMSSHProvider"
Cohesion: 0.19
Nodes (7): r""" Implement our SSH commands via AWS Systems Manager SSH connections…, Return a shell command suitable for establishing an interactive ssh session. If…, Build a command that will tunnel through an SSM connection to an instance to…, Return a shell command suitable for uploading a file through an ssh tunnel to…, SSMSSHProvider, _instance(), TestAbstractSSHProvider

### Community 3 - "Instance"
Cohesion: 0.03
Nodes (43): AutoscalingGroup, Instance, Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., List. Returns: Operation result., List. Args: vpc_ids: vpc ids. image_ids: image ids. instance_types: instance…, Model autoscaling group behavior., Pk. Returns: Operation result., Name. Returns: Operation result. (+35 more)

### Community 4 - "TaskTagImporter"
Cohesion: 0.04
Nodes (34): Any, Task related tags we need to read from a task definition associated with a…, Initialize TaskTagImporter., Scale. Args: obj: obj. count: count., Initialize TaskDefinition. Args: data: data. containers: containers., Capacity Provider Strategies are stored in tags like::…, Logging. Returns: Operation result., If a constraint is a "memberOf" constraint: 'deployfish:placementConstraint.0':… (+26 more)

### Community 5 - "handle_model_exceptions"
Cohesion: 0.04
Nodes (43): ex, Change desired count for a service., Scale the number of instances in an ECS Cluster to match ``count``. ..…, ex, ex, ex, get_ssh_target(), ObjectSSHController (+35 more)

### Community 6 - "ObjectLoader"
Cohesion: 0.05
Nodes (44): ECSCluster, Model ecscluster behavior., ECSStandaloneTask, Model ecsstandalone task behavior., DeployfishObjectDoesNotExist, DeployfishSectionDoesNotExist, ObjectLoader, ObjectNotManaged (+36 more)

### Community 7 - "TestServiceManagerUpdateSave"
Cohesion: 0.17
Nodes (3): ServiceManager update/save/scale coverage., TestServiceManagerListValidation, TestServiceManagerUpdateSave

### Community 8 - "TableRenderer"
Cohesion: 0.05
Nodes (66): ArgparseController, ECSClusterSSH, Meta, Parse a date string in the form YYYY-MM-DD and return a datetime. Args: s: s.…, Model ecscluster ssh behavior., valid_date(), CrudBase, Meta (+58 more)

### Community 9 - "bind_controller"
Cohesion: 0.06
Nodes (33): ECSServiceCommands, Model ecsservice commands behavior., ECSService, ECSServiceStandaloneTasks, Controller, Valid date. Args: s: s. Returns: Operation result., Model ecsservice standalone tasks behavior., Model ecsservice behavior. (+25 more)

### Community 10 - "SupportsModel"
Cohesion: 0.04
Nodes (54): Meta, AbstractSSHProvider, Abstract class that provides the methods that ``SSHMixin`` will use to stablish…, Return a shell command suitable for establish an interactive ssh session. Args:…, Return a shell command suitable for establishing a "docker exec" session into a…, Return a shell command suitable for establishing an ssh tunnel through…, Return a shell command suitable for uploading a file through an ssh tunnel to…, Protocol (+46 more)

### Community 11 - "main.py"
Cohesion: 0.08
Nodes (37): Base, BaseService, BaseServiceDockerExec, BaseServiceSecrets, BaseServiceSSH, filename_envvar(), maybe_rename_existing_file(), Meta (+29 more)

### Community 12 - "check_napoleon_gate.py"
Cohesion: 0.07
Nodes (63): AST, _check_file(), _check_function_doc(), _constructor_has_args(), _first_doc_line(), _function_has_args(), _function_has_keyword_args(), _function_uses_return_or_yield() (+55 more)

### Community 13 - "ContainerDefinition"
Cohesion: 0.07
Nodes (16): ContainerDefinition, SecretsMixin, Copy. Returns: Operation result., Handle add. Args: other: other. Returns: Operation result., Model container definition behavior. Args: data: data., Pk. Returns: Operation result., Name. Returns: Operation result., Version. Returns: Operation result. (+8 more)

### Community 14 - "SchemaException"
Cohesion: 0.09
Nodes (12): Model terraform state factory behavior., New. Args: terraform_config: terraform config. context: context. Returns:…, TerraformStateFactory, There was a schema validation problem in the deployfish.yml file., SchemaException, Additional coverage for deployfish.core.adapters.deployfish.ecs., TestServiceHelperTaskAdapter_EC2, TestStandaloneTaskAdapter_EC2 (+4 more)

### Community 15 - "TaskDefinitionFARGATEMixin"
Cohesion: 0.06
Nodes (28): Any, Model task definition fargatemixin behavior., If this is a FARGATE task definition, return ``True``. Otherwise return…, Return the minimum necessary cpu for our task by summing up 'cpu' from each of…, For FARGATE tasks, task cpu is required and must be one of the values listed in…, For EC2 tasks, set task cpu if 'cpu' is provided, don't set otherwise. If 'cpu'…, Set task cpu requirement, based on whether this is a FARGATE task or an EC2…, Find the minimum necessary memory and maximum necessary memory for our task by… (+20 more)

### Community 16 - "TargetGroupTableRenderer"
Cohesion: 0.09
Nodes (10): Specialized renderer for ECS target groups., Render attached load balancer names. Args: obj: Target group being rendered.…, Render target names. Args: obj: Target group being rendered. _key: Unused…, Render listener protocol/port pairs. Args: obj: Target group being rendered.…, Render backing container protocol/port pair. Args: obj: Target group being…, TargetGroupTableRenderer, TestTargetGroupTableRendererGaps, TestLBListenerTableRenderer (+2 more)

### Community 17 - "Config"
Cohesion: 0.04
Nodes (37): Config, NoSuchSectionError, NoSuchSectionItemError, Any, Session, setter, Initialize config state from a file path or provided payload. Args: filename:…, Returns: The pre-interpolated version of the raw YAML. (+29 more)

### Community 18 - "ext_df_jinja2.py"
Cohesion: 0.10
Nodes (20): color(), fromtimestamp(), lb_listener_table(), load(), Any, Render table for target groups. Args: data: Target-group-like row objects.…, Render table for ELBv2 listeners. Args: data: Listener-like row objects.…, Bind custom template handler. Args: app: Cement application instance. Side… (+12 more)

### Community 19 - "._get_command_specific_data"
Cohesion: 0.13
Nodes (11): Any, Update the deployfish-specific environment variables in the container…, Build a dict that takes info from the service and overlays the generic (not…, Args: data: the ``tasks:`` section from our service definition in…, Change old style command defintions that look like this: tasks: - family:…, Build a dict that takes info from the output of :py:meth:`_get_base_task_data`…, Convert. Returns: Operation result., Set a ``data[data_key]`` on the dict ``data`` by looking at both ``task`` and… (+3 more)

### Community 20 - ".new"
Cohesion: 0.08
Nodes (10): Stable identity key used by baseline filtering., Construct and optionally interpolate a config object. Keyword Args: kwargs:…, Lazy load the deployfish.yml file. We only load it on request because most…, Lazy load the deployfish.yml file into a :py:class:`deployfish.config.Config`…, Path, TestConfigExtended, Path, TestConfigModule (+2 more)

### Community 21 - "Cluster"
Cohesion: 0.02
Nodes (56): Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., List. Args: vpc_id: vpc id. Returns: Operation result., Model subnet behavior., Pk. Returns: Operation result., Name. Returns: Operation result., Cidr block. Returns: Operation result., Available ips. Returns: Operation result., Subnet (+48 more)

### Community 22 - "ECSServiceSSH"
Cohesion: 0.08
Nodes (26): ECSServiceCommandLogs, Meta, Controller, Model ecsservice command logs behavior., LogsCloudWatchLogGroup, LogsCloudWatchLogStream, ex, Model logs cloud watch log group behavior. (+18 more)

### Community 23 - "ServiceHelperTaskAdapter"
Cohesion: 0.06
Nodes (8): The problem here is that, unlike all our other adapters, we need to create…, ServiceHelperTaskAdapter, TestServiceHelperTaskAdapterComprehensive, BaseTestServiceHelperTaskAdapter_basic, If we have no vpc_configuration, our network mode should be forced to 'bridge'., Ensure old style command definitions still work: tasks: - family: foobar-test-…, If we have vpc_configuration, our network mode should be forced to 'awsvpc'., TestServiceHelperTaskAdapter_FARGATE

### Community 24 - "ObjectDoesNotExist"
Cohesion: 0.14
Nodes (19): BaseMultipleObjectsReturned, BaseOperationFailed, DoesNotExist, ImproperlyConfigured, MultipleObjectsReturned, OperationFailed, Delete. Args: obj: obj. Keyword Args: _: ., We tried to get a single object but it does not exist in AWS. (+11 more)

### Community 25 - "CloudWatchLogGroup"
Cohesion: 0.08
Nodes (30): CloudWatchLogGroup, CloudWatchLogGroupTailer, CloudWatchLogStream, CloudWatchLogStreamIterator, CloudWatchLogStreamTailer, An iterator class that allows you to tail live logs from a CloudWatchLogStream.…, An iterator class that allows you to tail live logs from a CloudWatchLogStream.…, Handle iter. Returns: Operation result. (+22 more)

### Community 26 - "RDSInstance"
Cohesion: 0.06
Nodes (16): Status. Returns: Operation result., Returns: The engine for this RDS instance (e.g. "mysql"), Returns: The version of the engine for this RDS instance., Returns: The hostname of the db endpoint, Returns: The port for this RDS instance (e.g. "mysql"), Returns: The username of the root user for this instance., Secret enabled. Returns: Operation result., Returns: The ARN of the Secrets Manager Secret used to store the password for… (+8 more)

### Community 27 - ".get"
Cohesion: 0.12
Nodes (9): List. Args: load_balancer: load balancer. Returns: Operation result., Handle get rules for load balancer. Args: load_balancer_pk: load balancer pk.…, Handle get rules for target group. Args: target_group_arn: target group arn.…, List. Args: listener_arn: listener arn. load_balancer_pk: load balancer pk.…, Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., Ssl certificates. Returns: Operation result., Load balancer. Returns: Operation result., Load balancer. Returns: Operation result. (+1 more)

### Community 28 - "ConfigProcessingFailed"
Cohesion: 0.12
Nodes (29): BaseSkipConfigProcessing, AbstractConfigProcessor, ProcessingFailed, A base class for processors for our our ``deployfish.yml`` file. These…, Return all known replacements for ``deployfish.yml`` section name…, SkipConfigProcessing, EnvironmentConfigProcessor, # TODO: need to deal with multiple matches in the same line (+21 more)

### Community 29 - "ex"
Cohesion: 0.12
Nodes (9): ex, Create waiter. Args: obj: obj. Keyword Args: _: ., Create an object in AWS from configuration in deployfish.yml., Update waiter. Args: obj: obj. Keyword Args: _: ., Update an object in AWS from configuration in deployfish.yml., Delete waiter. Args: obj: obj. Keyword Args: _: ., Delete an object from AWS by primary key., Show details about a single object in AWS. (+1 more)

### Community 30 - "StandaloneTaskAdapter"
Cohesion: 0.08
Nodes (8): SecretsMixin, Model standalone task adapter behavior., StandaloneTaskAdapter, TestAbstractTaskAdapterBranches, TestStandaloneTaskAdapterComprehensive, BaseTestStandaloneTaskAdapter_basic, If we have vpc_configuration, our network mode should be forced to 'awsvpc'., TestStandaloneTaskAdapter_FARGATE

### Community 31 - ".new"
Cohesion: 0.05
Nodes (9): New. Args: obj: obj. source: source. Keyword Args: kwargs: kwargs. Returns:…, TestServiceProperties, TestServiceRenderForDiff, TestServiceUpdateAppscaling, TestServiceDeployfishEnvironment, TestServiceRestart, TestServiceSave, TestService_new (+1 more)

### Community 32 - "Annotator"
Cohesion: 0.08
Nodes (20): Annotator, process_service_update(), Get the authors for the most recent commits. Returns: Operation result., Get the committer for the most recent commits. Returns: Operation result., Get the deployer for the most recent commits. Returns: Operation result., Get the version for the most recent commits. Returns: Operation result., Get the name of the service. Returns: Operation result., Get the name of the service. Returns: Operation result. (+12 more)

### Community 33 - "ServiceAdapter"
Cohesion: 0.07
Nodes (17): Any, SecretsMixin, Update ``data`` with the configuration for the Service itself. This will look…, * Service itself [x] Args: data: data., Build a list of Secret and ExternalSecret objects from our Service's config:…, Handle build task definition. Args: kwargs: kwargs., Handle build application scaling objects. Args: kwargs: kwargs., Handle build service discovery service. Args: kwargs: kwargs. (+9 more)

### Community 34 - "LoadBalancerListener"
Cohesion: 0.08
Nodes (17): LoadBalancerListener, Listeners. Returns: Operation result., Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., Model load balancer listener behavior., Pk. Returns: Operation result., Name. Returns: Operation result., Arn. Returns: Operation result., Port. Returns: Operation result. (+9 more)

### Community 35 - "ClassicLoadBalancerTarget"
Cohesion: 0.06
Nodes (17): ClassicLoadBalancerTarget, Any, List. Args: load_balancer_name: load balancer name. Returns: Operation result., Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., Ssl policy. Returns: Operation result., Model classic load balancer target behavior. Args: data: data. instance:…, Initialize ClassicLoadBalancerTarget. Args: data: data. instance: instance., Pk. Returns: Operation result. (+9 more)

### Community 36 - "get_task"
Cohesion: 0.11
Nodes (13): get_task(), ex, Build a ``deployfish.core.waiters.HookedWaiter`` for the operation named…, Show info about a ServiceHelperTask object associated with a Service that…, List the helper tasks associated with a Service in AWS., Return the ``ServiceHelperTask`` whose related to ``obj`` whose command name…, Update command definitions in AWS independently of their Service., If a command for a Service has a schedule rule and that rule is currently… (+5 more)

### Community 37 - "Any"
Cohesion: 0.08
Nodes (16): Any, Get. Args: pk: pk. Keyword Args: _: ., Save. Args: obj: obj. Keyword Args: _: ., Exists. Args: pk: pk. Returns: Operation result., Diff. Args: obj: obj. Returns: Operation result., Needs update. Args: obj: obj. Returns: Operation result., Given an appropriate bit of data `obj` from a data source `source`, return the…, Is a factory method. .. note:: The ``**kwargs`` here is for the Adapter to use,… (+8 more)

### Community 38 - "DeployfishApp"
Cohesion: 0.12
Nodes (17): DeployfishAppError, Model deployfish app error behavior., DeployfishApp, main(), maybe_do_cli_debugging(), Meta, post_arg_parse_build_boto3_session(), App (+9 more)

### Community 39 - "ECSServiceScalingPolicyAdapter"
Cohesion: 0.08
Nodes (22): ECSServiceScalableTargetAdapter, ECSServiceScalingPolicyAdapter, Any, .. code-block:: python Args: data: data., Initialize ECSServiceScalableTargetAdapter. Args: data: data. Keyword Args:…, .. code-block:: python Args: data: data., Get resource id. Returns: Operation result., Convert. Returns: Operation result. (+14 more)

### Community 40 - "DeployfishCementPluginHandler"
Cohesion: 0.09
Nodes (18): DeployfishCementPluginHandler, get_deployfish_plugins(), load(), Meta, App, Cement plugin extension module., Load plugin. Args: plugin_name: plugin name., Load a list of plugins. Args: plugins: A list of plugin names to load. (+10 more)

### Community 41 - "Parameter Store Secrets Tutorial"
Cohesion: 0.07
Nodes (30): ECS Lifecycle Management, Terraform State Integration, SecretAdapter, ServiceAdapter, Service.save Creation Flow, TaskDefinitionAdapter, Basic ECS Service Tutorial, hello-world-test Service Example (+22 more)

### Community 42 - "Adapter"
Cohesion: 0.10
Nodes (21): Adapter, Return whether exactly one value in ``data`` is truthy. Args: data: Boolean…, Given a dict of data from a data source, convert it appropriate data Args:…, ECSServiceCPUAlarmAdapter, .. code-block:: python Args: data: data., # TODO: if the host_path doesn't start with a /, ensure that, EventScheduleRuleAdapter, EventTargetAdapter (+13 more)

### Community 43 - "LoadBalancer"
Cohesion: 0.08
Nodes (14): LoadBalancer, Get many. Args: pks: pks. Keyword Args: kwargs: kwargs. Returns: Operation…, Model load balancer behavior., Pk. Returns: Operation result., Name. Returns: Operation result., Arn. Returns: Operation result., Lb type. Returns: Operation result., Scheme. Returns: Operation result. (+6 more)

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
Cohesion: 0.09
Nodes (18): ExternalParameterException, parse_secret_string(), Any, Exception, Parse an identifier from a deployfish.yml parameter definition that looks like…, Model secret adapter behavior. Args: data: data., Initialize SecretAdapter. Args: data: data. Keyword Args: kwargs: kwargs., Is external. Returns: Operation result. (+10 more)

### Community 49 - "VPC"
Cohesion: 0.09
Nodes (13): Get many. Args: pks: pks. Keyword Args: kwargs: kwargs. Returns: Operation…, Pk. Returns: Operation result., Name. Returns: Operation result., Cidr block. Returns: Operation result., Bastion. Returns: Operation result., Provisioner. Returns: Operation result., List. Args: name: name. Returns: Operation result., VPC (+5 more)

### Community 50 - "ECSDeploymentStatusWaiterHook"
Cohesion: 0.11
Nodes (10): Service waiter. Args: obj: obj. Keyword Args: kwargs: kwargs., Delete waiter. Args: obj: obj. Keyword Args: kwargs: kwargs., Show periodic updates while we change desired count for a service. Args: obj:…, ECSDeploymentStatusWaiterHook, Success. Args: status: status. response: response. num_attempts: num attempts.…, Failure. Args: status: status. response: response. num_attempts: num attempts.…, for both the 'services_stable' and 'services_inactive' waiters on ECS. Args:…, Timeout. Args: status: status. response: response. num_attempts: num attempts.… (+2 more)

### Community 51 - "ContainerDefinitionAdapter"
Cohesion: 0.09
Nodes (17): ContainerDefinitionAdapter, Any, Convert our deployfish YAML definition of our containers to the same format…, ``deployfish.yml`` port mappings look like this:: ports: - "80" - "8443:443" -…, ``deployfish.yml`` environment variables are defined in one of the two…, ``deployfish.yml`` docker labels are defined in one of the two following ways::…, Get ulimits. Returns: Operation result., Get log configuration. Returns: Operation result. (+9 more)

### Community 52 - "ScalingPolicy"
Cohesion: 0.18
Nodes (5): Model scaling policy behavior. Args: data: data. alarm: alarm., Pk. Returns: Operation result., Name. Returns: Operation result., ScalingPolicy, TestScalingPolicyManager

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

### Community 60 - ".get"
Cohesion: 0.12
Nodes (8): Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., Get. Args: pk: pk. vpc_id: vpc id. Keyword Args: _: . Returns: Operation result., Get many. Args: pks: pks. vpc_id: vpc id. Keyword Args: _: . Returns: Operation…, Arn. Returns: Operation result., Name. Returns: Operation result., Subnet. Returns: Operation result., Vpc. Returns: Operation result., Vpc. Returns: Operation result.

### Community 61 - "ecs/__init__.py"
Cohesion: 0.13
Nodes (13): AbstractTaskAdapter, Any, When creating :py:class:`deployfish.core.models.ecs.ServiceHelperTask` objects,…, Model vpc configuration mixin behavior., Get vpc configuration. Args: source: source. Returns: Operation result., Model abstract task adapter behavior., Return ``True ``if this task definition is for FARGATE, ``False`` otherwise.…, Construct the dict that will be given as input for configuring an… (+5 more)

### Community 62 - "TaskDefinitionAdapter"
Cohesion: 0.13
Nodes (9): Any, Convert our deployfish YAML definition of our task definition to the same…, :rtype: dict(str, Any), dict(str, Any) Returns: Operation result., Initialize TaskDefinitionAdapter. Args: data: data. secrets: secrets.…, In the YAML, volume definitions look like this:: volumes: - name: 'string'…, TaskDefinitionAdapter, Copy. Returns: Operation result., TestTaskDefinitionAdapterComprehensive (+1 more)

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
Cohesion: 0.03
Nodes (44): datetime, List. Args: cluster: cluster. service: service. family: family.…, :param pk str: a string like "{cluster}:{container_instance_id}" Args: pk: pk.…, :param cluster str: the name of an ECS cluster Args: cluster: cluster. Returns:…, List. Args: cluster_name: cluster name. Returns: Operation result., :param pk str: cluster name Args: pk: pk. Returns: Operation result., Handle get service and cluster from pk. Args: pk: pk. Returns: Operation result., :param pk str: a string like "{cluster_name}:{service_name}" Args: pk: pk.… (+36 more)

### Community 67 - "EventTarget"
Cohesion: 0.06
Nodes (18): Any, Convert. Returns: Operation result., EventTarget, Any, Delete. Args: obj: obj. Keyword Args: _: ., :py:attr:`data` here has the same structure as what is returned by Args: data:…, New. Args: obj: obj. source: source. Keyword Args: kwargs: kwargs. Returns:…, Initialize EventTarget. Args: data: data. rule: rule. (+10 more)

### Community 68 - "TerraformS3State"
Cohesion: 0.07
Nodes (19): Any, Model terraform s3 state behavior. Args: terraform_config: terraform config.…, Initialize TerraformS3State. Args: terraform_config: terraform config. context:…, Retrive our statefile from S3 Args: state_file_url: state file url. profile:…, Handle load pre version 12. Args: tfstate: tfstate., Handle load post version 12. Args: tfstate: tfstate., Load. Args: replacements: replacements., Initialize TerraformEnterpriseState. Args: terraform_config: terraform config.… (+11 more)

### Community 69 - "create_hooked_waiter_with_client"
Cohesion: 0.15
Nodes (9): Get waiter. Args: waiter_name: waiter name. Returns: Operation result., create_hooked_waiter_with_client(), HookedWaiter, :type name: string :param name: The name of the waiter :type config:…, Wait. Keyword Args: kwargs: kwargs., :type waiter_name: str :param waiter_name: The name of the waiter. The name…, A HookedWaiter is almost exactly like a standard boto3 Waiter with one…, TestCreateHookedWaiterWithClient (+1 more)

### Community 70 - "TargetGroupTarget"
Cohesion: 0.12
Nodes (9): Model target group target behavior., Pk. Returns: Operation result., Name. Returns: Operation result., Port. Returns: Operation result., Health. Returns: Operation result., Target. Returns: Operation result., Target group. Returns: Operation result., List. Args: target_group_arn: target group arn. Returns: Operation result. (+1 more)

### Community 71 - "Any"
Cohesion: 0.25
Nodes (5): Any, Render for diff. Returns: Operation result., Initialize ServiceDiscoveryService. Args: data: data. Keyword Args: kwargs:…, Render for diff. Returns: Operation result., Render for create. Returns: Operation result.

### Community 72 - "ServiceDiscoveryNamespace"
Cohesion: 0.09
Nodes (11): Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., Model service discovery namespace behavior., Pk. Returns: Operation result., Name. Returns: Operation result., Arn. Returns: Operation result., Namespace. Returns: Operation result., List. Keyword Args: private_only: private only. Returns: Operation result., ServiceDiscoveryNamespace (+3 more)

### Community 73 - "Service"
Cohesion: 0.03
Nodes (69): Get task definition. Args: secrets: secrets. Returns: Operation result., ContainerInstance, DockerMixin, An ECS Task Definition. Args: data: data. containers: containers., If this task definition exists in AWS, return our ``<family>:<revision>``…, Name. Returns: Operation result., Launch type. Returns: Operation result., Family. Returns: Operation result. (+61 more)

### Community 74 - ".__init__"
Cohesion: 0.25
Nodes (5): Any, Replace. Args: obj: obj. key: key. value: value. section_name: section name.…, Initialize EnvironmentConfigProcessor. Args: config: config. context: context., Handle load env file. Args: filename: filename. Returns: Operation result., Load per item environment. Args: section_name: section name. item_name: item…

### Community 75 - "ServiceDiscoveryServiceManager"
Cohesion: 0.16
Nodes (9): Pk looks like '{namespace_pk}:{service_name}' Args: pk: pk. Returns: Operation…, `pk` is just a bare service name. Args: pk: pk. Returns: Operation result., `pk` is one of:: * a service id, which starts with "srv-" * a string like…, List. Args: namespace: namespace. Returns: Operation result., Delete. Args: obj: obj. Keyword Args: _: ., Pk. Returns: Operation result., Model service discovery service manager behavior., `pk` is a service['Id']: "srv-{hexstring}" Args: pk: pk. Returns: Operation… (+1 more)

### Community 76 - ".parse"
Cohesion: 0.12
Nodes (8): Deployfish supports putting 'config.KEY' as the value for the host and port…, Host. Returns: Operation result., User. Returns: Operation result., Db. Returns: Operation result., Password. Returns: Operation result., Character set. Returns: Operation result., Collation. Returns: Operation result., Port. Returns: Operation result.

### Community 77 - ".annotate"
Cohesion: 0.14
Nodes (9): GitChangelogMixin, Any, Look through the commits between the current version and the last version…, needs to be used after GitMixin in the inheritance chain., Look through the commits between the current version and the last version…, Annotate. Args: values: values., Annotate. Args: values: values., Annotate. Args: values: values. (+1 more)

### Community 78 - "Any"
Cohesion: 0.17
Nodes (8): Any, Render byte count into human-readable units. Args: value: Byte count to format.…, Render values using builtin datatype formatting rules. Args: value: Value to…, Reformat one value into a more human-friendly form. Args: obj: Source object…, Render one column value for one row object. Args: obj: Source object for the…, Render all rows into a formatted table string. Args: data: Sequence of row-like…, Initialize table renderer. Args: columns: Column configuration keyed by output…, Dereference one column from an object or rendered mapping. Args: obj: Source…

### Community 79 - "RDSManager"
Cohesion: 0.14
Nodes (8): Model rdsmanager behavior., Root password. Returns: Operation result., Subnets. Returns: Operation result., Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., Security groups. Returns: Operation result., Vpc. Returns: Operation result., List. Returns: Operation result., RDSManager

### Community 80 - "test_elbv2_managers.py"
Cohesion: 0.19
Nodes (5): _paginate(), TestLoadBalancerListenerManager, TestLoadBalancerListenerRuleManager, TestLoadBalancerManager, TestTargetGroupManager

### Community 81 - "_SecretsHost"
Cohesion: 0.24
Nodes (4): Any, SecretsMixin, _SecretsHost, TestSecretsMixinWriteSecrets

### Community 82 - ".__process"
Cohesion: 0.16
Nodes (8): Any, Perform string replacements on ``value``, a string value in our…, Process ``obj``, a value from a key of an item from ``deployfish.yml``, looking…, Process ``obj``, a list value of an item from ``deployfish.yml``, looking for…, Recurse through each key in our dict ``obj`` and process it appropriately. We…, Is the method that :py:class:`ConfigProcessor` will execute as it loops through…, Initialize AbstractConfigProcessor. Args: config: config. context: context., Populate :py:attr:`deployfish_lookups`.

### Community 83 - "ECSTaskStatusHook"
Cohesion: 0.15
Nodes (7): Run task waiter. Args: tasks: tasks. Keyword Args: kwargs: kwargs., ECSTaskStatusHook, for the 'tasks_stopped'' waiters on ECS, and prints the status of our tasks on…, Waiting. Args: status: status. response: response. num_attempts: num attempts.…, Success. Args: status: status. response: response. num_attempts: num attempts.…, Timeout. Args: status: status. response: response. num_attempts: num attempts.…, TestECSTaskStatusHook

### Community 84 - "establish_tunnel"
Cohesion: 0.18
Nodes (9): establish_tunnel(), get_tunnel(), get_tunnel_target(), Actually establish an SSH Tunnel. This does not return until the user manually…, Return an ``Instance`` object through which the user can make an ssh tunnel. If…, If we didn't get a specific tunnel to use, present the user with a list of all…, TestEstablishTunnel, TestGetTunnel (+1 more)

### Community 85 - ".convert"
Cohesion: 0.15
Nodes (7): Any, Initialize ECSServiceCPUAlarmAdapter. Args: data: data. Keyword Args: kwargs:…, Get alarm name. Returns: Operation result., Get alarm description. Returns: Operation result., Get comparison operator. Returns: Operation result., Get threshold. Returns: Operation result., Convert. Returns: Operation result.

### Community 86 - "CloudwatchAlarmManager"
Cohesion: 0.18
Nodes (7): CloudwatchAlarmManager, Arn. Returns: Operation result., Model cloudwatch alarm manager behavior., Get. Args: pk: pk. Keyword Args: kwargs: kwargs. Returns: Operation result., List. Args: cluster: cluster. service: service. Keyword Args: kwargs: kwargs.…, Save. Args: obj: obj. Keyword Args: kwargs: kwargs., Delete. Args: obj: obj. Keyword Args: kwargs: kwargs.

### Community 87 - "NoReturn"
Cohesion: 0.15
Nodes (7): Save. Args: obj: obj. Keyword Args: _: ., Save. Args: obj: obj. Keyword Args: kwargs: kwargs., Delete. Args: obj: obj. Keyword Args: kwargs: kwargs., Save. Args: obj: obj. Keyword Args: kwargs: kwargs., Delete. Args: obj: obj. Keyword Args: kwargs: kwargs., Delete. Args: obj: obj. Keyword Args: _: ., NoReturn

### Community 88 - "Basic ECS Services Example"
Cohesion: 0.17
Nodes (13): Basic ECS Services Example, load_balancer with target_group_arn, load_balancer with load_balancer_name, my-service-alb (ALB target group), my-service-elb (Classic ELB), network_mode: bridge, services section, task_role_arn IAM role (+5 more)

### Community 89 - "Python Dependencies"
Cohesion: 0.15
Nodes (13): Python Dependencies, boto3 dependency, cement dependency, click dependency, docker dependency, gitpython dependency, jinja2 dependency, jsondiff2 dependency (+5 more)

### Community 91 - "test_core_ssh.py"
Cohesion: 0.23
Nodes (6): build_sigint_handler(), Build signal handler for catching SIGINT (Control-C) while we are exec'ed into…, _instance(), TestBastionSSHProvider, TestBuildSigintHandler, TestSSMSSHProvider

### Community 92 - "_event_timestamp_to_utc"
Cohesion: 0.20
Nodes (8): _event_timestamp_to_utc(), Any, datetime, Convert CloudWatch millisecond timestamps to aware UTC datetimes. Args:…, Handle next. Returns: Operation result., Handle next. Returns: Operation result., :param start_time datetime: a timezone aware, UTC datetime Args: stream:…, Handle next. Returns: Operation result.

### Community 93 - ".annotate"
Cohesion: 0.20
Nodes (8): ImproperlyConfiguredError, Exception, Path, Process a pyproject.toml file and return the name and version. Raises:…, Extract some stuff from setup.py, if present. If setup.py is present, we'll add…, We programmers improperly configured something., Process a setup.py file and return the name and version. Raises: ValueError: if…, Process a Makefile and return the name and version. Raises: ValueError: if the…

### Community 94 - ".render"
Cohesion: 0.11
Nodes (10): Render for display. Returns: Operation result., Render for diff. Returns: Operation result., Render. Returns: Operation result., Render for display. Returns: Operation result., Render for diff. Returns: Operation result., Render. Returns: Operation result., Render for display. Returns: Operation result., Render for display. Returns: Operation result. (+2 more)

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

### Community 99 - "DockerMixin"
Cohesion: 0.22
Nodes (7): DockerMixin, NoRunningTasks, Docker exec. Returns: Operation result., Model docker mixin behavior. Args: *args: args., Return running invoked tasks associated with this object., Exec into a container running on an EC2 backed ECS Service. If ``ssh_target``…, Exec into a container using the ECS Exec capability of AWS Systems Manager.…

### Community 100 - ".render_for_update"
Cohesion: 0.20
Nodes (6): Any, Save. Args: obj: obj. Keyword Args: kwargs: kwargs., Scale. Args: count: count. force: force., Render for update. Returns: Operation result., Render for diff. Returns: Operation result., Initialize Instance. Args: data: data.

### Community 101 - "CodeNameVersionMixin"
Cohesion: 0.40
Nodes (4): CodeNameVersionMixin, Model code name version mixin behavior., Path, TestCodeNameVersionMixin

### Community 102 - "mysql/__init__.py"
Cohesion: 0.25
Nodes (8): pre_config_interpolate_add_mysql_section(), App, Add our "mysql" section to the list of sections on which keyword interpolation…, add_template_dir(), load(), App, Add template dir. Args: app: app., Load. Args: app: app.

### Community 107 - "DeployfishJinja2TemplateHandler"
Cohesion: 0.20
Nodes (8): DeployfishJinja2OutputHandler, DeployfishJinja2TemplateHandler, Meta, We're subclassing the cement Jinja2OutputHandler here so we can use our own…, We're subclassing the cement Jinja2TemplateHandler here so we can add some…, Jinja2OutputHandler, Jinja2TemplateHandler, TestExtJinja2RemainingFilters

### Community 108 - ".kms_key_id"
Cohesion: 0.20
Nodes (7): setter, Prefix. Returns: Operation result., Prefix. Args: value: value., Kms key id. Returns: Operation result., Kms key id. Args: value: value., Value. Returns: Operation result., Value. Args: value: value.

### Community 109 - "MySQLDatabaseManager"
Cohesion: 0.20
Nodes (5): MySQLDatabaseManager, Model my sqldatabase manager behavior., List the MySQLDatabase objects in the config file. Returns: A list of…, Create. Args: root_user: root user. root_password: root password. ssh_target:…, Is an alias for :py:meth:`create`. Args: obj: The ``MySQLDatabase`` object…

### Community 110 - ".render_mysql_command"
Cohesion: 0.20
Nodes (5): Return the MySQL version of the MySQL server. Example: If the server version is…, Show the GRANTs for the database user on the remote database. Args: obj: The…, Render mysql command. Args: sql: sql. user: user. password: password. Returns:…, Render for server version. Args: user: user. password: password. Returns:…, Render for show grants. Returns: Operation result.

### Community 112 - "_SecretsHost"
Cohesion: 0.24
Nodes (4): Any, SecretsMixin, _SecretsHost, TestSecretsMixin

### Community 113 - ".convert"
Cohesion: 0.25
Nodes (5): Any, Get cluster arn. Returns: Operation result., Get vpc configuration. Returns: Operation result., Convert. Returns: Operation result., Convert. Returns: Operation result.

### Community 114 - ".is_fargate"
Cohesion: 0.17
Nodes (6): If this is a FARGATE task definition, return ``True``. Otherwise return…, Ssh command all instances. Args: cmd: cmd. Returns: Operation result., Ssh target. Returns: Operation result., Ssh targets. Returns: Operation result., Do an interactive SSH session to ``ssh_target``. This method will not exit…, Run a command on ``ssh_target`` via ssh. This method will not exit until the…

### Community 115 - "BastionSSHProvider"
Cohesion: 0.15
Nodes (7): BastionSSHProvider, Initialize AbstractSSHProvider. Args: instance: instance. Keyword Args:…, Find the public-facing bastion host in the VPC in which :py:attr:`instance`…, Initialize BastionSSHProvider. Args: instance: instance. Keyword Args: verbose:…, Tunnel. Args: local_port: local port. target_host: target host. host_port: host…, Initialize DockerMixin. Args: *args: args. Keyword Args: kwargs: kwargs., TestBastionSSHProviderExtended

### Community 116 - "SecretManager"
Cohesion: 0.21
Nodes (8): Manage our SSM Parameter Store parameters. This differs from Args: model: model., Handle describe parameters. Args: key: key. option: option. Returns: Operation…, Handle get parameter values. Args: names: names. Keyword Args: decrypt:…, Convert. Args: parameter_data: parameter data. Returns: Operation result., .. note:: We need both encryption metadata from ``describe_parameters`` and…, List. Args: prefix: prefix. Keyword Args: decrypt: decrypt. Returns: Operation…, Delete. Args: obj: obj. Keyword Args: _: ., SecretManager

### Community 117 - "ScalingPolicyManager"
Cohesion: 0.22
Nodes (6): Get a single ScalableTarget. Args: pk: pk. Keyword Args: _: . Returns:…, Model scaling policy manager behavior., Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., Arn. Returns: Operation result., List. Args: cluster: cluster. service: service. Returns: Operation result., ScalingPolicyManager

### Community 118 - "deployfish-mysql plugin"
Cohesion: 0.22
Nodes (9): deploy mysql create, deploy mysql dump, deploy mysql load, deploy mysql show-grants, deploy mysql update, deploy mysql validate, deployfish-mysql plugin, ~/.deployfish.yml (+1 more)

### Community 119 - "Modular Plugin Architecture"
Cohesion: 0.25
Nodes (9): Deployfish Plugin System, deployfish-slack Plugin, ~/.deployfish.yml User Config, deployfish-sqs Plugin, Extensible Custom Modules, Cement Application Plugins, DeployfishCementPluginHandler, Modular Plugin Architecture (+1 more)

### Community 120 - "Interpolation Test Config"
Cohesion: 0.22
Nodes (9): Interpolation Test Config, service config secrets, ${env.*} environment variable interpolation, foobar-prod production service, network_mode: host, services section, terraform section, tunnels section (+1 more)

### Community 121 - "SSHMixin"
Cohesion: 0.20
Nodes (6): Model sshmixin behavior., Return an Instance that an be targeted by .ssh()., Return all :py:class:`deployfish.core.models.ec2.Instance` objects associated…, Return an Instance that an be targeted by :py:meth:`tunnel` For EC2 backed ECS…, Return an list of Instances that an be targeted by :py:meth:`tunnel`. For EC2…, SSHMixin

### Community 122 - "test_ecs_service_render.py"
Cohesion: 0.22
Nodes (4): _aws_service(), TestFargateServiceProperties, TestServiceRenderMethods, TestTaskDefinitionProperties

### Community 124 - "test_service_discovery_model.py"
Cohesion: 0.28
Nodes (3): _paginate(), TestServiceDiscoveryNamespaceManager, TestServiceDiscoveryServiceManager

### Community 125 - "CloudWatchLogStreamManager"
Cohesion: 0.32
Nodes (5): CloudWatchLogStreamManager, Model cloud watch log stream manager behavior., Handle get group and stream from pk. Args: pk: pk. Returns: Operation result., Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., .. note:: ``log_group_name`` stays required because listing every stream in…

### Community 126 - ".list_all"
Cohesion: 0.29
Nodes (4): List all the ServiceHelperTasks. To do this accurately, we need to: * List all…, List. Args: scheduled_only: scheduled only. Returns: Operation result., List all Tasks (StandaloneTasks and ServiceHelperTasks), filtering by various…, List only the scheduled tasks, filtering by various dimensions. We do this by…

### Community 127 - ".get_many"
Cohesion: 0.25
Nodes (4): Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., Get many. Args: pks: pks. Keyword Args: kwargs: kwargs. Returns: Operation…, Load balancers. Returns: Operation result.

### Community 128 - "LoadBalancerListenerRule"
Cohesion: 0.13
Nodes (8): LoadBalancerListenerRule, Get many. Args: pks: pks. Keyword Args: _: . Returns: Operation result., Model load balancer listener rule behavior. Args: data: data. listener_arn:…, Pk. Returns: Operation result., Name. Returns: Operation result., Arn. Returns: Operation result., .. note:: Deployfish assumes relevant target group is attached to first…, .. note:: The dumb thing here is that you can't ask the target group itself…

### Community 129 - "table.py"
Cohesion: 0.11
Nodes (14): is used for click commands, and gets re-raised when we get other exceptions so…, Initialize RenderException. Args: msg: msg. exit_code: exit code., Initialize NoSuchConfigSection. Args: section: section., Initialize NoSuchConfigSectionItem. Args: section: section. name: name., RenderException, AbstractRenderer, Any, Initialize renderer base class. Args: *args: Positional renderer configuration.… (+6 more)

### Community 130 - "AdapterRegistry"
Cohesion: 0.25
Nodes (5): AdapterRegistry, Initialize AdapterRegistry., Register a new Adapter class with a model and a source. :param model_name: the…, Return the source -> model Adapter class to use for the source ``source`` and…, A registry of adapters which consume specific data sources to configure…

### Community 131 - "Tutorial 2 Extended Service"
Cohesion: 0.25
Nodes (8): Tutorial 1 Minimal Service, hello-world-test minimal service, services section, Tutorial 2 Extended Service, container command override, container environment variables, hello-world-test with command and env, services section

### Community 132 - ".ssh_noninteractive"
Cohesion: 0.16
Nodes (10): Any, Spawn interactive shell command for long-lived terminal sessions. Args:…, Return a shell command suitable for running a command-line command via ssh on…, Ssh. Args: command: command. Returns: Operation result., Return ``True`` if ``data`` is a file-like object, ``False`` otherwise. Args:…, Run a command on ``ssh_target`` via ssh. This method will not exit until the…, Spawn shell syntax safely via an explicit shell executable. Args: command:…, _spawn_interactive_shell_command() (+2 more)

### Community 133 - "CloudwatchAlarm"
Cohesion: 0.13
Nodes (8): CloudwatchAlarm, Pk. Returns: Operation result., Name. Returns: Operation result., Set policy arn. Args: arn: arn., Model cloudwatch alarm behavior., TestScalableTargetManager, TestCloudwatchAlarmModel, TestEFSFileSystemModel

### Community 135 - ".convert"
Cohesion: 0.33
Nodes (4): Any, Initialize adapter with raw source data. Args: data: Raw source data to adapt.…, Copy one source value into output payload. Args: data: Destination payload…, Convert source payload into model constructor inputs. Returns: Tuple of adapted…

### Community 136 - ".list_all"
Cohesion: 0.33
Nodes (4): List all the StandaloneTasks, which means return the list of StandaloneTasks…, Filter ``tasks`` by various dimensions, returning only those tasks that match…, is_fnmatch_filter(), Use this function to determine if a string is a fnmatch filter, which is to say…

### Community 137 - "Any"
Cohesion: 0.28
Nodes (5): Any, Initialize ScalingPolicy. Args: data: data. alarm: alarm., Render for diff. Returns: Operation result., Initialize ScalableTarget. Args: data: data. policies: policies., Render for diff. Returns: Operation result.

### Community 138 - "Any"
Cohesion: 0.25
Nodes (5): Any, Diff our list of Secrets against `other`. `other` is either a list of Secrets…, Initialize SecretManager. Args: model: model. Keyword Args: readonly: readonly., Initialize Secret. Args: data: data. name: name., Render for diff. Returns: Operation result.

### Community 139 - ".parse"
Cohesion: 0.29
Nodes (4): Any, Deployfish supports putting 'config.KEY' as the value for the host and port…, Host. Returns: Operation result., Host port. Returns: Operation result.

### Community 140 - ".display_deployments"
Cohesion: 0.33
Nodes (4): Any, Display deployments. Args: deployments: deployments., Display events. Args: events: events., Waiting. Args: status: status. response: response. num_attempts: num attempts.…

### Community 141 - "Terraform Integration Example"
Cohesion: 0.18
Nodes (9): Any, Initialize ConfigProcessor. Args: config: config. context: context., Terraform Integration Example, {environment}/{service-name}/{cluster-name} replacements, services with terraform values, terraform section, ${terraform.*} string interpolation, terraform.lookups key mappings (+1 more)

### Community 142 - "SupportsSecrets"
Cohesion: 0.22
Nodes (5): Protocol, Model supports secrets behavior., Secrets. Returns: Operation result., Secrets. Args: value: value., SupportsSecrets

### Community 144 - ".save"
Cohesion: 0.22
Nodes (4): List names. Args: prefix: prefix. Returns: Operation result., Save. Args: obj: obj. Keyword Args: _: . Returns: Operation result., Delete many by name. Args: pks: pks., Render for create. Returns: Operation result.

### Community 145 - "TestServiceDiscoveryExtended"
Cohesion: 0.15
Nodes (3): _paginate(), TestServiceDiscoveryExtended, TestSMSecretManager

### Community 146 - "ScalableTargetManager"
Cohesion: 0.25
Nodes (5): Delete. Args: obj: obj. Keyword Args: _: ., Model scalable target manager behavior., List. Returns: Operation result., Delete. Args: obj: obj. Keyword Args: _: ., ScalableTargetManager

### Community 148 - "NoSSHTargetAvailable"
Cohesion: 0.13
Nodes (9): NoSSHTargetAvailable, Exception, Push. Args: filename: filename. Keyword Args: run: run. Returns: Operation…, Do an interactive SSH session to Instance. This method will not exit until the…, Establish an SSH tunnel. Args: tunnel: the tunnel config Keyword Args: verbose:…, Run shell syntax safely via an explicit shell executable. Args: command: Shell…, Upload a file via ssh to a remote instance. If ``ssh_target`` is not provided,…, _run_shell_command() (+1 more)

### Community 149 - ".__init__"
Cohesion: 0.33
Nodes (3): Initialize ECSTaskStatusHook. Args: obj: obj., Initialize ECSDeploymentStatusWaiterHook. Args: obj: obj., Initialize ECSTaskLogsHook. Args: obj: obj.

### Community 150 - "mysql section in deployfish.yml"
Cohesion: 0.33
Nodes (6): deployfish.core.models.rds, Relational Database Service, deployfish.core.models.ssh, SSH, mysql section in deployfish.yml, AWS SSM Parameter Store

### Community 151 - "DeployfishApp (cement.App subclass)"
Cohesion: 0.33
Nodes (6): Cement CLI Framework, Click Colorful Output, deployfish.config Module, DeployfishApp (cement.App subclass), Jinja2 Templates, Architecture Doc Reference

### Community 152 - "test_cloudwatchlogs_manager.py"
Cohesion: 0.32
Nodes (3): _paginate(), TestCloudWatchLogGroupManager, TestCloudWatchLogStreamManager

### Community 153 - "Multi-Container Task Example"
Cohesion: 0.33
Nodes (6): Multi-Container Task Example, container links, three-container task definition, mysql db container with alias, redis sidecar container, services section

### Community 154 - "Terraform Interpolate Test"
Cohesion: 0.40
Nodes (6): Terraform Interpolate Test, foobar-prod service, foobar-qa service, foobar-qa and foobar-prod services, terraform section with {environment} statefile, mysql QA and prod tunnels

### Community 156 - "_paginate"
Cohesion: 0.18
Nodes (4): _paginate(), TestInstanceManagerGaps, TestSecurityGroupManagerGaps, TestVPCManagerGaps

### Community 158 - ".render_for_create"
Cohesion: 0.40
Nodes (3): Save. Args: obj: obj. Keyword Args: _: ., Render for create. Returns: Operation result., Save. Args: obj: obj. Keyword Args: _: . Returns: Operation result.

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

### Community 168 - "CloudWatchLogGroupManager"
Cohesion: 0.33
Nodes (4): CloudWatchLogGroupManager, Model cloud watch log group manager behavior., Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., List. Args: prefix: prefix. Returns: Operation result.

### Community 169 - ".__init__"
Cohesion: 0.33
Nodes (4): _default_start_time_ms(), Initialize CloudWatchLogGroupTailer. Args: group: group. stream_prefix: stream…, :param start_time datetime: a timezone aware, UTC datetime Args: stream:…, Compute default tail start time in milliseconds. Args: sleep: Polling interval…

### Community 170 - ".get"
Cohesion: 0.33
Nodes (3): Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., Arn. Returns: Operation result., Modified username. Returns: Operation result.

### Community 173 - "SMSecret"
Cohesion: 0.09
Nodes (15): Name. Returns: Operation result., Arn. Returns: Operation result., Manage our Secrets Manager secrets. This differs from…, Kms key id. Returns: Operation result., Description. Returns: Operation result., Rotation enabled. Returns: Operation result., Last rotated. Returns: Operation result., Value. Returns: Operation result. (+7 more)

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

### Community 186 - "SchemaException"
Cohesion: 0.67
Nodes (3): BaseSchemaException, Raise this if data in the config source does not validate properly., SchemaException

### Community 187 - "set_app"
Cohesion: 0.67
Nodes (3): App, Store active Cement app for config helpers. Args: app: Cement app whose config…, set_app()

### Community 188 - "napoleon-gate documentation enforcement"
Cohesion: 0.67
Nodes (3): Documentation Contract, napoleon-gate documentation enforcement, Post-Implementation Quality Gate

### Community 189 - "California Institute of Technology"
Cohesion: 0.67
Nodes (3): Chris Malek, California Institute of Technology, MIT License

### Community 190 - ".copy"
Cohesion: 0.17
Nodes (6): Copy. Returns: Operation result., .. note:: Ideally here we would compare the full task definition attached to…, Save. Args: obj: obj. Keyword Args: _: . Returns: Operation result., Create. Args: obj: obj. Returns: Operation result., Update. Args: obj: obj. Returns: Operation result., Render for update. Returns: Operation result.

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
- **176 isolated node(s):** `deploy-complete.bash script`, `Meta`, `deployfish`, `Tooling Preflight (Required)`, `Post-Implementation Quality Gate (Required)` (+171 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **56 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Service` connect `Service` to `models/ecs.py`, `Model`, `SSMSSHProvider`, `Instance`, `TaskTagImporter`, `Tutorial 2 Extended Service`, `ObjectLoader`, `TestServiceManagerUpdateSave`, `bind_controller`, `main.py`, `ContainerDefinition`, `SchemaException`, `TaskDefinitionFARGATEMixin`, `Terraform Integration Example`, `TestServiceManagerSaveUpdate`, `._get_command_specific_data`, `TestServiceHelperTaskNew`, `Cluster`, `ECSServiceSSH`, `ServiceHelperTaskAdapter`, `.new`, `.reload_secrets`, `Annotator`, `test_service_manager_list.py`, `get_task`, `Autoscaling Group Example`, `DeployfishApp`, `ECSServiceScalingPolicyAdapter`, `setter`, `ECSDeploymentStatusWaiterHook`, `.service`, `_DockerHost`, `_service_from_yml`, `ecs/__init__.py`, `slack/hooks.py`, `.get`, `No Load Balancer Example`, `test_ecs_cluster_task_push.py`, `Basic ECS Services Example`, `Python Dependencies`, `.render`, `TestServiceRelatedObjects`, `_service_without_appscaling`, `.is_fargate`, `BastionSSHProvider`, `test_ecs_service_render.py`?**
  _High betweenness centrality (0.187) - this node is a cross-community bridge._
- **Why does `Model` connect `Model` to `models/ecs.py`, `LoadBalancerListenerRule`, `Instance`, `TaskTagImporter`, `CloudwatchAlarm`, `ObjectLoader`, `TableRenderer`, `SupportsModel`, `main.py`, `ContainerDefinition`, `SupportsSecrets`, `TaskDefinitionFARGATEMixin`, `.save`, `ScalableTargetManager`, `Cluster`, `ObjectDoesNotExist`, `CloudWatchLogGroup`, `RDSInstance`, `ex`, `.render_for_create`, `LoadBalancerListener`, `ClassicLoadBalancerTarget`, `Any`, `CloudWatchLogGroupManager`, `.__init__`, `LoadBalancer`, `SMSecret`, `VPC`, `ECSDeploymentStatusWaiterHook`, `.secret`, `ScalingPolicy`, `MySQLDatabase`, `.copy`, `.get`, `EventTarget`, `TargetGroupTarget`, `ServiceDiscoveryNamespace`, `Service`, `ServiceDiscoveryServiceManager`, `RDSManager`, `CloudwatchAlarmManager`, `NoReturn`, `.render`, `.render_for_update`, `SecretManager`, `ScalingPolicyManager`, `CloudWatchLogStreamManager`?**
  _High betweenness centrality (0.162) - this node is a cross-community bridge._
- **Why does `SchemaException` connect `SchemaException` to `models/ecs.py`, `Model`, `TaskTagImporter`, `TableRenderer`, `ContainerDefinition`, `TaskDefinitionFARGATEMixin`, `Cluster`, `ServiceHelperTaskAdapter`, `ConfigProcessingFailed`, `StandaloneTaskAdapter`, `ServiceAdapter`, `Adapter`, `SchemaException`, `TaskDefinitionAdapter`, `TerraformS3State`, `Service`, `TestContainerDefinitionAdapterComprehensive`, `TestServiceHelperTaskAdapter_schedule_EC2`, `TestServiceHelperTaskAdapter_schedule_FARGATE`, `TestStandaloneTaskAdapter_schedule_EC2`?**
  _High betweenness centrality (0.104) - this node is a cross-community bridge._
- **Are the 127 inferred relationships involving `Service` (e.g. with `ServiceHelperTaskAdapter` and `LazyAttributeMixin`) actually correct?**
  _`Service` has 127 INFERRED edges - model-reasoned connections that need verification._
- **Are the 92 inferred relationships involving `Model` (e.g. with `MultipleObjectsReturned` and `ObjectDoesNotExist`) actually correct?**
  _`Model` has 92 INFERRED edges - model-reasoned connections that need verification._
- **Are the 85 inferred relationships involving `Instance` (e.g. with `Manager` and `Model`) actually correct?**
  _`Instance` has 85 INFERRED edges - model-reasoned connections that need verification._
- **Are the 92 inferred relationships involving `Manager` (e.g. with `MultipleObjectsReturned` and `ObjectDoesNotExist`) actually correct?**
  _`Manager` has 92 INFERRED edges - model-reasoned connections that need verification._