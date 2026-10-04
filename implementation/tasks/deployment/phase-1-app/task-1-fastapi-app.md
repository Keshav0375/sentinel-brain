# task-1 — FastAPI app (3 routes + startup log + config)   ·   [deployment / phase-1-app]

| Field | Value |
|-------|-------|
| **Status** | `done-pending-review` |
| **Repo** | `Sentinel-deployment` |
| **Local path** | `../Sentinel-deployment` |
| **Phase branch** | `dev/deploy-phase-1-app` |
| **Commit prefix** | `feat:` |
| **Arch refs** | architecture/deployment.md §2 (all), §5 |
| **Depends on** | — (independent of infra to build; deploy target is infra 3.4) |
| **Referenced by** | [[task-2-app-tests]], [[task-2-ci-app-deployment]], [[task-1-scenario-branches]] |

## Spec
Intentionally minimal app — the deploy pipeline is the product; this is the target.

**Files created:**
- `app/__init__.py`
- `app/main.py` — FastAPI app; `GET /` → `{"message":"ok","service": settings.dd_service}`; `GET /health` → `{"status":"ok","uptime_seconds":N}`; `GET /version` → `{"version": settings.app_version, "service": settings.dd_service}` (`dd_service` defaults to `sentinel-watchtower`, R10); startup lifespan emits ONE structured JSON log line `app.startup` with dd.service/env/version (§2.2).
- `app/config.py` — `AppConfig(BaseSettings)` per §2.4: `app_version`, `dd_service`, `dd_env`, `port`.
- `requirements.txt` — exact `==` pins per §2.3: `fastapi`, `uvicorn`, `pydantic-settings`, `gunicorn` (the §2.5 start command needs it).
- `requirements-dev.txt` — `-r requirements.txt` + pinned `pytest`, `httpx`, `ruff` (never deployed; Oryx installs only `requirements.txt`).
- `.env.example` — from [implementation/env-examples/deployment.env.example](../../../env-examples/deployment.env.example) app section.
- `.gitignore` (extend), `README.md` (run locally: `uvicorn app.main:app --reload`).

## Prerequisites
- [ ] Python 3.12. [ ] pip.

## Acceptance Criteria
- [ ] `uvicorn app.main:app` boots; all three routes return the documented shapes.
- [ ] Startup emits exactly one `app.startup` structured line with dd tags + app_version from env.
- [ ] `/version` reflects `APP_VERSION` env (so demo PRs that change version are observable).

## Tests
- **Unit:** covered by [[task-2-app-tests]] (kept as its own task so the app PR stays focused; both land in this phase).
- **Quality gate:** `python3 scripts/gate.py deployment` (ruff · pytest) → `VERDICT GREEN`.

## Report
Built sentinel-watchtower FastAPI app (3 routes, one `app.startup` log line, AppConfig). Commit `bad8fbd` in Sentinel-deployment: feat: add sentinel-watchtower FastAPI app with startup log and config. Files: app/__init__.py, app/config.py, app/main.py, requirements.txt, requirements-dev.txt, .env.example, .gitignore, README.md.
Gate: VERDICT GREEN (n/a: yamllint, actionlint, pytest; ran ruff-lint, gitleaks). 7 pins co-install on 3.12.15, pip check clean; uvicorn and gunicorn (§2.5) both boot.
Gate rule change (user, 2026-10-04): missing-path skips report n/a (brain 80ce6fe).

## How to Verify (phase gate)
1. `pip install -r requirements.txt && uvicorn app.main:app --port 8000`.
2. `curl :8000/ :8000/health :8000/version` -> documented JSON; logs show one `app.startup` line.

## BLOCKED
_none — fully local._
