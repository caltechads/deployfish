# Graph Report - .  (2026-08-04)

## Corpus Check
- 286 files · ~120,037 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4331 nodes · 8939 edges · 245 communities (165 shown, 80 thin omitted)
- Extraction: 82% EXTRACTED · 18% INFERRED · 0% AMBIGUOUS · INFERRED: 1634 edges (avg confidence: 0.53)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- AWS Resource Models
- Abstract Model Layer
- Exception Hierarchy
- Instance Properties
- Event Scheduling
- CRUD Operations
- ECS Cluster Ops
- ECS Service Layer
- CLI Controllers
- Service Commands
- Docker Exec Tunnel
- Controller Base
- Quality Gate Tools
- Task Definitions
- Terraform State
- Community 15
- Community 16
- Community 17
- Community 18
- Community 19
- Community 20
- Community 21
- Community 22
- Community 23
- Community 24
- Community 25
- Community 26
- Community 27
- Community 28
- Community 29
- Community 30
- Community 31
- Community 32
- Community 33
- Community 34
- Community 35
- Community 36
- Community 37
- Community 38
- Community 39
- Community 40
- Community 41
- Community 42
- Community 43
- Community 44
- Community 45
- Community 46
- Community 47
- Community 48
- Community 49
- Community 50
- Community 51
- Community 52
- Community 53
- Community 54
- Community 55
- Community 56
- Community 57
- Community 58
- Community 59
- Community 60
- Community 61
- Community 62
- Community 63
- Community 64
- Community 65
- Community 66
- Community 67
- Community 68
- Community 69
- Community 70
- Community 71
- Community 72
- Community 73
- Community 74
- Community 75
- Community 76
- Community 77
- Community 78
- Community 79
- Community 80
- Community 81
- Community 82
- Community 83
- Community 84
- Community 85
- Community 86
- Community 87
- Community 88
- Community 89
- Community 90
- Community 91
- Community 92
- Community 93
- Community 94
- Community 95
- Community 96
- Community 97
- Community 98
- Community 99
- Community 100
- Community 101
- Community 102
- Community 103
- Community 104
- Community 105
- Community 106
- Community 107
- Community 108
- Community 109
- Community 110
- Community 111
- Community 112
- Community 113
- Community 114
- Community 115
- Community 116
- Community 117
- Community 118
- Community 119
- Community 120
- Community 121
- Community 122
- Community 123
- Community 124
- Community 125
- Community 126
- Community 127
- Community 128
- Community 129
- Community 130
- Community 131
- Community 132
- Community 133
- Community 134
- Community 135
- Community 136
- Community 137
- Community 138
- Community 139
- Community 140
- Community 141
- Community 142
- Community 143
- Community 144
- Community 145
- Community 146
- Community 147
- Community 148
- Community 149
- Community 150
- Community 151
- Community 152
- Community 153
- Community 154
- Community 155
- Community 156
- Community 157
- Community 158
- Community 159
- Community 160
- Community 161
- Community 162
- Community 163
- Community 164
- Community 165
- Community 166
- Community 167
- Community 168
- Community 169
- Community 170
- Community 171
- Community 172
- Community 173
- Community 174
- Community 175
- Community 176
- Community 177
- Community 178
- Community 179
- Community 180
- Community 181
- Community 182
- Community 183
- Community 184
- Community 185
- Community 186
- Community 187
- Community 188
- Community 189
- Community 190
- Community 191
- Community 192
- Community 193
- Community 194
- Community 195
- Community 196
- Community 197
- Community 198
- Community 199
- Community 200
- Community 201
- Community 202
- Community 203
- Community 204
- Community 205
- Community 206
- Community 207
- Community 208
- Community 209
- Community 210
- Community 211
- Community 212
- Community 213
- Community 214
- Community 215
- Community 216
- Community 217
- Community 218
- Community 219
- Community 220
- Community 229
- Community 230
- Community 231
- Community 232
- Community 233
- Community 234
- Community 235
- Community 236
- Community 237
- Community 238
- Community 239
- Community 240
- Community 241
- Community 242
- Community 243

## God Nodes (most connected - your core abstractions)
1. `Model` - 176 edges
2. `Instance` - 175 edges
3. `Service` - 134 edges
4. `Manager` - 120 edges
5. `handle_model_exceptions()` - 81 edges
6. `SchemaException` - 79 edges
7. `TaskDefinition` - 77 edges
8. `ObjectLoader` - 75 edges
9. `bind_controller()` - 75 edges
10. `TagsMixin` - 70 edges

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
- **Configuration Processing Pipeline** — docs_source_api_adapters_config_config_rst_deployfish_config_config, docs_source_api_config_config_processors_rst_deployfish_config_processors, docs_source_api_config_config_processors_rst_abstract_processor, docs_source_api_config_config_processors_rst_environment_processor, docs_source_api_config_config_processors_rst_terraform_processor, readme_md_deployfish_yml [INFERRED 0.85]
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

## Communities (245 total, 80 thin omitted)

### Community 0 - "AWS Resource Models"
Cohesion: 0.02
Nodes (123): LazyAttributeMixin, Model lazy attribute mixin behavior., Model scalable target behavior. Args: data: data. policies: policies., Pk. Returns: Operation result., Name. Returns: Operation result., ScalableTarget, Model security group behavior., Pk. Returns: Operation result. (+115 more)

### Community 1 - "Abstract Model Layer"
Cohesion: 0.02
Nodes (99): Manager, Model, Get many. Args: pks: pks. Keyword Args: _: ., Model model behavior. Args: data: data., Exists. Returns: Operation result., Save. Returns: Operation result., Handle str. Returns: Operation result., Model manager behavior. (+91 more)

### Community 2 - "Exception Hierarchy"
Cohesion: 0.03
Nodes (89): BaseMultipleObjectsReturned, BaseOperationFailed, DoesNotExist, ImproperlyConfigured, MultipleObjectsReturned, OperationFailed, Delete. Args: obj: obj. Keyword Args: _: ., We tried to get a single object but it does not exist in AWS. (+81 more)

### Community 3 - "Instance Properties"
Cohesion: 0.03
Nodes (51): Instance, Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., List. Args: vpc_id: vpc id. Returns: Operation result., Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., Get. Args: pk: pk. vpc_id: vpc id. Keyword Args: _: . Returns: Operation result., Get many. Args: pks: pks. vpc_id: vpc id. Keyword Args: _: . Returns: Operation…, List. Args: vpc_ids: vpc ids. image_ids: image ids. instance_types: instance…, Arn. Returns: Operation result. (+43 more)

### Community 4 - "Event Scheduling"
Cohesion: 0.02
Nodes (51): Any, List. Args: cluster: cluster. service: service. family: family.…, :param pk str: a string like "{cluster}:{container_instance_id}" Args: pk: pk.…, :param cluster str: the name of an ECS cluster Args: cluster: cluster. Returns:…, :param pk str: cluster name Args: pk: pk. Returns: Operation result., :param pk str: a string like "{cluster_name}:{service_name}" Args: pk: pk.…, Scale. Args: obj: obj. count: count., Initialize TaskDefinition. Args: data: data. containers: containers. (+43 more)

### Community 5 - "CRUD Operations"
Cohesion: 0.03
Nodes (44): ex, Create waiter. Args: obj: obj. Keyword Args: _: ., Create an object in AWS from configuration in deployfish.yml., Update waiter. Args: obj: obj. Keyword Args: _: ., Update an object in AWS from configuration in deployfish.yml., Delete waiter. Args: obj: obj. Keyword Args: _: ., Delete an object from AWS by primary key., Show details about a single object in AWS. (+36 more)

### Community 6 - "ECS Cluster Ops"
Cohesion: 0.04
Nodes (51): ECSCluster, ex, Change desired count for a service., Model ecscluster behavior., Scale the number of instances in an ECS Cluster to match ``count``. ..…, Meta, ObjectSecretsController, Controller (+43 more)

