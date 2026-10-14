# backend phase 2 — Memory & Tracing Rewrite

| | |
|---|---|
| **Repo** | `Sentinel` |
| **Branch → PR** | `dev/backend-phase-2-memory-and-tracing` → `release-phase-2` · PR #20 — https://github.com/Keshav0375/Sentinel/pull/20 |
| **Tasks** | 4/4 green |
| **Gate** | ⬜ awaiting sign-off (VERDICT GREEN at 112e27f) |

## What shipped

- **2.3 Embeddings** — vector-only embeddings, one model load per process (2b7ae05).
- **2.1 Episodic memory** — rewritten on asyncpg + pgvector (fa71aa7).
- **2.2 Semantic memory** — rewritten on asyncpg + pgvector (3c8f2de).
- **2.4 Langfuse v3 tracing** — observe, prompt loading, scores (49e3534).
- **Review fixes** — pool try/finally, load_prompt via to_thread, NULL tier -> standard, provenance and "model-generated, unverified" labels, created_at kept, close_pool survives cancelled shutdown.

## What this unblocks

- Phase 3+ agents can read/write Postgres-only memory and emit Langfuse v3 traces and scores.

## See it working

1. ```bash
   docker start sentinel-pg-test
   ```
2. ```bash
   TEST_DATABASE_URL=<container url> pytest tests/test_memory tests/test_infra/test_tracing.py -q
   ```
   → expect: 7 ran, 0 skipped
3. ```bash
   DATABASE_URL=<container url> sentinel serve
   ```
   → expect: db_pool_created and langfuse_enabled in logs

## Not done / blocked

- Live Langfuse trace check pending: rename LANGFUSE_HOST -> LANGFUSE_BASE_URL in Sentinel/.env.
- R14 LLM token/cost capture (backend 4.x); Phase-1 smoke-/eval- ids not UUIDs (phase 4); from_model_name loads synchronously in async contexts.
- eval/run_scenario still name Phase-1 acme services (lookups "not found" until phase 4).
- Judge model is the triage model (self-grading): fix in phase 6.
- Earlier pending: deployment live smoke, guard-main-source.yml head_ref injection, Azure `alembic upgrade head` + grant-db-access verify.
- **Skipped checks:** none.

## Decisions made during the build

- 2026-10-12: Langfuse v3 API (a0ec214); Postgres-only memory + R14 deferred (e10d048); Phase-1 models to section 5.3 mapping (254f34e).
- 2026-10-14: review amendments (95a0744).
