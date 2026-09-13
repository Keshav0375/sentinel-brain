# Sentinel Phase 2 — Implementation State

> Live execution state. `/implement-phase` reads this first and updates it after every task.
> Planning-side state (architecture decisions) stays in [architecture/decisions.md](../architecture/decisions.md).
> Closed blockers, resolved R-items and the change log live in [history.md](history.md) — the
> build loop never reads that file. **Keep this one live-only; append history there.**
>
> Last updated: 2026-09-13

## Current Position

| Field | Value |
|-------|-------|
| **Active category** | infra — **in progress** |
| **Active phase** | 6 — Dynamic Deployments & Workflows |
| **Active branch** | `fix/run-names-and-dispatch-edge-cases` (infra) |
| **Active PR** | [Sentinel-infra#11](https://github.com/Keshav0375/Sentinel-infra/pull/11) → `main` — post-merge repairs, awaiting review |
| **Current task** | _infra phase 6 is merged; three defects found by reading its run history are fixed in PR #11._ The phase-6 **gate row is still unwritten** — the code landed without a sign-off being recorded. |
| **Tasks verified** | 22 / 72 — phase 6's 8 tasks are merged but not gate-signed |
| **Phases merged** | 6 / 18 — infra 1-6 |
| **Branch model** | Per repo. **infra + deployment:** `main` → `dev/<cat>-phase-<M>-<slug>` → PR back to `main` (no release branch). **backend (`Sentinel`):** `release-phase-2` → `dev/backend-phase-<M>-<slug>` → PR back to `release-phase-2`; `release-phase-2` → `main` once, at the end of Phase 2, and `main` takes nothing else. See [README §6](README.md#6-git-model--one-branch--one-pr-per-phase). |
| **Tracker commits** | straight to `main` of this repo (`sentinel-brain`) — no branch, no PR. One phase = one code PR + tracker commits here. |
| **Control plane** | `sentinel-brain` (this repo). Code repos are siblings: `../Sentinel` (backend), `../Sentinel-deployment`, `../Sentinel-infra`. |

## Next Action

**Review and merge [Sentinel-infra#11](https://github.com/Keshav0375/Sentinel-infra/pull/11), then write the infra phase-6 gate row.**

Infra phase 6 merged as [#8](https://github.com/Keshav0375/Sentinel-infra/pull/8) on 2026-08-25
(`56d2e82`), followed by two repairs found in use — [#9](https://github.com/Keshav0375/Sentinel-infra/pull/9)
`d821b7f` (a destroy that reaches zero, an apply that seeds its own vault) and
[#10](https://github.com/Keshav0375/Sentinel-infra/pull/10) `58261de` (`plan --scope all`
before the platform exists). **No ledger row was ever written for the phase**, so the gate is
open on a phase whose code is on `main`. Sign it or say what is missing.

PR #11 fixes three defects found by reading the Deploy run history after the merge: identical
run names on every dispatch, a `verify` job that false-alarmed on runs the guards had refused,
and an App Service F1 quota that no preflight check could see.

**Proven live since the last update:**
- **Destroy works, twice.** 2026-09-12: `destroy · deployment` removed 22 resources, then
  `destroy · platform` removed 11. The subscription now holds only `rg-sentinel-bootstrap` and
  `NetworkWatcherRG` — the zero-cost floor, confirmed by `az group list`.
- ✅ **[Sentinel#18](https://github.com/Keshav0375/Sentinel/pull/18) merged** 2026-08-26 —
  `main`'s gate is 11 checks. This owner action is done.

**Still open as known gaps:**
- ⚠️ **Pause / Resume has never run.** `gh run list --workflow ci_pause.yml` returns nothing —
  zero runs, ever. It is the only phase-6 deliverable with no execution behind it, and it needs
  a live estate to act on.
- ⚠️ `identity.tf` deleted — a declared provider is configured even with every resource at
  `count = 0`, so an unauthenticable `azuread` broke every plan. Returns when
  `sentinel-tf-identity` carries `environment:*` federated credentials.
- ⚠️ `gha-ops` cannot-delete is proven by role inspection, not by a refused delete.
- ⚠️ Namespaces have never been created, so the kubelogin path is unexercised.
- ⚠️ The infra quality gate has never run `shellcheck`, `actionlint`, `tflint`, `tfsec`,
  `yamllint` or `gitleaks` locally — none are on the author's PATH. CI runs Terraform only.

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
