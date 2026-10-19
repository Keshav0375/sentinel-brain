# backend phase 4 — Agent Pipeline & Loops

| | |
|---|---|
| **Repo** | `Sentinel` |
| **Branch → PR** | `dev/backend-phase-4-agents` → `release-phase-2` · PR #22 — https://github.com/Keshav0375/Sentinel/pull/22 |
| **Tasks** | 4/4 green |
| **Gate** | ⬜ awaiting sign-off (VERDICT GREEN at fac21a9) |

## What shipped

- **4.1 Provider router** — model router with fake LLM, R14 bridge, default trace exporter dropped.
- **4.2 Orchestrator** — Python pipeline orchestrator with persistence, distinct judge + judge_conflict guard, 600s configurable run timeout.
- **4.3 Prompts** — reflexion and reverification prompts.
- **4.4 PR content generator** — drafts PR content, detects done-claims.

## What this unblocks

- Phase 5 webhook/API wiring can call the orchestrator and read PipelineResult.

## See it working

1. ```bash
   docker start sentinel-pg-test
   TEST_DATABASE_URL=<url> pytest tests/test_agents/test_orchestrator.py tests/test_providers -q
   ```
   → expect: pass
2. ```bash
   SENTINEL_FAKE_LLM=1 DATABASE_URL= poetry run sentinel serve
   curl -s -X POST localhost:8000/webhooks/alert -H 'content-type: application/json' -d '{"source":"datadog","service":"checkout","metric":"error_rate","threshold":0.05,"current_value":0.4,"severity":"critical"}'
   curl -s localhost:8000/incidents/<incident_id>
   ```
   → expect: 202 with incident_id, then PipelineResult

## Not done / blocked

- **Live end-to-end run** — .env has placeholder keys; needs Anthropic key plus OpenAI key (gpt-4.1 judge, gpt-4o fallback).
- Fast path should also compare to context.pr_details.sha once phase-5 webhook body exists.
- Webhook auth (phase 5): signal_type is caller-chosen (still gated).
- models/remediation.py RemediationPlan is unused.
- Judge not run on fake LLM (phase 6).
- Older carry-overs: deployment live smoke, Azure alembic+grant, guard-main-source.yml.

## Decisions made during the build

- 2026-10-15 Backend phase 4 + exporter amendment; 2026-10-18 distinct judge (R14 closed).
- Reviews: architecture-warden CONFORMS; safety-reviewer UNSAFE then SAFE; code-reviewer LGTM.
