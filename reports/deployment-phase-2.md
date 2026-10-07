# deployment phase 2 — Deploy Pipeline

| | |
|---|---|
| **Repo** | `Sentinel-deployment` |
| **Branch → PR** | `dev/deploy-phase-2-deploy-pipeline` → `main` · PR #2 — https://github.com/Keshav0375/Sentinel-deployment/pull/2 |
| **Tasks** | 3/3 green (gate GREEN at bab357c) |
| **Gate** | ✅ signed 2026-10-07 (PR #2 `4d9bc88`, follow-up PR #3 `e67e19d`) |

## What shipped

- **2.1 dd-report action** — composite action posting Datadog events and logs (US5 via dd-site), jq-built bodies, key in a 0600 header file, fail-soft, retry only on curl exit 6/7.
- **2.2 ci_app_deployment** — workflow plus `.github/scripts`: build, deploy, verify, record, summary; symlink refusal, SHA-pinned actions, re-login before record.
- **2.3 Datadog triggers** — deploy-failure monitor, 2 synthetics, sentinel-event-grid webhook (one-element array payload), `datadog/apply.sh`.

## What this unblocks

- Phase 3 can consume the deploy workflow, the dd-report action and the Datadog to Event Grid trigger path. Related infra PRs #16 and #17 merged (gha-app, outputs, grant/push scripts, CustomEventSchema, seed-vault retry).

## See it working

VERIFIED LIVE 2026-10-07:

- Run 37564896708: build, deploy, verify succeeded; `pr-3-e67e19d` live; gha-app OIDC login worked twice; gha-app Postgres Entra login worked; record failed only on `relation "deployments" does not exist` (expected, R12 / backend 1.3); Datadog events and logs accepted.
- Event Grid: Datadog monitor test notification -> PublishSuccess, then DeliverySuccess at 2026-10-07T03:32Z, so the bridge dispatched to Keshav0375/Sentinel.
- Earlier run 37559626662 proved the failure-reporting path (deploy failed on F1 QuotaExceeded).
- Infra repairs merged along the way: PR #18 (f4292a4: az OIDC refresh per layer, kubelogin wrapper, FIC deprecations, preflight ownership) and PR #19 (001cece: github-pat seeded from DISPATCH_PAT, bridge skips an unresolved token).
- The estate was destroyed again after the test (destroy run in flight at sign-off).

## Not done / blocked

- **deployments row** — deferred to backend 1.3 (R12).
- **Follow-ups:** DISPATCH_PAT 90-day expiry has no automated warning; Datadog app key is unscoped; synthetics must be deleted/paused while the estate is down; bridge alert_transition filter (infra); the gate has no shellcheck for `.github/scripts` and `datadog/apply.sh`; a checkout failure leaves dd-report unresolvable; Synthetics location aws:ca-central-1 on US5 unverified; `$EVENT_TITLE` escaping; 15 test-suite notes.
- **Skipped checks:** none.

## Decisions made during the build

- Datadog to Event Grid uses CustomEventSchema input mapping (Datadog cannot emit ISO eventTime); architecture amendments in brain a11f45f, 984a079.
