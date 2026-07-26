# ⛔ STALE — Phase 1 (MVP). DO NOT USE.

**Nothing in this folder describes how Sentinel works.** These documents describe the
**Phase-1 MVP**, a local prototype that Phase 2 replaced wholesale. They are kept only so
the decision history is not lost.

## If you are an agent

**Do not read these files.** They are not "extra context" — they are *wrong* context. Every
question about how Sentinel works is answered by [`architecture/`](../../architecture/README.md).
If a Phase-2 doc and a file in here disagree, the Phase-2 doc is right and this one is
history. Reading these will make you build the wrong thing.

The only legitimate reason to open this folder is a human explicitly asking
"what did the MVP do?" — never to plan, design, or implement Phase-2 work.

## What changed, Phase 1 → Phase 2

This is the whole pivot. It is not an increment; almost every layer was replaced.

| Concern | Phase 1 (these docs — dead) | Phase 2 (what we build) |
|---------|-----------------------------|--------------------------|
| Data store | SQLite + `aiosqlite`, `sentinel.db` | Azure PostgreSQL B1MS + pgvector, 3 tables |
| Test data | synthetic scenario JSON in `data/`, `src/sentinel/generator/` | 30 real scenario branches deployed to a live app |
| Signal source | generated alerts/logs/deploys | real Datadog monitors on a real deploy pipeline |
| HITL gate | `request_human_approval` tool + `/approvals` endpoint | **the revert PR is the gate** — no approval tool, no endpoint, fire-and-forget |
| Execution | backend called GitHub/Slack directly | **backend reasons, GHA executes** — no tool touches external state |
| Agents | 6 agents, linear chain | orchestrator branches on `signal_type`; plan-execute + reflexion (≤2) + reverification, 20-tool budget |
| Hosting | local / ephemeral container | AKS single replica, node pool scale-to-zero 0↔1 |
| Auth | none / shared `X-Sentinel-Token` | Entra bearer (JWKS) inbound; Entra-only Postgres; AKS workload identity |
| LLM | Groq + Gemini | Anthropic (default) + OpenAI (fallback) |
| Tracing | local JSON trajectories | LangFuse traces, prompts, judge scores |
| Comms | `comms_tools.py` from the backend | GitHub Actions posts to Teams |

Backend task **9.1** deletes the Phase-1 code artifacts (`data/`, `src/sentinel/generator/`,
`db.py`, the Phase-1 scripts) from the `Sentinel` repo. Until then the old code still exists
there — that is deliberate sequencing, **not** an endorsement of these docs.

## Contents

- `ARCHITECTURE.md` — the Phase-1 architecture
- `TODO.md` — the Phase-1 task list (all complete; superseded)
- `story-reports/` — 50 per-story completion reports from the Phase-1 build
