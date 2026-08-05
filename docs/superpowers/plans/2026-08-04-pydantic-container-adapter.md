# Pydantic ContainerDefinitionAdapter Pilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `ContainerDefinitionAdapter`'s hand-rolled `Adapter.set()` dict-mutation with a
Pydantic-validated input model (`ContainerDefinitionInput`), as the pilot for ADR
`docs/adr/0001-pydantic-adapters.md`, with zero change to `.convert()`'s output contract.

**Architecture:** A new `deployfish/config/schema/` package holds Pydantic models that validate and
reshape the *input* (the `deployfish.yml` container stanza) only. `ContainerDefinitionAdapter`
validates eagerly at construction, translates `pydantic.ValidationError` into the existing
`SchemaException`, and its `get_*()` builder methods read from the validated model instead of raw
`self.data` to assemble the same boto3-shaped output dict as today. A `partial_model()` helper derives
an all-optional variant of `ContainerDefinitionInput` for `partial=True` (overlay) construction.

**Tech Stack:** Python 3.13, pydantic 2.13.4, pytest, ruff, mypy (strict per `deployfish` conventions).

## Global Constraints

- Use `.venv/bin/python`, `.venv/bin/pytest`, `.venv/bin/ruff`, `.venv/bin/mypy` (per `CLAUDE.md`).
- Use `uv add <package>` / `uv add --group=test <package>` for any new dependency (none expected —
  pydantic is already added).
- Every non-test Python file: class docstrings describe the contract with constructor `Args:`;
  function docstrings get only-applicable sections (`Args:`, `Keyword Args:`, `Raises:`, `Returns:`);
  Napoleon `#:` comments on class attributes and `__init__` instance attributes. Enforced by
  `make napoleon-gate` — no new violations.
- After every task's code changes: `ruff check` and `.venv/bin/mypy` on touched files, fix all
  reported problems (pre-existing failures in unrelated files may be noted separately, not fixed).
- `Model.__init__(data)` and every other consumer outside `deployfish/core/adapters/deployfish/ecs/`
  and `deployfish/config/schema/` must see **zero** behavior change — `.convert()` still returns
  `(data, kwargs)` with `data` shaped exactly as before.
- `graphify update .` after code changes land (per project convention).

---

## File Structure

- **Create:** `deployfish/config/schema/__init__.py` — empty package marker.
- **Create:** `deployfish/config/schema/_partial.py` — the `partial_model()` helper (shared by future
  adapters, not just this pilot).
- **Create:** `deployfish/config/schema/container.py` — `PortMapping`, `Ulimit`, `ExtraHost`,
  `LoggingConfig`, `TmpfsMount`, `ContainerDefinitionInput`, `ContainerDefinitionOverlayInput`.
- **Create:** `tests/test_config_schema_partial.py` — tests for `partial_model()`.
- **Create:** `tests/test_config_schema_container.py` — tests for the container input models.
- **Create:** `tests/test_container_definition_adapter_golden_master.py` — characterization test
  capturing today's `.convert()` output, run first against unmodified code.
- **Modify:** `deployfish/core/adapters/deployfish/ecs/container.py` — `ContainerDefinitionAdapter`
  validates eagerly, `get_*()` methods read from the validated model.
- **Modify:** `tests/test_ecs_adapters_comprehensive.py` — the ~6 direct-`get_*()`-call tests that
  currently expect exceptions from a specific accessor now expect them at construction (per the ADR's
  eager-validation decision).

---

### Task 1: Golden-master characterization test for `ContainerDefinitionAdapter.convert()`

**Files:**
- Create: `tests/test_container_definition_adapter_golden_master.py`
- Test: itself (this is the test)

**Interfaces:**
- Consumes: `deployfish.core.adapters.deployfish.ecs.container.ContainerDefinitionAdapter` (existing,
  unmodified at this point in the plan).

This test runs against **today's unmodified code** and must keep passing, unchanged, through every
later task. It exists to catch any drift in `.convert()`'s output shape once the rewrite lands.

- [ ] **Step 1: Write the characterization test**

```python
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
```

- [ ] **Step 2: Run it to verify it PASSES against today's unmodified code**

Run: `.venv/bin/pytest tests/test_container_definition_adapter_golden_master.py -v`
Expected: all 8 tests PASS (this is characterization of existing behavior, not new behavior — verified
empirically against the current, unmodified codebase during plan review).

- [ ] **Step 3: Commit**

```bash
git add tests/test_container_definition_adapter_golden_master.py
git commit -m "test: add golden-master characterization tests for ContainerDefinitionAdapter"
```

---

### Task 2: `partial_model()` helper

**Files:**
- Create: `deployfish/config/schema/__init__.py`
- Create: `deployfish/config/schema/_partial.py`
- Test: `tests/test_config_schema_partial.py`

**Interfaces:**
- Produces: `deployfish.config.schema._partial.partial_model(model: type[BaseModel], name: str | None = None) -> type[BaseModel]` — later tasks call this to derive `ContainerDefinitionOverlayInput`.

- [ ] **Step 1: Write the failing test**

