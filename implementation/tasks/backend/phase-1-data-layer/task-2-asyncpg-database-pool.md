# task-2 — asyncpg pool `infra/database.py`   ·   [backend / phase-1-data-layer]

| Field | Value |
|-------|-------|
| **Status** | `verified` |
| **Repo** | `Sentinel` (backend) |
| **Phase branch** | `dev/backend-phase-1-data-layer` |
| **Commit prefix** | `feat:` |
| **Arch refs** | architecture/backend.md §4.5, §5.1, §13.3 |
| **Depends on** | [[task-1-phase2-dependencies]] |
| **Referenced by** | [[task-1-episodic-memory]], [[task-2-semantic-memory]], [[task-5-deploy-checker]], [[task-5-app-lifespan-and-concurrency]] |

## Spec
New `src/sentinel/infra/database.py` — asyncpg pool (parallel to old `db.py`, which stays
until Phase 9 per §13.5 step 2).

**Files created:** `src/sentinel/infra/database.py`
- `async def create_pool(dsn: str, *, min_size=2, max_size=10) -> asyncpg.Pool` (bounds from config).
- Register the `pgvector` codec on each connection (`pgvector.asyncpg.register_vector`).
- `@asynccontextmanager acquire()` helper; module-level pool holder set at lifespan startup, closed at shutdown.
- `from __future__ import annotations`, full type hints, structured logging.

## Prerequisites
- [ ] task 1.1 deps. [ ] Local `pgvector/pgvector:pg16` for tests.

## Acceptance Criteria
- [ ] Pool creates/acquires/releases; vector codec registered; min/max honored from config.
- [ ] Clean async lifecycle (no leaked connections); errors wrapped in `MemoryError` per exception hierarchy.

## Tests
- **Unit/integration (`tests/test_infra/test_database.py`):** against local pgvector container — acquire a conn, `SELECT 1`, round-trip a `vector(3)` value.
- **Quality gate:** `--repo backend`.

## How to Verify (phase gate)
1. `docker run -d --name sentinel-pg-test -e POSTGRES_PASSWORD=test -e POSTGRES_DB=sentinel -p 55432:5432 pgvector/pgvector:pg16`
2. `DATABASE_URL=postgresql://postgres:test@localhost:55432/sentinel GROQ_API_KEY=fake-key-for-ci poetry run pytest tests/test_infra/test_database.py -q` → green.
3. `poetry run sentinel serve` boots (DATABASE_URL blank or container).

## Report   ·   _filled on completion_
Built asyncpg + pgvector pool in `infra/database.py`: `create_pool(dsn, *, min_size, max_size, password=str|callable)`, `register_vector` via init, `acquire()` helper; lifespan opens pool only when DATABASE_URL is a Postgres URL. `SentinelError` hierarchy in `sentinel/exceptions.py`; added dev dep asyncpg-stubs.
Commits (Sentinel): 12bb1c2 feat: asyncpg + pgvector pool in infra/database.py; bdaa4dc fix: blank DATABASE_URL in .env.example; never-blank pool errors.
Files: src/sentinel/infra/database.py, exceptions.py, config.py, main.py, CONVENTIONS.md, tests/conftest.py, tests/test_infra/test_database.py, tests/test_config.py, pyproject.toml, poetry.lock, .env.example.
Notes: local Sentinel/.env has stale Azure placeholder DSN picked up by litellm load_dotenv; blank it or point at container. conftest session fixture creates vector extension until 1.3 alembic replaces it.

## Tests
Gate VERDICT GREEN, 7 ran, 31 tests (GROQ_API_KEY=fake-key-for-ci, DATABASE_URL=postgresql://postgres:test@localhost:55432/sentinel, container `sentinel-pg-test`). Tree clean, attribution none.

## BLOCKED
_none locally (uses local pgvector). Azure DB verify ⛔ B1 (not required for this task)._
