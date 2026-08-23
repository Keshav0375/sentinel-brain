# infra Phase 2 — Core Resource Modules

**Date:** 2026-08-23 · **Branch:** `dev/infra-phase-2-core-modules` · **PR:** [#2](https://github.com/Keshav0375/Sentinel-infra/pull/2) (merged `90bf6f6`)
**Status:** ✅ verified — owner ran the checklist and signed off 2026-08-23

---

## What shipped

| Task | Deliverable | Live in Azure |
|------|-------------|---------------|
| **2.1** ACR | `modules/acr/` | `sentinelacr0375.azurecr.io` · Standard · **$0** (free grant) |
| **2.2** PostgreSQL | `modules/postgresql/` | `sentinel-pg-0375` · PG 16 · B1MS · Entra-only · pgvector · **$0** (750 h/mo grant) |
| **2.3** Key Vault | `modules/keyvault/` | `sentinel-kv-0375` · RBAC · 7-day soft delete · **$0** |

All three applied and **verified live**, not just planned:
- Postgres: connected as `arri@uwindsor.ca` with an **Entra token as the password** — no
  password exists on the server at all.
- Key Vault: secret written, read, deleted and **purged** through the RBAC path.
- `terraform plan` → `No changes` · `tflint` **CLEAN** (first time — phase-1 warnings cleared
  by consumption, not suppression) · gate `PASS (6 ran)`.

## What it unblocks

Phase 3 (AKS + Event Grid + Functions + App Service + identity plane + rotation) has its
registry, database and secret store. Backend phases 1–2 have a real Postgres to migrate
against once infra completes.

## Decisions made in this phase

| # | Decision |
|---|----------|
| ACR SKU | **Standard, $0** — reversed my own Basic recommendation after reading the actual Students entitlement; the free grant is scoped to the Standard meter, so the cheaper SKU was the expensive choice |
| Naming | `0375` suffix systematically on all globally-unique names — 5 of them were already taken by other tenants |
| KV lifecycle | 7-day soft delete, purge protection off, explicit purge in teardown |
| **R6** | **Teardown is Owner-run and local; `ci_destroy_infra.yml` removed.** CI cannot purge a soft-deleted vault (subscription-scope action, CI holds nothing there) — reproduced, not theorized. Net: CI ends with *less* standing privilege |

## What review caught (both reviewers, findings reproduced live)

- **The deferral pattern the spec prescribed would have failed at plan in phase 3** —
  `count` on a value unknown at plan time errors. Replaced with bool toggles.
- **KV Officer bound to "whoever ran apply"** — the first CI apply would have destroyed the
  human's secret-seeding rights. Now an explicit `kv_admin_object_id`, migrated via `moved`.
- **`kv_admin_object_id` was required but supplied nowhere** — the documented CI invocation
  failed on it; phase looked green only via my gitignored tfvars. Wired through all 4 supply
  points.
- **Ambient `tenant_id`** — ForceNew on the Postgres admin; an `az login` to the identity
  tenant elsewhere would have proposed replacing it. Now pinned.

## Honest gaps

- **Zero Azure-specific static analysis ran.** `tfsec` is not installed and `tflint` has no
  azurerm ruleset — the green gate checked fmt/validate/naming, not one Azure security rule.
  The allow-all firewall and `admin_enabled` were reviewed by humans/agents only.
- ACR's admin password sits in plaintext **state** (inherent to `admin_enabled`; annotated,
  mitigated by rotation). The state blob's readers are the two blob-RBAC principals.
- The allow-all firewall argument covers login, **not availability** — 50 connection slots
  on B1ms are exhaustible pre-auth. Accepted for a demo stack.
- R5's RBAC grant and the whole OIDC path have still **never been exercised from CI** — that
  proof lands with phase 4's workflows.
- B4–B9 (the 9 secret *values*) remain open; the vault is empty by design until §10 step 7.

## See it working

```powershell
# db must be running for terraform (400 ServerStoppedError otherwise)
az postgres flexible-server start -n sentinel-pg-0375 -g sentinel-rg   # if stopped

cd Sentinel-infra; git checkout dev/infra-phase-2-core-modules; git pull
terraform plan     # → No changes. Your infrastructure matches the configuration.

az acr show -n sentinelacr0375 -g sentinel-rg --query sku.name -o tsv          # Standard
az postgres flexible-server show -n sentinel-pg-0375 -g sentinel-rg `
  --query "{aad:authConfig.activeDirectoryAuth, pwd:authConfig.passwordAuth}"  # Enabled / Disabled
az keyvault show -n sentinel-kv-0375 --query properties.enableRbacAuthorization # true
az keyvault secret list --vault-name sentinel-kv-0375 -o table                 # empty — by design
python ..\Sentinel\scripts\quality_gate.py --repo infra --path .               # PASS (6 ran)
```
