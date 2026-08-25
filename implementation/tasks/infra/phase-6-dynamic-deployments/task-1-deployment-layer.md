# task-6.1 — Per-deployment layer   ·   [infra / phase-6-dynamic-deployments]

| Field | Value |
|-------|-------|
| **Status** | `not-started` |
| **Repo** | `Sentinel-infra` |
| **Phase branch** | `dev/infra-phase-6-dynamic-deployments` |
| **Commit prefix** | `feat:` |
| **Arch refs** | infra.md §3 (rewritten) |
| **Depends on** | [[task-4-workspaces-and-remote-state]] |


> ⚠️ **Read [RESOLUTIONS.md](RESOLUTIONS.md) first.** These specs predate phase 5. Ten
> conflicts were resolved before the build; that file overrides this one where they differ.

## Spec
Everything a single deployment owns, in its own resource group and workspace.

```
rg-<d>-<env>-cc
  kv-<d>-<env>-<uid>       Key Vault, RBAC mode, empty by design
  func-<d>-<env>-<uid>     Function App — bridge + rotator
  st<d><env><uid>          Functions storage
  app-<d>-<env>-<uid>      App Service F1 (the target app)
  evgt-<d>-<env>           Event Grid topic + subscriptions
  uami-<d>-<env>-backend   workload identity for this deployment's namespace
```

Modules are the phase-2/3 ones, re-parameterised on the naming module instead of hardcoded
names. The Y1/F1 webspace conflict is structural and survives: Consumption and Dedicated Linux
plans cannot share a resource group, so each deployment needs its own functions RG
(`rg-<d>-<env>-func-cc`) — the same constraint that produced `sentinel-func-rg`, now derived
rather than special-cased.

## Acceptance Criteria
- [ ] Two deployments coexist with no name collision and no shared resource
- [ ] Destroying one leaves the other and the platform untouched
- [ ] Key Vault is created empty — Terraform never writes a runtime secret
- [ ] Every name comes from `module.naming`; no literal resource name in any module

## Tests
- **Integration:** apply `t1-dev` and `t2-dev`, assert disjoint resource sets, destroy `t1`, confirm `t2` healthy.
- **Quality gate:** `--repo infra`.

## Report   ·   _filled on completion_
_not yet implemented_
