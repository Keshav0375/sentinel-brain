---
name: new-tool
description: Scaffold a new Sentinel backend tool (Pydantic I/O, async @function_tool, structured errors, tests) in ../Sentinel, built and gated by task-implementer.
argument-hint: "<verb_noun>"
disable-model-invocation: true
context: fork
agent: task-implementer
background: false
---

Build a new Sentinel backend tool named: **$ARGUMENTS**. Repo `../Sentinel`, on its current branch
(must be a `dev/*` or `fix/*` branch — if it is `main` or `release-phase-2`, HALT).

1. Spec: `python3 scripts/arch.py backend 4.8 13.2` (tool contracts + side effects). Tool not in the
   architecture → HALT; never invent one.
2. **Safety first:** a Phase-2 tool is read-only or output-only — it may query Postgres, Datadog or
   the GitHub API for information, or format a draft. It never modifies external state. If the tool
   as asked would act on the world → HALT and say so.
3. New models → `src/sentinel/models/`. Tool → `src/sentinel/tools/<verb>_<noun>.py`: Pydantic v2
   I/O, `async` + `@function_tool`, `from __future__ import annotations`, full hints, a docstring
   (it is the description the LLM sees), structured error returns (never raise raw), injected deps.
4. Tests → `tests/test_tools/test_<name>.py`: valid input, an edge case, the structured-error path,
   external deps mocked (`tests/test_tools/` is in the gate's `pytest-unit`).
5. Register it where the active task file says (agent wiring or registry).
6. Gate to `VERDICT GREEN` (`python3 scripts/gate.py backend`), boot check, one commit, no attribution.

Report in your DONE format, plus the tool's I/O schema and which agent(s) use it.
