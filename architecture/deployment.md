# sentinel-deployment — Architecture Document

> **↑ Deep dive of the [Architecture Index](README.md).** Start there for the whole
> picture; this file is the authoritative detail for the **target app + ground-truth** concerns
> (index §4 map).

> **Purpose:** A near-trivial FastAPI app deployed to Azure App Service (F1 free tier)
> via GitHub Actions. It is the system's **real ground truth** — genuinely deployed,
> genuinely emitting logs and events to Datadog on every deploy. The **deployment
> pipeline** is the product; **30 pre-authored scenario branches** (§4) drive three
> outcomes — clean pass, deploy failure, and green-deploy-but-runtime-error — which
> land as real Datadog signal for Sentinel's agents to analyze and become the eval
> dataset. (Supersedes the old `ci_demo_prs.yml` template-PR model, now removed.)

---

## 1. System Overview

```
PR merged to main
       │
       ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     ci_app_deployment.yml (GHA workflow)                        │
│                                                                      │
│  ┌───────────┐    ┌───────────┐    ┌───────────┐                    │
│  │   BUILD   │───►│  DEPLOY   │───►│  VERIFY   │                    │
│  │ pip + zip │    │ az webapp │    │ /health   │                    │
│  │ package   │    │ deploy    │    │ /version  │                    │
│  └─────┬─────┘    └─────┬─────┘    └─────┬─────┘                    │
│        │                │                │                           │
│        ▼                ▼                ▼                           │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │             Datadog Events API + Log Intake API              │    │
│  │  Every stage reports: stage, status, version, error detail   │    │
│  └──────────────────────────────────────────────────────────────┘    │
│        │                                                             │
│        ▼                                                             │
│  ┌──────────────────┐                                                │
│  │  FINAL SUMMARY   │  (if: always())                                │
│  │  Datadog Event   │  title: "Deploy {succeeded|failed} PR #N"      │
│  │  + pipeline log  │  tags: version, stage, status                  │
│  └──────────────────┘                                                │
└──────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Azure App       │
                    │  Service (F1)    │
                    │  sentinel-watchtower  │
                    │  GET /health     │
                    │  GET /version    │
                    │  GET /           │
                    └──────────────────┘
```

**Key insight:** The deployment pipeline (GHA) is the thing being observed, not the
app. Every PR merge = one deploy attempt. Some succeed, some fail. Datadog accumulates
a real history of deployment events that Sentinel can later query for incident analysis.

**No Docker.** Azure App Service F1 (free tier) does not support container deploys.
The app is deployed as a zip package using `az webapp deploy`. Azure's Oryx build
system handles `pip install` from `requirements.txt` on the server side.

---

## 2. The App — Intentionally Minimal

The app exists only to be deployed to and verified against. No business logic.

### 2.1 Endpoints

| Method | Path | Response | Purpose |
|--------|------|----------|---------|
| `GET` | `/` | `{"message": "ok", "service": "sentinel-watchtower"}` | Basic hello-world |
| `GET` | `/health` | `{"status": "ok", "uptime_seconds": N}` | Deploy verification target |
| `GET` | `/version` | `{"version": "pr-47-a3f9c2", "service": "sentinel-watchtower"}` | Confirm which PR/SHA is live |

### 2.2 Startup Behavior

On boot, emit ONE structured log line to stdout:

```json
{
  "timestamp": "2026-07-01T12:00:00.000Z",
  "level": "info",
  "message": "app.startup",
  "app_version": "pr-47-a3f9c2",
  "dd.service": "sentinel-watchtower",
  "dd.env": "dev",
  "dd.version": "pr-47-a3f9c2"
}
```

The app doesn't talk to Datadog — the GHA pipeline does.

### 2.3 Tech Stack (app only)

```
# requirements.txt — what Oryx installs on App Service
fastapi==0.142.2
uvicorn==0.54.0
pydantic-settings==2.15.0
gunicorn==26.2.0

# requirements-dev.txt — local + CI only, never deployed
-r requirements.txt
pytest==9.1.1
httpx==0.28.1
ruff==0.16.10
```