### Community 7 - "ECS Service Layer"
Cohesion: 0.03
Nodes (40): datetime, List. Args: cluster_name: cluster name. Returns: Operation result., Get many. Args: pks: pks. Keyword Args: _: . Returns: Operation result., # FIXME: INACTIVE should not be considered the same as non-existant, List. Args: cluster_name: cluster name. service_name: service name.…, If this is a FARGATE task definition, return ``True``. Otherwise return…, Timestamp. Returns: Operation result., # FIXME: should we be splitting these into Secrets and ExternalSecrets so we… (+32 more)

### Community 8 - "CLI Controllers"
Cohesion: 0.05
Nodes (52): ArgparseController, Parse a date string in the form YYYY-MM-DD and return a datetime. Args: s: s.…, valid_date(), get_task(), Return the ``ServiceHelperTask`` whose related to ``obj`` whose command name…, CrudBase, Meta, Controller (+44 more)

### Community 9 - "Service Commands"
Cohesion: 0.07
Nodes (32): ECSServiceCommandLogs, ECSServiceCommands, Meta, Controller, Model ecsservice command logs behavior., Model ecsservice commands behavior., ECSService, ECSServiceStandaloneTasks (+24 more)

### Community 10 - "Docker Exec Tunnel"
Cohesion: 0.04
Nodes (52): Meta, ObjectDockerExecController, ObjectSSHController, Controller, Model object docker exec controller behavior., Return an (instance, container_name) tuple suitable for using to exec into a…, Return an (task_arn, container_name) tuple suitable for using to exec into a…, Exec into a container running in an existing… (+44 more)

### Community 11 - "Controller Base"
Cohesion: 0.05
Nodes (55): Base, BaseService, BaseServiceDockerExec, BaseServiceSecrets, BaseServiceSSH, filename_envvar(), maybe_rename_existing_file(), Meta (+47 more)

### Community 12 - "Quality Gate Tools"
Cohesion: 0.07
Nodes (63): AST, _check_file(), _check_function_doc(), _constructor_has_args(), _first_doc_line(), _function_has_args(), _function_has_keyword_args(), _function_uses_return_or_yield() (+55 more)

### Community 13 - "Task Definitions"
Cohesion: 0.04
Nodes (28): Get task definition. Args: secrets: secrets. Returns: Operation result., An ECS Task Definition. Args: data: data. containers: containers., If this task definition exists in AWS, return our ``<family>:<revision>``…, Name. Returns: Operation result., Arn. Returns: Operation result., Render for display. Returns: Operation result., Render for diff. Returns: Operation result., Render. Returns: Operation result. (+20 more)

### Community 14 - "Terraform State"
Cohesion: 0.06
Nodes (29): Any, Model terraform s3 state behavior. Args: terraform_config: terraform config.…, Initialize TerraformS3State. Args: terraform_config: terraform config. context:…, Retrive our statefile from S3 Args: state_file_url: state file url. profile:…, Handle load pre version 12. Args: tfstate: tfstate., Handle load post version 12. Args: tfstate: tfstate., Load. Args: replacements: replacements., Initialize TerraformEnterpriseState. Args: terraform_config: terraform config.… (+21 more)

### Community 15 - "Community 15"
Cohesion: 0.06
Nodes (28): Any, Model task definition fargatemixin behavior., If this is a FARGATE task definition, return ``True``. Otherwise return…, Return the minimum necessary cpu for our task by summing up 'cpu' from each of…, For FARGATE tasks, task cpu is required and must be one of the values listed in…, For EC2 tasks, set task cpu if 'cpu' is provided, don't set otherwise. If 'cpu'…, Set task cpu requirement, based on whether this is a FARGATE task or an EC2…, Find the minimum necessary memory and maximum necessary memory for our task by… (+20 more)

### Community 16 - "Community 16"
Cohesion: 0.09
Nodes (33): ContainerDefinitionAdapter, Model vpc configuration mixin behavior., Convert our deployfish YAML definition of our containers to the same format…, ``deployfish.yml`` docker labels are defined in one of the two following ways::…, VpcConfigurationMixin, CloudWatchLogGroupTailer, CloudWatchLogStream, CloudWatchLogStreamIterator (+25 more)

### Community 17 - "Community 17"
Cohesion: 0.06
Nodes (33): Config, NoSuchSectionError, NoSuchSectionItemError, Any, Session, setter, Initialize config state from a file path or provided payload. Args: filename:…, Returns: The pre-interpolated version of the raw YAML. (+25 more)

### Community 18 - "Community 18"
Cohesion: 0.07
Nodes (28): color(), DeployfishJinja2OutputHandler, fromtimestamp(), lb_listener_table(), load(), Meta, Any, Render table for target groups. Args: data: Target-group-like row objects.… (+20 more)

