# Sentinel Phase 2 — Implementation State

> Live execution state. `/implement-phase` reads this first and updates it after every task.
> Planning-side state (architecture decisions) stays in [architecture/decisions.md](../architecture/decisions.md).
>
> Last updated: 2026-08-15

## Current Position

| Field | Value |
|-------|-------|
| **Active category** | infra — **in progress** |
| **Active phase** | 3 — Compute & Networking Modules |
| **Active branch** | _none — phase 3 not started_ |
| **Active PR** | _none_ |
| **Current task** | 3.1 — AKS module (⚠ **B11 halts 3.5** — do it before or during this phase) |
| **Tasks verified** | 6 / 58 |
| **Phases merged** | 2 / 16 |
| **Branch model** | Per repo. **infra + deployment:** `main` → `dev/<cat>-phase-<M>-<slug>` → PR back to `main` (no release branch). **backend (`Sentinel`):** `release-phase-2` → `dev/backend-phase-<M>-<slug>` → PR back to `release-phase-2`; `release-phase-2` → `main` once, at the end of Phase 2, and `main` takes nothing else. See [README §6](README.md#6-git-model--one-branch--one-pr-per-phase). |
| **Tracker commits** | straight to `main` of this repo (`sentinel-brain`) — no branch, no PR. One phase = one code PR + tracker commits here. |
| **Control plane** | `sentinel-brain` (this repo). Code repos are siblings: `../Sentinel` (backend), `../Sentinel-deployment`, `../Sentinel-infra`. |

## Next Action

**⚠ FIRST: start the database.** It was stopped 2026-08-16 to conserve the free grant.

```powershell
az postgres flexible-server start -n sentinel-pg-0375 -g sentinel-rg
```

**`terraform plan` FAILS while it is stopped** — not "plans a change", *errors*:
`400 ServerStoppedError` when the provider tries to refresh the administrator and database
sub-resources. Start it before running any Terraform, not just before connecting. Azure
auto-starts it after 7 days regardless.

**Then: build task 2.3 — Key Vault module.** 2.1 (ACR) and 2.2 (PostgreSQL) are
`done-pending-review` and applied. 2.3 is the last of the phase, then review + PR + gate.
It is also the **first thing that exercises R5's RBAC Administrator grant** — if it ever
fails in CI with `AuthorizationFailed`, R5 is the diagnosis.

> **Process note (2026-08-15):** commit `1c8e41d` (the `azq` helper fix + runbook correction)
> landed **directly on `Sentinel-infra` `main`** after PR #1 merged, outside the one-phase-one-PR
> model. Justified at the time as a post-merge repair on an unprotected repo — but it is a
> deviation and is recorded here rather than left silent. Future out-of-phase repairs in the
> sibling repos should use a `fix/*` branch + PR, matching the backend convention.

**The git workflow is clear.** B13 and B14 closed (2026-07-26). `fix/*` may now target
`release-phase-2` (2026-08-15).

**Halting prerequisites for Phase 1: none remaining.**
- **R3 (region) — RESOLVED 2026-08-15 → `canadacentral`.**
- **C1–C9 — RESOLVED 2026-08-15.** Nine architecture conflicts found by
  `architecture-warden` before any code was written; see
  [architecture/decisions.md](../architecture/decisions.md).
- **rev-9 identity rebuild — DECIDED 2026-08-15.** The CI identity is a User-Assigned
  Managed Identity, not an app registration, because the subscription sits in the
  **uwindsor.ca** tenant where the owner has no directory rights.

**Environment facts (confirmed 2026-08-15):**

| Field | Value |
|-------|-------|
| Tenant | University of Windsor · `uwindsor.ca` · `12f933b3-3d61-4b19-9a4d-689021de8cc9` |
| Subscription | Azure for Students · `174e25ca-ab82-4671-a913-9c2f66e5924d` · **Owner** · Active · $0 spent |
| Region | `canadacentral` |
| `sentinel-rg` | ✅ created 2026-08-15, `provisioningState: Succeeded` |
| Entra admin principal | `245bb98a-95a4-4f9d-930a-fcf3122dcea1` · `arri@uwindsor.ca` (→ `PG_ADMIN_OBJECT_ID` / `PG_ADMIN_PRINCIPAL_NAME`) |
| **Directory policy** | **Proven 2026-08-15** via `GET /v1.0/policies/authorizationPolicy`: `allowedToCreateApps: false`, `allowedToCreateSecurityGroups: false`, `allowedToReadOtherUsers: true`, `allowedToCreateTenants: true`. Read works; **all directory writes are denied at tenant-policy level.** This is the hard evidence that rev-9 was necessary, not precautionary. |
| Quota (`canadacentral`) | ✅ `Standard Basv2 Family vCPUs` limit **10** (AKS `B2ats_v2` needs 2) · `Total Regional vCPUs` limit **6** — the binding cap · all used = 0 |
| Resource providers | Registered 2026-08-15: Compute, ContainerService, ContainerRegistry, DBforPostgreSQL, KeyVault, EventGrid, Web, Storage, ManagedIdentity, OperationalInsights. A fresh subscription has these **unregistered**, which fails the first apply with a misleading error. |
| Local toolchain | terraform 1.15.8 · az 2.89.1 · tflint 0.64.0 · gitleaks 8.30.1 · actionlint 1.7.12 — all installed 2026-08-15. `tfsec` (optional, unavailable on winget) and `yamllint` (optional) remain absent and will report SKIPPED. |

**B1 and B2 are closed**, so Phase 1 is no longer offline-only: state storage exists and a
real `terraform init` succeeds against it. **B3** (the `sentinel-gha` UAMI bootstrap) is the
last one, and task 1.3 both writes and executes it.

**Resolved during Phase 1:** R3 (region), R4 (two-tenant identity split), R5 (CI identity
could not create role assignments), C1–C9, C12 (storage name collision), C13 (`actionlint`
gate defect — merged as `Sentinel` PRs #15/#16), and the shellcheck gate gap (`Sentinel`
PR #17, open).

**Owner action outstanding:**
- Sign off [Sentinel-infra#1](https://github.com/Keshav0375/Sentinel-infra/pull/1).
- Merge [Sentinel#17](https://github.com/Keshav0375/Sentinel/pull/17) (shellcheck in the gate).
- Before **infra Phase 3**: finish **B11** — register `sentinel-tf-identity` in the personal
  Entra tenant with a federated credential + Application Administrator.
- Set the GitHub *variables* on `Sentinel-infra` (§9) before **task 4.3** —
  `AZURE_CLIENT_ID=c9ed809b-eca3-4ecc-8678-5dbfb91be5ae`, `AZURE_TENANT_ID`,
  `AZURE_SUBSCRIPTION_ID`, `AZURE_LOCATION=canadacentral`, `PG_ADMIN_OBJECT_ID`,
  `PG_ADMIN_PRINCIPAL_NAME`, plus the `GH_PAT` secret.

## Phase Gate Ledger

A phase moves to `verified` only after the user confirms the feature works and the PR is
merged. Newest first.

| Date | Category | Phase | Branch | PR | Verified by | Notes |
|------|----------|-------|--------|----|-----|-------|
| 2026-08-23 | infra | 2 — Core Resource Modules | `dev/infra-phase-2-core-modules` | [#2](https://github.com/Keshav0375/Sentinel-infra/pull/2) | Keshav | Owner ran the checklist personally: ACR Standard, Postgres AAD-only, KV RBAC + Officer/User split, empty vault by design, gate PASS (6 ran). Live tests: Entra-token psql login; KV write→read→purge. Resolved R6; both reviewers' blockers fixed on-branch. |
| 2026-08-15 | infra | 1 — Foundations & Bootstrap | `dev/infra-phase-1-foundations` | [#1](https://github.com/Keshav0375/Sentinel-infra/pull/1) | Keshav | `terraform plan` → **No changes**; both bootstrap scripts idempotent; gate PASS (5 ran); 5 federated credentials verified in Azure. Resolved R3, R4, R5, C1–C9, C12, C13. Closed B1, B2, B3, B10, B15. |

## Blockers

External dependencies that halt verification. Mirror any task-level BLOCKED here.
(Seeded from [architecture/decisions.md](../architecture/decisions.md) blockers — these gate infra Phase 1–4.)

| # | Blocker | Blocks | Owner | Status |
|---|---------|--------|-------|--------|
| B1 | ~~Azure subscription + `sentinel-rg` resource group~~ | — | Keshav | ✅ **CLOSED 2026-08-15.** Subscription `174e25ca-…` (Owner, Active); `sentinel-rg` created in `canadacentral`; 10 resource providers registered. |
| B2 | ~~Terraform state storage bootstrapped (state-rg + storage + container)~~ | — | Keshav | ✅ **CLOSED 2026-08-15.** `sentinel-state-rg` + `sentineltfstate0375` + `tfstate` container + operator blob RBAC, all created by `scripts/bootstrap-state.sh` and verified by a real `terraform init` reporting "Successfully configured the backend". **C12 materialized** — `sentineltfstate` was taken by another tenant; renamed across 7 files. |
| B3 | ~~`sentinel-gha` UAMI + 2 role assignments + first 2 federated credentials, then the 7-object import~~ | — | Keshav | ✅ **CLOSED 2026-08-15.** UAMI `sentinel-gha` (`clientId c9ed809b-eca3-4ecc-8678-5dbfb91be5ae`), Contributor on `sentinel-rg`, Storage Blob Data Contributor on `sentineltfstate0375`, **all 5 federated credentials** live, plus RBAC Administrator + state-RG Contributor (R5). Seven objects imported, three credentials created by apply, `terraform plan` → **"No changes"**. rev-9 proven end to end: a managed identity does substitute for an app registration. |
| B4 | Anthropic API key | backend LLM calls; Key Vault seed | Keshav | open |
| B5 | OpenAI API key | backend fallback; Key Vault seed | Keshav | open |
| B6 | Datadog account + API key + app key + site | deployment pipeline + monitors; backend fetch_logs | Keshav | open |
| B7 | LangFuse cloud account (public + secret key) | backend tracing | Keshav | open |
| B8 | Microsoft Teams incoming webhook URL | notifications (GHA) | Keshav | open |
| B9 | GitHub PAT (`repo` scope) for cross-repo secret push + Function bridge | infra 4.1, Function bridge | Keshav | open |
| B10 | ~~Entra `sentinel-db-admins` security group~~ → record your own Entra user object ID + UPN (`az ad signed-in-user show`); DB roles still created via `pgaadauth_create_principal` | infra Postgres (Entra-only auth), all DB access | Keshav | ✅ **CLOSED 2026-08-15 — superseded by rev-9.** No group is created; Postgres Entra admins are attached directly (human + backend UAMI). Needs no directory write. |
| B11 | ~~Personal Entra tenant~~ → register `sentinel-tf-identity` there with a federated credential for `Keshav0375/Sentinel-infra` + the **Application Administrator** directory role | infra 3.5, backend 5.6 | Keshav | **partly closed 2026-08-15.** Tenant `eae0d3c6-af22-4b70-ad3b-12d625a06139` · `keshavk5655gmail.onmicrosoft.com` · **Entra ID Free** · no subscription (intended). **App registration PROVEN** — a `sentinel-permcheck` app was created there successfully (`publisherDomain` confirmed the personal tenant), so the R4 design is validated against reality, not assumed. Note `az ad app create` patches by display name rather than erroring, so the bootstrap is naturally idempotent. Remaining: `sentinel-tf-identity` + its directory role, before infra Phase 3. |
| B15 | ~~`quality_gate.py` runs `actionlint` as a **required** check with no argv path, so it never gets pruned and hard-FAILs on a repo with no `.github/workflows/`~~ | — | Claude | ✅ **CLOSED 2026-08-15 — conflict C13 fixed.** `IMPLICIT_PATHS` extends the gate's existing "no such path yet" skip semantics to tools that discover their own inputs. Verified both ways: SKIPPED against workflow-less `Sentinel-infra`, still runs and reports findings where workflows exist. On `fix/quality-gate-implicit-paths`; **PR still to be opened — `gh` not authenticated.** |
| B12 | AKS OIDC issuer + workload identity enabled; backend UAMI + federated credential; `sentinel-backend` ServiceAccount annotated | backend runtime KV/DB access (no pod secret) | Keshav | open |
| B13 | ~~`release-phase-2` created in `Sentinel-infra` + `Sentinel-deployment`~~ | — | Keshav | ✅ **CLOSED 2026-07-26 — obsolete.** Branch model changed: those two repos have no release train, `dev/*` PRs into their own `main`. Nothing to create. |
| B14 | ~~Updated `guard-main-source.yml` + `ci.yml` merged into `release-phase-2` **and** `main` of `Sentinel`~~ | — | Keshav | ✅ **CLOSED 2026-07-26.** `planning/phase-2-e2e` merged to `main` (PR #14, `5b97232`); `release-phase-2` fast-forwarded to match. Both protected branches now carry the rewritten guard, `ci.yml` and `scripts/quality_gate.py`. |

## Open Reconciliations (decide before the affected task)

| # | Item | Affects | Status / resolution |
|---|------|---------|---------------------|
| R1 | GitHub owner `keshxvDev` in arch docs vs real `Keshav0375`; repo casing | infra 1.3, 4.1, 3.3 | ✅ **RESOLVED 2026-07-11** — all arch docs updated to `Keshav0375` + real repo casing via `/sentinel-planner`; OIDC subjects noted case-sensitive. |
| R2 | Backend repo GitHub name = `Sentinel` (capital S) | infra 4.1, Function bridge dispatch target | ✅ **RESOLVED 2026-07-11** — all three remotes confirmed `Keshav0375/Sentinel-infra`, `.../Sentinel-deployment`, `.../Sentinel`. |
| R3 | Azure region for all resources (arch examples use `eastus`) | all infra modules | ✅ **RESOLVED 2026-08-15 → `canadacentral`.** Chosen for proximity, Canadian residency, and lower burstable-SKU contention than `eastus`. `var.location` still has **no default** — supplied via the `AZURE_LOCATION` GitHub variable (C5). ✅ **Quota confirmed 2026-08-15:** `Standard Basv2 Family vCPUs` limit **10** (AKS `B2ats_v2` needs 2) and `Total Regional vCPUs` limit **6** — the real cap, and enough for the single-node scale-to-zero design. No quota-increase request needed. |
| R4 | Inbound Entra bearer auth (`api://sentinel-backend` + `Incident.Write`) needs an app registration — a directory write the uwindsor.ca tenant denies | infra 3.5, backend 5.6, B11 | ✅ **RESOLVED 2026-08-15 → two-tenant identity split.** UWindsor IT is **not an option** (owner decision: no institutional involvement). The two app registrations — and only those two — move to a **personally-owned Entra tenant**; every Azure resource and all three UAMIs stay in the school tenant, because they hold RBAC on school resources and would break if relocated. **No stored secret:** the caller is a `sentinel-gha-client` app registration carrying a GitHub-OIDC federated credential — the same trust source as the UAMI — and `azure/login@v2` supports `allow-no-subscriptions`, so the identity tenant needs no subscription and costs $0. Note the `sentinel-gha` UAMI **cannot** hold the app role: app-role assignment is a within-tenant directory operation with no cross-tenant form. Accepted costs: two tenants to reason about, an aliased `azuread` provider, a second bootstrap seam. Design in `infra.md` §4.4; execution tracked as **B11**. |
| R5 | `sentinel-gha` holds only Contributor, which **cannot create role assignments** (`notActions` include `Microsoft.Authorization/*/Write`). Phases 2-3 declare six Terraform-managed assignments | infra 2.3, 3.1, 3.6, `ci_destroy_infra` | ✅ **RESOLVED 2026-08-15 → RBAC Administrator on `sentinel-rg` + Contributor on `sentinel-state-rg`.** Found by `code-reviewer` at the phase-1 gate; the architecture had the same gap, so this was a missing decision rather than a code defect. Phase 1 passed only because every apply ran locally as subscription **Owner** — CI had never exercised the identity. Chose **Role Based Access Control Administrator** over Owner/User Access Administrator because its built-in ABAC condition forbids assigning Owner, UAA or itself, so CI cannot escalate — which matters for `pull_request`-triggered workflows. Both assignments are live and imported. |
| R6 | CI cannot purge a soft-deleted Key Vault — deleted vaults live at **subscription scope** and `sentinel-gha` holds nothing there, so `ci_destroy_infra`'s purge 403s silently and the next apply fails on the reserved name | infra 4.3, teardown | ✅ **RESOLVED 2026-08-16 → teardown is Owner-run and local; `ci_destroy_infra.yml` removed.** Found and *reproduced* by `code-reviewer` at the phase-2 gate; it falsified the justification for the 2026-08-15 soft-delete decision. Rejected a subscription-scope Key Vault Contributor grant (would let CI manage any vault in the subscription) and a custom purge-only role (extra bootstrap + role to maintain). Net effect: the CI identity ends up with **less** standing privilege, and infra ships 3 workflows instead of 4. |

## Change Log

- **2026-08-15** — **rev-9: identity plane rebuilt on managed identities; R3 closed;
  C1–C9 resolved.** Triggered by discovering the subscription is **Azure for Students inside
  the uwindsor.ca tenant** — Owner on the subscription, **no directory rights**. Every rev-5
  identity construct was a directory object, so B3/B10/B11 were unbuildable as designed.
  **(a)** CI identity → `azurerm_user_assigned_identity.sentinel_gha` + 5
  `azurerm_federated_identity_credential` children (was `azuread_application` + SP + 5 app
  federated creds). Closes B3's design gap.
  **(b)** `sentinel-db-admins` group deleted → two direct Postgres Entra admins (human as
  `User`, backend UAMI as `ServicePrincipal`). **Closes B10.** Cost: admin changes are now a
  Terraform apply, not an Entra membership edit.
  **(c)** **B11 cannot be rescued** — only an app registration can define an API audience +
  app role. New **R4**; `infra.md` §4.4 carries a ⛔ banner; halts infra 3.5 + backend 5.6.
  **(d)** **R3 → `canadacentral`.** `var.location` keeps no default; CI supplies it via the
  new `AZURE_LOCATION` GitHub variable.
  **(e)** **C1–C9 resolved** before a line of code (see decisions.md): RG is a **data source**
  (C1); state account gets **Storage Blob Data Contributor** + backend `use_azuread_auth`/
  `use_oidc` — without which *every* CI `terraform init` fails (C2); **all five** bootstrap
  objects imported, not one (C3); `subscription_id` wired into the provider (C4); `location`
  passed as `-var` (C5); **`GITHUB_PAT` → `GH_PAT`**, the old name being illegal under
  GitHub's reserved prefix (C6); `AZURE_*` are `vars.` not `secrets.` (C7); `github_owner`
  stays a variable (C8); versions pinned — `terraform >= 1.9`, `azurerm ~> 4.0`,
  `integrations/github ~> 6.0`, **`azuread` dropped entirely** (C9).
  **(f)** New **B15/C13** — `quality_gate.py` fails `actionlint` on any repo without
  `.github/workflows/`, contradicting its own docstring and making infra phases 1–3 and
  deployment phase 1 unable to report green. Fix pending go-ahead.
  **(g)** Local toolchain installed: terraform, az, tflint, gitleaks, actionlint.
  Unchanged: 58 tasks, 16 phases, branch model, HITL, the human phase gate.

- **2026-07-26** — **rev-8: per-repo branch model + agents on Opus.** The single "all repos use
  `release-phase-2`" rule is replaced by a per-repo integration branch:
  **(a) `Sentinel-infra` and `Sentinel-deployment` use `main` directly** — `main` →
  `dev/<cat>-phase-<M>-<slug>` → PR → `main`, one PR per phase, no release train. Those repos
  have no branch protection, no external consumers and one author, so a release train was
  ceremony with no reviewer on the other end. This closes **B13** as obsolete.
  **(b) `Sentinel` keeps the release train** — `release-phase-2` → `dev/backend-phase-<M>-<slug>`
  → PR → `release-phase-2`, and `main` accepts exactly one merge (`release-phase-2`) at the end
  of Phase 2. Its `main` is the protected showcase branch, which is what justifies the extra step.
  **(c) `planning/phase-2-e2e` retired** — merged to `Sentinel` `main` as PR #14 (`5b97232`);
  `release-phase-2` fast-forwarded `cac026e..5b97232` to match, so both protected branches now
  carry the rewritten `guard-main-source.yml`, the `dev`-aware `ci.yml`, and
  `scripts/quality_gate.py`. This closes **B14**. Planning now lives only in `sentinel-brain`.
  **(d)** All four subagents moved `model: sonnet` → **`model: opus`**.
  **(e)** Docs updated to match: [CLAUDE.md](../CLAUDE.md), [README.md](../README.md),
  [README §6](README.md#6-git-model--one-branch--one-pr-per-phase), [TODO.md](TODO.md), the
  phase-report template, infra task 1.1, and `/implement-phase` (Branch model, Step 3, Step 6).
  Unchanged: 58 tasks, 16 phases, the `dev/` prefix, one-phase-one-PR, the human phase gate,
  and tracker commits going straight to brain `main`.

- **2026-07-26** — **rev-7: control plane split out into `sentinel-brain`.** Architecture, this
  tracker, all Claude agents/skills/commands and phase reports moved out of the `Sentinel` code
  repo into this repo. The three code repos now carry **code + CI only** — no `Planning/`, no
  `.claude/`. New layout: `architecture/` (index + `backend.md` / `deployment.md` / `infra.md` +
  `decisions.md`), `implementation/` (TODO, STATE, `tasks/<category>/phase-*/`), `reports/`,
  `reference/`, `archive/mvp-phase-1/`. Consequences:
  **(a)** every task's **Arch refs** now reads `architecture/<repo>.md §X` (was
  `Planning/Phase-2/sentinel/ARCHITECTURE.md §X`), and task folders are
  `tasks/{infra,deployment,backend}/` (was `category-N-*`).
  **(b)** Agent repo paths are now siblings — backend is `../Sentinel`, not `.`.
  **(c)** **Tracker commits go straight to brain `main`**, superseding rev-6's two-branch /
  two-PR tracker model: the tracker no longer lives in a protected repo, so that ceremony is
  gone. One phase = one code PR + tracker commits here.
  **(d)** Phase-1/MVP docs are quarantined in `archive/` behind stale banners, a permission deny
  rule, and explicit "never read this" instructions in `CLAUDE.md` and all four agents — Phase 2
  replaced that design wholesale, so loading it causes wrong builds.
  **(e)** Deployment phase 3 renamed `phase-3-demo-scenarios` → `phase-3-scenario-branches`, task
  `task-1-demo-prs-workflow` → `task-1-scenario-branches`, matching the rev-5 pivot.
  **(f)** Added `reports/` + a phase-report template for short user-facing phase summaries.
  Unchanged: 58 tasks, 16 phases, the `dev/*` → `release-phase-2` branch model in code repos,
  and every blocker below.

- **2026-07-26** — **rev-6 build-loop repair.** Audit of architecture ↔ implementation ↔ tasks ↔
  human gate found three defects that would have broken or falsified the first phase. Fixed:
  **(1) Branch model** — phases now branch from `release-phase-2` with a **`dev/`** prefix (was
  `impl/` off `main`) and PR back into `release-phase-2`; `release-phase-2` → `main` is a single
  final merge. `ci.yml` branch-convention accepts `dev`; `guard-main-source.yml` allows
  `release-phase-2 <- dev/* | planning/phase-2-e2e`. Previously **every** phase PR failed two
  required checks by construction. **(2) Quality gate** — `terraform validate` now runs after
  `terraform init -backend=false` (bare `validate` always failed → infra could never go green);
  backend pytest globs extended to `test_memory/`, `test_infra/`, `test_providers/`, `test_eval/`,
  `test_config.py` (backend phases 1, 2 and 6 previously reported green with **zero** of their own
  tests executed); non-existent path args are pruned so the gate is safe mid-build.
  **(3) Tracker commits** — defined: they ride the phase's `dev/` branch in `Sentinel`, so an
  infra/deployment phase is 2 branches + 2 PRs closed at one gate. **(4) Stale rev-5 sweep** —
  infra 1.1/2.2/2.3/4.3 and backend 5.1 bodies reconciled with their own rev-5 callouts; both
  `env-examples/` de-staled (`db_password`, `SENTINEL_API_TOKEN`). **(5) Open R-items** are now a
  halting prerequisite in `/implement-phase` Step 4.1 — R3 (region) can no longer be silently
  defaulted to `eastus`. **(6)** Legacy `/implement` + `/fire` retired, `/review` rewritten for
  Phase-2 invariants. New blockers **B13** (create `release-phase-2` in the two sibling repos) and
  **B14** (guard workflow must reach `release-phase-2` + `main` before it takes effect).
- **2026-07-12** — **rev-5 security + ground-truth overhaul** applied across all architecture
  docs (via `/sentinel-planner`; logged in [architecture/decisions.md](../architecture/decisions.md) decision
  log). Four approved changes: (1) `ci_destroy_infra` full-teardown workflow; (2) sentinel-
  deployment pivot to 30 scenario branches (3 cases) — `ci_demo_prs.yml` removed, branches
  become the eval dataset; (3) Azure-native dynamic secrets — Entra-only PostgreSQL, Key Vault
  rotation Function, AKS workload identity; (4) inbound Entra bearer auth on the backend
  (deletes `sentinel-api-token`). New bootstrap blockers **B10–B12** added (Entra DB admin
  group, backend app registration, AKS workload identity). TODO tracker updated with new/
  modified tasks (see TODO.md); task total re-baselined.
- **2026-07-11** — R1 + R2 resolved: architecture docs reconciled from placeholder
  `keshxvDev`/lowercase repos to real `Keshav0375` + `Sentinel-infra`/`Sentinel-deployment`/
  `Sentinel` casing (via `/sentinel-planner`, logged in Phase-2 STATE decision log). All three
  git remotes confirmed. R3 (region) still open.
- **2026-07-11** — Implementation tracker created. Full decomposition: 3 categories, 16
  phases, 55 tasks. Git model set: one branch + one PR per phase, merged after human
  phase-gate; no Claude attribution on commits/PRs.
