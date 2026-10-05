# Sentinel Phase 2 — Implementation State

> Live execution state. `/implement-phase` reads this first and updates it after every task.
> Planning-side state (architecture decisions) stays in [architecture/decisions.md](../architecture/decisions.md).
> Closed blockers, resolved R-items and the change log live in [history.md](history.md) — the
> build loop never reads that file. **Keep this one live-only; append history there.**
>
> Last updated: 2026-10-04

## Current Position

| Field | Value |
|-------|-------|
| **Active category** | **deployment** — phase 1 signed; phase 2 next. infra is ✅ COMPLETE (2026-09-13) |
| **Active phase** | deployment 2 — Deploy Pipeline |
| **Active branch** | none yet (`dev/deploy-phase-2-deploy-pipeline` to be cut from `main`, Sentinel-deployment) |
| **Active PR** | none (deployment PR #1 merged 2026-10-04) |
| **Current task** | deployment 2.1 — `dd-report` composite action |
| **Tasks verified** | 31 / 72 — infra 6.8 is ⚠️ shipped-but-unexercised, so uncounted |
| **Phases merged** | 6 / 18 — infra 1-6, all merged; deployment 1 signed (counter per where.py) |
| **Branch model** | Per repo. **infra + deployment:** `main` → `dev/<cat>-phase-<M>-<slug>` → PR back to `main` (no release branch). **backend (`Sentinel`):** `release-phase-2` → `dev/backend-phase-<M>-<slug>` → PR back to `release-phase-2`; `release-phase-2` → `main` once, at the end of Phase 2, and `main` takes nothing else. See [README §6](README.md#6-git-model--one-branch--one-pr-per-phase). |
| **Tracker commits** | straight to `main` of this repo (`sentinel-brain`) — no branch, no PR. One phase = one code PR + tracker commits here. |
| **Control plane** | `sentinel-brain` (this repo). Code repos are siblings: `../Sentinel` (backend), `../Sentinel-deployment`, `../Sentinel-infra`. |

## Next Action

**Start deployment phase 2.** Branch `dev/deploy-phase-2-deploy-pipeline` from `Sentinel-deployment`
`main`, PR back into `main` (no release branch in this repo).

| # | Task | What |
|---|------|------|
| 2.1 | `dd-report` composite action | |
| 2.2 | `ci_app_deployment.yml` | Build→Deploy→Verify→Record (Entra DB token)→Summary |
| 2.3 | Datadog monitors | deploy-failure → `deploy_failure`; runtime-health → `runtime_error` |

## Carried into the deployment category

Two items left open when infra was signed off. Neither gates deployment; both should be closed
on the next occasion the platform is up.

- ⚠️ **`Sentinel — Pause / Resume` has never executed.** Zero runs, ever. `gha-ops`, the `ops`
  environment and the ten-action custom RBAC role have never authenticated once. Needs a live
  estate: apply platform → pause → resume → destroy, ~50 min.
- ⚠️ **The live `plan-pull-request` federated credential still exists on `gha-plan`.** PR #15
  stopped it being recreated and added `remove_fic` so the next bootstrap deletes it, but merging
  a PR does not delete a credential in Azure. One command:
  `az identity federated-credential delete --name plan-pull-request --identity-name gha-plan --resource-group rg-sentinel-bootstrap --yes`

**Standing gaps, not blockers:**
- `identity.tf` deleted — returns when `sentinel-tf-identity` carries `environment:*` federated
  credentials. Per-deployment Entra app registrations are written and work (commit `65e35b9`).
- `gha-ops` cannot-delete is proven by role inspection, not by a refused delete.
- **All four repos are PUBLIC.** Subscription and tenant ids are in `docs/BOOTSTRAP.md` and in
  git history; the admin UPN is now masked in new run logs but remains in old ones. Neither id
  authenticates anything. Whether the repos should be public at all is an open decision.
- Infra gate tools are now installed locally (macOS, 2026-10-03): `python3 scripts/gate.py infra --fast`
  ran tf-fmt/init/validate, tflint, shellcheck, py-unittest, tf-test, actionlint green. Still
  open: `ruff-infra` (no `Sentinel-infra/.venv`) and `yamllint` reports `line too long` in
  `.github/` (non-required, so shown as skipped). `tfsec`/`gitleaks` not yet run in full mode.

## Phase Gate Ledger

A phase moves to `verified` only after the user confirms the feature works and the PR is
merged. Newest first.

| Date | Category | Phase | Branch | PR | Verified by | Notes |
|------|----------|-------|--------|----|-----|-------|
| 2026-10-04 | deployment | 1 — The App | `dev/deploy-phase-1-app` | [#1](https://github.com/Keshav0375/Sentinel-deployment/pull/1) | Keshav | 1.1, 1.2 verified; merged manually by Keshav (squash 852660e) |
| 2026-09-13 | infra | **6 — Dynamic Deployments & Workflows** ✅ **CATEGORY COMPLETE** | `dev/infra-phase-6-dynamic-deployments` | [#8](https://github.com/Keshav0375/Sentinel-infra/pull/8) + [#9](https://github.com/Keshav0375/Sentinel-infra/pull/9) [#10](https://github.com/Keshav0375/Sentinel-infra/pull/10) [#11](https://github.com/Keshav0375/Sentinel-infra/pull/11) [#12](https://github.com/Keshav0375/Sentinel-infra/pull/12) [#13](https://github.com/Keshav0375/Sentinel-infra/pull/13) [#14](https://github.com/Keshav0375/Sentinel-infra/pull/14) [#15](https://github.com/Keshav0375/Sentinel-infra/pull/15) | Keshav | Full lifecycle proven live from an empty subscription: `apply·platform` 11 resources ([34778509991](https://github.com/Keshav0375/Sentinel-infra/actions/runs/34778509991)), `apply·deployment` 31 resources incl. **`kubernetes_namespace sentinel-dev`** + quota + LimitRange + NetworkPolicy + ServiceAccount + federated credential ([34779137478](https://github.com/Keshav0375/Sentinel-infra/actions/runs/34779137478)) — closing the kubelogin gap carried since 2026-08-25 — `destroy·deployment` ([34779589393](https://github.com/Keshav0375/Sentinel-infra/actions/runs/34779589393)), `destroy·all` 7 destroyed, workspace deleted, verify **11/11 ok** ([34782250925](https://github.com/Keshav0375/Sentinel-infra/actions/runs/34782250925)). Estate back to `rg-sentinel-bootstrap` + `NetworkWatcherRG` only. **Five defects found by reading the run history and fixed the same day, each proven in production**: identical run names + false-alarm verify + unseen F1 quota + a PR plan that tried to CREATE its workspace (#11); `apply` unguarded against a missing platform (#12); that refusal arriving 2m30s late (#13); **the destroy deadlock** — the Entra admin dropped concurrently with the database it owns, Postgres `2BP01`, 30 min hang, Postgres left billing (#14); and two security items (#15). **Signed with 6.8 (Pause/Resume) recorded as ⚠️ shipped-but-unexercised — zero runs, ever.** |
| 2026-08-25 | infra | 5 — Dynamic Foundations | `dev/infra-phase-5-dynamic-foundations` | [#7](https://github.com/Keshav0375/Sentinel-infra/pull/7) | Keshav | Owner answered **Approve & merge**; merged `7849310`. Old estate destroyed (45 resources) and rebuilt as a two-layer platform. Proven live: a deployment workspace plans ZERO Azure resources and its `plan -destroy` reports nothing to destroy, while still reading platform outputs via `terraform_remote_state`; `gha-plan` holds `*/read` + 2 blob reads only. The merge was initially BLOCKED by the branch ruleset — the workflows still described the pre-phase-5 contract, fixed in-phase rather than deferred, which surfaced that Reader cannot refresh ACR/AKS. Superseded R5, R6, C1 and one-cluster-per-estate. |
| 2026-08-24 | infra | 4 — Cross-Repo Wiring & CI | `dev/infra-phase-4-wiring-and-ci` | [#4](https://github.com/Keshav0375/Sentinel-infra/pull/4) | Keshav | Owner answered **Approve & merge** at the gate; PR #4 merged `09b2510`→`f2aa5da`. **The identity plane was proven live**: on its first-ever CI run Terraform refreshed the whole estate under the `sentinel-gha` UAMI, exercising the OIDC round trip, R5's RBAC grant and the state blob — none of which phases 1-3 had tested, since all three applied locally as Owner. `ci_runners` built and pushed the image; the first automated `apply` succeeded. Follow-ups landed as PR #5 (ten review fixes that never reached disk, the `environment:production` credential bootstrap, and a DB start-guard) and PR #6 (workflow renames, sha- image versioning, manual dispatch). Closed B16. **Ledger row written 2026-08-25** — the sign-off happened at merge time; recording it lagged. |
| 2026-08-24 | infra | 3 — Compute & Networking | `dev/infra-phase-3-compute-modules` | [#3](https://github.com/Keshav0375/Sentinel-infra/pull/3) | Keshav | Owner ran the checklist: plan **No changes** (0 warnings), 14/14 handler tests, gate PASS (8 ran — now incl. py-unittest + ruff), AKS Stopped, bridge function registered, rotation subscription Succeeded. Both reviewers' blockers fixed on-branch (Datadog tags shape, client_payload 10-prop cap, zip redeploy, KV-literal guard, func-rg grant). Closed B12. |
| 2026-08-23 | infra | 2 — Core Resource Modules | `dev/infra-phase-2-core-modules` | [#2](https://github.com/Keshav0375/Sentinel-infra/pull/2) | Keshav | Owner ran the checklist personally: ACR Standard, Postgres AAD-only, KV RBAC + Officer/User split, empty vault by design, gate PASS (6 ran). Live tests: Entra-token psql login; KV write→read→purge. Resolved R6; both reviewers' blockers fixed on-branch. |
| 2026-08-15 | infra | 1 — Foundations & Bootstrap | `dev/infra-phase-1-foundations` | [#1](https://github.com/Keshav0375/Sentinel-infra/pull/1) | Keshav | `terraform plan` → **No changes**; both bootstrap scripts idempotent; gate PASS (5 ran); 5 federated credentials verified in Azure. Resolved R3, R4, R5, C1–C9, C12, C13. Closed B1, B2, B3, B10, B15. |

## Blockers

External dependencies that halt verification. Mirror any task-level BLOCKED here.
(Seeded from [architecture/decisions.md](../architecture/decisions.md) blockers — these gate infra Phase 1–4.)

| # | Blocker | Blocks | Owner | Status |
|---|---------|--------|-------|--------|
| B16 | ~~`sentinel-tf-identity` cannot serve infra CI — two faults~~ | — | Keshav | ✅ **CLOSED 2026-08-24.** (a) `sentinel-tf-pr` + `sentinel-tf-env-production` federated credentials created — the identity tenant now carries all three subjects the school tenant has. (b) The SP had **no directory role at all**: `transitiveMemberOf` returned empty, so B11's record that Application Administrator was granted to it was a **false positive**. Assigned via `roleManagement/directory/roleAssignments` and verified. Proven live: PR check green, both tenants authenticated **and** authorised from CI, `Plan: 0 to add, 2 to change` identical to local. |
| B4 | Anthropic API key | backend LLM calls; Key Vault seed | Keshav | open |
| B5 | OpenAI API key | backend fallback; Key Vault seed | Keshav | open |
| B6 | ~~Datadog account + API key + app key~~ | — | Keshav | ✅ **CLOSED 2026-09-13.** `DATADOG_API_KEY` + `DATADOG_APP_KEY` present in `Sentinel-infra/.env` and in that repo's `production` environment secrets. Still to be pushed to `Sentinel-deployment` — see R8. |
| B7 | ~~LangFuse cloud account~~ | — | Keshav | ✅ **CLOSED 2026-09-13.** `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL` present. Backend-only consumer. |
| B8 | ~~Microsoft Teams incoming webhook~~ | — | Keshav | ✅ **CLOSED 2026-09-13.** `TEAMS_WEBHOOK_URL` present. |
| B9 | ~~GitHub PAT (`repo` scope) for cross-repo secret push~~ | — | Keshav | ✅ **SUPERSEDED 2026-09-13.** The `github` provider and `github-repo-config.tf` were deleted in phase 5, so no PAT is held by Terraform at all. Distribution is now `scripts/set-gh-secrets.sh`, which runs under the operator's own `gh` auth. The remaining work is R8, not a credential. |

## Open Reconciliations (decide before the affected task)

| # | Item | Affects | Status / resolution |
|---|------|---------|---------------------|
| ~~R7~~ | ~~No OIDC identity for `Sentinel-deployment`~~ | — | ✅ **CLOSED 2026-10-05.** `gha-app` bootstrapped (principal `eff18b0a-…`), one FIC `environment:sentinel-dev`; live role = Website Contributor on `app-sentinel-dev-b136` only (verified). |
| ~~R8~~ | ~~Cross-repo secret distribution~~ | — | ✅ **CLOSED 2026-10-05.** `push-deploy-config.sh` pushed 4 secrets + 7 vars to `sentinel-dev`; main-only branch policy; `main` requires PR. Datadog org is **US5**. Survives destroy (names deterministic). |
| ~~R9~~ | ~~Stale names in `deployment.md`~~ | — | ✅ **CLOSED 2026-10-05.** §3.1/§3.3/§3.4/§8 rewritten to `vars.*` from infra outputs (`f5d07c5`); no hardcoded resource names remain. |
| ~~R10~~ | ~~What is the `service` identity?~~ | — | ✅ **CLOSED 2026-10-04.** `service` = **`sentinel-watchtower`** — a stable logical name, decoupled from the Azure resource name (`app-<dep>-<env>-<uid>`), used for the Datadog `service` tag, `deployments.service`, monitor queries and the app's `dd_service` default. Docs updated. **Follow-up (infra):** `modules/app-service/main.tf` `DD_SERVICE` + `modules/functions/tests/test_handlers.py` fixtures still say `dummy-api` — lands with the R7/R11/R12 infra fix. |
| ~~R11~~ | ~~App URL/name not root outputs~~ | — | ✅ **CLOSED 2026-10-05.** Outputs `app_name`, `app_url`, `deployment_resource_group`, `database_name`, `database_host` (infra PR #16). |
| **R12** | Pipeline Postgres access. | backend 1.3 | **PARTLY CLOSED 2026-10-05.** `gha-app` is a DB principal on `sentinel_dev` (CONNECT/USAGE verified). ⏳ Table grant: backend 1.3's migration grants on `deployments`; re-run `grant-db-access.sh` after it **and after every platform recreate** (destroy drops the role). |
| ~~R13~~ | ~~Cross-repo composite actions missing~~ | — | ✅ **CLOSED 2026-10-05.** Record stage inlines the SQL (`psql -v` vars only); no dependency on backend actions. |

Resolved R1–R6 are in [history.md](history.md).

## History

Closed blockers, resolved reconciliations and the full change log moved to
[history.md](history.md) on 2026-08-24 — they are audit record, not live state, and every
`/implement-phase` run was paying ~4K tokens to re-read them. Nothing in the build loop
reads history.md; append to it, never to this file.
