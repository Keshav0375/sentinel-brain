# task-2 — Remote state bootstrap (script + doc)   ·   [infra / phase-1-foundations]

| Field | Value |
|-------|-------|
| **Status** | `verified` — owner sign-off 2026-08-15, PR #1 merged |
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
  - `az storage account create --name sentineltfstate0375 -g sentinel-state-rg --sku Standard_LRS --encryption-services blob`
  - `az storage container create --name tfstate --account-name sentineltfstate0375 --auth-mode login`
  - **grant the operator `Storage Blob Data Contributor` on the account** — see the
    control-plane/data-plane note below.
- `docs/BOOTSTRAP.md` (or README section) — the ordered one-time setup (§10 steps 1–2),
  the blob-lease locking note (§8.2), and how `backend.tf` maps to these names.

**Contract:** names must match `backend.tf` from task 1: `sentinel-state-rg`,
`sentineltfstate0375`, `tfstate`, key `sentinel.terraform.tfstate`, region `canadacentral`.

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
- [x] **B1** — Azure subscription + `az login`. Closed 2026-08-15.
- [x] Storage account name globally unique. **`sentineltfstate` WAS taken** — C12 materialized
      on the first run. Renamed to `sentineltfstate0375` across all 7 files in one commit.

## Acceptance Criteria
- [x] `bootstrap-state.sh` runs clean and is re-runnable (idempotent).
- [x] `terraform init` (real, with backend) succeeds against the created container.
- [x] The operator holds `Storage Blob Data Contributor` on the account.
- [x] BOOTSTRAP.md lists exact commands in order, region `canadacentral`.

## Tests
- **Script:** `bash -n scripts/bootstrap-state.sh` (syntax) + shellcheck.
- **Integration (blocked on B1):** run the script, then `terraform init` resolves the backend.
- **Quality gate:** `--repo infra`.

## How to Verify (phase gate)
1. Run `scripts/bootstrap-state.sh` → state RG + storage + container exist
   (`az storage container list --account-name sentineltfstate0375 --auth-mode login`).
2. Re-run it → no errors, nothing duplicated.
3. `terraform init` → "Successfully configured the backend".

## Report   ·   _2026-08-15_

`scripts/bootstrap-state.sh` + `docs/BOOTSTRAP.md`, both **executed against the live
subscription** — this task is verified for real, not just written.

**Created:** `sentinel-state-rg` · `sentineltfstate0375` (Standard_LRS, blob encryption,
TLS 1.2 min) · `tfstate` container · `Storage Blob Data Contributor` → `245bb98a-…` (User).

**Proof:**
- First run created everything cleanly.
- **Second run skipped all four steps** — idempotency is real, not asserted.
- **`terraform init` → "Successfully configured the backend \"azurerm\"!"** This one line is
  the actual acceptance test: it proves the storage account, container, `use_azuread_auth`
  path and the data-plane role assignment all work together. It is the first live
  confirmation that the **C2** fix was both necessary and sufficient.
- Gate `RESULT: PASS`. `terraform init -backend=false` still works against an
  already-initialised backend, so the gate is unaffected by local state.

**⚠️ C12 materialized.** `sentineltfstate` was already taken **by another Azure tenant** —
storage account names are globally unique across all of Azure, not per-tenant. The script's
`check-name` guard distinguished "taken by someone else" from "already yours" and printed
the exact remediation list, rather than failing with a generic "already exists". Renamed to
**`sentineltfstate0375`** across 7 files (20 occurrences) in a single pass, verified zero
bare `sentineltfstate` remained. This is the risk the architecture flagged and it cost
about two minutes because the guard existed.

**Design note — the container is created with `--auth-mode login`, not an access key.**
Creating it with a key would have worked and left the *actual* credential path untested
until the first `terraform init`. Doing it via Entra means the bootstrap exercises exactly
what Terraform will use. That is also why the script retries: RBAC is eventually consistent
and propagation runs 30–120s, so a single attempt would fail intermittently for reasons that
look nothing like the real cause.

**Not run:** `shellcheck` (not installed). `bash -n` syntax check passed. Worth installing
before task 1.3 ships a second, longer script.

## BLOCKED   ·   _only if halted_
_none — B1 and B2 both closed 2026-08-15._
