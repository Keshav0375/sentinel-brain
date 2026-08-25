# task-6.5 — Preflight job — what a plan structurally cannot check   ·   [infra / phase-6-dynamic-deployments]

| Field | Value |
|-------|-------|
| **Status** | `not-started` |
| **Repo** | `Sentinel-infra` |
| **Phase branch** | `dev/infra-phase-6-dynamic-deployments` |
| **Commit prefix** | `ci:` |
| **Arch refs** | infra.md §7 (rewritten) |
| **Depends on** | [[task-1-config-and-naming]] |


> ⚠️ **Read [RESOLUTIONS.md](RESOLUTIONS.md) first.** These specs predate phase 5. Ten
> conflicts were resolved before the build; that file overrides this one where they differ.

## Spec
`terraform plan` proves auth works, state is readable, config is valid, and what would change.
It **cannot** prove an apply will succeed. Every item below is a failure this project actually
hit, and none of them are visible to a plan:

| Check | The failure it prevents |
|---|---|
| both tenants mint a token | phase 4: the azuread client 401'd after the azurerm plan fully succeeded |
| global name availability (ACR, storage, KV, PG, app) | `sentineltfstate` was taken by another tenant |
| soft-deleted vault holding the name | destroy → recreate fails on a vault nobody can see |
| AKS SKU exists in region **and** is permitted | `B2ats_v2` failed the system-pool RAM floor; `B2s` was not in the allowed list |
| regional vCPU quota ≥ requested | the 6-vCPU ceiling |
| resource providers registered | ten had to be registered by hand |
| Postgres running | `400 ServerStoppedError` broke a run three times |

Runs as a job before validate, on `environment: plan` so it needs only the read-only identity.
Output is a table of pass/fail with the remedy beside each failure — a preflight that says "no"
without saying "run this" has moved the problem rather than solved it.

## Acceptance Criteria
- [ ] All seven checks implemented and independently failable
- [ ] Every failure prints the exact remediating command
- [ ] Runs entirely under `gha-plan` — no write action required
- [ ] Completes in under ~60s

## Tests
- **Negative:** force each check to fail (a taken name, an absent SKU) and assert the message.
- **Quality gate:** `--repo infra`.

## Report   ·   _filled on completion_
_not yet implemented_