```python
"""Tests for deployfish.config.schema._partial.partial_model."""

import pytest
from pydantic import BaseModel, ValidationError, field_validator

from deployfish.config.schema._partial import partial_model


class _Widget(BaseModel):
    name: str
    count: int = 1

    @field_validator("count")
    @classmethod
    def _count_must_be_positive(cls, value: int) -> int:
        if value < 1:
            msg = "count must be positive"
            raise ValueError(msg)
        return value


class TestPartialModel:
    def test_all_fields_become_optional(self) -> None:
        Partial = partial_model(_Widget)
        instance = Partial()
        assert instance.name is None
        assert instance.count is None

    def test_default_name_is_Partial_prefixed(self) -> None:
        Partial = partial_model(_Widget)
        assert Partial.__name__ == "PartialWidget"

    def test_custom_name(self) -> None:
        Partial = partial_model(_Widget, name="WidgetOverlay")
        assert Partial.__name__ == "WidgetOverlay"

    def test_inherited_validators_still_run_when_value_given(self) -> None:
        Partial = partial_model(_Widget)
        with pytest.raises(ValidationError, match="count must be positive"):
            Partial(count=0)

    def test_inherited_validators_skipped_when_value_omitted(self) -> None:
        Partial = partial_model(_Widget)
        instance = Partial(name="thing")
        assert instance.name == "thing"
        assert instance.count is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_config_schema_partial.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'deployfish.config.schema'`

- [ ] **Step 3: Write the implementation**

```python
# deployfish/config/schema/__init__.py
```

(empty file — package marker)

```python
# deployfish/config/schema/_partial.py
"""
Helper for deriving "partial update" Pydantic models, used for the ``partial``
(overlay) construction mode our adapters support.
"""

from typing import Any

from pydantic import BaseModel, create_model


def partial_model(model: type[BaseModel], name: str | None = None) -> type[BaseModel]:
    """
    Build a subclass of ``model`` where every field is optional and defaults to
    ``None``.

    Field validators defined on ``model`` are inherited unchanged, because the
    result is a real subclass of ``model``: a validator still runs -- and can
    still raise -- whenever a field is actually given a value, but no longer
    runs (and no error is raised) when the field is omitted.

    Args:
        model: the strict model to derive the partial variant from.

    Keyword Args:
        name: the name to give the new model class. Defaults to
            ``f"Partial{model.__name__}"``.

    Returns:
        A new model class, subclassing ``model``, with every field optional.

    """
    field_overrides: dict[str, Any] = {
        field_name: (field_info.annotation | None, None)
        for field_name, field_info in model.model_fields.items()
    }
    return create_model(
        name or f"Partial{model.__name__}",
        __base__=model,
        **field_overrides,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_config_schema_partial.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Ruff and mypy**

Run: `.venv/bin/ruff check deployfish/config/schema/ tests/test_config_schema_partial.py`
Run: `.venv/bin/mypy deployfish/config/schema/`
Expected: clean. Fix anything reported.

- [ ] **Step 6: Commit**

```bash
git add deployfish/config/schema/__init__.py deployfish/config/schema/_partial.py tests/test_config_schema_partial.py
git commit -m "feat: add partial_model() helper for deriving overlay Pydantic models"
```

---

### Task 3: Container sub-models (`PortMapping`, `Ulimit`, `ExtraHost`, `LoggingConfig`, `TmpfsMount`)

**Files:**
- Create: `deployfish/config/schema/container.py` (this task adds the sub-models only; `ContainerDefinitionInput` itself is Task 4)
- Test: `tests/test_config_schema_container.py`

**Interfaces:**
- Produces: `PortMapping(host_port: int | None, container_port: int, protocol: str)`,
  `Ulimit(soft: int, hard: int)`, `ExtraHost(hostname: str, ip_address: str)`,
  `LoggingConfig(driver: str, options: dict[str, str])`,
  `TmpfsMount(container_path: str, size: int, mount_options: list[str])`.
  `PortMapping` exposes a classmethod `PortMapping.parse(raw: int | str) -> "PortMapping"` that
  replicates today's `ContainerDefinitionAdapter.PORTS_RE` parsing exactly, including the quirk where
  a single bare port number becomes `container_port` with `host_port=None` (not the other way round).

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for the ContainerDefinitionInput sub-models."""

import pytest
from pydantic import ValidationError

from deployfish.config.schema.container import (
    ExtraHost,
    LoggingConfig,
    PortMapping,
    TmpfsMount,
    Ulimit,
)


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_config_schema_container.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'deployfish.config.schema.container'`

- [ ] **Step 3: Write the implementation**

