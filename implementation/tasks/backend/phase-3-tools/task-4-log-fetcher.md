# task-4 — `fetch_logs` → Datadog Logs API   ·   [backend / phase-3-tools]

| Field | Value |
|-------|-------|
| **Status** | `done-pending-review` |
| **Repo** | `Sentinel` (backend) |
| **Phase branch** | `dev/backend-phase-3-tools` |
| **Commit prefix** | `refactor:` |
| **Arch refs** | architecture/backend.md §3 Tools, §4.8, §13.2 |
| **Depends on** | [[task-1-config-extensions]] |
| **Referenced by** | analysis agent |

## Spec
Rewrite `fetch_logs` to call the Datadog Logs API via httpx (was synthetic).

**Files modified:** `src/sentinel/tools/log_fetcher.py`
- Input `LogQuery{service, window_minutes, level?}` → Output `LogAnalysis{entries, count, ...}`.
- httpx async call to Datadog Logs API using `dd_api_key`/`dd_app_key`/`dd_site` from config; retry w/ backoff (CLAUDE.md: 3 attempts 1/2/4s); read-only; structured `ToolError` on failure.
- Respect `SENTINEL_FAKE_LLM`/test mode by allowing an injected client for deterministic tests.

## Prerequisites
- [ ] task 3.1 config. [ ] ⛔ B6 Datadog keys for live calls (tests use a mock httpx client).

## Acceptance Criteria
- [ ] Real Datadog query shape correct (endpoint, auth headers, time window); returns typed entries.
- [ ] Retries/backoff on transient errors; structured error return (never raw raise).

## Tests
- **Unit (`tests/test_tools/test_log_fetcher.py`):** mocked httpx returns a canned Datadog response → parsed correctly; error path returns structured error; retry invoked on 5xx.
- **Quality gate:** `--repo backend`.

## How to Verify (phase gate)
1. `pytest tests/test_tools/test_log_fetcher.py -q` green (mocked).
2. (with B6) a live query returns recent logs for `sentinel-watchtower`.

## Report   ·   _filled on completion_
Built `fetch_logs` per decision 2026-10-14: evidence = Datadog Synthetics results (tests tagged `service:<svc>`; failure code/message, snippets) + CI deploy logs (v2 logs search `service:<svc> (@deploy.status:* OR "deploy.completed")`). URLs built from `dd_site`; 3 attempts w/ backoff on transient errors only, 429 honours Retry-After (cap 10s); missing key -> ToolFailure(unavailable). New `LogFetchResult` has `sources`; `LogAnalysis` untouched; output truncated. Scope: `ToolDeps` gained settings; `build_log_analyst_agent` dropped scenario.
Commit `5423739` refactor: fetch_logs reads Datadog Synthetics results and CI deploy logs.
Files: tools/log_fetcher.py, models/tools.py, tools/registry.py, agents/log_analyst.py, agents/prompts/log_analyst.txt, main.py, eval/runner.py, tests (conftest, test_log_fetcher, test_registry, test_log_analyst).
Live check skipped: no scoped DD keys yet; Sentinel/.env has DD_SITE=datadoghq.com, must become us5.datadoghq.com.

## Tests
56 tests on httpx MockTransport, no network. Gate: VERDICT GREEN (7 ran; env -i + TEST_DATABASE_URL). Tree clean, no attribution.

## How to Verify (phase gate)
1. `pytest tests/test_tools/test_log_fetcher.py -q` green (mocked).
2. (with B6, DD_SITE=us5.datadoghq.com) a live query returns Synthetics results and deploy logs for the service.

## BLOCKED
_Live calls ⛔ B6. Code + mocked tests writable now._
