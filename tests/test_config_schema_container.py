"""Tests for the ContainerDefinitionInput sub-models."""

import pytest
from deployfish.config.schema.container import (
    ContainerDefinitionInput,
    ContainerDefinitionOverlayInput,
    ExtraHost,
    LoggingConfig,
    PortMapping,
    TmpfsMount,
    Ulimit,
)
from pydantic import ValidationError


class TestPortMapping:
    def test_bare_int_becomes_container_port_only(self) -> None:
        pm = PortMapping.parse(9090)
        assert pm.host_port is None
        assert pm.container_port == 9090
        assert pm.protocol == "tcp"

    def test_bare_string_becomes_container_port_only(self) -> None:
        pm = PortMapping.parse("9090")
        assert pm.host_port is None
        assert pm.container_port == 9090

    def test_host_and_container_port(self) -> None:
        pm = PortMapping.parse("8443:443")
        assert pm.host_port == 8443
        assert pm.container_port == 443
        assert pm.protocol == "tcp"

    def test_host_container_and_protocol(self) -> None:
        pm = PortMapping.parse("8125:8125/udp")
        assert pm.host_port == 8125
        assert pm.container_port == 8125
        assert pm.protocol == "udp"

    def test_invalid_mapping_raises(self) -> None:
        with pytest.raises(ValueError, match="not a valid port mapping"):
            PortMapping.parse("not-a-port")


class TestUlimit:
    def test_scalar_sets_soft_and_hard_equal(self) -> None:
        u = Ulimit.model_validate(1024)
        assert u.soft == 1024
        assert u.hard == 1024

    def test_dict_sets_soft_and_hard_independently(self) -> None:
        u = Ulimit.model_validate({"soft": 10, "hard": 20})
        assert u.soft == 10
        assert u.hard == 20


class TestExtraHost:
    def test_parses_hostname_colon_ip(self) -> None:
        h = ExtraHost.parse("somehost:10.0.0.1")
        assert h.hostname == "somehost"
        assert h.ip_address == "10.0.0.1"


class TestLoggingConfig:
    def test_requires_driver(self) -> None:
        with pytest.raises(ValidationError, match='logging: block must contain "driver"'):
            LoggingConfig.model_validate({"options": {"tag": "x"}})

    def test_options_default_to_empty_dict(self) -> None:
        lc = LoggingConfig.model_validate({"driver": "awslogs"})
        assert lc.options == {}


class TestTmpfsMount:
    def test_mount_options_default_to_empty_list(self) -> None:
        tc = TmpfsMount.model_validate({"container_path": "/run", "size": 64})
        assert tc.mount_options == []


class TestContainerDefinitionInput:
    def test_minimal(self) -> None:
        model = ContainerDefinitionInput.model_validate(
            {"name": "web", "image": "nginx:1.25"}
        )
        assert model.name == "web"
        assert model.essential is True
        assert model.ports == []

    def test_essential_false(self) -> None:
        model = ContainerDefinitionInput.model_validate(
            {"name": "web", "image": "nginx:1.25", "essential": False}
        )
        assert model.essential is False

    def test_cpu_and_memory_coerce_strings(self) -> None:
        model = ContainerDefinitionInput.model_validate(
            {"name": "web", "image": "nginx:1.25", "cpu": "128", "memory": "256"}
        )
        assert model.cpu == 128
        assert model.memory == 256

    def test_memory_reservation_alias(self) -> None:
        model = ContainerDefinitionInput.model_validate(
            {"name": "web", "image": "nginx:1.25", "memoryReservation": 300}
        )
        assert model.memory_reservation == 300

    def test_memory_reservation_must_be_integer(self) -> None:
        with pytest.raises(ValidationError):
            ContainerDefinitionInput.model_validate(
                {"name": "web", "image": "nginx:1.25", "memoryReservation": "not-a-number"}
            )

    def test_command_and_entrypoint_shlex_split(self) -> None:
        model = ContainerDefinitionInput.model_validate(
            {
                "name": "web",
                "image": "nginx:1.25",
                "command": "nginx -g daemon off;",
                "entrypoint": "/bin/sh -c",
            }
        )
        assert model.command == ["nginx", "-g", "daemon", "off;"]
        assert model.entrypoint == ["/bin/sh", "-c"]

    def test_ports_list_parsed(self) -> None:
        model = ContainerDefinitionInput.model_validate(
            {"name": "web", "image": "nginx:1.25", "ports": [9090, "8443:443"]}
        )
        assert model.ports[0].container_port == 9090
        assert model.ports[0].host_port is None
        assert model.ports[1].host_port == 8443

    def test_invalid_port_raises(self) -> None:
        with pytest.raises(ValidationError, match="not a valid port mapping"):
            ContainerDefinitionInput.model_validate(
                {"name": "web", "image": "nginx:1.25", "ports": ["not-a-port"]}
            )

    def test_environment_list_form(self) -> None:
        model = ContainerDefinitionInput.model_validate(
            {
                "name": "web",
                "image": "nginx:1.25",
                "environment": ["FOO=bar", "BAZ=qux"],
            }
        )
        assert model.environment == {"FOO": "bar", "BAZ": "qux"}

    def test_environment_dict_form(self) -> None:
        model = ContainerDefinitionInput.model_validate(
            {"name": "web", "image": "nginx:1.25", "environment": {"FOO": "bar"}}
        )
        assert model.environment == {"FOO": "bar"}

    def test_labels_list_form(self) -> None:
        model = ContainerDefinitionInput.model_validate(
            {
                "name": "web",
                "image": "nginx:1.25",
                "labels": ["com.example.foo=bar"],
            }
        )
        assert model.labels == {"com.example.foo": "bar"}

    def test_ulimits_scalar_and_dict(self) -> None:
        model = ContainerDefinitionInput.model_validate(
            {
                "name": "web",
                "image": "nginx:1.25",
                "ulimits": {"nofile": 1024, "nproc": {"soft": 10, "hard": 20}},
            }
        )
        assert model.ulimits["nofile"].soft == 1024
        assert model.ulimits["nofile"].hard == 1024
        assert model.ulimits["nproc"].soft == 10
        assert model.ulimits["nproc"].hard == 20

    def test_extra_hosts_parsed(self) -> None:
        model = ContainerDefinitionInput.model_validate(
            {
                "name": "web",
                "image": "nginx:1.25",
                "extra_hosts": ["somehost:10.0.0.1"],
            }
        )
        assert model.extra_hosts[0].hostname == "somehost"

    def test_logging_requires_driver(self) -> None:
        with pytest.raises(ValidationError, match='logging: block must contain "driver"'):
            ContainerDefinitionInput.model_validate(
                {
                    "name": "web",
                    "image": "nginx:1.25",
                    "logging": {"options": {"tag": "x"}},
                }
            )

    def test_unknown_field_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ContainerDefinitionInput.model_validate(
                {"name": "web", "image": "nginx:1.25", "bogus_field": "x"}
            )

    def test_name_and_image_required(self) -> None:
        with pytest.raises(ValidationError):
            ContainerDefinitionInput.model_validate({"image": "nginx:1.25"})


class TestContainerDefinitionOverlayInput:
    def test_name_and_image_optional(self) -> None:
        model = ContainerDefinitionOverlayInput.model_validate({"cpu": "64"})
        assert model.name is None
        assert model.image is None
        assert model.cpu == 64

    def test_validators_still_run_for_given_fields(self) -> None:
        with pytest.raises(ValidationError, match="not a valid port mapping"):
            ContainerDefinitionOverlayInput.model_validate({"ports": ["not-a-port"]})