Every dependency is pinned exactly (`==`) so a deploy is reproducible and only a scenario
branch can change what is installed. `gunicorn` is listed because the §2.5 start command
runs it; the App Service image happening to ship one is not relied on. Bumps are deliberate
PRs, never drift. (Decision 2026-10-04.)

### 2.4 App Config

```python
class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_version: str = "local-dev"
    dd_service: str = "sentinel-watchtower"
    dd_env: str = "dev"
    port: int = 8000
```

### 2.5 Azure App Service Startup

App Service F1 runs Python apps via Oryx. The startup command is configured in the
App Service settings:

```
gunicorn --bind=0.0.0.0 --timeout 600 -k uvicorn.workers.UvicornWorker app.main:app
```

Note: F1 uses shared compute. `gunicorn` with one uvicorn worker is the standard
Azure pattern for Python + async frameworks.

---

## 3. Deployment Pipeline — The Core of the Project

### 3.1 `ci_app_deployment.yml` — Triggered on PR merge to main

**Trigger:** `push` to `main` (fires after squash-merge from any PR)

Every stage reports its outcome to Datadog. Failures are never swallowed —
a failed build is just as visible in Datadog as a successful deploy.

#### Stage 1: Checkout + Metadata

```yaml
- Checkout repo
- Extract from merge commit / GHA context:
    PR_NUMBER   (from commit message or github.event)
    SHORT_SHA   (github.sha[:7])
    PR_TITLE    (from github.event.head_commit.message)
    APP_VERSION = "pr-${PR_NUMBER}-${SHORT_SHA}"
```

#### Stage 2: Build (zip package)

```bash
# Create deployment package
mkdir -p deploy_package
cp -r app/ deploy_package/app/
cp requirements.txt deploy_package/
cd deploy_package && zip -r ../deploy.zip . && cd ..
```

No Docker build — just package the app files + requirements.txt into a zip.
Azure's Oryx build system runs `pip install -r requirements.txt` on the server.

**On failure** (missing files, zip error):

```
POST https://api.${DD_SITE}/api/v1/events
{
  "title": "Build FAILED for PR #${PR_NUMBER}: ${PR_TITLE}",
  "text": "${BUILD_ERROR_OUTPUT}",
  "tags": ["version:${APP_VERSION}", "service:sentinel-watchtower", "env:dev",
           "stage:build", "deploy_status:failed"],
  "alert_type": "error"
}
```

#### Stage 3: Deploy

```bash
# Login to Azure — OIDC via azure/login@v2 as `gha-app` (secrets.AZURE_CLIENT_ID /
# AZURE_TENANT_ID / AZURE_SUBSCRIPTION_ID; no client secret exists, see §3.4).
# The job declares `environment: sentinel-dev` — that is the only OIDC subject gha-app trusts.

# Set app version env var
az webapp config appsettings set \
  --resource-group "$AZURE_RG" \
  --name "$APP_NAME" \
  --settings APP_VERSION="${APP_VERSION}"

# Deploy zip package (Entra auth — basic-auth publishing is disabled on the app)
az webapp deploy \
  --resource-group "$AZURE_RG" \
  --name "$APP_NAME" \
  --src-path deploy.zip \
  --type zip
```

`AZURE_RG` / `APP_NAME` / `DEPLOYED_APP_URL` are **environment variables** of `sentinel-dev`
(`vars.*`), never hardcoded: the names come from infra's naming module
(`rg-<dep>-<env>-cc`, `app-<dep>-<env>-<uid>`, uid = `sha1(sub-dep-env)[0:4]`), are stable across
destroy/recreate, and are pushed once by infra `scripts/push-deploy-config.sh` (§3.4).
`gha-app` holds `Website Contributor` on this one App Service and nothing else.

**On failure** (auth error, deploy rejected, app crash):

```
Datadog Event: stage:deploy, deploy_status:failed
```

#### Stage 4: Verify

