"""Additional coverage for deployfish.core.adapters.deployfish.ecs."""

from copy import deepcopy
from unittest.mock import MagicMock, patch

import deployfish.core.adapters  # noqa: F401
import pytest
from deployfish.core.adapters.deployfish.ecs import (
    ContainerDefinitionAdapter,
    ServiceAdapter,
    ServiceHelperTaskAdapter,
    StandaloneTaskAdapter,
    TaskDefinitionAdapter,
)
from deployfish.core.models import Service
from deployfish.core.models.ecs import TaskDefinition
from deployfish.core.models.service_discovery import ServiceDiscoveryService
from deployfish.exceptions import SchemaException

from tests.fixtures import (
    FARGATE_SERVICE_YML,
    SERVICE_YML,
    SERVICE_YML_WITH_HELPER_TASKS,
    STANDALONE_TASK_YML,
)


class TestAbstractTaskAdapterBranches:
    def test_is_fargate_true_when_requires_compatibilities(self) -> None:
        adapter = StandaloneTaskAdapter(
            {**deepcopy(STANDALONE_TASK_YML), "requiresCompatibilities": ["FARGATE"]}
        )
        assert adapter.is_fargate({}) is True

    def test_is_fargate_false_for_ec2_task(self) -> None:
        adapter = StandaloneTaskAdapter(deepcopy(STANDALONE_TASK_YML))
        assert adapter.is_fargate({}) is False

    def test_get_schedule_data_maps_group_and_vpc_configuration(self) -> None:
        adapter = StandaloneTaskAdapter(deepcopy(STANDALONE_TASK_YML))
        yml = deepcopy(STANDALONE_TASK_YML)
        task_definition = TaskDefinition.new(yml, "deployfish")
        schedule_data = adapter.get_schedule_data(
            {
                "schedule": "cron(0 12 * * ? *)",
                "cluster": "foobar-cluster",
                "group": "nightly",
                "launchType": "FARGATE",
                "platformVersion": "1.4.0",
                "networkConfiguration": {
                    "awsvpcConfiguration": {
                        "subnets": ["subnet-a"],
                        "securityGroups": ["sg-a"],
                        "allowPublicIp": "ENABLED",
                    }
                },
            },
            task_definition,
        )
        assert schedule_data["group"] == "nightly"
        assert schedule_data["platform_version"] == "1.4.0"
        assert schedule_data["vpc_configuration"]["subnets"] == ["subnet-a"]
        assert schedule_data["vpc_configuration"]["security_groups"] == ["sg-a"]
        assert schedule_data["vpc_configuration"]["public_ip"] is True

    def test_update_container_logging_standalone_uses_cluster_log_group(self) -> None:
        yml = deepcopy(STANDALONE_TASK_YML)
        yml["launch_type"] = "FARGATE"
        yml["containers"][0]["logging"] = {
            "driver": "fluentd",
            "options": {"fluentd-address": "127.0.0.1:24224"},
        }
        adapter = StandaloneTaskAdapter(yml)
        task_definition = adapter.get_task_definition()
        data = {"name": "foobar-test-mytask", "cluster": "foobar-cluster"}
        with patch(
            "deployfish.core.adapters.deployfish.ecs.common.get_boto3_session",
            return_value=MagicMock(region_name="us-east-1"),
        ):
            adapter.update_container_logging(data, task_definition)
        lc = task_definition.containers[0].data["logConfiguration"]
        assert lc["logDriver"] == "awslogs"
        assert lc["options"]["awslogs-group"] == "/foobar-cluster/standalone-tasks"
        assert lc["options"]["awslogs-stream-prefix"] == "foobar-test-mytask"


