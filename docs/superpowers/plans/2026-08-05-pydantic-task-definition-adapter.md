# Pydantic TaskDefinitionAdapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert `TaskDefinitionAdapter` to validate `deployfish.yml` task-definition stanzas through a Pydantic `TaskDefinitionInput` model that composes `ContainerDefinitionInput` as a nested field, per `docs/adr/0002-pydantic-task-definition-adapter.md`.

**Architecture:** A new `TaskDefinitionInput` (and derived `TaskDefinitionOverlayInput`) in `deployfish/config/schema/task_definition.py` validates the whole task-definition stanza, including nested containers, in one `model_validate()` call at `TaskDefinitionAdapter.__init__`. Cross-object cpu/memory checks (container vs. task-level limits) move into a `model_validator` on `TaskDefinitionInput`. Volume `path`/`config`/`efs_config` mutual exclusion and duplicate-name rejection become a validated `Volume` sub-model. `partial_model()` gains opt-in support for swapping a nested list field's inner model to that model's own partial variant, needed so `TaskDefinitionOverlayInput.containers` uses `ContainerDefinitionOverlayInput`, not the strict container model. `TaskDefinitionAdapter.convert()` keeps its existing `(data, kwargs)` contract; boto3-shaped dict construction (volumes, per-container output via `ContainerDefinitionAdapter`, task cpu/memory aggregation via `set_task_cpu`/`set_task_memory`) stays adapter-level plain code, unchanged in mechanism.

**Tech Stack:** Python, Pydantic v2, pytest.

## Global Constraints

- Use `.venv/bin/python`, `.venv/bin/pytest`, `.venv/bin/ruff`, `.venv/bin/mypy` — never bare `python`/`pytest`/`ruff`/`mypy`.
- Every non-test Python file touched needs: class docstrings with `Args:` when the constructor takes arguments; function/method docstrings with only the applicable `Side Effects:`/`Args:`/`Keyword Args:`/`Raises:`/`Returns:`/`Yields:` sections (no placeholders); Napoleon `#:` comments on class attributes, `__init__` instance attributes, and module-level globals.
- After implementation edits: run `ruff` and `mypy` on touched files, then `make napoleon-gate`. Fix everything before finishing a task.
- `pydantic.ValidationError` never escapes an adapter boundary — always translate to `Adapter.SchemaException` (subclass of `deployfish.exceptions.SchemaException`) with a short, hand-built message, same contract as ADR 0001 and the existing `ContainerDefinitionAdapter._validate()`.
- Do not modify `tests/test_container_definition_adapter_golden_master.py` (locked characterization test from the completed pilot). A new, equally-locked golden-master file for `TaskDefinitionAdapter` is added in Task 1 and must not be modified by any later task in this plan.
- `ContainerDefinitionAdapter` is only ever constructed by `TaskDefinitionAdapter` in production code (verified: no other call site). Changes to its `get_cpu()`/`get_memory()` cross-check behavior (Task 6) are safe to make without a wider search.

---

## Task 1: Golden-master characterization test for TaskDefinitionAdapter.convert()

**Files:**
- Create: `tests/test_task_definition_adapter_golden_master.py`

**Interfaces:**
- Consumes: `deployfish.core.adapters.deployfish.ecs.task_definition.TaskDefinitionAdapter` (current, unmodified implementation), `deployfish.exceptions.SchemaException`.
- Produces: a locked fixture file asserting `TaskDefinitionAdapter(...).convert()` output shape for representative stanzas. Every later task must keep this file passing unmodified (it is the contract that "identical output dict shape" survives the rewrite).

This test runs against **today's** `TaskDefinitionAdapter` before any other task in this plan touches it. It must be written and passing before Task 5 begins.

- [ ] **Step 1: Write the golden-master test file**

```python
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
        assert payload["cpu"] is None or "cpu" not in payload

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
        # No task-level or container-level cpu/memory given: set_task_cpu /
        # set_task_memory pick the smallest valid FARGATE tier.
        assert payload["cpu"] == "256"
        assert payload["memory"] == "512"

    def test_fargate_without_execution_role_raises(self) -> None:
        data = {
            "family": "web",
            "launch_type": "FARGATE",
            "containers": [{"name": "web", "image": "nginx:1.25"}],
        }
        with pytest.raises(SchemaException):
            TaskDefinitionAdapter(deepcopy(data))

    def test_missing_containers_raises(self) -> None:
        data = {"family": "web"}
        with pytest.raises(SchemaException, match="at least one container"):
            TaskDefinitionAdapter(deepcopy(data))

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
        with pytest.raises(SchemaException):
            TaskDefinitionAdapter(deepcopy(data))

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
        with pytest.raises(SchemaException, match="cpu is greater than the task cpu"):
            TaskDefinitionAdapter(deepcopy(data))
```

- [ ] **Step 2: Run the golden-master test against today's (unmodified) TaskDefinitionAdapter**

Run: `.venv/bin/pytest tests/test_task_definition_adapter_golden_master.py -v`
Expected: All tests PASS against the current hand-rolled adapter. If any assertion doesn't match today's actual output, fix the assertion (not the adapter) — this file characterizes current behavior, it doesn't specify desired behavior.

- [ ] **Step 3: Commit**

```bash
git add tests/test_task_definition_adapter_golden_master.py
git commit -m "test: add golden-master characterization for TaskDefinitionAdapter.convert()"
```

---

## Task 2: Opt-in nested-partial support in partial_model()

**Files:**
- Modify: `deployfish/config/schema/_partial.py`
- Test: `tests/test_config_schema_partial.py`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `partial_model(model, name=None, nested=None)` — new optional `nested: dict[str, type[BaseModel]] | None` kwarg. For any field named in `nested`, the derived model's field type becomes `list[nested[field_name]] | None` if the original field was a `list[...]`, or `nested[field_name] | None` otherwise, instead of the naive `original_annotation | None`. Fields not named in `nested` are completely unaffected — this preserves `ContainerDefinitionOverlayInput = partial_model(ContainerDefinitionInput, name="ContainerDefinitionOverlayInput")`'s exact current behavior (it passes no `nested` arg).

- [ ] **Step 1: Write the failing test**

Add to `tests/test_config_schema_partial.py`:

```python
class _Gadget(BaseModel):
    name: str
    tags: list[str] = []


class _WidgetContainer(BaseModel):
    name: str
    widgets: list[_Widget] = []
    gadget: _Gadget | None = None


class TestPartialModelNested:
    def test_list_field_not_in_nested_keeps_strict_inner_type(self) -> None:
        Partial = partial_model(_WidgetContainer)  # noqa: N806
        with pytest.raises(ValidationError):
            # widgets entries are still strict _Widget: count=0 is invalid
            Partial(widgets=[{"name": "a", "count": 0}])

    def test_list_field_in_nested_uses_partial_inner_type(self) -> None:
        PartialWidget = partial_model(_Widget)  # noqa: N806
        Partial = partial_model(  # noqa: N806
            _WidgetContainer, nested={"widgets": PartialWidget}
        )
        instance = Partial(widgets=[{"count": 0}])
        assert instance.widgets[0].name is None
        assert instance.widgets[0].count == 0

    def test_scalar_field_in_nested_uses_partial_inner_type(self) -> None:
        PartialGadget = partial_model(_Gadget)  # noqa: N806
        Partial = partial_model(  # noqa: N806
            _WidgetContainer, nested={"gadget": PartialGadget}
        )
        instance = Partial(gadget={"tags": ["x"]})
        assert instance.gadget.name is None
        assert instance.gadget.tags == ["x"]

    def test_field_not_named_in_nested_is_unaffected_by_sibling_nesting(self) -> None:
        PartialWidget = partial_model(_Widget)  # noqa: N806
        Partial = partial_model(  # noqa: N806
            _WidgetContainer, nested={"widgets": PartialWidget}
        )
        instance = Partial()
        assert instance.name is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_config_schema_partial.py -v`
