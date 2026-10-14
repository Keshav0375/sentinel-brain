# task-1 — `memory/episodic.py` (asyncpg + pgvector)   ·   [backend / phase-2-memory-and-tracing]

| Field | Value |
|-------|-------|
| **Status** | `verified` |
| **Repo** | `Sentinel` (backend) |
| **Phase branch** | `dev/backend-phase-2-memory-and-tracing` |
| **Commit prefix** | `refactor:` |
| **Arch refs** | architecture/backend.md §5.2, §5.3, §13.2 |
| **Depends on** | [[task-2-asyncpg-database-pool]], [[task-3-embeddings]] |
| **Referenced by** | [[task-3-incident-search]], [[task-1-webhook-receiver]] (store), [[task-1-judge-langfuse-scores]] |

## Spec
Rewrite episodic memory to asyncpg + pgvector, keeping the existing `MemoryStore` protocol
(`memory/base.py`) — same interface, new implementation (§13.2).

**Files modified:** `src/sentinel/memory/episodic.py`
- `store_incident(...)` → INSERT into `incidents` (trajectory JSONB, embedding VECTOR(384), all correlation fields, mttr, reflexion_loops).
- `search_similar(embedding, k)` → `ORDER BY embedding <=> $1 LIMIT k` (ivfflat).
- `get(incident_id)`, `list(status/service filters)`.
- Provenance preserved (which incident/agent) per safety invariant.

## Prerequisites
- [ ] tasks 1.2, 1.3, 2.3. [ ] local pgvector.

## Acceptance Criteria
- [ ] Implements the `MemoryStore` protocol unchanged; all methods async + typed.
- [ ] Similarity search uses the pgvector `<=>` operator (not numpy scan).
- [ ] Round-trips a full incident row incl. trajectory + embedding.

## Tests
- **Integration (`tests/test_memory/test_episodic.py`):** store 3 incidents, similarity search returns nearest; filter by status/service.
- **Quality gate:** `--repo backend`. VERDICT GREEN: 7 ran, 1617 tests (env -i, only TEST_DATABASE_URL); tree clean, attribution none. 35 Postgres tests; boot proven with and without DATABASE_URL.

## How to Verify (phase gate)
1. `pytest tests/test_memory/test_episodic.py -q` green against local pgvector (set TEST_DATABASE_URL).
2. Store + search returns the expected nearest incident.

## Report   ·   _filled on completion_
Commit `fa71aa7` (refactor: episodic memory on asyncpg + pgvector) on `dev/backend-phase-2-memory-and-tracing`.
EpisodicMemory(pool | None, embedding_client); pool None raises SentinelMemoryError on every method. Incident ids are str(uuid4()); trajectory = {symptoms, timeline}; similarity via `<=>` under SET LOCAL ivfflat.probes=10, no numpy. Added search_by_embedding (MemoryQueryResult) and list_incidents(status, service, limit). incident_search reports "memory unavailable" instead of crashing. resolved_at written when the model has it.
Files: src/sentinel/memory/episodic.py, memory/short_term.py, tools/incident_search.py, tools/registry.py, main.py, eval/runner.py, scripts/run_scenario.py, models/incident.py, api/webhooks.py, plus tests (test_episodic, test_incident_search, test_runner, test_triage, test_registry, test_incident, test_webhooks).

## BLOCKED
_none locally._
