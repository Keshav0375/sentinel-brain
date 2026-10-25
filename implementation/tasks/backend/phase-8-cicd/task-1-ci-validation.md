# task-1 — `ci_validation.yml` (fast PR gate)   ·   [backend / phase-8-cicd]

| Field | Value |
|-------|-------|
| **Status** | `done-pending-review` |
| **Repo** | `Sentinel` (backend) |
| **Phase branch** | `dev/backend-phase-8-cicd` |
| **Commit prefix** | `feat:` |
| **Arch refs** | architecture/backend.md §9.1, §9.5 |
| **Depends on** | Phase-5 app boots, [[task-1-dockerfile-update]] |
| **Referenced by** | PR gate for all future backend PRs |

## Spec
Fast PR gate — quality + single-job build/run/test (no ACR, no AKS, stubbed LLM). **Single
runner rule** (§9.1/§13.6): build image, run container, pgvector service, tests all in ONE
job.

**Files created:** `.github/workflows/ci_validation.yml` — name `[sentinel] PR — validation`; `pull_request` to main (paths src/tests/pyproject/Dockerfile/azure).
- `run-quality`: ruff check + `ruff format --check` + `pyright src/`.
- `build-and-test` (needs run-quality; service pgvector/pgvector:pg16): docker build (local, no push) → `docker run` with local DB + `SENTINEL_FAKE_LLM=1` → poll `/health`+`/ready` → `pytest test_tools+test_models` (unit) → `pytest test_agents+test_api` (integration) → teardown (`if: always()`).
- Can use the ACR ci-runner image as `container:` once available (infra 4.2) — optional.

## Prerequisites
- [ ] actionlint. [ ] Phase-5 app + Dockerfile (7.1).

## Acceptance Criteria
- [ ] Validates under actionlint; single-job build/run/test; no ACR/AKS/external calls; FAKE_LLM deterministic; ~3–5 min.

## Tests
- **Lint:** actionlint, yamllint.
- **Integration:** open a PR → the gate runs green on a clean branch.
- **Quality gate:** `--repo backend` (its steps mirror `quality_gate.py --repo backend`).

## How to Verify (phase gate)
1. actionlint clean.
2. A test PR runs the gate to green (quality + build + tests, no cloud).

## Report   ·   _filled on completion_
Built `ci_validation.yml` PR gate (PRs into main and release-phase-2; read-only, no cloud, arm64 runner; one job: build, migrate, run, probe, pytest; always-teardown). `guard-main-source.yml` head_ref injection fixed via env (one documented shellcheck SC2254 disable). Commit 69efed0. Files: .github/workflows/ci_validation.yml, guard-main-source.yml, tests/test_infra/test_ci_validation_workflow.py (16 tests). Gate: VERDICT GREEN on e0e8335 (full run, 7 ran, 0 skipped); boot OK (/health, /ready 200; protected routes 401). Not verified live (B1 + infra CI-identity ticket).

Review fixes 0402b8e, 7b82bfe (2026-10-24): PR gate now runs tests/test_scripts + tests/test_infra with a pinned, checksum-verified actionlint; timeout-minutes set; ci.yml pinned too. All actions pinned by SHA (tests/test_infra/test_workflow_hardening.py). Gate: VERDICT GREEN on 7b82bfe (full run, 7 ran, 0 skipped); boot OK (/health, /ready 200; protected routes incl. rollback-spec 401). Decisions: 29edfa7, 8b72023, 61178fa, e1cdbf0. Status stays done-pending-review.

## BLOCKED
_none for authoring; live PR run needs the repo on GitHub (present)._
