# sentinel-brain

The control plane for **Sentinel** — an autonomous DevOps incident-response agent.

This repo holds the **architecture**, the **implementation tracker**, the **AI agents that do
the building**, and the **phase reports**. It contains no application code. It drives three
code repos from the outside so they stay clean: no planning docs, no agent configs, no
trackers, no reports in the repos that ship.

```
Sentinel-development-project/
├── sentinel-brain/         ← this repo — architecture, tracker, agents, reports
├── Sentinel/               ← backend: multi-agent pipeline on AKS
├── Sentinel-deployment/    ← target app: FastAPI on App Service + 30 scenario branches
└── Sentinel-infra/         ← Terraform: 7 modules + Entra/OIDC identity plane
```

## What Sentinel does

Datadog detects a failed or broken deploy → an Event Grid → Function bridge stamps the signal
type and dispatches → a multi-agent pipeline diagnoses the incident → it either drafts a
**revert PR** (which a human merges — that PR *is* the approval gate) or **escalates** to a
human. The backend reasons; GitHub Actions executes. No backend tool touches the outside world.

~$5–12/month, LLM calls only; $0 infra at idle (the AKS node pool scales to zero between runs).

## Layout

| Path | What it is |
|------|-----------|
| `architecture/` | **Binding** Phase-2 architecture. `README.md` is the index; `backend.md` / `deployment.md` / `infra.md` are authoritative for detail; `decisions.md` is the decision log. |
| `implementation/` | The tracker: `TODO.md` (58 tasks / 16 phases), `STATE.md` (where we are, blockers), `tasks/` (one file per task — spec *and* completion report). |
| `reports/` | Short per-phase summaries written at each human sign-off gate. |
| `reference/` | LLM provider notes, external doc links, draft repo READMEs. |
| `archive/mvp-phase-1/` | ⛔ **Stale.** Phase-1 prototype docs, history only — Phase 2 replaced that design wholesale. |
| `.claude/` | Agents, the `/implement-phase` skill, and commands that drive the build. |

## How the build runs

`/implement-phase` builds one whole phase end-to-end: rebuild context → distill the
architecture contract → implement task by task to a green quality gate → three-way review
(architecture / code / safety) → open the PR → **ask the human to verify**. Nothing is marked
verified without the user confirming it works.

Order is **infra → deployment → backend**. Every phase is one branch (`dev/<cat>-phase-N-<slug>`
off `release-phase-2`) and one PR back into `release-phase-2`.

Start at [CLAUDE.md](CLAUDE.md) for the full map.
