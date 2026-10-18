# task-2 — Orchestrator: plan-execute + reflexion + reverification + budget   ·   [backend / phase-4-agents]

| Field | Value |
|-------|-------|
| **Status** | `done-pending-review` |
| **Repo** | `Sentinel` (backend) |
| **Phase branch** | `dev/backend-phase-4-agents` |
| **Commit prefix** | `refactor:` |
| **Arch refs** | architecture/backend.md §4.1–4.6, §3 (flow) |
| **Depends on** | [[task-1-provider-routing]], [[task-3-reflexion-reverification-prompts]], all Phase-3 tools |
| **Referenced by** | [[task-1-webhook-receiver]], [[task-1-judge-langfuse-scores]] |

## Spec
Rewrite the orchestrator from a linear chain to plan-execute with reflexion + reverification
loops and a hard tool-call budget (§4.1–4.6).

**Files modified:** `src/sentinel/agents/orchestrator.py` (+ triage/analysis/resolution agent wiring as needed).
- **Plan-execute:** orchestrator plans agent order after triage.
- **Reflexion:** after analysis, critique step; if confidence < 0.7 loop back with guidance, **max 2 loops** (§4.3).
- **Decision gate:** confidence ≥ 0.7 AND root cause = specific deploy → Resolution; else Escalate (§4.2).
- **Reverification:** after resolution, PASS/FAIL/ESCALATE; FAIL → 1 retry; ESCALATE → escalate (§4.4).
- **Budget:** hard cap **20** tool calls; exhaustion → escalate with gathered context (§4.6).
- Records `reflexion_loops`; produces the response fields the webhook returns.

## Prerequisites
- [ ] task 4.1 providers, 4.3 prompts, Phase-3 tools done. [ ] fake LLM for deterministic tests.

## Acceptance Criteria
- [ ] Reflexion loops capped at 2; tool-call budget enforced at 20; both observable in output/trajectory.
- [ ] Decision gate + reverification implemented; escalation path returns full context.
- [ ] Judge scores both paths (wired in Phase 6).

## Tests
- **Integration (`tests/test_agents/test_orchestrator.py`, fake LLM):** low-confidence analysis triggers ≤2 reflexion loops then escalate; high-confidence deploy → resolution → reverify PASS → rollback spec; budget exhaustion → escalate.
- **Safety-reviewer:** cap enforced, no self-eval, no execute tool.
- **Quality gate:** `--repo backend`.

## How to Verify (phase gate)
1. `pytest tests/test_agents/test_orchestrator.py -q` green with scripted fake-LLM scenarios.
2. safety-reviewer confirms budget + no-execute invariants.

## Report   ·   _filled on completion_
Built the Python orchestrator: plan by signal_type (deploy_failure fast path), reflexion (<=2 loops), confidence>=0.7 + specific-deploy gate, RollbackSpec cross-check vs deployments, reverify FAIL <=1 retry, per-incident 20-call budget (incl. parallel/fallback) -> escalate. Six agents (triage, analysis, reflexion, resolution, reverification, pr_content_generator). PipelineResult{rollback_proposed|escalated, tool_calls_used, tokens_used, models_used}; persistence via store_incident(IncidentOutcome), persist=False for eval/run_scenario.
Commits: 3e4e239 (orchestrator), a3a1dd8 (store pipeline outcome).
Tests/gate: VERDICT GREEN, 7 ran (orchestrator: env -i + TEST_DATABASE_URL); fake LLM + real Postgres; boot with no keys proven.
Verify: run the orchestrator tests with env -i and TEST_DATABASE_URL set; `poetry run sentinel serve` boots with no keys.

## BLOCKED
_none locally (fake LLM). Real-model runs ⛔ B4/B5 (not required for this task)._
