# Graph Report - .  (2026-08-25)

## Corpus Check
- 321 files · ~155,007 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4595 nodes · 9657 edges · 255 communities (190 shown, 65 thin omitted)
- Extraction: 80% EXTRACTED · 20% INFERRED · 0% AMBIGUOUS · INFERRED: 1956 edges (avg confidence: 0.53)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Core Model Managers
- ECS Tasks And Secrets
- EC2 Resource Managers
- ECS Service Lifecycle
- CRUD Controllers
- SSH And Exec Types
- Service CLI Controllers
- ECS Command Controllers
- ECS Service Tests
- Subnets And Tags
- Config Initialization
- Container Definition Adapter
- Service New Lifecycle Tests
- Napoleon Doc Gate
- Task Definition Model
- Controller Test Harness
- Object Loaders
- CloudWatch Log Tailers
- Fargate Task Mixins
- Service Adapter
- Service Manager CRUD
- Helper Task Adapter Tests
- Plugin Docs Index
- Terraform S3 State
- Config Processors
- RDS Instance Model
- Jinja2 Template Filters
- SQS Plugin Hooks
- Container Instance Model
- Container Schema Models
- AWS Session Builder
- Cement App Entry
- ALB Listener Model
- Standalone Task CLI
- App Scaling Adapter
- Service Secret Properties
- Cement Plugin Handler
- Target Group Renderer
- Adapter Base Classes
- Task Definition Adapter Tests
- Autoscaling Group Model
- Controller API Docs
- Load Balancer Model
- Task Volume Schema Tests
- SSM Secrets Model
- Classic ELB Targets
- SSM SSH Providers
- Render Exceptions
- README Project Overview
- YAML Tutorial Docs
- Secret Manager SSM
- Config Interpolation Tests
- Partial Pydantic Models
- ECS Service Waiters
- VPC Task Adapter Mixins
- Docker Host Mixin Tests
- Secrets Manager SMSecret
- MySQL Database Model
- Service Render Push Tests
- Pytest Boto Fixtures
- Service Discovery Model
- Core Utility Mixins
- Waiter Hook Base
- Model Render Diff
- Git Annotation Mixin
- Slack Plugin Hooks
- Secret Adapter
- CloudWatch Alarm Model
- Listener Rule Model
- Event Target Model
- Interactive SSH Session
- Layered Architecture Plan
- Helper Task Adapter
- Secrets Mixin Adapter
- Hooked Waiter Factory
- Target Group Targets
- Discovery Service CRUD
- Discovery Namespace Model
- Container Schema Tests
- Scaling Policy Model
- SupportsSecrets Protocol
- Discovery Service Manager
- Docker Exec Mixin
- MySQL Connection Fields
- SSH Tunnel Model
- Git Changelog Mixin
- Table Renderer
- ELBv2 Manager Tests
- Secrets Discovery Tests
- Standalone Task Adapter Tests
- Abstract Config Processor
- Container Schema Validators
- Task Definition Validators
- ECS Task Waiter Hooks
- SSH Tunnel Controller
- Listener Related Objects
- Event Schedule Rule
- SSH Command Spawn
- Pydantic Adapter ADRs
- Cluster Controller
- CPU Alarm Adapter
- Event Rule Copy New
- SSH SIGINT Handler
- Extensibility Architecture Docs
- Basic YAML Examples
- Python Package Dependencies
- Secrets CLI Commands
- Standalone Task Adapter
- Model Manager Cache
- Log Stream Iterator
- Event Rule Manager
- Project Metadata Mixins
- Waiter Hook Lifecycle
- MySQL Create Update
- Remote Access Architecture
- Service Manager Push Tests
- ELBv2 Coverage Tests
- Task Definition Adapter
- Listener Rule Manager
- Code Name Version Mixin
- Jinja2 Cement Handlers
- MySQL Plugin Loader
- Workload Definition Docs
- VPC Manager Gap Tests
- Service Properties Tests
- Discovery Manager Push Tests
- Helper Task EC2 Schedule Tests
- Helper Task Fargate Schedule Tests
- Standalone EC2 Schedule Tests
- Standalone Fargate Schedule Tests
- Scaling Policy Manager
- Secret Field Setters
- Listener Rule Matching Tests
- MySQL Database Manager
- MySQL Validate Commands
- Model Diff Equality Tests
- SecretsMixin Push Tests
- SecretsMixin Write Tests
- Environment Config Processor
- Task Volume Schema
- Events Adapter Convert
- Scaling Policy Render
- Secret Diff Render
- Plugin System Docs
- Interpolation YAML Fixture
- Discovery Model Tests
- Terraform Lookup Replace
- Port Mapping Schema Tests
- Tunnel Controller Commands
- Scalable Target Manager
- Log Stream Manager
- Scheduled Task Listing
- Classic ELB Manager
- ELBv2 Get Many
- Adapter Registry
- Tutorial YAML Examples
- Log Group Manager Tests
- Secret Manager Tests
- Standalone Launch Type Tests
- Agent Doc Contract
- Abstract Adapter Convert
- EC2 Instance Render
- Task List Filters
- Abstract Task Adapter Tests
- Event Rule Save Delete
- Deployment Waiter Display
- ELBv2 Architecture Docs
- Secrets Deployment Docs
- Terraform YAML Example
- Service Save Update Tests
- Project Structure Docs
- Scaling Policy Save
- Log Group Manager
- Log Tailer Init
- Helper Task New Tests
- Waiter Hook Init
- Cement App Architecture Docs
- App Scaling YAML Example
- Multi Container YAML Example
- Terraform Interpolate Fixture
- Classic ELB Manager Tests
- Service List Tests
- Standalone Task Convert
- Reload Secrets
- Tags Mixin
- Cached Secrets Diff Types
- ASG YAML Example
- Volume YAML Example
- GitHub Test Workflow
- Event Rule Manager Tests
- Model Lazy Init
- Log Group Tail Helpers
- EC2 Tags
- Task ARN PK Parsing
- SMSecret Value
- MySQL Create Alias
- MySQL SQL Load
- MySQL Show Grants
- MySQL Secret Lookup
- MySQL Service Binding
- Read The Docs Config
- Models API Docs
- Renderers API Docs
- Parameter Store YAML Example
- Scalable Target Model Tests
- Secret Model Tests
- License And Authors
- Schema Exception
- Bash Deploy Completion
- ConfigProcessor Init
- Discovery Adapter Convert
- SSH Adapter Convert
- Package Version
- Main App API Docs
- Adding Commands Guide
- No ELB YAML Example
- Scalable Target Manager Tests
- Log Group ARN
- Log Streams List
- Log Group PK
- Log Group Iterator
- Log Stream PK
- Loaders API Docs
- Plugin Controller Docs
- Plugin Model Docs
- Coverage Gate Docs
- Cohesive Class Architecture
- Botocraft Preference
- Author Glenn Bach
- Author Katarina Liu
- Contributing Guide
- Resource Attribute Guide
- Plugin Interpolation Hooks
- Uv Sync Setup
- Deploy Create Tutorial
- Deploy Scale Tutorial
- Env File Tutorial
- Environment Parameter Tutorial
- Application Scaling YAML Docs
- AWS Credentials YAML Docs
- Capacity Provider YAML Docs
- Service Discovery YAML Docs
- Scale Down Policy Example
- Scale Up Policy Example
- Pyproject Metadata

