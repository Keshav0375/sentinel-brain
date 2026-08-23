# task-3 — Key Vault module (+ RBAC roles, secrets)   ·   [infra / phase-2-core-modules]

| Field | Value |
|-------|-------|
| **Status** | `done-pending-review` |
| **Repo** | `Sentinel-infra` |
| **Phase branch** | `dev/infra-phase-2-core-modules` |
| **Commit prefix** | `feat:` |
| **Arch refs** | architecture/infra.md §3.3 |
| **Depends on** | [[task-2-postgresql-module]], [[task-3-oidc-federation]] (GHA SP object id) |
| **Referenced by** | [[task-1-aks-module]], [[task-2-ci-app-deployment]], [[task-3-composite-actions]] (get-kv-secrets), all runtime-secret consumers |

> ⚠ **rev-5 (2026-07-12):** secret inventory + RBAC changed. **No `db-password`** (Postgres is
> Entra-only) and **no `sentinel-api-token`** (Entra bearer). Add two more RBAC roles: backend
> UAMI = Secrets User, rotator Function MI = Secrets Officer. LLM keys get an expiry (rotation,
> task 3.6). No `db_password` input variable. See sentinel-infra §3.3.

## Spec
Central secret store, RBAC-authorized. Terraform writes, GHA SP + backend UAMI read, rotator writes.

**Files created:** `modules/keyvault/{main.tf,variables.tf,outputs.tf}`
- `azurerm_key_vault "sentinel"` — name `sentinel-kv-0375`, sku `standard`,
  **`rbac_authorization_enabled = true`** (NOT `enable_rbac_authorization` — deprecated in
  azurerm v4, removed in v5; verified against the pinned 4.81.0), tenant from a
  **module-local** `data "azurerm_client_config" "current"` (data sources do not inherit
  across module boundaries), plus `soft_delete_retention_days = 7` and
  `purge_protection_enabled = false` (owner decision 2026-08-15 — Azure's 90-day +
  purge-protection default would leave the vault name reserved after any `ci_destroy_infra`
  teardown, making the rebuild impossible under the same name).
- `azurerm_role_assignment "terraform_kv_admin"` — `Key Vault Secrets Officer` to `data.azurerm_client_config.current.object_id`.
- `azurerm_role_assignment "gha_kv_reader"` — `Key Vault Secrets User` to the GHA SP object id (task 1.3 output).
- `azurerm_role_assignment "backend_kv_reader"` — `Key Vault Secrets User` to the backend UAMI (task 3.1).
- `azurerm_role_assignment "rotator_kv_officer"` — `Key Vault Secrets Officer` to the rotator Function MI (task 3.6).
- Secret placeholders loaded post-apply via `az keyvault secret set` (§10). LLM keys seeded with a ~90d expiry (rotation, task 3.6).
- `variables.tf` — `resource_group_name`, `location`, `gha_principal_id`, `backend_uami_principal_id` (**no** `db_password`).
- `outputs.tf` — `key_vault_id`, `key_vault_name`, `key_vault_uri`.

**Secrets (§3.3, 7):** anthropic-api-key ↻, openai-api-key ↻, dd-api-key, dd-app-key,
teams-webhook-url, langfuse-secret-key, langfuse-public-key, acr-password, github-pat.
**Removed:** ~~db-password~~ (Entra DB auth), ~~sentinel-api-token~~ (Entra bearer).

## Prerequisites
- [ ] task 1.3 GHA SP object id available. [ ] task 3.1 backend UAMI principal id, task 3.6 rotator MI
  (both land in phase 3 — wire their role assignments then, or pass `null` and add in 3.1/3.6).
- [ ] ⛔ B1 to apply; ⛔ B4–B9 to populate runtime secrets.

## Acceptance Criteria
- [ ] Validates; RBAC (not access policies); **four** role assignments — Secrets Officer for the
      TF SP and the rotator Function MI, Secrets User for the GHA SP and the backend UAMI.
- [ ] **No `db-password` and no `sentinel-api-token`** anywhere in the module (Entra-only DB auth,
      Entra bearer API auth). Terraform writes **no secret values** — the 9 runtime secrets are
      documented for `az keyvault secret set` (§10 step 6).
- [ ] LLM keys (`anthropic-api-key`, `openai-api-key`) carry a ~90d expiry for task 3.6 rotation.
- [ ] Outputs expose vault id/name/uri.

## Tests
- **Validate:** validate, tflint, tfsec, gitleaks (ensure no literal secret values committed).
- **Integration (⛔ B1):** apply; GHA SP can `az keyvault secret show anthropic-api-key`; TF SP can
  set; GHA SP cannot set; `az keyvault secret list` contains **no** `db-password`/`sentinel-api-token`.
- **Quality gate:** `--repo infra`.

## How to Verify (phase gate)
1. `terraform plan -target=module.keyvault` → vault + 4 role assignments, **no secret resources**.
2. (post-apply) `az keyvault secret list --vault-name sentinel-kv-0375`; confirm GHA SP read-only via `az role assignment list`.

## Report   ·   _2026-08-16_

`modules/keyvault/{main,variables,outputs}.tf` + root wiring. Applied live:
`sentinel-kv-0375` · standard · **RBAC** (`rbac_authorization_enabled`, not the deprecated
spelling) · 7-day soft delete · purge protection off. **Zero secret resources in state** —
verified, not asserted. Live write→read→delete→**purge** test through the RBAC path passed;
the purge is the same mechanism the teardown depends on.

**Review changed this task materially:**
- `terraform_kv_admin` → `kv_admin` bound to an explicit `kv_admin_object_id` instead of
  `client_config.current.object_id`, which resolves to the **CI identity** when CI applies —
  the first CI apply would have destroyed the human's Officer rights. Renamed via a `moved`
  block so no window exists with no Officer on the vault.
- The count-on-null deferral was replaced by **bool toggles** (`enable_backend_reader`,
  `enable_rotator_officer`) — `count` on a value unknown at plan time errors, and phase 3
  passes exactly such a value. Cross-variable validation fails with a message naming the
  real cause if a toggle is set without its principal id.
- `tenant_id` is a pinned root variable, not ambient `client_config` — an `az login` to the
  identity tenant elsewhere would have repointed the vault's directory.
- **R6:** CI cannot purge the soft-deleted vault (subscription-scope action; the CI identity
  holds nothing there). Teardown is now an Owner-run local procedure; `ci_destroy_infra.yml`
  is removed from the design.

**Honest gaps:** `tfsec` absent and `tflint` has no azurerm plugin, so **zero Azure-specific
static analysis ran** — the gate's PASS covered fmt/validate/naming only. First real exercise
of R5's RBAC Administrator grant happens when CI applies (phase 4), not yet.

## BLOCKED
_Apply ⛔ B1. Populating runtime secret values ⛔ B4–B9. Code writable now._
