# Phase 6 — pre-build resolutions (2026-08-25)

The eight task specs were written 2026-08-24, **before** phase 5 was built. Phase 5 then moved
the repo under them. `architecture-warden` and `phase-context-builder` found nine conflicts and
three warnings; this file is the binding answer to each, and **overrides the task files where
they differ**.

---

## 1. The kubernetes provider authenticates via Entra RBAC — owner decision

The specs had 6.2 authenticate "from the AKS admin credential in the platform remote state".
No such output exists, and `gha-plan` (Reader) cannot call `listClusterUserCredential` at all —
the same constraint that already forced `-refresh=false` on the PR plan.

**Chosen: enable Entra-integrated Kubernetes RBAC on the platform cluster.**

```hcl
azure_active_directory_role_based_access_control {
  azure_rbac_enabled = true
}
```

This is what makes fetching a kubeconfig *safe*. Without `azure_rbac_enabled`, a kubeconfig from
`listClusterUserCredential` is effectively cluster-wide access — handing it to the identity a
pull request can trigger would be the same mistake as granting `listCredentials`. **With** it,
the kubeconfig carries an exec plugin that mints an Entra token for the *calling* identity, and
that identity's cluster rights are governed by Azure RBAC:

| Identity | Control plane | Data plane |
|---|---|---|
| `gha-plan` | `Azure Kubernetes Service Cluster User Role` | `Azure Kubernetes Service RBAC Reader` |
| `gha-deploy` | already holds `Cluster Admin Role` | `Azure Kubernetes Service RBAC Cluster Admin` |

Both need the **Cluster User Role** to fetch the kubeconfig; what differs is what the token can
then *do*. Provider config uses `exec` with `kubelogin`, so the workflows add
`azure/use-kubelogin@v1`.

**This modifies the platform cluster**, so phase 6 begins with a platform re-apply. Noted as
future hardening, deliberately not done now: `local_account_disabled = true` would remove the
admin bypass entirely, but locks out recovery if the Entra path breaks.

---

## 2. Per-deployment app registrations belong to 6.1

`modules/naming` already emits `api_app_name`, `gha_client_name` and `api_identifier_uri`, and
`main.tf` says the aliased `azuread` provider "returns in phase 6" — but no task owned it.
**Folded into 6.1.** It re-adds `azuread ~> 3.0` to `versions.tf` and the aliased provider.

Binding from §4.4, carried forward: app role `Incident.Write`, `allowed_member_types = ["Application"]`,
identifier URI **tenant-qualified** (`api://<identity-tenant>/sentinel-backend-<d>-<env>`) —
new Entra tenants reject the bare form.

Per-deployment is the point: a token minted for one deployment fails **audience** validation at
another's backend, so the API isolates the same way the namespaces do.

---

## 3. The vault ships empty; seeding is documented, not automated

§3.5 has the bridge read `GITHUB_TOKEN` as `@Microsoft.KeyVault(...;SecretName=github-pat)`, so
a fresh deployment's bridge resolves that reference to nothing.

**Not automated, and that is deliberate.** A secret written by Terraform is a secret in state —
readable by anything with state access and present in every plan. Phase 3 already built the
guard: the rotator detects an unresolved `@Microsoft.KeyVault(...)` literal and logs rather than
crashing, and there is a unit test for it.

So: `BOOTSTRAP.md` gains a per-deployment seeding step, and the deployment's outputs include the
exact `az keyvault secret set` commands. **A deployment without seeded secrets is a valid,
expected state** — the bridge simply cannot dispatch until they exist.

---

## 4. Preflight only runs what Reader can actually run

Name availability (`checkNameAvailability` on Key Vault, Storage, ACR, Web, Postgres) is a POST
`*/action`. Reader has none of them, so those checks **cannot** run in the PR preflight.

Split by identity rather than weakening one:

| Runs under `gha-plan` (PR preflight) | Runs under `gha-deploy` (pre-apply) |
|---|---|
| both tenants mint a token | global name availability |
| resource providers registered | soft-deleted vault holding a name |
| regional vCPU quota | |
| AKS SKU exists + permitted | |
| Postgres state (report only — it cannot start it) | |

The apply-side checks are the ones that must not fail *mid-apply*; the PR-side ones are the ones
worth knowing before review. Neither identity is widened to satisfy a checklist.

---

## 5. `modules/postgresql` must be parameterised

It hardcodes database `sentinel`, `sku_name`, `storage_mb`, and admin `principal_name =
"sentinel-backend-wi"`. 6.3 adds `database_name`, `sku`, `storage_mb` and drops the hardcoded
backend admin — the per-deployment identity is granted by the deployment layer, not by the
platform module.

`azure/config/deployment-config.yaml` already carries `database.{mode,sku,storage_mb}`; they are
currently unread.

---

## 6. Two environments in one workflow → an expression

`environment: ${{ inputs.action == 'destroy' && 'destroy' || 'production' }}` on a single job.
Split jobs were considered and rejected — it duplicates every step so the two paths can drift,
and the whole point is that destroy is the *same* code path with a different credential.

## 7. `layer` stays; `target` gets defined

6.6's proposed input list dropped `layer`, which phase 5 made a required root variable **and**
the workspace selector. It stays. `target` is a single resource address for `-target` — a
documented escape hatch, manual only, never on a push.

## 8. Postgres discovery iterates

Phase 5's guard is `az postgres flexible-server list --query "[0].name"` — the first server
only. With `database.mode: dedicated` there can be several. Both the start-guard and pause/resume
iterate.

## 9. The identity is named from `module.naming`

6.1 wrote `uami-<d>-<env>-backend`; naming emits `id-<d>-<env>-backend`. Naming wins — no
literal resource name in any module is the rule.

## 10. Capture the vault name before destroying it

6.7 purges the vault after `terraform destroy`, but the name lives in the state being destroyed.
Read `terraform output` **before** the destroy step and carry it in an env var.

---

## Also noted

- **`ResourceQuota` with `requests.*`/`limits.*` rejects any pod that omits requests.** Add a
  `LimitRange` with defaults, or the first backend deployment fails admission with a message
  about quota rather than about its own manifest.
- **`infra.md` has no §7.4** — 6.8's Arch ref does not exist. Pause/resume is constrained only
  by its task spec and the decisions entry, and 5.5's supersession banner is where it gets
  written down.
- **GitHub environments `destroy` and `ops` do not exist yet.** Code can be written; running it
  needs the owner to create them, with a required reviewer on `destroy`.
