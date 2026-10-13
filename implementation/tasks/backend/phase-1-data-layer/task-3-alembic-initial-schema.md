# task-3 — Alembic setup + `001_initial_schema`   ·   [backend / phase-1-data-layer]

| Field | Value |
|-------|-------|
| **Status** | `verified` |
| **Repo** | `Sentinel` (backend) |
| **Phase branch** | `dev/backend-phase-1-data-layer` |
| **Commit prefix** | `feat:` |
| **Arch refs** | architecture/backend.md §5.3 (schema), §5.5, §13.3, §13.5 step 3 |
| **Depends on** | [[task-2-asyncpg-database-pool]] |
| **Referenced by** | [[task-4-seed-services-migration]], all memory/tool tasks |

## Spec
`alembic init` + the initial migration creating the extension, 3 tables, and indexes exactly
per §5.3.

**Files created:** `alembic.ini`, `alembic/env.py` (async engine), `alembic/versions/001_initial_schema.py`
- `CREATE EXTENSION IF NOT EXISTS vector`.
- `incidents` (all columns incl. `root_cause_confidence REAL`, `resolution_type`, `pr_number`, `pr_url`, `trajectory JSONB`, `eval_score JSONB`, `langfuse_trace_id`, `reflexion_loops`, `mttr_seconds`, `embedding VECTOR(384)`).
- `services` (name unique, team, tier, dependencies JSONB, runbook, metadata, embedding VECTOR(384)).
- `deployments` (service, pr_number, commit_sha, author, deploy_status, gha_run_id BIGINT, dd_deploy_event_id, files_changed JSONB, incident_id UUID FK→incidents, deployed_at, metadata).
- Indexes: status, service, correlation, ivfflat(incidents.embedding lists=10), ivfflat(services.embedding lists=5), deployments service/incident/commit.

## Prerequisites
- [ ] task 1.2 pool. [ ] local pgvector container.

## Acceptance Criteria
- [ ] `alembic upgrade head` on a fresh pgvector DB creates extension + 3 tables + all indexes; `downgrade` reverses.
- [ ] Column types/names match §5.3 exactly (conformance-checked).
- [ ] The migration that creates `deployments` also runs `GRANT INSERT, SELECT ON deployments TO "gha-app"` (guarded by `IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'gha-app')` so a local DB without the role still migrates). Only the table owner can grant, and that is the migration's role. Afterwards `Sentinel-infra/scripts/grant-db-access.sh` verifies it (decision 2026-10-05, R12).

## Tests
- **Integration (`tests/test_infra/test_migrations.py`):** upgrade against local container, assert tables/columns/indexes via `information_schema` + `pg_indexes`; downgrade clean.
- **Quality gate:** `--repo backend`.

## How to Verify (phase gate)
1. `alembic upgrade head` on local pgvector → 3 tables.
2. `\d+ incidents` shows the vector column + ivfflat index.

## Report   ·   _filled on completion_
Built (commit 75564fa, `feat: alembic setup + 001_initial_schema`): §5.3 DDL verbatim — vector extension, 3 tables, 8 indexes (ivfflat lists 10/5). gha-app grant guarded on role existing (closes R12; verified has_table_privilege INSERT+SELECT plus a real INSERT as gha-app). Pipeline INSERT shape proven for succeeded/failed/rolled_back. Downgrade keeps the extension (shared server-wide). env.py uses asyncpg async_creator; DSN from config.attributes, env, or .env. Run via `poetry run alembic upgrade head` (not wired into startup). conftest now runs `alembic upgrade head` on the test DB.
Files: alembic.ini, alembic/env.py, alembic/script.py.mako, alembic/versions/001_initial_schema.py, tests/test_infra/test_migrations.py, tests/conftest.py, pyproject.toml, CONVENTIONS.md, .env.example.
Follow-ups: Dockerfile must COPY alembic/ (§13.5 step 9, phase 7). After 1.3 is live on Azure, re-run Sentinel-infra/scripts/grant-db-access.sh to verify the grant.

**Tests / gate:** VERDICT GREEN · 7 ran · env GROQ_API_KEY=fake-key-for-ci, DATABASE_URL=local pgvector container. Tree clean, attribution none.

**How to verify:** with GROQ_API_KEY=fake-key-for-ci and DATABASE_URL set to local pgvector: `poetry run alembic upgrade head` (3 tables), then `\d+ incidents` (vector column + ivfflat index); `poetry run alembic downgrade base` reverses.

## BLOCKED
_none locally. Azure `alembic upgrade head` (infra §10 step 10) ⛔ B1 — separate from this task._
