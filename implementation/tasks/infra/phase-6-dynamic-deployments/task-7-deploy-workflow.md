# task-6.7 — Rebuild `Sentinel Infra — Deploy` (apply / destroy)   ·   [infra / phase-6-dynamic-deployments]

| Field | Value |
|-------|-------|
| **Status** | `not-started` |
| **Repo** | `Sentinel-infra` |
| **Phase branch** | `dev/infra-phase-6-dynamic-deployments` |
| **Commit prefix** | `ci:` |
| **Arch refs** | infra.md §7.2 (rewritten), decisions.md (supersedes R6) |
| **Depends on** | [[task-6-validate-plan-workflow]] |

## Spec
Rewrite `ci_infra.yml`. One workflow, both directions.

```
deployment    (required)  demo1
action        plan-only | apply | destroy | refresh-only
environment   dev | prod
confirm       ______      required for destroy — must equal `deployment`
components / database_mode / location / target
```

`environment: production` for apply, **`environment: destroy` for destroy** — distinct subjects,
so a required reviewer can be attached to destruction alone.

**Destroy safeguards, and why each exists:**
- typed confirmation matching the deployment name — the difference between an irreversible action and a mis-click
- `workflow_dispatch` only; no push path can ever destroy
- **purge the Key Vault after destroy.** Without it the name is reserved 7 days and the next create fails on a vault nobody can see. This is the whole reason `gha-deploy` holds purge rights, and the destroy→recreate cycle is the phase's headline test.
- refuse to destroy the `platform` workspace from this workflow — the shared layer is not a deployment

**Acceptance test for the phase:** destroy `demo1`, recreate `demo1`, and get an identical
estate. That single cycle exercises naming determinism, purge, workspace handling and namespace
teardown at once.

## Acceptance Criteria
- [ ] `deployment: demo1` + `apply` produces a complete deployment with no other input
- [ ] destroy without a matching `confirm` refuses before authenticating
- [ ] destroy purges the vault; an immediate recreate succeeds
- [ ] `platform` cannot be destroyed here
- [ ] `actionlint` clean

## Report   ·   _filled on completion_
_not yet implemented_
