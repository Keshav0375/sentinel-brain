# task-1 — `POST /webhooks/incident` receiver   ·   [backend / phase-5-api]

| Field | Value |
|-------|-------|
| **Status** | `done-pending-review` |
| **Repo** | `Sentinel` (backend) |
| **Phase branch** | `dev/backend-phase-5-api` |
| **Commit prefix** | `feat:` |
| **Arch refs** | architecture/backend.md §3.1, §4.5 (concurrency), §2 (correlation) |
| **Depends on** | [[task-2-orchestrator-loops]], [[task-1-episodic-memory]], [[task-5-app-lifespan-and-concurrency]] (lifespan/pool), [[task-6-entra-bearer-auth]] (`require_incident_write`) |
| **Referenced by** | [[task-3-ci-incident-response]] (caller), [[task-2-incident-query-endpoints]] (poll) |

> ⚠ **rev-5 (2026-07-12):** (a) auth is Entra bearer via `require_incident_write` (task 5.6),
> **not** `X-Sentinel-Token`; (b) the payload carries **`signal_type`** (`deploy_failure` |
> `runtime_error`) which the orchestrator branches on — deploy_failure → rollback fast path,
> runtime_error → full pipeline. See sentinel §3.1.

> ⚠ **Payload contract (2026-08-23, from infra 3.3):** `client_payload` carries exactly
> three top-level keys — `signal_type`, `correlation_id` (Event Grid event id, stable
> across re-deliveries → dedupe on it), and **`event`** holding the full Datadog payload.
> Read Datadog fields as `client_payload.event.*`, NOT flat: GitHub caps client_payload at
> 10 top-level properties, so the flat passthrough the architecture once showed cannot
> exist.

## Spec
The webhook that triggers the pipeline. Accepts the GHA-enriched payload, launches an
isolated asyncio task per incident, returns 202 immediately.

**Files created/modified:** `src/sentinel/api/webhooks.py`
- `IncidentPayload` Pydantic model per §3.1 (source, alert_id, dd_event_id, correlation_id, **signal_type**, title, severity, tags{service, deploy_status, failed_stage, version}, context{service_metadata, pr_details, recent_logs}, timestamp, raw_payload).
- `POST /webhooks/incident` (dep: `require_incident_write`) → generate `incident_id`, spawn `handle_incident` task with its own ShortTermMemory + LangFuse trace (§4.5), passing `signal_type` for the two-case branch, return 202 `{incident_id, correlation_id, status:"accepted"}`.
- Store terminal incident to episodic memory on completion.

## Prerequisites
- [ ] Phase-4 orchestrator, episodic memory, lifespan/pool (5.5), **Entra bearer dep (5.6)**.
- [ ] fake LLM for tests; a way to mint/stub an `Incident.Write` token for the 401/200 cases.

## Acceptance Criteria
- [ ] 202 with incident_id; pipeline runs as an independent task (concurrent incidents isolated).
- [ ] **401 without a valid Entra bearer** (missing, wrong audience, expired, or no `Incident.Write`
      role); correlation_id echoed on success.
- [ ] `signal_type` is required and drives the two-case branch (`deploy_failure` → rollback fast
      path, `runtime_error` → full pipeline).
- [ ] Terminal incident persisted with trajectory + resolution_type.

## Tests
- **Integration (`tests/test_api/test_webhooks.py`, fake LLM):** POST canned payload with a stubbed valid bearer → 202; poll shows stored incident; **no/invalid bearer → 401**; both `signal_type` values take their documented branch; two concurrent POSTs isolated.
- **Quality gate:** `--repo backend` (this file runs under `pytest-integration`).

## How to Verify (phase gate)
1. `pytest tests/test_api/test_webhooks.py -q` green.
2. ```bash
   TOKEN=$(az account get-access-token --resource api://sentinel-backend --query accessToken -o tsv)
   curl -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
        -d @sample.json "$BACKEND_URL/webhooks/incident"
   ```
   → 202 then a stored incident. Repeat without the header → 401.

## Report   ·   _filled on completion_
Built `POST /webhooks/incident` (backend commit ac630a0, plus 360496a `fix(deps): certifi 2026.10.19` for unrelated advisory PYSEC-2026-4320). 25 files, ~41 tests.
- Replaces the Phase-1 `/webhooks/alert`, AlertDeduplicator and AlertAck.
- `IncidentPayload` requires signal_type/correlation_id/title; tags as object or comma string; severity/alert_id/service default "unknown".
- Duplicate correlation_id -> 202 with the original incident_id, status `duplicate`.
- One task per incident with its own STM; fast path pinned to `context.pr_details.sha` (7-char prefix rule); on rollback_proposed `deployments.incident_id` is backfilled.

Review fixes 2026-10-21 (d0f7ae9..d27a8f3, status stays done-pending-review): d9ead3f IncidentTasks (concurrency cap 429, drain, 503, task error logging); 31a79b0 body cap 413 + bounded alert context; 05a1bda per-incident pipeline timeout; d27a8f3 503 on shutdown during the dedupe lookup, nothing recorded. Gate on d27a8f3: VERDICT GREEN (full run, 7 ran, 0 skipped, TEST_DATABASE_URL set); boot OK (/health 200, /ready 200, protected 401, clean exit).

## Tests
Gate: VERDICT GREEN (7 ran; orchestrator, env -i + TEST_DATABASE_URL, at 360496a). Tree clean, no attribution.

## How to Verify
1. `pytest tests/test_api/test_webhooks.py -q` green.
2. `TOKEN=$(az account get-access-token --resource api://sentinel-backend --query accessToken -o tsv)`; `curl -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d @sample.json "$BACKEND_URL/webhooks/incident"` -> 202 then a stored incident; without the header -> 401.

## BLOCKED
_none locally (fake LLM + local pgvector)._
