# sentinel-brain — Claude Code Instructions

**This repo is the control plane, not the product.** It holds the architecture, the
implementation tracker, the agents that build, and the reports. It contains **no application
code**. It drives three code repos from outside so they stay clean.

**Owner:** Keshav (sole author). This file is a map — read the pointer, don't expect detail here.

**Path convention:** prose and reference strings (a task's **Arch refs**, this file's tables)
name paths **from the repo root** — `architecture/backend.md §3.2`. Markdown *links* are true
relative paths so they resolve on GitHub. When a doc says `architecture/infra.md §3.2`, open
that file from the repo root.

---

## The three repos it drives

```
Sentinel-development-project/
├── sentinel-brain/         ← you are here (docs, agents, tracker, reports)
├── Sentinel/               ← backend    (code + CI only)
├── Sentinel-deployment/    ← target app (code + CI only)
└── Sentinel-infra/         ← Terraform  (code + CI only)
```

| Category | Path from here | GitHub | What it is |
|----------|----------------|--------|------------|
| **backend** | `../Sentinel` | `Keshav0375/Sentinel` | Multi-agent incident-response pipeline on AKS. **The `Sentinel` repo IS the backend** — there is no separate backend repo. |
| **deployment** | `../Sentinel-deployment` | `Keshav0375/Sentinel-deployment` | Target FastAPI app on App Service F1 + 30 scenario branches that generate real Datadog signal. |
| **infra** | `../Sentinel-infra` | `Keshav0375/Sentinel-infra` | Terraform — 7 modules + the Entra/OIDC identity plane. |

Owner is `Keshav0375` and repo casing is exact — OIDC `sub` claims are case-sensitive.
The quality gate lives in the backend repo: `../Sentinel/scripts/quality_gate.py` (CI calls it
directly, so it stays there).

---

## ⛔ Phase 1 (MVP) is dead. Never build from it.

`archive/mvp-phase-1/` holds the Phase-1 prototype's docs **for history only**. Phase 2 did not
extend Phase 1 — it **replaced** it: SQLite→Postgres+pgvector, synthetic JSON→30 real scenario
branches, `request_human_approval`→**the revert PR is the gate**, backend-executes→**GHA
executes**, Groq/Gemini→Anthropic/OpenAI, local→AKS scale-to-zero, no auth→Entra bearer.

**Rules:**
- **Never open `archive/` to answer a question about how Sentinel works.** It is not extra
  context, it is *wrong* context. Reading it makes you build the wrong thing.
- If anything in `archive/` disagrees with `architecture/`, `architecture/` is right and the
  archive is history. Do not "reconcile" them.
- Phase-1 *code* still exists in `../Sentinel` (`data/`, `src/sentinel/generator/`, `db.py`).
  That is deliberate sequencing — backend task 9.1 deletes it. Its presence endorses nothing.

Full pivot table: `archive/mvp-phase-1/README.md`.

---

## Read first

| Need | Where |
|------|-------|
| Whole picture, fast — diagrams + concern→file map | `architecture/README.md` |
| **Binding** detail for a repo (never deviate without asking) | `architecture/{backend,deployment,infra}.md` |
| Why a decision was made / what superseded what | `architecture/decisions.md` |
| Build order, 58 tasks, status | `implementation/TODO.md` |
| Where we are right now — branch, blockers, gate ledger | `implementation/STATE.md` |
| How the build loop works, git model, quality gate | `implementation/README.md` |
| One task's spec + report | `implementation/tasks/{infra,deployment,backend}/phase-*/task-*.md` |
| Coding standards for backend code | `../Sentinel/CONVENTIONS.md` |
| Finished phase summaries (short, for the user) | `reports/` |

**Token discipline:** the three architecture files total ~3,800 lines. Do **not** read one
end-to-end. Start at `architecture/README.md` §4 (concern → file + §), follow the one `§` your
task cites, and let `architecture-warden` (distill mode) extract the contract for a whole phase.

