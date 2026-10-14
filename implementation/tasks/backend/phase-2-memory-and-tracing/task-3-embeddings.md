# task-3 — `memory/embeddings.py` (pgvector `<=>`)   ·   [backend / phase-2-memory-and-tracing]

| Field | Value |
|-------|-------|
| **Status** | `verified` |
| **Repo** | `Sentinel` (backend) |
| **Phase branch** | `dev/backend-phase-2-memory-and-tracing` |
| **Commit prefix** | `refactor:` |
| **Arch refs** | architecture/backend.md §13.2, §13.4 (numpy removal deferred) |
| **Depends on** | [[task-1-phase2-dependencies]] |
| **Referenced by** | [[task-1-episodic-memory]], [[task-2-semantic-memory]], [[task-4-seed-services-migration]] |

## Spec
Keep the local embedding model (all-MiniLM-L6-v2, 384-dim); move similarity to the DB
(pgvector `<=>`) instead of numpy cosine. This module now only produces embeddings.

**Files modified:** `src/sentinel/memory/embeddings.py`
- `embed(text) -> list[float]` (384) via sentence-transformers, model name from config.
- Remove numpy cosine helpers (numpy dep formally dropped in Phase 9; if ST needs it transitively, keep as transitive only).
- Cache the model instance; async-safe wrapper if the encode is sync (run in threadpool).

## Prerequisites
- [ ] task 1.1 deps. [ ] embedding model downloadable (first run pulls weights).

## Acceptance Criteria
- [ ] `embed()` returns a 384-float vector; deterministic for the same input.
- [ ] No cosine-in-Python similarity remains here (moved to pgvector in memory modules).

## Tests
- **Unit (`tests/test_memory/test_embeddings.py`):** vector length 384; two similar strings closer than a dissimilar one (compare via dot product for the assertion only).
- **Quality gate:** `--repo backend`.

## How to Verify (phase gate)
1. `pytest tests/test_memory/test_embeddings.py -q` green.
2. `python3 scripts/gate.py backend` (from brain) -> VERDICT GREEN.

## Report   ·   _filled on completion_
Built (2b7ae05, `refactor: embeddings produce vectors only; one model load per process`): embeddings now produce vectors only; process-wide model cache keyed by name under a lock; encode via asyncio.to_thread (keeps contextvars/OTel). 384-dim unit vectors. EmbeddingClient API unchanged (alembic 002 and conftest depend on it). No numpy cosine remained here; episodic.py's numpy cosine is task 2.1's job.
Files: src/sentinel/memory/embeddings.py, tests/test_memory/test_embeddings.py. Backend boot proven.

**Tests / gate:** VERDICT GREEN, 7 ran (env -i, only TEST_DATABASE_URL); tree clean, attribution none. 11 tests added.

## BLOCKED
_none (first run downloads model weights ~90 MB)._
