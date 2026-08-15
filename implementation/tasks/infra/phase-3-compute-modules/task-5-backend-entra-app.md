# task-5 — Identity plane: backend Entra app (two-tenant)   ·   [infra / phase-3-compute-modules]

| Field | Value |
|-------|-------|
| **Status** | `not-started` |
| **Repo** | `Sentinel-infra` |
| **Local path** | `../Sentinel-infra` |
| **Phase branch** | `dev/infra-phase-3-compute-modules` |
| **Commit prefix** | `feat:` |
| **Arch refs** | architecture/infra.md §4.4, §4.5, §9 |
| **Depends on** | [[task-3-oidc-federation]], **B11** |
| **Referenced by** | backend task 5.6 (`api/auth.py`), [[task-1-cross-repo-secrets]] |

> ⚠ **rev-9 / R4 (2026-08-15) — this task was rewritten for the two-tenant split.**
> These app registrations do **not** live in the Azure subscription's tenant. `uwindsor.ca`
> denies app registration at tenant policy and UWindsor IT is not an option, so they live in
> a **personally-owned Entra tenant** holding nothing else. Everything else in Sentinel stays
> in the school tenant. See `architecture/decisions.md` → "R4 resolved — two-tenant identity
> split".

## Spec
Give the backend a real API identity so callers present **audience-scoped Entra tokens**
instead of a shared secret — the change that deleted `sentinel-api-token` in rev-5.

**Files created:** `identity.tf` (new — keep it separate from `oidc.tf`, which is
school-tenant only; the file boundary makes the tenant boundary obvious in review).

**Resources — all with `provider = azuread.identity`:**
| Resource | Name | Purpose |
|---|---|---|
| `azuread_application` | `sentinel-backend-api` | `identifier_uris = ["api://sentinel-backend"]`, `app_role` **Incident.Write** (stable GUID `11111111-…`) |
| `azuread_service_principal` | ↑ | the resource half of the role assignment |
| `azuread_application` | `sentinel-gha-client` | the caller |
| `azuread_service_principal` | ↑ | the principal half |
| `azuread_application_federated_identity_credential` | `sentinel-main` | `repo:Keshav0375/Sentinel:ref:refs/heads/main` |
| `azuread_app_role_assignment` | `gha_incident_write` | grants the caller the role |

**Also:** aliased provider block, `identity_tenant_id` root variable, `azuread ~> 3.0` added
to `versions.tf` (deliberately absent in phases 1–2), `AZURE_IDENTITY_TENANT_ID` GitHub
variable.

> ### ⛔ The trap — read before writing a line
> **`principal_object_id` must be `azuread_service_principal.sentinel_gha_client.object_id`,
> NOT the `sentinel-gha` UAMI.** The UAMI is a service principal in the *school* tenant.
> App-role assignment is a within-tenant directory operation and has **no cross-tenant
> form**. Referencing the UAMI here fails at apply with a misleading "principal not found",
> and the instinct will be to debug permissions rather than tenancy.
>
> This is why the caller needs its own registration — and why it still involves no stored
> secret: it carries a GitHub-OIDC federated credential, the same trust source as the UAMI.

## Prerequisites
- [ ] ⛔ **B11** — personal Entra tenant exists; `sentinel-tf-identity` registered there with
      a federated credential for `repo:Keshav0375/Sentinel-infra` **and** the
      **Application Administrator** directory role. This is the second bootstrap seam,
      mirroring §4.3 — Terraform cannot grant itself permission to manage a directory.
- [ ] Infra Phase 1 signed off (`oidc.tf` exists, state remote).

## Acceptance Criteria
- [ ] Every resource in `identity.tf` carries `provider = azuread.identity`. No directory
      resource silently targets the school tenant.
- [ ] `az account get-access-token --resource api://sentinel-backend` (as `sentinel-gha-client`
      against the identity tenant) returns a token whose `roles` claim contains
      `Incident.Write`.
- [ ] The `aud` claim is `api://sentinel-backend` and `iss` is the **identity** tenant.
- [ ] `terraform plan` is clean after the bootstrap import.
- [ ] No client secret exists on either app registration.

## Tests
- **Validate:** `terraform validate`, `tflint`.
- **Integration:** decode the issued token (jwt.io or `python -c`) and assert `aud`, `iss`,
  and `roles`. That decode is the real test — it is exactly what backend 5.6 will check.
- **Quality gate:** `--repo infra`.

## How to Verify (phase gate)
1. `terraform apply` → both apps, both SPs, the federated credential and the role assignment.
2. From a workflow (or locally via the federated token), acquire a token for
   `api://sentinel-backend` and decode it → `roles: ["Incident.Write"]`.
3. Confirm in the **identity** tenant portal that neither app has a client secret.

## Report   ·   _filled on completion_
_not yet implemented_

## BLOCKED   ·   _only if halted_
_BLOCKED on **B11** — the personal Entra tenant and its Terraform identity must exist first.
No longer blocked on R4: that decision closed 2026-08-15._
