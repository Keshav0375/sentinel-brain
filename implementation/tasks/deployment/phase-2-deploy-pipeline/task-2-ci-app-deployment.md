# task-2 — `ci_app_deployment.yml` (Build→Deploy→Verify→Record→Summary)   ·   [deployment / phase-2-deploy-pipeline]

| Field | Value |
|-------|-------|
| **Status** | `not-started` |
| **Repo** | `Sentinel-deployment` |
| **Phase branch** | `dev/deploy-phase-2-deploy-pipeline` |
| **Commit prefix** | `feat:` |
| **Arch refs** | architecture/deployment.md §3.1, §3.3, §3.4; §6.1/6.2 |
| **Depends on** | [[task-1-fastapi-app]], [[task-1-dd-report-action]]; infra PR #16 (`gha-app`, outputs, `grant-db-access.sh`, `push-deploy-config.sh`) + deployment `sentinel`/`dev` applied. **No backend dependency** (R13). |
| **Referenced by** | [[task-3-datadog-monitors]], backend `deployments` table consumers |

## Spec
The core pipeline. Fires on push to main; every stage reports to Datadog; the record stage
writes the `deployments` row that backend correlation depends on.

**Files created:** `.github/workflows/ci_app_deployment.yml` — name `[deployment] deploy — build and ship`; `push: [main]`; env DD_SITE/DD_SERVICE/DD_ENV.
- **Stage 1** metadata: PR_NUMBER, SHORT_SHA, PR_TITLE, `APP_VERSION=pr-<n>-<sha>`.
- **Stage 2** build zip (app/ + requirements.txt); on failure → `dd-report` `stage:build deploy_status:failed`.
- Job declares `environment: sentinel-dev`; `permissions: id-token: write, contents: read`; `concurrency: deploy-sentinel-dev` (no cancel).
- **Stage 3** deploy: `azure/login@v2` (OIDC as `gha-app`), `az webapp config appsettings set APP_VERSION`, `az webapp deploy --type zip`, against `vars.AZURE_RG` / `vars.APP_NAME`; on failure → dd-report `stage:deploy`.
- **Stage 4** verify: sleep 30, retry `/health` ×3, `/version` == APP_VERSION; on failure → dd-report `stage:verify`.
- **Stage 5** record (`if: always()`, `continue-on-error: true`, `id: record`): **inline** (R13) — `az account get-access-token --resource-type oss-rdbms` → `psql` as `vars.PG_USER` on `vars.PG_HOST`/`vars.PG_DATABASE`, INSERT into `deployments` (service, pr_number, commit_sha, author, deploy_status, gha_run_id, files_changed jsonb, metadata{failed_stage,version}) with **every value a `psql -v` variable** (never string-built SQL). `incident_id` NULL. Record failure → dd-report `stage:record`, never changes `deploy_status`.
- **Stage 6** summary (`if: always()`): dd-report final event + structured `deploy.completed` log (§3.1 payload).
- Config (§3.4, environment `sentinel-dev`): secrets AZURE_CLIENT_ID/TENANT_ID/SUBSCRIPTION_ID, DD_API_KEY; vars AZURE_RG, APP_NAME, DEPLOYED_APP_URL, PG_HOST, PG_DATABASE, PG_USER, DD_SITE.

## Prerequisites
- [ ] actionlint. [ ] `sentinel-dev` environment + config pushed (infra BOOTSTRAP step 9). [ ] Deployment `sentinel`/`dev` applied.

## Acceptance Criteria
- [ ] Workflow validates; Build→Deploy→Verify→Record→Summary present; failure paths report per §3.1.
- [ ] Record stage runs `if: always()` (failed deploys recorded) and writes all `deployments` columns.
- [ ] Uses OIDC as `gha-app` (no client secret); inline SQL with `psql -v` variables only.
- [ ] **No** required status check on `main` (decision 2026-10-05 — post-merge workflow can't gate a PR; scenario branches must merge).
- [ ] `STATUS` is `succeeded` | `failed` — the same value for the Datadog tag and `deployments.deploy_status`.

## Tests
- **Lint:** actionlint, yamllint.
- **Integration:** merge a PR → App Service updated, `/version` matches, Datadog shows the events. The record stage reports `stage:record` failure ("relation deployments does not exist") until backend phase 1 — **the row check is deferred to after backend 1.3**, not claimed here.
- **Quality gate:** `--repo deployment`.

## How to Verify (phase gate)
1. actionlint clean.
2. (wired) merge a trivial PR → app redeploys, Datadog event visible, `psql -c 'select * from deployments order by deployed_at desc limit 1'` shows the row.

## Report   ·   _filled on completion_
_not yet implemented_

## BLOCKED
_None for the YAML. Live run needs the estate applied (`ci_infra.yml apply all sentinel dev`) + `grant-db-access.sh`. The `deployments` row is deferred to backend 1.3 (R12)._
