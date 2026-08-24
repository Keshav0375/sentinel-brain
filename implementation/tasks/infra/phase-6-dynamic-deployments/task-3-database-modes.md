# task-6.3 — Database — shared or dedicated per deployment   ·   [infra / phase-6-dynamic-deployments]

| Field | Value |
|-------|-------|
| **Status** | `not-started` |
| **Repo** | `Sentinel-infra` |
| **Phase branch** | `dev/infra-phase-6-dynamic-deployments` |
| **Commit prefix** | `feat:` |
| **Arch refs** | infra.md §3.2 (rewritten) |
| **Depends on** | [[task-1-deployment-layer]] |

## Spec
`database.mode` per deployment, defaulting to `shared`.

**`shared`** — a database plus an Entra role on the platform server. Cheap: one server's compute
serves every deployment. Accepted cost: shared compute, so a runaway query in one deployment can
slow another.

**`dedicated`** — its own flexible server in the deployment's resource group. Full isolation of
compute, storage, admins and backups. Costs a VM against the same grant, ~8 minutes to create,
and adds one more server that must be **started before any plan can run** — the
`ServerStoppedError` problem multiplied per deployment, which the CI start-guard must therefore
iterate over rather than hardcode one server name.

Both paths must produce the **same connection contract** so the backend cannot tell them apart:
one output shape, `db_host` / `db_name`, Entra-only auth, no password in either case.

## Acceptance Criteria
- [ ] Both modes apply and produce identical output *shapes*
- [ ] Switching mode on an existing deployment is either clean or fails loudly — never silent data loss
- [ ] `shared` grants only that deployment's database, verified by a cross-deployment connection attempt that is refused
- [ ] The CI start-guard discovers servers dynamically; no hardcoded server name anywhere

## Tests
- **Integration:** Entra-token psql to both a shared database and a dedicated server.
- **Negative:** deployment A's identity cannot connect to deployment B's database.
- **Quality gate:** `--repo infra`.

## Report   ·   _filled on completion_
_not yet implemented_
