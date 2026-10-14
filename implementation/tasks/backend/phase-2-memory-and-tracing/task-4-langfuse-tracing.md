# task-4 — `infra/tracing.py` → LangFuse (observe + prompts + scoring)   ·   [backend / phase-2-memory-and-tracing]

| Field | Value |
|-------|-------|
| **Status** | `verified` |
| **Repo** | `Sentinel` (backend) |
| **Phase branch** | `dev/backend-phase-2-memory-and-tracing` |
| **Commit prefix** | `refactor:` |
| **Arch refs** | architecture/backend.md §6 (all), §13.2 |
| **Depends on** | [[task-1-phase2-dependencies]], [[task-1-config-extensions]] (keys) — note: config is Phase 3; use env directly here or land config keys first |
| **Referenced by** | [[task-2-orchestrator-loops]], [[task-1-judge-langfuse-scores]], all agents |

## Spec
Replace custom trace capture with LangFuse: `@observe` decorators, LangFuse-first prompt
loading with local fallback, and score piping (§6.2–6.4).

**Files modified:** `src/sentinel/infra/tracing.py`
_(v3 API, amended 2026-10-12 — langfuse 3.x; see decisions.md 2026-10-12)_
- Client via `from langfuse import get_client` → `get_client()`, from env `LANGFUSE_PUBLIC_KEY` /
  `LANGFUSE_SECRET_KEY` / `LANGFUSE_BASE_URL` (not the deprecated `LANGFUSE_HOST`). No `langfuse.decorators`.
- `from langfuse import observe` wrappers for pipeline / agent / tool (`as_type="agent"` / `"tool"`);
  trace attributes via `propagate_attributes(metadata, tags)` (§6.2). Trace id = `incident_id.hex`
  passed as `langfuse_trace_id=` to the root observed call; `RunContext` carries the id string (§4.5).
- `async def load_prompt(agent_name)` — `get_prompt(name, cache_ttl_seconds=300)` inside try/except,
  fallback to `agents/prompts/{name}.txt` (§6.3). Keyless client raises in `get_prompt` — the except is required.
- `push_score(trace_id, name, value)` → `create_score(trace_id=…, name=…, value=…, data_type="NUMERIC")` (§6.4).
- `shutdown()` on app exit, `flush()` at the end of CLI/eval runs.
- Degrade gracefully when LangFuse keys are absent/unreachable (disabled client, file prompts, no crash).
- Do not touch the openai-agents `TracingProcessor` wiring; LLM-generation capture is an open decision (§6.2 gap).

## Prerequisites
- [ ] task 1.1 deps. [ ] ⛔ B7 LangFuse keys for live tracing (fallback path works offline).

## Acceptance Criteria
- [ ] Prompt loader returns LangFuse prompt when available, file otherwise (test both).
- [ ] Trace/score helpers callable and typed; no hard failure when keys absent.

## Tests
Gate: VERDICT GREEN (7 ran, env -i, only TEST_DATABASE_URL); 13 tests in test_tracing.py.
- **Unit (`tests/test_infra/test_tracing.py`):** prompt fallback to file when LangFuse mocked-unavailable; score helper builds the right `create_score` call (mock client).
- **Quality gate:** `--repo backend`.

## How to Verify (phase gate — end of Category 3 Phase 2)
1. `pytest tests/test_infra/test_tracing.py -q` green (fallback path).
2. (with B7 keys) a sample `@observe` run appears as a trace in the LangFuse dashboard.

## Report   ·   _filled on completion_
Built v3 LangFuse tracing in `infra/tracing.py`: `trace_incident` context manager (root "incident-pipeline", trace id = UUID.hex, propagate_attributes), `incident_trace_id`, `load_prompt` (LangFuse-first, package-relative file fallback), `push_score` (create_score NUMERIC), shutdown in lifespan, flush in CLI/scripts. Safe with no keys or unreachable Langfuse. R14 (token/cost) out of scope.
Commit `49e3534` refactor: LangFuse v3 tracing — observe, prompt loading, scores.
Files: src/sentinel/infra/tracing.py, main.py, cli.py, scripts/run_eval.py, scripts/run_scenario.py, tests/conftest.py, tests/test_infra/test_tracing.py, .env.example.
Live trace check SKIPPED: user's .env uses LANGFUSE_HOST; needs rename to LANGFUSE_BASE_URL.

## BLOCKED
_Live tracing ⛔ B7. Fallback + unit tests writable now._
