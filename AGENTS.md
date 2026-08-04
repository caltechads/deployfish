# AGENTS.md

## Tooling Preflight (Required)

Before planning or implementation, show concise evidence of:

1. `graphify` for codebase exploration and knowledge exploration
2. At least one `code-index` call (search/find/symbol/summary as useful)
3. `context7` and/or `package-registry-mcp` when external library/package behavior, versioning, or package details matter

During Planning:

- Use `code-index` and `graphify` to find files and function calls

In an early progress update: tool names used + one line per result. If a tool is not relevant, say so in one line.

## Post-Implementation Quality Gate (Required)

After implementation edits [Important: Python code files only]:

1. `ruff` on touched files (or broader if needed)
2. `.venv/bin/mypy` on touched files (or broader if needed)
3. `make napoleon-gate`
4. Fix all reported problems before finishing

## Implementation Priority (Required)

Implement the correct product code directly. Do not add runtime patching, indirection, monkey-patching, startup hooks, or similar workarounds just to dodge doc-gate noise, baseline drift, or other documentation-tool friction.

1. Prefer 3rd-party open source packages that solve or can greatly assist the ADR/Spec/problem before building it ourselves

   a. Judge the 3rd-party package for code quality: commit cadence (is it abandoned); stars on github, other typical criteria
      and factor that into your decision.
   b. Use `context7` and `package-registry-mcp` to help you in searching and evaluating

2. Put the change in the correct source file, even when that file has noisy docs or baseline issues
3. Report quality-gate blockers separately, noting pre-existing or unrelated failures
4. Architecture and correctness beat avoiding documentation churn

## Project Structure (Mandatory)

1. Data models (Pydantic, `@dataclass`) → semantically named files in `regis_inspector.models`; mostly bare models plus validation
2. Business logic → service classes in `regis_inspector.services`; inject `click`/`rich`/`textual` from CLI when needed
3. CLI/user interaction/display → `regis_inspector.cli` only; no business logic there

## AWS Interaction

Prefer botocraft models and managers. If botocraft lacks support, tell the user and stop: ask whether to extend botocraft or use straight boto3.

## Architecture (Required)

Prefer cohesive, human-comprehensible classes over loose function collections, even when mostly stateless.

- Model real workflow boundaries and stable domain concepts, not arbitrary namespaces
- Use constructor injection and explicit collaborators
- Keep methods and function bodies ≤ 60 lines
- **Single responsibility:** one clear job per service class; no god classes mixing many different concerns
- Split multi-concern workflows into named collaborators that map to human-understandable concepts
- Keep the public service a thin facade with a small entry-point API
- Put per-run orchestration and mutable run state in a dedicated execution/orchestrator class
- Prefer stateless collaborators; isolate per-run mutable state in one accumulator/orchestrator

Reference: `ExtractionOrchestrator` in `regis_inspector/services/orchestrator.py` (per-run orchestration + `RunStats` accumulator, driving stateless collaborators like `DdlExtractor`).

## Documentation Contract (Required)

For all non-test Python code:

**Class docstrings:** describe the contract; include constructor `Args:` when constructor arguments exist.

**Function/method docstrings:** brief description plus only applicable sections:

- `Side Effects:` — real side effects only
- `Args:` — positional args only
- `Keyword Args:` — keyword args only
- `Raises:` — meaningful exceptions only
- `Returns:` or `Yields:` — when applicable

Do not add placeholder sections or empty/`None`-semantic sections.

**Napoleon `#:` comments** on class attributes, `__init__` instance attributes, and module-level globals.

Enforcement: `make napoleon-gate` (no new violations vs baseline); `make napoleon-gate-strict` when explicitly requested.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
