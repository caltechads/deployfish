---
status: accepted
---

# Compose ContainerDefinitionInput into TaskDefinitionInput

Following the `ContainerDefinitionAdapter` pilot (ADR 0001), `TaskDefinitionAdapter`
(`deployfish/core/adapters/deployfish/ecs/task_definition.py`) becomes the next Pydantic
slice. `TaskDefinitionInput` composes `ContainerDefinitionInput` directly as a nested
field (`containers: list[ContainerDefinitionInput]`), now that nested models exist. This
is the first adapter where composition, rather than a single self-contained resource, is
in play, and it forces two things ADR 0001 explicitly deferred: real cross-object
validation and a nested overlay/partial variant.

Cross-object validation splits by what it operates on, not just "cpu/memory checks."
`ContainerDefinitionAdapter.get_cpu()`/`get_memory()` today validate a container's
`cpu`/`memory` against the *raw* task-level `cpu`/`memory` values, passed in via the
`task_definition_data` constructor arg, and need `is_fargate`/`partial` context to pick
the container's default (e.g. `256` for a non-partial EC2 container with no explicit
`cpu`). That's genuine input-shape validation now that both live in one model — it moves
into a `model_validator(mode="after")` on `TaskDefinitionInput`, replacing the
`task_definition_data` dict hand-off entirely. `set_task_cpu`/`set_task_memory`
(`deployfish/core/models/mixins.py`), by contrast, aggregate already-adapter-defaulted,
boto3-shaped container output dicts *upward* to pick a valid task-level FARGATE cpu/memory
tier — this operates on `.convert()` output, not on validated input, and stays adapter-level
plain code after `.convert()` builds the container dicts, unchanged from today.

Task-definition-level volume declarations (`path`/`config`/`efs_config` mutual exclusion,
today hand-checked in `TaskDefinitionAdapter.get_volumes()`) become a `Volume` model in a
new `deployfish/config/schema/task_definition.py` (not folded into `container.py` --
volumes are a task-definition-level concern, not a container one), with the mutual
exclusion enforced by a `model_validator`. Today's `get_volumes()` silently drops
duplicate-named volumes; the new model instead raises on a duplicate name. This is a
deliberate, documented behavior change (a silent drop reads as a latent bug, not
intentional behavior), consistent with ADR 0001's "unknown keys now raise" precedent for
tightening lenient legacy parsing.

Same eager-validation-at-construction pattern as the container pilot:
`TaskDefinitionInput.model_validate()` runs once at `TaskDefinitionAdapter.__init__`.
Because containers now nest inside one model, a bad container stanza surfaces as a
`pydantic.ValidationError` with a `loc` path like `containers.2.ports.0`; the
`SchemaException` translation layer resolves the container index back to
`data["containers"][i].get("name", f"#{i}")` so the message attributes the error to a
container by name, not just an index. Validation remains fail-fast on the first error
(not batched across containers), matching Pydantic's and ADR 0001's existing behavior.

Scope includes `TaskDefinitionOverlayInput`, the `partial_model()`-derived overlay variant
used when `StandaloneTaskAdapter`/`ServiceHelperTaskAdapter` build partial/overlay task
data (`TaskDefinition.new(data, "deployfish", partial=True)`) -- most visibly,
`ServiceHelperTaskAdapter`'s per-command container overrides
(`containers: [{name: "foobar", command: "..."}]`, no `image`), which is the central
reason this matters, not an edge case. `partial_model()` (`deployfish/config/schema/_partial.py`)
only unions each field's annotation with `None`; it does not swap a nested model's type,
so a naive `partial_model(TaskDefinitionInput)` would produce
`containers: list[ContainerDefinitionInput] | None` -- the list becomes optional, but each
entry inside it stays the *strict* container model, rejecting exactly the partial
container overrides `ServiceHelperTaskAdapter` sends today. `partial_model()` gains an
explicit opt-in mechanism for a field to also swap its nested-model type to that model's
own partial variant; only `TaskDefinitionOverlayInput.containers` opts in
(`list[ContainerDefinitionOverlayInput] | None`). This is deliberately not blanket
recursion: `ContainerDefinitionOverlayInput` (already built via
`partial_model(ContainerDefinitionInput, ...)` in `container.py`) keeps its exact current
behavior for `ports`/`ulimits`/`tmpfs`/`extra_hosts` -- those fields would also match "list
or dict of nested models," and auto-partializing them was judged an unwelcome, silently
broadening side effect on already-accepted pilot code, not a considered improvement.

A golden-master test for `TaskDefinitionAdapter.convert()` (representative task-definition
YAML corpus through current `.convert()`, output captured and asserted unchanged through
the rewrite) is added before the rewrite, same rationale as ADR 0001: the rewrite changes
validation mechanism, and "identical output dict shape" is the contract worth protecting
directly. Existing tests that construct an adapter with invalid data and expect a specific
`get_volumes()`/`convert()` call to raise move to expecting the exception at construction
time, matching the eager-validation change.

## Considered Options

- Keep `task_definition_data` as a raw dict handed to each `ContainerDefinitionAdapter`
  for cross-object cpu/memory checks, as today -- rejected: ADR 0001 explicitly named
  nested composition as the thing that would make this natural; doing the composition
  without also moving the validation just keeps the same context-passing smell one more
  refactor.
- Make `set_task_cpu`/`set_task_memory`'s FARGATE-tier aggregation part of the
  `model_validator` too -- rejected: it depends on already-defaulted, boto3-shaped output
  (post-`.convert()` container dicts), not on the validated input shape; folding it into
  the input model would require re-deriving adapter output inside a validator.
- Blanket-recursive `partial_model()` (auto-detect any `list[BaseModel]`/`dict[str, BaseModel]`
  field and partialize its inner type) -- rejected: silently changes
  `ContainerDefinitionOverlayInput`'s already-accepted behavior for fields nobody asked to
  change.
- Two hand-written `TaskDefinitionInput` classes (strict and overlay) instead of deriving
  the overlay from `partial_model()` -- rejected: same duplication-of-field-definitions
  reasoning ADR 0001 already rejected for `ContainerDefinitionOverlayInput`.
- Silently drop duplicate-named volumes, matching today's behavior exactly -- rejected:
  a silent drop is indistinguishable from a bug; raising surfaces the deployfish.yml
  author's mistake instead of hiding it.
