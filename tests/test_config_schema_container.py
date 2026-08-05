"""Tests for the ContainerDefinitionInput sub-models."""

import pytest
from deployfish.config.schema.container import (
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
