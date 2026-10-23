# task-5 — `main.py` lifespan + concurrency + token auth   ·   [backend / phase-5-api]

| Field | Value |
|-------|-------|
| **Status** | `verified` |
| **Repo** | `Sentinel` (backend) |
| **Phase branch** | `dev/backend-phase-5-api` |
| **Commit prefix** | `feat:` |
| **Arch refs** | architecture/backend.md §1.1 (routes), §3 (auth), §4.5 (concurrency) |
| **Depends on** | [[task-2-asyncpg-database-pool]], [[task-4-langfuse-tracing]], [[task-1-webhook-receiver]] |
| **Referenced by** | all API routes, [[task-1-ci-validation]] (boots the app) |

> ⚠ **rev-5 (2026-07-12):** auth changed. `X-Sentinel-Token`/`require_token` is **gone** —
> inbound auth is now Entra bearer, implemented in [[task-6-entra-bearer-auth]] (`require_incident_write`).
> This task now (a) wires the workload-identity Key Vault + PostgreSQL Entra-token access at
> startup, and (b) applies the **task-6** dependency to non-health routes. See sentinel §3.6 + §8.2.

## Spec
Wire the FastAPI app: lifespan (open asyncpg pool via **Entra DB token**, load LLM keys from
Key Vault via **workload identity**, init LangFuse at startup, close at shutdown), apply the
**Entra bearer** dependency (`require_incident_write`, task 5.6) to all non-health routes,
router registration, and structlog config.

**Files modified:** `src/sentinel/main.py`
- `lifespan` context: acquire Entra DB token + create pool (min/max from config), init KV client (workload identity), init LangFuse; teardown reverses.
- Apply `require_incident_write` (from `api/auth.py`, task 5.6) to webhooks/incidents/generate; `/health`+`/ready` exempt.
- Mount routers: webhooks, incidents, generate, health, eval.
- structlog bound with `incident_id` where applicable.

## Prerequisites
- [ ] tasks 1.2, 2.4, and the route tasks (5.1–5.4). [ ] eval router (Phase 6) may mount later — leave a stub or land after 6.x.

## Acceptance Criteria
- [ ] App boots cleanly (CLAUDE.md non-negotiable startup check) with pool + LangFuse initialized.
- [ ] Token enforced on protected routes; probes open.
- [ ] Graceful shutdown closes the pool (no leaked connections).

## Tests
- **Integration (`tests/test_api/test_app_boot.py`):** app starts; protected route 401 without token, 200 with; `/health` open; shutdown closes pool.
- **Boot check:** `uvicorn sentinel.main:app` starts with no import errors.
- **Quality gate:** `--repo backend`.

## How to Verify (phase gate — end of Category 3 Phase 5)
1. `uvicorn sentinel.main:app` boots; `/health` ok, protected routes require the token.
2. `pytest tests/test_api/ -q` green.

## Report   ·   _filled on completion_
Built in `d0f7ae9` (`feat: app lifespan: Entra bearer on every non-probe route, optional Key Vault secrets, PG* Entra-token pool`), `src/sentinel/main.py`.
- Entra bearer on every non-probe route; `/health`, `/ready`, `/docs`, openapi stay open (§3.6).
- Optional Key Vault (`KEY_VAULT_URL`) loads Datadog + Langfuse secrets before Langfuse init; LLM keys never read from the vault.
- PG* path uses an Entra-token password callable; `DATABASE_URL` wins. `SENTINEL_DEV_OPEN_DASHBOARD` opens only dashboard pages + read APIs.
- Lifespan no longer seeds SQLite; scenario CLI/scripts/eval still use it until 9.1. New azure deps: azure-identity 1.26.0, azure-keyvault-secrets 4.11.3, msal 1.39.0.
- Live boot: /health 200, /ready 200; /incidents, POST /webhooks/incident, POST /generate/pr-content, /api/config, / all 401 without token.

Review fixes 2026-10-21 (d0f7ae9..d27a8f3, status stays done-pending-review): ebca7f8 test_database counts only its own tagged pool; d9ead3f IncidentTasks (shared with 5.1); 09ab874 Key Vault doc (secrets read once at startup, restart to rotate); 354d722 Langfuse shutdown bounded by a 5s daemon thread. Gate on d27a8f3: VERDICT GREEN (full run, 7 ran, 0 skipped, TEST_DATABASE_URL set); boot OK (/health 200, /ready 200, protected 401, clean exit).

## Tests
50 tests, 7 ran in the integrated gate (env -i + TEST_DATABASE_URL). Gate: VERDICT GREEN. pip-audit clean.

## How to Verify
1. `cd ../Sentinel && poetry run sentinel serve` boots; `curl :8000/health` and `/ready` return 200.
2. `curl -i :8000/incidents` returns 401 without a token.
3. `pytest tests/test_api/ -q` green.

## BLOCKED
_none locally._
