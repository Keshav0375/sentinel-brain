# infra Phase 1 — Foundations & Bootstrap

**Date:** 2026-08-15 · **Branch:** `dev/infra-phase-1-foundations` ·
**PR:** [Sentinel-infra#1](https://github.com/Keshav0375/Sentinel-infra/pull/1) → `main`
**Status:** done-pending-review — awaiting owner sign-off

---

## What shipped

| Task | Deliverable |
|------|-------------|
| **1.1** Repo skeleton | `versions.tf` · `main.tf` · `backend.tf` · `variables.tf` · `outputs.tf` · `terraform.tfvars.example` · `.gitignore` · `.gitattributes` |
| **1.2** State bootstrap | `scripts/bootstrap-state.sh` · `docs/BOOTSTRAP.md` |
| **1.3** OIDC federation | `oidc.tf` · `scripts/bootstrap-oidc.sh` |

**Not just written — executed.** Every resource below exists in the live subscription, and
both bootstrap scripts were re-run to prove idempotency.

## What it does

Terraform can now run against Azure at all. That is the whole point of this phase, and it
required resolving two circular dependencies:

1. **State.** Terraform keeps state in an Azure Storage container it cannot create, because
   it needs somewhere to put state before it can run.
2. **Identity.** GitHub Actions authenticates via OIDC to run Terraform, but the identity
   that makes OIDC work cannot be created by that pipeline.

Both are broken the same way: a small, scripted, documented manual seam, then `terraform
import` so everything afterwards is codified.

**Live in Azure:** `sentinel-state-rg` / `sentineltfstate0375` / `tfstate` ·
`sentinel-gha` UAMI (`c9ed809b-eca3-4ecc-8678-5dbfb91be5ae`) · 4 role assignments ·
5 federated credentials.

## What it unblocks

Infra Phase 2 (ACR, PostgreSQL, Key Vault) can now be written *and applied*. Blockers
**B1, B2, B3, B10** are closed; **B15** is fixed.

## The decisions that shaped it

**The CI identity is a managed identity, not an app registration.** The subscription lives
in the `uwindsor.ca` tenant, where `allowedToCreateApps` is `false` at tenant policy —
proven via Graph, not assumed. This invalidated the entire rev-5 identity plane. A UAMI is
an ordinary Azure resource governed by RBAC and carries federated credentials identically;
`azure/login@v2` cannot tell them apart. **rev-9**, and it is now proven end to end.

**`sentinel-rg` is read, never owned.** Resources at the trust root — created before
Terraform can run — belong in `data` blocks. Owning it would make `terraform destroy` delete
the group that `ci_destroy_infra` then tries to `az group delete`.

**Control plane ≠ data plane.** Owner on the subscription grants *no* blob access. This is
the single most confusing thing in the phase and it is documented in four places on purpose.

**Explicit over DRY at the manual seam.** Five near-identical federated credentials are
written out rather than `for_each`-ed, because two are imported by hand and
`...gha["sentinel_infra_main"]` quotes differently in bash and PowerShell. Optimising the
one manual step for hard-to-get-wrong beat optimising the source for brevity.

## Reconciliations resolved

| # | Item | Resolution |
|---|------|-----------|
| **R3** | Azure region | `canadacentral`; quota verified (Basv2 limit 10, regional cap 6) |
| **R4** | Inbound Entra bearer auth has no home tenant | Two-tenant split — 2 app registrations in a personally-owned tenant, everything else stays. No stored secret. |
| **R5** | CI identity could not create role assignments | RBAC Administrator on `sentinel-rg` + Contributor on `sentinel-state-rg` |
| **C1–C9** | Nine architecture conflicts | All resolved *before* any code was written |
| **C12** | `sentineltfstate` globally taken | → `sentineltfstate0375`, 20 occurrences across 7 files |
| **C13** | `actionlint` gate defect blocking four phases | `Sentinel` PRs #15/#16, merged |

## What review caught

`architecture-warden`: **CONFORMS, 0 blockers.** But four warnings were architecture defects
*this phase created* — §3.7 carrying deprecations §4.2 had just dropped, §7 workflows reading
`secrets.AZURE_*` where §9 says variables, a stale §2 repo tree, and task-3's Contract
contradicting its own Report. Each would have detonated one to three phases later.

`code-reviewer`: **2 blockers.**
- **`Contributor` cannot create role assignments.** Phases 2–3 declare six of them; every CI
  apply would have failed. Phase 1 passed only because it ran locally as **Owner** — CI has
  never authenticated as this identity. Became R5.
- **`bootstrap-oidc.sh` could print empty `terraform import` ids** — jmespath `[0].id` over an
  empty array yields an empty string with exit 0, so `set -euo pipefail` never fired.

Installing `shellcheck` immediately found **CRLF line endings**, which would have failed every
script on `ubuntu-latest` with `bad interpreter: ...bash^M`. Git had warned on every commit.
`Sentinel` PR #17 makes shellcheck a required gate check so those two files can never be
unlinted again.

## Honest gaps

- **`tflint` is not clean** — 3 `terraform_unused_declarations`, all Postgres forward
  references consumed in phase 2. Deliberately **not suppressed**: silencing a correct rule to
  make a scaffold look finished would hide real dead code later. If any survive phase 2, that
  is a genuine finding.
- **`tfsec`** (unavailable on winget) and **`yamllint`** are not installed → SKIPPED.
- **`actionlint` SKIPPED** — no workflows until task 4.3.
- **The identity has never authenticated from CI.** Phase 1 proves only the Azure half of the
  trust relationship. Task 4.3 closes the loop, and until it does, R5's fix is reasoned rather
  than observed.

## See it working

```bash
cd Sentinel-infra
terraform init && terraform plan     # → No changes. Your infrastructure matches...
bash scripts/bootstrap-state.sh      # → every step "already exists — skipping"
bash scripts/bootstrap-oidc.sh       # → every step "already exists — skipping"
python ../Sentinel/scripts/quality_gate.py --repo infra --path .   # → PASS (5 ran)
az identity federated-credential list --identity-name sentinel-gha -g sentinel-rg -o table
```
