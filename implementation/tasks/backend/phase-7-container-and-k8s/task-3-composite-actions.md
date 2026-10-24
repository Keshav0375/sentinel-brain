# task-3 — Composite actions (backend-up/down, kv-secrets, teams, psql)   ·   [backend / phase-7-container-and-k8s]

| Field | Value |
|-------|-------|
| **Status** | `done-pending-review` |
| **Repo** | `Sentinel` (backend) |
| **Phase branch** | `dev/backend-phase-7-container-and-k8s` |
| **Commit prefix** | `feat:` |
| **Arch refs** | architecture/backend.md §8.5, §9 (actions table), §13.3 |
| **Depends on** | [[task-2-k8s-manifests]]; infra [[task-1-aks-module]], [[task-3-keyvault-module]] |
| **Referenced by** | ALL backend workflows (Phase 8). *Not* sentinel-deployment: its record stage inlines the SQL (decision 2026-10-05, R13). |

> ⚠ **rev-5 (2026-07-12):** **seven** actions, not five. Two new token-minting actions replace
> stored credentials — `get-db-token` (Entra token for Postgres) and `get-backend-token` (Entra
> bearer for the backend API). `psql-exec` now takes a **token**, never a `db-password`. See
> sentinel §9.

## Spec
The seven reusable composite actions that are the execution building blocks. Built before the
workflows that use them.

**Files created (`.github/actions/*/action.yml`):**
- `backend-up` — nodepool→1, `kubectl apply -f azure/k8s/`, scale replicas→1, wait rollout, resolve LB IP, poll `/health`+`/ready`, output `backend-url` (§8.5). No static URL.
- `backend-down` — skip if `SENTINEL_KEEP_WARM=true`; `kubectl delete -f service.yaml` (release IP), replicas→0, nodepool→0.
- `get-kv-secrets` — input `names`; fetch via `az keyvault secret show`, `::add-mask::` each, one output per secret.
- `get-db-token` — `az account get-access-token --resource https://ossrdbms-aad.database.windows.net`; `::add-mask::` it; output `db-token`. Short-lived (~1 h), never stored.
- `get-backend-token` — `az account get-access-token --resource api://sentinel-backend`; `::add-mask::` it; output `api-token` for the `Authorization: Bearer` header.
- `notify-teams` — inputs title/body/severity/webhook-url → POST Teams webhook.
- `psql-exec` — inputs `sql` + **`db-token`** (from `get-db-token`, used as the psql password) → run against sentinel PostgreSQL, output `result` (JSON). **No `db-password` input.**

## Prerequisites
- [ ] actionlint. [ ] AKS + Key Vault + PostgreSQL (⛔ B1) for live runs; azure/login OIDC (task infra 1.3).
- [ ] ⛔ B10 (Entra DB roles) for `get-db-token`; ⛔ B11 (backend app registration) for `get-backend-token`.

## Acceptance Criteria
- [ ] All **seven** validate under actionlint; `backend-up` outputs `backend-url`; every token/secret is `::add-mask::`ed; `backend-down` honors KEEP_WARM.
- [ ] `psql-exec` accepts a token and has no password input anywhere in its interface.
- [ ] Cross-repo usable (`uses: Keshav0375/Sentinel/.github/actions/psql-exec@main`).

## Tests
- **Lint:** actionlint, yamllint, shellcheck on embedded scripts.
- **Integration (⛔ B1):** in a scale workflow, backend-up brings up + returns a reachable URL; backend-down releases the IP.
- **Quality gate:** `--repo backend`.

## How to Verify (phase gate — end of Category 3 Phase 7)
VERIFY: `pytest tests/test_infra/test_composite_actions.py`; `python3 scripts/gate.py backend`.
1. actionlint clean on all five.
2. (with AKS) `ci_backend_scale up` uses backend-up → reachable `/health`; `down` → node pool 0.

## Report   ·   _filled on completion_
Built seven composite actions (backend-up/down, get-kv-secrets, get-db-token, get-backend-token, notify-teams, psql-exec) plus `.github/actions/README.md` (pin by commit SHA, never @main). Commit 91f923b on dev/backend-phase-7-container-and-k8s.
Files: `.github/actions/*/action.yml`, `tests/test_infra/test_composite_actions.py` (54 tests, 0 skipped).
I/O per §9: pg-token, bearer, psql-exec(sql, pg-token), backend-url. Inputs reach run only via env:; all tokens masked; psql -v carries values.
backend-down honours keep-warm, deletes Service, scales to 0, never `az aks stop`. backend-up starts AKS only if stopped.
get-kv-secrets: six fixed outputs; github-pat and LLM keys excluded on purpose.
Live use needs the CI identity infra ticket (decision dd95eef) before phase 8.

## Tests
Gate: VERDICT GREEN (full run); backend boot OK. actionlint probe, shellcheck, yamllint clean; stubbed dry-runs cover every action (actionlint test skips on CI runner lacking it).

## BLOCKED
_Live runs ⛔ B1. YAML + lint now._
