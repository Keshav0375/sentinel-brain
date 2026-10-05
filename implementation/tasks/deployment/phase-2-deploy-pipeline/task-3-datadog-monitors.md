# task-3 — Datadog monitors (deploy-failure + runtime-health)   ·   [deployment / phase-2-deploy-pipeline]

| Field | Value |
|-------|-------|
| **Status** | `in-progress` |
| **Repo** | `Sentinel-deployment` |
| **Phase branch** | `dev/deploy-phase-2-deploy-pipeline` |
| **Commit prefix** | `feat:` |
| **Arch refs** | architecture/deployment.md §6.3, §4 (A/B/C); master §2 |
| **Depends on** | [[task-2-ci-app-deployment]] (produces the events), infra [[task-2-event-grid-module]] + [[task-3-functions-bridge-module]] (webhook target) |
| **Referenced by** | backend [[task-3-ci-incident-response]] (triggered by these) |

## Spec
The two monitors that turn Datadog signal into a `repository_dispatch`. Defined as code
(Datadog Terraform provider OR versioned monitor JSON + apply script — pick one; document).

**Artifacts:**
- `sentinel-deploy-failure` — event monitor on `deploy_status:failed` (Condition C).
- `sentinel-runtime-health` — metric/HTTP monitor: App Service 5xx rate over threshold OR failed synthetic pings to `/` and `/health` (Condition B).
- Both notify the same webhook channel → Event Grid topic (infra 3.2 endpoint+key) → Function → dispatch.
- Monitor hygiene (§6.3): renotify OFF, recovery period, 5-min eval window on runtime monitor.
- **Files:** `datadog/monitors/*.json` (or `*.tf`) + `datadog/README.md` (webhook setup, tag→evidence-class mapping).

## Prerequisites
- [ ] `DD_APP_KEY` in `Sentinel-infra/.env` (owner adds it — the API key alone cannot create monitors). [ ] Estate applied (Event Grid topic + bridge Function exist).

**Decided 2026-10-05 (binding):**
- **Applied locally by the owner**, not CI: monitors + webhook are versioned JSON under `datadog/`, applied by an idempotent `datadog/apply.sh` (reads `DD_API_KEY`/`DD_APP_KEY`/`DD_SITE` from an `--env-file`, never echoes them; `--dry-run`). Re-run after every estate recreate — the Event Grid topic key changes.
- **Webhook contract:** a Datadog Webhooks-integration webhook `sentinel-event-grid` → the topic endpoint (`az eventgrid topic show … --query endpoint`), custom header `aeg-sas-key` (from `az eventgrid topic key list`, stored only in Datadog's webhook config). The body is **flat JSON** `{"title":"$EVENT_TITLE","tags":"$TAGS","alert_transition":"$ALERT_TRANSITION","link":"$LINK","alert_id":"$ALERT_ID","date":"$DATE"}`. The topic's **CustomEventSchema** input mapping (infra, amended 2026-10-05) wraps it, so Event Grid stamps `id`/`eventTime` and the bridge reads it as `data`.
- **Alert-only notify:** each monitor's message mentions `@webhook-sentinel-event-grid` inside `{{#is_alert}}…{{/is_alert}}` only — a recovery must never dispatch (the bridge would classify it `runtime_error`).
- **`sentinel-runtime-health` = Datadog Synthetics API tests** on `GET /` and `GET /health` of `DEPLOYED_APP_URL`, 1 managed location, every 5 min, alert when a test fails (any location) for the 5-min window; renotify off. No Azure integration.
- **`sentinel-deploy-failure`** = event monitor on `tags:deploy_status:failed service:sentinel-watchtower`; the alert payload carries `deploy_status:failed` so the bridge classifies `deploy_failure`.
- Record-stage failures (`stage:record`) are reported **without** `deploy_status:failed`, so they never fire this monitor.
- [ ] Deploy events already flowing (task 2.2) to test the event monitor.

## Acceptance Criteria
- [ ] Both monitors defined as code with the exact trigger conditions (C = deploy_status:failed event; B = 5xx/failed pings).
- [ ] Webhook wired to the Event Grid topic; tags let agents distinguish B vs C.
- [ ] Hygiene settings applied so demos fire predictably.

## Tests
- **Validate:** JSON/HCL lint; dry-run the monitor definition.
- **Integration (estate applied):** trigger a failed deploy → deploy-failure monitor fires → dispatch reaches sentinel repo. Break `GET /` (PR #11 style) → runtime-health fires.
- **Quality gate:** `--repo deployment`.

## How to Verify (phase gate — end of Category 2)
1. Monitor definitions validate.
2. (wired) a Condition-C PR fires `sentinel-deploy-failure`; a Condition-B PR fires `sentinel-runtime-health`; both produce an `incident-alert` dispatch in the sentinel repo Actions tab.

## Report   ·   _filled on completion_
_not yet implemented_

## BLOCKED
_⛔ B6 (Datadog) + infra Event Grid/Function. Definitions writable now._
