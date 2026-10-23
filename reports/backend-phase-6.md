# backend phase 6 — Eval

| | |
|---|---|
| **Repo** | `Sentinel` |
| **Branch → PR** | `dev/backend-phase-6-eval` → `release-phase-2` · PR #24 — https://github.com/Keshav0375/Sentinel/pull/24 |
| **Tasks** | 2/2 green (done-pending-review) |
| **Gate** | ⬜ awaiting sign-off (VERDICT GREEN on cf56e67, full run, 7 ran, 0 skipped; boot OK) |

Reviews: architecture CONFORMS after 1 fix round (rubric blocker cleared) · code LGTM · safety SAFE. All warnings addressed.

## What shipped

- **6.1 Judge + LangFuse scores** — read-only judge scoring 0-1 per dimension, anchored on the branches.yaml fields; one LangFuse score per dimension; `judge_failed` flag stored in eval_score (never pushed or aggregated); untrusted-data preamble with `<trajectory>`/`<ground_truth>` tags.
- **6.2 Eval runner + datasets** — `scripts/run_eval.py` scores finished scenario runs from the LangFuse dataset `sentinel-scenario-runs` against branches.yaml, writes `/api/eval-report` data, and persists `incidents.eval_score` via `eval/score_store.py` (best effort, `--no-store` skips).

## What this unblocks

- Phase 7 can deploy a working scorer; the dashboard eval page and `/api/eval-report` have real data shape.

## See it working

1. `docker start sentinel-pg-test`
2. `cd ../Sentinel && poetry run pytest tests/test_eval -q`
3. Runner needs a LangFuse dataset, so there is no fully offline CLI run; the offline dataset path is covered by tests/test_eval/test_runner.py.

## Not done / blocked

- (a) Live eval needs real scenario runs: estate up, a human merging the scenario branch PRs, real LLM keys in Sentinel/.env (B4/B5).
- (b) score_store connects via DATABASE_URL only, not the Entra PG* path; off-cluster runner needs DATABASE_URL.
- (c) Vendored tests/test_eval/fixtures/branches.yaml must stay in sync with Sentinel-deployment/scenarios/branches.yaml.
- (d) eval_score JSONB gains a `judge_failed` key (implied by the amendment).
- From phase 5: 37s worst-case shutdown vs 30s grace period; phase 7 needs terminationGracePeriodSeconds >= 45.

## Decisions made during the build

- Judge is not wired into the live pipeline; the runner is the scorer, read-only, 0-1 scores (brain 1ffd083).
- Review amendments: dataset name, rubric anchors, judge_failed (brain a85666d).
