# Deployfish Quality Gate Recovery Master Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan phase-by-phase. Keep verification tight after each phase.

**Goal:** Bring `/Users/cmalek/src/workspace/deployfish` to green for `ruff`, `mypy`, and `make napoleon-gate` without weakening standards globally.

**Current State:** As of 2026-06-01, gate wiring is fixed and broad mechanical cleanup already happened. Latest measured status: Ruff reduced from 2163 to 1254 errors, mypy from 389 to 159 errors, and Napoleon gate now targets real deployfish code but still reports 1462 source doc violations.

**Strategy:** Finish repo in ordered phases that remove shared blockers first, then collapse remaining domain hotspots, then complete documentation debt and final verification.

---

## Phase 1: Shared Infra and Gate Stabilization

**Objective:** Finish the highest-leverage shared files so that typing, rendering, and helper abstractions stop generating cross-cutting errors.

**Primary targets:**
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

**What phase must accomplish:**
- Remove remaining shared-signature mypy issues in adapters, renderers, helpers, and extension filters.
- Make protocol/test-double contracts explicit enough that test scaffolding stops tripping abstract/protocol mismatches.
- Clean Ruff findings in these files, especially `E501`, `ARG00x`, `FBT001/002`, `SIM117`, `PLW2901`, `PERF401`, `D404`, `PGH003`, `B904`, `S101`.
- Add Napoleon-compliant docstrings and `#:` comments for this slice so these files stop contributing avoidable gate noise.

**Acceptance criteria:**
- `ruff check` passes on Phase 1 files.
- `mypy` passes on Phase 1 files.
- Targeted tests for renderers/ext/helpers/SSH/secrets pass.
- `make napoleon-gate` shows reduced total violations from current baseline of 1462.

## Phase 2: Test-Suite Ruff and Type Cleanup

**Objective:** Remove concentrated test-only debt that is blocking whole-repo Ruff and inflating mypy noise.

**Primary targets:**
- `tests/test_ServiceHelperTaskAdapter.py`
- `tests/test_StandaloneTaskAdapter.py`
- `tests/test_service_discovery_manager_push.py`
- `tests/test_service_manager_list.py`
- `tests/test_service_manager_extended.py`
- `tests/test_ssh_main_controller_push.py`
- `tests/test_utils_mixins.py`
- `tests/test_waiters.py`
- other test files still contributing `PT019`, `SIM117`, `E501`, and `ARG00x`

**What phase must accomplish:**
- Eliminate `PT019` fixture misuse repo-wide.
- Flatten nested `with` blocks causing `SIM117`.
- Resolve long-line fallout introduced or left after formatting.
- Fix test-local mypy issues involving incorrectly typed `Model` placeholders and helper return types where possible without weakening production contracts.

**Acceptance criteria:**
- `ruff check tests` either passes or leaves only failures from production-coupled tests not practically separable yet.
- Mypy errors drop materially below current 159, with most remaining errors concentrated in production ECS/SSH domain files.

## Phase 3: SSH, Secrets, and Service Discovery Domain Typing

**Objective:** Clear domain-level protocol and optional-typing issues outside the biggest ECS file.

**Primary targets:**
- `deployfish/core/ssh.py`
- `deployfish/core/models/secrets.py`
- `deployfish/core/models/events.py`
- `deployfish/core/models/service_discovery.py`
- `deployfish/core/models/appscaling.py`
- `deployfish/core/models/elbv2.py`
- `deployfish/core/models/cloudwatchlogs.py`
- related tests still failing after Phase 2

**What phase must accomplish:**
- Normalize `None`-default signatures to explicit optionals.
- Align `SSHMixin` / `SupportsTunnel` signatures.
- Fix secrets protocol usage and sequence-vs-dict mismatches.
- Resolve mypy issues around optional schedules, alarms, namespaces, and service discovery linkage.

**Acceptance criteria:**
- `mypy` no longer fails on SSH/secrets/service-discovery families.
- Targeted domain tests pass for SSH, secrets, appscaling, waiters, and service discovery.

## Phase 4: ECS Models and Adapter Hotspots

**Objective:** Finish the heavy production hotspots that currently dominate both Ruff and mypy counts.

**Primary targets:**
- `deployfish/core/models/ecs.py`
- `deployfish/core/adapters/deployfish/ecs.py`
- `deployfish/plugins/mysql/models/mysql.py`
- `deployfish/controllers/network.py`
- `deployfish/controllers/service.py`
- `deployfish/controllers/tunnel.py`
- `deployfish/core/waiters/hooks/ecs.py`

**What phase must accomplish:**
- Resolve ECS adapter return/signature mismatches.
- Fix optional-return and abstract-instantiation issues in ECS models.
- Collapse remaining large Ruff clusters in these files.
- Keep behavior unchanged while improving explicit contracts.

**Acceptance criteria:**
- `mypy` passes on ECS/adapters/controllers hotspot set.
- Ruff findings in these files are cleared.
- Relevant ECS/controller tests pass.

## Phase 5: Repo-Wide Napoleon Completion

**Objective:** Drive non-test source documentation debt to zero so `make napoleon-gate` passes cleanly.

**Primary targets:**
- `deployfish/__init__.py`
- `deployfish/registry.py`
- `deployfish/main.py`
- `deployfish/ext/*.py`
- `deployfish/renderers/*.py`
- `deployfish/plugins/*`
- `deployfish/core/models/*`
- `deployfish/core/adapters/*`
- any remaining source files reported by `make napoleon-gate`

**What phase must accomplish:**
- Add missing class contract docstrings with constructor `Args:` when needed.
- Add missing function sections only when semantically required.
- Add all required `#:` comments for module globals, class attributes, and instance attributes assigned in `__init__`.
- Keep docs concise and human-readable; no placeholder sections.

**Acceptance criteria:**
- `make napoleon-gate` passes with zero violations.

## Phase 6: Final Whole-Repo Verification and Fallout

**Objective:** Prove repo is actually green and close out any regressions from prior phases.

**Commands:**
- `.venv/bin/ruff check deployfish tests`
- `.venv/bin/mypy deployfish tests`
- `make napoleon-gate`
- targeted pytest for touched hotspots

**Acceptance criteria:**
- All three quality gates pass.
- Targeted tests for touched domains pass.
- Any remaining risk is documented explicitly.

## Operating Rules

- Do not weaken global lint/type settings to “make green” cheaply.
- Prefer direct product-code fixes over workarounds.
- Use `apply_patch` for manual edits.
- Re-run verification after each meaningful batch.
- If a phase uncovers a design bug that forces broad API changes, stop and update this plan before continuing.