```python
"""
Pydantic models describing the shape of a ``deployfish.yml`` container
definition stanza. These validate and reshape input only -- the boto3-shaped
output dict is still assembled by hand in
:py:class:`deployfish.core.adapters.deployfish.ecs.container.ContainerDefinitionAdapter`.
"""

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

#: Matches ``"hostPort[:containerPort[/protocol]]"`` port mapping strings.
_PORTS_RE = re.compile(
    r"(?P<hostPort>\d+)(:(?P<containerPort>\d+)(/(?P<protocol>udp|tcp))?)?"
)
#: Matches characters not allowed in an auto-generated volume name.
_MOUNT_RE = re.compile("[^A-Za-z0-9_-]")


class PortMapping(BaseModel):
    """
    A single container port mapping.

    Args:
        host_port: the host port, if any.
        container_port: the container port.
        protocol: ``"tcp"`` or ``"udp"``.

    """

    model_config = ConfigDict(extra="forbid")

    #: The host port, if this mapping specifies one.
    host_port: int | None = None
    #: The container port.
    container_port: int
    #: The protocol -- ``"tcp"`` or ``"udp"``.
    protocol: str = "tcp"

    @classmethod
    def parse(cls, raw: int | str) -> "PortMapping":
        """
        Parse a ``deployfish.yml`` ports entry, which may be a bare port
        number or a ``"hostPort[:containerPort[/protocol]]"`` string.

        Args:
            raw: the raw ports list entry.

        Raises:
            ValueError: if ``raw`` is not a valid port mapping.

        Returns:
            The parsed ``PortMapping``.

        """
        text = str(raw)
        match = _PORTS_RE.search(text)
        if not match:
            msg = f"{raw} is not a valid port mapping"
            raise ValueError(msg)
        if not match.group("containerPort"):
            # A bare port number is the container port, not the host port.
            return cls(container_port=int(match.group("hostPort")))
        protocol = match.group("protocol") or "tcp"
        return cls(
            host_port=int(match.group("hostPort")),
            container_port=int(match.group("containerPort")),
            protocol=protocol,
        )


class Ulimit(BaseModel):
    """
    A single container ulimit.

    Args:
        soft: the soft limit.
        hard: the hard limit.

    """

    model_config = ConfigDict(extra="forbid")

    #: The soft limit.
    soft: int
    #: The hard limit.
    hard: int

    @model_validator(mode="before")
    @classmethod
    def _normalize_scalar_or_dict(cls, data: Any) -> Any:
        """
        Accept either a bare scalar (``soft == hard``) or a
        ``{"soft": ..., "hard": ...}`` dict.

        Args:
            data: the raw ulimit value.

        Returns:
            A dict with ``soft`` and ``hard`` keys.

        """
        if isinstance(data, dict):
            return data
        return {"soft": data, "hard": data}


class ExtraHost(BaseModel):
    """
    A single ``/etc/hosts`` entry to add to the container.

    Args:
        hostname: the hostname.
        ip_address: the IP address.

    """

    model_config = ConfigDict(extra="forbid")

    #: The hostname.
    hostname: str
    #: The IP address.
    ip_address: str

    @classmethod
    def parse(cls, raw: str) -> "ExtraHost":
        """
        Parse a ``"hostname:ip_address"`` extra_hosts entry.

        Args:
            raw: the raw extra_hosts list entry.

        Returns:
            The parsed ``ExtraHost``.

        """
        hostname, ip_address = raw.split(":")
        return cls(hostname=hostname, ip_address=ip_address)


class LoggingConfig(BaseModel):
    """
    A container's logging configuration.

    Args:
        driver: the log driver.
        options: log driver options.

    """

    model_config = ConfigDict(extra="forbid")

    #: The log driver.
    driver: str = Field(...)
    #: Log driver options.
    options: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _require_driver(cls, data: Any) -> Any:
        """
        Raise a clear, specific error when ``driver`` is missing, instead of
        Pydantic's generic "field required" message.

        Args:
            data: the raw logging block.

        Raises:
            ValueError: if ``driver`` is missing.

        Returns:
            ``data`` unchanged.

        """
        if isinstance(data, dict) and "driver" not in data:
            msg = 'logging: block must contain "driver"'
            raise ValueError(msg)
        return data


class TmpfsMount(BaseModel):
    """
    A single tmpfs mount for a container.

    Args:
        container_path: the container path to mount.
        size: the size, in MiB.
        mount_options: mount options.

    """

    model_config = ConfigDict(extra="forbid")

    #: The container path to mount.
    container_path: str
    #: The size, in MiB.
    size: int
    #: Mount options.
    mount_options: list[str] = Field(default_factory=list)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_config_schema_container.py -v`
Expected: PASS (9 tests)

- [ ] **Step 5: Ruff and mypy**

Run: `.venv/bin/ruff check deployfish/config/schema/container.py tests/test_config_schema_container.py`
Run: `.venv/bin/mypy deployfish/config/schema/container.py`
Expected: clean.

- [ ] **Step 6: Commit**

```bash
git add deployfish/config/schema/container.py tests/test_config_schema_container.py
git commit -m "feat: add container sub-models (PortMapping, Ulimit, ExtraHost, LoggingConfig, TmpfsMount)"
```

---

### Task 4: `ContainerDefinitionInput`

**Files:**
- Modify: `deployfish/config/schema/container.py` (add `ContainerDefinitionInput` below the sub-models from Task 3)
- Test: `tests/test_config_schema_container.py` (add a new test class)

**Interfaces:**
- Consumes: `PortMapping.parse`, `Ulimit`, `ExtraHost.parse`, `LoggingConfig`, `TmpfsMount` (Task 3).
- Produces: `ContainerDefinitionInput` with fields `name: str`, `image: str`, `essential: bool`,
  `cpu: int | None`, `memory: int | None`, `memory_reservation: int | None` (alias
  `"memoryReservation"`), `command: list[str] | None`, `entrypoint: list[str] | None`,
  `links: list[str]`, `ports: list[PortMapping]`, `environment: dict[str, str]`,
  `labels: dict[str, str]`, `ulimits: dict[str, Ulimit]`, `logging: LoggingConfig | None`,
  `extra_hosts: list[ExtraHost]`, `cap_add: list[str]`, `cap_drop: list[str]`,
  `tmpfs: list[TmpfsMount]`, `volumes: list[str]`. `model_config` uses `populate_by_name=True,
  extra="forbid"`.

