# infra phase 4 — Cross-Repo Wiring & CI

**Status:** done-pending-review · PR [#4](https://github.com/Keshav0375/Sentinel-infra/pull/4) · branch `dev/infra-phase-4-wiring-and-ci`
**Date:** 2026-08-24 · **Tasks:** 4.1–4.4 · **Gate:** ⬜ awaiting owner

The last infra phase. Infrastructure stops being something applied from a laptop and becomes
something CI owns.

---

## What shipped

| # | What | Commit |
|---|------|--------|
| 4.2 | **CI runner image** — `ci-runner.Dockerfile` (python:3.12-slim + Azure CLI + ruff/pyright/pytest/asyncpg/alembic) and `build-push.sh`, the one-time push that breaks the ACR bootstrap circularity | `7019da8` |
| 4.3 | **Three workflows** — `ci_infra_dry.yml`, `ci_infra.yml`, `ci_runners.yml`. No destroy workflow (R6) | `58eff64` |
| 4.4 | **10 root outputs + README** | `cbbca98` |
| 4.1 | **Cross-repo distribution** — 3 secrets + 9 variables, deferred behind `enable_repo_config` until B9 | `5252a01` |
| fix | Five review blockers | `e0e3710` |
| docs | Identity-tenant credential gap found by the first live run | `510d727` |

---

## The one result that matters

**The identity plane works.** Three things had never executed once before today — the
GitHub→Azure OIDC round trip, R5's RBAC Administrator grant, and the remote state blob under a
CI identity. On the first pull-request run, Terraform refreshed **every resource in the estate**
and printed every output. Phases 1–3 were all applied locally as subscription Owner; that
proved nothing about whether CI could do it. Now it has.

The run still ends red, for a reason worth more than the green would have been — see below.

---

## Four decisions this phase settled

Both reviewers halted the build before a line was written: the task specs and `infra.md`
contradicted each other in **ten** places. Six were stale text. Four were real:

1. **`quality_gate.py` does not run in infra CI.** The gate lives in the `Sentinel` repo;
   these workflows run in `Sentinel-infra`. Chosen: terraform-only CI.
   ⚠️ **`tflint`, `shellcheck` and `gitleaks` now never run on an infra PR.** The gate is a
   pre-commit discipline enforced by a human. This is the only place in Sentinel where "green"
   is not machine-verified.
2. **Identity pointers are GitHub variables, not secrets.** Under OIDC there is no secret — a
   client id is a public identifier and the trust decision is the federated-credential subject.
   This paid off within an hour: the first failed run printed *which* values were missing
   instead of `***`.
3. **The dry run splits by credential need.** `run-validate` needs no Azure, no state and no
   variable values, so it runs on every push including `dev/*` branches that have no credential
   at all. `run-plan` is pull-request only.
4. **4.1 also pushes the identity-tenant pointers** — §4.5 needs a second login as
   `sentinel-gha-client` and that identity was reachable from nowhere.

---

## Five defects caught before they ran

| | Defect | Why it mattered |
|---|---|---|
| 🚨 | **`environment: production` rewrites the OIDC subject** to `repo:…:environment:production` | `sentinel-infra-main` matched every workflow *except* the one that writes to Azure. Every apply would have died at `azure/login`. Sixth federated credential added. |
| 🚨 | **The function zip hashed differently per platform** — `__pycache__` rode into the package, sources were CRLF on Windows, and `archive_file` recorded mode 0666 vs 0644 | Local apply and CI apply would each redeploy what the other had just deployed, forever, with a byte-identical tree and nothing to see in git |
| 🚨 | **Plan and apply raced the state lease** on every merge to main | Whichever lost failed on a lock error describing nothing |
| ⚠️ | `curl \| bash` for the Azure CLI: no `-f`, and dash has no `pipefail` | A 404 page piped to bash exits 0 — an image with no Azure CLI |
| ⚠️ | pyright's Node warm-up wrote to `/root/.cache`; Actions sets `HOME=/github/home` | Every CI job re-downloaded Node anyway |

The zip fix is worth keeping in mind: a `dynamic "source"` block was tried and **rejected**
because it writes entries with no Unix mode at all. `source_dir` + `output_file_mode = "0644"`
was the better answer — same determinism, correct modes, and it keeps the packaging shape that
has already deployed successfully.

---

## What the live run found that no reviewer could

**The two-tenant split doubles the federated-credential surface.** CI authenticates to two
tenants on every run — the school tenant as the `sentinel-gha` UAMI, and the identity tenant as
`sentinel-tf-identity`. A federated credential is scoped to one identity in one tenant, so every
workflow context needs a credential in **both**.

B11 created exactly one: `sentinel-tf-main`, for `ref:refs/heads/main`. The identity tenant
still needs `pull_request` and `environment:production`. Until then a PR plan dies at
`AADSTS700213` *after* the azurerm plan has fully succeeded — and the message names the subject
but not the tenant, so it reads as though the school credential is broken.

Written up as **BOOTSTRAP.md step 4b** with the exact commands. This is the cost of R4 that the
decision entry did not price in, and it is a fair price: the alternative was involving
university IT.

---

## What this unblocks

Infra is **complete**. `deployment` phase 1 is next, and it inherits a working CI identity, a
runner image, and a distribution mechanism for its own credentials.

---

## Still blocked

| | | |
|---|---|---|
| ⛔ | **Identity-tenant credentials** | 2 `az` commands, BOOTSTRAP step 4b. Blocks the PR plan going green. |
| ⛔ | **B9** — GitHub PAT (`repo` scope) | `github-repo-config.tf` ships disabled. The github provider authenticates at *configure* time, so a missing PAT fails the whole plan with a 401 rather than skipping one resource. BOOTSTRAP step 9. |
| ⛔ | **B4–B8** — secret values | The vault is empty by design. Does not block this phase. |
| ⚠️ | **The runner image was never built** | Docker Desktop was not running. `build-push.sh` is unexecuted; the Dockerfile is unverified. |
| ⚠️ | `Sentinel` PR #18 | Still unmerged — CI-side gate ≠ local gate |

---

## See it working

```powershell
git checkout dev/infra-phase-4-wiring-and-ci

# 1. The gate — the ONLY place tflint/shellcheck/gitleaks now run
python ../Sentinel/scripts/quality_gate.py --repo infra --path .

# 2. Plan. Start the DB first — a stopped server errors the plan.
az postgres flexible-server start -n sentinel-pg-0375 -g sentinel-rg
terraform plan
#    expect: 1 to add   (the environment federated credential)
#            2 to change (both function apps redeploy ONCE for the
#                         LF-normalized, bytecode-free, mode-normalized package)

# 3. The zip is deterministic. Run the tests, replan — the hashes must NOT move.
cd modules/functions/tests; python -m unittest discover -q .; cd ../../..
terraform plan

# 4. CI: run-validate is credential-free and already green on a dev/* branch
gh run list --branch dev/infra-phase-4-wiring-and-ci --limit 4

# 5. Close the identity-tenant gap (BOOTSTRAP step 4b), then rerun the PR check
#    -> az login --tenant eae0d3c6-...  + 2x az ad app federated-credential create
gh run rerun --failed <run-id>

# 6. Build the runner image (needs Docker Desktop running)
./ci-images/build-push.sh

az postgres flexible-server stop -n sentinel-pg-0375 -g sentinel-rg
az aks stop -g sentinel-rg -n sentinel-aks
```

**Gate:** `terraform plan` matching step 2, the gate PASS, and `run-validate` green on the
branch. Steps 5–6 can follow the merge if you would rather not switch tenants now.
