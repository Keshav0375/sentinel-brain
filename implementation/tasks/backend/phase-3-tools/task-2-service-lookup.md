# task-2 — `get_service_metadata` → PostgreSQL   ·   [backend / phase-3-tools]

| Field | Value |
|-------|-------|
| **Status** | `verified` |
| **Repo** | `Sentinel` (backend) |
| **Phase branch** | `dev/backend-phase-3-tools` |
| **Commit prefix** | `refactor:` |
| **Arch refs** | architecture/backend.md §3 Tools, §4.8, §13.2 |
| **Depends on** | [[task-2-semantic-memory]], [[task-1-config-extensions]] |
| **Referenced by** | triage agent, orchestrator |

## Spec
Rewrite `get_service_metadata` to read the `services` table (was JSON seed). `@function_tool`,
typed I/O, read-only, no external state, structured error return (never raise raw).

**Files modified:** `src/sentinel/tools/service_lookup.py`
- Input `ServiceLookupInput{service_name}` → Output `ServiceMetadata{team, tier, dependencies, runbook, ...}` or structured `ToolError`.
- Uses injected semantic memory (DI, not singleton).

## Prerequisites
- [ ] tasks 2.2, 3.1, seeded services (1.4). [ ] local pgvector.

## Acceptance Criteria
- [ ] Returns metadata from Postgres; unknown service → structured not-found (no raise).
- [ ] Pydantic v2 I/O; read-only; docstring = tool description.

## Tests
- **Gate:** VERDICT GREEN, 7 ran (~28 tests incl. seeded DB), tree clean.
- **Unit (`tests/test_tools/test_service_lookup.py`):** known service returns metadata; unknown returns structured error; mocked/seeded DB.
- **Quality gate:** `--repo backend`.

## How to Verify (phase gate)
1. `pytest tests/test_tools/test_service_lookup.py -q` green.

## Report   ·   _filled on completion_
Built `get_service_metadata` on Postgres: returns typed `SemanticRecord` or `ToolFailure{tool,kind,message}` (not_found/unavailable/bad_input). Commit 63fc81f. Files: models/tools.py (new: ToolFailure, ServiceLookupInput), tools/service_lookup.py, tests (test_service_lookup, test_models/test_tools, test_semantic).

## BLOCKED
_none locally._
