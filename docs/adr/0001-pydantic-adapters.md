---
status: accepted
---

# Replace hand-rolled Adapter dict-mutation with Pydantic models

Our `Adapter` base class (`deployfish/core/adapters/abstract.py`) converts `deployfish.yml` dicts into
AWS API-shaped dicts via `Adapter.set()`: manual field rename, default, optional, and coercion logic,
repeated across all 8 adapter files with zero schema validation. We're replacing this pattern with
Pydantic models, one adapter at a time, starting with `ContainerDefinitionAdapter` as a pilot rather
than converting all 8 adapters in a single pass. Pydantic is a new dependency (added specifically
for this refactor — not previously used by `deployfish/core/models/`), justified because it gives us
field aliasing, defaults, and real validation errors for free instead of hand-rolled equivalents. The
incremental rollout de-risks converting
`ServiceAdapter` (currently the highest-degree node in the adapters module, composing most of the
other adapters) until the pattern proves out on a smaller, self-contained adapter first.

Pydantic is confined to the adapter's internal parse/build step. `Adapter.convert()` keeps its
existing contract (documented in `docs/source/runbook/adapters.rst`): it returns `(data, kwargs)`
where `data` is a plain dict shaped exactly like a boto3 `describe_*` response, which
`Model.__init__(data)` consumes directly and keeps as `self.data` for the model's whole lifecycle
(including later direct use in `create_*`-style AWS calls, and the from-AWS vs from-yaml lazy-loading
split described in the runbook). We are not changing that contract. A Pydantic-validated adapter
still ends `.convert()` with a plain dict built the same way `Model.__init__` has always consumed it
— see below for how that dict actually gets built (not via Pydantic serialization/aliasing).

Input models validate (and reshape) the `deployfish.yml` stanza only — they don't try to also produce
the final boto3-shaped output via Pydantic aliasing/serialization. All of the messy-input-shape
problems specific to a container stanza (env/labels as list-of-strings-or-dict, ulimits as
scalar-or-`{soft,hard}`, ports as int-or-`"host:container/proto"` string) are handled by
`field_validator`/`model_validator` functions on `ContainerDefinitionInput` — that's exactly what
Pydantic validators are for, including the structural reshaping (e.g. regex-parsing a port string
into `{hostPort, containerPort, protocol}`), not just accept/reject checks. What stays out of Pydantic
entirely is the final rename into boto3's exact key casing (`dockerLabels`, `entryPoint`,
`linuxParameters`, ...): that remains plain code in the adapter (the existing `get_ports()`,
`get_ulimits()`, etc. methods), now operating on the validated model's already-normalized fields
instead of a raw dict, because Q3/Q6 rejected using Pydantic's alias/serialization system to produce
this output — several of these transforms are structural, not simple renames.

Note: task-definition-level volume declarations (`path`/`config`/`efs_config` mutual exclusion,
handled today by `TaskDefinitionAdapter.get_volumes()`) are a different adapter and out of scope for
this pilot (Q1 scoped the pilot to `ContainerDefinitionAdapter` only). Container-level volume
handling (`get_mountPoints()`, which references existing volume names via `host:container[:ro]`
syntax and mutates `task_definition_data["volumes"]`) has no mutual-exclusion validation and is a
cross-object concern — see below.

Cross-object validation (a container's `cpu`/`memory` vs. the task definition's own `cpu`/`memory`
limits; whether a mount-point's volume already exists on the task definition) stays out of the input
model too, as adapter-level plain code that runs after `model_validate()`, using the validated model's
fields as trusted input. The input model only validates what's self-contained in the container's own
yaml stanza. Two reasons: cross-object checks would require passing sibling state in via Pydantic's
`context` mechanism, which is a layering smell for "is this container stanza well-formed"; and
`get_mountPoints()` today *mutates* the task definition's volume list as a side effect of building
mount points, which validators must not do. This is expected to change as nested Pydantic models
(container model composed into a task-definition model) make direct field-level cross-validation
natural instead of context-passing.

Input models live in `deployfish/config/schema/` (new module, one file per resource, mirroring the
adapter-file split), not inside `deployfish/core/adapters/` or `deployfish/core/models/`. They
describe the shape of `deployfish.yml`, which is a `config` concern — the existing
`deployfish/config/processors/` (terraform interpolation etc.) already lives there. This location was
chosen with a specific future goal in mind: eventually composing these per-resource input models into
a single validator for an entire `deployfish.yml` file. Adapters will import and consume these models
as a dependency, not own them.

`pydantic.ValidationError` is caught at the adapter boundary and re-raised as the existing
`Adapter.SchemaException`, with a short hand-built message summarizing the validation errors. This
keeps the current exception contract intact: `deployfish/controllers/utils.py`'s
`handle_model_exceptions` catches `SchemaException` and prints `str(e)` in red as the CLI's
user-facing error — Pydantic's native multi-line `ValidationError` dump is not what a `deployfish.yml`
author should see for a typo'd port mapping.

`ContainerDefinitionAdapter` keeps subclassing `Adapter` even though it stops calling
`Adapter.set()`/`only_one_is_True()` once the input model's validators absorb that work. The
`.convert()` contract, `self.data`, `self.partial`, and `self.SchemaException` all keep working
unchanged for `TaskDefinitionAdapter`, which still instantiates and calls `.convert()` on it the same
way. The now-unused `Adapter` helpers are accepted as dead code on this one class for now — cutting
the inheritance is a separate, bigger decision (redesigning the adapter interface itself) deferred
until more adapters have converted and `Adapter`'s own fate is decided.

Values injected by the caller rather than present in the container's own yaml stanza — `secrets`,
`extra_environment`, `readonly_root_filesystem`, and (per the cross-object-validation decision above)
`task_definition_data` — stay as plain `ContainerDefinitionAdapter` constructor args / attributes,
exactly as today. They are not folded into the input model. The input model's job stays crisp:
validate the shape of the container's own `deployfish.yml` stanza, nothing about what this adapter
run additionally needs.

`ContainerDefinitionAdapter`'s `partial` flag (used when building overlay containers for
`ServiceHelperTask` command-specific overrides) changes which fields are required, not just their
values — under `partial=True`, `name`/`image`/etc. may be absent rather than raising. Rather than
hand-duplicating the input model as two separate classes, or making everything `Optional` and
re-implementing required-ness by hand in a validator, the overlay variant is derived programmatically
from the strict `ContainerDefinitionInput` (pydantic's documented pattern for building an all-optional
"patch" model from a base model, via `create_model`). One source of truth for field definitions; the
strict/overlay distinction is a real PATCH/overlay semantic, matching what `partial=True` already
means in the domain.

