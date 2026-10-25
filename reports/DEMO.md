# Sentinel live demo runbook

The steps you run to do the live demo end to end. Repos: `Sentinel` (backend), `Sentinel-deployment` (target app + scenarios), `Sentinel-infra` (estate).
Every workflow and script named here exists. Expected outcomes come from `Sentinel-deployment/scenarios/branches.yaml`.

## 1. One-time prerequisites

1. **Estate up** (`Sentinel-infra`):
   - `scripts/bootstrap-state.sh` and `scripts/bootstrap-identities.sh` (first time only)
   - `ci_infra.yml` → `action=apply`, `scope=all`
   - `scripts/grant-db-access.sh`
   - then in `../Sentinel`: `poetry run alembic upgrade head`
2. **Infra CI-identity ticket done.** The full list of vars, secrets and grants is in `architecture/decisions.md` 2026-10-24 phase 8, "Names the infra CI-identity ticket must create". It covers:
   - `sentinel-dev` env vars: `AZURE_*`, `SENTINEL_API_*`, `AKS_*`, `ACR_*`, `KEY_VAULT_URI`, `PG_*`
   - `SENTINEL_KEEP_WARM`
   - the gha-backend AcrPush/KV/AKS/PG grants
   - the API app registration with `Incident.Write`
3. **`REVERT_PR_PAT`** as a `sentinel-dev` environment secret on `Keshav0375/Sentinel`. Use a fine-grained token scoped to Sentinel-deployment only, with Contents and PRs read/write, valid for 90 days.
4. **Real Anthropic/OpenAI keys in Key Vault** via `Sentinel-infra/scripts/seed-vault.sh` (`anthropic-api-key`, `openai-api-key`).
5. **Datadog (US5) synthetics and monitors:** `Sentinel-deployment/datadog/apply.sh`.
6. **Backend deployed:** push to `release-phase-2` triggers `ci_backend_deployment.yml`, or run `ci_backend_scale.yml` with `direction=up`. Check `GET /health` and `/ready` → 200.

## 2. Scenarios

Run these in order: `pass/01`, then `deployfail/03`, then `runtime/01`. `runtime/07` is optional.

| Scenario | Fault | Expect |
|---|---|---|
| `pass/01` | add GET /info | deploy green, **no incident** |
| `deployfail/03` | pin fastapi to a non-existent version | deploy fails → **revert PR + Teams** |
| `runtime/01` | GET / returns 500 | monitor alert → **revert PR or escalation** |
| `runtime/07` (optional) | /health 503 once >10 min after deploy | delayed alert → revert PR or escalation |

For each scenario:
1. Merge the scenario branch PR on `Sentinel-deployment`.
2. Watch these in order:
   - the `ci_app_deployment.yml` run
   - the Datadog monitor (runtime scenarios)
   - the `ci_incident_response.yml` run on `Sentinel`
   - the revert PR on `Sentinel-deployment`
   - the Teams card
   - the LangFuse trace
   - `GET /incidents/{id}`, plus `/trajectory` and `/rollback-spec`
3. Trace by `correlation_id`: it is the same value in the workflow logs, the incident row, the LangFuse trace and the Teams card.
4. **Human gate:** review the revert PR, then merge it or close it. Sentinel never merges.

## 3. Score

```bash
cd ../Sentinel
python3 scripts/run_eval.py --branches ../Sentinel-deployment/scenarios/branches.yaml   # dataset sentinel-scenario-runs
curl -H "Authorization: Bearer $TOKEN" https://<backend>/api/eval-report
```

## 4. Teardown

1. Run `ci_backend_scale.yml` with `direction=down`.
2. Run `Sentinel-infra` `ci_infra.yml` with `action=destroy`, `scope=all`. It should end with verify ok and only `rg-sentinel-bootstrap` left.

## 5. Troubleshooting

- **F1 quota:** the Postgres/App tier quota in the region can block apply. Check the subscription quota, free or delete the old resource, then re-run apply.
- **OIDC expiry:** your local `az` token expires. Run `az logout && az login --tenant <tenant>` (and `kubelogin convert-kubeconfig -l azurecli`), then retry. CI federated tokens are per-run, so re-run the job.
- **Concurrency pending-run limit:** the `sentinel-backend` concurrency group holds one running and one pending run. A third run cancels the pending one. Wait for the current run to finish before you trigger another.
