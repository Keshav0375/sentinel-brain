# deployment phase 1 — The App

| | |
|---|---|
| **Repo** | `Sentinel-deployment` |
| **Branch → PR** | `dev/deploy-phase-1-app` → `main` · PR #1 — https://github.com/Keshav0375/Sentinel-deployment/pull/1 |
| **Tasks** | 2/2 green |
| **Gate** | ⬜ awaiting sign-off |

## What shipped

- **1.1 FastAPI app** — `sentinel-watchtower` app with config, startup log, endpoints, requirements, `.env.example`, README (bad8fbd).
- **1.2 App tests** — 4 tests for endpoints and startup log; review fix asserts exact `/health` shape (04ad349, fb84894).

## What this unblocks

- Phase 2 (deploy pipeline) now has a runnable, tested app to containerize and deploy.

## See it working

1. ```bash
   cd /Users/keshav/Projects/Sentinel-deployment && pip install -r requirements-dev.txt && pytest tests/ -q
   ```
   → expect: 4 passed
2. ```bash
   uvicorn app.main:app --port 8000 & sleep 2; curl localhost:8000/health
   ```
   → expect: exact health JSON; startup log line printed

## Not done / blocked

- **Skipped checks:** yamllint, actionlint reported n/a (no such paths ever existed in repo history). Ran: ruff-lint, gitleaks, pytest. Verdict GREEN.
- Infra local gate is PARTIAL (tfsec/yamllint non-zero, no Sentinel-infra .venv); pre-existing, unrelated.
- Infra follow-up: app-service `DD_SERVICE` still `dummy-api-0375`, so the deployed app reports that until the R7/R11/R12 infra fix lands.

## Decisions made during the build

- **Gate rule change (user, 2026-10-04):** a check skipped only because its path never existed in repo history is n/a and does not demote GREEN; a path that existed and was lost stays PARTIAL. Brain commits 80ce6fe, c3940c2, 0e05f29. Limitation: a MATRIX path typo reads n/a forever; fixing needs per-task required-path lists.
- `port` in `app/config.py` is unused at runtime (start command binds its own port); kept per §2.4.
- Uptime clock starts at import (fine without gunicorn `--preload`).
- StarletteDeprecationWarning: TestClient httpx → httpx2 on pinned dev deps (follow-up).
- Reviews: architecture-warden CONFORMS (+2 notes); code-reviewer LGTM; safety-reviewer n/a.