### Community 19 - "Community 19"
Cohesion: 0.06
Nodes (24): Any, Args: data: the ``tasks:`` section from our service definition in…, Set a ``data[data_key]`` on the dict ``data`` by looking at both ``task`` and…, Construct ``data`` so that it can be used for constructing our…, Update the deployfish-specific environment variables in the container…, Build a dict that takes info from the service and overlays the generic (not…, Change old style command defintions that look like this: tasks: - family:…, Build a dict that takes info from the output of :py:meth:`_get_base_task_data`… (+16 more)

### Community 20 - "Community 20"
Cohesion: 0.06
Nodes (15): Stable identity key used by baseline filtering., Construct and optionally interpolate a config object. Keyword Args: kwargs:…, Lazy load the deployfish.yml file. We only load it on request because most…, Lazy load the deployfish.yml file into a :py:class:`deployfish.config.Config`…, Path, TestConfigExtended, Path, TestConfigModule (+7 more)

### Community 21 - "Community 21"
Cohesion: 0.06
Nodes (18): AutoscalingGroup, Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., List. Returns: Operation result., Model autoscaling group behavior., Pk. Returns: Operation result., Name. Returns: Operation result., Autoscaling group. Returns: Operation result., Instances. Returns: Operation result. (+10 more)

### Community 22 - "Community 22"
Cohesion: 0.05
Nodes (24): InvokedTask, DockerMixin, Handle get cluster and task arn from pk. Args: pk: pk. Returns: Operation…, :param name str: a string like '{cluster}:{task_arn}' Args: pk: pk. Keyword…, A record of a running AWS ECS Task, which means either a task running as part…, Pk. Returns: Operation result., Name. Returns: Operation result., Arn. Returns: Operation result. (+16 more)

### Community 23 - "Community 23"
Cohesion: 0.06
Nodes (8): The problem here is that, unlike all our other adapters, we need to create…, ServiceHelperTaskAdapter, TestServiceHelperTaskAdapterComprehensive, BaseTestServiceHelperTaskAdapter_basic, If we have no vpc_configuration, our network mode should be forced to 'bridge'., Ensure old style command definitions still work: tasks: - family: foobar-test-…, If we have vpc_configuration, our network mode should be forced to 'awsvpc'., TestServiceHelperTaskAdapter_FARGATE

### Community 24 - "Community 24"
Cohesion: 0.05
Nodes (19): Cluster, :param pk str: cluster name Args: pk: pk. Keyword Args: _: . Returns: Operation…, :param pk list[str]: list of cluster names Args: pks: pks. Keyword Args: _: .…, Pk. Returns: Operation result., Name. Returns: Operation result., Arn. Returns: Operation result., Cluster type. Returns: Operation result., Container instances. Returns: Operation result. (+11 more)

### Community 25 - "Community 25"
Cohesion: 0.07
Nodes (21): CloudWatchLogGroup, CloudWatchLogGroupManager, Model cloud watch log group manager behavior., Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., List. Args: prefix: prefix. Returns: Operation result., Model cloud watch log group behavior., Pk. Returns: Operation result., Name. Returns: Operation result. (+13 more)

### Community 26 - "Community 26"
Cohesion: 0.06
Nodes (21): Returns: The engine for this RDS instance (e.g. "mysql"), Returns: The version of the engine for this RDS instance., Returns: The hostname of the db endpoint, Returns: The port for this RDS instance (e.g. "mysql"), Returns: The username of the root user for this instance., Secret enabled. Returns: Operation result., Returns: The ARN of the Secrets Manager Secret used to store the password for…, Root password. Returns: Operation result. (+13 more)

### Community 27 - "Community 27"
Cohesion: 0.06
Nodes (20): LoadBalancerListenerRule, Any, List. Args: load_balancer: load balancer. Returns: Operation result., Initialize LoadBalancerListenerRuleManager., Get many. Args: pks: pks. Keyword Args: _: . Returns: Operation result., Handle get rules for load balancer. Args: load_balancer_pk: load balancer pk.…, Handle get rules for target group. Args: target_group_arn: target group arn.…, List. Args: listener_arn: listener arn. load_balancer_pk: load balancer pk.… (+12 more)

### Community 28 - "Community 28"
Cohesion: 0.12
Nodes (23): BaseSkipConfigProcessing, AbstractConfigProcessor, ProcessingFailed, A base class for processors for our our ``deployfish.yml`` file. These…, Return all known replacements for ``deployfish.yml`` section name…, SkipConfigProcessing, # FIXME: need to deal with multiple matches in the same line, ConfigProcessor (+15 more)

### Community 29 - "Community 29"
Cohesion: 0.06
Nodes (18): Handle get service and cluster from pk. Args: pk: pk. Returns: Operation result., Exists. Args: pk: pk. Returns: Operation result., Save. Args: obj: obj. Keyword Args: _: ., Create. Args: obj: obj., Update. Args: obj: obj., Delete. Args: obj: obj. Keyword Args: _: ., Copy. Returns: Operation result., Handle add. Args: other: other. Returns: Operation result. (+10 more)

### Community 30 - "Community 30"
Cohesion: 0.08
Nodes (8): SecretsMixin, Model standalone task adapter behavior., StandaloneTaskAdapter, TestAbstractTaskAdapterBranches, TestStandaloneTaskAdapterComprehensive, BaseTestStandaloneTaskAdapter_basic, If we have vpc_configuration, our network mode should be forced to 'awsvpc'., TestStandaloneTaskAdapter_FARGATE

### Community 31 - "Community 31"
Cohesion: 0.09
Nodes (7): New. Args: obj: obj. source: source. Keyword Args: kwargs: kwargs. Returns:…, TestServiceManagerCreate, TestFargateServiceProperties, TestServiceDelete, TestServiceSaveHelperTasks, TestServiceSave, TestService_new

### Community 32 - "Community 32"
Cohesion: 0.08
Nodes (20): Annotator, process_service_update(), Get the committer for the most recent commits. Returns: Operation result., Get the deployer for the most recent commits. Returns: Operation result., Get the version for the most recent commits. Returns: Operation result., Get the name of the service. Returns: Operation result., Get the name of the service. Returns: Operation result., Get the title for the message. Returns: Operation result. (+12 more)

### Community 33 - "Community 33"
Cohesion: 0.10
Nodes (8): * Service itself [x] Args: data: data., Get client token. Returns: Operation result., Get load balancers. Returns: Operation result., Update ``data`` with the configuration for the Service itself. This will look…, ServiceAdapter, TestECSAdapterGaps, TestServiceAdapterComprehensive, TestServiceAdapter

### Community 34 - "Community 34"
Cohesion: 0.07
Nodes (18): LoadBalancerListener, Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., Model load balancer listener behavior., Pk. Returns: Operation result., Name. Returns: Operation result., Arn. Returns: Operation result., Port. Returns: Operation result., Protocol. Returns: Operation result. (+10 more)

### Community 35 - "Community 35"
Cohesion: 0.06
Nodes (18): ClassicLoadBalancerTarget, Any, List. Args: load_balancer_name: load balancer name. Returns: Operation result., Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., Ssl policy. Returns: Operation result., Model classic load balancer target behavior. Args: data: data. instance:…, Initialize ClassicLoadBalancerTarget. Args: data: data. instance: instance., Pk. Returns: Operation result. (+10 more)

### Community 36 - "Community 36"
Cohesion: 0.07
Nodes (19): ex, Build a ``deployfish.core.waiters.HookedWaiter`` for the operation named…, Show info about a ServiceHelperTask object associated with a Service that…, List the helper tasks associated with a Service in AWS., Update command definitions in AWS independently of their Service., If a command for a Service has a schedule rule and that rule is currently…, If a command for a Service has a schedule rule and that rule is currently…, Run task waiter. Args: tasks: tasks. Keyword Args: kwargs: kwargs. (+11 more)

### Community 37 - "Community 37"
Cohesion: 0.08
Nodes (16): Any, Get. Args: pk: pk. Keyword Args: _: ., Save. Args: obj: obj. Keyword Args: _: ., Exists. Args: pk: pk. Returns: Operation result., Diff. Args: obj: obj. Returns: Operation result., Needs update. Args: obj: obj. Returns: Operation result., Given an appropriate bit of data `obj` from a data source `source`, return the…, This is a factory method. .. note:: The ``**kwargs`` here is for the Adapter to… (+8 more)

### Community 38 - "Community 38"
Cohesion: 0.10
Nodes (20): App, Store active Cement app for config helpers. Args: app: Cement app whose config…, set_app(), DeployfishAppError, Model deployfish app error behavior., DeployfishApp, main(), maybe_do_cli_debugging() (+12 more)

### Community 39 - "Community 39"
Cohesion: 0.11
Nodes (16): ECSServiceScalableTargetAdapter, ECSServiceScalingPolicyAdapter, Any, .. code-block:: python Args: data: data., Initialize ECSServiceScalableTargetAdapter. Args: data: data. Keyword Args:…, .. code-block:: python Args: data: data., Get resource id. Returns: Operation result., Convert. Returns: Operation result. (+8 more)

### Community 40 - "Community 40"
Cohesion: 0.09
Nodes (18): DeployfishCementPluginHandler, get_deployfish_plugins(), load(), Meta, App, Cement plugin extension module., Load plugin. Args: plugin_name: plugin name., Load a list of plugins. Args: plugins: A list of plugin names to load. (+10 more)

### Community 41 - "Community 41"
Cohesion: 0.07
Nodes (30): ECS Lifecycle Management, Terraform State Integration, SecretAdapter, ServiceAdapter, Service.save Creation Flow, TaskDefinitionAdapter, Basic ECS Service Tutorial, hello-world-test Service Example (+22 more)

### Community 42 - "Community 42"
Cohesion: 0.13
Nodes (18): Adapter, Return whether exactly one value in ``data`` is truthy. Args: data: Boolean…, Given a dict of data from a data source, convert it appropriate data Args:…, ECSServiceCPUAlarmAdapter, .. code-block:: python Args: data: data., EventScheduleRuleAdapter, EventTargetAdapter, # FIXME: use VpcConfigurationMixin for this (+10 more)

### Community 43 - "Community 43"
Cohesion: 0.07
Nodes (14): LoadBalancer, Get many. Args: pks: pks. Keyword Args: kwargs: kwargs. Returns: Operation…, Model load balancer behavior., Pk. Returns: Operation result., Name. Returns: Operation result., Arn. Returns: Operation result., Lb type. Returns: Operation result., Scheme. Returns: Operation result. (+6 more)

### Community 44 - "Community 44"
Cohesion: 0.09
Nodes (29): Base, deployfish.controllers.base, Cluster, deployfish.controllers.cluster, Commands, deployfish.controllers.commands, Crud, deployfish.controllers.crud (+21 more)

### Community 45 - "Community 45"
Cohesion: 0.09
Nodes (28): Class-Oriented Architecture Preference, sphinx-click, VPC Bastion Host Assumption, deploy cluster command, deploy service exec, deploy service ssh, deployfish.core.adapters.abstract, deployfish.core.adapters.deployfish.appscaling (+20 more)

### Community 46 - "Community 46"
Cohesion: 0.12
Nodes (16): AWSSessionBuilder, build_boto3_session(), ForbiddenAWSAccountId, NoSuchAWSProfile, Any, Exception, Session, Build a boto3 session object from the deployfish.yml file, commandline flags… (+8 more)

### Community 47 - "Community 47"
Cohesion: 0.07
Nodes (18): setter, Return a dictionary of the secrets (AWS SSM Parameter Store parameters) for…, Secrets. Args: value: value., Secrets. Returns: Operation result., Secrets. Args: value: value., Secrets. Returns: Operation result., Secrets. Args: value: value., Service names are only unique within a cluster, so to fully identify a service… (+10 more)

### Community 48 - "Community 48"
Cohesion: 0.11
Nodes (14): ExternalParameterException, parse_secret_string(), Any, Exception, Parse an identifier from a deployfish.yml parameter definition that looks like…, Model secret adapter behavior. Args: data: data., Initialize SecretAdapter. Args: data: data. Keyword Args: kwargs: kwargs., Is external. Returns: Operation result. (+6 more)

### Community 49 - "Community 49"
Cohesion: 0.11
Nodes (10): Task related tags we need to read from a task definition associated with a…, Initialize TaskTagImporter., Capacity Provider Strategies are stored in tags like::…, ``placementStrategy`` is stored in tags as:: 'deployfish:placementStrategy.0':…, Handle convert awsvpc configuration. Args: key: key. value: value., TaskTagImporter, Coverage for TaskTagImporter/Exporter and VPCConfigurationMixin., TestTaskTagImporter (+2 more)

### Community 50 - "Community 50"
Cohesion: 0.11
Nodes (10): Service waiter. Args: obj: obj. Keyword Args: kwargs: kwargs., Delete waiter. Args: obj: obj. Keyword Args: kwargs: kwargs., Show periodic updates while we change desired count for a service. Args: obj:…, ECSDeploymentStatusWaiterHook, Success. Args: status: status. response: response. num_attempts: num attempts.…, Failure. Args: status: status. response: response. num_attempts: num attempts.…, Timeout. Args: status: status. response: response. num_attempts: num attempts.…, This for both the 'services_stable' and 'services_inactive' waiters on ECS.… (+2 more)

### Community 51 - "Community 51"
Cohesion: 0.08
Nodes (12): Build a list of Secret and ExternalSecret objects from our Service's config:…, Add parameter store values to the container's 'secrets' list. The task will…, In ``deployfish.yml``, volumes take one of these two forms:: volumes: -…, ``deployfish.yml`` port mappings look like this:: ports: - "80" - "8443:443" -…, ``deployfish.yml`` environment variables are defined in one of the two…, Get ulimits. Returns: Operation result., Get log configuration. Returns: Operation result., Get linux parameters. Returns: Operation result. (+4 more)

### Community 52 - "Community 52"
Cohesion: 0.11
Nodes (12): Model scaling policy behavior. Args: data: data. alarm: alarm., Initialize ScalingPolicy. Args: data: data. alarm: alarm., Pk. Returns: Operation result., Name. Returns: Operation result., Initialize ScalableTarget. Args: data: data. policies: policies., ScalingPolicy, CloudwatchAlarm, Name. Returns: Operation result. (+4 more)

### Community 53 - "Community 53"
Cohesion: 0.11
Nodes (24): Adapter Abstract Base, importer_registry Adapter Registry, Model.new Factory Method, Adapters Layer, Controllers Layer, ObjectLoader Pattern, Models Layer, Renderers Layer (+16 more)

### Community 54 - "Community 54"
Cohesion: 0.10
Nodes (5): _DockerHost, Any, DockerMixin, setter, TestDockerMixinPush

### Community 55 - "Community 55"
Cohesion: 0.09
Nodes (12): MySQLDatabase, self.data here has the following structure: { 'name': 'string', 'service':…, Pk. Returns: Operation result., Name. Returns: Operation result., Ssh target. Returns: Operation result., Ssh targets. Returns: Operation result., Cluster. Returns: Operation result., Update. Args: root_user: root user. root_password: root password. ssh_target:… (+4 more)

### Community 56 - "Community 56"
Cohesion: 0.13
Nodes (8): Coverage for Service render/save paths and related model branches., _service_from_aws(), _service_from_yml(), TestServiceProperties, TestServiceRenderForDiff, TestServiceRenderForDisplay, TestServiceRenderForUpdate, TestServiceSaveFlow

### Community 57 - "Community 57"
Cohesion: 0.19
Nodes (19): Client. Returns: Operation result., application_scaling_yml(), config_secrets_yml(), fargate_service_yml(), helper_tasks_yml(), minimal_deployfish_yml(), mock_boto3_client(), _mock_boto3_session() (+11 more)

### Community 58 - "Community 58"
Cohesion: 0.13
Nodes (15): AnnotationMixin, CodebuildMixin, DeployfishDeployMixin, DockerImageNameMixin, DockerMixin, Model annotation mixin behavior., Annotate. Args: context: context., Model codebuild mixin behavior. Args: *args: args. (+7 more)

### Community 59 - "Community 59"
Cohesion: 0.11
Nodes (11): AbstractWaiterHook, Do something when our waiter status is 'timeout'. Args: status: status.…, Initialize AbstractWaiterHook. Args: obj: obj., Mark. Args: status: status. response: response. num_attempts: num attempts.…, Model abstract waiter hook behavior. Args: obj: obj., Do something when our waiter status is 'error'. Args: status: status. response:…, ECSTaskLogsHook, This for the 'tasks_stopped'' waiters on ECS. Args: obj: obj. (+3 more)

### Community 60 - "Community 60"
Cohesion: 0.18
Nodes (7): ECSClusterSSH, Meta, Model ecscluster ssh behavior., Render a list of results as an ASCII table. Args: columns: Column configuration…, TableRenderer, TestTableRendererExtended, TestTableRenderer

### Community 61 - "Community 61"
Cohesion: 0.15
Nodes (11): AbstractTaskAdapter, # TODO: if the host_path doesn't start with a /, ensure that, Model abstract task adapter behavior., Any, Convert. Returns: Operation result., Model sshconfig mixin behavior., SSHConfigMixin, Model secrets mixin behavior. (+3 more)

### Community 62 - "Community 62"
Cohesion: 0.16
Nodes (7): Initialize ServiceAdapter. Args: data: data. Keyword Args: kwargs: kwargs., Convert our deployfish YAML definition of our task definition to the same…, Initialize TaskDefinitionAdapter. Args: data: data. secrets: secrets.…, Initialize ContainerDefinitionAdapter. Args: data: data. task_definition_data:…, TaskDefinitionAdapter, TestTaskDefinitionAdapterComprehensive, TestTaskDefinitionAdapter

### Community 63 - "Community 63"
Cohesion: 0.15
Nodes (9): GitMixin, Model git mixin behavior. Args: *args: args., Initialize GitMixin. Args: *args: args. Keyword Args: url_type: url type.…, Handle format url. Args: url: url. label: label. Returns: Operation result., Handle build url patterns., Update the `values` dict with: * `previous_version`: the version number for the…, Handle get concise info. Returns: Operation result., Extract info about the git repo. Assume we're in the checked out clone. Args:… (+1 more)

### Community 64 - "Community 64"
Cohesion: 0.15
Nodes (12): DeployfishMessage, process_service_update(), Initialize ServiceUpdateMessage. Args: app: app. obj: obj. repo_folder: repo…, Add service update. Args: obj: obj., Process service update. Args: app: app. obj: obj. success: success. reason:…, A message from deployfish. Args: app: app. *args: args., Initialize DeployfishMessage. Args: app: app. *args: args. Keyword Args:…, A message indicating that a service has been updated. Args: app: app. obj: obj.… (+4 more)

### Community 65 - "Community 65"
Cohesion: 0.11
Nodes (19): CloudWatch, deployfish.core.models.cloudwatch, CloudWatch Logs, deployfish.core.models.cloudwatchlogs, deployfish.core.models.ec2, Elastic Compute Cloud, deployfish.core.models.efs, Elastic File System (+11 more)

### Community 66 - "Community 66"
Cohesion: 0.12
Nodes (11): Model scalable target manager behavior., Get a single ScalableTarget. Args: pk: pk. Keyword Args: _: . Returns:…, List. Returns: Operation result., Model scaling policy manager behavior., Delete. Args: obj: obj. Keyword Args: _: ., Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., Arn. Returns: Operation result., List. Args: cluster: cluster. service: service. Returns: Operation result. (+3 more)

### Community 67 - "Community 67"
Cohesion: 0.12
Nodes (8): EventTarget, :py:attr:`data` here has the same structure as what is returned by Args: data:…, Pk. Returns: Operation result., Name. Returns: Operation result., Arn. Returns: Operation result., Set task definition arn. Args: arn: arn., List. Args: rule: rule. Returns: Operation result., TestEventTargetManager

### Community 68 - "Community 68"
Cohesion: 0.15
Nodes (10): AbstractTerraformState, Model terraform enterprise state behavior. Args: terraform_config: terraform…, Get terraform state download url. Returns: Operation result., Load. Args: _: ., Model abstract terraform state behavior. Args: terraform_config: terraform…, Initialize AbstractTerraformState. Args: terraform_config: terraform config.…, Load. Args: replacements: replacements., Lookup. Args: attr: attr. replacements: replacements. Returns: Operation result. (+2 more)

### Community 69 - "Community 69"
Cohesion: 0.15
Nodes (9): Get waiter. Args: waiter_name: waiter name. Returns: Operation result., create_hooked_waiter_with_client(), HookedWaiter, :type name: string :param name: The name of the waiter :type config:…, Wait. Keyword Args: kwargs: kwargs., :type waiter_name: str :param waiter_name: The name of the waiter. The name…, A HookedWaiter is almost exactly like a standard boto3 Waiter with one…, TestCreateHookedWaiterWithClient (+1 more)

### Community 70 - "Community 70"
Cohesion: 0.12
Nodes (9): Name. Returns: Operation result., Port. Returns: Operation result., Health. Returns: Operation result., Target. Returns: Operation result., Target group. Returns: Operation result., List. Args: target_group_arn: target group arn. Returns: Operation result., Model target group target behavior., Pk. Returns: Operation result. (+1 more)

### Community 71 - "Community 71"
Cohesion: 0.13
Nodes (9): Any, Save. Args: obj: obj. Keyword Args: _: . Returns: Operation result., Create. Args: obj: obj. Returns: Operation result., Update. Args: obj: obj. Returns: Operation result., Render for diff. Returns: Operation result., Initialize ServiceDiscoveryService. Args: data: data. Keyword Args: kwargs:…, Render for diff. Returns: Operation result., Render for create. Returns: Operation result. (+1 more)

### Community 72 - "Community 72"
Cohesion: 0.13
Nodes (9): Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., Model service discovery namespace behavior., Pk. Returns: Operation result., Name. Returns: Operation result., Namespace. Returns: Operation result., List. Keyword Args: private_only: private only. Returns: Operation result., ServiceDiscoveryNamespace, _paginate() (+1 more)

### Community 73 - "Community 73"
Cohesion: 0.17
Nodes (8): _cluster_paginator(), _describe_services_by_name(), Any, _service_data(), _service_paginator(), TestServiceManagerGetManyExtended, TestServiceManagerListFilters, TestServicePropertiesExtended

### Community 74 - "Community 74"
Cohesion: 0.19
Nodes (8): EnvironmentConfigProcessor, Any, Replace. Args: obj: obj. key: key. value: value. section_name: section name.…, Model environment config processor behavior. Args: config: config. context:…, Initialize EnvironmentConfigProcessor. Args: config: config. context: context., Handle load env file. Args: filename: filename. Returns: Operation result., Load per item environment. Args: section_name: section name. item_name: item…, TestEnvironmentConfigProcessor

### Community 75 - "Community 75"
Cohesion: 0.16
Nodes (9): Pk looks like '{namespace_pk}:{service_name}' Args: pk: pk. Returns: Operation…, `pk` is just a bare service name. Args: pk: pk. Returns: Operation result., `pk` is one of:: * a service id, which starts with "srv-" * a string like…, List. Args: namespace: namespace. Returns: Operation result., Delete. Args: obj: obj. Keyword Args: _: ., Pk. Returns: Operation result., Model service discovery service manager behavior., `pk` is a service['Id']: "srv-{hexstring}" Args: pk: pk. Returns: Operation… (+1 more)

### Community 76 - "Community 76"
Cohesion: 0.12
Nodes (8): Deployfish supports putting 'config.KEY' as the value for the host and port…, Host. Returns: Operation result., User. Returns: Operation result., Db. Returns: Operation result., Password. Returns: Operation result., Character set. Returns: Operation result., Collation. Returns: Operation result., Port. Returns: Operation result.

### Community 77 - "Community 77"
Cohesion: 0.14
Nodes (9): GitChangelogMixin, Any, Look through the commits between the current version and the last version…, This needs to be used after GitMixin in the inheritance chain., Look through the commits between the current version and the last version…, Annotate. Args: values: values., Annotate. Args: values: values., Annotate. Args: values: values. (+1 more)

### Community 78 - "Community 78"
Cohesion: 0.17
Nodes (8): Any, Render byte count into human-readable units. Args: value: Byte count to format.…, Render values using builtin datatype formatting rules. Args: value: Value to…, Reformat one value into a more human-friendly form. Args: obj: Source object…, Render one column value for one row object. Args: obj: Source object for the…, Render all rows into a formatted table string. Args: data: Sequence of row-like…, Initialize table renderer. Args: columns: Column configuration keyed by output…, Dereference one column from an object or rendered mapping. Args: obj: Source…

### Community 79 - "Community 79"
Cohesion: 0.17
Nodes (7): Specialized renderer for ECS target groups., Render attached load balancer names. Args: obj: Target group being rendered.…, Render target names. Args: obj: Target group being rendered. _key: Unused…, Render listener protocol/port pairs. Args: obj: Target group being rendered.…, Render backing container protocol/port pair. Args: obj: Target group being…, TargetGroupTableRenderer, TestTargetGroupTableRendererGaps

### Community 80 - "Community 80"
Cohesion: 0.19
Nodes (5): _paginate(), TestLoadBalancerListenerManager, TestLoadBalancerListenerRuleManager, TestLoadBalancerManager, TestTargetGroupManager

### Community 81 - "Community 81"
Cohesion: 0.16
Nodes (5): Any, SecretsMixin, _SecretsHost, TestSecretModel, TestSecretsMixinWriteSecrets

### Community 82 - "Community 82"
Cohesion: 0.16
Nodes (8): Any, Perform string replacements on ``value``, a string value in our…, Process ``obj``, a value from a key of an item from ``deployfish.yml``, looking…, Process ``obj``, a list value of an item from ``deployfish.yml``, looking for…, Recurse through each key in our dict ``obj`` and process it appropriately. We…, This is the method that :py:class:`ConfigProcessor` will execute as it loops…, Initialize AbstractConfigProcessor. Args: config: config. context: context., Populate :py:attr:`deployfish_lookups`.

### Community 83 - "Community 83"
Cohesion: 0.15
Nodes (7): Run task waiter. Args: tasks: tasks. Keyword Args: kwargs: kwargs., ECSTaskStatusHook, This for the 'tasks_stopped'' waiters on ECS, and prints the status of our…, Waiting. Args: status: status. response: response. num_attempts: num attempts.…, Success. Args: status: status. response: response. num_attempts: num attempts.…, Timeout. Args: status: status. response: response. num_attempts: num attempts.…, TestECSTaskStatusHook

### Community 84 - "Community 84"
Cohesion: 0.21
Nodes (7): establish_tunnel(), get_tunnel_target(), Actually establish an SSH Tunnel. This does not return until the user manually…, Return an ``Instance`` object through which the user can make an ssh tunnel. If…, TestEstablishTunnel, TestGetTunnel, TestGetTunnelTarget

### Community 85 - "Community 85"
Cohesion: 0.15
Nodes (7): Any, Initialize ECSServiceCPUAlarmAdapter. Args: data: data. Keyword Args: kwargs:…, Get alarm name. Returns: Operation result., Get alarm description. Returns: Operation result., Get comparison operator. Returns: Operation result., Get threshold. Returns: Operation result., Convert. Returns: Operation result.

### Community 86 - "Community 86"
Cohesion: 0.18
Nodes (7): Copy. Returns: Operation result., Any, New. Args: obj: obj. source: source. Keyword Args: kwargs: kwargs. Returns:…, Initialize EventTarget. Args: data: data. rule: rule., New. Args: obj: obj. source: source. Keyword Args: _: . Returns: Operation…, Initialize EventScheduleRule. Args: data: data., .. note:: Ideally here we would compare the full task definition attached to…

### Community 87 - "Community 87"
Cohesion: 0.15
Nodes (7): Save. Args: obj: obj. Keyword Args: _: ., Save. Args: obj: obj. Keyword Args: kwargs: kwargs., Delete. Args: obj: obj. Keyword Args: kwargs: kwargs., Save. Args: obj: obj. Keyword Args: kwargs: kwargs., Delete. Args: obj: obj. Keyword Args: kwargs: kwargs., Delete. Args: obj: obj. Keyword Args: _: ., NoReturn

### Community 88 - "Community 88"
Cohesion: 0.17
Nodes (13): Basic ECS Services Example, load_balancer with target_group_arn, load_balancer with load_balancer_name, my-service-alb (ALB target group), my-service-elb (Classic ELB), network_mode: bridge, services section, task_role_arn IAM role (+5 more)

### Community 89 - "Community 89"
Cohesion: 0.15
Nodes (13): Python Dependencies, boto3 dependency, cement dependency, click dependency, docker dependency, gitpython dependency, jinja2 dependency, jsondiff2 dependency (+5 more)

### Community 91 - "Community 91"
Cohesion: 0.18
Nodes (7): CloudwatchAlarmManager, Arn. Returns: Operation result., Model cloudwatch alarm manager behavior., Get. Args: pk: pk. Keyword Args: kwargs: kwargs. Returns: Operation result., List. Args: cluster: cluster. service: service. Keyword Args: kwargs: kwargs.…, Save. Args: obj: obj. Keyword Args: kwargs: kwargs., Delete. Args: obj: obj. Keyword Args: kwargs: kwargs.

### Community 92 - "Community 92"
Cohesion: 0.20
Nodes (8): _event_timestamp_to_utc(), Any, datetime, Convert CloudWatch millisecond timestamps to aware UTC datetimes. Args:…, Handle next. Returns: Operation result., Handle next. Returns: Operation result., :param start_time datetime: a timezone aware, UTC datetime Args: stream:…, Handle next. Returns: Operation result.

### Community 93 - "Community 93"
Cohesion: 0.18
Nodes (7): EventScheduleRuleManager, Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., List. Returns: Operation result., If ``obj`` is disabled, change its state of "ENABLED". Otherwise, do nothing.…, If ``obj`` is enabled, change the its state to "DISABLED". Otherwise, do…, Get. Args: pk: pk. Keyword Args: kwargs: kwargs. Returns: Operation result., Model event schedule rule manager behavior.

### Community 94 - "Community 94"
Cohesion: 0.20
Nodes (8): ImproperlyConfiguredError, Exception, Path, Process a pyproject.toml file and return the name and version. Raises:…, Extract some stuff from setup.py, if present. If setup.py is present, we'll add…, We programmers improperly configured something., Process a setup.py file and return the name and version. Raises: ValueError: if…, Process a Makefile and return the name and version. Raises: ValueError: if the…

### Community 95 - "Community 95"
Cohesion: 0.17
Nodes (6): Do any necessary cleanup after the waiter iteration has completed and we've…, Args: * 'state': the current state of the waiter. One of 'waiting', 'success',…, Do any necessary setup on the waiter iteration before we've done our per-state…, Do something when our waiter status is 'waiting'. Args: status: status.…, Do something when our waiter status is 'success'. Args: status: status.…, Do something when our waiter status is 'failure'. Args: status: status.…

### Community 96 - "Community 96"
Cohesion: 0.17
Nodes (6): Create the database and user for ``obj``, and assign appropriate grants to the…, Update the grants and password for the database user on ``obj``. Args: obj: The…, Return the major.minor version of the MySQL server. Example: If the server…, Server version. Args: ssh_target: ssh target. verbose: verbose. user: user.…, Render for create. Args: root_user: root user. root_password: root password.…, Render for update. Args: root_user: root user. root_password: root password.…

### Community 97 - "Community 97"
Cohesion: 0.18
Nodes (12): Deployfish, Developer Guide, User Guide, AWS CLI v2, FARGATE container EXEC, Installation, pip install deployfish, Session Manager plugin (+4 more)

### Community 98 - "Community 98"
Cohesion: 0.24
Nodes (5): _paginate(), Additional ELBv2 manager coverage., TestLoadBalancerListenerModelPush, TestLoadBalancerManagerPush, TestTargetGroupManagerPush

### Community 99 - "Community 99"
Cohesion: 0.22
Nodes (6): Any, Save. Args: obj: obj. Keyword Args: _: ., Render for diff. Returns: Operation result., Render for diff. Returns: Operation result., Render for create. Returns: Operation result., Save. Args: obj: obj. Keyword Args: _: . Returns: Operation result.

### Community 100 - "Community 100"
Cohesion: 0.20
Nodes (6): Any, Save. Args: obj: obj. Keyword Args: kwargs: kwargs., Scale. Args: count: count. force: force., Render for update. Returns: Operation result., Render for diff. Returns: Operation result., Initialize Instance. Args: data: data.

### Community 101 - "Community 101"
Cohesion: 0.40
Nodes (4): CodeNameVersionMixin, Model code name version mixin behavior., Path, TestCodeNameVersionMixin

### Community 102 - "Community 102"
Cohesion: 0.25
Nodes (8): pre_config_interpolate_add_mysql_section(), App, Add our "mysql" section to the list of sections on which keyword interpolation…, add_template_dir(), load(), App, Add template dir. Args: app: app., Load. Args: app: app.

### Community 108 - "Community 108"
Cohesion: 0.20
Nodes (7): setter, Prefix. Returns: Operation result., Prefix. Args: value: value., Kms key id. Returns: Operation result., Kms key id. Args: value: value., Value. Returns: Operation result., Value. Args: value: value.

### Community 109 - "Community 109"
Cohesion: 0.20
Nodes (5): MySQLDatabaseManager, Model my sqldatabase manager behavior., List the MySQLDatabase objects in the config file. Returns: A list of…, Create. Args: root_user: root user. root_password: root password. ssh_target:…, This is an alias for :py:meth:`create`. Args: obj: The ``MySQLDatabase`` object…

### Community 110 - "Community 110"
Cohesion: 0.20
Nodes (5): Return the MySQL version of the MySQL server. Example: If the server version is…, Show the GRANTs for the database user on the remote database. Args: obj: The…, Render mysql command. Args: sql: sql. user: user. password: password. Returns:…, Render for server version. Args: user: user. password: password. Returns:…, Render for show grants. Returns: Operation result.

### Community 112 - "Community 112"
Cohesion: 0.24
Nodes (4): Any, SecretsMixin, _SecretsHost, TestSecretsMixin

### Community 113 - "Community 113"
Cohesion: 0.25
Nodes (5): Any, Get cluster arn. Returns: Operation result., Get vpc configuration. Returns: Operation result., Convert. Returns: Operation result., Convert. Returns: Operation result.

### Community 114 - "Community 114"
Cohesion: 0.25
Nodes (5): Any, Diff our list of Secrets against `other`. `other` is either a list of Secrets…, Initialize SecretManager. Args: model: model. Keyword Args: readonly: readonly., Initialize Secret. Args: data: data. name: name., Render for diff. Returns: Operation result.

### Community 115 - "Community 115"
Cohesion: 0.22
Nodes (5): Protocol, Model supports secrets behavior., Secrets. Returns: Operation result., Secrets. Args: value: value., SupportsSecrets

### Community 116 - "Community 116"
Cohesion: 0.25
Nodes (5): Manage our SSM Parameter Store parameters. This differs from Args: model: model., Delete. Args: obj: obj. Keyword Args: _: ., SecretManager, SecretManager edge cases., TestSecretManagerEdgeCases

### Community 117 - "Community 117"
Cohesion: 0.28
Nodes (5): AbstractRenderer, Any, Initialize renderer base class. Args: *args: Positional renderer configuration.…, Render provided data into a string. Args: data: Data to render. Keyword Args:…, Render structured data into human-readable output. Args: *args: Positional…

### Community 118 - "Community 118"
Cohesion: 0.22
Nodes (9): deploy mysql create, deploy mysql dump, deploy mysql load, deploy mysql show-grants, deploy mysql update, deploy mysql validate, deployfish-mysql plugin, ~/.deployfish.yml (+1 more)

### Community 119 - "Community 119"
Cohesion: 0.25
Nodes (9): Deployfish Plugin System, deployfish-slack Plugin, ~/.deployfish.yml User Config, deployfish-sqs Plugin, Extensible Custom Modules, Cement Application Plugins, DeployfishCementPluginHandler, Modular Plugin Architecture (+1 more)

### Community 120 - "Community 120"
Cohesion: 0.22
Nodes (9): Interpolation Test Config, service config secrets, ${env.*} environment variable interpolation, foobar-prod production service, network_mode: host, services section, terraform section, tunnels section (+1 more)

### Community 122 - "Community 122"
Cohesion: 0.31
Nodes (3): _aws_service(), TestServiceRenderMethods, TestTaskDefinitionProperties

### Community 124 - "Community 124"
Cohesion: 0.28
Nodes (3): _paginate(), TestServiceDiscoveryNamespaceManager, TestServiceDiscoveryServiceManager

### Community 125 - "Community 125"
Cohesion: 0.32
Nodes (5): CloudWatchLogStreamManager, Model cloud watch log stream manager behavior., Handle get group and stream from pk. Args: pk: pk. Returns: Operation result., Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., .. note:: ``log_group_name`` stays required because listing every stream in…

### Community 126 - "Community 126"
Cohesion: 0.29
Nodes (4): List all the ServiceHelperTasks. To do this accurately, we need to: * List all…, List. Args: scheduled_only: scheduled only. Returns: Operation result., List all Tasks (StandaloneTasks and ServiceHelperTasks), filtering by various…, List only the scheduled tasks, filtering by various dimensions. We do this by…

### Community 127 - "Community 127"
Cohesion: 0.25
Nodes (4): Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., Get many. Args: pks: pks. Keyword Args: kwargs: kwargs. Returns: Operation…, Load balancers. Returns: Operation result.

### Community 128 - "Community 128"
Cohesion: 0.29
Nodes (4): Handle get parameter values. Args: names: names. Keyword Args: decrypt:…, Convert. Args: parameter_data: parameter data. Returns: Operation result., .. note:: We need both encryption metadata from ``describe_parameters`` and…, List. Args: prefix: prefix. Keyword Args: decrypt: decrypt. Returns: Operation…

### Community 129 - "Community 129"
Cohesion: 0.25
Nodes (5): This is used for click commands, and gets re-raised when we get other…, Initialize RenderException. Args: msg: msg. exit_code: exit code., Initialize NoSuchConfigSection. Args: section: section., Initialize NoSuchConfigSectionItem. Args: section: section. name: name., RenderException

### Community 130 - "Community 130"
Cohesion: 0.25
Nodes (5): AdapterRegistry, Initialize AdapterRegistry., Register a new Adapter class with a model and a source. :param model_name: the…, Return the source -> model Adapter class to use for the source ``source`` and…, A registry of adapters which consume specific data sources to configure…

### Community 131 - "Community 131"
Cohesion: 0.25
Nodes (8): Tutorial 1 Minimal Service, hello-world-test minimal service, services section, Tutorial 2 Extended Service, container command override, container environment variables, hello-world-test with command and env, services section

### Community 133 - "Community 133"
Cohesion: 0.25
Nodes (3): TestCloudwatchAlarmModel, TestEFSFileSystemModel, TestRDSInstanceModel

### Community 135 - "Community 135"
Cohesion: 0.33
Nodes (4): Any, Initialize adapter with raw source data. Args: data: Raw source data to adapt.…, Copy one source value into output payload. Args: data: Destination payload…, Convert source payload into model constructor inputs. Returns: Tuple of adapted…

### Community 136 - "Community 136"
Cohesion: 0.33
Nodes (4): Filter ``tasks`` by various dimensions, returning only those tasks that match…, List all the StandaloneTasks, which means return the list of StandaloneTasks…, is_fnmatch_filter(), Use this function to determine if a string is a fnmatch filter, which is to say…

### Community 137 - "Community 137"
Cohesion: 0.29
Nodes (3): Save. Args: obj: obj. Keyword Args: _: . Returns: Operation result., Delete. Args: obj: obj. Keyword Args: _: ., Save ourselves as a Cloudwatch Events Rule target. :rtype: dict

### Community 138 - "Community 138"
Cohesion: 0.29
Nodes (3): Save. Args: obj: obj. Keyword Args: _: . Returns: Operation result., Delete many by name. Args: pks: pks., Render for create. Returns: Operation result.

### Community 139 - "Community 139"
Cohesion: 0.29
Nodes (4): Any, Deployfish supports putting 'config.KEY' as the value for the host and port…, Host. Returns: Operation result., Host port. Returns: Operation result.

### Community 140 - "Community 140"
Cohesion: 0.33
Nodes (4): Any, Display deployments. Args: deployments: deployments., Display events. Args: events: events., Waiting. Args: status: status. response: response. num_attempts: num attempts.…

### Community 141 - "Community 141"
Cohesion: 0.29
Nodes (7): Terraform Integration Example, {environment}/{service-name}/{cluster-name} replacements, services with terraform values, terraform section, ${terraform.*} string interpolation, terraform.lookups key mappings, terraform.statefile S3 path

### Community 146 - "Community 146"
Cohesion: 0.33
Nodes (4): _default_start_time_ms(), Initialize CloudWatchLogGroupTailer. Args: group: group. stream_prefix: stream…, :param start_time datetime: a timezone aware, UTC datetime Args: stream:…, Compute default tail start time in milliseconds. Args: sleep: Polling interval…

### Community 148 - "Community 148"
Cohesion: 0.33
Nodes (3): Get. Args: pk: pk. Keyword Args: _: . Returns: Operation result., Arn. Returns: Operation result., Modified username. Returns: Operation result.

### Community 149 - "Community 149"
Cohesion: 0.33
Nodes (3): Initialize ECSTaskStatusHook. Args: obj: obj., Initialize ECSDeploymentStatusWaiterHook. Args: obj: obj., Initialize ECSTaskLogsHook. Args: obj: obj.

### Community 150 - "Community 150"
Cohesion: 0.33
Nodes (6): deployfish.core.models.rds, Relational Database Service, deployfish.core.models.ssh, SSH, mysql section in deployfish.yml, AWS SSM Parameter Store

### Community 151 - "Community 151"
Cohesion: 0.33
Nodes (6): Cement CLI Framework, Click Colorful Output, deployfish.config Module, DeployfishApp (cement.App subclass), Jinja2 Templates, Architecture Doc Reference

### Community 152 - "Community 152"
Cohesion: 0.33
Nodes (6): Application Scaling Example, application_scaling, containers list, load_balancer configuration, my-service-scaling ECS service, services section

### Community 153 - "Community 153"
Cohesion: 0.33
Nodes (6): Multi-Container Task Example, container links, three-container task definition, mysql db container with alias, redis sidecar container, services section

### Community 154 - "Community 154"
Cohesion: 0.40
Nodes (6): Terraform Interpolate Test, foobar-prod service, foobar-qa service, foobar-qa and foobar-prod services, terraform section with {environment} statefile, mysql QA and prod tunnels

### Community 159 - "Community 159"
Cohesion: 0.60
Nodes (3): _cluster_paginator(), _service_paginator(), TestServiceManagerList

### Community 161 - "Community 161"
Cohesion: 0.40
Nodes (3): Any, Return secret diff summary. Args: other: Secrets to compare against current…, Return cached value or populate and cache it. Args: key: Cache key. populator:…

### Community 162 - "Community 162"
Cohesion: 0.40
Nodes (5): deployfish.core.models.ecs, Elastic Container Service, Classic Load Balancing, deployfish.core.models.elb, ECS service configuration example

### Community 163 - "Community 163"
Cohesion: 0.40
Nodes (5): deployfish.renderers.abstract, deployfish.renderers.misc, deployfish.renderers.table, Renderers, Reference

### Community 164 - "Community 164"
Cohesion: 0.40
Nodes (5): Autoscaling Group Example, autoscalinggroup_name, load_balancer configuration, my-service ECS service, services section

### Community 165 - "Community 165"
Cohesion: 0.40
Nodes (5): Volume Mounts Example, named volume with driver config, services section, host path volume mounts, task-level volumes definition

### Community 166 - "Community 166"
Cohesion: 0.40
Nodes (5): make cov, make test, test CI job, Tests GitHub Actions Workflow, uv package manager

### Community 179 - "Community 179"
Cohesion: 0.50
Nodes (3): setter, Service. Returns: Operation result., Service. Args: value: value.

### Community 180 - "Community 180"
Cohesion: 0.50
Nodes (4): Sphinx, sphinx_rtd_theme, Read the Docs Configuration, docs/source/conf.py Sphinx configuration

### Community 181 - "Community 181"
Cohesion: 0.50
Nodes (4): Abstract, deployfish.core.models.abstract, Application Scaling, deployfish.core.models.appscaling

### Community 182 - "Community 182"
Cohesion: 0.50
Nodes (4): Parameter Store Example, config section for Parameter Store secrets, my-service with secrets config, services section

### Community 188 - "Community 188"
Cohesion: 0.67
Nodes (3): Documentation Contract, napoleon-gate documentation enforcement, Post-Implementation Quality Gate

### Community 189 - "Community 189"
Cohesion: 0.67
Nodes (3): Chris Malek, California Institute of Technology, MIT License

### Community 190 - "Community 190"
Cohesion: 0.67
Nodes (3): BaseSchemaException, Raise this if data in the config source does not validate properly., SchemaException

### Community 195 - "Community 195"
Cohesion: 0.67
Nodes (3): config, config_processors, Config and Config Processors

### Community 196 - "Community 196"
Cohesion: 0.67
Nodes (3): Application configuration, deployfish.main, Main

### Community 197 - "Community 197"
Cohesion: 0.67
Nodes (3): No Load Balancer Example, service without load balancer, services section

## Knowledge Gaps
- **169 isolated node(s):** `deploy-complete.bash script`, `Meta`, `deployfish`, `Tests GitHub Actions Workflow`, `uv package manager` (+164 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **80 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Model` connect `Abstract Model Layer` to `AWS Resource Models`, `Exception Hierarchy`, `Instance Properties`, `Event Scheduling`, `CRUD Operations`, `ECS Cluster Ops`, `ECS Service Layer`, `Community 137`, `Community 138`, `Controller Base`, `Task Definitions`, `Community 15`, `Community 16`, `Community 21`, `Community 22`, `Community 24`, `Community 25`, `Community 26`, `Community 27`, `Community 29`, `Community 34`, `Community 35`, `Community 37`, `Community 171`, `Community 43`, `Community 49`, `Community 50`, `Community 178`, `Community 52`, `Community 55`, `Community 66`, `Community 67`, `Community 70`, `Community 71`, `Community 72`, `Community 75`, `Community 86`, `Community 87`, `Community 91`, `Community 93`, `Community 99`, `Community 100`, `Community 115`, `Community 116`, `Community 125`?**
  _High betweenness centrality (0.158) - this node is a cross-community bridge._
- **Why does `Service` connect `ECS Service Layer` to `AWS Resource Models`, `Abstract Model Layer`, `Exception Hierarchy`, `Instance Properties`, `Event Scheduling`, `Community 131`, `ECS Cluster Ops`, `Community 132`, `CLI Controllers`, `Service Commands`, `Task Definitions`, `Terraform State`, `Community 15`, `Community 141`, `Community 19`, `Community 21`, `Community 22`, `Community 24`, `Community 152`, `Community 29`, `Community 31`, `Community 160`, `Community 32`, `Community 159`, `Community 164`, `Community 47`, `Community 50`, `Community 179`, `Community 56`, `Community 61`, `Community 64`, `Community 197`, `Community 73`, `Community 88`, `Community 89`, `Community 111`, `Community 122`?**
  _High betweenness centrality (0.130) - this node is a cross-community bridge._
- **Why does `SchemaException` connect `Terraform State` to `AWS Resource Models`, `Abstract Model Layer`, `Event Scheduling`, `ECS Service Layer`, `CLI Controllers`, `Task Definitions`, `Community 15`, `Community 22`, `Community 23`, `Community 24`, `Community 28`, `Community 30`, `Community 33`, `Community 42`, `Community 49`, `Community 62`, `Community 190`, `Community 68`, `Community 90`, `Community 104`, `Community 105`, `Community 106`, `Community 107`?**
  _High betweenness centrality (0.104) - this node is a cross-community bridge._
- **Are the 92 inferred relationships involving `Model` (e.g. with `MultipleObjectsReturned` and `ObjectDoesNotExist`) actually correct?**
  _`Model` has 92 INFERRED edges - model-reasoned connections that need verification._
- **Are the 85 inferred relationships involving `Instance` (e.g. with `Manager` and `Model`) actually correct?**
  _`Instance` has 85 INFERRED edges - model-reasoned connections that need verification._
- **Are the 30 inferred relationships involving `Service` (e.g. with `LazyAttributeMixin` and `Manager`) actually correct?**
  _`Service` has 30 INFERRED edges - model-reasoned connections that need verification._
- **Are the 92 inferred relationships involving `Manager` (e.g. with `MultipleObjectsReturned` and `ObjectDoesNotExist`) actually correct?**
  _`Manager` has 92 INFERRED edges - model-reasoned connections that need verification._