# Phase 1 Prompt: Shared Infra and Gate Stabilization

Use this prompt in a fresh Codex/Coding-agent session rooted at:

`/Users/cmalek/src/workspace/deployfish`

---

You are continuing a deployfish quality-gate recovery effort.

Goal for this phase:
- Finish shared infra and gate-stabilization work so cross-cutting helpers stop generating repeated `ruff`, `mypy`, and Napoleon failures.

Current measured repo state:
- `ruff`: 1254 errors remaining
- `mypy`: 159 errors remaining
- `make napoleon-gate`: 1462 strict violations remaining

Important context already completed:
- `Makefile` / `bin/check_napoleon_gate.py` now run Napoleon gate against real deployfish source instead of stale `tfreporter`.
- narrow mypy overrides were added in `pyproject.toml`
- repo-wide `ruff check --fix --unsafe-fixes` and `ruff format` already ran
- targeted tests already passing for renderers/ext/helpers/secrets/ssh slices

Your Phase 1 scope:
- `deployfish/config/__init__.py`
- `deployfish/config/config.py`
- `deployfish/core/adapters/abstract.py`
- `deployfish/core/loaders.py`
- `deployfish/renderers/abstract.py`
- `deployfish/renderers/misc.py`
- `deployfish/renderers/table.py`
- `deployfish/ext/ext_df_jinja2.py`
- `deployfish/types.py`
- `tests/controller_helpers.py`
- `tests/test_ext_jinja2.py`
- `tests/test_ext_jinja2_extended.py`
- `tests/test_ssh_mixin_push.py`
- `tests/test_secrets_model.py`
- `tests/test_secrets_discovery_push.py`

What to do:
1. Read current errors for these files with:
   - `.venv/bin/ruff check <phase1-files>`
   - `.venv/bin/mypy <phase1-files>`
   - `make napoleon-gate`
2. Fix only Phase 1 files unless a direct dependency forces a small adjacent edit.
3. Prioritize:
   - shared signature mismatches
   - protocol/test-double compatibility
   - remaining `E501`, `ARG00x`, `FBT001/002`, `SIM117`, `PLW2901`, `PERF401`, `PGH003`, `B904`, `S101`
   - Napoleon-compliant docstrings and `#:` comments for this slice
4. Preserve runtime behavior. Do not relax repo-wide rules.
5. Re-run verification after each batch.

Success criteria for this phase:
- `ruff check` passes on Phase 1 files
- `mypy` passes on Phase 1 files
- targeted tests for these files pass
- `make napoleon-gate` total violation count drops below 1462

Required verification before claiming success:
- `.venv/bin/ruff check <phase1-files>`
- `.venv/bin/mypy <phase1-files>`
- `pytest -q tests/test_ext_jinja2.py tests/test_ext_jinja2_extended.py tests/test_ssh_mixin_push.py tests/test_secrets_model.py tests/test_secrets_discovery_push.py`
- `make napoleon-gate`

When done, report:
- files changed
- exact verification results
- remaining blockers for Phase 2
