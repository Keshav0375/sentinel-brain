# task-2 — Remote state bootstrap (script + doc)   ·   [infra / phase-1-foundations]

| Field | Value |
|-------|-------|
| **Status** | `not-started` |
| **Repo** | `Sentinel-infra` |
| **Local path** | `../Sentinel-infra` |
| **Phase branch** | `dev/infra-phase-1-foundations` |
| **Commit prefix** | `feat:` |
| **Arch refs** | architecture/infra.md §8.1, §8.2, §10 (bootstrap) |
| **Depends on** | [[task-1-repo-skeleton-and-providers]] |
| **Referenced by** | [[task-3-oidc-federation]], [[task-4-root-wiring-and-apply]] |

## Spec
Terraform's `azurerm` backend needs a state RG + storage account + container that exist
*before* the first `init`. This is a one-time manual bootstrap — scripted + documented,
not applied by Terraform (chicken-and-egg).

**Files created:**
- `scripts/bootstrap-state.sh` — idempotent, guards on existence, `MSYS_NO_PATHCONV=1`:
  - `az group create --name sentinel-state-rg --location canadacentral`
  - `az storage account create --name sentineltfstate -g sentinel-state-rg --sku Standard_LRS --encryption-services blob`
  - `az storage container create --name tfstate --account-name sentineltfstate --auth-mode login`
  - **grant the operator `Storage Blob Data Contributor` on the account** — see the
    control-plane/data-plane note below.
- `docs/BOOTSTRAP.md` (or README section) — the ordered one-time setup (§10 steps 1–2),
  the blob-lease locking note (§8.2), and how `backend.tf` maps to these names.

**Contract:** names must match `backend.tf` from task 1: `sentinel-state-rg`,
`sentineltfstate`, `tfstate`, key `sentinel.terraform.tfstate`, region `canadacentral`.

> **⚠ Control plane ≠ data plane.** `backend.tf` sets `use_azuread_auth = true` (C2), so
> `terraform init` reaches the state blob with an **Entra token**, not a storage access key.
> Being **Owner** on the subscription does *not* grant blob data access — Owner is a
> control-plane role. Without an explicit data-plane grant, `init` fails with a 403 that
> reads like a bug. Both principals need it:
> - **you**, for local runs — `az role assignment create --assignee-object-id $(az ad signed-in-user show --query id -o tsv) --assignee-principal-type User --role "Storage Blob Data Contributor" --scope <storage-account-id>`
> - **the `sentinel-gha` UAMI**, for CI — granted by task 1.3's `gha_state_blob` resource.

> **Why a separate resource group.** State lives in `sentinel-state-rg`, not `sentinel-rg`,
> so that `ci_destroy_infra`'s `terraform destroy` + `az group delete` (§7.3) cannot delete
> the state that describes what it is destroying. Blast-radius isolation at the trust root.

## Prerequisites
- [x] `az` CLI installed (2.89.1).
- [ ] ⛔ **B1** — Azure subscription + `az login`.
- [ ] Storage account name globally unique. **If `sentineltfstate` is taken, stop** — it must
      change in `backend.tf`, this script, `docs/BOOTSTRAP.md`, infra.md §8.1 and task 1.3's
      `gha_state_blob` scope together, in one commit.

## Acceptance Criteria
- [ ] `bootstrap-state.sh` runs clean and is re-runnable (idempotent).
- [ ] `terraform init` (real, with backend) succeeds against the created container.
- [ ] The operator holds `Storage Blob Data Contributor` on the account.
- [ ] BOOTSTRAP.md lists exact commands in order, region `canadacentral`.

## Tests
- **Script:** `bash -n scripts/bootstrap-state.sh` (syntax) + shellcheck.
- **Integration (blocked on B1):** run the script, then `terraform init` resolves the backend.
- **Quality gate:** `--repo infra`.

## How to Verify (phase gate)
1. Run `scripts/bootstrap-state.sh` → state RG + storage + container exist
   (`az storage container list --account-name sentineltfstate --auth-mode login`).
2. Re-run it → no errors, nothing duplicated.
3. `terraform init` → "Successfully configured the backend".

## Report   ·   _filled on completion_
_not yet implemented_

## BLOCKED   ·   _only if halted_
_Verification BLOCKED on B1 (Azure subscription). Script + docs are writable now._