## God Nodes (most connected - your core abstractions)
1. `Service` - 231 edges
2. `Model` - 176 edges
3. `Instance` - 175 edges
4. `Manager` - 120 edges
5. `TaskDefinition` - 109 edges
6. `Cluster` - 109 edges
7. `InvokedTask` - 95 edges
8. `SchemaException` - 85 edges
9. `handle_model_exceptions()` - 81 edges
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
- **Advanced Cluster Access Commands** — docs_source_advanced_rst_bastion_host, docs_source_advanced_rst_deploy_cluster, docs_source_advanced_rst_deploy_service_ssh, docs_source_advanced_rst_deploy_service_exec, docs_source_api_adapters_ssh_rst_deployfish_core_adapters_deployfish_ssh [INFERRED 0.85]
- **deployfish.yml Adapter Modules** — docs_source_api_adapters_abstract_rst_deployfish_core_adapters_abstract, docs_source_api_adapters_mixins_rst_deployfish_core_adapters_deployfish_mixins, docs_source_api_adapters_appscaling_rst_deployfish_core_adapters_deployfish_appscaling, docs_source_api_adapters_cloudwatch_rst_deployfish_core_adapters_deployfish_cloudwatch, docs_source_api_adapters_ecs_rst_deployfish_core_adapters_deployfish_ecs, docs_source_api_adapters_events_rst_deployfish_core_adapters_deployfish_events, docs_source_api_adapters_service_discovery_rst_deployfish_core_adapters_deployfish_service_discovery, docs_source_api_adapters_ssh_rst_deployfish_core_adapters_deployfish_ssh [EXTRACTED 1.00]
- **Elastic Load Balancer Controller Modules** — docs_source_api_controllers_elb_deployfish_controllers_elb, docs_source_api_controllers_elb_deployfish_controllers_elbv2 [EXTRACTED 1.00]
- **Deployfish Controllers API Documentation** — docs_source_api_controllers_index_controllers [EXTRACTED 1.00]
- **Core Models API Documentation** — docs_source_api_models_abstract_abstract, docs_source_api_models_appscaling_application_scaling, docs_source_api_models_abstract_deployfish_core_models_abstract, docs_source_api_models_appscaling_deployfish_core_models_appscaling [EXTRACTED 1.00]
- **AWS service model API documentation pages** — docs_source_api_models_cloudwatch_cloudwatch, docs_source_api_models_cloudwatchlogs_cloudwatch_logs, docs_source_api_models_ec2_elastic_compute_cloud, docs_source_api_models_ecs_elastic_container_service, docs_source_api_models_efs_elastic_file_system, docs_source_api_models_elb_classic_load_balancing, docs_source_api_models_events_events, docs_source_api_models_rds_relational_database_service, docs_source_api_models_secrets_manager_secrets_manager, docs_source_api_models_service_discovery_service_discovery, docs_source_api_models_ssh_ssh [INFERRED 0.85]
- **deployfish renderer modules** — docs_source_api_renderers_deployfish_renderers_abstract, docs_source_api_renderers_deployfish_renderers_table, docs_source_api_renderers_deployfish_renderers_misc [EXTRACTED 1.00]
- **deploy mysql CLI commands** — docs_source_plugins_mysql_deploy_mysql_create, docs_source_plugins_mysql_deploy_mysql_update, docs_source_plugins_mysql_deploy_mysql_validate, docs_source_plugins_mysql_deploy_mysql_dump, docs_source_plugins_mysql_deploy_mysql_load, docs_source_plugins_mysql_deploy_mysql_show_grants [EXTRACTED 1.00]
- **Deployfish MVC-like Architecture Layers** — docs_source_runbook_architecture_deployfishapp, docs_source_runbook_architecture_controllers_layer, docs_source_runbook_architecture_loaders_layer, docs_source_runbook_architecture_models_layer, docs_source_runbook_architecture_adapters_layer, docs_source_runbook_architecture_renderers_layer [EXTRACTED 1.00]
- **Plugin Extension Component Stack** — docs_source_runbook_extending_plugin_adapter, docs_source_runbook_extending_plugin_model_manager, docs_source_runbook_extending_plugin_controller, docs_source_runbook_extending_plugin_hooks, docs_source_runbook_extending_deployfish_cement_plugin_handler [EXTRACTED 1.00]
- **Quality Gate Recovery Phases 1-6** — docs_superpowers_plans_2026_06_01_quality_gate_recovery_master_plan_phase_1_shared_infra, docs_superpowers_plans_2026_06_01_quality_gate_recovery_master_plan_phase_2_test_cleanup, docs_superpowers_plans_2026_06_01_quality_gate_recovery_master_plan_phase_3_ssh_secrets_sd, docs_superpowers_plans_2026_06_01_quality_gate_recovery_master_plan_phase_4_ecs_hotspots, docs_superpowers_plans_2026_06_01_quality_gate_recovery_master_plan_phase_5_napoleon_completion, docs_superpowers_plans_2026_06_01_quality_gate_recovery_master_plan_phase_6_final_verification [EXTRACTED 1.00]
- **ECS Service Configuration Examples** — examples_basic, examples_fargate, examples_no_elb, examples_tutorial_1, examples_tutorial_2 [INFERRED 0.85]
- **Fargate Launch Type Pattern** — examples_fargate_launch_type_fargate, examples_run_task_launch_type_fargate, examples_fargate_vpc_configuration, examples_run_task_vpc_configuration [INFERRED 0.95]
- **Terraform State Integration Pattern** — examples_terraform_basic_terraform, tests_interpolate_terraform, tests_terraform_interpolate_terraform [INFERRED 0.95]
- **Pydantic Adapter Migration** — docs_adr_0001_pydantic_adapters_containerdefinitioninput, docs_adr_0002_pydantic_task_definition_adapter_taskdefinitioninput, docs_adr_0001_pydantic_adapters_adapter_convert_contract, docs_adr_0001_pydantic_adapters_config_schema_module, docs_superpowers_plans_2026_08_04_pydantic_container_adapter_partial_model [INFERRED 0.85]
- **Deployment Rollout Participants** — docs_source_architecture_context_service, docs_source_architecture_context_workload_definition, docs_source_architecture_context_companion_task, docs_source_architecture_context_discovery_registration, docs_source_architecture_context_scaling_policy [EXTRACTED 1.00]
- **Rebuild Domain Glossary Core** — docs_source_architecture_context_manifest, docs_source_architecture_context_cluster, docs_source_architecture_context_service, docs_source_architecture_context_workload_definition, docs_source_architecture_context_container_spec [EXTRACTED 1.00]

## Communities (255 total, 65 thin omitted)

### Community 0 - "Core Model Managers"
Cohesion: 0.02
Nodes (160): BaseMultipleObjectsReturned, BaseOperationFailed, DoesNotExist, ImproperlyConfigured, LazyAttributeMixin, Manager, Model, MultipleObjectsReturned (+152 more)

### Community 1 - "ECS Tasks And Secrets"
Cohesion: 0.02
Nodes (63): Scale the number of instances in an ECS Cluster to match ``count``. ..…, Cluster, InvokedTask, DockerMixin, SecretsMixin, :param pk str: cluster name Args: pk: pk. Keyword Args: _: . Returns: Operation…, :param pk list[str]: list of cluster names Args: pks: pks. Keyword Args: _: .…, StandaloneTasks are TaskDefinitions with their own configuration, apart from… (+55 more)

### Community 2 - "EC2 Resource Managers"
Cohesion: 0.02
Nodes (55): Instance, Tags. Returns: Operation result., Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., List. Args: vpc_id: vpc id. Returns: Operation result., Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., Get. Args: pk: pk. vpc_id: vpc id. Keyword Args: _: . Returns: Operation result., Get many. Args: pks: pks. vpc_id: vpc id. Keyword Args: _: . Returns: Operation…, List. Args: vpc_ids: vpc ids. image_ids: image ids. instance_types: instance… (+47 more)

### Community 3 - "ECS Service Lifecycle"
Cohesion: 0.02
Nodes (57): Any, List. Args: cluster: cluster. service: service. family: family.…, :param pk str: a string like "{cluster}:{container_instance_id}" Args: pk: pk.…, :param cluster str: the name of an ECS cluster Args: cluster: cluster. Returns:…, :param pk str: cluster name Args: pk: pk. Returns: Operation result., :param pk str: a string like "{cluster_name}:{service_name}" Args: pk: pk.…, Scale. Args: obj: obj. count: count., Initialize TaskDefinition. Args: data: data. containers: containers. (+49 more)

### Community 4 - "CRUD Controllers"
Cohesion: 0.03
Nodes (55): Parse a date string in the form YYYY-MM-DD and return a datetime. Args: s: s.…, valid_date(), Controller, ex, Helper method that renders output from self.list() so that we can override…, Create waiter. Args: obj: obj. Keyword Args: _: ., Model read only crud base behavior., Create an object in AWS from configuration in deployfish.yml. (+47 more)

### Community 5 - "SSH And Exec Types"
Cohesion: 0.03
Nodes (63): Meta, Return an (instance, container_name) tuple suitable for using to exec into a…, Return an (task_arn, container_name) tuple suitable for using to exec into a…, AbstractSSHProvider, NoSSHTargetAvailable, Abstract class that provides the methods that ``SSHMixin`` will use to stablish…, Return a shell command suitable for establish an interactive ssh session. Args:…, Return a shell command suitable for establishing a "docker exec" session into a… (+55 more)

### Community 6 - "Service CLI Controllers"
Cohesion: 0.06
Nodes (70): ArgparseController, Base, BaseService, BaseServiceDockerExec, BaseServiceSecrets, BaseServiceSSH, filename_envvar(), maybe_rename_existing_file() (+62 more)

### Community 7 - "ECS Command Controllers"
Cohesion: 0.05
Nodes (47): ECSServiceCommandLogs, ECSServiceCommands, get_task(), Meta, Controller, ex, Build a ``deployfish.core.waiters.HookedWaiter`` for the operation named…, Show info about a ServiceHelperTask object associated with a Service that… (+39 more)

### Community 8 - "ECS Service Tests"
Cohesion: 0.04
Nodes (42): If this is a FARGATE task definition, return ``True``. Otherwise return…, Model service helper task behavior., Command. Returns: Operation result., Ssh command all instances. Args: cmd: cmd. Returns: Operation result., Model service behavior. Args: data: data., Name. Returns: Operation result., Return the version tag on the container image for the first container in the…, Launch type. Returns: Operation result. (+34 more)

### Community 9 - "Subnets And Tags"
Cohesion: 0.05
Nodes (35): Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., List. Args: vpc_id: vpc id. Returns: Operation result., Model subnet behavior., Pk. Returns: Operation result., Name. Returns: Operation result., Cidr block. Returns: Operation result., Available ips. Returns: Operation result., Subnet (+27 more)

### Community 10 - "Config Initialization"
Cohesion: 0.05
Nodes (38): Stable identity key used by baseline filtering., Config, NoSuchSectionError, NoSuchSectionItemError, Any, Session, setter, Initialize config state from a file path or provided payload. Args: filename:… (+30 more)

### Community 11 - "Container Definition Adapter"
Cohesion: 0.05
Nodes (21): ContainerDefinitionAdapter, Any, Return ``True`` if this container is part of a FARGATE task Returns: Operation…, Add parameter store values to the container's 'secrets' list. The task will…, In ``deployfish.yml``, volumes take one of these two forms:: volumes: -…, Convert our deployfish YAML definition of our containers to the same format…, ``deployfish.yml`` port mappings look like this:: ports: - "80" - "8443:443" -…, ``deployfish.yml`` environment variables are defined in one of the two… (+13 more)

### Community 12 - "Service New Lifecycle Tests"
Cohesion: 0.05
Nodes (10): New. Args: obj: obj. source: source. Keyword Args: kwargs: kwargs. Returns:…, TestServiceManagerCreate, TestServiceProperties, TestServiceRenderForDiff, TestServiceUpdateAppscaling, TestServiceDeployfishEnvironment, TestServiceRestart, TestServiceSave (+2 more)

### Community 13 - "Napoleon Doc Gate"
Cohesion: 0.07
Nodes (63): AST, _check_file(), _check_function_doc(), _constructor_has_args(), _first_doc_line(), _function_has_args(), _function_has_keyword_args(), _function_uses_return_or_yield() (+55 more)

### Community 14 - "Task Definition Model"
Cohesion: 0.04
Nodes (29): ContainerDefinition, An ECS Task Definition. Args: data: data. containers: containers., If this task definition exists in AWS, return our ``<family>:<revision>``…, Name. Returns: Operation result., Launch type. Returns: Operation result., Family. Returns: Operation result., Return the version for the task definition. We're cheating here by just…, Deployfish environment. Returns: Operation result. (+21 more)

### Community 15 - "Controller Test Harness"
Cohesion: 0.08
Nodes (23): ECSService, Valid date. Args: s: s. Returns: Operation result., Model ecsservice behavior., valid_date(), bind_controller(), bind_service_loader(), cement_app(), fixture (+15 more)

### Community 16 - "Object Loaders"
Cohesion: 0.06
Nodes (37): DeployfishObjectDoesNotExist, DeployfishSectionDoesNotExist, ObjectLoader, ObjectNotManaged, Any, Exception, Get an object from AWS directly, and don't look at our config in…, A mixin for Service objects to support dereferencing of identifiers in the form… (+29 more)