```bash
# Wait for app to restart after deploy (F1 cold starts can take 30-60s)
sleep 30

# Health check (retry up to 3 times with 10s gap)
for i in 1 2 3; do
  HEALTH=$(curl -sf ${DEPLOYED_APP_URL}/health) && break
  sleep 10
done

# Version check
LIVE_VERSION=$(curl -sf ${DEPLOYED_APP_URL}/version | jq -r '.version')
if [[ "$LIVE_VERSION" != "${APP_VERSION}" ]]; then
  # Report: version mismatch — old version still serving
fi
```

**Important:** F1 tier apps sleep after idle and have cold-start latency.
The verify step retries with a 30s initial wait + 3 attempts.

**On failure** (health check fails, version mismatch):

```
Datadog Event: stage:verify, deploy_status:failed
```

#### Stage 5: Record Deployment in PostgreSQL (if: always())

Every deploy attempt — success or failure — gets a row in Sentinel's PostgreSQL
`deployments` table. This is the data the Analysis agent's `get_deploy_details` tool
and the deploy ↔ incident correlation depend on. **Failed deploys matter most** —
they're exactly the rows incidents join against.

```bash
# OIDC login already done in Stage 3 (azure/login@v2, as gha-app)
sudo apt-get install -y postgresql-client

# Entra DB token as the psql password — no db-password secret anywhere.
export PGPASSWORD=$(az account get-access-token --resource-type oss-rdbms \
  --query accessToken -o tsv)

# Values go in as psql variables (:'name' quotes them) — NEVER interpolated into the SQL
# text: PR titles, authors and file lists are attacker-influenced strings.
psql "host=${PG_HOST} dbname=${PG_DATABASE} user=${PG_USER} sslmode=require" \
  -X -v ON_ERROR_STOP=1 \
  -v service="$DD_SERVICE" -v pr="$PR_NUMBER" -v sha="$SHORT_SHA" -v author="$PR_AUTHOR" \
  -v status="$STATUS" -v run="$GITHUB_RUN_ID" -v files="$FILES_CHANGED_JSON" \
  -v stage="${FAILED_STAGE:-none}" -v version="$APP_VERSION" <<'SQL'
INSERT INTO deployments
  (service, pr_number, commit_sha, author, deploy_status, gha_run_id, files_changed, metadata)
VALUES
  (:'service', :'pr'::int, :'sha', :'author', :'status', :'run'::bigint, :'files'::jsonb,
   jsonb_build_object('failed_stage', :'stage', 'version', :'version'));
SQL
```

Notes:
- Runs `if: always()` — failed builds/deploys are recorded with their `failed_stage`.
- Auth is a **short-lived Entra DB token** from the OIDC identity (audience
  `https://ossrdbms-aad.database.windows.net`) — no `db-password`, no DB
  credential stored as a GitHub secret anywhere.
- `incident_id` stays NULL here; the backend backfills it when an incident
  correlates to this deploy.
- **Inline, not cross-repo actions** (decision 2026-10-05, R13): no
  `Keshav0375/Sentinel/.github/actions/*` dependency — the deployment pipeline must not wait on
  backend phases to exist.
- **`continue-on-error: true`.** A failed record is reported to Datadog as `stage:record` and
  **never changes `deploy_status`** — the run's colour describes the deploy, not bookkeeping.
- `PG_USER` is `gha-app`, a database principal bound by object ID (infra
  `scripts/grant-db-access.sh`), not a server admin. Its `INSERT, SELECT` on `deployments` is
  granted by **backend phase 1's migration** (the table owner); until that migration runs the
  record stage fails visibly with `relation "deployments" does not exist` — expected, and the
  end-to-end "a row exists" check belongs after backend phase 1.

#### Stage 6: Final Summary (if: always())

Runs regardless of which stage succeeded or failed.

```json
{
  "title": "Deployment ${STATUS} for PR #${PR_NUMBER}: ${PR_TITLE}",
  "tags": ["version:${APP_VERSION}", "service:sentinel-watchtower", "env:dev",
           "deploy_status:${STATUS}", "failed_stage:${FAILED_STAGE:-none}"],
  "alert_type": "info or error"
}
```

Also ships a structured log line via the Datadog Log Intake API:

