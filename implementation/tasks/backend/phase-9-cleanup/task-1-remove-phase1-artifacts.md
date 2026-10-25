# task-1 — Remove Phase-1 artifacts + deps   ·   [backend / phase-9-cleanup]

| Field | Value |
|-------|-------|
| **Status** | `done-pending-review` |
| **Repo** | `Sentinel` (backend) |
| **Phase branch** | `dev/backend-phase-9-cleanup` |
| **Commit prefix** | `refactor:` |
| **Arch refs** | architecture/backend.md §13.1 (delete), §13.4 (deps), §13.5 step 8 |
| **Depends on** | ALL prior backend phases `verified` (Phase 2 tools proven before deleting Phase 1) |
| **Referenced by** | [[task-2-end-to-end-integration]] |

## Spec
Delete the Phase-1 synthetic-data machinery now that Phase-2 is proven (§13.5 step 8 is
intentionally late).

**Files deleted (§13.1):** `data/` (all), `src/sentinel/generator/` (all 4), `src/sentinel/infra/db.py`, `scripts/run_scenario.py`, `scripts/run_eval.py`, `scripts/demo.py`, `docker-compose.yml`.
**Deps removed (§13.4):** `aiosqlite`; `numpy` (keep only if transitively required by sentence-transformers).
**Files modified:** `pyproject.toml` (drop deps), `Dockerfile` (already no `data/` from 7.1), any lingering imports.

## Prerequisites
- [ ] Every prior backend phase `verified`. [ ] grep confirms no runtime code imports `data/`, `generator/`, `db.py`, or removed scripts.

## Acceptance Criteria
- [ ] All listed paths removed; app boots; full suite green; no dangling imports.
- [ ] `aiosqlite` gone; `numpy` gone or transitive-only; lockfile regenerated.

## Tests
- **Boot check + full suite:** app starts; `pytest -q` green post-removal.
- **grep:** no references to deleted modules remain.
- **Quality gate:** `--repo backend` (pip-audit clean of removed deps).

## How to Verify (phase gate)
1. `grep -r "sentinel.generator\|infra.db\|data/scenarios" src/ tests/` → no hits.
2. App boots; `pytest -q` green; `pip show aiosqlite` → not installed.

## Report
Commit `8a55663` on `dev/backend-phase-9-cleanup`: "refactor: remove Phase-1 synthetic data, generator, SQLite and scripts; serve the scenario catalog".
- Deleted: `data/`, `src/sentinel/generator/`, `infra/db.py`, `api/events.py` (SSE `/events/{id}`, dashboard-only), `scripts/run_scenario.py`, `scripts/demo.py`, `docker-compose.yml`, Phase-1 tests.
- Kept: `scripts/run_eval.py` (decision 2026-10-25), alembic 001/002.
- `aiosqlite` removed (lock: aiosqlite + content-hash only); numpy transitive only. pyproject no longer includes `data/`; CLI serve-only; `config.sentinel_db_path` removed.
- Catalog: vendored `src/sentinel/catalog/branches.yaml` (git mv from eval fixture) + loader; `/api/scenarios` serves it read-only behind bearer. Dashboard is a read-only catalog (no Fire button, no live view).
- Decisions: 3c492de, 9320bb1.
- Follow-up: EventBus and DashboardEventEmitter have no subscriber; kept per decision 2026-10-15 (emitter as trace processor); removal needs a decision.

## Tests
Gate: VERDICT GREEN (full run, 7 ran, 0 skipped). Boot probe: /health and /ready 200, protected routes 401. arm64 image builds, serves /health with `--read-only --network none`, ships catalog (30 entries).

## How to Verify
1. `grep -r "sentinel.generator\|infra.db\|data/scenarios" src/ tests/` -> no hits.
2. `poetry run sentinel serve` boots; `pytest -q` green; `pip show aiosqlite` -> not installed.
3. `GET /api/scenarios` with bearer returns 30 catalog entries; without bearer 401.
