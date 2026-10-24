# backend phase 7 — Container & K8s

| | |
|---|---|
| **Repo** | `Sentinel` |
| **Branch → PR** | `dev/backend-phase-7-container-and-k8s` → `release-phase-2` · PR #26 — https://github.com/Keshav0375/Sentinel/pull/26 |
| **Tasks** | 3/3 done-pending-review |
| **Gate** | ⬜ awaiting sign-off (VERDICT GREEN on 1729dbf, full run, 7 ran, 0 skipped; boot OK) |

## What shipped

- **7.1 Dockerfile** — lock-based arm64 image, non-root, embedding model baked in and run offline, base image and model revision pinned; runs with a read-only root.
- **7.2 K8s manifests** — deployment, service, configmap, networkpolicy under `azure/k8s/`; read-only root, no auto-mounted SA token, emptyDir for /app/reports and /tmp, grace 45s.
- **7.3 Composite actions** — backend-up/down, get-kv-secrets, get-db-token, get-backend-token, notify-teams, psql-exec; callers log in first (azure/login).

## What this unblocks

- Phase 8 workflows can call the pinned composite actions; the image and manifests are ready to deploy once the CI identity exists.

## See it working

1. `docker buildx build --platform linux/arm64 -t sentinel-backend:local .` → image builds
2. `docker run --read-only --tmpfs /tmp --tmpfs /app/reports --network none ...` → /health 200
3. `poetry run pytest tests/test_infra/test_k8s_manifests.py tests/test_infra/test_composite_actions.py` → pass
4. envsubst per `azure/k8s/placeholders.txt`, then `kubectl --context orbstack -n sentinel-dev apply --dry-run=client -f $OUT` → valid

## Not done / blocked

- **(a) 🚨 Before backend phase 8: infra ticket** — gha-backend identity with a FIC for `repo:Keshav0375/Sentinel` environment `sentinel-dev` and AKS/KV/AcrPush grants; API app registration with the Incident.Write role; root outputs (ACR login server, KV URI, backend UAMI client ID, API app client ID); `seed-vault.sh` adds anthropic-api-key and openai-api-key.
- **(b) Nothing verified live** — estate is down (B1): AKS apply, LB IP, backend-up/down and startup time vs the liveness budget (no startupProbe) are unverified.
- **(c)** actionlint is missing on the CI runner, so that test skips in CI.
- **(d)** The filelock pip-audit ignore expires 2026-11-24 and is not auto-enforced.
- **(e)** automountServiceAccountToken=false combined with workload identity is unverified live.

## Decisions made during the build

- dd95eef, b384323 (caller-side login, KV URI input, trusted manifests, hardening).
- Tooling repair: Sentinel PR #25 (pip-audit filelock exception, expires 2026-11-24).
- Reviews: architecture CONFORMS, code LGTM, safety SAFE; all 8 warnings and 3 hardening notes fixed in 1729dbf.
