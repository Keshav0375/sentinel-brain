# task-1 — Provider routing + fallback (`providers/`)   ·   [backend / phase-4-agents]

| Field | Value |
|-------|-------|
| **Status** | `done-pending-review` |
| **Repo** | `Sentinel` (backend) |
| **Phase branch** | `dev/backend-phase-4-agents` |
| **Commit prefix** | `feat:` |
| **Arch refs** | architecture/backend.md §4.7 (models + fallback), §1.3 (providers/ bucket) |
| **Depends on** | [[task-1-config-extensions]] |
| **Referenced by** | [[task-2-orchestrator-loops]], [[task-4-pr-content-generator]], all agents |

## Spec
LLM provider routing: Anthropic default, OpenAI fallback, per-agent model assignment, and
automatic fallback on rate-limit/timeout/API error (§4.7).

**Files created:** `src/sentinel/providers/` — `__init__.py`, `router.py`, maybe `models.py`.
- Model map per agent/step (§4.7 table): orchestrator/analysis/resolution → `anthropic/claude-sonnet-4-6` (fb `openai/gpt-4o`); triage/reflexion/reverification/judge/pr-content → `anthropic/claude-haiku-4-5` (fb `openai/gpt-4o-mini`).
- `call_with_fallback(agent, input, primary, fallback)` per §4.7 snippet; switch default via `sentinel_primary_provider`.
- `SENTINEL_FAKE_LLM=1` → a deterministic stub provider for CI (no network).
- Uses OpenAI Agents SDK `Agent.with_model(...)` pattern.

## Prerequisites
- [ ] task 3.1 config. [ ] ⛔ B4/B5 for live calls (fake provider for tests).

## Acceptance Criteria
- [ ] Correct model string per agent role (conformance-checked against §4.7).
- [ ] Fallback triggers on RateLimit/Timeout/APIError and logs the switch (structlog).
- [ ] Fake mode returns canned outputs, no network.

## Tests
- **Unit (`tests/test_providers/test_router.py`):** primary success path; forced primary error → fallback invoked; model map matches §4.7; fake mode deterministic.
- **Quality gate:** `--repo backend`.

## How to Verify (phase gate)
Gate: `python3 scripts/gate.py backend` VERDICT GREEN (~80 tests; boot with no keys proven).
1. `pytest tests/test_providers/ -q` green (fake + fallback).
2. (with B4/B5) a real Haiku call returns a completion.

## Report   ·   _filled on completion_
Built the provider router (role map by `sentinel_primary_provider`, Anthropic/OpenAI only; judge on the non-primary provider with a guard; `call_with_fallback` returns `model_used`), `SENTINEL_FAKE_LLM` deterministic Model, R14 token bridge (generation spans to Langfuse, per-incident totals, 50K warning), and `set_trace_processors` with only our processors (`trace_include_sensitive_data=False`). `PUT /api/config` removed. Interim: agents keep Phase-1 shape until 4.2.
Commits (Sentinel): db70a9f, a0f4458, c37f70d, 75e113d. Per decision 2026-10-15 + amendment 52a5f7f.

## BLOCKED
_Live calls ⛔ B4/B5. Router + fake-mode tests writable now._
