# task-4 — `ci_backend_scale.yml` (scale toggle + nightly)   ·   [backend / phase-8-cicd]

| Field | Value |
|-------|-------|
| **Status** | `done-pending-review` |
| **Repo** | `Sentinel` (backend) |
| **Phase branch** | `dev/backend-phase-8-cicd` |
| **Commit prefix** | `feat:` |
| **Arch refs** | architecture/backend.md §8.5 (safety net), §9.5 |
| **Depends on** | [[task-3-composite-actions]] |
| **Referenced by** | scale-to-zero safety + live demo prep |

## Spec
Manual up/down toggle + nightly auto-down safety net for scale-to-zero (§8.5 rule 4).

**Files created:** `.github/workflows/ci_backend_scale.yml` — name `[sentinel] backend — scale`; `workflow_dispatch` (input `direction: up|down`) + nightly cron `0 2 * * *` (down).
- `up` → `backend-up` (outputs URL for the session); `down` → `backend-down`.
- Nightly always scales to zero (forgotten KEEP_WARM costs at most one night).

## Prerequisites
- [ ] task 7.3 actions. [ ] ⛔ B1 (AKS) for live scaling.

## Acceptance Criteria
- [ ] Validates; dispatch up/down works; nightly cron scales to zero; uses the shared actions.

## Tests
- **Lint:** actionlint, yamllint.
- **Integration (⛔ B1):** dispatch `up` → node/replicas 1 + reachable URL; `down` → 0; cron scheduled.
- **Quality gate:** `--repo backend`.

## How to Verify (phase gate — end of Category 3 Phase 8)
1. actionlint clean.
2. (with AKS) `up` brings the backend online, `down` scales to zero; nightly cron visible in Actions.

## Report   ·   _filled on completion_
Built `ci_backend_scale` workflow: manual up/down toggle plus nightly scale-to-zero cron; cron always scales down, never stops the cluster. Commit e0e8335. Files: workflow, tests/test_infra/test_workflow_scale.py (21 tests). Gate: VERDICT GREEN on e0e8335 (full run, 7 ran, 0 skipped); boot OK (/health, /ready 200; protected routes 401). Not verified live (B1 + infra CI-identity ticket).

## BLOCKED
_Live scaling ⛔ B1. YAML + lint now._
