# task-2 — App tests (health / version / root)   ·   [deployment / phase-1-app]

| Field | Value |
|-------|-------|
| **Status** | `done-pending-review` |
| **Repo** | `Sentinel-deployment` |
| **Phase branch** | `dev/deploy-phase-1-app` |
| **Commit prefix** | `test:` |
| **Arch refs** | architecture/deployment.md §2.1, §5 |
| **Depends on** | [[task-1-fastapi-app]] |
| **Referenced by** | [[task-2-ci-app-deployment]] (CI runs these) |

## Spec
Endpoint tests using FastAPI `TestClient`.

**Files created:** `tests/__init__.py`, `tests/test_app.py`
- `test_root` — 200, body `{"message":"ok","service":"sentinel-watchtower"}`.
- `test_health` — 200, `status == "ok"`, `uptime_seconds` is an int ≥ 0.
- `test_version` — 200, `version` matches configured `app_version`, `service == "sentinel-watchtower"`.
- `test_startup_log` (optional) — capture the startup log line shape.
- Add `pytest` (+`httpx`) to a dev-requirements or `requirements-dev.txt`.

## Prerequisites
- [ ] task 1.1 app exists. [ ] pytest installed.

## Acceptance Criteria
- [ ] `pytest tests/ -x` green; covers all three endpoints + response shapes.
- [ ] Tests import the app without hitting the network (TestClient).

## Tests
- **Unit:** the file itself. **Quality gate:** `--repo deployment` (ruff + pytest + actionlint on any workflows present).

## Report
Added tests/__init__.py, tests/test_app.py (4 tests: root, health, version via APP_VERSION, startup_log). Commit `04ad349` in Sentinel-deployment: test: add endpoint and startup-log tests for sentinel-watchtower. Env/.env isolation proven; mutation check confirmed failures on breakage.
Gate: VERDICT GREEN (n/a: yamllint, actionlint; ran ruff-lint, gitleaks, pytest).
Review fix `fb84894` in Sentinel-deployment: test: assert exact /health response shape (Refs #41).
Follow-up: StarletteDeprecationWarning (httpx -> httpx2 for TestClient) on pinned dev deps.

## How to Verify (phase gate)
1. `pytest tests/ -q` -> all pass.
2. `python3 scripts/gate.py deployment` -> `VERDICT GREEN`.

## BLOCKED
_none — fully local._
