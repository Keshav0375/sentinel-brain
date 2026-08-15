# task-3 — OIDC federation (bootstrap + Terraform federated creds)   ·   [infra / phase-1-foundations]

| Field | Value |
|-------|-------|
| **Status** | `not-started` |
| **Repo** | `Sentinel-infra` |
| **Local path** | `../Sentinel-infra` |
| **Phase branch** | `dev/infra-phase-1-foundations` |
| **Commit prefix** | `feat:` |
| **Arch refs** | architecture/infra.md §4.2, §4.3, §4.3.1, §9 |
| **Depends on** | [[task-1-repo-skeleton-and-providers]], [[task-2-remote-state-bootstrap]] |
| **Referenced by** | [[task-1-cross-repo-secrets]], every workflow that does `azure/login` |

> ⚠ **rev-9 (2026-08-15) — this task was rewritten.** The CI identity is a **User-Assigned
> Managed Identity**, *not* an app registration. The subscription sits in the **uwindsor.ca**
> tenant where we hold Owner on the subscription but **no directory rights**, so
> `azuread_application` cannot be created. A UAMI is a plain Azure resource under RBAC and
> carries federated credentials identically; `azure/login@v2` cannot tell them apart.
> See architecture/decisions.md → "rev-9 — identity plane rebuilt on managed identities".

## Spec
Passwordless GitHub→Azure auth. **One UAMI** with federated credentials for all three repos,
no stored client secret. Bootstrap the identity + the two `Sentinel-infra` credentials by
hand, import all five objects into Terraform, then TF manages the rest.

**Files created:**
- `oidc.tf` — `azurerm_user_assigned_identity "sentinel_gha"`; `azurerm_role_assignment`
  **Contributor** on the RG (via `data.azurerm_resource_group.sentinel`, C1);
  `azurerm_role_assignment` **Storage Blob Data Contributor** on `sentineltfstate` (C2 —
  the state account is outside the Contributor scope, and without this every CI
  `terraform init` fails); and one `azurerm_federated_identity_credential` per repo+trigger
  (§4.2): `Sentinel-infra` main+pr, `Sentinel` main+pr, `Sentinel-deployment` main.
- `scripts/bootstrap-oidc.sh` — one-time `az identity create` + both role assignments +
  the two `Sentinel-infra` federated credentials (§4.3), then prints all five
  `terraform import` commands. Must:
  - set **`MSYS_NO_PATHCONV=1`** so `--scope /subscriptions/...` survives Git Bash;
  - use **`--assignee-object-id` + `--assignee-principal-type ServicePrincipal`**, never
    bare `--assignee` — the latter does a Microsoft Graph lookup that fails without
    directory read rights;
  - be re-runnable (idempotent).
- `docs/BOOTSTRAP.md` / README: the import step + the GitHub **variables** and the one
  `GH_PAT` **secret** (§9 — note the classification, C7).

**⚠ R1 — use real subjects:** `repo:Keshav0375/Sentinel-infra:ref:refs/heads/main`,
`repo:Keshav0375/Sentinel:...`, `repo:Keshav0375/Sentinel-deployment:ref:refs/heads/main`.
Azure matches these case-sensitively; older arch text showed `keshxvDev` — do NOT copy it.

**Contract:**
```
issuer   = https://token.actions.githubusercontent.com
audience = ["api://AzureADTokenExchange"]        # azurerm arg is `audience`, singular
subject  = repo:Keshav0375/<Repo>:<ref:refs/heads/main|pull_request>
parent_id = azurerm_user_assigned_identity.sentinel_gha.id
```

**The import set (C3 — all five, or the first apply collides):**
```
azurerm_user_assigned_identity.sentinel_gha
azurerm_federated_identity_credential.sentinel_infra_main
azurerm_federated_identity_credential.sentinel_infra_pr
azurerm_role_assignment.gha_contributor
azurerm_role_assignment.gha_state_blob
```

## Prerequisites
- [x] `az` CLI installed (2.89.1). **No directory/app-registration rights needed** — rev-9.
- [x] Repo names on GitHub confirmed (R2).
- [ ] ⛔ **B1** — `sentinel-rg` exists in `canadacentral`.
- [ ] ⛔ **B2** — task 1.2 state storage exists (so TF can manage the imported objects, and
      so the `gha_state_blob` scope resolves).

## Acceptance Criteria
- [ ] `oidc.tf` validates; subjects use `Keshav0375` + correct repo names/refs.
- [ ] **No `azuread_*` resource anywhere.**
- [ ] Bootstrap script is idempotent and creates identity + both role assignments + the two
      `Sentinel-infra` credentials.
- [ ] All five imports succeed, and `terraform plan` afterwards shows **no destroy and no
      replace** — only the three remaining federated credentials planned to add.

## Tests
- **Validate:** `terraform validate`, `tflint`.
- **Integration (blocked on B1/B2):** run the bootstrap → import → `plan` is clean.
- **Quality gate:** `--repo infra`.

## How to Verify (phase gate)
1. `bash scripts/bootstrap-oidc.sh` (or PowerShell equivalent) → identity, 2 role
   assignments, 2 federated credentials created. Re-run it → no errors, no duplicates.
2. Run the five `terraform import` commands it printed, then `terraform plan` → **no
   destroy, no replace**; 3 credentials to add.
3. `az identity federated-credential list --identity-name sentinel-gha -g sentinel-rg` →
   the two bootstrap subjects, exact casing.

> **Deferred to task 4.3, deliberately:** end-to-end proof that a GitHub workflow actually
> exchanges its token (`azure/login@v2`) needs a workflow to exist, and `Sentinel-infra`
> ships none until task 4.3. Adding a throwaway workflow here would be scope creep into that
> task. Phase 1 verifies the **Azure half** of the trust relationship; Phase 4 closes the loop.

## Report   ·   _filled on completion_
_not yet implemented_

## BLOCKED   ·   _only if halted_
_Verification BLOCKED on B1 + B2 (resource group + state storage). Code writable now.
No longer blocked on directory rights — that was the point of rev-9._
