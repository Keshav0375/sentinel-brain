# Sentinel Phase 2 — Implementation State

> Live execution state. `/implement-phase` reads this first and updates it after every task.
> Planning-side state (architecture decisions) stays in [architecture/decisions.md](../architecture/decisions.md).
> Closed blockers, resolved R-items and the change log live in [history.md](history.md) — the
> build loop never reads that file. **Keep this one live-only; append history there.**
>
> Last updated: 2026-09-13 (post acceptance run)

## Current Position

| Field | Value |
|-------|-------|
| **Active category** | infra — **in progress** |
| **Active phase** | 6 — Dynamic Deployments & Workflows |
| **Active branch** | none — `Sentinel-infra` `main` is clean |
| **Active PR** | none open |
| **Current task** | _infra phase 6 acceptance run complete._ 7 of 8 tasks proven end-to-end against live Azure. **Task 6.8 (Pause / Resume) has never executed** — that is the only thing between here and the gate. |
| **Tasks verified** | 29 / 72 — phase-6 tasks 6.1-6.7 proven live; 6.8 shipped but unexercised |
| **Phases merged** | 6 / 18 — infra 1-6 |
| **Branch model** | Per repo. **infra + deployment:** `main` → `dev/<cat>-phase-<M>-<slug>` → PR back to `main` (no release branch). **backend (`Sentinel`):** `release-phase-2` → `dev/backend-phase-<M>-<slug>` → PR back to `release-phase-2`; `release-phase-2` → `main` once, at the end of Phase 2, and `main` takes nothing else. See [README §6](README.md#6-git-model--one-branch--one-pr-per-phase). |
| **Tracker commits** | straight to `main` of this repo (`sentinel-brain`) — no branch, no PR. One phase = one code PR + tracker commits here. |
| **Control plane** | `sentinel-brain` (this repo). Code repos are siblings: `../Sentinel` (backend), `../Sentinel-deployment`, `../Sentinel-infra`. |

## Next Action

**Run `Sentinel — Pause / Resume` once, then sign the infra phase-6 gate.**

`gh run list --workflow ci_pause.yml` returns nothing. Zero executions, ever. The `gha-ops`
identity, the `ops` environment and the ten-action custom RBAC role have never authenticated
once — and a role proven only by inspection is the thing most likely to be wrong. It needs a
live estate, so proving it means: apply platform (~20 min) → pause → resume → destroy (~15 min).

Everything else in phase 6 is proven live on 2026-09-13, from an empty subscription:

| run | what it proved |
|---|---|
| [34778509991](https://github.com/Keshav0375/Sentinel-infra/actions/runs/34778509991) | `apply · platform` — ACR + AKS + Postgres, 11 resources from zero |
| [34779137478](https://github.com/Keshav0375/Sentinel-infra/actions/runs/34779137478) | `apply · deployment` — 31 resources, **including `kubernetes_namespace sentinel-dev`, the quota, LimitRange, NetworkPolicy, ServiceAccount and the federated credential** |
| [34779589393](https://github.com/Keshav0375/Sentinel-infra/actions/runs/34779589393) | `destroy · deployment` — one tenant leaves, platform untouched |
| [34782250925](https://github.com/Keshav0375/Sentinel-infra/actions/runs/34782250925) | `destroy · all` — 7 destroyed, workspace deleted, verify 11/11 `ok` |

**Gaps closed by that run:**
- ✅ **Namespaces have been created.** The kubelogin + Entra-token path to the cluster is
  exercised, not theoretical. This was carried forward since 2026-08-25.
- ✅ Destroy reaches zero: the subscription holds only `rg-sentinel-bootstrap` and
  `NetworkWatcherRG`.

**Five defects found and fixed the same day**, each proven in production:

| PR | defect |
|---|---|
| [#11](https://github.com/Keshav0375/Sentinel-infra/pull/11) | every dispatch rendered as the same run name; `verify` false-alarmed on refused runs; preflight could not see the App Service F1 quota; a PR plan tried to CREATE the workspace it planned in |
| [#12](https://github.com/Keshav0375/Sentinel-infra/pull/12) | `apply --scope deployment` was unguarded against a missing platform (only `plan` was); verify double-reported on an already-failed action |
| [#13](https://github.com/Keshav0375/Sentinel-infra/pull/13) | the missing-platform refusal arrived 2m30s in, after preflight's F1 probe had run |
| [#14](https://github.com/Keshav0375/Sentinel-infra/pull/14) | **destroy deadlock** — the Entra admin was dropped concurrently with the database it owns, hit Postgres `2BP01`, and hung 30 min until the OIDC assertion expired, leaving Postgres billing |

**Still open as known gaps:**
- ⚠️ **Pause / Resume has never run.** See above.
- ⚠️ `identity.tf` deleted — returns when `sentinel-tf-identity` carries `environment:*`
  federated credentials.
- ⚠️ `gha-ops` cannot-delete is proven by role inspection, not by a refused delete.
- ⚠️ **Security: all four repos are PUBLIC.** Subscription id, tenant id and a real UPN are in
  `docs/BOOTSTRAP.md` and in world-readable run logs. Not credentials, but a tenant id plus a
  real UPN is the pair used to target password-spray and consent-phishing.
- ⚠️ **Security: `gha-plan` carries an unused federated credential** on subject
  `repo:Keshav0375/Sentinel-infra:pull_request`. Every job that authenticates as `gha-plan`
  declares `environment: plan`, so that subject is never presented — but it is the only one a
  fork PR could match, and `gha-plan` holds subscription-wide Reader **plus Blob Data Reader on
  the Terraform state**, which contains the ACR admin password (`admin_enabled = true`).
  Remove it: `az identity federated-credential delete --name plan-pull-request
  --identity-name gha-plan --resource-group rg-sentinel-bootstrap --yes`
- ⚠️ The infra quality gate has never run `shellcheck`, `actionlint`, `tflint`, `tfsec`,
  `yamllint` or `gitleaks` — none on the author's PATH. CI runs Terraform only.

## Phase Gate Ledger

A phase moves to `verified` only after the user confirms the feature works and the PR is
merged. Newest first.

| Date | Category | Phase | Branch | PR | Verified by | Notes |
|------|----------|-------|--------|----|-----|-------|
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
| B6 | Datadog account + API key + app key + site | deployment pipeline + monitors; backend fetch_logs | Keshav | open |
| B7 | LangFuse cloud account (public + secret key) | backend tracing | Keshav | open |
| B8 | Microsoft Teams incoming webhook URL | notifications (GHA) | Keshav | open |
| B9 | GitHub PAT (`repo` scope) for cross-repo secret push + Function bridge | infra 4.1, Function bridge | Keshav | open |

## Open Reconciliations (decide before the affected task)

| # | Item | Affects | Status / resolution |
|---|------|---------|---------------------|

_None open._ Resolved R1–R6 are in [history.md](history.md).

## History

Closed blockers, resolved reconciliations and the full change log moved to
[history.md](history.md) on 2026-08-24 — they are audit record, not live state, and every
`/implement-phase` run was paying ~4K tokens to re-read them. Nothing in the build loop
reads history.md; append to it, never to this file.
