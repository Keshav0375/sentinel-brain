---
description: Scaffold a new Sentinel backend tool with Pydantic schemas, implementation, and test
allowed-tools: Read, Write, Edit, Bash
model: sonnet
---

Create a new Sentinel tool named: $ARGUMENTS

You run from `sentinel-brain`. The backend code is at **`../Sentinel`** — every path below is
relative to that repo. Never write backend code into this repo.

Steps:

1. Read `architecture/backend.md` **§4.8** (tool contracts + side effects) and **§13.2** for
   this tool's spec. If the tool is not in the architecture, **stop and ask** — do not invent one.
2. **Safety gate, before writing anything:** a Phase-2 tool is **read-only or output-only**.
   It may query Postgres, Datadog or the GitHub API for *information*, or format a draft. It may
   **never** modify external state — no opening PRs, no posting to Teams, no deploys, no
   rollbacks. The backend reasons; GitHub Actions executes. If the tool as asked would act on
   the world, stop and say so rather than building it.
3. If it needs new Pydantic models, add them under `../Sentinel/src/sentinel/models/`.
4. Create `../Sentinel/src/sentinel/tools/<verb>_<noun>.py` with:
   - Pydantic v2 input/output models (or imports from `models/`)
   - the function decorated with `@function_tool` from the Agents SDK, `async`
   - `from __future__ import annotations` and full type hints
   - a docstring — this becomes the tool description the LLM sees
   - error handling that returns a **structured error response**, never raises raw
   - dependencies injected, never constructed inside the tool
5. Create `../Sentinel/tests/test_tools/test_<name>.py`: valid input → expected output; an edge
   case (empty / missing fields); the structured-error path; external deps mocked.
   `tests/test_tools/` is inside the gate's `pytest-unit` glob, so it will actually run.
6. Register it wherever the phase's task file says (agent wiring or a registry).
7. Run `python ../Sentinel/scripts/quality_gate.py --repo backend --path ../Sentinel` to green.
8. Print: files created, the tool's I/O schema, which agent(s) use it, and the § it implements.
