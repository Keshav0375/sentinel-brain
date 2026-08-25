# infra phase 5 — Dynamic Foundations

**Status:** ✅ verified — owner approved and merged 2026-08-25 (`7849310`)
**Date:** 2026-08-25 · **Tasks:** 5.0–5.5 · **Gate:** ⬜ awaiting owner

The static single-estate model is gone. What replaces it is a shared platform plus deployments
that can be created and destroyed independently of it.

---

## What shipped

| # | What | Commit |
|---|------|--------|
| 5.0 | Destroy the phase-1-4 estate; re-bootstrap state | `a2ba959` |
| 5.1 | `modules/naming` + `azure/config/deployment-config.yaml` | `e164f1d` |
| 5.2 | Three CI identities — `gha-plan` / `gha-deploy` / `gha-ops` | `ac940aa` |
| 5.3 + 5.4 | Platform layer, workspace model, remote-state seam | `91a4ee6` |
| 5.5 | `BOOTSTRAP.md` rewrite; `infra.md` + `decisions.md` supersessions | `91a4ee6`, brain |

```
rg-sentinel-bootstrap    stsentineltfb7fa37 · gha-plan · gha-deploy · gha-ops
rg-sentinel-plat-cc      acrsentinelplat2fef · aks-sentinel-plat · psql-sentinel-plat-2fef
```

---

## The two properties this phase exists to establish

Both are **proven**, not asserted — which matters, because both are the kind of claim that is
easy to believe and expensive to be wrong about.

**1. A deployment cannot touch the platform.**

```
deployment workspace  →  plans 3 guards, ZERO Azure resources
plan -destroy         →  "No changes. No objects need to be destroyed."
                      →  and still READS acr / cluster / issuer via remote state
```

Two state files. Destroying a deployment cannot reach the shared cluster because its state
contains none of it. Not a convention anyone has to respect.

**2. The dangerous identity is unreachable from a pull request.**

`gha-deploy` federates only on `environment:*` subjects, and GitHub will not mint those for a
`pull_request` event — so it is unreachable *by construction*, with no rule to misconfigure.
Meanwhile `gha-plan`'s entire permission set, read off the role definitions, is `*/read` plus
two blob reads: **no write action anywhere in the subscription.**

That second part cost a design decision. `terraform plan` normally takes a state lock, which is
a blob *write*; granting it would have left the "read-only" identity able to corrupt state.
Plans run `-lock=false` instead. The trade is real and stated: an unlocked plan racing an apply
can produce a stale plan. Acceptable, since plans are advisory and applies are dispatch-only.

---

## Decisions

- **One cluster, a namespace per deployment.** Regional quota is 6 vCPU and an AKS node is 2 —
  cluster-per-deployment stops at three with no headroom. The isolation is not weaker for being
  logical: workload identity federates on `system:serviceaccount:<ns>:<sa>`, matched by Entra as
  an exact string with no wildcard.
- **`apply` is dispatch-only.** Dropping `ref:refs/heads/main` from every identity means no push
  can apply — deliberate, because a push cannot know *which* deployment it means.
- **`rg-sentinel-bootstrap` holds exactly what Terraform can never own.** Phases 1-4 put the CI
  identity in the *application* group, so the app could not be destroyed without taking CI down.
  Untenable once application groups come and go on demand.
- **Providers removed until they have a consumer** — `azuread`, `github`, `kv_admin_object_id`.
  tflint flagged all three, and this repo's own phase-1 note already said it: an unused provider
  is dead weight the lock file still pins.
- **`infra.md` got a banner and six section markers, not a rewrite.** Its Azure facts are still
  true and were expensive to learn — why the AKS SKU is ARM64, why ACR must be Standard rather
  than Basic, the Y1/F1 webspace conflict. Rewriting to describe the new model would have thrown
  away the reasoning.

---

## Bugs caught before they ran

