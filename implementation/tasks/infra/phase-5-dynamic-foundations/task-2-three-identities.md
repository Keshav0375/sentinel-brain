# task-5.2 — Three CI identities + GitHub environments   ·   [infra / phase-5-dynamic-foundations]

| Field | Value |
|-------|-------|
| **Status** | `not-started` |
| **Repo** | `Sentinel-infra` |
| **Phase branch** | `dev/infra-phase-5-dynamic-foundations` |
| **Commit prefix** | `feat:` |
| **Arch refs** | infra.md §4 (rewritten), decisions.md 2026-08-24 (supersedes R5, R6) |
| **Depends on** | [[task-0-destroy-old-estate]] |

## Spec
Dynamic deployments create their own resource groups, and destroy must purge Key Vaults. Neither
is possible with rights scoped to one resource group, so the CI identity gains **subscription
scope** — which supersedes R5's scoping and R6's refusal to let CI tear down.

R5's *intent* survives: the dangerous rights must be unreachable from a pull request. That is
achieved by splitting the identity, not by narrowing the scope.

| Identity | Rights | Federated subjects | Reachable from a PR? |
|---|---|---|---|
| `gha-plan` | **Reader** (subscription) + Storage Blob Data Contributor (state) | `:pull_request`, `:environment:plan` | yes — and it can change nothing |
| `gha-deploy` | **Contributor** + **RBAC Administrator** + Key Vault purge + **AKS RBAC Cluster Admin** (subscription) | `:environment:production`, `:environment:destroy` | **no** |
| `gha-ops` | custom role: `*/start/action`, `*/stop/action`, `*/read` only | `:environment:ops` | **no** |

**Why the environment subject is the mechanism, not a policy.** A job declaring `environment: X`
receives the OIDC subject `repo:<owner>/<repo>:environment:X` instead of the branch form. GitHub
will not mint that token for a `pull_request` event. So `gha-deploy` is unreachable from a PR
**by construction** — there is no rule to misconfigure. This is the same behaviour that failed
the first phase-4 apply, used deliberately.

**`gha-ops` gets a custom role rather than Contributor** because pause/resume is the operation
run most often and should carry the least privilege. Contributor can delete; a start/stop role
cannot. Cheap to define while the bootstrap script is being written anyway.

**Files:** `scripts/bootstrap-identities.sh` (creates all three + the custom role definition +
federated credentials, idempotent), `identity.tf` extended with matching FICs on
`sentinel-tf-identity` for `environment:plan|production|destroy|ops`.

**GitHub environments:** `plan`, `production`, `destroy`, `ops`. `destroy` should carry a
required reviewer; the others need not.

## Prerequisites
- [ ] 5.0 complete · [ ] Owner in the school tenant · [ ] identity-tenant login available for the FIC step

## Acceptance Criteria
- [ ] Three UAMIs exist; `gha-plan` has **no** write action anywhere (verified by a failing test apply)
- [ ] Custom role JSON contains only read + start/stop actions and no `Microsoft.Authorization/*`
- [ ] Every environment subject has a matching FIC in **both** tenants (the phase-4 lesson: the two-tenant split doubles the credential surface)
- [ ] `bootstrap-identities.sh` is idempotent — second run is a no-op
- [ ] Imported into state; `terraform plan` → no changes

## Tests
- **Negative, and it is the important one:** run a plan as `gha-plan` and confirm apply is refused.
- **Integration:** each environment authenticates from a dispatched workflow.
- **Quality gate:** `--repo infra`.

## How to Verify (phase gate)
1. `az identity list -g <platform-rg> -o table` → three.
2. `az role definition list --custom-role-only true` → the start/stop role.
3. A dispatched job on `environment: plan` authenticates; the same job cannot apply.

## Report   ·   _filled on completion_
_not yet implemented_
