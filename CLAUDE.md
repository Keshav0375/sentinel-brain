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
| infra | `../Sentinel-infra` | `Keshav0375/Sentinel-infra` | Terraform — 7 modules + the Entra/OIDC identity plane. |

**Phase 1 (MVP) is dead.** Phase 2 *replaced* it (SQLite→Postgres+pgvector, synthetic JSON→real
scenario branches, approval tool→**the revert PR is the gate**, backend-executes→**GHA executes**,
local→AKS scale-to-zero, no auth→Entra bearer). `archive/` is history and is blocked by a hook; if
anything there disagrees with `architecture/`, `architecture/` is right — never reconcile them.

**Paths:** prose names paths from the brain root (`architecture/infra.md §3.2`); markdown links
are true relative paths.

## Where things are — use the readers, not `Read`

```bash
python3 scripts/where.py            # active phase: repo, branch, gate, tasks, gating blockers (~175 tok)
python3 scripts/where.py infra-4    # a named phase — exit 1 = do not enter
python3 scripts/where.py --all      # every phase + every open blocker / R-item
python3 scripts/arch.py --map       # concern -> file + §
python3 scripts/arch.py infra --list        # TOC + token cost per §
python3 scripts/arch.py infra 3.2 3.3       # just those sections (~3K tok, not 21K)
python3 scripts/arch.py decisions R6        # one decision entry
python3 scripts/gate.py <infra|deployment|backend> [--fast]   # the quality gate, done right
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
just to orient. `scripts/gate.py` exists because the gate must come from `release-phase-2` (the
local `Sentinel` checkout may be stale) and must find ruff/pytest in the target repo's `.venv`;
it ends with one `VERDICT` line and exits non-zero unless the gate is fully green.

## Building Phase 2 — `/implement-phase`

Order **infra → deployment → backend**. One phase = one branch + one PR, merged only on the user's
end-of-phase sign-off. `/implement-phase` (spec: `.claude/skills/implement-phase/SKILL.md`)
orchestrates; specialists do the work in throwaway contexts:

| Agent | Model | Job |
|-------|-------|-----|
| `phase-context-builder` | sonnet | brief: prior work consumed, tasks, deps, blockers, drift |
| `architecture-warden` | opus | distill the verbatim contract · review conformance |
| `task-implementer` | opus | build one task → tests → gate GREEN → one commit |
| `gate-runner` | haiku | independent gate + clean-tree + no-attribution check |
| `tracker-clerk` | sonnet | task reports, TODO/STATE, phase report, PR, sign-off merge |
| `code-reviewer` · `safety-reviewer` | opus | correctness · agentic-safety invariants |

Other skills: `/progress` (tracker overview) · `/check <cat>` (gate) · `/review [cat]` (quick diff
review) · `/new-tool` · `/new-agent` (backend scaffolds).

## Branch model (binding)

The **branch name** for a phase is exactly what `where.py` prints (it comes from the TODO.md phase
heading) — never re-derive it.

| Repo | Branch from | PR into | Protected? |
|------|-------------|---------|-----------|
| `Sentinel` (backend) | `release-phase-2` | `release-phase-2` | yes — `main` is guarded |
| `Sentinel-infra` | `main` | `main` | no |
| `Sentinel-deployment` | `main` | `main` | no |

- `Sentinel` `main` accepts exactly one merge — `release-phase-2`, once, at the end of Phase 2,
  driven by the user. `guard-main-source.yml` rejects `dev/*` → `main`.
- `fix/*` → `release-phase-2` is allowed for out-of-phase repairs (tooling/CI defects found
  mid-build). Phase work is always `dev/*`; never use `fix/` to dodge the phase model.
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
