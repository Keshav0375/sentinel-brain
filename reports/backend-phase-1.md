# backend phase 1 — Data Layer Foundation

| | |
|---|---|
| **Repo** | `Sentinel` |
| **Branch → PR** | `dev/backend-phase-1-data-layer` → `release-phase-2` · PR #19 — https://github.com/Keshav0375/Sentinel/pull/19 |
| **Tasks** | 4/4 green |
| **Gate** | ⬜ awaiting sign-off (gate-runner GREEN at 9a61e49, TEST_DATABASE_URL set, 736 integration tests) |

## What shipped

- **1.1 Dependencies** — backend deps added, vulnerable ones upgraded after pip-audit (user-approved).
- **1.2 Pool** — asyncpg pool created inside the lifespan try/finally; `.env.example` added.
- **1.3 Alembic + 001** — migration framework and the first schema migration.
- **1.4 Migration 002** — seed data (services row), no Settings dependency.

Reviews: architecture-warden CONFORMS; code-reviewer 2 blockers + 6 warnings, all fixed, re-review LGTM; safety-reviewer SAFE, 2 warnings fixed.

## What this unblocks

- Phase 2 can use the pool, the schema and the seeded services row.

## See it working

1. ```bash
   docker start sentinel-pg-test
   ```
   → container up (or use the docker run line)
2. Run the gate with TEST_DATABASE_URL set → VERDICT GREEN
3. ```bash
   DATABASE_URL=postgresql://postgres:test@localhost:55432/sentinel poetry run alembic upgrade head
   ```
   → migrations 001, 002 applied
4. psql check of the services row → seeded row present
5. `poetry run sentinel serve` with DATABASE_URL at the container → `db_pool_created`

## Not done / blocked

- Rewrite §6.2/§4.5 to the Langfuse v3 API before backend phase 2.
- Dockerfile ignores poetry.lock and must COPY alembic/ (phase 7).
- Service lookups must not rely on ivfflat at probes=1.
- 002 embeds even in `--sql` offline mode.
- `_backend_count` test baselines can flake under concurrent sessions.
- Local Sentinel/.env has a stale DATABASE_URL placeholder and empty GROQ_API_KEY.
- After next Azure apply: `alembic upgrade head` (Entra token via PGPASSWORD), then re-run Sentinel-infra/scripts/grant-db-access.sh to verify the gha-app grant.
- Deferred deployment live smoke (pass/01, deployfail/03, runtime/01, runtime/07) still pending.
- **Skipped checks:** CI's new pgvector job validated by actionlint only; first real CI run proves it.

## Decisions made during the build

- 2026-10-10: sentinel-watchtower-only registry; Langfuse v3; SentinelMemoryError.
- User-approved dependency upgrades in 1.1.
- R12 closed 2026-10-09.
- Gate change fb0c8eb: backend run without TEST_DATABASE_URL is PARTIAL.
