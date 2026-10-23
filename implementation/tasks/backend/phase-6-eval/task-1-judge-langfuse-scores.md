# task-1 — `eval/judge.py` → LangFuse scores   ·   [backend / phase-6-eval]

| Field | Value |
|-------|-------|
| **Status** | `done-pending-review` |
| **Repo** | `Sentinel` (backend) |
| **Phase branch** | `dev/backend-phase-6-eval` |
| **Commit prefix** | `refactor:` |
| **Arch refs** | architecture/backend.md §3 (judge both paths), §6.4, §13.2 |
| **Depends on** | [[task-4-langfuse-tracing]], [[task-2-orchestrator-loops]], [[task-1-provider-routing]] |
| **Referenced by** | [[task-2-eval-runner-datasets]], [[task-1-webhook-receiver]] (scores stored) |

## Spec
Judge scores trajectory quality on both rollback and escalation paths; scores pushed to
LangFuse and stored on the incident row (`eval_score` JSONB).

**Files modified:** `src/sentinel/eval/judge.py`
- Judge agent (model per §4.7 / dec 2026-10-18, **different family/model discipline** from graded agents — safety invariant) scores per-dimension (triage_accuracy, root_cause_correctness, etc.).
- `push_score(trace_id, name, value)` per dimension (§6.4); return structured `JudgeResult`.
- Evaluates reasoning quality, not outcome (§3): good escalation can score well.

## Prerequisites
- [ ] Phase-4 orchestrator, tracing (2.4). [ ] fake LLM for deterministic tests.

## Acceptance Criteria
- [ ] Scores both paths; per-dimension values in [0,1]; pushed to LangFuse; stored on incident.
- [ ] Judge model distinct from the agents it grades (no self-eval).

## Tests
- **Integration (`tests/test_eval/test_judge.py`, fake LLM):** rollback + escalation trajectories both scored; scores stored; safety-reviewer confirms no self-grading.
- **Quality gate:** `--repo backend`.

## How to Verify (phase gate)
1. `pytest tests/test_eval/test_judge.py -q` green (from ../Sentinel).
2. (B7 closed 2026-09-13) scores appear on the LangFuse trace.

## Report
Built in Sentinel commit faf7412 on dev/backend-phase-6-eval: "refactor: eval judge scores 0-1, pushes one LangFuse score per dimension, stores incidents.eval_score". Both outcomes judged; conflict stored but not pushed; eval_score shape `{judge_model, judge_conflict, scores, reasoning}`. Judge not wired into live pipeline (6.2 runner is the scorer; dec 2026-10-22, brain 1ffd083).
Files: models/eval_result.py; eval/{rubric,judge,report,runner}.py; memory/episodic.py (new store_eval_score); dashboard/eval.html; scripts/run_eval.py; tests.

## Tests
~30 new tests plus existing rescaled /5: 0-1 validators, eval_score shape, both outcomes, conflict not pushed, R14 values-only, store_eval_score on real pgvector. Gate: VERDICT GREEN (full run, 7 ran, 0 skipped). Boot OK: /health 200, /ready 200, protected routes 401.

## BLOCKED
_Resolved: B7 closed 2026-09-13; no longer blocking._
