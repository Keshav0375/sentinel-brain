# task-5.1 — Deployment config schema + naming module   ·   [infra / phase-5-dynamic-foundations]

| Field | Value |
|-------|-------|
| **Status** | `not-started` |
| **Repo** | `Sentinel-infra` |
| **Phase branch** | `dev/infra-phase-5-dynamic-foundations` |
| **Commit prefix** | `feat:` |
| **Arch refs** | infra.md §2 (rewritten), decisions.md 2026-08-24 |
| **Depends on** | [[task-0-destroy-old-estate]] |

## ⚠ RESOLVED 2026-08-25 — pre-build audit

**The Key Vault budget is `len(deployment) + len(environment) <= 15`, not `len(deployment) <= 8`
alone.** `kv-`(3) + `-`(1) + `-`(1) + `uid`(4) = 9 fixed characters against a 24-char cap. A
deployment of 8 holds only while the environment is <= 7. Implement the *sum* rule in
`validation`; the 8-char cap is a consequence, not the rule.

**Location needs an abbreviation map.** `rg-<d>-<env>-<loc>` uses `cc`, which implies a mapping
that does not exist. Add one to the naming module, with a fallback that fails loudly rather than
silently emitting a 13-character region name:

```hcl
locals {
  loc_abbrev = { canadacentral = "cc", canadaeast = "ce", eastus = "eus", westus2 = "wus2" }
  loc = lookup(local.loc_abbrev, var.location, null)   # null -> precondition failure
}
```

**The platform layer is `deployment = "sentinel"`, `environment = "plat"`** (12 chars, inside the
budget). `platform` as an environment is 16 with `sentinel` and breaks the rule the same module
enforces.

**Per-deployment API identity (owner decision, 2026-08-25).** Each deployment gets its own
backend API app registration, so a token minted for one deployment is rejected by another's
backend on audience mismatch — the API layer isolates the same way the namespaces do. Extend the
naming table:

| Resource | Pattern | Constraint |
|---|---|---|
| backend API app | `sentinel-backend-<d>-<env>` | display name, tenant-unique |
| API identifier URI | `api://<identity-tenant-id>/sentinel-backend-<d>-<env>` | **must be tenant-qualified** — new tenants reject the bare form (`InvalidUniqueTenantIdentifierAsPerAppPolicy`) |
| GHA client app | `sentinel-gha-client-<d>-<env>` | its federated subject must be per-deployment too, or A's client mints B's token |

The apps themselves are built in phase 6; 5.1 only owns the names, because 5.2 writes federated
credentials that must agree with them.

**`aks_dns_prefix` was missing from the table** — `aks-<d>-<env>`, 1-54 chars, alnum + `-`,
no `--`.

## Spec
Two pieces of machinery every later task depends on.

**`azure/config/deployment-config.yaml`** — one file, all deployments, read natively by Terraform:

```hcl
locals {
  all = yamldecode(file("${path.root}/azure/config/deployment-config.yaml"))
  cfg = merge(local.all.defaults, try(local.all.deployments[var.deployment], {}))
}
```

```yaml
defaults:
  location: canadacentral
  components: [keyvault, database, functions, app_service, event_grid, namespace]
  database: { mode: shared }
  namespace: { cpu_limit: "1", memory_limit: 2Gi }

deployments:
  demo1: {}                                  # pure defaults
  perf:
    database: { mode: dedicated, sku: B_Standard_B2s }
```

**A deployment absent from `deployments:` uses `defaults:` entirely.** That is what makes
`deployment: demo1` + `apply` a complete instruction with no file edit — the file is for
exceptions, not enrolment.

**`modules/naming`** — takes `deployment`, `environment`, `location`; returns every resource
name. Azure CAF prefixes, plus `uid = substr(sha1("${subscription}-${deployment}-${env}"), 0, 4)`
for global uniqueness — deterministic, so it is stable across applies and never needs typing.

| Resource | Pattern | Constraint that shapes it |
|---|---|---|
| resource group | `rg-<d>-<env>-<loc>` | 90 chars, permissive |
| AKS | `aks-<d>-<env>` | unique per RG only — no uid needed |
| ACR | `acr<d><env><uid>` | **alphanumeric only**, no hyphens, global |
| Postgres | `psql-<d>-<env>-<uid>` | lowercase, global |
| Key Vault | `kv-<d>-<env>-<uid>` | **24 chars max**, global, soft-delete reservation |
| Storage | `st<d><env><uid>` | 24 chars, lowercase alnum, global |
| Function App | `func-<d>-<env>-<uid>` | global (azurewebsites.net) |
| App Service | `app-<d>-<env>-<uid>` | global |
| Event Grid | `evgt-<d>-<env>` | unique per region |

**`deployment` is capped at 8 characters**, and that cap is derived, not arbitrary: Key Vault's
24-char limit minus `kv-` (3) minus `-<env>` (≤5) minus `-<uid>` (5) leaves 11, and 8 keeps
headroom for a longer `environment` later. A `validation` block enforces it with that reasoning
in the error message, because a truncation bug here surfaces as a name collision three modules
away.

## Prerequisites
- [ ] 5.0 complete — no old-scheme resources to collide with

## Acceptance Criteria
- [ ] `yamldecode` reads the config; an absent deployment falls back to `defaults` cleanly
- [ ] Every generated name satisfies its Azure charset and length rule, verified for an 8-char deployment
- [ ] `deployment` longer than 8 chars fails `terraform validate` with an explanatory message
- [ ] `uid` is stable across two consecutive plans and differs between environments
- [ ] No `0375` string anywhere in the repo

## Tests
- **Unit:** `terraform console` over the naming module for `deployment=abcdefgh, env=prod` — assert each length/charset.
- **Negative:** a 9-char deployment fails validate.
- **Quality gate:** `--repo infra`.

## How to Verify (phase gate)
1. `terraform console` → `module.naming.names` prints the full set.
2. Change `environment` and confirm every `uid`-bearing name changes.

## Report   ·   _filled on completion_
_not yet implemented_