| | |
|---|---|
| 🚨 | The spec's remote-state config used the **S3** workspace key layout (`env:/platform/…`). azurerm appends instead, as `<key>env:<workspace>` — it would have read a nonexistent blob and reported "no state found", which reads as though the platform were never applied. |
| 🚨 | `gha-deploy` had no blob role in the spec — every `terraform init` under it would have 403'd. The same control-plane-vs-data-plane trap `oidc.tf` already documented. |
| 🚨 | "AKS RBAC Cluster Admin" is a *data*-plane role, inert without Entra-integrated Kubernetes RBAC. The control-plane role is what returns the admin kubeconfig. |
| ⚠️ | The naming module's unmapped-location guard used a `null` fallback — which explodes inside string templates *before* the precondition can report it. The guard existed and could never fire. Caught by the test asserting it fires. |

A ten-item pre-build audit by `architecture-warden` found the first three, in specs written the
day before. That audit is the reason this phase applied on the first attempt.

---

## Azure behaviours that cost real time

All four are now written into the scripts rather than into someone's memory:

- **Git Bash rewrites `/subscriptions/…`** into a Windows path, so `--scope` arrives mangled and
  the API answers `MissingSubscription` — a message that says nothing about path conversion.
  Third occurrence of this class in the project.
- **`az` emits CRLF**; command substitution strips the newline but not the carriage return.
- **`--role-definition` needs the `@file` form** and cannot read a Git Bash `/tmp` path.
- **Assigning a custom role needs the full ARM id.** Neither the display name nor the bare GUID
  works — both fail with "Role doesn't exist" while the role is present, correctly scoped and
  listable, so the obvious next move confirms it exists and gets you no closer.

---

## A process failure worth recording

**Every "gate PASS (9 ran)" reported during this phase came from an unmerged branch.**
`Sentinel` had `fix/quality-gate-infra-python` checked out in its working tree, so the gate
included `shellcheck`, `py-unittest` and `ruff-infra`. On `main` the infra gate is **6** checks.
The numbers were true locally and overstated what a fresh checkout would verify.

Worse, the structural version: `shellcheck` named two files by hand, so replacing
`bootstrap-oidc.sh` with `bootstrap-identities.sh` left **250 lines that create the
subscription's trust root unlinted behind a green gate.** Third time this blindspot class has
appeared.

Fixed at the root — the gate now expands globs, so `scripts/*.sh` covers whatever exists.
infra is 11 checks, up from 8. Pushed to [Sentinel#18](https://github.com/Keshav0375/Sentinel/pull/18).

---

## What this unblocks

**Phase 6** — the deployment layer, namespaces, preflight, and the three workflows that make
create/destroy/pause one button press each.

## Still blocked

| | | |
|---|---|---|
| ⛔ | **[Sentinel#18](https://github.com/Keshav0375/Sentinel/pull/18) must merge** | until it does, `main`'s gate is 6 checks, not 11 |
| ⛔ | **Identity-tenant credentials** | `sentinel-tf-identity` needs `environment:plan\|production\|destroy`; interactive cross-tenant login, BOOTSTRAP step 4 |
| ⚠️ | **`gha-plan` cannot-apply is proven by inspection** | a failing apply needs running *as* it — a phase-6 CI test. Inspection is reported as inspection. |
| ⚠️ | **Infra CI workflows still describe the old model** | they will fail until phase 6 rewrites them |
| ⛔ | B4–B8 | secret values; the vault is a deployment-layer resource and does not exist yet |

---

## See it working

```powershell
git checkout dev/infra-phase-5-dynamic-foundations

python ../Sentinel/scripts/quality_gate.py --repo infra --path .    # expect 11 ran

terraform workspace select platform
terraform plan                                                      # expect: No changes

cd modules/naming; terraform test; cd ../..                         # expect: 9 passed

# the isolation property — the thing worth checking yourself
terraform workspace new demo1-dev
terraform plan -destroy -var layer=deployment -var deployment=demo1 -var environment=dev
#   expect: "No changes. No objects need to be destroyed."
terraform workspace select platform; terraform workspace delete demo1-dev

# idle the compute
az aks stop -g rg-sentinel-plat-cc -n aks-sentinel-plat
az postgres flexible-server stop -n psql-sentinel-plat-2fef -g rg-sentinel-plat-cc
```
