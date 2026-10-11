# task-4 — `002_seed_services` migration   ·   [backend / phase-1-data-layer]

| Field | Value |
|-------|-------|
| **Status** | `done-pending-review` |
| **Repo** | `Sentinel` (backend) |
| **Phase branch** | `dev/backend-phase-1-data-layer` |
| **Commit prefix** | `feat:` |
| **Arch refs** | architecture/backend.md §5.3 (services), §13.1 (replaces data/seed.py), §13.3 |
| **Depends on** | [[task-3-alembic-initial-schema]], [[task-3-embeddings]] (for embedding values — see note) |
| **Referenced by** | [[task-2-service-lookup]], triage flow |

## Spec
> **Amended 2026-10-10 (decision "Backend phase 1"):** seed exactly ONE row, `sentinel-watchtower` (team `sentinel`, tier `standard`, deps `[]`, metadata repo/platform, runbook = the revert-PR rollback procedure + pointer to `Sentinel-deployment/scenarios/README.md`, embedding at seed time). The Phase-1 acme-corp `service_map.json` is NOT seeded; it may only back test fixtures.

Seed the `services` table (replaces Phase-1 `data/services/*.json` + `seed.py`). Source the
service registry from the Phase-1 `service_map.json` content, mapped to columns: name, team,
tier, dependencies (JSONB), runbook (markdown), metadata, embedding(384).

**Files created:** `alembic/versions/002_seed_services.py`
- INSERT the known services with their dependencies/runbooks.
- Embedding: compute via the embedding model (all-MiniLM-L6-v2) at migration time, OR insert
  NULL and backfill in a follow-up if the model isn't importable in the migration context —
  **decide and document** (prefer computing so similarity search works immediately).

## Prerequisites
- [ ] task 1.3 schema. [ ] Phase-1 `data/services/*.json` still present (removed in Phase 9). [ ] embeddings util (task 2.3) if computing at seed time.

## Acceptance Criteria
- [ ] `alembic upgrade head` seeds all services with correct dependencies/runbooks/tier.
- [ ] Embeddings populated (or a documented backfill path), so `search services by symptom` returns matches.
- [ ] Idempotent-ish (ON CONFLICT (name) DO UPDATE or guarded).

## Tests
- **Integration:** upgrade → `SELECT count(*) FROM services` matches expected; a known symptom vector search returns the right service.
- **Quality gate:** `--repo backend`.

## How to Verify (phase gate — end of Category 3 Phase 1)
1. Fresh DB `alembic upgrade head` → services seeded.
2. Query one service by name; run a similarity search returning a sensible match.
Gate: VERDICT GREEN, 7 ran (run with `GROQ_API_KEY=fake-key-for-ci` and `DATABASE_URL` pointing at the local pgvector container). 8 tests in `tests/test_infra/test_migrations.py`, including the symptom query ranking `sentinel-watchtower` first via the ivfflat index.

## Report   ·   _filled on completion_
Built `002_seed_services` (Sentinel e26d733, `feat: 002_seed_services — seed sentinel-watchtower with its embedding`). Seeds exactly one row, `sentinel-watchtower`, with a revert-PR runbook and a MiniLM-384 embedding computed at seed time (decision: compute, no backfill). ON CONFLICT upsert, then REINDEX `idx_services_embedding`. Downgrade removes only that row. CI injects a fake embedding client, so the model is never downloaded.
Files: `alembic/versions/002_seed_services.py`, `tests/conftest.py`, `tests/test_infra/test_migrations.py`.
Follow-ups: (1) service lookups must not rely on IVFFlat returning all rows at probes=1 (use a name lookup or `SET ivfflat.probes`) — tools phase. (2) First `alembic upgrade head` on an operator machine downloads the ~90 MB model (`HF_HUB_OFFLINE=1` if cached). (3) Gate needs `GROQ_API_KEY` set in the caller env (local Sentinel/.env has it empty); make gate/test config set a dummy key.

## BLOCKED
_Dependency on embeddings util (2.3) if computing at seed time — otherwise seed with backfill. Note the ordering choice in Report._
