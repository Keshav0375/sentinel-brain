---
name: new-agent
description: Scaffold a new Sentinel backend agent (prompt file, Agent definition, fake-LLM tests) in ../Sentinel, built and gated by task-implementer.
argument-hint: "<agent-name>"
disable-model-invocation: true
context: fork
agent: task-implementer
background: false
---

Build a new Sentinel agent named: **$ARGUMENTS**. Repo `../Sentinel`, on its current branch (must be a
`dev/*` or `fix/*` branch — if it is `main` or `release-phase-2`, HALT).

1. Spec: `python3 scripts/arch.py backend 4 4.7` (pipeline + loops, per-agent model assignment).
   Agent not in the architecture → HALT.
2. Prompt → `src/sentinel/agents/prompts/<name>.txt` per the prompt rules in `CONVENTIONS.md`: role on
   line 1, explicit tool-use instructions, output format, constraints, < 800 tokens. Prompts load at
   runtime — never hardcoded in Python.
3. Agent → `src/sentinel/agents/<role>.py`: tools from `src/sentinel/tools/`, prompt loaded from the
   file, SDK pattern from `CONVENTIONS.md`, model from §4.7, `from __future__ import annotations`,
   full hints, docstring, `handoffs=` only on the orchestrator.
4. Tests → `tests/test_agents/test_<name>.py`: config assertions (name, model, tools, handoffs) + an
   integration test on the fake LLM (`SENTINEL_FAKE_LLM=1`) — deterministic, no network.
5. Export from `src/sentinel/agents/__init__.py`.
6. Safety: no agent both drafts and executes; orchestrator changes respect the 20-call budget and the
   ≤2 reflexion cap (§4.3, §4.6).
7. Gate to `VERDICT GREEN` (`python3 scripts/gate.py backend`), boot check, one commit, no attribution.

Report in your DONE format, plus tools/handoffs wired, model chosen, and the § implemented.
