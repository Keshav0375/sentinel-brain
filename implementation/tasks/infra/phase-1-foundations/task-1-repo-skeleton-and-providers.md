# task-1 — Repo skeleton + provider/backend/vars config   ·   [infra / phase-1-foundations]

| Field | Value |
|-------|-------|
| **Status** | `verified` — owner sign-off 2026-08-15, PR #1 merged |
| **Repo** | `Sentinel-infra` |
| **Local path** | `../Sentinel-infra` |
| **Phase branch** | `dev/infra-phase-1-foundations` |
| **Commit prefix** | `feat:` |
| **Arch refs** | architecture/infra.md §2, §4.2, §8.1, §9 |
| **Depends on** | — |
| **Referenced by** | [[task-3-oidc-federation]], all phase-2/3/4 module tasks |

> ✅ **R3 RESOLVED 2026-08-15 → `canadacentral`.** `var.location` still carries **no
> default** — the value reaches CI through the `AZURE_LOCATION` GitHub variable (C5).
>
> ⚠ **rev-9 (2026-08-15):** no `azuread` provider, and **no
> `postgres_entra_admin_group_object_id`**. The `sentinel-db-admins` group was removed —
> Postgres Entra admins are now attached directly, so the variables are the admin's
> **object id + UPN**. See infra.md §3.2 / §4.2 and [[task-2-postgresql-module]].
>
> ⚠ **rev-5:** still **no `db_password`** — PostgreSQL is Entra-only
> (`password_auth_enabled=false`), so no password exists to pass in.

## Spec
Lay down the root Terraform layout that every module wires into. No resources yet beyond
the provider/backend plumbing.

**Files created:**
- `main.tf` — provider blocks (`azurerm` with `features {}` **and `subscription_id`**,
  `github` with `owner = var.github_owner`), `data "azurerm_client_config" "current"`, and
  `data "azurerm_resource_group" "sentinel"` — a **data source, not a resource** (C1: the RG
  is created by the bootstrap and deleted by `ci_destroy_infra`; Terraform reads it, never
  owns it). Module call stubs commented for phases 2–3.
- `versions.tf` — `required_version >= 1.9` and pinned `required_providers` (C9):
  `azurerm ~> 4.0`, `integrations/github ~> 6.0`. **No `azuread`** — rev-9 removed every
  directory object from phases 1–2.
- `variables.tf` — see the contract below.
- `outputs.tf` — empty scaffold with header comment (populated in task 4.4).
- `backend.tf` — `backend "azurerm"` per §8.1, **including `use_azuread_auth = true` and
  `use_oidc = true`** (C2 — without these CI cannot reach the state blob at all).
- `terraform.tfvars.example` — every non-secret var with placeholder values; real
  `terraform.tfvars` gitignored.
- `.gitignore` — **extend** the existing Python template, don't replace it: add
  `.terraform/`, `*.tfstate*`, `terraform.tfvars`, `*.tfplan` (`.env` is already there).

**Variable contract (binding — later phases inherit these names):**

| Name | Type | Default | Notes |
|------|------|---------|-------|
| `subscription_id` | string | — | wired into `provider "azurerm"`; mandatory under azurerm v4 (C4) |
| `location` | string | **none** | R3 = `canadacentral`, but **never defaulted in HCL** |
| `resource_group_name` | string | `sentinel-rg` | |
| `postgres_entra_admin_object_id` | string | — | rev-9 — replaces the group object id |
| `postgres_entra_admin_principal_name` | string | — | rev-9 — the admin's UPN |
| `github_owner` | string | `Keshav0375` | case-sensitive (R1) |
| `github_pat` | string, `sensitive = true` | — | |

**No `db_password`. No `postgres_entra_admin_group_object_id`. No `azuread` provider.**

## Prerequisites
- [x] `terraform` CLI installed — v1.15.8, 2026-08-15.
- [x] Repo cloned locally (present, bare — one `Initial commit`).
- [x] **Branch base** — `Sentinel-infra` has no release train; branch from `main`, PR to `main`.
- [x] **R3 RESOLVED** — `canadacentral`.

## Acceptance Criteria
- [x] `terraform fmt -check -recursive` clean.
- [x] `terraform init -backend=false && terraform validate` passes (offline validate; real
      init needs state — task 1.2 / B2).
- [x] `terraform.tfvars` and `.env` are gitignored; the Python template's entries survive.
- [x] Provider `github.owner` resolves to `Keshav0375`.
- [x] `azurerm_resource_group` appears **only** as a `data` block.
- [x] `backend.tf` carries `use_azuread_auth` + `use_oidc`.
- [x] Providers pinned; **no `azuread` provider declared**.
- [x] No `db_password`, no `postgres_entra_admin_group_object_id`; `location` has no default.

## Tests
- **Unit/validate:** `terraform fmt -check`, `terraform validate` (with `-backend=false`).
- **Quality gate:** `python ../Sentinel/scripts/quality_gate.py --repo infra --path <repo>`.
  Expect `tfsec` + `yamllint` SKIPPED (not installed) and `actionlint` to FAIL until
  **B15/C13** is fixed — the repo ships no `.github/workflows/` until task 4.3.

## How to Verify (phase gate)
1. `cd Sentinel-infra && terraform fmt -check -recursive` → clean.
2. `terraform init -backend=false && terraform validate` → "Success".
3. `grep -c azuread *.tf` → 0.

## Report   ·   _2026-08-15_

Six files on `dev/infra-phase-1-foundations`: `versions.tf`, `main.tf`, `backend.tf`,
`variables.tf`, `outputs.tf`, `terraform.tfvars.example`, plus a Terraform section appended
to the existing Python `.gitignore` (template preserved — `.env` was already at line 151).

**Gate:** `RESULT: PASS` — `tf-fmt` ✅ · `tf-init -backend=false` ✅ · `tf-validate` ✅ ·
`gitleaks` ✅. Skipped: `tfsec` + `yamllint` (not installed), `actionlint` (no
`.github/workflows/` until task 4.3 — this is the C13/B15 fix working as intended).

**⚠️ `tflint` reports 5 `terraform_unused_declarations` warnings** — `location`,
`postgres_entra_admin_object_id`, `postgres_entra_admin_principal_name`,
`data.azurerm_client_config.current`, `data.azurerm_resource_group.sentinel`. All five are
correct-but-premature: each is consumed by a module that lands in phase 2. tflint is an
*optional* check so the gate still passes, but it is **not** clean and is not being
presented as such. Deliberately **not** suppressed via `.tflint.hcl` — silencing a correct
rule to make a scaffold look finished would also hide genuinely dead code later. Expect
these to clear themselves in phase 2 task 2.2; if any survive phase 2, that is a real
finding.

**Design notes.** `sentinel-rg` is a `data` source, not a resource (C1) — Terraform owning
it would make `terraform destroy` delete the group that `ci_destroy_infra` then tries to
`az group delete`, and would collide with the bootstrap on first apply. `subscription_id`
is a variable wired into the provider rather than ambient `ARM_SUBSCRIPTION_ID`, so a
wrong subscription shows up in the plan instead of the environment. `github_owner` carries
a `validation` block pinning it to `Keshav0375` exactly, because Azure matches OIDC subject
claims case-sensitively and the failure mode is a silent auth error, not a diff.

## BLOCKED   ·   _only if halted_
_none — code is writable and gateable offline. Full `terraform init` with remote state is
BLOCKED on B2 until task 1.2 bootstraps state storage._