- [ ] **Step 1: Write the failing tests**

```python
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
```

Add `ContainerDefinitionInput` and these imports to the top of
`tests/test_config_schema_container.py`:

```python
from deployfish.config.schema.container import ContainerDefinitionInput
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_config_schema_container.py -v`
Expected: FAIL with `ImportError: cannot import name 'ContainerDefinitionInput'`

- [ ] **Step 3: Write the implementation**

Append the class body below to `deployfish/config/schema/container.py`. Merge the imports shown here
into the file's existing top-of-file import block from Task 3 (`import re`, `from typing import Any`,
`from pydantic import BaseModel, ConfigDict, Field, model_validator`) rather than adding a second
import block — the result should be one `import shlex`, one `from typing import Annotated, Any`, and
one `from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator` at the top:

```python
import shlex
from typing import Annotated, Any

from pydantic import BeforeValidator


def _split_command(value: Any) -> Any:
    """Split a shell command string into argv, if given as a string."""
    if isinstance(value, str):
        return shlex.split(value)
    return value


def _parse_ports(value: Any) -> Any:
    """Parse each raw ports entry into a PortMapping-constructible dict."""
    if not isinstance(value, list):
        return value
    return [PortMapping.parse(v) if not isinstance(v, PortMapping) else v for v in value]


def _normalize_environment(value: Any) -> Any:
    """Normalize deployfish.yml's list-of-"K=V"-or-dict environment shape."""
    if isinstance(value, list):
        result: dict[str, str] = {}
        for entry in value:
            key, _, val = entry.partition("=")
            result[key] = val
        return result
    return value


def _normalize_labels(value: Any) -> Any:
    """Normalize deployfish.yml's list-of-"K=V"-or-dict labels shape."""
    if isinstance(value, list):
        result: dict[str, str] = {}
        for entry in value:
            key, val = entry.split("=")
            result[key] = val
        return result
    return value


def _parse_extra_hosts(value: Any) -> Any:
    """Parse each raw extra_hosts entry into an ExtraHost-constructible value."""
    if not isinstance(value, list):
        return value
    return [ExtraHost.parse(v) if isinstance(v, str) else v for v in value]


class ContainerDefinitionInput(BaseModel):
    """
    Validates and reshapes a single ``deployfish.yml`` container definition
    stanza. Does not produce the boto3-shaped output dict -- see
    :py:class:`deployfish.core.adapters.deployfish.ecs.container.ContainerDefinitionAdapter`
    for that.

    Args:
        name: the container name.
        image: the container image.

    """

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    #: The container name.
    name: str
    #: The container image.
    image: str
    #: Whether this container is essential to the task.
    essential: bool = True
    #: CPU units to reserve, if specified at the container level.
    cpu: int | None = None
    #: Memory (MiB) to allow, if specified at the container level.
    memory: int | None = None
    #: Soft memory reservation (MiB), if specified.
    memory_reservation: int | None = Field(default=None, alias="memoryReservation")
    #: The container's entrypoint command, if overridden.
    command: Annotated[list[str] | None, BeforeValidator(_split_command)] = None
    #: The container's entrypoint, if overridden.
    entrypoint: Annotated[list[str] | None, BeforeValidator(_split_command)] = None
    #: Legacy container links.
    links: list[str] = Field(default_factory=list)
    #: Port mappings for this container.
    ports: Annotated[list[PortMapping], BeforeValidator(_parse_ports)] = Field(
        default_factory=list
    )
    #: Environment variables for this container.
    environment: Annotated[dict[str, str], BeforeValidator(_normalize_environment)] = (
        Field(default_factory=dict)
    )
    #: Docker labels for this container.
    labels: Annotated[dict[str, str], BeforeValidator(_normalize_labels)] = Field(
        default_factory=dict
    )
    #: Ulimits for this container, keyed by ulimit name.
    ulimits: dict[str, Ulimit] = Field(default_factory=dict)
    #: Logging configuration for this container, if overridden.
    logging: LoggingConfig | None = None
    #: Extra /etc/hosts entries for this container.
    extra_hosts: Annotated[list[ExtraHost], BeforeValidator(_parse_extra_hosts)] = Field(
        default_factory=list
    )
    #: Linux capabilities to add.
    cap_add: list[str] = Field(default_factory=list)
    #: Linux capabilities to drop.
    cap_drop: list[str] = Field(default_factory=list)
    #: tmpfs mounts for this container.
    tmpfs: list[TmpfsMount] = Field(default_factory=list)
    #: Volume mount specs, in "host:container[:ro]" or "volumeName:container" form.
    volumes: list[str] = Field(default_factory=list)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_config_schema_container.py -v`
Expected: PASS (all tests in the file, Task 3 + Task 4 combined)

- [ ] **Step 5: Ruff and mypy**

Run: `.venv/bin/ruff check deployfish/config/schema/container.py tests/test_config_schema_container.py`
Run: `.venv/bin/mypy deployfish/config/schema/container.py`
Expected: clean.

- [ ] **Step 6: Napoleon gate**

Run: `make napoleon-gate`
Expected: no new violations.

- [ ] **Step 7: Commit**

