# task-1 — Add Phase-2 deps (asyncpg, pgvector, alembic, langfuse)   ·   [backend / phase-1-data-layer]

| Field | Value |
|-------|-------|
| **Status** | `done-pending-review` |
| **Repo** | `Sentinel` (backend) |
| **Phase branch** | `dev/backend-phase-1-data-layer` |
| **Commit prefix** | `feat:` |
| **Arch refs** | architecture/backend.md §11, §13.5 step 1 |
| **Depends on** | — |
| **Referenced by** | all backend phases |

## Spec
Add Phase-2 dependencies; do NOT remove Phase-1 deps yet (§13.5 keeps Phase 1 working until
Phase 2 is proven — removal is Phase 9).

**Files modified:** `pyproject.toml` — add `asyncpg`, `pgvector`, `alembic`, `langfuse`,
ensure `httpx`. Keep `aiosqlite`/`numpy` for now. Update lockfile.

## Prerequisites
- [ ] Python 3.12 env. [ ] Package manager per repo (Poetry or pip — match existing).

## Acceptance Criteria
- [ ] New deps resolve and install cleanly; app still imports and boots (Phase-1 intact).
- [ ] Lockfile regenerated (per CLAUDE.md post-implementation check).

## Tests
- **Unit:** existing suite still green. **Boot check:** `sentinel serve` / `uvicorn sentinel.main:app` starts (CLAUDE.md non-negotiable startup check).
- **Quality gate:** `--repo backend` (ruff · pyright · pytest · pip-audit).

## How to Verify (phase gate)
1. `pip install -e ".[dev]"` (or `poetry install`) succeeds.
2. App boots without import errors; `pytest -q` green.

## Report   ·   _filled on completion_
Built: Phase-2 deps added (asyncpg, pgvector, alembic, langfuse v3, sqlalchemy[asyncio]); pip-audit added to dev group; requires-python now >=3.12,<4.0 (langfuse). Commits 3fcfd6e (feat: add Phase-2 deps) + 679343e (fix(deps): clear pip-audit advisories). Files: pyproject.toml, poetry.lock.
User decision 2026-10-10: upgrade pre-existing vulnerable deps inside 1.1 (aiohttp, anyio, cryptography, fsspec, litellm, mcp, multidict, pyasn1, pydantic-settings, pyjwt, python-multipart, sentence-transformers, setuptools, starlette/fastapi 0.143.0, torch, transformers, urllib3). No ignores; openai-agents held at 0.6.4.
Follow-ups: Dockerfile `pip install .` ignores poetry.lock (task 7.1); local Sentinel/.env GROQ_API_KEY empty, so local gate/boot need a dummy key.

Tests: gate VERDICT GREEN, 7 ran, 0 skipped (pip-audit: no known vulnerabilities), run with GROQ_API_KEY=fake-key-for-ci. 1527 tests pass; `sentinel serve` boots.

Verify: `poetry install`; `GROQ_API_KEY=fake-key-for-ci poetry run pytest -q`; `GROQ_API_KEY=fake-key-for-ci poetry run sentinel serve`; `python3 scripts/gate.py backend`.

## BLOCKED
_none — local._