Expected: `test_list_field_in_nested_uses_partial_inner_type` and `test_scalar_field_in_nested_uses_partial_inner_type` FAIL with a `TypeError` (`partial_model() got an unexpected keyword argument 'nested'`). `test_list_field_not_in_nested_keeps_strict_inner_type` and `test_field_not_named_in_nested_is_unaffected_by_sibling_nesting` PASS already (they test today's behavior) — that's fine, they're regression guards for later.

- [ ] **Step 3: Implement nested opt-in support**

Replace the body of `partial_model()` in `deployfish/config/schema/_partial.py`:

```python
"""
Helper for deriving "partial update" Pydantic models, used for the ``partial``
(overlay) construction mode our adapters support.
"""

import copy
import typing
from typing import Any

from pydantic import BaseModel, create_model


def partial_model(
    model: type[BaseModel],
    name: str | None = None,
    nested: dict[str, type[BaseModel]] | None = None,
) -> type[BaseModel]:
    """
    Build a subclass of ``model`` where every field is optional and defaults to
    ``None``.

    Field validators defined on ``model`` are inherited unchanged, because the
    result is a real subclass of ``model``: a validator still runs -- and can
    still raise -- whenever a field is actually given a value, but no longer
    runs (and no error is raised) when the field is omitted.

    Each field's original :py:class:`pydantic.fields.FieldInfo` is copied
    (not rebuilt from scratch), so metadata beyond the annotation --
    ``alias`` in particular -- survives onto the derived model. Without
    this, fields declared with ``Field(alias=...)`` (e.g.
    ``memory_reservation``'s ``"memoryReservation"`` alias) would silently
    lose that alias on the partial variant, and ``extra="forbid"`` would
    then reject the aliased key as an unknown field.

    ``nested`` opts specific fields into also swapping their nested model
    type for a caller-supplied partial variant, instead of just unioning the
    field's existing annotation with ``None``. Without this, a
    ``list[SomeModel]`` field would become ``list[SomeModel] | None`` --
    the list itself becomes optional, but entries inside it stay the
    *strict* ``SomeModel``, rejecting partial entries. This is opt-in per
    field (not automatic for every ``list[BaseModel]``/``BaseModel`` field)
    so existing callers -- e.g. ``ContainerDefinitionOverlayInput`` --
    keep their exact current behavior unless they explicitly ask for more.

    Args:
        model: the strict model to derive the partial variant from.

    Keyword Args:
        name: the name to give the new model class. Defaults to
            ``f"Partial{model.__name__}"``.
        nested: a ``{field_name: partial_variant}`` map. For each named
            field, use ``partial_variant`` as the field's (or its list
            entries') type instead of the field's original nested model
            type.

    Returns:
        A new model class, subclassing ``model``, with every field optional.

    """
    # Use get_type_hints (not __annotations__) so inherited/composed models
    # still resolve Annotated types with their metadata intact.
    type_hints = typing.get_type_hints(model, include_extras=True)
    nested = nested or {}

    field_overrides: dict[str, Any] = {}
    for field_name, field_info in model.model_fields.items():
        original_annotation = type_hints.get(field_name, field_info.annotation)

        if field_name in nested:
            replacement = nested[field_name]
            origin = typing.get_origin(original_annotation)
            effective_annotation: Any = (
                list[replacement] if origin is list else replacement
            )
        else:
            effective_annotation = original_annotation

        # Make it optional by unioning with None
        optional_annotation = (
            effective_annotation | None
            if effective_annotation is not None
            else None
        )

        # Copy the original FieldInfo so alias (and any other metadata)
        # survives, rather than building a bare Field(default=None).
        new_field_info = copy.copy(field_info)
        new_field_info.annotation = optional_annotation
        new_field_info.default = None
        new_field_info.default_factory = None

        field_overrides[field_name] = (optional_annotation, new_field_info)

    model_name = model.__name__.lstrip("_")
    return create_model(
        name or f"Partial{model_name}",
        __base__=model,
        **field_overrides,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_config_schema_partial.py -v`
Expected: All PASS.

- [ ] **Step 5: Run existing container schema/adapter tests to confirm no regression**

Run: `.venv/bin/pytest tests/test_config_schema_container.py tests/test_container_definition_adapter_golden_master.py tests/test_ecs_adapters_comprehensive.py -v`
Expected: All PASS unchanged — `ContainerDefinitionOverlayInput` passes no `nested` arg, so its behavior is untouched.

- [ ] **Step 6: Quality gate**

Run: `.venv/bin/ruff check deployfish/config/schema/_partial.py` and `.venv/bin/mypy deployfish/config/schema/_partial.py`
Expected: No errors. Fix any and re-run.

- [ ] **Step 7: Commit**

```bash
git add deployfish/config/schema/_partial.py tests/test_config_schema_partial.py
git commit -m "feat: opt-in nested-partial support in partial_model()"
```

---

## Task 3: Volume model with mutual exclusion and duplicate-name rejection

**Files:**
- Create: `deployfish/config/schema/task_definition.py`
- Test: `tests/test_config_schema_task_definition.py`

**Interfaces:**
- Consumes: nothing from other tasks (standalone model).
- Produces: `Volume` (fields `name: str`, `path: str | None`, `config: DockerVolumeConfig | None`, `efs_config: EFSConfig | None`), `DockerVolumeConfig`, `EFSConfig`. Later tasks (`TaskDefinitionInput`) use `volumes: list[Volume]` with duplicate-name rejection enforced at the list level (needs a `model_validator` on the *containing* model, since a single `Volume` can't see its siblings — see Step 3).

- [ ] **Step 1: Write the failing test**

Create `tests/test_config_schema_task_definition.py`:

```python
"""Tests for the TaskDefinitionInput sub-models."""

import pytest
from deployfish.config.schema.task_definition import (
    DockerVolumeConfig,
    EFSConfig,
    Volume,
)
from pydantic import ValidationError


class TestVolume:
    def test_path_only(self) -> None:
        v = Volume.model_validate({"name": "host-vol", "path": "/data"})
        assert v.path == "/data"
        assert v.config is None
        assert v.efs_config is None

    def test_config_only(self) -> None:
        v = Volume.model_validate(
            {
                "name": "docker-vol",
                "config": {"scope": "task", "autoprovision": True, "driver": "local"},
            }
        )
        assert v.config.scope == "task"
        assert v.config.autoprovision is True
        assert v.config.driver == "local"

    def test_efs_config_only(self) -> None:
        v = Volume.model_validate(
            {
                "name": "efs-vol",
                "efs_config": {"file_system_id": "fs-123", "root_directory": "/mnt"},
            }
        )
        assert v.efs_config.file_system_id == "fs-123"
        assert v.efs_config.root_directory == "/mnt"

    def test_efs_config_root_directory_optional(self) -> None:
        v = Volume.model_validate(
            {"name": "efs-vol", "efs_config": {"file_system_id": "fs-123"}}
        )
        assert v.efs_config.root_directory is None

    def test_path_and_config_both_set_raises(self) -> None:
        with pytest.raises(ValidationError, match='only one of "path"'):
            Volume.model_validate(
                {"name": "bad", "path": "/a", "config": {"scope": "task"}}
            )

    def test_none_set_is_valid(self) -> None:
        # A bare volume with no path/config/efs_config is valid -- the
        # container-level `volumes:` mount-point syntax populates it later.
        v = Volume.model_validate({"name": "bare"})
        assert v.path is None
        assert v.config is None
        assert v.efs_config is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_config_schema_task_definition.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'deployfish.config.schema.task_definition'`.

- [ ] **Step 3: Write the Volume model**

Create `deployfish/config/schema/task_definition.py`:

```python
"""
Pydantic models describing the shape of a ``deployfish.yml`` task-definition
stanza. These validate and reshape input only -- the boto3-shaped output dict
is still assembled by hand in
:py:class:`deployfish.core.adapters.deployfish.ecs.task_definition.TaskDefinitionAdapter`.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from deployfish.config.schema._partial import partial_model
from deployfish.config.schema.container import (
    ContainerDefinitionInput,
    ContainerDefinitionOverlayInput,
)


class DockerVolumeConfig(BaseModel):
    """
    A Docker-managed volume's configuration.

    Args:
        scope: ``"task"`` or ``"shared"``.
        autoprovision: whether to automatically provision the volume.
        driver: the volume driver name.
        driver_opts: volume driver options.
        labels: labels to apply to the volume.

    """

    #: Pydantic model configuration.
    model_config = ConfigDict(extra="forbid")

    #: ``"task"`` or ``"shared"``.
    scope: str | None = None
    #: Whether to automatically provision the volume.
    autoprovision: bool | None = None
    #: The volume driver name.
    driver: str | None = None
    #: Volume driver options.
    driver_opts: dict[str, str] = Field(default_factory=dict, alias="driverOpts")
    #: Labels to apply to the volume.
    labels: dict[str, str] = Field(default_factory=dict)


class EFSConfig(BaseModel):
    """
    An EFS-backed volume's configuration.

    Args:
        file_system_id: the EFS file system ID.
        root_directory: the root directory within the file system to mount.

    """

    #: Pydantic model configuration.
    model_config = ConfigDict(extra="forbid")

    #: The EFS file system ID.
    file_system_id: str
    #: The root directory within the file system to mount, if not the root.
    root_directory: str | None = None


class Volume(BaseModel):
    """
    A single task-definition-level volume declaration. ``path``, ``config``,
    and ``efs_config`` are mutually exclusive.

    Args:
        name: the volume name, referenced by container mount points.
        path: a host bind-mount path.
        config: a Docker-managed volume configuration.
        efs_config: an EFS-backed volume configuration.

    """

    #: Pydantic model configuration.
    model_config = ConfigDict(extra="forbid")

    #: The volume name, referenced by container mount points.
    name: str
    #: A host bind-mount path.
    path: str | None = None
    #: A Docker-managed volume configuration.
    config: DockerVolumeConfig | None = None
    #: An EFS-backed volume configuration.
    efs_config: EFSConfig | None = None

    @model_validator(mode="after")
    def _mutually_exclusive(self) -> "Volume":
        """
        Enforce that ``path``, ``config``, and ``efs_config`` are mutually
        exclusive.

        Raises:
            ValueError: if more than one of ``path``, ``config``, or
                ``efs_config`` is set.

        Returns:
            ``self``, unchanged.

        """
        specified = sum(
            x is not None for x in (self.path, self.config, self.efs_config)
        )
        if specified > 1:
            msg = (
                'When defining volumes, specify only one of "path", "config" '
                'or "efs_config"'
            )
            raise ValueError(msg)
        return self
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_config_schema_task_definition.py -v`
Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add deployfish/config/schema/task_definition.py tests/test_config_schema_task_definition.py
git commit -m "feat: add Volume schema model with path/config/efs_config mutual exclusion"
```

---

## Task 4: TaskDefinitionInput and TaskDefinitionOverlayInput

**Files:**
- Modify: `deployfish/config/schema/task_definition.py` (append to the file from Task 3)
- Test: `tests/test_config_schema_task_definition.py` (append)

**Interfaces:**
- Consumes: `Volume` (Task 3), `partial_model(model, name=None, nested=None)` (Task 2), `ContainerDefinitionInput`/`ContainerDefinitionOverlayInput` (existing, from `deployfish/config/schema/container.py`).
- Produces: `TaskDefinitionInput` (fields: `family: str`, `network_mode: str = "bridge"` aliased from `networkMode`... see below for exact field list), `TaskDefinitionOverlayInput = partial_model(TaskDefinitionInput, name="TaskDefinitionOverlayInput", nested={"containers": ContainerDefinitionOverlayInput})`. `TaskDefinitionAdapter` (Task 5) will call `TaskDefinitionInput.model_validate(data)` or `TaskDefinitionOverlayInput.model_validate(data)` depending on `partial`.

Field-to-yaml-key mapping (preserving exact current behavior from `task_definition.py`'s `convert()`):

| Model field | yaml key | notes |
|---|---|---|
| `family` | `family` | required unless partial |
| `network_mode` | `network_mode` | default `"bridge"` |
| `launch_type` | `launch_type` | default `"EC2"` |
| `runtime_platform` | `runtime_platform` | optional, nested `{cpu_architecture, operating_system_family}` |
| `placement_constraints` | `placementConstraints` (**literal camelCase yaml key**, existing quirk, preserved as-is) | optional passthrough list of dicts |
| `readonly_root_filesystem` | `readonly_root_filesystem` | optional bool |
| `task_role_arn` | `task_role_arn` | optional |
| `execution_role` | `execution_role` | required if `launch_type == "FARGATE"` and not partial |
| `volumes` | `volumes` | `list[Volume]`, default `[]`, duplicate names rejected |
| `containers` | `containers` | `list[ContainerDefinitionInput]`, required key unless partial |
| `cpu` | `cpu` | optional, coerced to `int` |
| `memory` | `memory` | optional, coerced to `int` |

`cpu`/`memory` on `TaskDefinitionInput` exist only to feed the cross-object validator below — `TaskDefinitionAdapter.convert()` keeps reading `self.data` (the raw dict) for `set_task_cpu`/`set_task_memory`, unchanged (see Task 5).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_config_schema_task_definition.py`:

```python
from deployfish.config.schema.task_definition import (
    TaskDefinitionInput,
    TaskDefinitionOverlayInput,
)


class TestTaskDefinitionInputVolumes:
    def test_duplicate_volume_names_raise(self) -> None:
        with pytest.raises(ValidationError, match='duplicate volume name "dup"'):
            TaskDefinitionInput.model_validate(
                {
                    "family": "web",
                    "containers": [{"name": "web", "image": "nginx:1.25"}],
                    "volumes": [
                        {"name": "dup", "path": "/a"},
                        {"name": "dup", "path": "/b"},
                    ],
                }
            )

    def test_unique_volume_names_pass(self) -> None:
        td = TaskDefinitionInput.model_validate(
            {
                "family": "web",
                "containers": [{"name": "web", "image": "nginx:1.25"}],
                "volumes": [
                    {"name": "a", "path": "/a"},
                    {"name": "b", "path": "/b"},
                ],
            }
        )
        assert [v.name for v in td.volumes] == ["a", "b"]


class TestTaskDefinitionInputContainers:
    def test_composes_container_definition_input(self) -> None:
        td = TaskDefinitionInput.model_validate(
            {
                "family": "web",
                "containers": [
                    {"name": "web", "image": "nginx:1.25", "cpu": 128, "memory": 256}
                ],
            }
        )
        assert len(td.containers) == 1
        assert td.containers[0].name == "web"
        assert td.containers[0].image == "nginx:1.25"

    def test_missing_containers_key_raises_custom_message(self) -> None:
        with pytest.raises(
            ValidationError, match="at least one container in your task definition"
        ):
            TaskDefinitionInput.model_validate({"family": "web"})

    def test_container_cpu_greater_than_task_cpu_raises(self) -> None:
        with pytest.raises(ValidationError, match="cpu is greater than the task cpu"):
            TaskDefinitionInput.model_validate(
                {
                    "family": "web",
                    "cpu": 256,
                    "containers": [
                        {
                            "name": "web",
                            "image": "nginx:1.25",
                            "cpu": 512,
                            "memory": 256,
                        }
                    ],
                }
            )

    def test_container_memory_greater_than_task_memory_raises(self) -> None:
        with pytest.raises(ValidationError, match="memory is greater than task memory"):
            TaskDefinitionInput.model_validate(
                {
                    "family": "web",
                    "memory": 256,
                    "containers": [
                        {
                            "name": "web",
                            "image": "nginx:1.25",
                            "cpu": 128,
                            "memory": 512,
                        }
                    ],
                }
            )

    def test_container_cpu_within_task_cpu_passes(self) -> None:
        td = TaskDefinitionInput.model_validate(
            {
                "family": "web",
                "cpu": 512,
                "containers": [
                    {"name": "web", "image": "nginx:1.25", "cpu": 256, "memory": 256}
                ],
            }
        )
        assert td.cpu == 512

    def test_fargate_without_execution_role_raises(self) -> None:
        with pytest.raises(ValidationError, match='"execution_role"'):
            TaskDefinitionInput.model_validate(
                {
                    "family": "web",
                    "launch_type": "FARGATE",
                    "containers": [{"name": "web", "image": "nginx:1.25"}],
                }
            )

    def test_fargate_with_execution_role_passes(self) -> None:
        td = TaskDefinitionInput.model_validate(
            {
                "family": "web",
                "launch_type": "FARGATE",
                "execution_role": "MY_ROLE",
                "containers": [{"name": "web", "image": "nginx:1.25"}],
            }
        )
        assert td.execution_role == "MY_ROLE"


class TestTaskDefinitionOverlayInput:
    def test_all_fields_optional(self) -> None:
        overlay = TaskDefinitionOverlayInput.model_validate({})
        assert overlay.family is None
        assert overlay.containers is None

    def test_partial_container_overrides_allowed(self) -> None:
        # A ServiceHelperTask command override: only name + command, no image.
        overlay = TaskDefinitionOverlayInput.model_validate(
            {"containers": [{"name": "foobar", "command": "./manage.py migrate"}]}
        )
        assert overlay.containers[0].name == "foobar"
        assert overlay.containers[0].image is None

    def test_missing_containers_does_not_raise(self) -> None:
        # Unlike the strict model, omitting "containers" entirely is fine.
        overlay = TaskDefinitionOverlayInput.model_validate({"family": "web"})
        assert overlay.containers is None

    def test_fargate_without_execution_role_does_not_raise(self) -> None:
        # The strict model's FARGATE/execution_role requirement does not
        # apply to overlay/partial data.
        overlay = TaskDefinitionOverlayInput.model_validate(
            {"launch_type": "FARGATE"}
        )
        assert overlay.execution_role is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_config_schema_task_definition.py -v`
Expected: FAIL with `ImportError` (`TaskDefinitionInput` doesn't exist yet).

- [ ] **Step 3: Implement TaskDefinitionInput and TaskDefinitionOverlayInput**

Append to `deployfish/config/schema/task_definition.py`:

```python
class RuntimePlatform(BaseModel):
    """
    A task definition's CPU/OS platform requirements.

    Args:
        cpu_architecture: the CPU architecture, e.g. ``"X86_64"``.
        operating_system_family: the OS family, e.g. ``"LINUX"``.

    """

    #: Pydantic model configuration.
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    #: The CPU architecture.
    cpu_architecture: str = Field(default="X86_64", alias="cpuArchitecture")
    #: The OS family.
    operating_system_family: str = Field(
        default="LINUX", alias="operatingSystemFamily"
    )


class TaskDefinitionInput(BaseModel):
    """
    Validates and reshapes a ``deployfish.yml`` task-definition stanza,
    including its nested containers. Does not produce the boto3-shaped
    output dict -- see
    :py:class:`deployfish.core.adapters.deployfish.ecs.task_definition.TaskDefinitionAdapter`
    for that.

    Args:
        family: the task definition family name.

    """

    #: Pydantic model configuration.
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    #: The task definition family name.
    family: str
    #: The Docker network mode.
    network_mode: str = "bridge"
    #: The ECS launch type -- ``"EC2"`` or ``"FARGATE"``.
    launch_type: str = "EC2"
    #: CPU/OS platform requirements, if specified.
    runtime_platform: RuntimePlatform | None = None
    #: Placement constraints, passed through unchanged. Note: the
    #: documented/actual yaml key for this is the literal camelCase
    #: ``placementConstraints``, not a snake_case key -- this matches
    #: today's adapter behavior exactly, an existing inconsistency versus
    #: this model's other fields, not something this refactor corrects.
    placement_constraints: list[dict[str, Any]] = Field(
        default_factory=list, alias="placementConstraints"
    )
    #: Whether containers should get a read-only root filesystem by default.
    readonly_root_filesystem: bool | None = None
    #: The IAM role ARN tasks run as.
    task_role_arn: str | None = None
    #: The IAM role ARN ECS uses to pull images / write logs. Required when
    #: ``launch_type`` is ``"FARGATE"``.
    execution_role: str | None = None
    #: Task-definition-level volumes.
    volumes: list[Volume] = Field(default_factory=list)
    #: This task definition's containers.
    containers: list[ContainerDefinitionInput] = Field(default_factory=list)
    #: Task-level CPU units, if specified.
    cpu: int | None = None
    #: Task-level memory (MiB), if specified.
    memory: int | None = None

    @model_validator(mode="before")
    @classmethod
    def _require_containers(cls, data: Any) -> Any:
        """
        Raise a clear, specific error when ``containers`` is missing, instead
        of Pydantic's generic "field required" message. Matches
        ``TaskDefinitionAdapter``'s current message text exactly. Only
        enforced on the strict model -- inherited ``mode="before"``
        validators run for subclasses too, so this must explicitly check
        ``cls`` to avoid also enforcing on ``TaskDefinitionOverlayInput``
        (partial/overlay data), matching today's
        ``if self.partial: containers = self.data.get("containers", [])``
        guard.

        Args:
            data: the raw task-definition stanza.

        Raises:
            ValueError: if ``containers`` is missing on the strict model.

        Returns:
            ``data`` unchanged.

        """
        if (
            cls is TaskDefinitionInput
            and isinstance(data, dict)
            and "containers" not in data
        ):
            msg = "You must define at least one container in your task definition"
            raise ValueError(msg)
        return data

    @model_validator(mode="after")
    def _validate_volume_names_unique(self) -> "TaskDefinitionInput":
        """
        Reject duplicate volume names.

        Raises:
            ValueError: if two volumes share a name.

        Returns:
            ``self``, unchanged.

        """
        seen: set[str] = set()
        for v in self.volumes:
            if v.name in seen:
                msg = f'duplicate volume name "{v.name}"'
                raise ValueError(msg)
            seen.add(v.name)
        return self

    @model_validator(mode="after")
    def _validate_container_resource_limits(self) -> "TaskDefinitionInput":
        """
        Reject any container whose ``cpu``/``memory`` exceeds this task
        definition's own ``cpu``/``memory``, when both are specified.

        Raises:
            ValueError: if a container's ``cpu`` or ``memory`` exceeds the
                task-level value.

        Returns:
            ``self``, unchanged.

        """
        for container in self.containers:
            if (
                self.cpu is not None
                and container.cpu is not None
                and container.cpu > self.cpu
            ):
                msg = (
                    f'container "{container.name}": cpu is greater than the '
                    "task cpu value"
                )
                raise ValueError(msg)
            if (
                self.memory is not None
                and container.memory is not None
                and container.memory > self.memory
            ):
                msg = (
                    f'container "{container.name}": memory is greater than '
                    "task memory"
                )
                raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _validate_fargate_requires_execution_role(self) -> "TaskDefinitionInput":
        """
        Require ``execution_role`` when ``launch_type`` is ``"FARGATE"``.
        Only enforced on the strict model -- ``TaskDefinitionOverlayInput``
        (partial/overlay data) skips this, matching today's
        ``if not self.partial`` guard.

        Raises:
            ValueError: if ``launch_type`` is ``"FARGATE"`` and
                ``execution_role`` is not set.

        Returns:
            ``self``, unchanged.

        """
        if type(self) is TaskDefinitionInput and self.launch_type == "FARGATE":
            if not self.execution_role:
                msg = (
                    'If your launch_type is "FARGATE", you must supply '
                    '"execution_role"'
                )
                raise ValueError(msg)
        return self


#: All-optional variant of TaskDefinitionInput, for partial/overlay
#: construction (e.g. StandaloneTaskAdapter/ServiceHelperTaskAdapter's
#: TaskDefinition.new(..., partial=True) call sites). ``containers`` opts
#: into ContainerDefinitionOverlayInput so partial container overrides
#: (e.g. a command override with no "image") validate correctly.
TaskDefinitionOverlayInput = partial_model(
    TaskDefinitionInput,
    name="TaskDefinitionOverlayInput",
    nested={"containers": ContainerDefinitionOverlayInput},
)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_config_schema_task_definition.py -v`
Expected: All PASS.

- [ ] **Step 5: Quality gate**

Run: `.venv/bin/ruff check deployfish/config/schema/task_definition.py` and `.venv/bin/mypy deployfish/config/schema/task_definition.py`
Expected: No errors. Fix any and re-run.

- [ ] **Step 6: Commit**

```bash
git add deployfish/config/schema/task_definition.py tests/test_config_schema_task_definition.py
git commit -m "feat: add TaskDefinitionInput composing ContainerDefinitionInput"
```

---

## Task 5: Remove redundant cross-checks from ContainerDefinitionAdapter

**Files:**
- Modify: `deployfish/core/adapters/deployfish/ecs/container.py:358-442` (`get_cpu()`, `get_memory()`)
- Modify: `tests/test_ecs_adapters_comprehensive.py` (remove/replace `test_cpu_exceeding_task_cpu_raises`)

**Interfaces:**
- Consumes: nothing new — this only removes now-dead code.
- Produces: `get_cpu()`/`get_memory()` keep their default-selection behavior (`is_fargate`/`partial`-based defaulting) unchanged; they no longer raise when a container's cpu/memory exceeds the task-level value, because `TaskDefinitionInput`'s `_validate_container_resource_limits` (Task 4) now guarantees that invariant before `TaskDefinitionAdapter` ever constructs a `ContainerDefinitionAdapter`.

This is a deliberate, documented behavior change for *direct* `ContainerDefinitionAdapter` construction (bypassing `TaskDefinitionAdapter`): the cross-check no longer exists at that layer. Production code only ever reaches `ContainerDefinitionAdapter` through `TaskDefinitionAdapter`, so the invariant still holds end-to-end.

- [ ] **Step 1: Confirm the test to be removed**

Run: `.venv/bin/pytest tests/test_ecs_adapters_comprehensive.py::TestContainerDefinitionAdapterComprehensive::test_cpu_exceeding_task_cpu_raises -v`
Expected: PASS (this is today's behavior, about to be removed).

- [ ] **Step 2: Remove the cross-check from get_cpu()**

In `deployfish/core/adapters/deployfish/ecs/container.py`, in `get_cpu()`, replace:

```python
        default = None if self.is_fargate or self.partial else 256
        cpu = self._input.cpu if self._input.cpu is not None else default
        if "cpu" in self.task_definition_data:
            task_cpu = self.task_definition_data["cpu"]
            if isinstance(task_cpu, str):
                task_cpu = int(task_cpu)
            if cpu is not None and cpu > task_cpu:
                msg = (
                    f'container "{self._input.name}": cpu is greater than the '
                    "task cpu value"
                )
                raise self.SchemaException(msg)
        return cpu
```

with:

```python
        default = None if self.is_fargate or self.partial else 256
        return self._input.cpu if self._input.cpu is not None else default
```

Update the method's docstring to remove the now-inapplicable `Raises:` section (the cross-check moved to `TaskDefinitionInput` -- see `docs/adr/0002-pydantic-task-definition-adapter.md`).

- [ ] **Step 3: Remove the cross-check from get_memory()**

In the same file, in `get_memory()`, replace:

```python
        memory = self._input.memory
        if "memory" in self.task_definition_data:
            task_memory = self.task_definition_data["memory"]
            if isinstance(task_memory, str):
                task_memory = int(task_memory)
            if memory > task_memory:
                msg = (
                    f'container "{self._input.name}": memory is greater than '
                    "task memory"
                )
                raise self.SchemaException(msg)
        return memory
```

with:

```python
        return self._input.memory
```

Update the docstring's `Raises:` section to drop the "container memory is greater than task memory" bullet, for the same reason as Step 2.

- [ ] **Step 4: Replace the removed test with a TaskDefinitionAdapter-level equivalent**

In `tests/test_ecs_adapters_comprehensive.py`, delete `test_cpu_exceeding_task_cpu_raises` from `TestContainerDefinitionAdapterComprehensive`. (Its replacement, `test_container_cpu_exceeding_task_cpu_raises`, already exists in `TestTaskDefinitionInputContainers` from Task 4, and `test_container_cpu_exceeding_task_cpu_raises` in the golden-master file from Task 1 covers it end-to-end through `TaskDefinitionAdapter`.)

- [ ] **Step 5: Run affected tests**

Run: `.venv/bin/pytest tests/test_ecs_adapters_comprehensive.py tests/test_container_definition_adapter_golden_master.py -v`
Expected: All PASS (the deleted test is gone, nothing else references the removed behavior).

- [ ] **Step 6: Quality gate**

Run: `.venv/bin/ruff check deployfish/core/adapters/deployfish/ecs/container.py` and `.venv/bin/mypy deployfish/core/adapters/deployfish/ecs/container.py`
Expected: No errors. Fix any and re-run.

- [ ] **Step 7: Commit**

```bash
git add deployfish/core/adapters/deployfish/ecs/container.py tests/test_ecs_adapters_comprehensive.py
git commit -m "refactor: remove redundant cpu/memory cross-checks from ContainerDefinitionAdapter"
```

---

## Task 6: Rewrite TaskDefinitionAdapter to validate through TaskDefinitionInput

**Files:**
- Modify: `deployfish/core/adapters/deployfish/ecs/task_definition.py` (full rewrite of `__init__`, `get_volumes()`, `convert()`)

**Interfaces:**
- Consumes: `TaskDefinitionInput`/`TaskDefinitionOverlayInput` (Task 4), `ContainerDefinitionAdapter` (existing, unchanged constructor signature).
- Produces: `TaskDefinitionAdapter.convert() -> tuple[dict[str, Any], dict[str, Any]]` — same contract as before. `TaskDefinitionAdapter.__init__` now raises `SchemaException` eagerly (at construction) instead of lazily inside `convert()`/`get_volumes()`.

- [ ] **Step 1: Replace task_definition.py**

Replace the full contents of `deployfish/core/adapters/deployfish/ecs/task_definition.py`:

```python
from copy import copy
from typing import Any, cast

from pydantic import ValidationError

from deployfish.config.schema.task_definition import (
    TaskDefinitionInput,
    TaskDefinitionOverlayInput,
)
from deployfish.core.models.mixins import TaskDefinitionFARGATEMixin
from deployfish.core.models.secrets import Secret

from ...abstract import Adapter
from .container import ContainerDefinitionAdapter


class TaskDefinitionAdapter(TaskDefinitionFARGATEMixin, Adapter):
    """
    Convert our deployfish YAML definition of our task definition to the same
    format that :py:meth:`describe_task_definition` returns, but translate all
    container info into :py:class:`deployfish.core.models.ecs.ContainerDefinition`
    objects.

    Args:
        data: The data from deployfish.yml for this task definition

    Keyword Args:
        secrets: A list of :py:class:`deployfish.core.models.ecs.Secret` objects
            that are used by this task definition
        extra_environment: A dict of extra environment variables to add to the
            task definition
        partial: If True, this is a partial task definition, and we should be
            more lenient about what we accept as valid data.

    """

    def __init__(
        self,
        data: dict[str, Any],
        secrets: list[Secret] | None = None,
        extra_environment: dict[str, Any] | None = None,
        partial: bool = False,  # noqa: FBT001, FBT002
    ) -> None:
        """
        Initialize TaskDefinitionAdapter.

        Args:
            data: data.
            secrets: secrets.
            extra_environment: extra environment.
            partial: partial.

        Raises:
            SchemaException: if ``data`` does not validate against
                :py:class:`deployfish.config.schema.task_definition.TaskDefinitionInput`.

        """
        super().__init__(data)
        #: Secrets.
        self.secrets = secrets or []
        #: Extra environment.
        self.extra_environment = extra_environment or {}
        #: Partial.
        self.partial = partial
        #: The validated, reshaped task-definition stanza.
        self._input = self._validate(data)

    def _validate(
        self, data: dict[str, Any]
    ) -> TaskDefinitionInput:
        """
        Validate ``data`` against the appropriate input model, translating
        :py:exc:`pydantic.ValidationError` into :py:exc:`self.SchemaException`.

        Args:
            data: the raw task-definition stanza.

        Raises:
            SchemaException: if ``data`` does not validate.

        Returns:
            The validated, reshaped task-definition stanza.

        """
        if self.partial:
            input_model = TaskDefinitionOverlayInput
        else:
            input_model = TaskDefinitionInput
        model = cast("type[TaskDefinitionInput]", input_model)
        try:
            return model.model_validate(data)
        except ValidationError as e:
            errors = []
            for err in e.errors():
                loc = err["loc"]
                if loc and loc[0] == "containers" and len(loc) > 1:
                    index = loc[1]
                    container_name = "#{}".format(index)
                    containers = data.get("containers", [])
                    if isinstance(index, int) and index < len(containers):
                        container_name = containers[index].get(
                            "name", f"#{index}"
                        )
                    remainder = ".".join(str(p) for p in loc[2:])
                    label = f"container \"{container_name}\""
                    if remainder:
                        label = f"{label}: {remainder}"
                    errors.append(f"{label}: {err['msg']}")
                else:
                    errors.append(f'{".".join(str(p) for p in loc)}: {err["msg"]}')
            msg = f"task definition is invalid: {'; '.join(errors)}"
            raise self.SchemaException(msg) from e

    def get_volumes(self) -> list[dict[str, Any]]:
        """
        Convert this task definition's validated volume declarations to the
        same structure that :py:meth:`describe_task_definition` returns for
        that info::

            [
                {
                    'name': 'string',
                    'host': {
                        'sourcePath': 'string'
                    },
                    'dockerVolumeConfiguration': {
                        'scope': 'task'|'shared',
                        'autoprovision': True|False,
                        'driver': 'string',
                        'driverOpts': {
                            'string': 'string'
                        },
                        'labels': {
                            'string': 'string'
                        }
                    },
                    'efsVolumeConfiguration': {
                        'fileSystemId': 'string',
                        'rootDirectory': 'string'
                    },
            ]

        Returns:
            A list of volume definitions for this task definition.

        """
        volumes: list[dict[str, Any]] = []
        for v in self._input.volumes:
            v_dict: dict[str, Any] = {"name": v.name}
            if v.path is not None:
                v_dict["host"] = {"sourcePath": v.path}
            elif v.config is not None:
                v_dict["dockerVolumeConfiguration"] = copy(
                    v.config.model_dump(by_alias=True, exclude_none=True)
                )
            elif v.efs_config is not None:
                efs: dict[str, Any] = {"fileSystemId": v.efs_config.file_system_id}
                if v.efs_config.root_directory is not None:
                    efs["rootDirectory"] = v.efs_config.root_directory
                v_dict["efsVolumeConfiguration"] = efs
            volumes.append(v_dict)
        return volumes

    def convert(self) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        :rtype: dict(str, Any), dict(str, Any)

        Returns:
            Operation result.

        """
        data: dict[str, Any] = {}
        data["family"] = self._input.family
        data["networkMode"] = self._input.network_mode
        launch_type = self._input.launch_type
        if launch_type == "FARGATE":
            data["requiresCompatibilities"] = ["FARGATE"]
        if self._input.runtime_platform is not None:
            data["runtimePlatform"] = {
                "cpuArchitecture": self._input.runtime_platform.cpu_architecture,
                "operatingSystemFamily": (
                    self._input.runtime_platform.operating_system_family
                ),
            }
        if self._input.placement_constraints:
            data["placementConstraints"] = self._input.placement_constraints
        readonly_root_filesystem = self._input.readonly_root_filesystem
        if self._input.task_role_arn is not None:
            data["taskRoleArn"] = self._input.task_role_arn
        if self._input.execution_role is not None:
            data["executionRoleArn"] = self._input.execution_role
        data["volumes"] = self.get_volumes()
        containers_data = []
        for container_definition, container_input in zip(
            self.data.get("containers", []),
            self._input.containers or [],
            strict=True,
        ):
            containers_data.append(
                ContainerDefinitionAdapter(
                    container_definition,
                    data,
                    secrets=self.secrets,
                    extra_environment=self.extra_environment,
                    partial=self.partial,
                    readonly_root_filesystem=readonly_root_filesystem,
                ).convert()
            )
        container_data = [c[0] for c in containers_data]
        self.set_task_cpu(data, container_data)
        self.set_task_memory(data, container_data)

        return data, {"containers": containers_data}
```

Note the `zip(self.data.get("containers", []), self._input.containers, strict=True)` in `convert()`: `ContainerDefinitionAdapter` is still constructed from the *raw* container dict (`container_definition`), not `container_input` — Task 5 didn't change `ContainerDefinitionAdapter`'s own `_validate()`, which still runs `ContainerDefinitionInput.model_validate()` on the raw dict itself (redundant re-validation, same as ADR 0001's stated design: the per-resource adapter still owns boto3-shaped output construction). `container_input` (the already-validated model) isn't otherwise used here — it exists so `_validate_container_resource_limits` (Task 4) can run before any `ContainerDefinitionAdapter` is constructed.

- [ ] **Step 2: Run the golden-master test from Task 1**

Run: `.venv/bin/pytest tests/test_task_definition_adapter_golden_master.py -v`
Expected: All PASS — output shape unchanged from the hand-rolled version.

- [ ] **Step 3: Update tests/test_TaskDefinitionAdapter.py**

Replace `test_fargate_requires_execution_role` (currently expects `KeyError` — a pre-existing bug this refactor fixes):

```python
    def test_fargate_requires_execution_role(self) -> None:
        data = deepcopy(SERVICE_YML)
        data["launch_type"] = "FARGATE"
        del data["execution_role"]
        with pytest.raises(SchemaException, match='"execution_role"'):
            TaskDefinitionAdapter(data)
```

Add the import at the top of the file:

```python
from deployfish.exceptions import SchemaException
```

- [ ] **Step 4: Update tests/test_ecs_adapters_comprehensive.py**

`TestTaskDefinitionAdapterComprehensive.test_get_volumes_host_docker_and_efs`, `test_get_volumes_rejects_multiple_volume_specs`, and `test_convert_requires_containers_when_not_partial` all currently expect the exception (or the volume list) from a specific method call (`get_volumes()`, `convert()`) rather than from construction. Update them:

```python
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

    def test_get_volumes_rejects_multiple_volume_specs(self) -> None:
        data = deepcopy(SERVICE_YML)
        data["volumes"] = [{"name": "bad", "path": "/a", "config": {"scope": "task"}}]
        with pytest.raises(SchemaException):
            TaskDefinitionAdapter(data)

    def test_convert_requires_containers_when_not_partial(self) -> None:
        data = deepcopy(SERVICE_YML)
        del data["containers"]
        with pytest.raises(SchemaException, match="at least one container"):
            TaskDefinitionAdapter(data)
```

(`test_get_volumes_host_docker_and_efs` no longer needs the existing assertions on the exact original dict-comparison — check the file's current assertions past line 108 and adjust to match the fields actually asserted there, keeping the same coverage.)

- [ ] **Step 5: Run the full adapter test suite**

Run: `.venv/bin/pytest tests/test_TaskDefinitionAdapter.py tests/test_ecs_adapters_comprehensive.py tests/test_task_definition_adapter_golden_master.py tests/test_config_schema_task_definition.py -v`
Expected: All PASS.

- [ ] **Step 6: Run the StandaloneTaskAdapter / ServiceHelperTaskAdapter tests**

Run: `.venv/bin/pytest tests/ -k "StandaloneTask or ServiceHelperTask or standalone_task or service_helper_task" -v`
Expected: All PASS — confirms `TaskDefinition.new(..., partial=True)` still works end-to-end with `TaskDefinitionOverlayInput`.

- [ ] **Step 7: Run the full test suite**

Run: `.venv/bin/pytest -v`
Expected: All PASS. Investigate and fix any failures before proceeding — do not skip or xfail.

- [ ] **Step 8: Quality gate**

Run: `.venv/bin/ruff check deployfish/core/adapters/deployfish/ecs/task_definition.py`
Run: `.venv/bin/mypy deployfish/core/adapters/deployfish/ecs/task_definition.py`
Run: `make napoleon-gate`
Expected: No errors/new violations. Fix any and re-run.

- [ ] **Step 9: Commit**

```bash
git add deployfish/core/adapters/deployfish/ecs/task_definition.py tests/test_TaskDefinitionAdapter.py tests/test_ecs_adapters_comprehensive.py
git commit -m "feat: validate TaskDefinitionAdapter input through TaskDefinitionInput"
```

---

## Task 7: Update runbook documentation

**Files:**
- Modify: `docs/source/runbook/adapters.rst`

**Interfaces:**
- Consumes: nothing.
- Produces: updated docs reflecting `TaskDefinitionAdapter` as a second Pydantic-validated adapter, alongside `ContainerDefinitionAdapter`.

- [ ] **Step 1: Check what the runbook currently says about ContainerDefinitionAdapter's Pydantic conversion**

Run: `grep -n "Pydantic\|ContainerDefinitionAdapter" docs/source/runbook/adapters.rst`

- [ ] **Step 2: Add an equivalent note for TaskDefinitionAdapter**

Add a paragraph next to the existing `ContainerDefinitionAdapter` Pydantic note (matching its structure and tone) stating that `TaskDefinitionAdapter` now validates through `TaskDefinitionInput` (composing `ContainerDefinitionInput`), referencing `docs/adr/0002-pydantic-task-definition-adapter.md`. Keep it to 2-3 sentences, consistent with the existing note's length.

- [ ] **Step 3: Commit**

```bash
git add docs/source/runbook/adapters.rst
git commit -m "docs: note TaskDefinitionAdapter's Pydantic validation in the runbook"
```

---

## Task 8: Final verification pass

**Files:** none (verification only)

- [ ] **Step 1: Full test suite**

Run: `.venv/bin/pytest -v`
Expected: All PASS, zero skips introduced by this plan.

- [ ] **Step 2: Full lint/type gate**

Run: `.venv/bin/ruff check deployfish/ tests/`
Run: `.venv/bin/mypy deployfish/`
Run: `make napoleon-gate`
Expected: No errors, no new napoleon-gate violations vs. baseline.

- [ ] **Step 3: Confirm both golden-master files are untouched by this plan's diff**

Run: `git log --oneline -- tests/test_container_definition_adapter_golden_master.py`
Expected: No new commits from this plan touch this file (it should show only pilot-era commits).

- [ ] **Step 4: Report**

Summarize: files created/modified, test counts before/after, any pre-existing failures encountered that are unrelated to this work (report separately, do not fix as part of this plan unless trivial and directly blocking).