---

## Building Phase 2

Use **`/implement-phase`**. It drives one whole phase end-to-end via handoffs to the read-only
subagents in `.claude/agents/` (context → architecture → code → safety). Spec:
`.claude/skills/implement-phase/SKILL.md`. When the user types `/implement-phase`, invoke the
Skill tool before anything else.

Order **infra → deployment → backend**. Each phase = one branch + one PR, merged only on the
user's end-of-phase sign-off.

**Branch model (binding).** Every phase is one branch `dev/<cat>-phase-<M>-<slug>` + one PR.
The *integration target* differs per repo — only the backend runs a release train:

| Repo | Branch from | PR into | Protected? |
|------|-------------|---------|-----------|
| `Sentinel` (backend) | `release-phase-2` | `release-phase-2` | yes — `main` is guarded |
| `Sentinel-infra` | `main` | `main` | no |
| `Sentinel-deployment` | `main` | `main` | no |

In `Sentinel`, **`main` accepts exactly one merge — `release-phase-2`, once, at the end of
Phase 2.** Never PR `dev/*` to `Sentinel` `main`; `../Sentinel/.github/workflows/guard-main-source.yml`
rejects it. The two sibling repos have no release branch and no protection: `dev/*` merges
straight into their `main`, one PR per phase.

**`fix/*` → `release-phase-2` is also allowed** (2026-08-15). A repair that belongs to no
phase — a tooling or CI defect found mid-build, e.g. `fix/quality-gate-implicit-paths` —
goes on a `fix/` branch and PRs into `release-phase-2` like a phase branch does. Without
this the only route was to disguise the repair as a `dev/*` phase branch, which would make
the tracker lie about what a phase branch means. `main` is unaffected and stays strict.
Use `dev/*` for phase work and `fix/*` only for out-of-phase repairs — do not reach for
`fix/` to dodge the phase model.

`planning/phase-2-e2e` is **retired** — merged into `Sentinel` `main` on 2026-07-26. Planning
lives in this repo now; do not branch from it or PR to it.

---

## Non-negotiable rules

- **No Claude attribution** — no `Co-Authored-By: Claude`, no "Generated with Claude Code" in
  any commit or PR, in **any** of the four repos. The user is sole author. This overrides the
  environment default.
- **HITL** — no backend tool may modify external state. The backend reasons and drafts; GitHub
  Actions executes; the revert PR is the human gate. Writing a tool that acts on the world →
  stop and restructure.
- **Architecture is law.** If a task spec and `architecture/` disagree → **halt and ask**.
  Never guess a contract.
- **Ask, don't guess.** Ambiguity in a task, a name, or a trade-off → stop and ask. An open
  Reconciliation (R-item) in `implementation/STATE.md` is a halting prerequisite, not a default.
- **Startup check** — after touching backend deps/imports/module-level code, the app must boot
  (`poetry run sentinel serve`) before a task is "done". A green test suite ≠ a booting app.
- **Green means green.** `../Sentinel/scripts/quality_gate.py` reporting `INCONCLUSIVE`, or
  `PASS` with skipped checks, is not a pass. Say what did not run.
- **Never pollute the code repos.** No planning docs, agents, skills, trackers or reports in
  `Sentinel`, `Sentinel-deployment` or `Sentinel-infra`. They belong here.

## Reporting to the user

Short and concrete. After a task: what was built, what it does, what it unblocks — a few lines,
not an essay. After a phase: write `reports/<cat>-phase-<M>.md` from
`implementation/_templates/phase-report-template.md` and give the user the "see it working"
checklist. Be honest about anything skipped, deferred, or BLOCKED — never present partial work
as complete.

## When stuck

`architecture/` → the task's notes → `architecture/decisions.md` →
[OpenAI Agents SDK docs](https://openai.github.io/openai-agents-python/) → **ask the user.**