class TestTaskDefinitionAdapterComprehensive:
    def test_get_volumes_host_docker_and_efs(self) -> None:
        data = deepcopy(SERVICE_YML)
        data["volumes"] = [
            {"name": "host-vol", "path": "/data"},
            {
                "name": "docker-vol",
                "config": {
                    "scope": "task",
                    "autoprovision": True,
                    "driver": "local",
                },
            },
            {
                "name": "efs-vol",
                "efs_config": {
                    "file_system_id": "fs-123",
                    "root_directory": "/mnt",
                },
            },
        ]
        volumes = TaskDefinitionAdapter(data).get_volumes()
        assert volumes[0]["host"]["sourcePath"] == "/data"
        assert volumes[1]["dockerVolumeConfiguration"]["scope"] == "task"
        assert volumes[2]["efsVolumeConfiguration"]["fileSystemId"] == "fs-123"
        assert volumes[2]["efsVolumeConfiguration"]["rootDirectory"] == "/mnt"

    def test_get_volumes_rejects_multiple_volume_specs(self) -> None:
        data = deepcopy(SERVICE_YML)
        data["volumes"] = [{"name": "bad", "path": "/a", "config": {"scope": "task"}}]
        with pytest.raises(SchemaException):
            TaskDefinitionAdapter(data).get_volumes()

    def test_convert_includes_runtime_platform_and_placement_constraints(self) -> None:
        data = deepcopy(SERVICE_YML)
        data["runtime_platform"] = {
            "cpu_architecture": "ARM64",
            "operating_system_family": "LINUX",
        }
        data["placementConstraints"] = [
            {"type": "memberOf", "expression": "attribute:foo"},
        ]
        data["readonly_root_filesystem"] = True
        payload, _kwargs = TaskDefinitionAdapter(data).convert()
        assert payload["runtimePlatform"]["cpuArchitecture"] == "ARM64"
        assert payload["placementConstraints"][0]["type"] == "memberOf"
        container_data = _kwargs["containers"][0][0]
        assert container_data["readonlyRootFilesystem"] is True

    def test_convert_requires_containers_when_not_partial(self) -> None:
        data = deepcopy(SERVICE_YML)
        del data["containers"]
        with pytest.raises(SchemaException, match="at least one container"):
            TaskDefinitionAdapter(data).convert()


