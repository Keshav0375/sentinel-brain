# task-2 — PostgreSQL module (+ pgvector, firewall)   ·   [infra / phase-2-core-modules]

| Field | Value |
|-------|-------|
| **Status** | `not-started` |
| **Repo** | `Sentinel-infra` |
| **Phase branch** | `dev/infra-phase-2-core-modules` |
| **Commit prefix** | `feat:` |
| **Arch refs** | architecture/infra.md §3.2 |
| **Depends on** | [[task-1-repo-skeleton-and-providers]] |
| **Referenced by** | [[task-3-keyvault-module]] (host/name outputs — **no** db-password), [[task-3-alembic-initial-schema]] (backend), [[task-2-ci-app-deployment]] (record-deployment, Entra DB token) |

> ⚠ **rev-9 (2026-08-15) — this task was rewritten.** The `sentinel-db-admins` **group is
> gone**; creating a group is a directory write the `uwindsor.ca` tenant denies. §3.2 now
> declares **two** administrator resources with direct principals, and there is no
> `postgres_entra_admin_group_object_id` variable anywhere. **B10 is closed as superseded.**
>
> ⚠ **rev-5:** **Entra-ONLY auth** — `password_auth_enabled = false`, no
> `administrator_password`, no `db_password` variable. Clients present a short-lived Entra
> token as the password; Entra DB roles are created post-apply via
> `pgaadauth_create_principal` (§10 step 8 — *not* Terraform's job). "Network reach ≠ auth":
> the allow-all firewall is acceptable because a valid token is still required.

## Spec
Flexible Server B1MS + `sentinel` DB + pgvector + **Entra-only auth** + dev allow-all firewall.

**Files created:** `modules/postgresql/{main.tf,variables.tf,outputs.tf}`

- `azurerm_postgresql_flexible_server "sentinel"` — name `sentinel-pg-0375`, version `16`,
  sku `B_Standard_B1ms`, storage `32768`, zone `"1"`,
  `authentication { active_directory_auth_enabled = true, password_auth_enabled = false }`
  (**no admin login/password**).
- **Two** `azurerm_postgresql_flexible_server_active_directory_administrator` resources, both
  with `tenant_id = data.azurerm_client_config.current.tenant_id` and `depends_on` the server:
  | Name | `object_id` | `principal_name` | `principal_type` |
  |------|-------------|------------------|------------------|
  | `human` | `var.postgres_entra_admin_object_id` | `var.postgres_entra_admin_principal_name` | `User` |
  | `backend_uami` | `var.backend_uami_principal_id` | `sentinel-backend-wi` | `ServicePrincipal` |
- `azurerm_postgresql_flexible_server_database "sentinel"` — charset UTF8, collation en_US.utf8.
- `azurerm_postgresql_flexible_server_configuration "pgvector"` — `azure.extensions = VECTOR`.
- `azurerm_postgresql_flexible_server_firewall_rule "allow_all_dev"` — 0.0.0.0–255.255.255.255,
  comment citing the §3.2 comparison table.
- **`data "azurerm_client_config" "current" {}` inside the module.** Data sources do **not**
  inherit across module boundaries; §3.2 is written as root-flat HCL and needs translating.
- `variables.tf` — `resource_group_name`, `location`, `postgres_entra_admin_object_id`,
  `postgres_entra_admin_principal_name`, `backend_uami_principal_id`.
  **No `db_password`. No `postgres_entra_admin_group_object_id`.**
- `outputs.tf` — `db_host`, `db_name`, `db_port`. **No password output — none exists.**

> ### Deferred second admin (owner decision 2026-08-15)
> `var.backend_uami_principal_id` has **no source until phase 3 task 3.1**, which creates the
> backend UAMI in the AKS module. Handle it with a nullable variable and a count guard:
> ```hcl
> variable "backend_uami_principal_id" { type = string, default = null }
> resource "..._active_directory_administrator" "backend_uami" {
>   count = var.backend_uami_principal_id == null ? 0 : 1
>   ...
> }
> ```
> Phase 3.1 then supplies the real value and the admin appears — a one-line diff. This is the
> **same pattern task 2.3 already prescribes** for its backend-UAMI and rotator role
> assignments, so both tasks defer identically rather than inventing two styles for one
> problem.

## Prerequisites
- [x] terraform CLI (1.15.8).
- [x] **B1** closed 2026-08-15 — apply is possible.
- [x] **B10** closed as superseded — no group to create.
- [x] Admin principal known: `245bb98a-95a4-4f9d-930a-fcf3122dcea1` / `arri@uwindsor.ca`.

## Acceptance Criteria
- [ ] Validates + fmt clean; `azure.extensions=VECTOR` present so the backend can
      `CREATE EXTENSION vector`.
- [ ] **Two** administrator resources, the second guarded by `count` on a null variable.
- [ ] No `db_password`, no `administrator_login`, no `postgres_entra_admin_group_object_id`.
- [ ] Firewall rule documented as dev-only (comment cites the §3.2 comparison table).
- [ ] Outputs expose host/name/port and nothing else.
- [ ] Consuming `postgres_entra_admin_*` clears 2 of the 3 `tflint`
      `terraform_unused_declarations` warnings carried over from phase 1.

## Tests
- **Validate:** `terraform validate`, `tflint`, `tfsec` (**not installed → will report
  SKIPPED; say so at the gate**). Allow-all firewall is an accepted dev risk — annotate the
  suppression, never silence it.
- **Integration:** apply, then `psql "host=sentinel-pg-0375.postgres.database.azure.com ... sslmode=require"`
  with an Entra token as the password; `SELECT * FROM pg_available_extensions WHERE name='vector'`.
- **Quality gate:** `--repo infra`.

## How to Verify (phase gate)
1. `terraform plan -target=module.postgresql` → server + **1** admin (the second is
   count-guarded to 0) + db + config + firewall.
2. Post-apply: acquire a token
   (`az account get-access-token --resource https://ossrdbms-aad.database.windows.net`) and
   connect with `psql`; `SELECT * FROM pg_available_extensions WHERE name='vector';` returns a row.

## Report   ·   _filled on completion_
_not yet implemented_

## BLOCKED   ·   _only if halted_
_none — B1 and B10 both closed 2026-08-15. The `backend_uami` admin is deferred by design to
task 3.1, not blocked._
