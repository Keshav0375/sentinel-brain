# task-2 — `memory/semantic.py` (asyncpg)   ·   [backend / phase-2-memory-and-tracing]

| Field | Value |
|-------|-------|
| **Status** | `verified` |
| **Repo** | `Sentinel` (backend) |
| **Phase branch** | `dev/backend-phase-2-memory-and-tracing` |
| **Commit prefix** | `refactor:` |
| **Arch refs** | architecture/backend.md §5.2, §13.2 |
| **Depends on** | [[task-2-asyncpg-database-pool]], [[task-4-seed-services-migration]] |
| **Referenced by** | [[task-2-service-lookup]] |

## Spec
Rewrite semantic (service registry) memory to asyncpg PostgreSQL queries; same protocol.

**Files modified:** `src/sentinel/memory/semantic.py`
- `get_service(name)` → row from `services`.
- `search_services(embedding, k)` → pgvector similarity ("which service matches this symptom?").
- Typed dataclass/Pydantic return; async.

## Prerequisites
- [ ] tasks 1.2, 1.4 (seeded services). [ ] local pgvector.

## Acceptance Criteria
- [ ] Lookup-by-name + similarity search implemented against `services`.
- [ ] Protocol-compatible; no LLM call for lookup.

## Tests
- **Integration (`tests/test_memory/test_semantic.py`):** seed + lookup by name + symptom similarity returns expected service.
- **Quality gate:** `--repo backend`.
- Result: VERDICT GREEN, 7 ran (env -i, only TEST_DATABASE_URL); 46 tests; tree clean, attribution none.

## How to Verify (phase gate)
1. `pytest tests/test_memory/test_semantic.py -q` green (needs TEST_DATABASE_URL).

## Report   ·   _filled on completion_
Commit 3c8f2de `refactor: semantic memory on asyncpg + pgvector` (Sentinel).
Files: src/sentinel/memory/semantic.py, tools/service_lookup.py, main.py, eval/runner.py, scripts/run_scenario.py, tools/registry.py, models/{memory,service}.py (docstrings), tests (test_semantic, test_service_lookup, test_registry, test_triage, test_log_analyst, test_runner).
SemanticMemory(pool | None): pool None raises SentinelMemoryError; missing service is KeyError. Exact name lookup; search_services under SET LOCAL ivfflat.probes=5. metadata JSONB fills oncall_channel/description/repo_url; services.runbook parsed into ordered steps. Edge choices: store/delete stay NotImplementedError; NULL team -> "", invalid tier raises SentinelMemoryError; blank runbook = NULL.
Known: eval/run_scenario scenarios still name Phase-1 acme services (lookups "not found") until phase 4. Boot proven both ways.

## BLOCKED
_none locally._
