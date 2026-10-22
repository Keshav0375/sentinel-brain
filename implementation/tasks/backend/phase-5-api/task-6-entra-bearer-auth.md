# task-6 — `api/auth.py` — Entra bearer validation (JWKS)   ·   [backend / phase-5-api]

| Field | Value |
|-------|-------|
| **Status** | `done-pending-review` |
| **Repo** | `Sentinel` (backend) |
| **Phase branch** | `dev/backend-phase-5-api` |
| **Commit prefix** | `feat:` |
| **Arch refs** | architecture/backend.md §3.6 (Entra bearer validation) + §3 auth note |
| **Depends on** | [[task-1-phase2-dependencies]] (pyjwt), infra [[task-5-backend-entra-app]] (the app reg) |
| **Referenced by** | every non-health route (5.1, 5.2, 5.3) |

> **rev-5 (2026-07-12):** new task. Replaces the shared `X-Sentinel-Token` with Entra bearer
> auth validated against JWKS. Deletes `sentinel-api-token`.

## Spec
A FastAPI dependency that validates inbound Entra JWTs statelessly and gates non-health routes.

**Files created / changed:**
- `src/sentinel/api/auth.py` — `require_incident_write` dependency:
  - `HTTPBearer` scheme (also renders the Swagger **Authorize** button).
  - `jwt.PyJWKClient("https://login.microsoftonline.com/<tenant>/discovery/v2.0/keys")`.
  - `jwt.decode(..., algorithms=["RS256"], audience="api://sentinel-backend", issuer=<tenant issuer>)`.
  - 401 on invalid/expired/incorrect-aud/iss; 403 when `roles` lacks `Incident.Write`.
- `config.py` — read `AZURE_TENANT_ID` + `SENTINEL_API_AUDIENCE` from env (public config, from the
  `sentinel-config` ConfigMap / GitHub variables — **not** secrets).
- Wire the dependency onto `/webhooks/incident`, `/incidents*`, `/generate/pr-content`
  (via `dependencies=[Depends(require_incident_write)]` on the routers). **Leave `/health` + `/ready` open.**

**Contract:**
```
header    = Authorization: Bearer <entra jwt>
checks    = signature (RS256/JWKS), aud=api://sentinel-backend, iss=<tenant>, exp, roles∋Incident.Write
open      = GET /health, GET /ready  (K8s probes)
config    = AZURE_TENANT_ID, SENTINEL_API_AUDIENCE  (non-secret)
```

## Prerequisites
- [ ] `pyjwt[crypto]` added (task 1.1). [ ] backend Entra app reg exists (infra 3.5) for live tokens.

## Acceptance Criteria
- [ ] Valid `Incident.Write` token → 200; missing token → 401; valid token without the role → 403.
- [ ] `/health` + `/ready` reachable with no token.
- [ ] Swagger `/docs` shows an Authorize (bearer) button; authorizing attaches the token to calls.
- [ ] Tenant/audience come from config, not hardcoded, not secrets.

## Tests
- **Unit:** mock JWKS + signed test JWTs (valid / expired / wrong-aud / no-role) → assert 200/401/403.
- **Integration:** app with the dependency wired → `/health` open, `/webhooks/incident` rejects tokenless.
- **Quality gate:** `--repo backend`.

## How to Verify (phase gate)
1. Start the app; `curl` `/webhooks/incident` without a token → 401; `/health` → 200.
2. With a real `api://sentinel-backend` token (from the gha SP) → 200; a token lacking the role → 403.

## Report   ·   _filled on completion_
Built 2026-10-18, commit 5db1a20 (from c128792): Entra bearer auth (require_incident_write); v2 JWKS of identity tenant (SENTINEL_API_TENANT_ID), audience SENTINEL_API_AUDIENCE; 401/403; pyjwt[crypto] added.
Tests: 37 added. Integrated gate (backend, env -i + TEST_DATABASE_URL): VERDICT GREEN (7 ran). Live boot: /health ok, /ready 200.

Review fixes 2026-10-21 (d0f7ae9..d27a8f3, status stays done-pending-review): ab3adea SENTINEL_API_AUDIENCE is a comma-separated list; v2 tokens carry the client-id GUID. Gate on d27a8f3: VERDICT GREEN (full run, 7 ran, 0 skipped, TEST_DATABASE_URL set); boot OK (/health 200, /ready 200, protected 401, clean exit).

## BLOCKED
_Live-token verification needs infra 3.5 (backend app reg). Unit tests (mock JWKS) writable + runnable now._
