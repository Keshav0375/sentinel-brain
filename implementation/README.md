# Sentinel Phase 2 — Implementation Tracker

> **This folder is the execution source of truth.** The design it implements lives in
> [`architecture/`](../architecture) (binding architecture + decision log). Here we track
> *building* it: what to build, in what order, whether it's done, and a per-task report of
> what shipped.
>
> Build driver: [`/implement-phase`](../.claude/skills/implement-phase/SKILL.md) — one
> orchestrator that builds a whole phase and closes it with a human sign-off.

---

## 1. How work is organized

```
Category  →  Phase (= 1 branch + 1 PR)  →  Task (= 1 commit, PR-sized)
```

- **3 categories**, one per code repo, implemented **in dependency order**:
  **infra → deployment → backend**. Infra first so deployment and backend build on real,
  provisioned ground truth.
- **16 phases** total. **Each phase is one git branch and one pull request** in its code repo.
- **58 tasks** total. Each task is one PR-sized commit on its phase branch, ships
  **unit + integration tests**, and must pass the category **quality gate** (§7).

The master checklist is [TODO.md](TODO.md) — headings + status only. The full technical
detail for each task lives in its own file (§2).

## 2. Folder map

| Path | What it is |
|------|-----------|
| [TODO.md](TODO.md) | Master tracker — every phase & task as `heading · file · status`. Lean by design. |
| [STATE.md](STATE.md) | Live execution state: current phase/branch/PR, phase-gate ledger, blockers, open reconciliations. |
| [_templates/task-template.md](_templates/task-template.md) | Schema every task file follows (spec + report + blocked). |
| [_templates/phase-report-template.md](_templates/phase-report-template.md) | Schema for the short user-facing report written at each phase gate. |
| `env-examples/` | Canonical `.env` reference per repo. |
| `tasks/infra/` | Infra tasks. [Index](tasks/infra/README.md) · 4 phases · 16 tasks. |
| `tasks/deployment/` | Deployment tasks. [Index](tasks/deployment/README.md) · 3 phases · 6 tasks. |
| `tasks/backend/` | Backend tasks. [Index](tasks/backend/README.md) · 9 phases · 36 tasks. |

Each `tasks/<category>/` has a `README.md` indexing its phases, and one `phase-M-*/` folder per
phase holding `task-K-*.md` files. **A task file is both the spec and the report** — the spec is
written up front and stays stable; Report / Tests / How-to-Verify are filled in on completion.
Finished-phase summaries for the user go in [`reports/`](../reports/README.md).

## 3. Where everything lives

This tracker is in **`sentinel-brain`**, not in any code repo. Brain drives the three code repos
from outside so they stay clean — no planning docs, no agents, no trackers, no reports in them.

```
Sentinel-development-project/
├── sentinel-brain/         ← this repo (architecture, tracker, agents, reports)
├── Sentinel/               ← backend
├── Sentinel-deployment/    ← target app
└── Sentinel-infra/         ← Terraform
```

| Category | Path from brain root | GitHub | Notes |
|----------|----------------------|--------|-------|
| **infra** | `../Sentinel-infra` | `Keshav0375/Sentinel-infra` | Terraform IaC. Currently bare (`.gitignore`, `LICENSE`, `README.md`). |
| **deployment** | `../Sentinel-deployment` | `Keshav0375/Sentinel-deployment` | Target FastAPI app + deploy pipeline. Bare. |
| **backend** | `../Sentinel` | `Keshav0375/Sentinel` | **The `Sentinel` repo IS the backend** — there is no separate backend repo. Still holds the Phase-1 code that backend task 9.1 removes. |

> ✅ **Owner/repo identity (reconciled 2026-07-11):** owner is **`Keshav0375`**, repos are
> `Sentinel-infra` / `Sentinel-deployment` / `Sentinel` (capitalized). The architecture docs
> were updated from the old `keshxvDev` placeholder — OIDC `sub` claims are exact
> case-sensitive matches, so use these values verbatim. History in [STATE.md](STATE.md).

## 4. Architecture reference (read before building a task)

Every task cites the section it implements. Never deviate from architecture without asking.
**Start at the index** for the whole picture, then follow its §4 map to the per-repo file your
task's **Arch refs** name — the per-repo files are authoritative for detail.

