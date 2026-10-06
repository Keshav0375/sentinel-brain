# deployment phase 2 — Deploy Pipeline

| | |
|---|---|
| **Repo** | `Sentinel-deployment` |
| **Branch → PR** | `dev/deploy-phase-2-deploy-pipeline` → `main` · PR #2 — https://github.com/Keshav0375/Sentinel-deployment/pull/2 |
| **Tasks** | 3/3 green (gate GREEN at bab357c) |
| **Gate** | ⬜ awaiting sign-off |

## What shipped

- **2.1 dd-report action** — composite action posting Datadog events and logs (US5 via dd-site), jq-built bodies, key in a 0600 header file, fail-soft, retry only on curl exit 6/7.
- **2.2 ci_app_deployment** — workflow plus `.github/scripts`: build, deploy, verify, record, summary; symlink refusal, SHA-pinned actions, re-login before record.
- **2.3 Datadog triggers** — deploy-failure monitor, 2 synthetics, sentinel-event-grid webhook (one-element array payload), `datadog/apply.sh`.

## What this unblocks

- Phase 3 can consume the deploy workflow, the dd-report action and the Datadog to Event Grid trigger path. Related infra PRs #16 and #17 merged (gha-app, outputs, grant/push scripts, CustomEventSchema, seed-vault retry).

## See it working

NOT VERIFIED LIVE: estate destroyed 2026-10-05; DD_APP_KEY not yet in Sentinel-infra/.env. First real run, Datadog events/logs, monitor firing and Event Grid to bridge dispatch are unproven.

1. ```bash
   gh workflow run ci_infra.yml apply all sentinel dev   # then approve
   ```
2. ```bash
   bash scripts/grant-db-access.sh --deployment sentinel --environment dev
   ```
3. Add DD_APP_KEY to Sentinel-infra/.env, then from Sentinel-deployment:
   ```bash
   bash datadog/apply.sh --dry-run
   bash datadog/apply.sh
   ```
4. Merge the phase PR, watch the ci_app_deployment run, then:
   ```bash
   curl $DEPLOYED_APP_URL/version
   ```
   → expect events/logs in Datadog US5
5. Expected record-stage failure: `relation deployments does not exist`
6. Destroy the estate afterwards.

## Not done / blocked

- **deployments row** — deferred to backend 1.3 (R12).
- **Live verification** — all of it (see above).
- **Follow-ups:** bridge alert_transition filter (infra); shellcheck for `.github/scripts` and `datadog/apply.sh` in the deployment gate; a checkout failure leaves dd-report unresolvable; Synthetics location aws:ca-central-1 on US5 unverified; `$EVENT_TITLE` escaping; 15 test-suite notes.
- **Skipped checks:** none.

## Decisions made during the build

- Datadog to Event Grid uses CustomEventSchema input mapping (Datadog cannot emit ISO eventTime); architecture amendments in brain a11f45f, 984a079.
