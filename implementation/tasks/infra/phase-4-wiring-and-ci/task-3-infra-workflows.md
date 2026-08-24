# task-3 — Infra workflows (dry / apply / runners)   ·   [infra / phase-4-wiring-and-ci]

| Field | Value |
|-------|-------|
| **Status** | `not-started` |
| **Repo** | `Sentinel-infra` |
| **Phase branch** | `dev/infra-phase-4-wiring-and-ci` |
| **Commit prefix** | `feat:` |
| **Arch refs** | architecture/infra.md §6.3, §7.1, §7.2 · decisions.md 2026-08-24 (phase-4 decisions 1 + 3) |
| **Depends on** | [[task-3-oidc-federation]], [[task-2-ci-runner-image]] |
| **Referenced by** | ongoing infra apply |

> ⚠ **R6 (2026-08-16): THREE workflows.** `ci_destroy_infra.yml` is **removed** — full teardown
> is a local Owner-run procedure (§7.3). The CI identity holds nothing at subscription scope,
> and purging a soft-deleted Key Vault requires it; from CI the purge 403s silently and the next
> apply then fails on the reserved name. Chosen over granting CI a subscription-scope Key Vault
> role, which would let it manage any vault in the subscription.

## Spec
**Three** GHA workflows in `.github/workflows/`.

> ⚠ **Body rewritten 2026-08-24.** It previously described four workflows and a gate step —
> the R6 banner above said three while every other line said four. Two decisions settle it:
>
> - **decisions.md 2026-08-24 #1** — `quality_gate.py` lives in the `Sentinel` repo and these
>   workflows run in `Sentinel-infra`. Rather than check out a second repo, infra CI is
>   **terraform-only**. ⚠️ tflint / shellcheck / gitleaks therefore never run on a PR; the gate
>   is a local pre-commit discipline. Accepted knowingly — see the decision entry.
> - **decisions.md 2026-08-24 #3** — the dry run splits by credential need, because the
>   federated credentials cover only `main` and `pull_request`.

**Files created:**

- **`ci_infra_dry.yml`** — `[infra] terraform — validate and plan (dry run)`
  - `on:` `push: branches: ['**']`, `pull_request: branches: [main]`
  - `permissions:` `id-token: write`, `contents: read`, `pull-requests: write`
  - **`run-validate`** — *no Azure*: `fmt -check -recursive`, `init -backend=false`, `validate`.
    Runs on **every** push, `dev/*` included. `-backend=false` is what makes it credential-free.
  - **`run-plan`** — `needs: run-validate`, `if: pull_request || ref == refs/heads/main`.
    `azure/login@v2` → `init` → `plan`; posts the plan to the PR via `actions/github-script@v7`,
    truncated at 60000 chars.
- **`ci_infra.yml`** — `[infra] terraform — apply`; `on: push branches [main]`;
  `environment: production`; `permissions: id-token: write, contents: read`; job `run-apply`:
  `azure/login@v2` → `init` → `apply -auto-approve`.
- **`ci_runners.yml`** — `[infra] runners — build and push`; `on: push branches [main]
  paths ['ci-images/**']`; job `build-and-push`: `azure/login@v2` → `az acr login` →
  `docker build` → push `ci-runner:latest`. (Called `build-runners.yml` in three stale places
  in §3.1/§6.2/§10 — `ci_runners.yml` is correct, matching `ci_infra*`.)

**Shared contract for the Azure jobs:**
- `azure/login@v2` with `client-id: ${{ vars.AZURE_CLIENT_ID }}`,
  `tenant-id: ${{ vars.AZURE_TENANT_ID }}`, `subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}`
  — **variables, not secrets** (decision #2).
- **`env: ARM_*`** on every terraform step — `ARM_CLIENT_ID`, `ARM_TENANT_ID`,
  `ARM_SUBSCRIPTION_ID`, `ARM_USE_OIDC: true`. §8.1 claimed these "arrive from the workflow" but
  no workflow set them; `azure/login` authenticates the `az` CLI, **not** the azurerm provider
  or its backend. Without these, `init` has no credential path.
- Terraform inputs as `-var=` flags, never `TF_VAR_*` (C5): `github_pat` (from secret `GH_PAT`),
  `location`, `subscription_id`, `postgres_entra_admin_object_id`,
  `postgres_entra_admin_principal_name`, `kv_admin_object_id`, `identity_client_id`,
  `identity_use_oidc=true`. The last two are mandatory per §9 and were missing from §7.1/§7.2.
- **No `db_password`** anywhere — Entra-only Postgres.
- Job IDs `kebab-case`, job `name:` Title case, workflow `name:` `[repo] scope — description`.

## Prerequisites
- [x] task 1.3 OIDC + 5 federated credentials — B3 **closed**; B1 **closed**
- [x] task 4.2 runner image (`ci_runners.yml` builds it)
- [ ] `actionlint` available locally — if not, the gate reports it SKIPPED and that must be said

## Acceptance Criteria
- [ ] **Three** workflows; `ci_destroy_infra.yml` does **not** exist.
- [ ] `actionlint` clean on all three.
- [ ] Every Azure job declares `id-token: write`.
- [ ] `run-validate` runs `init -backend=false` and calls no Azure action — a `dev/*` push
      cannot fail on `azure/login`.
- [ ] `run-plan` is gated to `pull_request` + `push main` (the only federated subjects).
- [ ] Every terraform step sets the four `ARM_*` env vars.
- [ ] `identity_client_id` and `identity_use_oidc` are passed to plan and apply.
- [ ] `ci_infra.yml` uses `environment: production`.
- [ ] No `db_password` and no `quality_gate.py` reference in any workflow.

## Tests
- **Lint:** `actionlint .github/workflows/*.yml`; yamllint if present.
- **Local gate:** `--repo infra` — creating `.github/workflows/` makes the gate's `actionlint`
  check start running (it was SKIPPED as "no such path yet" through phases 1–3).
- **Integration:** deferred to the phase gate — the first real OIDC run.

## How to Verify (phase gate)
1. `actionlint` clean on all three; `ls .github/workflows` shows exactly three files.
2. Pushing the phase branch runs **`run-validate` only**, and it goes green — proving the
   credential-free split works.
3. On the PR, `run-plan` authenticates via OIDC and posts a plan comment. **This is the first
   time the identity plane has ever been exercised.**

## Report   ·   _filled on completion_
_not yet implemented_

## BLOCKED
_None. B1 and B3 closed 2026-08-15._