| Doc | Scope |
|-----|-------|
| [architecture/README.md](../architecture/README.md) | **Architecture Index — start here.** Whole picture in diagrams + a concern→file §4 map. Routes to the deep-dive files below. |
| [architecture/infra.md](../architecture/infra.md) | 7 Terraform modules + identity plane, Entra DB auth, KV rotation, workload identity, `ci_destroy_infra`, cross-repo secrets, CI. |
| [architecture/deployment.md](../architecture/deployment.md) | Deploy pipeline stages, Datadog schema, **30 scenario branches (3 cases)**. |
| [architecture/backend.md](../architecture/backend.md) | Agents, tools, memory, API (+ Entra bearer §3.6, signal_type two-case), DB schema, K8s (workload identity), workflows, Phase-1 cleanup. |
| [architecture/decisions.md](../architecture/decisions.md) | Planning decision log + open blockers. |

> ⚠ **rev-5 (2026-07-12) supersedes several existing task bodies — read the arch first.**
> The TODO row descriptions are current, but some task-file *bodies* predate the security +
> ground-truth overhaul. When building these, follow the cited arch section, not the stale body:
>
> | Task file | Superseded by |
> |-----------|---------------|
> | infra 1.1 repo-skeleton | no `db_password` variable — Postgres is Entra-only (architecture/infra.md §3.2) |
> | infra 2.2 postgresql-module | Entra-only auth + admin group (architecture/infra.md §3.2) — no `db-password`/password auth |
> | infra 2.3 keyvault-module | secret inventory minus db-password/api-token; 4 RBAC roles (architecture/infra.md §3.3) |
> | infra 3.1 aks-module | + workload identity (OIDC issuer, backend UAMI, federated cred) (architecture/infra.md §3.7) |
> | infra 3.2 event-grid / 3.3 functions-bridge | two-signal routing + bridge stamps `signal_type` (architecture/infra.md §3.4/§3.5) |
> | infra 4.1 cross-repo-secrets | variables + `SENTINEL_API_AUDIENCE`, no `DB_PASSWORD` (architecture/infra.md §5) |
> | infra 4.3 infra-workflows | add `ci_destroy_infra.yml` (architecture/infra.md §7.3); no `db_password` workflow var |
> | deploy 2.2 ci-app-deployment | record stage uses Entra DB token, not `db-password` (architecture/deployment.md §3 Stage 5) |
> | backend 5.1 webhook-receiver | `signal_type` two-case handling (architecture/backend.md §3.1); auth = Entra bearer via task 5.6, **not** `X-Sentinel-Token` (architecture/backend.md §3.6) |
> | backend 5.5 app-lifespan | workload-identity KV/DB wiring; auth moved to 5.6 |
> | backend 7.2 k8s-manifests | ServiceAccount + workload-identity label; ConfigMap not Secret (architecture/backend.md §8.2) |
> | backend 7.3 composite-actions | + `get-db-token`, `get-backend-token`; `psql-exec` takes a token (architecture/backend.md §9) |
> | backend 6.2 eval-runner | scores against 30 branches / `branches.yaml`, not synthetic JSON (architecture/backend.md §13.2) |
>
> New rev-5 tasks: infra [3.5 backend-entra-app](tasks/infra/phase-3-compute-modules/task-5-backend-entra-app.md),
> infra [3.6 keyvault-rotation](tasks/infra/phase-3-compute-modules/task-6-keyvault-rotation.md),
> backend [5.6 entra-bearer-auth](tasks/backend/phase-5-api/task-6-entra-bearer-auth.md).

## 5. The build loop (per phase)

Driven by `/implement-phase` (see its SKILL for the authoritative steps). One run builds a
whole phase; within it, each task moves through:

1. **Locate + context** — resolve the active phase (category order + phase-gate locks), rebuild
   full context via the `phase-context-builder` subagent, and distill the architecture contract
   via `architecture-warden` (distill mode).
2. **Goal + branch** — one todo per task; branch `dev/<cat>-phase-<M>-<slug>` fresh from
   `release-phase-2` (§6).
