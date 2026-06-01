# AGENTS.md

## Tooling Preflight Evidence (Required)

Before planning or implementation, every agent must provide concise evidence of:

1. `memory_search` for relevant prior context.
2. At least one `aidex` call (`aidex_session` plus a query/signature/tree/files/status call as useful).
3. At least one `code-index` call (search/find/symbol/summary as useful).
4. `context7` and/or `package-registry-mcp` when external library/package behavior, versioning, or package details are relevant.

In an early progress update, include the tool names used and one line on what each returned.
If a tool is not relevant for the task, state that explicitly in one line.

## Post-Implementation Quality Gate (Required)

After implementation edits are complete:

1. Run `ruff` on the touched files (or broader target if the task requires it).
2. Run `mypy` on the touched files (or broader target if the task requires it).
3. Run `make napoleon-gate` to enforce no new Napoleon documentation violations.
4. Fix all problems reported by those runs before finishing the task.

## Implementation Priority (Required)

Always choose the correct, direct implementation of product code over workarounds
added only to avoid doc-gate noise, baseline drift, or other documentation-tool
friction.

Specifically:

1. Do not add runtime patching, indirection, monkey-patching, startup hooks, or
   similar architectural workarounds solely to avoid touching the correct source
   file.
2. If the correct implementation lives in a legacy file with noisy documentation
   or baseline issues, implement it there anyway.
3. Then report the quality-gate blocker clearly and separately, including which
   failures are pre-existing or unrelated.
4. Architecture and code correctness take priority over avoiding documentation
   churn.

## Documentation Contract (Required)

For all non-test Python code in this repository:

1. Class docstrings must describe the class contract and include constructor `Args:` when constructor arguments exist.
2. Function/method docstrings must include:
   - brief description
   - `Side Effects:` (only when there are real side effects; omit otherwise)
   - `Args:` (only when positional args exist; omit otherwise)
   - `Keyword Args:` (only when keyword args exist; omit otherwise)
   - `Raises:` (only when meaningful exceptions are raised; omit otherwise)
   - `Returns:` or `Yields:` (only when applicable; omit otherwise)
   - Do not add placeholder content such as `None.` for empty/inapplicable sections.
   - Never add `Args:`/`Keyword Args:`/`Returns:`/`Yields:` sections when they would be empty or semantically `None`.
3. Document all of the following with Napoleon `#:` comments:
   - class attributes
   - instance attributes assigned in `__init__`
   - module-level global variables

## Human-Comprehensible Architecture Preference (Required)

For most non-trivial behavior in this repository, prefer implementing cohesive,
human-comprehensible classes over large collections of loosely related free
functions, even when those classes are mostly stateless.

Reason:

1. Clear class responsibilities and interactions make it easier for humans to
   cognitively model the system.
2. Prefer classes that represent real workflow boundaries, owned
   responsibilities, or stable concepts in the domain.
3. Avoid creating classes that are just arbitrary namespaces, but when the
   alternative is a mass of individual functions with shared implicit context,
   prefer the class-oriented design.
4. Favor constructor injection and explicit collaborators when that improves
   readability and makes the system easier for humans to follow.

Enforcement command:

- `make napoleon-gate` (no new violations vs baseline)
- `make napoleon-gate-strict` (all violations; use when explicitly requested)

## Browser testing and Docker logs

To run browser automation against the local app while watching container logs:

1. **Playwright MCP** (server: `user-playwright`): Use for navigation, snapshots, and clicks (e.g. "Export Contact CSV").

2. **Docker MCP** (server: `user-docker-mcp`): Use to fetch container logs during or after the export. Call tool `get-logs` with `container_name: "access_admin"` to retrieve latest logs.