class TestContainerDefinitionAdapterComprehensive:
    def _adapter(
        self,
        container: dict,
        *,
        task_data: dict | None = None,
        **kwargs,
    ) -> ContainerDefinitionAdapter:
        task_data = task_data or {"volumes": [], "requiresCompatibilities": []}
        return ContainerDefinitionAdapter(container, task_data, **kwargs)

    def test_invalid_data_raises_schema_exception_at_construction(self) -> None:
        with pytest.raises(SchemaException, match="not a valid port mapping"):
            self._adapter({"name": "foobar", "image": "img:1", "ports": ["nope"]})

    def test_unknown_field_raises_schema_exception_at_construction(self) -> None:
        with pytest.raises(SchemaException):
            self._adapter({"name": "foobar", "image": "img:1", "bogus_field": "x"})

    def test_partial_construction_allows_missing_name(self) -> None:
        # Should not raise -- partial containers may omit "name".
        self._adapter({"cpu": 64}, partial=True)

    def test_get_mount_points_adds_host_volume(self) -> None:
        container = {
            "name": "foobar",
            "image": "img:1",
            "cpu": 128,
            "memory": 256,
            "volumes": ["/host/data:/container/data:ro"],
        }
        task_data: dict = {"volumes": []}
        mounts = self._adapter(container, task_data=task_data).get_mountPoints()
        assert mounts[0]["containerPath"] == "/container/data"
        assert mounts[0]["readOnly"] is True
        assert task_data["volumes"][0]["host"]["sourcePath"] == "/host/data"

    def test_get_ports_accepts_integer_mapping(self) -> None:
        container = {
            "name": "foobar",
            "image": "img:1",
            "cpu": 128,
            "memory": 256,
            "ports": [9090],
        }
        ports = self._adapter(container).get_ports()
        assert ports == [{"containerPort": 9090, "protocol": "tcp"}]

    def test_get_ports_rejects_invalid_mapping(self) -> None:
        container = {
            "name": "foobar",
            "image": "img:1",
            "cpu": 128,
            "memory": 256,
            "ports": ["not-a-port"],
        }
        with pytest.raises(SchemaException, match="not a valid port mapping"):
            self._adapter(container)

    def test_get_environment_dict_form(self) -> None:
        container = {
            "name": "foobar",
            "image": "img:1",
            "cpu": 128,
            "memory": 256,
            "environment": {"FOO": "bar", "BAZ": "qux"},
        }
        env = self._adapter(container).get_environment()
        assert {"name": "FOO", "value": "bar"} in env
        assert {"name": "BAZ", "value": "qux"} in env

    def test_convert_omits_environment_when_no_environment_stanza(self) -> None:
        # Regression: extra_environment (e.g. DEPLOYFISH_* vars injected by
        # Service/StandaloneTask) must not cause an "environment" key to
        # appear in the converted container definition when the yaml
        # stanza itself had no "environment:" block. The old dict-based
        # code gated both the merge and the output on
        # `"environment" in self.data`, so extra_environment was silently
        # dropped in that case -- this must keep matching that behavior.
        container = {
            "name": "foobar",
            "image": "img:1",
            "cpu": 128,
            "memory": 256,
        }
        data, _kwargs = self._adapter(
            container, extra_environment={"DEPLOYFISH_SERVICE_NAME": "x"}
        ).convert()
        assert "environment" not in data

    def test_convert_partial_with_extra_environment_does_not_raise(self) -> None:
        # Regression: under partial=True, ContainerDefinitionOverlayInput
        # defaults "environment" to None, so get_environment()'s old
        # `dict(self._input.environment)` raised TypeError. Constructing
        # with partial=True and extra_environment set (even though no
        # "environment:" stanza is present) must not crash.
        container = {"name": "foobar", "cpu": 64}
        data, _kwargs = self._adapter(
            container,
            extra_environment={"DEPLOYFISH_SERVICE_NAME": "x"},
            partial=True,
        ).convert()
        assert isinstance(data, dict)

    def test_get_docker_labels_list_form(self) -> None:
        container = {
            "name": "foobar",
            "image": "img:1",
            "cpu": 128,
            "memory": 256,
            "labels": ["com.example.foo=bar"],
        }
        assert self._adapter(container).get_dockerLabels() == {"com.example.foo": "bar"}

    def test_get_ulimits_scalar_and_dict(self) -> None:
        container = {
            "name": "foobar",
            "image": "img:1",
            "cpu": 128,
            "memory": 256,
            "ulimits": {
                "nofile": 1024,
                "nproc": {"soft": 10, "hard": 20},
            },
        }
        ulimits = self._adapter(container).get_ulimits()
        assert {"name": "nofile", "softLimit": 1024, "hardLimit": 1024} in ulimits
        assert {"name": "nproc", "softLimit": 10, "hardLimit": 20} in ulimits

    def test_logging_block_requires_driver(self) -> None:
        container = {
            "name": "foobar",
            "image": "img:1",
            "cpu": 128,
            "memory": 256,
            "logging": {"options": {"tag": "x"}},
        }
        with pytest.raises(
            SchemaException,
            match='logging: block must contain "driver"',
        ):
            self._adapter(container)

    def test_convert_linux_parameters_and_extra_hosts(self) -> None:
        container = {
            "name": "foobar",
            "image": "img:1",
            "cpu": 128,
            "memory": 256,
            "cap_add": ["NET_ADMIN"],
            "cap_drop": ["MKNOD"],
            "tmpfs": [
                {
                    "container_path": "/run",
                    "size": 64,
                    "mount_options": ["noexec"],
                }
            ],
            "extra_hosts": ["somehost:10.0.0.1"],
        }
        data, _kwargs = self._adapter(container).convert()
        assert data["linuxParameters"]["capabilities"]["add"] == ["NET_ADMIN"]
        assert data["linuxParameters"]["tmpfs"][0]["containerPath"] == "/run"
        assert data["extraHosts"] == [{"hostname": "somehost", "ipAddress": "10.0.0.1"}]

    def test_sidecar_container_essential_false(self) -> None:
        container = {
            "name": "sidecar",
            "image": "sidecar:1",
            "cpu": 128,
            "memory": 256,
            "essential": False,
        }
        data, _kwargs = self._adapter(container).convert()
        assert data["essential"] is False

    def test_memory_reservation_must_be_less_than_memory(self) -> None:
        container = {
            "name": "foobar",
            "image": "img:1",
            "cpu": 128,
            "memory": 256,
            "memoryReservation": 300,
        }
        with pytest.raises(SchemaException, match="memoryReservation"):
            self._adapter(container).convert()

    def test_labels_produces_docker_labels_after_pilot_fix(self) -> None:
        # Deliberate behavior fix (docs/adr/0001-pydantic-adapters.md): today
        # labels: produces no dockerLabels output at all, because convert()
        # never called get_dockerLabels(). This adapter now wires it through.
        container = {
            "name": "foobar",
            "image": "img:1",
            "cpu": 128,
            "memory": 256,
            "labels": ["com.example.foo=bar"],
        }
        data, _kwargs = self._adapter(container).convert()
        assert data["dockerLabels"] == {"com.example.foo": "bar"}

    def test_docker_labels_dict_form_round_trips(self) -> None:
        # Regression: dockerLabels: is the real, documented container-labels
        # key (docs/source/yaml.rst). ContainerDefinitionInput.labels once
        # had no alias, so `extra="forbid"` rejected "dockerLabels" outright.
        container = {
            "name": "foobar",
            "image": "img:1",
            "cpu": 128,
            "memory": 256,
            "dockerLabels": {"a": "b"},
        }
        data, _kwargs = self._adapter(container).convert()
        assert data["dockerLabels"] == {"a": "b"}

    def test_partial_memory_reservation_alias_is_preserved(self) -> None:
        # Regression: partial_model() used to rebuild each field with a
        # bare Field(default=None), dropping the original FieldInfo's
        # alias. memory_reservation's "memoryReservation" alias was lost on
        # ContainerDefinitionOverlayInput, so partial=True containers using
        # "memoryReservation" raised SchemaException("Extra inputs are not
        # permitted").
        container = {"name": "foobar", "cpu": 64, "memoryReservation": 256}
        data, _kwargs = self._adapter(container, partial=True).convert()
        assert data["memoryReservation"] == 256

    def test_normalize_labels_bare_key_and_embedded_equals(self) -> None:
        # Regression: _normalize_labels used str.split("=") (raises
        # ValueError on a bare key with no "=", and mis-splits values that
        # themselves contain "="). Fixed to use str.partition("="), matching
        # _normalize_environment's existing behavior.
        container = {
            "name": "foobar",
            "image": "img:1",
            "cpu": 128,
            "memory": 256,
            "dockerLabels": ["edu.caltech.some-flag", "foo=a=b"],
        }
        labels = self._adapter(container).get_dockerLabels()
        assert labels["edu.caltech.some-flag"] == ""
        assert labels["foo"] == "a=b"