```bash
git add deployfish/config/schema/container.py tests/test_config_schema_container.py
git commit -m "feat: add ContainerDefinitionInput Pydantic model"
```

---

### Task 5: `ContainerDefinitionOverlayInput`

**Files:**
- Modify: `deployfish/config/schema/container.py`
- Test: `tests/test_config_schema_container.py`

**Interfaces:**
- Consumes: `partial_model()` (Task 2), `ContainerDefinitionInput` (Task 4).
- Produces: `ContainerDefinitionOverlayInput = partial_model(ContainerDefinitionInput,
  name="ContainerDefinitionOverlayInput")`.

- [ ] **Step 1: Write the failing test**

```python
class TestContainerDefinitionOverlayInput:
    def test_name_and_image_optional(self) -> None:
        model = ContainerDefinitionOverlayInput.model_validate({"cpu": "64"})
        assert model.name is None
        assert model.image is None
        assert model.cpu == 64

    def test_validators_still_run_for_given_fields(self) -> None:
        with pytest.raises(ValidationError, match="not a valid port mapping"):
            ContainerDefinitionOverlayInput.model_validate({"ports": ["not-a-port"]})
```

Add to the import line at the top of the test file:

```python
from deployfish.config.schema.container import (
    ContainerDefinitionInput,
    ContainerDefinitionOverlayInput,
    ExtraHost,
    LoggingConfig,
    PortMapping,
    TmpfsMount,
    Ulimit,
)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_config_schema_container.py -v`
Expected: FAIL with `ImportError: cannot import name 'ContainerDefinitionOverlayInput'`

- [ ] **Step 3: Write the implementation**

Add `from deployfish.config.schema._partial import partial_model` to the top-of-file import block in
`deployfish/config/schema/container.py` (alongside the imports from Tasks 3-4), then append the
assignment below at the end of the file:

```python
#: All-optional variant of ContainerDefinitionInput, for partial/overlay
#: construction (e.g. ServiceHelperTask command-specific container overrides).
ContainerDefinitionOverlayInput = partial_model(
    ContainerDefinitionInput, name="ContainerDefinitionOverlayInput"
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_config_schema_container.py -v`
Expected: PASS

- [ ] **Step 5: Ruff and mypy**

Run: `.venv/bin/ruff check deployfish/config/schema/container.py tests/test_config_schema_container.py`
Run: `.venv/bin/mypy deployfish/config/schema/container.py`
Expected: clean.

- [ ] **Step 6: Commit**

```bash
git add deployfish/config/schema/container.py tests/test_config_schema_container.py
git commit -m "feat: derive ContainerDefinitionOverlayInput from ContainerDefinitionInput"
```

---

### Task 6: Wire eager validation into `ContainerDefinitionAdapter.__init__`

**Files:**
- Modify: `deployfish/core/adapters/deployfish/ecs/container.py:59-90` (`__init__`)
- Test: `tests/test_ecs_adapters_comprehensive.py` (add new tests; existing tests updated in Task 8)

**Interfaces:**
- Consumes: `ContainerDefinitionInput`, `ContainerDefinitionOverlayInput` (Tasks 4-5).
- Produces: `self._input: ContainerDefinitionInput` (or the overlay variant when `partial=True`),
  available to every method in Tasks 7+.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_ecs_adapters_comprehensive.py`, inside `TestContainerDefinitionAdapterComprehensive`:

```python
    def test_invalid_data_raises_schema_exception_at_construction(self) -> None:
        with pytest.raises(SchemaException, match="not a valid port mapping"):
            self._adapter({"name": "foobar", "image": "img:1", "ports": ["nope"]})

    def test_unknown_field_raises_schema_exception_at_construction(self) -> None:
        with pytest.raises(SchemaException):
            self._adapter({"name": "foobar", "image": "img:1", "bogus_field": "x"})

    def test_partial_construction_allows_missing_name(self) -> None:
        # Should not raise -- partial containers may omit "name".
        self._adapter({"cpu": 64}, partial=True)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_ecs_adapters_comprehensive.py::TestContainerDefinitionAdapterComprehensive -v`
Expected: FAIL — construction currently never raises for these inputs (old code only raises when the
relevant `get_*()`/`convert()` method is later called).

- [ ] **Step 3: Modify `ContainerDefinitionAdapter.__init__`**

In `deployfish/core/adapters/deployfish/ecs/container.py`, replace the `__init__` method body (keep
the signature) with:

```python
    def __init__(  # noqa: PLR0913
        self,
        data: dict[str, Any],
        task_definition_data: dict[str, Any] | None = None,
        secrets: list[Secret] | None = None,
        extra_environment: dict[str, Any] | None = None,
        partial: bool = False,  # noqa: FBT001, FBT002
        readonly_root_filesystem: bool | None = None,  # noqa: FBT001
    ) -> None:
        """
        Initialize ContainerDefinitionAdapter.

        Args:
            data: data.
            task_definition_data: task definition data.
            secrets: secrets.
            extra_environment: extra environment.
            partial: partial.
            readonly_root_filesystem: readonly root filesystem.

        Raises:
            SchemaException: if ``data`` does not validate against
                :py:class:`deployfish.config.schema.container.ContainerDefinitionInput`.

        """
        super().__init__(data)
        #: Task definition data.
        self.task_definition_data = task_definition_data or {}
        #: Secrets.
        self.secrets = secrets or []
        #: Extra environment.
        self.extra_environment = extra_environment or {}
        #: Partial.
        self.partial = partial
        #: Readonly root filesystem.
        self.readonly_root_filesystem = readonly_root_filesystem
        #: The validated, reshaped container stanza.
        self._input = self._validate(data)

    def _validate(
        self, data: dict[str, Any]
    ) -> ContainerDefinitionInput | ContainerDefinitionOverlayInput:
        """
        Validate ``data`` against the appropriate input model, translating
        :py:exc:`pydantic.ValidationError` into :py:exc:`self.SchemaException`.

        Args:
            data: the raw container stanza.

        Raises:
            SchemaException: if ``data`` does not validate.

        Returns:
            The validated, reshaped container stanza.

        """
        model = ContainerDefinitionOverlayInput if self.partial else ContainerDefinitionInput
        try:
            return model.model_validate(data)
        except ValidationError as e:
            errors = "; ".join(
                f'{".".join(str(p) for p in err["loc"])}: {err["msg"]}' for err in e.errors()
            )
            msg = f"container definition is invalid: {errors}"
            raise self.SchemaException(msg) from e
