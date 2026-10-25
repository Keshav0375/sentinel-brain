# task-2 — End-to-end integration smoke + eval   ·   [backend / phase-9-cleanup]

| Field | Value |
|-------|-------|
| **Status** | `done-pending-review` |
| **Repo** | `Sentinel` (backend) + full system |
| **Phase branch** | `dev/backend-phase-9-cleanup` |
| **Commit prefix** | `test:` |
| **Arch refs** | master ARCHITECTURE.md §2 (end-to-end flow); sentinel §9.3; deployment §4 |
| **Depends on** | ALL categories complete + infra/deployment verified |
| **Referenced by** | project completion |

## Spec
The final proof: a real demo failure flows through the whole system and produces a revert PR
(Condition C) and a runtime-triggered incident (Condition B), with eval scores recorded.

**Artifacts:**
- `tests/test_e2e/` — an orchestrated smoke that (offline, FAKE_LLM + local pgvector) exercises webhook → pipeline → rollback spec/escalation → judge, asserting stored incident + scores.
- A documented **live demo runbook** (`reports/DEMO.md`) for the full-stack path: dispatch demo PR #3 (C) and #11 (B), watch Datadog fire → dispatch → incident workflow → revert PR + Teams + LangFuse trace.

## Prerequisites
- [ ] All 54 prior tasks `verified`. [ ] ⛔ B1–B9 + all cloud wiring for the LIVE demo (the offline e2e smoke runs without cloud).

## Acceptance Criteria
- [ ] Offline e2e smoke green (webhook→pipeline→judge, both paths).
- [ ] Live demo runbook reproduces: Condition C → revert PR on sentinel-deployment; Condition B → runtime-health incident → revert PR; both traced in LangFuse with judge scores.
- [ ] MTTR + judge scores visible; correlation IDs traceable incident→PR→deploy→logs→trace.

## Tests
- **E2E offline:** `pytest tests/test_e2e -q` (FAKE_LLM + local DB).
- **Full-stack (⛔ B1–B9):** the DEMO.md runbook end to end.
- **Quality gate:** `--repo backend` across the whole repo.

## How to Verify (phase gate — FINAL, Category 3 Phase 9)
1. `pytest tests/test_e2e -q` green.
2. Full-stack: run the DEMO.md steps → observe a revert PR + Teams notification + LangFuse trace for both a C and a B scenario.

## Report
Built offline e2e smoke + terminal-state LangFuse dataset item. Commit 180be42 on dev/backend-phase-9-cleanup: "test: offline end-to-end smoke + terminal-state LangFuse dataset item (sentinel-scenario-runs)".
Files: src/sentinel/eval/dataset_writer.py (new; one item per terminal incident, best effort, strips R14 data), agents/orchestrator.py (mttr set at terminal state), models/alert.py (PRDetails.branch), scripts/incident_dispatch.py (forwards head.ref as branch), scripts/quality_gate.py + ci_backend_deployment.yml (tests/test_e2e in integration), tests/test_e2e/ (7 tests: both paths, dedupe, SHA mismatch, judge scoring, no-outbound-network guard), writer/dispatch/alert tests.
Gate: VERDICT GREEN (full run, 7 ran, 0 skipped); full pytest 2127 passed; boot probe /health and /ready 200, protected routes 401.
Not yet run: live demo (pass/01, deployfail/03, runtime/01) - gated on infra CI-identity ticket, default-branch switch, REVERT_PR_PAT, real LLM keys, estate up. Runbook goes in reports/DEMO.md at close-phase. Decisions: 3c492de, 9320bb1, b0fa4a4.
Review fix `3f7cdd3` ("fix: phase 9 review — branch kept out of prompts, dataset write off the critical path, Phase-1 models removed"): pr_details.branch is eval metadata only (excluded from all agent prompts via agent_view(), validated, catalog-checked); dataset write runs in the DatasetWrites background registry with a 10 s timeout, drained at shutdown; _dataset_ready set only on success or 409; failure logs carry field names only; e2e drain has a timeout. Gate: VERDICT GREEN on 3f7cdd3 (full run); boot OK. Decisions: 3c492de, 9320bb1, b0fa4a4, 8e763a0, 934fe7d.

## BLOCKED
_Live full-stack demo ⛔ B1–B9 + all upstream phases verified. Offline e2e smoke writable now._
