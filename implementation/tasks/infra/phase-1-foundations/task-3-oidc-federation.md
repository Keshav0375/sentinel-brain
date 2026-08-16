# task-3 — OIDC federation (bootstrap + Terraform federated creds)   ·   [infra / phase-1-foundations]

| Field | Value |
|-------|-------|
| **Status** | `done-pending-review` |
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
  `azurerm_role_assignment` **Storage Blob Data Contributor** on `sentineltfstate0375` (C2 —
  the state account is outside the Contributor scope, and without this every CI
  `terraform init` fails); and one `azurerm_federated_identity_credential` per repo+trigger
  (§4.2): `Sentinel-infra` main+pr, `Sentinel` main+pr, `Sentinel-deployment` main.
- `scripts/bootstrap-oidc.sh` — one-time `az identity create` + both role assignments +
  the two `Sentinel-infra` federated credentials (§4.3), then prints all five
  `terraform import` commands. Must:
  - set **`MSYS_NO_PATHCONV=1`** so `--scope /subscriptions/...` survives Git Bash;
  - on **`az role assignment create`**, use `--assignee-object-id` +
    `--assignee-principal-type ServicePrincipal`, never bare `--assignee` — the latter
    does a Microsoft Graph lookup that fails without directory write rights. (Scoped to
    `create` deliberately: `az role assignment list --assignee` degrades to the literal
    GUID and is fine, which is what the idempotency probes use.)
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
user_assigned_identity_id = azurerm_user_assigned_identity.sentinel_gha.id
#          ^ NOT `parent_id` — renamed in azurerm v4, and `resource_group_name`
#            is unused on this resource. Both emit deprecation warnings.
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
- [x] **B1** — `sentinel-rg` exists in `canadacentral`. Closed 2026-08-15.
- [x] **B2** — task 1.2 state storage exists. Closed 2026-08-15.

## Acceptance Criteria
- [x] `oidc.tf` validates; subjects use `Keshav0375` + correct repo names/refs.
- [x] **No `azuread_*` resource anywhere.**
- [x] Bootstrap script is idempotent and creates identity + both role assignments + the two
      `Sentinel-infra` credentials.
- [x] All five imports succeed, and `terraform plan` afterwards shows **no destroy and no
      replace** — only the three remaining federated credentials planned to add.
- [x] After apply, `terraform plan` reports **"No changes."**

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

## Report   ·   _2026-08-15_

`oidc.tf` + `scripts/bootstrap-oidc.sh`, **executed end to end against the live
subscription**. rev-9 is no longer a hypothesis — a managed identity does substitute for an
app registration.

**Live state:** UAMI `sentinel-gha` (`clientId c9ed809b-eca3-4ecc-8678-5dbfb91be5ae`,
`canadacentral`) · Contributor on `sentinel-rg` · Storage Blob Data Contributor on
`sentineltfstate0375` · **all 5 federated credentials**, subjects verified with exact casing.

**Acceptance met:** 5 objects imported → `Plan: 3 to add, 2 to change, 0 to destroy` (no
destroy, no replace) → apply → **`No changes. Your infrastructure matches the
configuration.`** Gate `RESULT: PASS`.

### Four things reality taught us — all now encoded

1. **Resource-ID casing.** `az identity show --query id` returns `resourcegroups`
   (lowercase); the azurerm parser is case-sensitive and fails with *"the segment at position
   0 didn't match"* — an error pointing nowhere near the cause. The script now builds the ID
   by hand with `resourceGroups`.
2. **MSYS mangling hits `terraform`, not just `az`.** `/subscriptions/...` became
   `C:/Program Files/Git/subscriptions/...` and three imports failed. The scripts guarded
   themselves; the *printed import commands* did not. Now they warn.
3. **`skip_service_principal_aad_check` is create-only.** It planned as an in-place update
   and failed with `doesn't support update`. Removed — and the reasoning matters: these two
   assignments are always bootstrap-created and only imported, so the replication race it
   guards cannot occur here. Phase 2/3 assignments against fresh identities *do* need it.
4. **Two deprecations in azurerm v4.81:** `resource_group_name` is unused on federated
   credentials, and `parent_id` → `user_assigned_identity_id`. Fixed; clears 10 warnings per
   plan so real warnings stay visible.

**Also hardened:** both bootstrap scripts now assert the expected subscription ID. Sentinel
spans two tenants and `az` keeps one shared context in `~/.azure`, so an `az login` in any
other terminal silently repoints this one — which happened mid-task. The script refused
rather than creating `sentinel-gha` in the wrong tenant.

**Design note.** The five credentials are written explicitly rather than with `for_each`.
`for_each` is DRYer and tempting for five near-identical resources, but each is imported by
hand at the bootstrap seam, and `...gha["sentinel_infra_main"]` needs shell quoting that
breaks differently in bash and PowerShell. Optimising the one manual step for
hard-to-get-wrong beat optimising the source for brevity.

**Not run:** `shellcheck` (not installed) — `bash -n` only. `tfsec`/`yamllint` absent.
`tflint` reports 3 unused-declaration warnings, down from 5, all Postgres forward references
for phase 2.

## BLOCKED   ·   _only if halted_
_none — B1, B2 and B3 all closed 2026-08-15._