### Community 17 - "CloudWatch Log Tailers"
Cohesion: 0.08
Nodes (30): CloudWatchLogGroup, CloudWatchLogGroupTailer, CloudWatchLogStream, CloudWatchLogStreamIterator, CloudWatchLogStreamTailer, An iterator class that allows you to tail live logs from a CloudWatchLogStream.…, An iterator class that allows you to tail live logs from a CloudWatchLogStream.…, Handle iter. Returns: Operation result. (+22 more)

### Community 18 - "Fargate Task Mixins"
Cohesion: 0.06
Nodes (28): Any, Model task definition fargatemixin behavior., If this is a FARGATE task definition, return ``True``. Otherwise return…, Return the minimum necessary cpu for our task by summing up 'cpu' from each of…, For FARGATE tasks, task cpu is required and must be one of the values listed in…, For EC2 tasks, set task cpu if 'cpu' is provided, don't set otherwise. If 'cpu'…, Set task cpu requirement, based on whether this is a FARGATE task or an EC2…, Find the minimum necessary memory and maximum necessary memory for our task by… (+20 more)

### Community 19 - "Service Adapter"
Cohesion: 0.06
Nodes (18): Any, SecretsMixin, Update ``data`` with the configuration for the Service itself. This will look…, * Service itself [x] Args: data: data., Build a list of Secret and ExternalSecret objects from our Service's config:…, Handle build task definition. Args: kwargs: kwargs., Handle build application scaling objects. Args: kwargs: kwargs., Handle build service discovery service. Args: kwargs: kwargs. (+10 more)

### Community 20 - "Service Manager CRUD"
Cohesion: 0.05
Nodes (24): datetime, List. Args: cluster_name: cluster name. Returns: Operation result., Handle get service and cluster from pk. Args: pk: pk. Returns: Operation result., Get many. Args: pks: pks. Keyword Args: _: . Returns: Operation result., Exists. Args: pk: pk. Returns: Operation result., List. Args: cluster_name: cluster name. service_name: service name.…, Save. Args: obj: obj. Keyword Args: _: ., Create. Args: obj: obj. (+16 more)

### Community 21 - "Helper Task Adapter Tests"
Cohesion: 0.06
Nodes (9): The problem here is that, unlike all our other adapters, we need to create…, ServiceHelperTaskAdapter, TestServiceHelperTaskAdapterComprehensive, BaseTestServiceHelperTaskAdapter_basic, If we have no vpc_configuration, our network mode should be forced to 'bridge'., Ensure old style command definitions still work: tasks: - family: foobar-test-…, If we have vpc_configuration, our network mode should be forced to 'awsvpc'., TestServiceHelperTaskAdapter_EC2 (+1 more)

### Community 22 - "Plugin Docs Index"
Cohesion: 0.05
Nodes (46): CloudWatch, deployfish.core.models.cloudwatch, CloudWatch Logs, deployfish.core.models.cloudwatchlogs, deployfish.core.models.ec2, Elastic Compute Cloud, deployfish.core.models.ecs, Elastic Container Service (+38 more)

### Community 23 - "Terraform S3 State"
Cohesion: 0.07
Nodes (21): Any, Model terraform s3 state behavior. Args: terraform_config: terraform config.…, Initialize TerraformS3State. Args: terraform_config: terraform config. context:…, Retrive our statefile from S3 Args: state_file_url: state file url. profile:…, Handle load pre version 12. Args: tfstate: tfstate., Handle load post version 12. Args: tfstate: tfstate., Load. Args: replacements: replacements., Initialize TerraformEnterpriseState. Args: terraform_config: terraform config.… (+13 more)

### Community 24 - "Config Processors"
Cohesion: 0.11
Nodes (27): BaseSkipConfigProcessing, AbstractConfigProcessor, ProcessingFailed, A base class for processors for our our ``deployfish.yml`` file. These…, Return all known replacements for ``deployfish.yml`` section name…, SkipConfigProcessing, EnvironmentConfigProcessor, # TODO: need to deal with multiple matches in the same line (+19 more)

### Community 25 - "RDS Instance Model"
Cohesion: 0.05
Nodes (22): Status. Returns: Operation result., Returns: The engine for this RDS instance (e.g. "mysql"), Returns: The version of the engine for this RDS instance., Returns: The hostname of the db endpoint, Returns: The port for this RDS instance (e.g. "mysql"), Returns: The username of the root user for this instance., Secret enabled. Returns: Operation result., Returns: The ARN of the Secrets Manager Secret used to store the password for… (+14 more)

### Community 26 - "Jinja2 Template Filters"
Cohesion: 0.10
Nodes (20): color(), fromtimestamp(), lb_listener_table(), load(), Any, Render table for target groups. Args: data: Target-group-like row objects.…, Render table for ELBv2 listeners. Args: data: Listener-like row objects.…, Bind custom template handler. Args: app: Cement application instance. Side… (+12 more)

### Community 27 - "SQS Plugin Hooks"
Cohesion: 0.08
Nodes (20): Annotator, process_service_update(), Get the authors for the most recent commits. Returns: Operation result., Get the committer for the most recent commits. Returns: Operation result., Get the deployer for the most recent commits. Returns: Operation result., Get the version for the most recent commits. Returns: Operation result., Get the name of the service. Returns: Operation result., Get the name of the service. Returns: Operation result. (+12 more)

### Community 28 - "Container Instance Model"
Cohesion: 0.07
Nodes (18): ContainerInstance, :param pk str: a string like "{cluster}:{container_instance_id}" Args: pk: pk.…, :param pk str: a string like "{cluster}:{container_instance_id}" Args: pk: pk.…, Model container instance behavior. Args: data: data. cluster: cluster., Pk. Returns: Operation result., Name. Returns: Operation result., Arn. Returns: Operation result., Free cpu. Returns: Operation result. (+10 more)

### Community 29 - "Container Schema Models"
Cohesion: 0.14
Nodes (23): ContainerDefinitionInput, ExtraHost, LoggingConfig, _parse_extra_hosts(), PortMapping, BaseModel, Pydantic models describing the shape of a ``deployfish.yml`` container…, A single ``/etc/hosts`` entry to add to the container. Args: hostname: the… (+15 more)

### Community 30 - "AWS Session Builder"
Cohesion: 0.12
Nodes (20): AWSSessionBuilder, build_boto3_session(), ForbiddenAWSAccountId, get_boto3_session(), NoSuchAWSProfile, Any, Exception, Session (+12 more)

### Community 31 - "Cement App Entry"
Cohesion: 0.10
Nodes (20): App, Store active Cement app for config helpers. Args: app: Cement app whose config…, set_app(), DeployfishAppError, Model deployfish app error behavior., DeployfishApp, main(), maybe_do_cli_debugging() (+12 more)

### Community 32 - "ALB Listener Model"
Cohesion: 0.08
Nodes (17): LoadBalancerListener, Listeners. Returns: Operation result., Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., Model load balancer listener behavior., Pk. Returns: Operation result., Name. Returns: Operation result., Arn. Returns: Operation result., Port. Returns: Operation result. (+9 more)

### Community 33 - "Standalone Task CLI"
Cohesion: 0.11
Nodes (12): ECSStandaloneTask, ex, Delete an object from AWS by primary key., Model ecsstandalone task behavior., If a command for a Service has a schedule rule and that rule is currently…, If a StandaloneTask has a schedule rule and that rule is currently enabled in…, Run a StandaloneTask., Show what we would do if we were to update an ECS StandaloneTask in AWS. (+4 more)

### Community 34 - "App Scaling Adapter"
Cohesion: 0.11
Nodes (16): ECSServiceScalableTargetAdapter, ECSServiceScalingPolicyAdapter, Any, .. code-block:: python Args: data: data., Initialize ECSServiceScalableTargetAdapter. Args: data: data. Keyword Args:…, .. code-block:: python Args: data: data., Get resource id. Returns: Operation result., Convert. Returns: Operation result. (+8 more)

### Community 35 - "Service Secret Properties"
Cohesion: 0.07
Nodes (20): setter, Return a dictionary of the secrets (AWS SSM Parameter Store parameters) for…, Secrets. Args: value: value., Secrets. Returns: Operation result., Secrets. Args: value: value., Secrets. Returns: Operation result., Secrets. Args: value: value., Service names are only unique within a cluster, so to fully identify a service… (+12 more)

### Community 36 - "Cement Plugin Handler"
Cohesion: 0.09
Nodes (18): DeployfishCementPluginHandler, get_deployfish_plugins(), load(), Meta, App, Cement plugin extension module., Load plugin. Args: plugin_name: plugin name., Load a list of plugins. Args: plugins: A list of plugin names to load. (+10 more)

### Community 37 - "Target Group Renderer"
Cohesion: 0.09
Nodes (10): Specialized renderer for ECS target groups., Render attached load balancer names. Args: obj: Target group being rendered.…, Render target names. Args: obj: Target group being rendered. _key: Unused…, Render listener protocol/port pairs. Args: obj: Target group being rendered.…, Render backing container protocol/port pair. Args: obj: Target group being…, TargetGroupTableRenderer, TestTargetGroupTableRendererGaps, TestLBListenerTableRenderer (+2 more)

### Community 38 - "Adapter Base Classes"
Cohesion: 0.13
Nodes (18): Adapter, Return whether exactly one value in ``data`` is truthy. Args: data: Boolean…, Given a dict of data from a data source, convert it appropriate data Args:…, ECSServiceCPUAlarmAdapter, .. code-block:: python Args: data: data., EventScheduleRuleAdapter, EventTargetAdapter, # TODO: use VpcConfigurationMixin for this (+10 more)

### Community 39 - "Task Definition Adapter Tests"
Cohesion: 0.12
Nodes (7): Convert our deployfish YAML definition of our task definition to the same…, TaskDefinitionAdapter, TestTaskDefinitionAdapterComprehensive, Golden-master characterization tests for TaskDefinitionAdapter.convert(). These…, # NOTE: message text updated for the Pydantic rewrite (Task 6). Task 4, TestTaskDefinitionAdapterGoldenMaster, TestTaskDefinitionAdapter

### Community 40 - "Autoscaling Group Model"
Cohesion: 0.08
Nodes (14): AutoscalingGroup, Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., List. Returns: Operation result., Model autoscaling group behavior., Pk. Returns: Operation result., Name. Returns: Operation result., Autoscaling group. Returns: Operation result., Instances. Returns: Operation result. (+6 more)

