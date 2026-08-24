# Sentinel Phase 2 — Implementation State

> Live execution state. `/implement-phase` reads this first and updates it after every task.
> Planning-side state (architecture decisions) stays in [architecture/decisions.md](../architecture/decisions.md).
> Closed blockers, resolved R-items and the change log live in [history.md](history.md) — the
> build loop never reads that file. **Keep this one live-only; append history there.**
>
> Last updated: 2026-08-15

## Current Position

| Field | Value |
|-------|-------|
| **Active category** | infra — **in progress** |
| **Active phase** | 4 — Cross-Repo Wiring & CI |
| **Active branch** | `dev/infra-phase-4-wiring-and-ci` |
| **Active PR** | [Sentinel-infra#4](https://github.com/Keshav0375/Sentinel-infra/pull/4) → `main` — awaiting phase gate |
| **Current task** | _phase 4 code-complete; both reviews addressed_ — PR #4 awaiting gate |
| **Tasks verified** | 12 / 58 |
| **Phases merged** | 3 / 16 |
| **Branch model** | Per repo. **infra + deployment:** `main` → `dev/<cat>-phase-<M>-<slug>` → PR back to `main` (no release branch). **backend (`Sentinel`):** `release-phase-2` → `dev/backend-phase-<M>-<slug>` → PR back to `release-phase-2`; `release-phase-2` → `main` once, at the end of Phase 2, and `main` takes nothing else. See [README §6](README.md#6-git-model--one-branch--one-pr-per-phase). |
| **Tracker commits** | straight to `main` of this repo (`sentinel-brain`) — no branch, no PR. One phase = one code PR + tracker commits here. |
| **Control plane** | `sentinel-brain` (this repo). Code repos are siblings: `../Sentinel` (backend), `../Sentinel-deployment`, `../Sentinel-infra`. |

## Next Action

**Build infra Phase 4 — Cross-Repo Wiring & CI** — the last infra phase. 4.2 runner image →
4.3 workflows → 4.4 root wiring; **4.1 is gated on B9** and can be done last.

Phase 4 is different in kind from 1–3: those built resources with a locally-run,
subscription-Owner apply. Phase 4 hands the keys to CI, so it is the **first phase that
exercises the identity plane for real** — three things have never once executed:

1. the GitHub→Azure **OIDC round trip** (5 federated credentials, all created, none used);
2. **R5's RBAC Administrator** grant — every role assignment so far was created by Owner;
3. the **identity-tenant** azuread provider authenticating as `sentinel-tf-identity`.

Expect the first CI run to fail on one of these. That is the phase working as intended,
not a regression.

- **B9 (GitHub PAT, `repo` scope) blocks 4.1** — the github provider cannot push a secret
  without it. Sequence 4.2/4.3/4.4 first; 4.1 last, once B9 lands.
- B4–B8 stay open and do **not** block Phase 4. The vault is empty by design; 4.1 pushes
  *references and variables*, not the secret values.
- Reminder: AKS is **ARM64** (`B2pls_v2`), so 4.2's runner image and every later backend
  image must build `linux/arm64`.
- Both `Sentinel` gate PRs (#17 shellcheck, #18 Python checks) are **still unmerged** —
  merge them before Phase 4 or CI runs an older gate than your local one.

## Next Action

**Close the infra phase-4 gate.** All four tasks are `done-pending-review`, gate PASS (9 ran),
PR #4 open. Two follow-ups are owner actions, not build work:

- ⛔ **Identity-tenant federated credentials** (BOOTSTRAP step 4b) — `sentinel-tf-identity`
  has only `ref:refs/heads/main`. A PR plan completes the whole azurerm refresh and then dies
  at `AADSTS700213` on the azuread client. 2 `az` commands; needs an identity-tenant login.
- ✅ **Runner image built and pushed by CI** — `ci_runners.yml` succeeded on the merge to main; `sentinel-acr0375/ci-runner:latest` is live. Task 4.2 verified end to end.
- ⚠️ **PR [#5](https://github.com/Keshav0375/Sentinel-infra/pull/5)** open — ten review fixes that never reached disk, plus the environment-credential bootstrap and a database start-guard for CI.

**Proven live 2026-08-24:** the GitHub→Azure OIDC round trip, R5's RBAC Administrator grant
and the remote state blob all work under the CI identity, on their first-ever execution.

After the gate, infra is complete → **deployment phase 1**.

## Phase Gate Ledger

A phase moves to `verified` only after the user confirms the feature works and the PR is
merged. Newest first.

| Date | Category | Phase | Branch | PR | Verified by | Notes |
|------|----------|-------|--------|----|-----|-------|
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
