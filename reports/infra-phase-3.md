# infra Phase 3 — Compute & Networking Modules

**Date:** 2026-08-23 · **Branch:** `dev/infra-phase-3-compute-modules` ·
**PR:** [Sentinel-infra#3](https://github.com/Keshav0375/Sentinel-infra/pull/3)
**Status:** done-pending-review — awaiting owner sign-off

---

## What shipped — all applied live

| Task | Resource | State |
|------|----------|-------|
| 3.1 AKS | `sentinel-aks` · Free tier · OIDC + workload identity · 1× `B2pls_v2` **ARM64** | **stopped** when idle |
| 3.1 | `sentinel-backend-wi` UAMI + `sentinel-backend-fic` (K8s SA subject) | 2nd Postgres admin + KV reader |
| 3.2 Event Grid | `sentinel-events-0375` + validated subscription | Succeeded |
| 3.3 Bridge | `sentinel-bridge-0375` · Y1 · SystemAssigned · KV read | function registered |
| 3.4 App Service | `dummy-api-0375` on `sentinel-deploy-plan` F1 | Running |
| 3.5 Identity | `sentinel-backend-api` + `sentinel-gha-client` in the **personal tenant** | 6 directory objects |
| 3.6 Rotation | `sentinel-rotator-0375` + system topic on `SecretNearExpiry` only | registered |

Plus `sentinel-func-rg` (forced: Y1/F1 Linux plans cannot share an RG) and 14 stdlib-only
unit tests for the two handlers, now executed by the gate (`Sentinel` PR #18).

## The review earned its cost — headline finds

- **Datadog's `$TAGS` is a comma-joined string.** The naive `" ".join` iterated it
  per-character: every real deploy failure would have classified `runtime_error` and taken
  the wrong backend path. My tests had encoded my own assumption (list-shaped tags).
- **The flat `client_payload` passthrough could never work** — GitHub caps it at 10
  top-level properties. Now `{signal_type, correlation_id, event}`; backend 5.1 reads
  `client_payload.event.*` and the contract is planted in its task file.
- **`correlation_id` is the Event Grid event id** — stable across re-deliveries, so
  duplicates are dedupable; a fresh uuid4 per retry defeated its own purpose.
- **`zip_deploy_file` never redeploys on src change** (the provider diffs the path
  string). Content-hash app setting forces it — proven live by these fixes reaching the
  apps through the very mechanism.
- **Unresolved KV references are the literal `@Microsoft.KeyVault(...)` string**, not
  empty. The rotator's escalation path would have died on `unknown url type`.
- **A Teams hiccup after a successful mint re-minted up to 30×** (Event Grid re-delivery).
  Post-write notification is now best-effort.
- **R5-class repeat (warden):** the func-rg CI grant was Terraform-managed at a scope CI
  cannot administer; moved to the bootstrap — where my earlier edit had *silently missed
  its anchor*, which the code reviewer caught. Assertion added to my own process: verify
  script edits by grep, not by the patch tool's exit code.

## Constraints Azure taught us (all in the decision log)

1. Grant SKU `B2ats_v2` can't host an AKS system pool (1 GiB < 4 GB floor) — **the 750h
   grant is unusable for AKS**; allowed small SKUs here are ARM-only → `B2pls_v2`,
   ~$0.03/hr only while started → **backend images must build `linux/arm64`**.
2. System pools can't scale below 1 node → scale-to-zero is `az aks stop/start`.
3. Y1 + F1 Linux plans can't share a resource group → `sentinel-func-rg`.
4. New Entra tenants reject bare `api://name` URIs → audience is
   `api://<tenant>/sentinel-backend`, absorbed because `SENTINEL_API_AUDIENCE` was config.
5. Guest invitation ≠ access — redemption requires one interactive login (my scripted
   "token minted" check was a false positive, corrected in the log).

## Honest gaps

- **End-to-end dispatch and rotation cannot fire until B4–B9 seed the vault** — it is
  empty by design. Every piece of plumbing short of the secret values is proven.
- Both function apps hold unresolved KV references until seeding (guarded in code).
- **CI has never authenticated** — the OIDC round trip, R5's grant, and the identity-tenant
  provider auth are all first exercised by phase 4's workflows.
- `tfsec`/`yamllint` still absent; `ruff` optional-skipped locally.
- Local applies of `identity.tf` depend on the guest login; CI needs
  `-var identity_client_id -var identity_use_oidc=true` explicitly (ARM_* env otherwise
  leaks the wrong identity — documented, wired in phase 4).

## See it working

```powershell
cd ..\Sentinel-infra; git checkout dev/infra-phase-3-compute-modules; git pull
terraform plan                                            # No changes, 0 warnings
python -m unittest discover modules/functions/tests -v    # 14 OK
python ..\Sentinel\scripts\quality_gate.py --repo infra --path .   # PASS (8 ran)
az aks show -n sentinel-aks -g sentinel-rg --query powerState.code -o tsv       # Stopped
az functionapp function list -n sentinel-bridge-0375 -g sentinel-func-rg -o table
az eventgrid system-topic event-subscription list --system-topic-name sentinel-kv-0375-events -g sentinel-rg -o table
az ad app list --query "[].displayName" -o tsv   # after: az login --tenant eae0d3c6-... (identity tenant)
```