```

Add these imports to the top of `deployfish/core/adapters/deployfish/ecs/container.py`:

```python
from pydantic import ValidationError

from deployfish.config.schema.container import (
    ContainerDefinitionInput,
    ContainerDefinitionOverlayInput,
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_ecs_adapters_comprehensive.py::TestContainerDefinitionAdapterComprehensive -v`
Expected: the 3 new tests PASS. Other tests in this class will now FAIL (they still reference
`self.data` in ways the next task fixes) -- that's expected at this checkpoint; Task 7 fixes them.

- [ ] **Step 5: Commit**

```bash
git add deployfish/core/adapters/deployfish/ecs/container.py tests/test_ecs_adapters_comprehensive.py
git commit -m "feat: validate container stanza eagerly via ContainerDefinitionInput"
```

---

### Task 7: Rewrite `get_*()` methods and `convert()` to use `self._input`

**Files:**
- Modify: `deployfish/core/adapters/deployfish/ecs/container.py` (`get_cpu`, `get_memory`,
  `get_ports`, `get_environment`, `get_dockerLabels`, `get_ulimits`, `get_logConfiguration`,
  `get_linuxParameters`, `get_extraHosts`, `get_mountPoints`, `convert`)

**Interfaces:**
- Consumes: `self._input` (Task 6).
- Produces: identical `.convert()` output contract — verified by the Task 1 golden-master test and
  the existing test suite (as updated in Task 8).

- [ ] **Step 1: Run the current full test file to see the failures from Task 6's checkpoint**

Run: `.venv/bin/pytest tests/test_ecs_adapters_comprehensive.py tests/test_container_definition_adapter_golden_master.py -v`
Expected: several FAILs (methods still read `self.data` directly for fields now removed from that
flow, or the golden-master partial/full-featured tests fail because `self.set()` calls conflict with
strict validation of unknown/renamed keys). Confirm the failures are all in the methods this task
rewrites.

- [ ] **Step 2: Replace `get_cpu()`, `get_memory()`, `get_ports()`, `get_environment()`,
  `get_dockerLabels()`, `get_ulimits()`, `get_logConfiguration()`, `get_linuxParameters()`,
  `get_extraHosts()`, `get_mountPoints()`, and `convert()`**

Replace each method body as follows (keep existing signatures and docstrings, updating `Returns:`/
`Raises:` text only if the behavior text changed):

```python
    def get_cpu(self) -> int | None:
        default = None if self.is_fargate or self.partial else 256
        cpu = self._input.cpu if self._input.cpu is not None else default
        if "cpu" in self.task_definition_data:
            task_cpu = self.task_definition_data["cpu"]
            if isinstance(task_cpu, str):
                task_cpu = int(task_cpu)
            if cpu is not None and cpu > task_cpu:
                msg = 'container "{}": cpu is greater than the task cpu value'.format(
                    self._input.name
                )
                raise self.SchemaException(msg)
        return cpu

    def get_memory(self) -> int | None:
        if self.is_fargate:
            if self._input.memory is None:
                return None
        if self._input.memory is None:
            if "memory" in self.task_definition_data:
                return None
            if not self.partial:
                msg = 'container "{}": memory is required for containers if not specified at the task level'.format(  # noqa: E501
                    self._input.name
                )
                raise self.SchemaException(msg)
            return None
        memory = self._input.memory
        if "memory" in self.task_definition_data:
            task_memory = self.task_definition_data["memory"]
            if isinstance(task_memory, str):
                task_memory = int(task_memory)
            if memory > task_memory:
                msg = 'container "{}": memory is greater than task memory'.format(
                    self._input.name
                )
                raise self.SchemaException(msg)
        return memory

    def get_ports(self) -> list[dict[str, Any]]:
        port_mappings = []
        for p in self._input.ports:
            mapping: dict[str, Any] = {"containerPort": p.container_port, "protocol": p.protocol}
            if p.host_port is not None:
                mapping["hostPort"] = p.host_port
            port_mappings.append(mapping)
        return port_mappings

    def get_environment(self) -> list[dict[str, str]]:
        environment = dict(self._input.environment)
        environment.update(self.extra_environment)
        return [{"name": k, "value": v} for k, v in environment.items()]

    def get_dockerLabels(self) -> dict[str, str]:  # noqa: N802
        return dict(self._input.labels)

    def get_ulimits(self) -> list[dict[str, Any]]:
        return [
            {"name": name, "softLimit": u.soft, "hardLimit": u.hard}
            for name, u in self._input.ulimits.items()
        ]

    def get_logConfiguration(self) -> dict[str, Any]:  # noqa: N802
        if self._input.logging is None:
            return {}
        lc: dict[str, Any] = {"logDriver": self._input.logging.driver}
        if self._input.logging.options:
            lc["options"] = self._input.logging.options
        return lc

    def get_linuxParameters(self) -> dict[str, Any]:  # noqa: N802
        linux_parameters: dict[str, Any] = {}
        if self._input.cap_add or self._input.cap_drop:
            capabilities: dict[str, Any] = {}
            if self._input.cap_add:
                capabilities["add"] = self._input.cap_add
            if self._input.cap_drop:
                capabilities["drop"] = self._input.cap_drop
            linux_parameters["capabilities"] = capabilities
        if self._input.tmpfs:
            linux_parameters["tmpfs"] = []
            for tc in self._input.tmpfs:
                entry: dict[str, Any] = {"containerPath": tc.container_path, "size": tc.size}
                if tc.mount_options:
                    entry["mountOptions"] = tc.mount_options
                linux_parameters["tmpfs"].append(entry)
        return linux_parameters

    def get_extraHosts(self) -> list[dict[str, str]]:  # noqa: N802
        return [
            {"hostname": h.hostname, "ipAddress": h.ip_address}
            for h in self._input.extra_hosts
        ]

    def get_mountPoints(self) -> list[dict[str, str]]:  # noqa: N802
        volume_names = set()
        for v in self.task_definition_data["volumes"]:
            volume_names.add(v["name"])

        mountPoints: list[dict[str, str]] = []  # noqa: N806
        for v in self._input.volumes:
            fields = v.split(":")
            host_path = fields[0]
            container_path = fields[1]
            readOnly = False  # noqa: N806
            if len(fields) == 3:  # noqa: PLR2004
                readOnly = fields[2] == "ro"  # noqa: N806
            name = self.MOUNT_RE.sub("_", host_path)
            name = name[:254] if len(name) > 254 else name  # noqa: PLR2004
            if name not in volume_names:
                self.task_definition_data["volumes"].append(
                    {"name": name, "host": {"sourcePath": host_path}}
                )
                volume_names.add(name)
            mountPoints.append(
                {
                    "sourceVolume": name,
                    "containerPath": container_path,
                    "readOnly": readOnly,
                }
            )
        return mountPoints

    def convert(self) -> tuple[dict[str, Any], dict[str, Any]]:  # noqa: PLR0912
        data: dict[str, Any] = {}
        # name/image/essential are Optional on ContainerDefinitionOverlayInput
        # (partial=True); when absent there, Adapter.set()'s old behavior was
        # to omit the key entirely rather than apply a default, so we do the
        # same here. On the strict ContainerDefinitionInput (partial=False)
        # these are never None, so this is equivalent to unconditional
        # assignment in that mode.
        if self._input.name is not None:
            data["name"] = self._input.name
        if self._input.image is not None:
            data["image"] = self._input.image
        if self._input.essential is not None:
            data["essential"] = self._input.essential
        cpu = self.get_cpu()
        if self._input.memory_reservation is not None:
            data["memoryReservation"] = self._input.memory_reservation
        if cpu is not None:
            data["cpu"] = cpu
        memory = self.get_memory()
        if memory is not None:
            data["memory"] = memory
        memoryReservation = data.get("memoryReservation")  # noqa: N806
        if memoryReservation is None and memory is None:
            if not self.partial:
                if not self.is_fargate:
                    data["memory"] = 512
        if memoryReservation is not None and memory is not None:
            if memoryReservation >= memory:
                msg = 'container "{}": "memoryReservation" must be less than "memory"'.format(  # noqa: E501
                    self._input.name
                )
                raise self.SchemaException(msg)
        if self._input.ports:
            data["portMappings"] = self.get_ports()
        if self._input.command:
            data["command"] = self._input.command
        if self._input.entrypoint:
            data["entryPoint"] = self._input.entrypoint
        if self._input.ulimits:
            data["ulimits"] = self.get_ulimits()
        if self._input.environment or self.extra_environment:
            data["environment"] = self.get_environment()
        if self._input.volumes:
            data["mountPoints"] = self.get_mountPoints()
        if self._input.links:
            data["links"] = self._input.links
        if self._input.labels:
            data["dockerLabels"] = self.get_dockerLabels()
        if self._input.logging:
            data["logConfiguration"] = self.get_logConfiguration()
        if self._input.extra_hosts:
            data["extraHosts"] = self.get_extraHosts()
        if self._input.cap_add or self._input.cap_drop or self._input.tmpfs:
            data["linuxParameters"] = self.get_linuxParameters()
        if self.secrets:
            data["secrets"] = self.get_secrets()
        if self.readonly_root_filesystem is not None:
            data["readonlyRootFilesystem"] = self.readonly_root_filesystem
        kwargs = {}
        kwargs["secrets"] = self.secrets
        return data, kwargs
```

No new import is needed for `MOUNT_RE` — `ContainerDefinitionAdapter` already declares it as a class
attribute (`MOUNT_RE = re.compile("[^A-Za-z0-9_-]")`), and `get_mountPoints()` above already uses
`self.MOUNT_RE`, unchanged from today. Remove the now-unused `PORTS_RE` class attribute (port parsing
moved to `PortMapping.parse()` in `deployfish/config/schema/container.py`) and the `shlex`/`re`
imports at the top of the file if nothing else references them after this task's changes.

- [ ] **Step 3: Add a test for the deliberate `labels` → `dockerLabels` fix**

Per the ADR's called-out exception to "zero behavior change": today, `deployfish.yml`'s `labels:` key
produces no `dockerLabels` output at all (`convert()` never called `get_dockerLabels()`). This rewrite
fixes that. Add to `tests/test_ecs_adapters_comprehensive.py`, inside
`TestContainerDefinitionAdapterComprehensive`:

```python
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
```

- [ ] **Step 4: Run the full test file**

Run: `.venv/bin/pytest tests/test_ecs_adapters_comprehensive.py tests/test_container_definition_adapter_golden_master.py -v`
Expected: golden-master tests PASS unchanged, and `test_labels_produces_docker_labels_after_pilot_fix`
PASSES (new behavior). Some other `TestContainerDefinitionAdapterComprehensive` tests still FAIL — the
ones calling `get_ports()`/`get_logConfiguration()`/etc. directly with invalid data and expecting the
exception from that call (Task 8 fixes these).

- [ ] **Step 5: Ruff and mypy**

Run: `.venv/bin/ruff check deployfish/core/adapters/deployfish/ecs/container.py`
Run: `.venv/bin/mypy deployfish/core/adapters/deployfish/ecs/container.py`
Expected: clean (fix any reported issues — e.g. remove now-dead `self.set()`/`only_one_is_True`
usages and unused imports).

- [ ] **Step 6: Commit**

```bash
git add deployfish/core/adapters/deployfish/ecs/container.py tests/test_ecs_adapters_comprehensive.py
git commit -m "refactor: rebuild ContainerDefinitionAdapter output from validated ContainerDefinitionInput

Also fixes labels: -> dockerLabels wiring, which convert() never did (docs/adr/0001-pydantic-adapters.md)."
```

---

### Task 8: Update the direct-`get_*()`-call tests for eager validation

**Files:**
- Modify: `tests/test_ecs_adapters_comprehensive.py:179-188` (`test_get_ports_rejects_invalid_mapping`)
- Modify: `tests/test_ecs_adapters_comprehensive.py:227-239` (`test_logging_block_requires_driver`)

**Interfaces:**
- Consumes: `ContainerDefinitionAdapter` (as rewritten in Tasks 6-7).

- [ ] **Step 1: Update `test_get_ports_rejects_invalid_mapping`**

Replace:

```python
    def test_get_ports_rejects_invalid_mapping(self) -> None:
        container = {
            "name": "foobar",
            "image": "img:1",
            "cpu": 128,
            "memory": 256,
            "ports": ["not-a-port"],
        }
        with pytest.raises(SchemaException, match="not a valid port mapping"):
            self._adapter(container).get_ports()
```

with:

```python
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
```

- [ ] **Step 2: Update `test_logging_block_requires_driver`**

Replace:

```python
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
            self._adapter(container).get_logConfiguration()
```

with:

```python
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
```

- [ ] **Step 3: Run the full test file**

Run: `.venv/bin/pytest tests/test_ecs_adapters_comprehensive.py tests/test_container_definition_adapter_golden_master.py -v`
Expected: ALL PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/test_ecs_adapters_comprehensive.py
git commit -m "test: move ContainerDefinitionAdapter invalid-input assertions to construction time"
```

---

### Task 9: Full verification and cleanup

**Files:** none new — verification only.

- [ ] **Step 1: Run the full test suite with coverage**

Run: `.venv/bin/pytest --cov=deployfish.core.adapters --cov=deployfish.config.schema --cov-report=term-missing tests/ -q`
Expected: all tests pass; coverage on `deployfish/config/schema/` and
`deployfish/core/adapters/deployfish/ecs/container.py` at or above the project's 80% floor.

- [ ] **Step 2: Ruff and mypy on everything touched**

Run: `.venv/bin/ruff check deployfish/config/schema/ deployfish/core/adapters/deployfish/ecs/container.py tests/`
Run: `.venv/bin/mypy deployfish/config/schema/ deployfish/core/adapters/deployfish/ecs/container.py`
Expected: clean. Note any pre-existing, unrelated failures separately (do not fix them here).

- [ ] **Step 3: Napoleon gate**

Run: `make napoleon-gate`
Expected: no new violations.

- [ ] **Step 4: Update the graph index**

Run: `graphify update .`

- [ ] **Step 5: Final commit (if any cleanup was needed in steps 1-4)**

```bash
git add -A
git commit -m "chore: final verification pass for ContainerDefinitionAdapter Pydantic pilot"
```

---

## Post-pilot follow-up (not part of this plan)

Once this lands and the pattern is validated, the ADR (`docs/adr/0001-pydantic-adapters.md`) anticipates:
converting the remaining 7 adapters one at a time, and eventually composing per-resource input models
in `deployfish/config/schema/` into a single `deployfish.yml`-wide validator. Neither is in scope here.
