# task-4 — `pr_content_generator` agent + prompt   ·   [backend / phase-4-agents]

| Field | Value |
|-------|-------|
| **Status** | `verified` |
| **Repo** | `Sentinel` (backend) |
| **Phase branch** | `dev/backend-phase-4-agents` |
| **Commit prefix** | `feat:` |
| **Arch refs** | architecture/backend.md §3.4 (contract + prompt rules), §13.3 |
| **Depends on** | [[task-1-provider-routing]] |
| **Referenced by** | [[task-3-generate-pr-content-endpoint]] |

## Spec
The agent that writes the **rollback** PR title + description during an incident (the only
consumer is `ci_incident_response.yml`). No tools — pure constrained generation, Haiku.

**Files created:**
- `src/sentinel/agents/pr_content_generator.py` — Agent def, model `anthropic/claude-haiku-4-5` (fb `openai/gpt-4o-mini`), no tools, traced as `pr-content-generation` span.
- `src/sentinel/agents/prompts/pr_content_generator.txt` — per §3.4 key instructions: title `revert:` prefix < 72 chars with PR# + incident id; description sections Incident/Root Cause/Evidence/Rollback; state confidence plainly; 100–200 words.

## Prerequisites
- [ ] task 4.1 providers. [ ] fake LLM for tests.

## Acceptance Criteria
- [ ] Given the §3.4 input (root_cause, evidence, confidence, target_deploy) produces `{title, description, model_used, tokens_used}`.
- [ ] Title format + description sections match §3.4; no tools attached.

## Tests
- **Unit (`tests/test_agents/test_pr_content_generator.py`, fake LLM):** output has a `revert:`-prefixed title with PR# + incident id, all four description sections, confidence stated.
- **Quality gate:** `--repo backend`.
- **Result:** 38 tests (7 ran in gate); gate VERDICT GREEN (orchestrator, env -i + TEST_DATABASE_URL); tree clean, attribution none.

## How to Verify (phase gate — end of Category 3 Phase 4)
1. `pytest tests/test_agents/test_pr_content_generator.py -q` green (fake).
2. (with B4) a real Haiku call returns a well-formed revert PR body.

## Report   ·   _filled on completion_
Built `pr_content_generator` agent + prompt (commit 98751f8, Sentinel, feat: pr_content_generator agent + prompt — §3.4 revert PR title and description). No tools; router haiku (fb gpt-4o-mini) via call_with_fallback; Langfuse prompt loader linked via use_agent_prompts; span `pr-content-generation`, no IO. RollbackSpec -> PRContent{title, description, model_used, tokens_used}. Title (revert:, PR #, incident id, <72) and description (4 sections, confidence, 100-200 words) rules enforced in code with deterministic fallbacks. Plain-text reply. Not yet wired to an endpoint (phase 5).

## BLOCKED
_Live call ⛔ B4. Agent + prompt + fake tests writable now._
