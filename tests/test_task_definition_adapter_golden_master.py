"""Golden-master characterization tests for TaskDefinitionAdapter.convert().

These fixtures capture TaskDefinitionAdapter's current output shape for a
range of representative task-definition stanzas. This file must not be
modified while converting TaskDefinitionAdapter to use a Pydantic input model
(docs/adr/0002-pydantic-task-definition-adapter.md) -- if it fails, the
rewrite changed observable output shape.
"""

from copy import deepcopy

import pytest

from deployfish.core.adapters.deployfish.ecs.task_definition import TaskDefinitionAdapter
from deployfish.exceptions import SchemaException


class TestTaskDefinitionAdapterGoldenMaster:
    def test_minimal_ec2_task_definition(self) -> None:
        data = {
            "family": "web",
            "containers": [
                {"name": "web", "image": "nginx:1.25", "cpu": 128, "memory": 256}
            ],
        }
        payload, kwargs = TaskDefinitionAdapter(deepcopy(data)).convert()
        assert payload["family"] == "web"
        assert payload["networkMode"] == "bridge"
        assert payload["volumes"] == []
        assert "requiresCompatibilities" not in payload
        container_data = kwargs["containers"][0][0]
        assert container_data == {
            "name": "web",
            "image": "nginx:1.25",
            "essential": True,
            "cpu": 128,
            "memory": 256,
        }
        assert "cpu" not in payload
        assert "memory" not in payload

    def test_fargate_task_definition_sets_requires_compatibilities(self) -> None:
        data = {
            "family": "web",
            "launch_type": "FARGATE",
            "execution_role": "MY_EXECUTION_ROLE_ARN",
            "containers": [{"name": "web", "image": "nginx:1.25"}],
        }
        payload, _kwargs = TaskDefinitionAdapter(deepcopy(data)).convert()
        assert payload["requiresCompatibilities"] == ["FARGATE"]
        assert payload["executionRoleArn"] == "MY_EXECUTION_ROLE_ARN"
        # No task-level or container-level cpu/memory given: cpu and memory are
        # not included in the payload.
        assert "cpu" not in payload
        assert "memory" not in payload

    def test_fargate_without_execution_role_raises(self) -> None:
        data = {
            "family": "web",
            "launch_type": "FARGATE",
            "containers": [{"name": "web", "image": "nginx:1.25"}],
        }
        adapter = TaskDefinitionAdapter(deepcopy(data))
        with pytest.raises(KeyError):
            adapter.convert()

    def test_missing_containers_raises(self) -> None:
        data = {"family": "web"}
        adapter = TaskDefinitionAdapter(deepcopy(data))
        with pytest.raises(SchemaException, match="at least one container"):
            adapter.convert()

    def test_volumes_host_docker_and_efs(self) -> None:
        data = {
            "family": "web",
            "containers": [
                {"name": "web", "image": "nginx:1.25", "cpu": 128, "memory": 256}
            ],
            "volumes": [
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
            ],
        }
        payload, _kwargs = TaskDefinitionAdapter(deepcopy(data)).convert()
        volumes = {v["name"]: v for v in payload["volumes"]}
        assert volumes["host-vol"]["host"]["sourcePath"] == "/data"
        assert volumes["docker-vol"]["dockerVolumeConfiguration"]["scope"] == "task"
        assert (
            volumes["efs-vol"]["efsVolumeConfiguration"]["fileSystemId"] == "fs-123"
        )
        assert (
            volumes["efs-vol"]["efsVolumeConfiguration"]["rootDirectory"] == "/mnt"
        )

    def test_volume_rejects_multiple_specs(self) -> None:
        data = {
            "family": "web",
            "containers": [
                {"name": "web", "image": "nginx:1.25", "cpu": 128, "memory": 256}
            ],
            "volumes": [{"name": "bad", "path": "/a", "config": {"scope": "task"}}],
        }
        adapter = TaskDefinitionAdapter(deepcopy(data))
        with pytest.raises(SchemaException):
            adapter.convert()

    def test_runtime_platform_and_placement_constraints(self) -> None:
        data = {
            "family": "web",
            "runtime_platform": {
                "cpu_architecture": "ARM64",
                "operating_system_family": "LINUX",
            },
            "placementConstraints": [
                {"type": "memberOf", "expression": "attribute:foo"},
            ],
            "readonly_root_filesystem": True,
            "containers": [
                {"name": "web", "image": "nginx:1.25", "cpu": 128, "memory": 256}
            ],
        }
        payload, kwargs = TaskDefinitionAdapter(deepcopy(data)).convert()
        assert payload["runtimePlatform"]["cpuArchitecture"] == "ARM64"
        assert payload["placementConstraints"][0]["type"] == "memberOf"
        container_data = kwargs["containers"][0][0]
        assert container_data["readonlyRootFilesystem"] is True

    def test_partial_overlay_omits_family_requirement(self) -> None:
        data = {"containers": [{"cpu": "64"}]}
        payload, kwargs = TaskDefinitionAdapter(deepcopy(data), partial=True).convert()
        assert "family" not in payload
        container_data = kwargs["containers"][0][0]
        assert container_data == {"cpu": 64}

    def test_container_cpu_exceeding_task_cpu_raises(self) -> None:
        data = {
            "family": "web",
            "cpu": 256,
            "containers": [
                {"name": "web", "image": "nginx:1.25", "cpu": 512, "memory": 256}
            ],
        }
        adapter = TaskDefinitionAdapter(deepcopy(data))
        with pytest.raises(SchemaException, match="container cpu sums to"):
            adapter.convert()