```json
{
  "message": "deploy.completed",
  "ddsource": "github-actions",
  "ddtags": "version:pr-47-a3f9c2,service:sentinel-watchtower,env:dev",
  "hostname": "gha-runner",
  "service": "sentinel-watchtower",
  "deploy": {
    "pr_number": 47,
    "version": "pr-47-a3f9c2",
    "pr_title": "feat: add retry config",
    "status": "succeeded",
    "failed_stage": "none",
    "duration_seconds": 95,
    "stages": {
      "build": "succeeded",
      "deploy": "succeeded",
      "verify": "succeeded"
    }
  }
}
```

### 3.2 Datadog Reporting Helper

These helpers live in a **local composite action** (`.github/actions/dd-report/`) so
every stage calls one implementation instead of copy-pasted curl blocks. Inputs:
`title`, `tags`, `alert-type`, optional structured log payload.

```bash
send_dd_event() {
  local title="$1" text="$2" alert_type="$3" tags="$4"
  curl -sf -X POST "https://api.${DD_SITE}/api/v1/events" \
    -H "DD-API-KEY: ${DD_API_KEY}" \
    -H "Content-Type: application/json" \
    -d "{\"title\":\"${title}\",\"text\":\"${text}\",\"tags\":[${tags}],\"alert_type\":\"${alert_type}\",\"source_type_name\":\"github\"}"
}

send_dd_log() {
  local payload="$1"
  curl -sf -X POST "https://http-intake.logs.${DD_SITE}/api/v2/logs" \
    -H "DD-API-KEY: ${DD_API_KEY}" \
    -H "Content-Type: application/json" \
    -d "[${payload}]"
}
```

### 3.3 GHA Workflow Structure

```yaml
name: "[deployment] deploy — build and ship"

on:
  push:
    branches: [main]

env:
  DD_SITE: ${{ vars.DD_SITE }}   # us5.datadoghq.com — never hardcode the site
  DD_SERVICE: sentinel-watchtower
  DD_ENV: dev

permissions:
  id-token: write   # OIDC token for azure/login
  contents: read

concurrency:
  group: deploy-sentinel-dev
  cancel-in-progress: false   # never abort a half-finished deploy

jobs:
  build-deploy-verify:
    name: Build Deploy and Verify
    runs-on: ubuntu-latest
    environment: sentinel-dev   # the only subject gha-app federates on; main-only policy
    steps:
      - name: Checkout
      - name: Extract PR metadata
      - name: Build zip package
      - name: Report build failure
        if: failure()
      - name: Login to Azure
      - name: Deploy to App Service
      - name: Report deploy failure
        if: failure()
      - name: Verify deployment
      - name: Report verify failure
        if: failure()
      - name: Record deployment in PostgreSQL
        id: record
        if: always()
        continue-on-error: true
      - name: Report record failure
        if: steps.record.outcome == 'failure'
      - name: Report final summary
        if: always()
```

**Build → Deploy → Verify → Record → Summary.** No image push stage — zip deploy
goes directly to App Service. The record stage writes the `deployments` row that
Sentinel's agents correlate incidents against.

### 3.4 Required GitHub Configuration — environment `sentinel-dev`

Everything lives on the **`sentinel-dev` environment** (not repo-level), pushed by infra
`scripts/push-deploy-config.sh` after the deployment is applied (decision 2026-10-05, R8).

| Kind | Name | Value / source |
|------|------|----------------|
| secret | `AZURE_CLIENT_ID` | `gha-app` client ID (bootstrap identity in `rg-sentinel-bootstrap`) |
| secret | `AZURE_TENANT_ID` | tenant of the subscription |
| secret | `AZURE_SUBSCRIPTION_ID` | Azure for Students subscription |
| secret | `DD_API_KEY` | Datadog API key (org on US5) |
| variable | `AZURE_RG` | infra output `deployment_resource_group` |
| variable | `APP_NAME` | infra output `app_name` |
| variable | `DEPLOYED_APP_URL` | infra output `app_url` |
| variable | `PG_HOST` / `PG_DATABASE` | infra outputs `database_host` / `database_name` |
| variable | `PG_USER` | `gha-app` |
| variable | `DD_SITE` | `us5.datadoghq.com` (the org lives on US5; an API key is valid on one site only) |