class TestStandaloneTaskAdapterComprehensive:
    def test_capacity_provider_strategy_and_placement(self) -> None:
        yml = deepcopy(STANDALONE_TASK_YML)
        yml["capacity_provider_strategy"] = [
            {"capacityProvider": "FARGATE_SPOT", "weight": 1}
        ]
        yml["placement_constraints"] = [{"type": "distinctInstance"}]
        yml["placement_strategy"] = [{"type": "spread", "field": "instanceId"}]
        yml["group"] = "batch"
        data, _kwargs = StandaloneTaskAdapter(yml).convert()
        assert data["capacityProviderStrategy"][0]["capacityProvider"] == "FARGATE_SPOT"
        assert data["placementConstraints"][0]["type"] == "distinctInstance"
        assert data["Group"] == "batch"

    def test_schedule_without_schedule_role_raises(self) -> None:
        yml = deepcopy(STANDALONE_TASK_YML)
        yml["schedule"] = "rate(1 day)"
        with pytest.raises(SchemaException, match="schedule_role"):
            StandaloneTaskAdapter(yml).convert()

    def test_resolves_bare_service_name_via_config(self) -> None:
        yml = deepcopy(STANDALONE_TASK_YML)
        yml["service"] = "foobar-test"
        mock_config = MagicMock()
        mock_config.get_section_item.return_value = {
            "cluster": "foobar-cluster",
            "name": "foobar-test",
        }
        with patch(
            "deployfish.core.adapters.deployfish.ecs.standalone_task.get_config",
            return_value=mock_config,
        ):
            data, _kwargs = StandaloneTaskAdapter(yml).convert()
        assert data["service"] == "foobar-cluster:foobar-test"

    def test_runtime_platform_on_standalone_task(self) -> None:
        yml = deepcopy(STANDALONE_TASK_YML)
        yml["runtime_platform"] = {
            "cpu_architecture": "ARM64",
            "operating_system_family": "LINUX",
        }
        data, _kwargs = StandaloneTaskAdapter(yml).convert()
        assert data["runtimePlatform"]["cpuArchitecture"] == "ARM64"


