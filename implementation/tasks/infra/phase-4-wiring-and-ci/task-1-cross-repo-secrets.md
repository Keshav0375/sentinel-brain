# task-1 — Cross-repo secret + variable distribution (github provider)   ·   [infra / phase-4-wiring-and-ci]

| Field | Value |
|-------|-------|
| **Status** | `not-started` |
| **Repo** | `Sentinel-infra` |
| **Phase branch** | `dev/infra-phase-4-wiring-and-ci` |
| **Commit prefix** | `feat:` |
| **Arch refs** | architecture/infra.md §5 · decisions.md 2026-08-24 (phase-4 decisions 2 + 4) |
| **Depends on** | [[task-1-acr-module]], [[task-3-oidc-federation]], [[task-5-backend-entra-app]] |
| **Referenced by** | sentinel `ci_*` workflows, sentinel-deployment `ci_app_deployment` |

## Spec
After apply, push identity/ACR values to the `Sentinel` and `Sentinel-deployment` repos so that
no value is ever hand-set in the GitHub UI.

> ⚠ **Corrected 2026-08-24 (decisions.md).** Three things in the original spec were wrong: the
> client id was sourced from `azuread_application.sentinel_gha`, **which rev-9 deleted**; the
> identity pointers were pushed as *secrets*, which under OIDC masks public identifiers and
> makes `AADSTS700213` unreadable; and the identity-tenant caller that §4.5 needs was pushed
> nowhere. Nine resources became **twelve**, split across two resource types.

**Files created:** `github-repo-config.tf`

**Secrets (`github_actions_secret`) — real credentials only, 3:**

| Repo | Name | Value |
|------|------|-------|
| `Sentinel` | `ACR_USERNAME` | `module.acr.acr_admin_username` |
| `Sentinel` | `ACR_PASSWORD` | `module.acr.acr_admin_password` (sensitive) |
| `Sentinel` | `ACR_LOGIN_SERVER` | `module.acr.acr_login_server` — secret for symmetry with §6.4's `container:` block, which reads it beside the credential pair |

**Variables (`github_actions_variable`) — public identifiers, 9:**

| Repo | Name | Value |
|------|------|-------|
| `Sentinel` | `AZURE_CLIENT_ID` | `azurerm_user_assigned_identity.sentinel_gha.client_id` |
| `Sentinel` | `AZURE_TENANT_ID` | `var.tenant_id` (school) |
| `Sentinel` | `AZURE_SUBSCRIPTION_ID` | `var.subscription_id` |
| `Sentinel` | `AZURE_IDENTITY_TENANT_ID` | `var.identity_tenant_id` — for the 2nd `azure/login` (§4.5) |
| `Sentinel` | `AZURE_GHA_CLIENT_ID` | `azuread_application.sentinel_gha_client.client_id` |
| `Sentinel` | `SENTINEL_API_AUDIENCE` | `api://<identity-tenant-id>/sentinel-backend` — the live `identity.tf` form, **not** the bare `api://sentinel-backend` in §5.4 prose |
| `Sentinel-deployment` | `AZURE_CLIENT_ID` | as above |
| `Sentinel-deployment` | `AZURE_TENANT_ID` | as above |
| `Sentinel-deployment` | `AZURE_SUBSCRIPTION_ID` | as above |

**Contract:** `provider "github" { token = var.github_pat, owner = var.github_owner }` (task 1.1).
`repository` args use exact casing — `"Sentinel"`, `"Sentinel-deployment"` (R1/R2).
**No `DB_PASSWORD`** anywhere: Postgres is Entra-only.

## Prerequisites
- [x] task 2.1 ACR outputs · [x] task 3.5 `sentinel_gha_client` · [x] task 1.3 UAMI — B1 and B3 **closed** 2026-08-15
- [ ] ⛔ **B9** GitHub PAT (`repo` scope) — required to *apply*. HCL is writable now.

## Acceptance Criteria
- [ ] Validates; **3 secrets + 9 variables**; exact repo casing.
- [ ] Client id comes from the **UAMI**, not a non-existent `azuread_application.sentinel_gha`.
- [ ] `ACR_PASSWORD` is sensitive and no secret value appears in plan output.
- [ ] No `DB_PASSWORD` / `AZURE_CLIENT_SECRET` resource exists.

## Tests
- **Validate:** `terraform validate`, tflint, gitleaks — the **local** gate. Infra CI does not
  run these (decisions.md 2026-08-24 #1).
- **Integration (⛔ B9):** apply; `gh secret list -R Keshav0375/Sentinel` shows 3;
  `gh variable list -R Keshav0375/Sentinel` shows 6;
  `gh variable list -R Keshav0375/Sentinel-deployment` shows 3.
- **Quality gate:** `--repo infra`.

## How to Verify (phase gate)
1. `terraform plan` → 12 resources (3 `github_actions_secret`, 9 `github_actions_variable`), no values shown.
2. (post-apply, needs B9) `gh secret list` + `gh variable list` on both repos show the names above.

## Report   ·   _filled on completion_
_not yet implemented_

## BLOCKED
_Apply ⛔ **B9** only. B1 and B3 closed 2026-08-15. HCL writable now._
