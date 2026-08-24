# task-5.3 — Platform layer — shared ACR, AKS, Postgres   ·   [infra / phase-5-dynamic-foundations]

| Field | Value |
|-------|-------|
| **Status** | `not-started` |
| **Repo** | `Sentinel-infra` |
| **Phase branch** | `dev/infra-phase-5-dynamic-foundations` |
| **Commit prefix** | `feat:` |
| **Arch refs** | infra.md §3 (rewritten), decisions.md 2026-08-24 |
| **Depends on** | [[task-1-config-and-naming]], [[task-2-three-identities]] |

## Spec
The resources every deployment shares, in their own resource group and their own Terraform
workspace.

```
rg-sentinel-platform-cc
  acrsentinelplatform<uid>   one registry, all images, all deployments
  aks-sentinel-platform      ONE cluster — deployments get namespaces, not clusters
  psql-sentinel-platform     shared server; deployments get a database on it
```

**Why one cluster.** The subscription's regional quota is **6 vCPU** and an AKS node is 2. A
cluster per deployment stops at three, with no headroom. A namespace per deployment scales to
whatever the cluster's RAM holds. The isolation is not weaker for being logical: workload
identity federates on `system:serviceaccount:<namespace>:<sa>`, so a pod in one namespace cannot
mint a token for another's Key Vault. That is enforced by the token exchange, not by naming.

**AKS:** `oidc_issuer_enabled`, `workload_identity_enabled`, one `Standard_B2pls_v2` ARM64 node,
`ignore_changes` on node_count. Backend images must therefore build `linux/arm64` — unchanged
from phase 3.

**Postgres:** one flexible server, Entra-only auth, pgvector. Deployments in `mode: shared` get
a database and an Entra role here; `mode: dedicated` builds its own server in its own RG (task
6.3).

**Separate workspace is not a preference, it is a safety property.** In one state,
`terraform destroy` of a deployment would take the cluster with it. Separate states make that
structurally impossible.

## Prerequisites
- [ ] 5.1 naming · [ ] 5.2 identities · [ ] regional vCPU quota ≥ 2 free

## Acceptance Criteria
- [ ] `terraform workspace list` → `platform` exists and is selected for these resources
- [ ] AKS OIDC issuer URL is a root output (deployments consume it)
- [ ] ACR is Standard (the free grant covers 1 Standard registry — Basic is a different, billable meter)
- [ ] Outputs published for every value a deployment needs: cluster name, OIDC issuer, ACR login server, PG FQDN, PG admin
- [ ] Nothing here references a deployment name

## Tests
- **Integration:** `az aks get-credentials` then `kubectl get nodes` → 1 Ready.
- **Integration:** Entra-token `psql` login to the shared server.
- **Quality gate:** `--repo infra`.

## How to Verify (phase gate)
1. `terraform workspace select platform && terraform output`
2. `kubectl get nodes` → one node, Ready.

## Report   ·   _filled on completion_
_not yet implemented_
