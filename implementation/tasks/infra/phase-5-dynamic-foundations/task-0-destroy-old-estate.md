# task-5.0 — Destroy the old estate   ·   [infra / phase-5-dynamic-foundations]

| Field | Value |
|-------|-------|
| **Status** | `not-started` |
| **Repo** | `Sentinel-infra` |
| **Phase branch** | `dev/infra-phase-5-dynamic-foundations` |
| **Commit prefix** | `chore:` |
| **Arch refs** | decisions.md 2026-08-24 (phase-5/6 dynamic platform) |
| **Depends on** | _none — this runs first_ |

## Spec
The phase-1-to-4 estate is built on a naming scheme and a resource-group model that phases 5-6
replace. It is **deleted, not migrated** (owner decision): nothing is deployed into it, so this
is the cheapest this will ever be, and leaving it beside the new model would mean maintaining
two schemes forever.

**Order matters — state goes last, because it describes everything above it.**

```bash
az postgres flexible-server start -n sentinel-pg-0375 -g sentinel-rg   # destroy must read it
terraform destroy                                                       # default workspace
az group delete --name sentinel-rg      --yes
az group delete --name sentinel-func-rg --yes
az keyvault purge --name sentinel-kv-0375 --location canadacentral       # else name reserved 7d
az group delete --name sentinel-state-rg --yes
```

Then re-bootstrap state storage under the new scheme (`st<org>tfstate<uid>`), because
`sentineltfstate0375` carries the same ad-hoc `0375` suffix this phase removes.

**Survives deliberately:** `sentinel-tf-identity` in the identity tenant and its three federated
credentials. They are repo-scoped, not deployment-scoped, so they stay valid — and re-creating
them means another interactive cross-tenant login.

**Deleted as a consequence:** `azuread_application.sentinel_backend` and `sentinel_gha_client`
are Terraform-managed, so `destroy` removes them. Phase 6 recreates them per deployment.

## Prerequisites
- [ ] Owner-level `az` login in the SCHOOL tenant (`az account show` → `Azure for Students`)
- [ ] Confirm nothing is deployed into the estate — vault empty, no AKS workloads, no DB schema

## Acceptance Criteria
- [ ] `az group list --query "[?starts_with(name,'sentinel')]"` → empty
- [ ] `az keyvault list-deleted --query "[?name=='sentinel-kv-0375']"` → empty (purged, not just deleted)
- [ ] New state account exists, `terraform init` reports "Successfully configured the backend"
- [ ] `sentinel-tf-identity` still present with 3 federated credentials

## Tests
- **Destructive, verified by absence.** Re-run each `az group show` and expect `ResourceNotFound`.
- **Quality gate:** `--repo infra`.

## How to Verify (phase gate)
1. `az group list -o table` shows only the new state resource group.
2. `az ad app federated-credential list --id 378ccade-…` (identity tenant) still shows 3.

## Report   ·   _filled on completion_
_not yet implemented_
