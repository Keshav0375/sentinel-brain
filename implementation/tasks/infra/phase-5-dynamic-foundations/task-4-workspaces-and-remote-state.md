# task-5.4 — Workspace model + cross-layer state wiring   ·   [infra / phase-5-dynamic-foundations]

| Field | Value |
|-------|-------|
| **Status** | `not-started` |
| **Repo** | `Sentinel-infra` |
| **Phase branch** | `dev/infra-phase-5-dynamic-foundations` |
| **Commit prefix** | `feat:` |
| **Arch refs** | infra.md §8 (rewritten) |
| **Depends on** | [[task-3-platform-layer]] |

## Spec
How the two layers find each other without sharing a state file.

**Workspaces.** `platform` for the shared layer; `<deployment>-<env>` for each deployment. The
azurerm backend maps a workspace to `env:/<workspace>/<key>` automatically, so one storage
account holds all of them with no `-backend-config` juggling per run.

```bash
terraform workspace select -or-create "${DEPLOYMENT}-${ENVIRONMENT}"
```

**Deployments read the platform, never write it:**

```hcl
data "terraform_remote_state" "platform" {
  backend = "azurerm"
  config = {
    resource_group_name  = "rg-sentinel-tfstate"
    storage_account_name = var.state_storage_account
    container_name       = "tfstate"
    key                  = "env:/platform/sentinel.tfstate"
    use_azuread_auth     = true
    use_oidc             = true
  }
}
```

A read-only data source is the right coupling: a deployment *needs* the cluster's OIDC issuer
and the ACR login server, and must be unable to change either. The alternative — passing them
as variables — means the same values typed in two places and drifting.

**Root layout.** One root, `var.layer` selecting `platform` or `deployment`, with modules
`count`-gated on it. Considered and rejected: two separate root directories. Two roots means two
provider blocks, two lock files and two `init` paths to keep in step, for one boolean's worth of
separation.

## Prerequisites
- [ ] 5.3 platform applied and its outputs published

## Acceptance Criteria
- [ ] `platform` and a scratch `t1-dev` workspace coexist; each plan sees only its own resources
- [ ] A deployment plan resolves the platform's OIDC issuer through the remote-state data source
- [ ] `terraform destroy` in a deployment workspace proposes **zero** platform resources — assert this explicitly, it is the whole point
- [ ] Selecting a non-existent workspace creates it rather than failing

## Tests
- **Integration:** create `t1-dev`, plan, confirm the platform is untouched, delete the workspace.
- **Quality gate:** `--repo infra`.

## How to Verify (phase gate)
1. `terraform workspace list` shows both.
2. In `t1-dev`, `terraform destroy` lists no `rg-sentinel-platform-cc` resource.

## Report   ·   _filled on completion_
_not yet implemented_