class TestServiceAdapterComprehensive:
    def test_capacity_provider_strategy_instead_of_launch_type(self) -> None:
        data = deepcopy(SERVICE_YML)
        data["capacity_provider_strategy"] = [
            {"capacityProvider": "FARGATE", "weight": 1, "base": 0}
        ]
        service_data, _kwargs = ServiceAdapter(data).convert()
        cps = service_data["capacityProviderStrategy"][0]
        assert cps["capacityProvider"] == "FARGATE"
        assert "launchType" not in service_data

    def test_service_discovery_on_awsvpc_service(self) -> None:
        data = deepcopy(FARGATE_SERVICE_YML)
        data["service_discovery"] = {
            "namespace": "local",
            "name": "foobar-test",
            "dns_records": [{"type": "A", "ttl": 60}],
        }
        _service_data, kwargs = ServiceAdapter(data).convert()
        assert isinstance(kwargs["service_discovery"], ServiceDiscoveryService)
        assert kwargs["service_discovery"].data["Name"] == "foobar-test"

    def test_service_discovery_requires_awsvpc(self) -> None:
        data = deepcopy(SERVICE_YML)
        data["service_discovery"] = {
            "namespace": "local",
            "name": "foobar-test",
            "dns_records": [{"type": "A", "ttl": 60}],
        }
        with pytest.raises(SchemaException, match='network_mode of "awsvpc"'):
            ServiceAdapter(data).convert()

    def test_daemon_scheduling_and_deployment_limits(self) -> None:
        data = deepcopy(SERVICE_YML)
        data["scheduling_strategy"] = "DAEMON"
        service_data, _kwargs = ServiceAdapter(data).convert()
        assert service_data["schedulingStrategy"] == "DAEMON"
        assert service_data["desiredCount"] == "automatically"
        daemon_max_percent = 100
        assert (
            service_data["deploymentConfiguration"]["maximumPercent"]
            == daemon_max_percent
        )

    def test_health_check_grace_period_and_propagate_tags(self) -> None:
        data = deepcopy(SERVICE_YML)
        health_grace_seconds = 120
        data["healthCheckGracePeriodSeconds"] = health_grace_seconds
        data["propagateTags"] = "SERVICE"
        data["placement_constraints"] = [{"type": "distinctInstance"}]
        data["placement_strategy"] = [{"type": "binpack", "field": "memory"}]
        service_data, _kwargs = ServiceAdapter(data).convert()
        assert service_data["healthCheckGracePeriodSeconds"] == health_grace_seconds
        assert service_data["propagateTags"] == "SERVICE"
        assert service_data["placementConstraints"][0]["type"] == "distinctInstance"

    def test_single_target_group_arn_load_balancer(self) -> None:
        data = deepcopy(SERVICE_YML)
        data["load_balancer"] = {
            "target_group_arn": "MY_SINGLE_TG_ARN",
            "container_name": "foobar",
            "container_port": 443,
        }
        service_data, _kwargs = ServiceAdapter(data).convert()
        assert service_data["loadBalancers"] == [
            {
                "targetGroupArn": "MY_SINGLE_TG_ARN",
                "containerName": "foobar",
                "containerPort": 443,
            }
        ]

    def test_service_role_arn_backwards_compatibility(self) -> None:
        data = deepcopy(SERVICE_YML)
        data["service_role_arn"] = "arn:aws:iam::123:role/legacy"
        service_data, _kwargs = ServiceAdapter(data).convert()
        assert service_data["role"] == "arn:aws:iam::123:role/legacy"

    def test_autoscalinggroup_name_in_kwargs(self) -> None:
        data = deepcopy(SERVICE_YML)
        data["autoscalinggroup_name"] = "my-asg"
        _service_data, kwargs = ServiceAdapter(data).convert()
        assert kwargs["autoscalinggroup_name"] == "my-asg"


