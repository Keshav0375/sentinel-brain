---
description: Scaffold a new Sentinel backend agent with prompt file, agent definition, and test stub
allowed-tools: Read, Write, Edit, Bash
model: sonnet
---

Create a new Sentinel agent named: $ARGUMENTS

You run from `sentinel-brain`. The backend code is at **`../Sentinel`** — every path below is
relative to that repo. Never write backend code into this repo.

Steps:

1. Read `architecture/backend.md` **§4** (pipeline + loops) and **§4.7** (per-agent model
   assignment) for this agent's spec. If it is not in the architecture, **stop and ask**.
2. Create the system prompt at `../Sentinel/src/sentinel/agents/prompts/<name>.txt`, following
   the prompt rules in `../Sentinel/CONVENTIONS.md`: first line declares the role, explicit
   tool-use instructions, output-format expectations, constraints, under 800 tokens.
   **Prompts live in files and load at runtime — never hardcoded in Python.**
3. Create `../Sentinel/src/sentinel/agents/<role>.py`:
   - import its tools from `src/sentinel/tools/`
   - load the prompt from the `.txt` file
   - build the `Agent` per the SDK pattern in `../Sentinel/CONVENTIONS.md`
   - the model comes from §4.7 — Sonnet for reasoning, Haiku for classification/scoring
   - `from __future__ import annotations`, full type hints, docstring
   - `handoffs=` only on the orchestrator
4. Create `../Sentinel/tests/test_agents/test_<name>.py`: a fixture building the agent with
   mock tools, a test asserting its configuration (name, model, tools, handoffs), and an
   integration test driven by the **fake LLM** (`SENTINEL_FAKE_LLM=1`) — deterministic, no
   network. `tests/test_agents/` is in the gate's `pytest-integration` glob.
5. Export it from `../Sentinel/src/sentinel/agents/__init__.py`.
6. **Safety:** no agent both drafts and executes; anything touching the orchestrator must
   respect the 20-call tool budget and the ≤2 reflexion-loop cap (§4.3, §4.6).
7. Run `python ../Sentinel/scripts/quality_gate.py --repo backend --path ../Sentinel` to green.
8. Print: files created, tools and handoffs wired, model chosen, and the § it implements.
