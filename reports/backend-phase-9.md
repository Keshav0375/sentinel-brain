# backend phase 9 — Cleanup & End-to-End

| | |
|---|---|
| **Repo** | `Sentinel` |
| **Branch → PR** | `dev/backend-phase-9-cleanup` → `release-phase-2` · PR #28 — https://github.com/Keshav0375/Sentinel/pull/28 |
| **Tasks** | 2/2 green (VERDICT GREEN on 3f7cdd3, full run; boot OK) |
| **Gate** | ⬜ awaiting sign-off |

Reviews: architecture CONFORMS (1 round) · code LGTM (1 round) · safety SAFE (branch-in-prompt finding promoted to a blocker and fixed in 3f7cdd3).

## What shipped

- **9.1 Remove Phase-1 artifacts** — Phase-1 data, generator, SQLite, models, scripts and SSE are gone; `/api/scenarios` serves the vendored catalog read-only; numpy and pytest-timeout are dev-only.
- **9.2 End-to-end integration** — an offline e2e smoke covers both paths, and each terminal incident writes one item to the LangFuse dataset `sentinel-scenario-runs`. The write runs in the background (DatasetWrites, 10 s timeout, drained at shutdown). `pr_details.branch` is eval metadata only and is kept out of every agent prompt.

## What this unblocks

- The live demo ([DEMO.md](DEMO.md)) and `scripts/run_eval.py` scoring over real runs.
- The final `release-phase-2` → `main` merge, which closes Phase 2.

## See it working

1. `cd ../Sentinel && poetry run sentinel serve` → `/health` and `/ready` 200, protected routes 401
2. `poetry run pytest -q tests/test_e2e` → green, no outbound network
3. `grep -r "sentinel.generator\|infra.db\|data/scenarios" src/ tests/` → no hits
4. `curl -H "Authorization: Bearer $TOKEN" localhost:8000/api/scenarios` → 30 entries

## Not done / blocked

- **(a) The live demo has not been run.** It needs the estate up, the infra CI-identity ticket, REVERT_PR_PAT and real LLM keys. Runbook: [DEMO.md](DEMO.md).
- **(b) EventBus/DashboardEventEmitter have no subscriber.** They are kept per decision 2026-10-15; removing them needs a decision.
- **(c) The filelock pip-audit ignore expires 2026-11-24.**
- **(d) NEXT:** the user-authorized final merge of release-phase-2 → main (back up main to main-backup first), the monorepo infra move, and backend phase 10 (Ops Dashboard).
- **Skipped checks:** none.

## Decisions made during the build

- 3c492de, 9320bb1: keep `scripts/run_eval.py`; the dashboard is a read-only catalog (no Fire button, no live view).
- b0fa4a4: the terminal-state dataset item feeds the eval.
- 8e763a0: SSE is removed; the branch is eval-only metadata; the dataset write is off the critical path.
- 934fe7d: numpy and pytest-timeout are dev-only deps.