class TestServiceHelperTaskAdapterComprehensive:
    def test_capacity_provider_strategy_when_not_fargate(self) -> None:
        service = Service.new(deepcopy(SERVICE_YML), "deployfish")
        tasks_yml = {
            "tasks": [
                {
                    "family": "foobar-tasks-test",
                    "capacity_provider_strategy": [
                        {"capacityProvider": "Infra-ECS-Cluster", "weight": 1}
                    ],
                    "containers": [{"name": "foobar", "cpu": 512, "memory": 512}],
                    "commands": [
                        {
                            "name": "migrate",
                            "containers": [
                                {"name": "foobar", "command": "manage.py migrate"}
                            ],
                        }
                    ],
                }
            ]
        }
        data_list, _kwargs_list = ServiceHelperTaskAdapter(tasks_yml, service).convert()
        assert data_list[0]["capacityProviderStrategy"][0]["capacityProvider"] == (
            "Infra-ECS-Cluster"
        )

    def test_command_without_name_raises(self) -> None:
        service = Service.new(deepcopy(SERVICE_YML), "deployfish")
        tasks_yml = deepcopy(SERVICE_YML_WITH_HELPER_TASKS)
        del tasks_yml["tasks"][0]["commands"][0]["name"]
        with pytest.raises(SchemaException, match='must have a "name"'):
            ServiceHelperTaskAdapter(tasks_yml, service).convert()

    def test_scheduled_command_without_schedule_role_raises(self) -> None:
        service = Service.new(deepcopy(SERVICE_YML), "deployfish")
        tasks_yml = deepcopy(SERVICE_YML_WITH_HELPER_TASKS)
        tasks_yml["tasks"][0]["commands"][0]["schedule"] = "cron(5 * * * ? *)"
        with pytest.raises(SchemaException, match="schedule_role"):
            ServiceHelperTaskAdapter(tasks_yml, service).convert()

    def test_command_level_count_override(self) -> None:
        service = Service.new(deepcopy(SERVICE_YML), "deployfish")
        tasks_yml = deepcopy(SERVICE_YML_WITH_HELPER_TASKS)
        command_count = 5
        tasks_yml["tasks"][0]["commands"][0]["count"] = command_count
        data_list, _kwargs_list = ServiceHelperTaskAdapter(tasks_yml, service).convert()
        assert data_list[0]["count"] == command_count
        assert "count" not in data_list[1]