`ContainerDefinitionInput.model_validate()` runs eagerly, once, at adapter construction — not lazily
inside individual `get_ports()`/`get_ulimits()`/etc. calls. This is an observable behavior change from
today: several existing tests (`test_get_ports_rejects_invalid_mapping`,
`test_logging_block_requires_driver`, etc., in `test_ecs_adapters_comprehensive.py`) construct the
adapter with invalid data and expect a specific `get_*()` method call to raise, rather than
construction itself. Those tests are updated as part of this work to expect the exception at
construction. Lazy per-method validation was rejected because it defeats the actual goal (catch bad
input once, up front) and would mean re-implementing validation checkpoints scattered across every
accessor instead of one coherent model — those tests are asserting an implementation-detail
granularity (which call raises) that this refactor is intentionally changing, as opposed to
`.convert()`'s output contract, which the golden-master test (below) protects.

Before rewriting `ContainerDefinitionAdapter`, we add a golden-master test: run a corpus of
representative container stanzas through the *current* `.convert()` and assert the output against
captured golden dicts. That test runs unmodified through the rewrite. The existing unit test suite
(`test_ecs_adapters_comprehensive.py`, `test_coverage_gaps_models_renderers.py`, ~90% coverage) isn't
sufficient on its own here — this rewrite changes the *mechanism* (validators + a derived partial
model replacing hand-written branching), and the one contract that must not drift is "identical `data`
dict shape out," which a golden-master test defends directly rather than incidentally.

One deliberate exception to "zero behavior change": today, `ContainerDefinitionAdapter.convert()`
does `self.set(data, "dockerLabels", optional=True)` — a literal passthrough of a `dockerLabels` key,
which `deployfish.yml` never actually sets (the real key is `labels:`). `get_dockerLabels()` (which
correctly handles `labels:`'s list-or-dict duality) exists but is never called by `convert()` — it's
reachable only via direct test calls. `deployfish.yml`'s `labels:` therefore produces no `dockerLabels`
output today; this is a bug, verified empirically against the running code. The pilot fixes this: the
rewritten `convert()` calls `get_dockerLabels()` when `labels` is present, so `labels:` in
`deployfish.yml` starts actually working. This is the one intentional deviation from this ADR's
"identical `data` dict shape out" contract, called out explicitly rather than silently preserved or
silently fixed.

## Considered Options

- Convert all 8 adapters in one pass — rejected: too large a single change against a 60-degree god
  node (`ServiceAdapter`) with no proof the pattern fits until tried.
- Keep the existing `Adapter`/`set()` pattern — rejected: no validation, silent `KeyError`s at
  runtime, and the same rename/default/optional logic re-implemented by hand in every adapter.
- Push Pydantic models through to `Model.__init__` itself — rejected: touches every `Model` subclass
  (`core/models/ecs.py` alone is 4300+ lines) and the documented from-AWS/from-yaml lazy-loading
  contract; a much larger change than "adapters get input validation."
- A single dual-purpose model per resource, using Pydantic aliasing to also produce the boto3-shaped
  output — rejected: several transforms are structural, not renames, and don't fit Pydantic's alias
  system.
- Input models inside `deployfish/core/adapters/` or `deployfish/core/models/` — rejected: they
  describe `deployfish.yml`'s shape, a `config` concern, and need a stable, adapter-independent home
  to later compose into a whole-file validator.
- Let `pydantic.ValidationError` propagate to the CLI directly — rejected: worse user-facing error
  messages than the current terse `SchemaException` text, and would require widening every existing
  `except SchemaException` catch site.
- Two hand-written model classes for strict vs. partial/overlay validation — rejected: duplicates
  field definitions between the two classes with no single source of truth.
- One model with all fields `Optional`, required-ness enforced by a hand-written validator — rejected:
  gives up Pydantic's declarative required-ness for exactly the fields (`name`, `image`) where it
  matters most.
- Rely on the existing unit test suite alone, with no golden-master fixtures — rejected: the rewrite
  changes validation mechanism, not just implementation detail, and the load-bearing contract
  (identical `data` dict shape) deserves a test that defends it directly.
- Lazy, per-`get_*()`-call validation to preserve today's exact "which call raises" behavior —
  rejected: defeats the goal of catching bad input once, up front, and re-scatters validation
  checkpoints across every accessor instead of one coherent model.