### Community 41 - "Controller API Docs"
Cohesion: 0.09
Nodes (29): Base, deployfish.controllers.base, Cluster, deployfish.controllers.cluster, Commands, deployfish.controllers.commands, Crud, deployfish.controllers.crud (+21 more)

### Community 42 - "Load Balancer Model"
Cohesion: 0.08
Nodes (14): LoadBalancer, Get many. Args: pks: pks. Keyword Args: kwargs: kwargs. Returns: Operation…, Model load balancer behavior., Pk. Returns: Operation result., Name. Returns: Operation result., Arn. Returns: Operation result., Lb type. Returns: Operation result., Scheme. Returns: Operation result. (+6 more)

### Community 43 - "Task Volume Schema Tests"
Cohesion: 0.09
Nodes (7): A single task-definition-level volume declaration. ``path``, ``config``, and…, Volume, Tests for the TaskDefinitionInput sub-models., TestTaskDefinitionInputContainers, TestTaskDefinitionInputVolumes, TestTaskDefinitionOverlayInput, TestVolume

### Community 44 - "SSM Secrets Model"
Cohesion: 0.11
Nodes (15): # TODO: if the host_path doesn't start with a /, ensure that, DecryptionFailed, ExternalSecret, Exception, An SSM Parameter Store Parameter. Args: data: data. name: name., Pk. Returns: Operation result., Name. Returns: Operation result., Is secure. Returns: Operation result. (+7 more)

### Community 45 - "Classic ELB Targets"
Cohesion: 0.08
Nodes (14): ClassicLoadBalancerTarget, Any, Model classic load balancer target behavior. Args: data: data. instance:…, Initialize ClassicLoadBalancerTarget. Args: data: data. instance: instance., Pk. Returns: Operation result., Name. Returns: Operation result., Hostname. Returns: Operation result., Private hostname. Returns: Operation result. (+6 more)

