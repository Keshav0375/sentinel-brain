# task-1 — 30 scenario branches + `scenarios/branches.yaml` catalog   ·   [deployment / phase-3-scenario-branches]

| Field | Value |
|-------|-------|
| **Status** | `in-progress` |
| **Repo** | `Sentinel-deployment` |
| **Phase branch** | `dev/deploy-phase-3-scenario-branches` |
| **Commit prefix** | `feat:` |
| **Arch refs** | architecture/deployment.md §4 (30 branches, 3 cases) + §4.1 (catalog) |
| **Depends on** | [[task-1-fastapi-app]], [[task-2-ci-app-deployment]], [[task-3-datadog-monitors]] |
| **Referenced by** | backend incident pipeline (signal_type) + eval runner (ground truth) |

> ⚠ **rev-5 (2026-07-12):** supersedes the old `ci_demo_prs.yml` + 14-PR (A/B/C) design.
> The demo app is now **real ground truth**; there is **no PR-faking workflow**. Scenarios
> are **30 real git branches** (10 per case), each with a fixed ground-truth label. The
> branch set doubles as the eval dataset (replaces Phase-1 synthetic scenario JSON).

## Spec
The binding catalog is **deployment.md §4.1**, which is exhaustive (redesigned 2026-10-07; read `python3 scripts/arch.py deployment 4.1`). Author 30 branches off `main` and the machine-readable catalog.

**Files created on the phase branch:**
- `scenarios/branches.yaml`: 30 entries with the §4.1 fields:
  - `branch`, `case`, `fault`
  - `expected_signal_type` (`none|deploy_failure|runtime_error`)
  - `expected_resolution` (`none|rollback|rollback_or_escalate`)
  - `expected_failed_stage` (case ii only)
  - `also_expected` (list)
  - `expected_culprit` (`self` / `none`)
- `scenarios/README.md`: how to run a scenario (merge the branch via PR, observe, revert the merge), detection latency (up to ~31 min for runtime; "Run test now" to speed it up), and that each must be reverted before the next.
- `datadog/synthetics/runtime-health-root.json`: add the `content-type` and `$.message == "ok"` assertions.
- `requirements-dev.txt`: pin PyYAML (and jsonschema if used) for the schema test.
- `tests/test_scenarios.py`:
  - schema: 30 entries, 10 per case, enums, `expected_failed_stage` iff case ii, `also_expected` ⊆ {runtime_error}
  - every branch exists on origin
  - its diff vs `main` touches `app/**` or `requirements.txt`
  - it applies cleanly
- The **30 branches**, each cut from `main` *after* the phase PR's catalog lands (or from the phase branch's base, see Notes). Each has exactly one focused commit implementing its §4.1 fault.

No `ci_demo_prs.yml`. No backend involvement. No `SENTINEL_API_URL`.

## Prerequisites
- [ ] Deploy phases 1–2 ✅. [ ] `gh` with repo write. [ ] Live estate only for the integration smoke (apply → grant → `datadog/apply.sh`).

## Acceptance Criteria
- [ ] `branches.yaml` validates; 30 entries, 10 per case, matching §4.1 exactly.
- [ ] Every branch exists on origin, applies cleanly to `main`, touches `app/**` or `requirements.txt`, and implements its catalogued fault (unit-checked locally where possible: e.g. `pass/*` keeps the test suite green; `runtime/*` passes `/health` + `/version` locally but fails its targeted check; `deployfail/*` reproduces its failure locally where it can).
- [ ] `GET /` synthetic asserts content-type + body.
- [ ] Live smoke (one per case, estate up): `pass/01` green with no alert; `deployfail/03` `failed_stage:deploy` and the previous version still serving; `runtime/01` green, then the `GET /` synthetic alerts and the bridge dispatches `runtime_error`.

## Tests
- **Lint:** `yamllint` on `branches.yaml`; assert each branch diff applies to `main`.
- **Integration:** deploy one per case (`pass/01`, `deployfail/01`, `runtime/01`) → assert the
  Datadog signal + `signal_type` the bridge would stamp (sentinel-infra §3.5).
- **Quality gate:** `--repo deployment`.

## How to Verify (phase gate)
1. `branches.yaml` schema-valid, 30 entries; a dry apply of a sample from each case produces the expected diff.
2. Deploy `deployfail/01` (previous version keeps serving; `deploy_failure` event) and `runtime/01`
   (green deploy, `runtime_error` after verify) → both reproduce the documented Datadog signal.

## Report   ·   _filled on completion_
_not yet implemented_

## BLOCKED
_End-to-end signal needs Category-2 phase-2 wired + Datadog/App Service live (B6). Branches + catalog writable now._
