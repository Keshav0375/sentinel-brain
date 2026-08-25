# task-5.2 — Three CI identities + GitHub environments   ·   [infra / phase-5-dynamic-foundations]

| Field | Value |
|-------|-------|
| **Status** | `not-started` |
| **Repo** | `Sentinel-infra` |
| **Phase branch** | `dev/infra-phase-5-dynamic-foundations` |
| **Commit prefix** | `feat:` |
| **Arch refs** | infra.md §4 (rewritten), decisions.md 2026-08-24 (supersedes R5, R6) |
| **Depends on** | [[task-0-destroy-old-estate]] |

## ⚠ RESOLVED 2026-08-25 — pre-build audit

Six gaps, all mechanism rather than intent. Binding answers:

**1. State access.** `gha-plan` **and** `gha-deploy` both need `Storage Blob Data Contributor` on
the state account. The spec gave it only to `gha-plan`, which would 403 every `terraform init`
under `gha-deploy` — the exact control-plane-vs-data-plane trap `oidc.tf` already documents.
`gha-ops` needs **none**: pause/resume is pure `az` and never touches Terraform state.

**2. AKS access is the CONTROL-plane role.** "AKS RBAC Cluster Admin" is a *data*-plane role and
is inert unless the cluster enables Entra-integrated Kubernetes RBAC, which §3.7's cluster does
not. Use **`Azure Kubernetes Service Cluster Admin Role`**, which returns the admin kubeconfig
via `az aks get-credentials --admin` and works against local accounts. Noted as future
hardening: enabling AAD-integrated RBAC would remove the static admin kubeconfig entirely.

**3. `gha-ops` custom role — explicit actions, not wildcards.** `*/start/action` grants start on
every provider in the subscription, which is not least privilege:

```
Microsoft.Resources/subscriptions/resourceGroups/read
Microsoft.ContainerService/managedClusters/read
Microsoft.ContainerService/managedClusters/start/action
Microsoft.ContainerService/managedClusters/stop/action
Microsoft.DBforPostgreSQL/flexibleServers/read
Microsoft.DBforPostgreSQL/flexibleServers/start/action
Microsoft.DBforPostgreSQL/flexibleServers/stop/action
Microsoft.Web/sites/read
Microsoft.Web/sites/start/action
Microsoft.Web/sites/stop/action
```

Name `Sentinel Ops Start Stop`; `assignableScopes` = the subscription. **`NotActions` empty and
no `*` anywhere** — that is the property the acceptance test checks.

**4. Key Vault purge is already in subscription Contributor.** `Microsoft.KeyVault/locations/deletedVaults/purge/action`
is not in Contributor's `NotActions`, so the separate grant the spec listed is redundant — drop
it. (`Key Vault Contributor` *does* NotAction it, which is where the confusion came from.)
⚠️ This must be **proven, not assumed**: the acceptance test purges a real vault as `gha-deploy`.
The whole destroy->recreate cycle depends on it.

**5. Federated subjects — the set is now closed.**

| Identity | Subjects |
|---|---|
| `gha-plan` | `repo:Keshav0375/Sentinel-infra:pull_request`, `:environment:plan` |
| `gha-deploy` | `:environment:production`, `:environment:destroy` |
| `gha-ops` | `:environment:ops` |

**`ref:refs/heads/main` is deliberately absent, and that changes behaviour: `apply` becomes
dispatch-only.** Push-to-main auto-apply cannot survive multi-deployment — it has no way to know
*which* deployment to apply. Every apply is now an explicit button press.

The old `Sentinel:*` and `Sentinel-deployment:*` subjects are **dropped**. Nothing uses them yet
(neither category has started), and re-adding them later scoped to those repos' actual needs is
better than carrying three unused credentials on a subscription-scoped identity.

**6. Identity-tenant FICs.** `sentinel-tf-identity` needs `:environment:plan|production|destroy`
— **not** `ops`, because pause/resume never runs Terraform and so never touches the `azuread`
provider.

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
