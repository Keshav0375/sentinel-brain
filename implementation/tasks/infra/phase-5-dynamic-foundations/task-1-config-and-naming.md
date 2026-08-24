# task-5.1 — Deployment config schema + naming module   ·   [infra / phase-5-dynamic-foundations]

| Field | Value |
|-------|-------|
| **Status** | `not-started` |
| **Repo** | `Sentinel-infra` |
| **Phase branch** | `dev/infra-phase-5-dynamic-foundations` |
| **Commit prefix** | `feat:` |
| **Arch refs** | infra.md §2 (rewritten), decisions.md 2026-08-24 |
| **Depends on** | [[task-0-destroy-old-estate]] |

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
