# Sentinel Phase 2 — Implementation State

> Live execution state. `/implement-phase` reads this first and updates it after every task.
> Planning-side state (architecture decisions) stays in [architecture/decisions.md](../architecture/decisions.md).
>
> Last updated: 2026-07-26

## Current Position

| Field | Value |
|-------|-------|
| **Active category** | infra (not yet started) |
| **Active phase** | 1 — Foundations & Bootstrap |
| **Active branch** | _none — phase not started_ |
| **Active PR** | _none_ |
| **Current task** | 1.1 — Repo skeleton + provider/backend/vars config |
| **Tasks verified** | 0 / 58 |
| **Phases merged** | 0 / 16 |
| **Branch model** | Per repo. **infra + deployment:** `main` → `dev/<cat>-phase-<M>-<slug>` → PR back to `main` (no release branch). **backend (`Sentinel`):** `release-phase-2` → `dev/backend-phase-<M>-<slug>` → PR back to `release-phase-2`; `release-phase-2` → `main` once, at the end of Phase 2, and `main` takes nothing else. See [README §6](README.md#6-git-model--one-branch--one-pr-per-phase). |
| **Tracker commits** | straight to `main` of this repo (`sentinel-brain`) — no branch, no PR. One phase = one code PR + tracker commits here. |
| **Control plane** | `sentinel-brain` (this repo). Code repos are siblings: `../Sentinel` (backend), `../Sentinel-deployment`, `../Sentinel-infra`. |

## Next Action

Start **infra Phase 1** — branch `dev/infra-phase-1-foundations` off `Sentinel-infra` `main`.

**The git workflow is clear.** B13 and B14 are both closed (2026-07-26): the branch model
changed so infra/deployment need no release branch, and `Sentinel` `release-phase-2` was
fast-forwarded to `main` (`cac026e..5b97232`), so it now carries the rewritten guard + `ci.yml`
+ `scripts/quality_gate.py`.

**One halting prerequisite remains:**
- **R3 — the Azure region.** Halting for infra 1.1 (`/implement-phase` Step 4.1). The agent
  will not default it to `eastus`.

The Terraform *code* for Phase 1 can be written without an Azure account, but nothing can
`plan`/`apply` or be verified until B1–B3 exist. `/implement-phase` writes BLOCKED reports for
any task whose verification needs an unavailable resource.

## Phase Gate Ledger

A phase moves to `verified` only after the user confirms the feature works and the PR is
merged. Newest first.

| Date | Category | Phase | Branch | PR | Verified by | Notes |
|------|----------|-------|--------|----|-----|-------|
| — | — | — | — | — | — | _no phases completed yet_ |

## Blockers

External dependencies that halt verification. Mirror any task-level BLOCKED here.
(Seeded from [architecture/decisions.md](../architecture/decisions.md) blockers — these gate infra Phase 1–4.)

| # | Blocker | Blocks | Owner | Status |
|---|---------|--------|-------|--------|
| B1 | Azure subscription + `sentinel-rg` resource group | All infra apply/verify (§10 bootstrap) | Keshav | open |
| B2 | Terraform state storage bootstrapped (state-rg + storage + container) | infra 1.2 verify, all applies | Keshav | open |
| B3 | OIDC SP + first federated credential created via `az` | infra 1.3 verify | Keshav | open |
| B4 | Anthropic API key | backend LLM calls; Key Vault seed | Keshav | open |
| B5 | OpenAI API key | backend fallback; Key Vault seed | Keshav | open |
| B6 | Datadog account + API key + app key + site | deployment pipeline + monitors; backend fetch_logs | Keshav | open |
| B7 | LangFuse cloud account (public + secret key) | backend tracing | Keshav | open |
| B8 | Microsoft Teams incoming webhook URL | notifications (GHA) | Keshav | open |
| B9 | GitHub PAT (`repo` scope) for cross-repo secret push + Function bridge | infra 4.1, Function bridge | Keshav | open |
| B10 | Entra `sentinel-db-admins` security group created + set as Postgres Entra admin; SP + backend UAMI added; DB roles created (`pgaadauth_create_principal`) | infra Postgres (Entra-only auth), all DB access | Keshav | open |
| B11 | Backend Entra app registration (`api://sentinel-backend` + `Incident.Write` role) + role grant to `sentinel-gha` SP | backend inbound auth, incident workflow token | Keshav | open |
| B12 | AKS OIDC issuer + workload identity enabled; backend UAMI + federated credential; `sentinel-backend` ServiceAccount annotated | backend runtime KV/DB access (no pod secret) | Keshav | open |
| B13 | ~~`release-phase-2` created in `Sentinel-infra` + `Sentinel-deployment`~~ | — | Keshav | ✅ **CLOSED 2026-07-26 — obsolete.** Branch model changed: those two repos have no release train, `dev/*` PRs into their own `main`. Nothing to create. |
| B14 | ~~Updated `guard-main-source.yml` + `ci.yml` merged into `release-phase-2` **and** `main` of `Sentinel`~~ | — | Keshav | ✅ **CLOSED 2026-07-26.** `planning/phase-2-e2e` merged to `main` (PR #14, `5b97232`); `release-phase-2` fast-forwarded to match. Both protected branches now carry the rewritten guard, `ci.yml` and `scripts/quality_gate.py`. |

## Open Reconciliations (decide before the affected task)

| # | Item | Affects | Status / resolution |
|---|------|---------|---------------------|
| R1 | GitHub owner `keshxvDev` in arch docs vs real `Keshav0375`; repo casing | infra 1.3, 4.1, 3.3 | ✅ **RESOLVED 2026-07-11** — all arch docs updated to `Keshav0375` + real repo casing via `/sentinel-planner`; OIDC subjects noted case-sensitive. |
| R2 | Backend repo GitHub name = `Sentinel` (capital S) | infra 4.1, Function bridge dispatch target | ✅ **RESOLVED 2026-07-11** — all three remotes confirmed `Keshav0375/Sentinel-infra`, `.../Sentinel-deployment`, `.../Sentinel`. |
| R3 | Azure region for all resources (arch examples use `eastus`) | all infra modules | **OPEN** — confirm free-tier availability of B2ats_v2 + F1 in chosen region before infra Phase 2/3. |

## Change Log

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
