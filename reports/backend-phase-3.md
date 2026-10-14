# backend phase 3 — Tools Rewrite

| | |
|---|---|
| **Repo** | `Sentinel` |
| **Branch → PR** | `dev/backend-phase-3-tools` → `release-phase-2` · PR #21 — https://github.com/Keshav0375/Sentinel/pull/21 |
| **Tasks** | 7/7 green |
| **Gate** | ⬜ awaiting sign-off (VERDICT GREEN at 7550eab) |

## What shipped

- **3.1 config** — tool configuration (`0800159`).
- **3.2 get_service_metadata** — read-only service metadata (`63fc81f`).
- **3.3 search_past_incidents** — past-incident search (`765ec48`).
- **3.4 fetch_logs** — Datadog logs, parallel with 45s deadline and partial results (`5423739`).
- **3.5 get_deploy_details** — GitHub deploy details, with retry (`453e1d2`).
- **3.6 prepare_rollback_spec + format_escalation** — pure drafting tools (`fc89e7f`).
- **3.7 removal** — comms/hitl/approval plumbing deleted (`87b4a11`).
- **Review fixes** (`c2916c8..7550eab`): CorrelatedDeploy, compact JSON outputs, untrusted-data preamble on every prompt, size caps, repo regex, orchestrator budget 20.

## What this unblocks

- Phase 4 agent work consumes the six read-only/pure tools via the registry.

## See it working

1. `docker start sentinel-pg-test`
2. `TEST_DATABASE_URL=... pytest tests/test_tools -q` → expect 7 ran, 0 skipped
3. Registry six-tool check → expect exactly six tools
4. Removal grep → expect nothing
5. `DATABASE_URL= poetry run sentinel serve` → expect it boots

## Not done / blocked

- **Live checks** — need user's scoped read-only DD app key (logs_read_data + synthetics_read), GitHub PAT (Pull requests: read), Sentinel/.env with DD_SITE=us5.datadoghq.com.
- **Carried:** 4.2 real tool-call counter that escalates; 4.x/5.x cross-check RollbackSpec.target_deploy; 5.x/6.x PUT /api/config unauthenticated, judge model still the triage model; 4.x Langfuse prompt path needs the preamble; phase 4 IncidentSummary 'pending_approval' status.
- **Notes:** direct-push deploy omits pr_number in JSON; GitHub ConnectError not retried; non-Datadog exception in fetch_logs collect escapes raw.

## Decisions made during the build

- Brain 2026-10-14 "phase 3 (tools) contract" (8212b96, amended 6bf8a82); carried requirements 128e63f, d829861.