### Community 46 - "SSM SSH Providers"
Cohesion: 0.11
Nodes (14): BastionSSHProvider, Initialize AbstractSSHProvider. Args: instance: instance. Keyword Args:…, r""" Implement our SSH commands via AWS Systems Manager SSH connections…, Return a shell command suitable for establishing an interactive ssh session. If…, Build a command that will tunnel through an SSM connection to an instance to…, Return a shell command suitable for uploading a file through an ssh tunnel to…, Find the public-facing bastion host in the VPC in which :py:attr:`instance`…, Tunnel. Args: local_port: local port. target_host: target host. host_port: host… (+6 more)

### Community 47 - "Render Exceptions"
Cohesion: 0.11
Nodes (14): is used for click commands, and gets re-raised when we get other exceptions so…, Initialize RenderException. Args: msg: msg. exit_code: exit code., Initialize NoSuchConfigSection. Args: section: section., Initialize NoSuchConfigSectionItem. Args: section: section. name: name., RenderException, AbstractRenderer, Any, Initialize renderer base class. Args: *args: Positional renderer configuration.… (+6 more)

### Community 48 - "README Project Overview"
Cohesion: 0.10
Nodes (26): sphinx-click, VPC Bastion Host Assumption, deploy cluster command, deploy service exec, deploy service ssh, deployfish.core.adapters.abstract, deployfish.core.adapters.deployfish.appscaling, deployfish.core.adapters.deployfish.cloudwatch (+18 more)

### Community 49 - "YAML Tutorial Docs"
Cohesion: 0.08
Nodes (26): ECS Lifecycle Management, Terraform State Integration, Basic ECS Service Tutorial, hello-world-test Service Example, Required Service Parameters, Ports Environment and Command Tutorial, ALB/NLB Target Group Configuration, Classic ELB Configuration (+18 more)

### Community 50 - "Secret Manager SSM"
Cohesion: 0.11
Nodes (13): Manage our SSM Parameter Store parameters. This differs from Args: model: model., Handle describe parameters. Args: key: key. option: option. Returns: Operation…, Handle get parameter values. Args: names: names. Keyword Args: decrypt:…, Convert. Args: parameter_data: parameter data. Returns: Operation result., Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., .. note:: We need both encryption metadata from ``describe_parameters`` and…, List names. Args: prefix: prefix. Returns: Operation result., List. Args: prefix: prefix. Keyword Args: decrypt: decrypt. Returns: Operation… (+5 more)

### Community 51 - "Config Interpolation Tests"
Cohesion: 0.09
Nodes (6): Any, statefile_loader(), TestContainerDefinition_load_yaml, TestContainerDefinition_load_yaml_no_interpolate, TestContainerDefinition_terraform_statefile_interpolation, TestTunnelDefinition_terraform_interpolation

### Community 52 - "Partial Pydantic Models"
Cohesion: 0.13
Nodes (12): partial_model(), BaseModel, Helper for deriving "partial update" Pydantic models, used for the ``partial``…, Build a subclass of ``model`` where every field is optional and defaults to…, field_validator, _Gadget, BaseModel, Tests for deployfish.config.schema._partial.partial_model. (+4 more)

### Community 53 - "ECS Service Waiters"
Cohesion: 0.11
Nodes (10): Service waiter. Args: obj: obj. Keyword Args: kwargs: kwargs., Delete waiter. Args: obj: obj. Keyword Args: kwargs: kwargs., Show periodic updates while we change desired count for a service. Args: obj:…, ECSDeploymentStatusWaiterHook, Success. Args: status: status. response: response. num_attempts: num attempts.…, Failure. Args: status: status. response: response. num_attempts: num attempts.…, for both the 'services_stable' and 'services_inactive' waiters on ECS. Args:…, Timeout. Args: status: status. response: response. num_attempts: num attempts.… (+2 more)

### Community 54 - "VPC Task Adapter Mixins"
Cohesion: 0.13
Nodes (13): AbstractTaskAdapter, Any, When creating :py:class:`deployfish.core.models.ecs.ServiceHelperTask` objects,…, Model vpc configuration mixin behavior., Get vpc configuration. Args: source: source. Returns: Operation result., Model abstract task adapter behavior., Return ``True ``if this task definition is for FARGATE, ``False`` otherwise.…, Construct the dict that will be given as input for configuring an… (+5 more)

### Community 55 - "Docker Host Mixin Tests"
Cohesion: 0.10
Nodes (5): _DockerHost, Any, DockerMixin, setter, TestDockerMixinPush

### Community 56 - "Secrets Manager SMSecret"
Cohesion: 0.10
Nodes (13): Name. Returns: Operation result., Arn. Returns: Operation result., Manage our Secrets Manager secrets. This differs from…, Kms key id. Returns: Operation result., Description. Returns: Operation result., Rotation enabled. Returns: Operation result., Last rotated. Returns: Operation result., Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result. (+5 more)

### Community 57 - "MySQL Database Model"
Cohesion: 0.09
Nodes (12): MySQLDatabase, self.data here has the following structure: { 'name': 'string', 'service':…, Pk. Returns: Operation result., Name. Returns: Operation result., Ssh target. Returns: Operation result., Ssh targets. Returns: Operation result., Cluster. Returns: Operation result., Update. Args: root_user: root user. root_password: root password. ssh_target:… (+4 more)

### Community 58 - "Service Render Push Tests"
Cohesion: 0.13
Nodes (8): Coverage for Service render/save paths and related model branches., _service_from_aws(), _service_from_yml(), TestServiceProperties, TestServiceRenderForDiff, TestServiceRenderForDisplay, TestServiceRenderForUpdate, TestServiceSaveFlow

### Community 59 - "Pytest Boto Fixtures"
Cohesion: 0.19
Nodes (19): Client. Returns: Operation result., application_scaling_yml(), config_secrets_yml(), fargate_service_yml(), helper_tasks_yml(), minimal_deployfish_yml(), mock_boto3_client(), _mock_boto3_session() (+11 more)

### Community 60 - "Service Discovery Model"
Cohesion: 0.12
Nodes (11): NamespaceNotFound, Exception, self.data has this structure:: Args: data: data., The namespace that this service is configured with does not exist in AWS., Name. Returns: Operation result., Arn. Returns: Operation result., Save. Returns: Operation result., ServiceDiscoveryService (+3 more)

### Community 61 - "Core Utility Mixins"
Cohesion: 0.13
Nodes (15): AnnotationMixin, CodebuildMixin, DeployfishDeployMixin, DockerImageNameMixin, DockerMixin, Model annotation mixin behavior., Annotate. Args: context: context., Model codebuild mixin behavior. Args: *args: args. (+7 more)

### Community 62 - "Waiter Hook Base"
Cohesion: 0.11
Nodes (11): AbstractWaiterHook, Do something when our waiter status is 'timeout'. Args: status: status.…, Initialize AbstractWaiterHook. Args: obj: obj., Mark. Args: status: status. response: response. num_attempts: num attempts.…, Model abstract waiter hook behavior. Args: obj: obj., Do something when our waiter status is 'error'. Args: status: status. response:…, ECSTaskLogsHook, for the 'tasks_stopped'' waiters on ECS. Args: obj: obj. (+3 more)

### Community 63 - "Model Render Diff"
Cohesion: 0.14
Nodes (10): Any, Diff. Args: obj: obj. Returns: Operation result., Render for display. Returns: Operation result., Render for diff. Returns: Operation result., Render for create. Returns: Operation result., Render for update. Returns: Operation result., Render. Returns: Operation result., Handle eq. Args: other: other. Returns: Operation result. (+2 more)

### Community 64 - "Git Annotation Mixin"
Cohesion: 0.15
Nodes (9): GitMixin, Model git mixin behavior. Args: *args: args., Initialize GitMixin. Args: *args: args. Keyword Args: url_type: url type.…, Handle format url. Args: url: url. label: label. Returns: Operation result., Handle build url patterns., Update the `values` dict with: * `previous_version`: the version number for the…, Handle get concise info. Returns: Operation result., Extract info about the git repo. Assume we're in the checked out clone. Args:… (+1 more)

### Community 65 - "Slack Plugin Hooks"
Cohesion: 0.15
Nodes (12): DeployfishMessage, process_service_update(), Initialize ServiceUpdateMessage. Args: app: app. obj: obj. repo_folder: repo…, Add service update. Args: obj: obj., Process service update. Args: app: app. obj: obj. success: success. reason:…, A message from deployfish. Args: app: app. *args: args., Initialize DeployfishMessage. Args: app: app. *args: args. Keyword Args:…, A message indicating that a service has been updated. Args: app: app. obj: obj.… (+4 more)

### Community 66 - "Secret Adapter"
Cohesion: 0.16
Nodes (10): ExternalParameterException, Any, Exception, Model secret adapter behavior. Args: data: data., Initialize SecretAdapter. Args: data: data. Keyword Args: kwargs: kwargs., Is external. Returns: Operation result., Parse an identifier from a deployfish.yml parameter definition that looks like…, Convert. Returns: Operation result. (+2 more)

### Community 67 - "CloudWatch Alarm Model"
Cohesion: 0.12
Nodes (10): CloudwatchAlarm, Any, Pk. Returns: Operation result., Name. Returns: Operation result., Arn. Returns: Operation result., Set policy arn. Args: arn: arn., Render for diff. Returns: Operation result., Get. Args: pk: pk. Keyword Args: kwargs: kwargs. Returns: Operation result. (+2 more)

### Community 68 - "Listener Rule Model"
Cohesion: 0.11
Nodes (10): LoadBalancerListenerRule, Any, Initialize LoadBalancerListenerRuleManager., Get many. Args: pks: pks. Keyword Args: _: . Returns: Operation result., Model load balancer listener rule behavior. Args: data: data. listener_arn:…, Initialize LoadBalancerListenerRule. Args: data: data. listener_arn: listener…, Pk. Returns: Operation result., Name. Returns: Operation result. (+2 more)

### Community 69 - "Event Target Model"
Cohesion: 0.12
Nodes (8): EventTarget, :py:attr:`data` here has the same structure as what is returned by Args: data:…, Pk. Returns: Operation result., Name. Returns: Operation result., Arn. Returns: Operation result., Set task definition arn. Args: arn: arn., List. Args: rule: rule. Returns: Operation result., TestEventTargetManager

### Community 70 - "Interactive SSH Session"
Cohesion: 0.14
Nodes (8): Push. Args: filename: filename. Keyword Args: run: run. Returns: Operation…, Do an interactive SSH session to Instance. This method will not exit until the…, Establish an SSH tunnel. Args: tunnel: the tunnel config Keyword Args: verbose:…, Run shell syntax safely via an explicit shell executable. Args: command: Shell…, Upload a file via ssh to a remote instance. If ``ssh_target`` is not provided,…, _run_shell_command(), _instance(), TestSSHMixinHelpers

### Community 71 - "Layered Architecture Plan"
Cohesion: 0.15
Nodes (18): Adapters Layer, Controllers Layer, ObjectLoader Pattern, Models Layer, Renderers Layer, Mypy Quality Gate, Napoleon Documentation Gate, Phase 1: Shared Infra and Gate Stabilization (+10 more)

### Community 72 - "Helper Task Adapter"
Cohesion: 0.16
Nodes (9): Any, Update the deployfish-specific environment variables in the container…, Build a dict that takes info from the service and overlays the generic (not…, Args: data: the ``tasks:`` section from our service definition in…, Change old style command defintions that look like this: tasks: - family:…, Build a dict that takes info from the output of :py:meth:`_get_base_task_data`…, Convert. Returns: Operation result., Set a ``data[data_key]`` on the dict ``data`` by looking at both ``task`` and… (+1 more)

### Community 73 - "Secrets Mixin Adapter"
Cohesion: 0.17
Nodes (8): parse_secret_string(), Parse an identifier from a deployfish.yml parameter definition that looks like…, Split. Returns: Operation result., Model secrets mixin behavior., Get secrets. Args: cluster: cluster. name: name. decrypt: decrypt. Returns:…, SecretsMixin, TestParseSecretString, TestSecretsMixinGetSecrets

### Community 74 - "Hooked Waiter Factory"
Cohesion: 0.15
Nodes (9): Get waiter. Args: waiter_name: waiter name. Returns: Operation result., create_hooked_waiter_with_client(), HookedWaiter, :type name: string :param name: The name of the waiter :type config:…, Wait. Keyword Args: kwargs: kwargs., :type waiter_name: str :param waiter_name: The name of the waiter. The name…, A HookedWaiter is almost exactly like a standard boto3 Waiter with one…, TestCreateHookedWaiterWithClient (+1 more)

### Community 75 - "Target Group Targets"
Cohesion: 0.12
Nodes (9): Model target group target behavior., Pk. Returns: Operation result., Name. Returns: Operation result., Port. Returns: Operation result., Health. Returns: Operation result., Target. Returns: Operation result., Target group. Returns: Operation result., List. Args: target_group_arn: target group arn. Returns: Operation result. (+1 more)

### Community 76 - "Discovery Service CRUD"
Cohesion: 0.13
Nodes (9): Any, Save. Args: obj: obj. Keyword Args: _: . Returns: Operation result., Create. Args: obj: obj. Returns: Operation result., Update. Args: obj: obj. Returns: Operation result., Render for diff. Returns: Operation result., Initialize ServiceDiscoveryService. Args: data: data. Keyword Args: kwargs:…, Render for diff. Returns: Operation result., Render for create. Returns: Operation result. (+1 more)

### Community 77 - "Discovery Namespace Model"
Cohesion: 0.12
Nodes (10): Model service discovery namespace manager behavior., Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., Model service discovery namespace behavior., Pk. Returns: Operation result., Name. Returns: Operation result., Arn. Returns: Operation result., Namespace. Returns: Operation result., List. Keyword Args: private_only: private only. Returns: Operation result. (+2 more)

### Community 79 - "Scaling Policy Model"
Cohesion: 0.15
Nodes (6): Model scaling policy behavior. Args: data: data. alarm: alarm., Pk. Returns: Operation result., Name. Returns: Operation result., ScalingPolicy, TestScalingPolicyManager, TestScalingPolicyModel

### Community 80 - "SupportsSecrets Protocol"
Cohesion: 0.12
Nodes (8): Protocol, Model supports secrets behavior., Save. Args: obj: obj. Keyword Args: _: . Returns: Operation result., Delete many by name. Args: pks: pks., Render for create. Returns: Operation result., Secrets. Returns: Operation result., Secrets. Args: value: value., SupportsSecrets

### Community 81 - "Discovery Service Manager"
Cohesion: 0.16
Nodes (9): Pk looks like '{namespace_pk}:{service_name}' Args: pk: pk. Returns: Operation…, `pk` is just a bare service name. Args: pk: pk. Returns: Operation result., `pk` is one of:: * a service id, which starts with "srv-" * a string like…, List. Args: namespace: namespace. Returns: Operation result., Delete. Args: obj: obj. Keyword Args: _: ., Pk. Returns: Operation result., Model service discovery service manager behavior., `pk` is a service['Id']: "srv-{hexstring}" Args: pk: pk. Returns: Operation… (+1 more)

### Community 82 - "Docker Exec Mixin"
Cohesion: 0.14
Nodes (10): DockerMixin, NoRunningTasks, Exception, Initialize BastionSSHProvider. Args: instance: instance. Keyword Args: verbose:…, Docker exec. Returns: Operation result., Model docker mixin behavior. Args: *args: args., Return running invoked tasks associated with this object., Initialize DockerMixin. Args: *args: args. Keyword Args: kwargs: kwargs. (+2 more)

### Community 83 - "MySQL Connection Fields"
Cohesion: 0.12
Nodes (8): Deployfish supports putting 'config.KEY' as the value for the host and port…, Host. Returns: Operation result., User. Returns: Operation result., Db. Returns: Operation result., Password. Returns: Operation result., Character set. Returns: Operation result., Collation. Returns: Operation result., Port. Returns: Operation result.

### Community 84 - "SSH Tunnel Model"
Cohesion: 0.13
Nodes (9): Any, setter, Secret. Args: name: name. Returns: Operation result., Deployfish supports putting 'config.KEY' as the value for the host and port…, Host. Returns: Operation result., Host port. Returns: Operation result., Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., Service. Returns: Operation result. (+1 more)

### Community 85 - "Git Changelog Mixin"
Cohesion: 0.14
Nodes (9): GitChangelogMixin, Any, Look through the commits between the current version and the last version…, needs to be used after GitMixin in the inheritance chain., Look through the commits between the current version and the last version…, Annotate. Args: values: values., Annotate. Args: values: values., Annotate. Args: values: values. (+1 more)

### Community 86 - "Table Renderer"
Cohesion: 0.17
Nodes (8): Any, Render byte count into human-readable units. Args: value: Byte count to format.…, Render values using builtin datatype formatting rules. Args: value: Value to…, Reformat one value into a more human-friendly form. Args: obj: Source object…, Render one column value for one row object. Args: obj: Source object for the…, Render all rows into a formatted table string. Args: data: Sequence of row-like…, Initialize table renderer. Args: columns: Column configuration keyed by output…, Dereference one column from an object or rendered mapping. Args: obj: Source…

### Community 87 - "ELBv2 Manager Tests"
Cohesion: 0.19
Nodes (5): _paginate(), TestLoadBalancerListenerManager, TestLoadBalancerListenerRuleManager, TestLoadBalancerManager, TestTargetGroupManager

### Community 88 - "Secrets Discovery Tests"
Cohesion: 0.15
Nodes (4): _paginate(), Coverage push for secrets, secrets manager, and service discovery., TestServiceDiscoveryExtended, TestSMSecretManager

### Community 90 - "Abstract Config Processor"
Cohesion: 0.16
Nodes (8): Any, Perform string replacements on ``value``, a string value in our…, Process ``obj``, a value from a key of an item from ``deployfish.yml``, looking…, Process ``obj``, a list value of an item from ``deployfish.yml``, looking for…, Recurse through each key in our dict ``obj`` and process it appropriately. We…, Is the method that :py:class:`ConfigProcessor` will execute as it loops through…, Initialize AbstractConfigProcessor. Args: config: config. context: context., Populate :py:attr:`deployfish_lookups`.

### Community 91 - "Container Schema Validators"
Cohesion: 0.15
Nodes (12): _normalize_environment(), _normalize_labels(), _parse_ports(), Any, model_validator, Raise a clear, specific error when ``driver`` is missing, instead of Pydantic's…, Split a shell command string into argv, if given as a string. Args: value: the…, Parse each raw ports entry into a PortMapping-constructible dict. Args: value:… (+4 more)

### Community 92 - "Task Definition Validators"
Cohesion: 0.18
Nodes (9): Any, model_validator, Validates and reshapes a ``deployfish.yml`` task-definition stanza, including…, Raise a clear, specific error when ``containers`` is missing, instead of…, Reject duplicate volume names. Raises: ValueError: if two volumes share a name.…, Reject any container whose ``cpu``/``memory`` exceeds this task definition's…, Require ``execution_role`` when ``launch_type`` is ``"FARGATE"``. Only enforced…, Enforce that exactly one of ``path``, ``config``, and ``efs_config`` is set.… (+1 more)

### Community 93 - "ECS Task Waiter Hooks"
Cohesion: 0.15
Nodes (7): Run task waiter. Args: tasks: tasks. Keyword Args: kwargs: kwargs., ECSTaskStatusHook, for the 'tasks_stopped'' waiters on ECS, and prints the status of our tasks on…, Waiting. Args: status: status. response: response. num_attempts: num attempts.…, Success. Args: status: status. response: response. num_attempts: num attempts.…, Timeout. Args: status: status. response: response. num_attempts: num attempts.…, TestECSTaskStatusHook

### Community 94 - "SSH Tunnel Controller"
Cohesion: 0.21
Nodes (7): establish_tunnel(), get_tunnel_target(), Actually establish an SSH Tunnel. This does not return until the user manually…, Return an ``Instance`` object through which the user can make an ssh tunnel. If…, TestEstablishTunnel, TestGetTunnel, TestGetTunnelTarget

### Community 95 - "Listener Related Objects"
Cohesion: 0.14
Nodes (7): List. Args: load_balancer: load balancer. Returns: Operation result., Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., Ssl certificates. Returns: Operation result., Load balancer. Returns: Operation result., Load balancer. Returns: Operation result., Listener. Returns: Operation result., .. note:: Deployfish assumes relevant target group is attached to first…

### Community 96 - "Event Schedule Rule"
Cohesion: 0.14
Nodes (7): EventScheduleRule, AWS cron job that deployfish uses to run ECS tasks periodically. Args: data:…, Pk. Returns: Operation result., Name. Returns: Operation result., Arn. Returns: Operation result., Enabled. Returns: Operation result., Set task definition arn. Args: arn: arn.

### Community 97 - "SSH Command Spawn"
Cohesion: 0.16
Nodes (10): Any, Spawn interactive shell command for long-lived terminal sessions. Args:…, Return a shell command suitable for running a command-line command via ssh on…, Ssh. Args: command: command. Returns: Operation result., Return ``True`` if ``data`` is a file-like object, ``False`` otherwise. Args:…, Run a command on ``ssh_target`` via ssh. This method will not exit until the…, Spawn shell syntax safely via an explicit shell executable. Args: command:…, _spawn_interactive_shell_command() (+2 more)

### Community 98 - "Pydantic Adapter ADRs"
Cohesion: 0.23
Nodes (14): Adapter.convert Contract, ContainerDefinitionAdapter, ContainerDefinitionInput, Eager Validation at Construction, ContainerDefinitionOverlayInput, SchemaException Translation, Nested Partial Model Opt-In, TaskDefinitionAdapter (+6 more)

### Community 99 - "Cluster Controller"
Cohesion: 0.23
Nodes (6): ECSCluster, ex, Change desired count for a service., Model ecscluster behavior., TestECSClusterControllerExtended, TestECSClusterController

### Community 100 - "CPU Alarm Adapter"
Cohesion: 0.15
Nodes (7): Any, Initialize ECSServiceCPUAlarmAdapter. Args: data: data. Keyword Args: kwargs:…, Get alarm name. Returns: Operation result., Get alarm description. Returns: Operation result., Get comparison operator. Returns: Operation result., Get threshold. Returns: Operation result., Convert. Returns: Operation result.

### Community 101 - "Event Rule Copy New"
Cohesion: 0.18
Nodes (7): Copy. Returns: Operation result., Any, New. Args: obj: obj. source: source. Keyword Args: kwargs: kwargs. Returns:…, Initialize EventTarget. Args: data: data. rule: rule., New. Args: obj: obj. source: source. Keyword Args: _: . Returns: Operation…, Initialize EventScheduleRule. Args: data: data., .. note:: Ideally here we would compare the full task definition attached to…

### Community 102 - "SSH SIGINT Handler"
Cohesion: 0.21
Nodes (7): build_sigint_handler(), Build signal handler for catching SIGINT (Control-C) while we are exec'ed into…, _instance(), TestBastionSSHProvider, TestBuildSigintHandler, TestSSMSSHProvider, TestBuildSigintHandler

### Community 103 - "Extensibility Architecture Docs"
Cohesion: 0.17
Nodes (13): config, config_processors, Config and Config Processors, Rebuild Tool Intent, Manifest Interpolation Behavior, Extension Failure Isolation, Message Queue Extension, Notification Extension (+5 more)

### Community 104 - "Basic YAML Examples"
Cohesion: 0.17
Nodes (13): Basic ECS Services Example, load_balancer with target_group_arn, load_balancer with load_balancer_name, my-service-alb (ALB target group), my-service-elb (Classic ELB), network_mode: bridge, services section, task_role_arn IAM role (+5 more)

### Community 105 - "Python Package Dependencies"
Cohesion: 0.15
Nodes (13): Python Dependencies, boto3 dependency, cement dependency, click dependency, docker dependency, gitpython dependency, jinja2 dependency, jsondiff2 dependency (+5 more)

### Community 106 - "Secrets CLI Commands"
Cohesion: 0.17
Nodes (6): ex, Write secrets to AWS Systems Manager Parameter Store., Extract AWS SSM Parameter Store secrets for a object in AWS and print them to…, Iterate through the secrets listed in our object's ``config:`` section in…, Diff secrets against what is currently in AWS Systems Manager Parameter Store.…, Show what we would do if we were to update an ECS Service in AWS.

### Community 107 - "Standalone Task Adapter"
Cohesion: 0.21
Nodes (4): SecretsMixin, Model standalone task adapter behavior., StandaloneTaskAdapter, TestStandaloneTaskAdapterComprehensive

### Community 108 - "Model Manager Cache"
Cohesion: 0.17
Nodes (5): Get. Args: pk: pk. Keyword Args: _: ., Exists. Args: pk: pk. Returns: Operation result., Needs update. Args: obj: obj. Returns: Operation result., Given an appropriate bit of data `obj` from a data source `source`, return the…, Is a factory method. .. note:: The ``**kwargs`` here is for the Adapter to use,…

### Community 109 - "Log Stream Iterator"
Cohesion: 0.20
Nodes (8): _event_timestamp_to_utc(), Any, datetime, Convert CloudWatch millisecond timestamps to aware UTC datetimes. Args:…, Handle next. Returns: Operation result., Handle next. Returns: Operation result., :param start_time datetime: a timezone aware, UTC datetime Args: stream:…, Handle next. Returns: Operation result.

### Community 110 - "Event Rule Manager"
Cohesion: 0.18
Nodes (7): EventScheduleRuleManager, Model event schedule rule manager behavior., Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., List. Returns: Operation result., If ``obj`` is disabled, change its state of "ENABLED". Otherwise, do nothing.…, If ``obj`` is enabled, change the its state to "DISABLED". Otherwise, do…, Get. Args: pk: pk. Keyword Args: kwargs: kwargs. Returns: Operation result.

### Community 111 - "Project Metadata Mixins"
Cohesion: 0.20
Nodes (8): ImproperlyConfiguredError, Exception, Path, Process a pyproject.toml file and return the name and version. Raises:…, Extract some stuff from setup.py, if present. If setup.py is present, we'll add…, We programmers improperly configured something., Process a setup.py file and return the name and version. Raises: ValueError: if…, Process a Makefile and return the name and version. Raises: ValueError: if the…

### Community 112 - "Waiter Hook Lifecycle"
Cohesion: 0.17
Nodes (6): Do any necessary cleanup after the waiter iteration has completed and we've…, Args: * 'state': the current state of the waiter. One of 'waiting', 'success',…, Do any necessary setup on the waiter iteration before we've done our per-state…, Do something when our waiter status is 'waiting'. Args: status: status.…, Do something when our waiter status is 'success'. Args: status: status.…, Do something when our waiter status is 'failure'. Args: status: status.…

### Community 113 - "MySQL Create Update"
Cohesion: 0.17
Nodes (6): Create the database and user for ``obj``, and assign appropriate grants to the…, Update the grants and password for the database user on ``obj``. Args: obj: The…, Return the major.minor version of the MySQL server. Example: If the server…, Server version. Args: ssh_target: ssh target. verbose: verbose. user: user.…, Render for create. Args: root_user: root user. root_password: root password.…, Render for update. Args: root_user: root user. root_password: root password.…

### Community 114 - "Remote Access Architecture"
Cohesion: 0.23
Nodes (12): Cluster Day-2 Operations, Bastion Host Strategy, Direct-to-Node Strategy, In-Container Exec, SSH-Based Exec, Auxiliary Datastore Extension, Bastion Tunnel, Cluster (+4 more)

### Community 115 - "Service Manager Push Tests"
Cohesion: 0.17
Nodes (3): ServiceManager update/save/scale coverage., TestServiceManagerListValidation, TestServiceManagerUpdateSave

### Community 116 - "ELBv2 Coverage Tests"
Cohesion: 0.24
Nodes (5): _paginate(), Additional ELBv2 manager coverage., TestLoadBalancerListenerModelPush, TestLoadBalancerManagerPush, TestTargetGroupManagerPush

### Community 117 - "Task Definition Adapter"
Cohesion: 0.22
Nodes (6): Any, Convert this task definition's validated volume declarations to the same…, Convert this task definition's validated data to the same structure that…, Initialize TaskDefinitionAdapter. Args: data: data. secrets: secrets.…, Validate ``data`` against the appropriate input model, translating…, Copy. Returns: Operation result.

### Community 118 - "Listener Rule Manager"
Cohesion: 0.24
Nodes (6): LoadBalancerListenerRuleManager, Model load balancer listener rule manager behavior., Handle get rules for load balancer. Args: load_balancer_pk: load balancer pk.…, Return listener rules on the target group's load balancer that forward to…, List. Args: listener_arn: listener arn. load_balancer_pk: load balancer pk.…, Get tags. Args: arn: arn. Returns: Operation result.

### Community 119 - "Code Name Version Mixin"
Cohesion: 0.40
Nodes (4): CodeNameVersionMixin, Model code name version mixin behavior., Path, TestCodeNameVersionMixin

### Community 120 - "Jinja2 Cement Handlers"
Cohesion: 0.20
Nodes (8): DeployfishJinja2OutputHandler, DeployfishJinja2TemplateHandler, Meta, We're subclassing the cement Jinja2OutputHandler here so we can use our own…, We're subclassing the cement Jinja2TemplateHandler here so we can add some…, Jinja2OutputHandler, Jinja2TemplateHandler, TestExtJinja2RemainingFilters

### Community 121 - "MySQL Plugin Loader"
Cohesion: 0.25
Nodes (8): pre_config_interpolate_add_mysql_section(), App, Add our "mysql" section to the list of sections on which keyword interpolation…, add_template_dir(), load(), App, Add template dir. Args: app: app., Load. Args: app: app.

### Community 122 - "Workload Definition Docs"
Cohesion: 0.25
Nodes (11): Workload Definition Immutability, Task Schedule, awslogs-Only Tailing, Companion Task, Companion Task Command, Container Spec, Log Source, One-Off Task (+3 more)

### Community 123 - "VPC Manager Gap Tests"
Cohesion: 0.27
Nodes (3): _paginate(), TestInstanceManagerGaps, TestVPCManagerGaps

### Community 130 - "Scaling Policy Manager"
Cohesion: 0.22
Nodes (6): Get a single ScalableTarget. Args: pk: pk. Keyword Args: _: . Returns:…, Model scaling policy manager behavior., Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., Arn. Returns: Operation result., List. Args: cluster: cluster. service: service. Returns: Operation result., ScalingPolicyManager

### Community 131 - "Secret Field Setters"
Cohesion: 0.20
Nodes (7): setter, Prefix. Returns: Operation result., Prefix. Args: value: value., Kms key id. Returns: Operation result., Kms key id. Args: value: value., Value. Returns: Operation result., Value. Args: value: value.

### Community 133 - "MySQL Database Manager"
Cohesion: 0.20
Nodes (5): MySQLDatabaseManager, Model my sqldatabase manager behavior., Use ``mysqldump`` to dump the remote database as SQL to a local file. If…, List the MySQLDatabase objects in the config file. Returns: A list of…, Render for dump. Returns: Operation result.

### Community 134 - "MySQL Validate Commands"
Cohesion: 0.20
Nodes (5): Validate that the database and user exist on the target MySQL server. Args:…, Return the MySQL version of the MySQL server. Example: If the server version is…, Render mysql command. Args: sql: sql. user: user. password: password. Returns:…, Render for validate. Returns: Operation result., Render for server version. Args: user: user. password: password. Returns:…

### Community 136 - "SecretsMixin Push Tests"
Cohesion: 0.24
Nodes (4): Any, SecretsMixin, _SecretsHost, TestSecretsMixin

### Community 137 - "SecretsMixin Write Tests"
Cohesion: 0.24
Nodes (4): Any, SecretsMixin, _SecretsHost, TestSecretsMixinWriteSecrets

### Community 138 - "Environment Config Processor"
Cohesion: 0.25
Nodes (5): Any, Replace. Args: obj: obj. key: key. value: value. section_name: section name.…, Initialize EnvironmentConfigProcessor. Args: config: config. context: context., Handle load env file. Args: filename: filename. Returns: Operation result., Load per item environment. Args: section_name: section name. item_name: item…

### Community 139 - "Task Volume Schema"
Cohesion: 0.28
Nodes (8): DockerVolumeConfig, EFSConfig, BaseModel, Pydantic models describing the shape of a ``deployfish.yml`` task-definition…, A task definition's CPU/OS platform requirements. Args: cpu_architecture: the…, A Docker-managed volume's configuration. Args: scope: ``"task"`` or…, An EFS-backed volume's configuration. Args: file_system_id: the EFS file system…, RuntimePlatform

### Community 140 - "Events Adapter Convert"
Cohesion: 0.25
Nodes (5): Any, Get cluster arn. Returns: Operation result., Get vpc configuration. Returns: Operation result., Convert. Returns: Operation result., Convert. Returns: Operation result.

### Community 141 - "Scaling Policy Render"
Cohesion: 0.28
Nodes (5): Any, Initialize ScalingPolicy. Args: data: data. alarm: alarm., Render for diff. Returns: Operation result., Initialize ScalableTarget. Args: data: data. policies: policies., Render for diff. Returns: Operation result.

### Community 142 - "Secret Diff Render"
Cohesion: 0.25
Nodes (5): Any, Diff our list of Secrets against `other`. `other` is either a list of Secrets…, Initialize SecretManager. Args: model: model. Keyword Args: readonly: readonly., Initialize Secret. Args: data: data. name: name., Render for diff. Returns: Operation result.

### Community 143 - "Plugin System Docs"
Cohesion: 0.25
Nodes (9): Deployfish Plugin System, deployfish-slack Plugin, ~/.deployfish.yml User Config, deployfish-sqs Plugin, Extensible Custom Modules, Cement Application Plugins, DeployfishCementPluginHandler, Modular Plugin Architecture (+1 more)

### Community 144 - "Interpolation YAML Fixture"
Cohesion: 0.22
Nodes (9): Interpolation Test Config, service config secrets, ${env.*} environment variable interpolation, foobar-prod production service, network_mode: host, services section, terraform section, tunnels section (+1 more)

### Community 145 - "Discovery Model Tests"
Cohesion: 0.28
Nodes (3): _paginate(), TestServiceDiscoveryNamespaceManager, TestServiceDiscoveryServiceManager

### Community 146 - "Terraform Lookup Replace"
Cohesion: 0.25
Nodes (4): Get terraform state download url. Returns: Operation result., Load. Args: _: ., Perform string replacements on ``value``, a string value in our…, Lookup. Args: attr: attr. replacements: replacements. Returns: Operation result.

### Community 148 - "Tunnel Controller Commands"
Cohesion: 0.25
Nodes (5): get_tunnel(), ex, Establish an SSH tunnel from our machine through an instance to a host:port in…, Establish an SSH tunnel from our machine through an instance to a host:port in…, If we didn't get a specific tunnel to use, present the user with a list of all…

### Community 149 - "Scalable Target Manager"
Cohesion: 0.25
Nodes (5): Delete. Args: obj: obj. Keyword Args: _: ., Model scalable target manager behavior., List. Returns: Operation result., Delete. Args: obj: obj. Keyword Args: _: ., ScalableTargetManager

### Community 150 - "Log Stream Manager"
Cohesion: 0.32
Nodes (5): CloudWatchLogStreamManager, Model cloud watch log stream manager behavior., Handle get group and stream from pk. Args: pk: pk. Returns: Operation result., Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., .. note:: ``log_group_name`` stays required because listing every stream in…

### Community 151 - "Scheduled Task Listing"
Cohesion: 0.29
Nodes (4): List all the ServiceHelperTasks. To do this accurately, we need to: * List all…, List. Args: scheduled_only: scheduled only. Returns: Operation result., List all Tasks (StandaloneTasks and ServiceHelperTasks), filtering by various…, List only the scheduled tasks, filtering by various dimensions. We do this by…

### Community 152 - "Classic ELB Manager"
Cohesion: 0.25
Nodes (4): List. Args: load_balancer_name: load balancer name. Returns: Operation result., Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., Ssl policy. Returns: Operation result., Get many. Args: pks: pks. Keyword Args: kwargs: kwargs. Returns: Operation…

### Community 153 - "ELBv2 Get Many"
Cohesion: 0.25
Nodes (4): Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., Get many. Args: pks: pks. Keyword Args: kwargs: kwargs. Returns: Operation…, Load balancers. Returns: Operation result.

### Community 154 - "Adapter Registry"
Cohesion: 0.25
Nodes (5): AdapterRegistry, Initialize AdapterRegistry., Register a new Adapter class with a model and a source. :param model_name: the…, Return the source -> model Adapter class to use for the source ``source`` and…, A registry of adapters which consume specific data sources to configure…

### Community 155 - "Tutorial YAML Examples"
Cohesion: 0.25
Nodes (8): Tutorial 1 Minimal Service, hello-world-test minimal service, services section, Tutorial 2 Extended Service, container command override, container environment variables, hello-world-test with command and env, services section

### Community 156 - "Log Group Manager Tests"
Cohesion: 0.32
Nodes (3): _paginate(), TestCloudWatchLogGroupManager, TestCloudWatchLogStreamManager

### Community 159 - "Agent Doc Contract"
Cohesion: 0.29
Nodes (7): Documentation Contract, Napoleon Gate, Container Adapter Golden Master, Pydantic Adapter Pattern, ServiceAdapter, Task Definition Adapter Golden Master, Pydantic Container Adapter Plan

### Community 160 - "Abstract Adapter Convert"
Cohesion: 0.33
Nodes (4): Any, Initialize adapter with raw source data. Args: data: Raw source data to adapt.…, Copy one source value into output payload. Args: data: Destination payload…, Convert source payload into model constructor inputs. Returns: Tuple of adapted…

### Community 161 - "EC2 Instance Render"
Cohesion: 0.33
Nodes (4): Any, Render for update. Returns: Operation result., Render for diff. Returns: Operation result., Initialize Instance. Args: data: data.

### Community 162 - "Task List Filters"
Cohesion: 0.33
Nodes (4): List all the StandaloneTasks, which means return the list of StandaloneTasks…, Filter ``tasks`` by various dimensions, returning only those tasks that match…, is_fnmatch_filter(), Use this function to determine if a string is a fnmatch filter, which is to say…

### Community 164 - "Event Rule Save Delete"
Cohesion: 0.29
Nodes (3): Save. Args: obj: obj. Keyword Args: _: . Returns: Operation result., Delete. Args: obj: obj. Keyword Args: _: ., Save ourselves as a Cloudwatch Events Rule target. :rtype: dict

### Community 165 - "Deployment Waiter Display"
Cohesion: 0.33
Nodes (4): Any, Display deployments. Args: deployments: deployments., Display events. Args: events: events., Waiting. Args: status: status. response: response. num_attempts: num attempts.…

### Community 166 - "ELBv2 Architecture Docs"
Cohesion: 0.33
Nodes (7): Volume Input Model, LoadBalancerListenerRuleManager.list, TargetGroup.rules, Weighted and Canary Target Groups, Created vs Referenced Boundary, Discovery Registration, Scaling Policy

### Community 167 - "Secrets Deployment Docs"
Cohesion: 0.43
Nodes (7): Deployment Rollout Sequence, External Secrets, Secret Binding Reconciliation, Deployment Rollout, Secret Binding, Secret Namespace, ServiceAdapter Composition

### Community 168 - "Terraform YAML Example"
Cohesion: 0.29
Nodes (7): Terraform Integration Example, {environment}/{service-name}/{cluster-name} replacements, services with terraform values, terraform section, ${terraform.*} string interpolation, terraform.lookups key mappings, terraform.statefile S3 path

### Community 170 - "Project Structure Docs"
Cohesion: 0.40
Nodes (6): Agent Instructions, Graphify Knowledge Graph, Project Structure Layers, Tooling Preflight, Claude Agent Instructions, deployfish.config.schema

### Community 171 - "Scaling Policy Save"
Cohesion: 0.40
Nodes (3): Save. Args: obj: obj. Keyword Args: _: ., Render for create. Returns: Operation result., Save. Args: obj: obj. Keyword Args: _: . Returns: Operation result.

### Community 172 - "Log Group Manager"
Cohesion: 0.33
Nodes (4): CloudWatchLogGroupManager, Model cloud watch log group manager behavior., Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., List. Args: prefix: prefix. Returns: Operation result.

### Community 173 - "Log Tailer Init"
Cohesion: 0.33
Nodes (4): _default_start_time_ms(), Initialize CloudWatchLogGroupTailer. Args: group: group. stream_prefix: stream…, :param start_time datetime: a timezone aware, UTC datetime Args: stream:…, Compute default tail start time in milliseconds. Args: sleep: Polling interval…

### Community 175 - "Waiter Hook Init"
Cohesion: 0.33
Nodes (3): Initialize ECSTaskStatusHook. Args: obj: obj., Initialize ECSDeploymentStatusWaiterHook. Args: obj: obj., Initialize ECSTaskLogsHook. Args: obj: obj.

### Community 176 - "Cement App Architecture Docs"
Cohesion: 0.33
Nodes (6): Cement CLI Framework, Click Colorful Output, deployfish.config Module, DeployfishApp (cement.App subclass), Jinja2 Templates, Architecture Doc Reference

### Community 177 - "App Scaling YAML Example"
Cohesion: 0.33
Nodes (6): Application Scaling Example, application_scaling, containers list, load_balancer configuration, my-service-scaling ECS service, services section

### Community 178 - "Multi Container YAML Example"
Cohesion: 0.33
Nodes (6): Multi-Container Task Example, container links, three-container task definition, mysql db container with alias, redis sidecar container, services section

### Community 179 - "Terraform Interpolate Fixture"
Cohesion: 0.40
Nodes (6): Terraform Interpolate Test, foobar-prod service, foobar-qa service, foobar-qa and foobar-prod services, terraform section with {environment} statefile, mysql QA and prod tunnels

### Community 181 - "Service List Tests"
Cohesion: 0.60
Nodes (3): _cluster_paginator(), _service_paginator(), TestServiceManagerList

### Community 182 - "Standalone Task Convert"
Cohesion: 0.40
Nodes (3): Any, Get task definition. Args: secrets: secrets. Returns: Operation result., Convert. Returns: Operation result.

### Community 185 - "Cached Secrets Diff Types"
Cohesion: 0.40
Nodes (3): Any, Return secret diff summary. Args: other: Secrets to compare against current…, Return cached value or populate and cache it. Args: key: Cache key. populator:…

### Community 186 - "ASG YAML Example"
Cohesion: 0.40
Nodes (5): Autoscaling Group Example, autoscalinggroup_name, load_balancer configuration, my-service ECS service, services section

### Community 187 - "Volume YAML Example"
Cohesion: 0.40
Nodes (5): Volume Mounts Example, named volume with driver config, services section, host path volume mounts, task-level volumes definition

### Community 188 - "GitHub Test Workflow"
Cohesion: 0.40
Nodes (5): make cov, make test, test CI job, Tests GitHub Actions Workflow, uv package manager

### Community 199 - "MySQL Service Binding"
Cohesion: 0.50
Nodes (3): setter, Service. Returns: Operation result., Service. Args: value: value.

### Community 200 - "Read The Docs Config"
Cohesion: 0.50
Nodes (4): Sphinx, sphinx_rtd_theme, Read the Docs Configuration, docs/source/conf.py Sphinx configuration

### Community 201 - "Models API Docs"
Cohesion: 0.50
Nodes (4): Abstract, deployfish.core.models.abstract, Application Scaling, deployfish.core.models.appscaling

### Community 202 - "Renderers API Docs"
Cohesion: 0.50
Nodes (4): deployfish.renderers.abstract, deployfish.renderers.misc, deployfish.renderers.table, Renderers

### Community 203 - "Parameter Store YAML Example"
Cohesion: 0.50
Nodes (4): Parameter Store Example, config section for Parameter Store secrets, my-service with secrets config, services section

### Community 206 - "License And Authors"
Cohesion: 0.67
Nodes (3): Chris Malek, California Institute of Technology, MIT License

### Community 207 - "Schema Exception"
Cohesion: 0.67
Nodes (3): BaseSchemaException, Raise this if data in the config source does not validate properly., SchemaException

### Community 213 - "Main App API Docs"
Cohesion: 0.67
Nodes (3): Application configuration, deployfish.main, Main

### Community 214 - "Adding Commands Guide"
Cohesion: 0.67
Nodes (3): Adding a New Command, CrudBase Controller, ReadOnlyCrudBase Controller

### Community 215 - "No ELB YAML Example"
Cohesion: 0.67
Nodes (3): No Load Balancer Example, service without load balancer, services section

## Knowledge Gaps
- **167 isolated node(s):** `deploy-complete.bash script`, `Meta`, `deployfish`, `Tests GitHub Actions Workflow`, `uv package manager` (+162 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **65 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Service` connect `ECS Service Tests` to `Core Model Managers`, `ECS Tasks And Secrets`, `EC2 Resource Managers`, `ECS Service Lifecycle`, `ECS Command Controllers`, `Model Diff Equality Tests`, `Subnets And Tags`, `Service New Lifecycle Tests`, `Task Definition Model`, `Controller Test Harness`, `Object Loaders`, `Fargate Task Mixins`, `Service Manager CRUD`, `Helper Task Adapter Tests`, `SQS Plugin Hooks`, `Container Instance Model`, `Tutorial YAML Examples`, `Cement App Entry`, `Service Secret Properties`, `Autoscaling Group Model`, `Terraform YAML Example`, `Service Save Update Tests`, `SSM Secrets Model`, `Helper Task New Tests`, `SSM SSH Providers`, `App Scaling YAML Example`, `ECS Service Waiters`, `VPC Task Adapter Mixins`, `Reload Secrets`, `Service List Tests`, `Docker Host Mixin Tests`, `ASG YAML Example`, `Service Render Push Tests`, `Service Discovery Model`, `Slack Plugin Hooks`, `Interactive SSH Session`, `MySQL Service Binding`, `Helper Task Adapter`, `No ELB YAML Example`, `Event Schedule Rule`, `SSH SIGINT Handler`, `Basic YAML Examples`, `Python Package Dependencies`, `Service Manager Push Tests`, `Service Properties Tests`?**
  _High betweenness centrality (0.158) - this node is a cross-community bridge._
- **Why does `SchemaException` connect `Subnets And Tags` to `Core Model Managers`, `ECS Tasks And Secrets`, `Standalone EC2 Schedule Tests`, `ECS Service Lifecycle`, `CRUD Controllers`, `Standalone Fargate Schedule Tests`, `ECS Service Tests`, `Container Definition Adapter`, `Task Definition Model`, `Fargate Task Mixins`, `Service Adapter`, `Helper Task Adapter Tests`, `Terraform S3 State`, `Config Processors`, `Container Instance Model`, `Standalone Launch Type Tests`, `Abstract Task Adapter Tests`, `Adapter Base Classes`, `Task Definition Adapter Tests`, `Service Discovery Model`, `Schema Exception`, `Standalone Task Adapter Tests`, `Standalone Task Adapter`, `Helper Task EC2 Schedule Tests`, `Helper Task Fargate Schedule Tests`?**
  _High betweenness centrality (0.141) - this node is a cross-community bridge._
- **Why does `Model` connect `Core Model Managers` to `ECS Tasks And Secrets`, `Scaling Policy Manager`, `EC2 Resource Managers`, `CRUD Controllers`, `SSH And Exec Types`, `Service CLI Controllers`, `ECS Service Lifecycle`, `ECS Service Tests`, `Subnets And Tags`, `Task Definition Model`, `Object Loaders`, `CloudWatch Log Tailers`, `Fargate Task Mixins`, `Service Manager CRUD`, `Scalable Target Manager`, `Log Stream Manager`, `RDS Instance Model`, `Container Instance Model`, `ALB Listener Model`, `Event Rule Save Delete`, `Autoscaling Group Model`, `Load Balancer Model`, `Scaling Policy Save`, `SSM Secrets Model`, `Log Group Manager`, `Classic ELB Targets`, `Secret Manager SSM`, `ECS Service Waiters`, `Secrets Manager SMSecret`, `MySQL Database Model`, `Service Discovery Model`, `Model Lazy Init`, `Model Render Diff`, `CloudWatch Alarm Model`, `Listener Rule Model`, `Event Target Model`, `MySQL Secret Lookup`, `Target Group Targets`, `Discovery Service CRUD`, `Discovery Namespace Model`, `Scaling Policy Model`, `SupportsSecrets Protocol`, `Discovery Service Manager`, `Event Schedule Rule`, `Event Rule Copy New`, `Model Manager Cache`, `Event Rule Manager`, `Listener Rule Manager`?**
  _High betweenness centrality (0.139) - this node is a cross-community bridge._
- **Are the 127 inferred relationships involving `Service` (e.g. with `ServiceHelperTaskAdapter` and `LazyAttributeMixin`) actually correct?**
  _`Service` has 127 INFERRED edges - model-reasoned connections that need verification._
- **Are the 92 inferred relationships involving `Model` (e.g. with `MultipleObjectsReturned` and `ObjectDoesNotExist`) actually correct?**
  _`Model` has 92 INFERRED edges - model-reasoned connections that need verification._
- **Are the 85 inferred relationships involving `Instance` (e.g. with `Manager` and `Model`) actually correct?**
  _`Instance` has 85 INFERRED edges - model-reasoned connections that need verification._
- **Are the 92 inferred relationships involving `Manager` (e.g. with `MultipleObjectsReturned` and `ObjectDoesNotExist`) actually correct?**
  _`Manager` has 92 INFERRED edges - model-reasoned connections that need verification._