# task-2 — `azure/k8s/` deployment + service manifests   ·   [backend / phase-7-container-and-k8s]

| Field | Value |
|-------|-------|
| **Status** | `verified` |
| **Repo** | `Sentinel` (backend) |
| **Phase branch** | `dev/backend-phase-7-container-and-k8s` |
| **Commit prefix** | `feat:` |
| **Arch refs** | architecture/backend.md §8.1, §8.5, §13.3 |
| **Depends on** | [[task-1-dockerfile-update]], [[task-4-health-ready-probes]]; infra [[task-1-aks-module]] |
| **Referenced by** | [[task-3-composite-actions]] (backend-up applies these), [[task-2-ci-backend-deployment]] |

## Spec
The K8s manifests the backend-up action applies. Single replica; Service is created/deleted
per run (dynamic URL, §8.5).

**Files created:**
- `azure/k8s/deployment.yaml` — Deployment `sentinel-backend`, `replicas: 1`, `strategy: Recreate`, image `sentinelacr.azurecr.io/sentinel-backend:sha-PLACEHOLDER` (CI sets via `kubectl set image`), `envFrom: sentinel-secrets`, readiness `/ready` (initialDelay 10), liveness `/health` (initialDelay 15), resources requests 250m/512Mi limits 1/2Gi.
- `azure/k8s/service.yaml` — `Service type: LoadBalancer`, selector app=sentinel-backend, port 80→8000.

## Prerequisites
- [ ] task 7.1 image. [ ] kubectl (for `--dry-run` validation). [ ] AKS (⛔ B1) for a live apply.

## Acceptance Criteria
- [ ] `kubectl apply --dry-run=client -f azure/k8s/` validates both manifests.
- [ ] Probes point at `/ready` + `/health`; envFrom the K8s Secret; Recreate strategy (never 2 pods on the 4 GB node).
- [ ] A `NetworkPolicy` allowing ingress to the backend pods on the service port from the LoadBalancer and from the AKS health probes. The cluster enforces the namespace's `default-deny-ingress` via Cilium (infra PR #16, 2026-10-05), so without this rule `/health` is unreachable through the LB.

## Tests
- **Validate:** `kubectl apply --dry-run=client`; kubeconform/kubeval (optional); yamllint.
- **Integration (⛔ B1):** apply to AKS → pod Ready, LB IP assigned, `/health` reachable.
- **Quality gate:** `--repo backend` (+ manifest lint).

## How to Verify (phase gate)
0. Gate: VERDICT GREEN (full run); backend boot OK; yamllint --strict clean; 25 tests in tests/test_infra/test_k8s_manifests.py.
1. `kubectl apply --dry-run=client -f azure/k8s/` → valid.
2. (with AKS) apply → `kubectl get pods` Ready; `kubectl get svc` shows an external IP serving `/health`.

## Report   ·   _filled on completion_
Built in 830bf34 "feat: azure/k8s manifests (deployment, service, configmap, networkpolicy)" on dev/backend-phase-7-container-and-k8s.
Files: azure/k8s/{deployment,service,configmap,networkpolicy}.yaml, azure/k8s/placeholders.txt (envsubst var list + recipe), tests/test_infra/test_k8s_manifests.py (25 tests).
No serviceaccount.yaml (infra owns SA sentinel-backend); no namespace in manifests, so pass -n sentinel-dev. Deployment: Recreate, 1 replica, WI label, grace 45s, /ready 10s + /health 15s probes, 250m/512Mi req, 1/2Gi limits, non-root, drop ALL. ConfigMap non-secret only; NetworkPolicy allows TCP 8000. kubectl dry-run=client (orbstack) passed.
Unverified live: startup time vs liveness budget (no startupProbe); B1 estate down. Decisions: dd95eef.
Review fixes 1729dbf (2026-10-24): automountServiceAccountToken false; readOnlyRootFilesystem true with emptyDir mounts for /app/reports and /tmp. Unverified live: automountServiceAccountToken=false combined with workload identity. Gate VERDICT GREEN on 1729dbf (full run, 7 ran, 0 skipped); boot OK. Decisions: dd95eef, b384323.

## BLOCKED
_Live apply ⛔ B1. Manifests + dry-run validate now._
