# task-2 — `eval/runner.py` → LangFuse datasets   ·   [backend / phase-6-eval]

| Field | Value |
|-------|-------|
| **Status** | `done-pending-review` |
| **Repo** | `Sentinel` (backend) |
| **Phase branch** | `dev/backend-phase-6-eval` |
| **Commit prefix** | `refactor:` |
| **Arch refs** | architecture/backend.md §6.1 (datasets), §13.2 |
| **Depends on** | [[task-1-judge-langfuse-scores]] |
| **Referenced by** | eval dashboard / regression testing |

## Spec
Rewrite the eval runner to work against LangFuse datasets (was iterating `data/` scenarios,
which are deleted in Phase 9) — run new prompt versions against historical trajectories.

**Files modified:** `src/sentinel/eval/runner.py`
- Pull a LangFuse dataset of past trajectories; re-run the pipeline (or judge) against each; aggregate scores; optional `GET /eval/results` data source (§1.1 route).
- No dependency on `data/scenarios/`.

## Prerequisites
- [ ] task 6.1 judge. [x] B7 closed 2026-09-13: LangFuse for real datasets (offline: a local fixture dataset for tests).

## Acceptance Criteria
- [ ] Runner iterates a dataset (fixture offline) and produces aggregate scores; no `data/` reference.
- [ ] Feeds the eval results endpoint.

## Tests
- **Integration (`tests/test_eval/test_runner.py`, fixture dataset + fake LLM):** runs, aggregates, returns a report.
- **Quality gate:** `--repo backend`.
- **Result:** ~40 tests (import ban, catalog, culprit binding, 4 ground-truth checks, offline dataset run, /api/eval-report, conflict exclusion, flush). Gate VERDICT GREEN, full run, 7 ran, 0 skipped; boot OK.

## How to Verify (phase gate — end of Category 3 Phase 6)
1. `pytest tests/test_eval/test_runner.py -q` green.
2. (B7 closed) run against a real LangFuse dataset → aggregate scores.

## Report   ·   _filled on completion_
Built commit 063c3d8 on dev/backend-phase-6-eval: "refactor: eval runner scores finished scenario runs from a LangFuse dataset against branches.yaml (#81)". Dataset `sentinel-scenario-runs` (item schema in runner docstring); scores go to a dataset-run trace; runner is read-only (dec 2026-10-22). Files: eval/runner.py, eval/report.py, models/eval_result.py, scripts/run_eval.py, README.md, pyproject.toml/poetry.lock (pyyaml>=6.0.0), tests/test_eval/fixtures/branches.yaml (vendored), tests.

## BLOCKED
_Resolved: B7 closed 2026-09-13; no longer blocking._