3. **Prereqs** — per task, verify tools/accounts/keys/upstream tasks **and that no open
   Reconciliation (R-item) in [STATE.md](STATE.md) applies to this task**. Missing →
   write a **BLOCKED** report into the task file + STATE.md, and **halt**. Never default an
   open R-item (e.g. don't silently pick a region).
4. **Implement** in the correct repo, per the task's Spec + the architecture contract.
5. **Test + gate** — add unit + integration tests, loop
   `python ../Sentinel/scripts/quality_gate.py --repo <name> --path <repo>` to green (§7).
6. **Commit** one task = one commit (conventional prefix, **no Claude attribution**).
7. **Report** — fill the task file's Report/Tests/How-to-Verify; flip status; update TODO + STATE.md.
8. **Phase review** — when all tasks are green, `architecture-warden` (review) + `code-reviewer` +
   `safety-reviewer` (backend) run over the phase diff; resolve blockers.
9. **Close** — open the PR **into `release-phase-2`**, present the "see it working" checklist,
   and ask the user to sign off (§6).

## 6. Git model — one branch + one PR per phase

```
release-phase-2  ──┬──►  dev/<cat>-phase-<M>-<slug>  ──PR──►  release-phase-2
                   │            (one branch + one PR per phase)
                   └──────────────────────────────────────────►  main
                            (final, once ALL 16 phases are merged)
```

- **`release-phase-2` is the integration branch in all three repos.** A phase branches
  fresh from it, never from `main`:
  `git checkout release-phase-2 && git pull && git checkout -b dev/<cat>-phase-<M>-<slug>`.
- The prefix is **`dev/`**. `Sentinel`'s `ci.yml`
  branch-convention check only accepts `dev|feat|fix|refactor|ci|docs|test|chore|planning|ai|hotfix`.
- Each task in the phase is a **separate commit** on that branch (prefixes: `feat/fix/refactor/test/docs`).
- **No Claude as contributor** — commits and the PR carry no `Co-Authored-By` / "generated with" attribution.
- When every task in the phase is `done-pending-review` and green, `/implement-phase` closes it:
  opens the **PR into `release-phase-2`**, produces a **verification checklist** ("here's how to
  see it working"), and asks the user to confirm.
- On **human sign-off**, the PR **merges to `release-phase-2`**; the branch is deleted; the phase
  is marked `verified` in TODO/STATE.md. The next phase branches from the updated `release-phase-2`.
- Until sign-off, the next phase stays **locked**. This is the human-review gate.
- **`release-phase-2` → `main` happens once**, at the end of Phase 2. The user drives that
  merge; `/implement-phase` never does.

> Enforced by `guard-main-source.yml` in
> the `Sentinel` repo: `release-phase-2 <- dev/* | planning/phase-2-e2e` and
> `main <- release-phase-2`. **A PR from `dev/*` straight to `main` is rejected.**

### Where the tracker commits live

The tracker is in **`sentinel-brain`**, which has no CI, no branch protection and no release
train — **commit tracker updates straight to brain `main`** and push after each task, so
`STATE.md` never lags the code. Brain's history *is* the build log.

So one phase = **one code PR** (in the target repo, `dev/*` → `release-phase-2`) **+ tracker
commits on brain `main`**. There is no tracker branch and no second PR.

| What | Where | How |
|------|-------|-----|
| Code for the phase | the target code repo | branch `dev/<cat>-phase-<M>-<slug>` → PR into `release-phase-2` |
| Task files, TODO, STATE, phase report | `sentinel-brain` | commits on `main`, pushed as you go |

## 7. Quality gate (reusable in CI)

`../Sentinel/scripts/quality_gate.py --repo {infra|deployment|backend}` runs the right toolchain per
repo type and is the exact body CI jobs call:

| Repo | Lint / Format | Types / Validate | Secrets / Security | Tests |
|------|---------------|------------------|--------------------|-------|
| infra | `terraform fmt -check`, `tflint` | `terraform init -backend=false` → `terraform validate` | `tfsec`/`checkov`, `gitleaks` | plan-assert / `terratest` |
| deployment | `ruff`, `actionlint`, `yamllint` | — | `gitleaks` | `pytest tests/` |
| backend | `ruff` check + format | `pyright` | `gitleaks`, `pip-audit` | `pytest` unit + integration (see below) |

**Backend test coverage — keep this in sync.** The gate's two pytest checks must name every
`tests/` package a task file uses, or a phase reports green with its own tests never run:

| Check | Packages | Notes |
|-------|----------|-------|
| `pytest-unit` | `test_models/` · `test_tools/` · `test_providers/` · `test_config.py` | no external service |
| `pytest-integration` | `test_infra/` · `test_memory/` · `test_agents/` · `test_api/` · `test_eval/` | needs pgvector / fake-LLM pipeline; skipped by `--fast` |

Adding a new `tests/` package in a task ⇒ add it to
`../Sentinel/scripts/quality_gate.py` `MATRIX` in the same commit.
Paths that don't exist yet are pruned automatically, so the gate is safe to run mid-build.

## 8. Blockers & standards halt

If a prerequisite is missing (unprovisioned Azure resource, absent account/key, a tool not
installed, an upstream task not `verified`), the build **stops**: a `BLOCKED` section is
written to the task file and mirrored to [implementation/STATE.md](STATE.md#blockers). Nothing
downstream proceeds until the user clears it. This is deliberate — we never build on a
missing foundation.

## 9. Status legend

`not-started` · `in-progress` · `blocked` · `done-pending-review` (built + green, awaiting
the end-of-phase gate) · `verified` (user signed off, merged).
