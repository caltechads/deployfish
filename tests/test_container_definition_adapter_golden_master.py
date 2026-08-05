"""Golden-master characterization tests for ContainerDefinitionAdapter.convert().

These fixtures capture ContainerDefinitionAdapter's current output shape for a
range of representative container stanzas. This file must not be modified
while converting ContainerDefinitionAdapter to use a Pydantic input model
(docs/adr/0001-pydantic-adapters.md) -- if it fails, the rewrite changed
observable output shape.
"""

import pytest

from deployfish.core.adapters.deployfish.ecs.container import ContainerDefinitionAdapter
from deployfish.exceptions import SchemaException


class TestContainerDefinitionAdapterGoldenMaster:
    def test_minimal_ec2_container(self) -> None:
        container = {"name": "web", "image": "nginx:1.25", "cpu": 128, "memory": 256}
        task_data = {"volumes": [], "requiresCompatibilities": []}
        data, kwargs = ContainerDefinitionAdapter(container, task_data).convert()
        assert data == {
            "name": "web",
            "image": "nginx:1.25",
            "essential": True,
            "cpu": 128,
            "memory": 256,
        }
        assert kwargs == {"secrets": []}

    def test_minimal_fargate_container_no_memory_gets_no_default(self) -> None:
        container = {"name": "web", "image": "nginx:1.25"}
        task_data = {"volumes": [], "requiresCompatibilities": ["FARGATE"]}
        data, _kwargs = ContainerDefinitionAdapter(container, task_data).convert()
        assert data == {"name": "web", "image": "nginx:1.25", "essential": True}

    def test_container_memory_defaults_to_512_when_task_already_has_memory(self) -> None:
        # get_memory() only returns None-without-raising when the task
        # definition already has its own top-level "memory" key -- a
        # container missing memory with NO task-level memory set raises
        # SchemaException instead (see test_missing_memory_raises_when_no_task_level_memory
        # below). This is the one reachable path to convert()'s "default
        # memory to 512" branch.
        container = {"name": "web", "image": "nginx:1.25", "cpu": 128}
        task_data = {"volumes": [], "requiresCompatibilities": [], "memory": 1024}
        data, _kwargs = ContainerDefinitionAdapter(container, task_data).convert()
        assert data["memory"] == 512

    def test_missing_memory_raises_when_no_task_level_memory(self) -> None:
        container = {"name": "web", "image": "nginx:1.25", "cpu": 128}
        task_data = {"volumes": [], "requiresCompatibilities": []}
        with pytest.raises(SchemaException, match="memory is required for containers"):
            ContainerDefinitionAdapter(container, task_data).convert()

    def test_full_featured_container(self) -> None:
        container = {
            "name": "web",
            "image": "nginx:1.25",
            "cpu": 128,
            "memory": 256,
            "essential": False,
            "ports": [9090, "8443:443", "8125:8125/udp"],
            "command": "nginx -g daemon off;",
            "entrypoint": "/bin/sh -c",
            "links": ["db"],
            "environment": ["FOO=bar", "BAZ=qux"],
            "ulimits": {"nofile": 1024, "nproc": {"soft": 10, "hard": 20}},
            "logging": {"driver": "awslogs", "options": {"tag": "x"}},
            "extra_hosts": ["somehost:10.0.0.1"],
            "cap_add": ["NET_ADMIN"],
            "cap_drop": ["MKNOD"],
            "tmpfs": [
                {"container_path": "/run", "size": 64, "mount_options": ["noexec"]}
            ],
            "volumes": ["/host/data:/container/data:ro"],
        }
        task_data = {"volumes": [], "requiresCompatibilities": []}
        data, _kwargs = ContainerDefinitionAdapter(container, task_data).convert()
        assert data["name"] == "web"
        assert data["essential"] is False
        assert data["portMappings"] == [
            {"containerPort": 9090, "protocol": "tcp"},
            {"hostPort": 8443, "containerPort": 443, "protocol": "tcp"},
            {"hostPort": 8125, "containerPort": 8125, "protocol": "udp"},
        ]
        assert data["command"] == ["nginx", "-g", "daemon", "off;"]
        assert data["entryPoint"] == ["/bin/sh", "-c"]
        assert data["links"] == ["db"]
        assert {"name": "FOO", "value": "bar"} in data["environment"]
        assert {"name": "BAZ", "value": "qux"} in data["environment"]
        # Note: no "labels" key in this fixture, and no dockerLabels assertion
        # here -- today, convert() never wires labels: -> dockerLabels (see
        # test_labels_produces_docker_labels_after_pilot_fix in Task 7, which
        # verifies the deliberate fix documented in the ADR).
        assert {"name": "nofile", "softLimit": 1024, "hardLimit": 1024} in data["ulimits"]
        assert {"name": "nproc", "softLimit": 10, "hardLimit": 20} in data["ulimits"]
        assert data["logConfiguration"] == {
            "logDriver": "awslogs",
            "options": {"tag": "x"},
        }
        assert data["extraHosts"] == [{"hostname": "somehost", "ipAddress": "10.0.0.1"}]
        assert data["linuxParameters"]["capabilities"] == {
            "add": ["NET_ADMIN"],
            "drop": ["MKNOD"],
        }
        assert data["linuxParameters"]["tmpfs"] == [
            {"containerPath": "/run", "size": 64, "mountOptions": ["noexec"]}
        ]
        assert data["mountPoints"][0]["containerPath"] == "/container/data"
        assert data["mountPoints"][0]["readOnly"] is True
        assert task_data["volumes"][0]["host"]["sourcePath"] == "/host/data"

    def test_environment_dict_form_and_extra_environment_merge(self) -> None:
        container = {
            "name": "web",
            "image": "nginx:1.25",
            "cpu": 128,
            "memory": 256,
            "environment": {"FOO": "bar"},
        }
        task_data = {"volumes": [], "requiresCompatibilities": []}
        data, _kwargs = ContainerDefinitionAdapter(
            container, task_data, extra_environment={"BAZ": "qux"}
        ).convert()
        assert {"name": "FOO", "value": "bar"} in data["environment"]
        assert {"name": "BAZ", "value": "qux"} in data["environment"]

    def test_partial_overlay_omits_name_and_essential_defaults(self) -> None:
        # Under partial=True, Adapter.set()'s `default=` branch is never taken
        # for an absent key -- `essential`/`name`/`image` are omitted from the
        # output entirely, not defaulted, when absent from the overlay.
        container = {"cpu": "64"}
        data, kwargs = ContainerDefinitionAdapter(
            container, {"volumes": [], "requiresCompatibilities": []}, partial=True
        ).convert()
        assert data == {"cpu": 64}
        assert kwargs == {"secrets": []}

    def test_readonly_root_filesystem_passthrough(self) -> None:
        container = {"name": "web", "image": "nginx:1.25", "cpu": 128, "memory": 256}
        task_data = {"volumes": [], "requiresCompatibilities": []}
        data, _kwargs = ContainerDefinitionAdapter(
            container, task_data, readonly_root_filesystem=True
        ).convert()
        assert data["readonlyRootFilesystem"] is True