**The merge gate.** `sentinel-dev` allows deployments from `main` only, and `main` requires a
pull request — so only merged code can mint `gha-app`'s token, never a scenario branch or a PR
run. **No required status check** (decision 2026-10-05): the deploy workflow runs only after merge, so it can never pass on a PR, and `deployfail/*` scenario branches must stay mergeable. "PR required" is the whole gate.

**No `AZURE_CLIENT_SECRET`, no DB password** — OIDC federation to `gha-app` (one subject:
`repo:Keshav0375/Sentinel-deployment:environment:sentinel-dev`) and a short-lived Entra DB token.
There is no demo-PR workflow; scenarios are real git branches (§4).

---

## 4. Scenario Surface — 30 Branches, 3 Cases

**Pivot (supersedes the old demo-PR model):** the demo app is now **real ground
truth** — genuinely deployed to App Service, genuinely emitting logs to Datadog.
There is no PR-faking workflow: **`ci_demo_prs.yml` is removed.** Instead the repo
ships **30 pre-authored scenario branches** (10 per case, expandable later). Each
branch is a self-contained change with a known ground-truth label; deploying it
produces exactly one of three outcomes.

| Case | 10 branches | Deploy pipeline | App at runtime | Datadog signal | `signal_type` | Sentinel outcome |
|------|-------------|-----------------|----------------|----------------|---------------|------------------|
| **i — clean pass** | `pass/01..10` | Green | Healthy, every endpoint 200 | success event only (no monitor) | — | **No incident** — true negative / baseline memory |
| **ii — deploy fails** | `deployfail/01..10` | **Red** (build/deploy/verify) | Previous good version stays live | deploy-failure event monitor (`deploy_status:failed`) | `deploy_failure` | **Case 2 — rollback** (heal main's deployability) |
| **iii — runtime error** | `runtime/01..10` | **Green** (verify passes) | Live app throws 5xx / errors | runtime-health monitor (5xx / failed pings) | `runtime_error` | **Case 3 — full incident response** (diagnose → rollback/escalate) |

**Two signal types → two handling paths** (case i produces neither):

- **`deploy_failure` (case ii):** the deploy never went live, so App Service keeps
  serving the previous version. The fix is a simple rollback of `main` to the last
  good SHA — no deep diagnosis. Evidence = the deploy-failure event + CI logs.
- **`runtime_error` (case iii):** the broken version **is** live. Headline case —
  the full agent pipeline correlates runtime error logs with the most-recent
  successful deploy (the `deployments` table), then rolls back or escalates.

**Why branches, not PRs:** each branch is a stable, replayable scenario with a
fixed ground-truth label. The sentinel-repo eval harness deploys a branch, watches
what Datadog + the agents do, and scores against the known label — so **the 30
branches _are_ the eval dataset** (they replace the Phase-1 synthetic scenario
JSON). To run one: deploy the branch via `ci_app_deployment.yml`, let the signal
flow, observe the outcome.

### 4.1 Branch Catalog (10 per case)

Ground-truth labels live in `scenarios/branches.yaml` — one entry per branch with
its case, the fault it injects, the expected `signal_type` + resolution, and the
`expected_culprit` — the deploy a correct revert PR must target (the scenario's own
merge, `pr-<N>-<sha>`, bound when the branch is deployed). The eval harness reads this
file to score agent runs against the known label: did it fire, did it classify, and did
its revert PR revert the right merge. A
representative spread (full 30 enumerated in the file):

**Case i — `pass/*` (clean, 10):** trivial safe changes — add `/info`, tweak a log
line, add a field to `GET /`, bump a comment. All deploy green and stay healthy.
These are the true negatives that prove Sentinel doesn't cry wolf.

**Case ii — `deployfail/*` (deploy fails, previous version stays live, 10):**

| Branch | Fault injected | Failed stage |
|--------|----------------|--------------|
| `deployfail/01` | Add `nonexistent-package==1.0.0` to requirements.txt | deploy (Oryx pip install) |
| `deployfail/02` | `/health` returns 503 | verify |
| `deployfail/03` | 60s `asyncio.sleep` in lifespan → health timeout | verify |
| `deployfail/04` | Hardcode `/version` to `"wrong"` → version mismatch | verify |
| `deployfail/05` | Syntax error in `main.py` → app won't boot | verify |
| `deployfail/06–10` | Spread across build/deploy/verify (bad start command, missing module, bad env, port clash, import error) | build/deploy/verify |

**Case iii — `runtime/*` (green deploy, breaks at runtime, 10):**

| Branch | Fault injected | How it slips past verify |
|--------|----------------|--------------------------|
| `runtime/01` | `GET /` returns 500 every call; `/health`+`/version` fine | verify only checks `/health`+`/version` |
| `runtime/02` | `/health` 200 for first ~5 min, then 503 | degrades after the verify window |
| `runtime/03` | Memory leak → 5xx under sustained traffic | fine at first ping |
| `runtime/04` | Unhandled exception on a specific payload | verify uses a safe payload |
| `runtime/05` | Latency spike (blocking call) on `GET /` | verify tolerates one slow call |
| `runtime/06–10` | Spread (intermittent 5xx, bad downstream call, resource exhaustion, wrong content-type, silent data error) | passes the narrow verify checks |

**The nuance that makes case iii the star:** the verify stage only probes `/health`
and `/version`. Any break elsewhere — or a delayed break — sails through the
pipeline green and can only be caught by runtime monitoring, which is exactly where
Sentinel's diagnostic value lives (correlate the runtime symptom back to "what
deployed most recently and succeeded?" via the `deployments` table).

---

## 5. Repository Structure

```
sentinel-deployment/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app: 3 routes + startup log
│   └── config.py            # AppConfig (pydantic-settings)
├── tests/
│   └── test_app.py          # Endpoint tests (health, version, root)
├── scenarios/
│   └── branches.yaml         # Ground-truth catalog: 30 branches, case + fault + expected signal_type/resolution
├── .github/
│   ├── actions/
│   │   └── dd-report/             # Local composite action: Datadog event + log reporting
│   └── workflows/
│       └── ci_app_deployment.yml  # Build → Deploy → Verify → Record → Report
├── requirements.txt          # pinned runtime deps (Oryx installs this)
├── requirements-dev.txt      # + pytest, httpx, ruff — never deployed
├── .env.example
├── .gitignore
└── README.md
```

No Dockerfile, no app.yaml, no container registry, **no `ci_demo_prs.yml`**. The
30 scenario branches are real git branches (catalogued in `scenarios/branches.yaml`);
deploying one via `ci_app_deployment.yml` is what generates signal. Zip deploy keeps
the app itself simple.

---

## 6. Datadog Schema

### 6.1 Events (timeline markers)

Every deploy produces at least one Datadog Event. Failed deploys produce two
(stage failure + final summary).

**Event tags (always present):**

| Tag | Value | Example |
|-----|-------|---------|
| `version` | PR number + SHA | `version:pr-47-a3f9c2` |
| `service` | Fixed | `service:sentinel-watchtower` |
| `env` | Fixed | `env:dev` |
| `deploy_status` | `succeeded` or `failed` | `deploy_status:failed` |
| `failed_stage` | Which stage failed | `failed_stage:build` / `failed_stage:none` |

### 6.2 Logs (searchable records)

Each deploy ships one structured log line via the HTTP Log Intake API.

Queryable in Datadog Log Explorer:
- `deploy_status:failed` — all failed deploys
- `failed_stage:build` — all build failures
- `@deploy.pr_number:47` — everything about PR #47's deploy
- `version:pr-47-*` — filter by deploy version

### 6.3 Monitors — What Triggers Sentinel

Two Datadog monitors, one per failure case (§4). Case i (clean pass) fires
neither.

| Monitor | Type | Fires On | Covers |
|---------|------|----------|--------|
| `sentinel-deploy-failure` | Event monitor | Any event tagged `deploy_status:failed` (shipped by this pipeline) | **Case ii** — build/deploy/verify failures → `signal_type=deploy_failure` |
| `sentinel-runtime-health` | Metric / HTTP monitor | App Service 5xx rate over threshold, or failed pings against `GET /health` + `GET /` (native Azure integration metrics or a Datadog synthetic check) | **Case iii** — runtime failures that passed verify → `signal_type=runtime_error` |

Both monitors notify the same webhook channel → Event Grid → Azure Function →
`repository_dispatch` on the sentinel repo. The bridge Function classifies the
payload and stamps `signal_type` (`deploy_failure` vs `runtime_error`, see
sentinel-infra §3.5), which the backend workflow branches on: CI logs + the deploy
event drive the **rollback** path (case ii); runtime error logs + "most recent
successful deploy" correlation (PostgreSQL `deployments` table) drive the **full
incident-response** path (case iii).

Monitor settings to keep the demo sane: renotify OFF, require a recovery period
before re-alerting, and a short evaluation window (5 min) on the runtime monitor so
condition-B demos fire while the room is still watching.

---

## 7. What This Enables for Sentinel

After deploying the 30 scenario branches, Datadog contains:

1. **Deploy events on a timeline** — visible in Events Explorer, tagged with branch + version
2. **Deploy logs** — searchable by status, stage, deploy version
3. **Failure patterns** — deploy failures (case ii) and runtime errors (case iii)
4. **Before/after correlation** — events mark exactly when each deploy happened

When the full Sentinel pipeline is connected:
- A monitor fires → webhook → Event Grid → bridge stamps `signal_type` → Sentinel GHA
- `deploy_failure` → **rollback** path; `runtime_error` → **full incident response**
- Sentinel agents fetch recent deploy logs via Datadog API + correlate against the
  `deployments` table to find the offending deploy
- Sentinel drafts a revert PR on sentinel-deployment (HITL gate)

---

## 8. Prerequisites & Setup Checklist

### Datadog
- [ ] Activate Student Pack Datadog offer (Pro, 10 servers, 2 years)
- [x] Datadog site: **US5 `us5.datadoghq.com`** (verified 2026-10-05: key valid on US5, 403 on every other site)
- [ ] Generate DD_API_KEY from Organization Settings → API Keys
- [ ] Test Events API: `curl -X POST "https://api.us5.datadoghq.com/api/v1/events" -H "DD-API-KEY: <key>" -d '{"title":"test","text":"hello"}'`

### Azure (all owned by Sentinel-infra — see its `docs/BOOTSTRAP.md` step 9)
- [ ] `gha-app` identity exists (`scripts/bootstrap-identities.sh`, run by the subscription Owner)
- [ ] Infra repo variable `GHA_APP_OBJECT_ID` set to `gha-app`'s principal ID
- [ ] Deployment `sentinel`/`dev` applied (Actions → *Sentinel Infra — Deploy*, `apply`, `all`) —
      App Service (F1, Python 3.12, §2.5 start command, basic-auth publishing off) + database
- [ ] `scripts/grant-db-access.sh --deployment sentinel --environment dev` (human Entra admin)

### GitHub (sentinel-deployment repo)
- [ ] `scripts/push-deploy-config.sh` (from Sentinel-infra) — creates `sentinel-dev` with the
      main-only policy, pushes §3.4, protects `main` (require PR)

### Local Development
- [ ] Python 3.12 available
- [ ] `pip install -r requirements.txt && uvicorn app.main:app --reload` works locally

---

## 9. Cost Breakdown

| Resource | Monthly Cost | Covered By |
|----------|-------------|------------|
| Azure App Service (F1) | Free | Always-free tier |
| Datadog Pro (events + logs) | Free | Student Pack (2 years) |
| GHA minutes (deploy runs) | Free | GitHub Pro (3,000 min/month) |
| **Total** | **$0/month** | **No credits consumed** |

GHA usage estimate:
- `ci_app_deployment.yml`: ~2 min per run (zip build + deploy + verify)
- ~20 merges/month = 40 min
- Well within 3,000 min/month quota
