# task-3 — `POST /generate/pr-content` endpoint   ·   [backend / phase-5-api]

| Field | Value |
|-------|-------|
| **Status** | `verified` |
| **Repo** | `Sentinel` (backend) |
| **Phase branch** | `dev/backend-phase-5-api` |
| **Commit prefix** | `feat:` |
| **Arch refs** | architecture/backend.md §3.4 |
| **Depends on** | [[task-4-pr-content-generator]] |
| **Referenced by** | [[task-3-ci-incident-response]] (generate-pr-content job) |

## Spec
The single endpoint that serves rollback PR content (demo PRs do NOT use it).

**Files created:** `src/sentinel/api/generate.py`
- `POST /generate/pr-content` — input per §3.4 (incident_id, root_cause, evidence_summary, confidence, target_deploy, resolution_type), token-protected → calls the `pr_content_generator` agent → `{title, description, model_used, tokens_used}`.

## Prerequisites
- [ ] task 4.4 agent. [ ] token auth (5.5). [ ] fake LLM for tests.

## Acceptance Criteria
- [ ] Endpoint returns the §3.4 response shape; title `revert:`-prefixed; 401 without token.
- [ ] Only wired to the agent (no PR creation here — GHA does that).

## Tests
- **Integration (`tests/test_api/test_generate.py`, fake LLM):** POST sample incident context → title + description present, model_used set; auth enforced.
- **Quality gate:** `--repo backend`.

## How to Verify (phase gate)
1. `pytest tests/test_api/test_generate.py -q` green.
2. (with B4) live call returns a realistic revert PR body.

## Report   ·   _filled on completion_
Built 2026-10-18, commit a9477f2 (from ee94c2d): POST /generate/pr-content; service from the stored incident; 404 unknown, 409 no matching deploy, 503 DB/unavailable, 502 after fallback; text only, never a PR.
Tests: 16 added. Integrated gate (backend, env -i + TEST_DATABASE_URL): VERDICT GREEN (7 ran). Live boot: /health ok, /ready 200.

Review fixes 2026-10-21 (d0f7ae9..d27a8f3, status stays done-pending-review): 17edf2b agents SDK errors (AgentsException) map to 502. Gate on d27a8f3: VERDICT GREEN (full run, 7 ran, 0 skipped, TEST_DATABASE_URL set); boot OK (/health 200, /ready 200, protected 401, clean exit).

## BLOCKED
_Live call ⛔ B4. Endpoint + fake tests writable now._
