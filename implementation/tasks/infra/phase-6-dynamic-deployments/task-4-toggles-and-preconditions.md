# task-6.4 — Component toggles + dependency preconditions   ·   [infra / phase-6-dynamic-deployments]

| Field | Value |
|-------|-------|
| **Status** | `not-started` |
| **Repo** | `Sentinel-infra` |
| **Phase branch** | `dev/infra-phase-6-dynamic-deployments` |
| **Commit prefix** | `feat:` |
| **Arch refs** | infra.md §2 (rewritten) |
| **Depends on** | [[task-1-deployment-layer]] |


> ⚠️ **Read [RESOLUTIONS.md](RESOLUTIONS.md) first.** These specs predate phase 5. Ten
> conflicts were resolved before the build; that file overrides this one where they differ.

## Spec
`components: [keyvault, database, functions, app_service, event_grid, namespace]` drives `count`
on each module.

**Checkbox independence is a lie, and this task exists to say so out loud.** The components have
hard dependencies:

| Component | Requires |
|---|---|
| `functions` | `keyvault` (KV references for its secrets), `event_grid` |
| `event_grid` | `functions` (the subscription needs the function app id) |
| `namespace` | platform AKS |
| backend identity | `namespace` + `database` + `keyvault` |

Unchecking `keyvault` while `functions` is on does not produce a smaller stack — it produces a
provider error hundreds of lines into a plan, naming a resource attribute rather than the
mistake. So every dependency gets a `precondition` that fails in seconds with the actual
sentence: `"components: functions requires keyvault"`.

Note `functions` and `event_grid` are mutually dependent — they are a single unit and the
validation should say so rather than pretending either can stand alone.

## Acceptance Criteria
- [ ] Every dependency in the table is enforced by a precondition with a human-readable message
- [ ] An invalid combination fails within ~5 seconds of `plan`, before any provider call
- [ ] A minimal deployment (`[keyvault, database]`) applies successfully
- [ ] Removing a component from a live deployment destroys only that component

## Tests
- **Negative, one per dependency edge:** assert the error text, not just the failure.
- **Quality gate:** `--repo infra`.

## Report   ·   _filled on completion_
_not yet implemented_
