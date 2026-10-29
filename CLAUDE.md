# sentinel-brain — Claude Code Instructions

**This repo is the control plane, not the product.** Architecture, tracker, build agents and
reports live here; **no application code**. It drives three sibling code repos from outside so they
stay clean. Owner: Keshav (sole author). This file is a map — follow the pointer for detail.

@.claude/skills/ground-rules/SKILL.md

## The repos

| Category | Path | GitHub | What it is |
|----------|------|--------|------------|
| backend | `../Sentinel` | `Keshav0375/Sentinel` | Multi-agent incident-response pipeline on AKS. The `Sentinel` repo **is** the backend. Hosts the quality gate (`scripts/quality_gate.py`). |
| deployment | `../Sentinel-deployment` | `Keshav0375/Sentinel-deployment` | Target FastAPI app on App Service F1 + 30 scenario branches that generate real Datadog signal. |
| infra | `../Sentinel/infra` | `Keshav0375/Sentinel` (`infra/`) | Terraform — 7 modules + the Entra/OIDC identity plane. Monorepo subdir since infra phase 7; `Keshav0375/Sentinel-infra` is the read-only backup — archived once the first infra plan run from `Sentinel` passes. |

**Phase 1 (MVP) is dead.** Phase 2 *replaced* it (SQLite→Postgres+pgvector, synthetic JSON→real
scenario branches, approval tool→**the revert PR is the gate**, backend-executes→**GHA executes**,
local→AKS scale-to-zero, no auth→Entra bearer). `archive/` is history and is blocked by a hook; if
anything there disagrees with `architecture/`, `architecture/` is right — never reconcile them.

**Paths:** prose names paths from the brain root (`architecture/infra.md §3.2`); markdown links
are true relative paths.

## Where things are — use the readers, not `Read`

```bash
python3 scripts/where.py            # active phase: repo, branch, gate, tasks, WAVES, gating blockers
python3 scripts/where.py infra-4    # a named phase — exit 1 = do not enter
python3 scripts/where.py --all      # every phase + every open blocker / R-item
python3 scripts/arch.py --map       # concern -> file + §
python3 scripts/arch.py infra --list        # TOC + token cost per §
python3 scripts/arch.py infra 3.2 3.3       # just those sections (~3K tok, not 21K)
python3 scripts/arch.py decisions R6        # one decision entry
python3 scripts/gate.py <infra|deployment|backend> [--fast] [--path WT]   # the quality gate, done right
python3 scripts/task_status.py <cat> <M.K> <status>           # flip a task + re-sync the board
python3 scripts/board_sync.py [--issues <cat>-<M>]           # mirror tracker → board / look up issue #s
```

| Need | Where |
|------|-------|
| Whole picture — diagrams + concern→file map | `architecture/README.md` (or `arch.py --map`) |
| **Binding** detail per repo | `architecture/{backend,deployment,infra}.md` via `arch.py` |
| Why a decision was made / what superseded what | `architecture/decisions.md` via `arch.py decisions <id>` |
| Live state — position, blockers, open R-items, gate ledger | `implementation/STATE.md` (cheap; read whole) |
| One task's spec + report | `implementation/tasks/<cat>/phase-<M>-*/task-*.md` |
| Build loop, git model, quality gate rationale | `implementation/README.md` |
| Backend coding standards | `../Sentinel/CONVENTIONS.md` |
| Finished phase summaries | `reports/` |

The session starts with `where.py` output already injected (SessionStart hook) — don't re-run it
just to orient. `scripts/gate.py` exists because the gate must come from `main` (the
local `Sentinel` checkout may be stale) and must find ruff/pytest in the target repo's `.venv`;
it ends with one `VERDICT` line and exits non-zero unless the gate is fully green.

## Building Phase 2 — `/implement-phase`

Order **infra → deployment → backend**. One phase = one branch + one PR, merged only on the user's
end-of-phase sign-off. `/implement-phase` (spec: `.claude/skills/implement-phase/SKILL.md`)
orchestrates as a DAG: `where.py` prints the phase's `WAVES` (from each task's `Depends on` row);
each wave is planned in parallel (Opus), built in parallel in `../.wt/` worktrees (Sonnet), then
cherry-picked onto the phase branch and gated once. Specialists work in throwaway contexts:

| Agent | Model | Job |
|-------|-------|-----|
| `phase-context-builder` | sonnet | brief: prior work consumed, tasks, deps, blockers, drift |
| `architecture-warden` | opus | distill the verbatim contract · review conformance |
| `task-planner` | opus | every decision for one task → an exact plan in `.plans/` |
| `task-builder` | sonnet | build to the plan (wave worktree) → tests → gate → one commit |
| `task-implementer` | opus | single-agent build for `/new-tool` · `/new-agent` |
| `gate-runner` | haiku | `/check` only — the phase loop runs `scripts/gate.py` itself |
| `tracker-clerk` | sonnet | task reports, TODO/STATE, phase report, PR, sign-off merge |
| `code-reviewer` · `safety-reviewer` | opus | correctness · agentic-safety invariants |

Other skills: `/progress` (tracker overview) · `/check <cat>` (gate) · `/review [cat]` (quick diff
review) · `/new-ticket` (add a task/phase, tracker-first) · `/new-tool` · `/new-agent` (backend scaffolds).

## Project board (Jira-style mirror)

[Sentinel board](https://github.com/users/Keshav0375/projects/4): **Epic** (one per category) →
**Phase** (parent, sub-issue) → **Task** (child, sub-issue), as issues in `sentinel-brain`. Fields:
Status (Backlog → Ready → In progress → In review → Done), Level, Category, Phase, Task ID,
Priority (build order: active phase P0, next P1, rest P2), Target date (gate date).
`python3 scripts/board_sync.py` regenerates it from TODO.md + task files — a **one-way mirror**:
never edit those issues by hand; the clerk re-syncs after every tracker commit. Ad-hoc bugs use
the issue forms in `.github/ISSUE_TEMPLATE/`.

## Branch model (binding)

The **branch name** for a phase is exactly what `where.py` prints (it comes from the TODO.md phase
heading) — never re-derive it.

| Repo | Branch from | PR into | Protected? |
|------|-------------|---------|-----------|
| `Sentinel` (backend) | `main` | `main` | yes — PR required; `guard-main-source.yml` allows only `dev/*`, `fix/*` |
| `Sentinel` / `infra/` | `main` | `main` | yes — same repo and rules as the backend row (dev/infra-phase-<M>-*) |
| `Sentinel-deployment` | `main` | `main` | no |

- **Phase 2 shipped to `main` on 2026-10-25 (PR #29).** `main-backup` holds the pre-release `main`;
  `release-phase-2` is **frozen** as the Phase 2 record (the guard rejects every PR into it).
- `fix/*` → `main` is allowed for out-of-phase repairs (tooling/CI defects). Phase work is always
  `dev/*`; never use `fix/` to dodge the phase model.
- Tracker commits go straight to brain `main` (no branch, no PR). `planning/phase-2-e2e` is retired.

## MCP servers (`.mcp.json`)

| Server | Mode | Use for |
|--------|------|---------|
| `github` | remote, **read-only** (repos · pull_requests · actions), auth = `gh auth token` | CI runs + job logs, PR state/reviews, file reads across the four repos |
| `terraform` | Docker, registry toolset | exact provider/module argument schemas + versions |
| `azure` | npx, **read-only**, Sentinel namespaces only; auth = `az login` | inspect the live estate (AKS, ACR, Postgres, KV, App Service, Functions…) |

All writes go through `git` / `gh` (where the attribution guard runs) — never through MCP.
claude.ai connectors and unrelated plugins are disabled for this project.

## Reporting to the user

Short and concrete. After a task: what was built, what it does, what it unblocks — a few lines.
After a phase: `reports/<cat>-phase-<M>.md` (from `implementation/_templates/phase-report-template.md`)
plus the "see it working" checklist. Be honest about anything skipped, deferred, PARTIAL or BLOCKED.

## When stuck

`architecture/` → the task's notes → `architecture/decisions.md` →
[OpenAI Agents SDK docs](https://openai.github.io/openai-agents-python/) → **ask the user.**
