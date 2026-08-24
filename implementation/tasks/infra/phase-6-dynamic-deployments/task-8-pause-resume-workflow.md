# task-6.8 — New workflow — `Sentinel — Pause / Resume`   ·   [infra / phase-6-dynamic-deployments]

| Field | Value |
|-------|-------|
| **Status** | `not-started` |
| **Repo** | `Sentinel-infra` |
| **Phase branch** | `dev/infra-phase-6-dynamic-deployments` |
| **Commit prefix** | `ci:` |
| **Arch refs** | infra.md §7.4 (new) |
| **Depends on** | [[task-2-three-identities]] |

## Spec
New file `ci_pause.yml`. Stops everything that bills compute, without deleting anything.

```
scope    platform | all | <deployment>
action   pause | resume
```

Runs as **`gha-ops`** on `environment: ops` — the custom start/stop role. Pause is the most
frequently run operation here and must not require the identity that can delete the
subscription.

| Resource | Paused how | Cost while paused |
|---|---|---|
| AKS | `az aks stop` — nodes deallocated | compute **stops**; OS disks remain |
| Postgres (shared + dedicated) | `az postgres flexible-server stop` | compute **stops**; storage remains |
| App Service | `az webapp stop` | F1 is free regardless |
| Functions | Consumption — already zero idle | — |
| namespace workloads | scale to 0 replicas | — |
| **ACR** | **cannot pause** | flat daily charge; covered by the free grant |
| **AKS load balancer** | **cannot pause** | persists while the cluster exists |

**Pause is not zero cost, and the workflow must say so.** It prints what it stopped *and what it
could not*, because a pause button that implies zero spend is worse than no button.

**Two limits that will surprise anyone who does not read this:**
- **Postgres auto-restarts after 7 days.** Azure forces it; there is no opt-out. A pause is a 7-day lease. An optional `schedule:` trigger re-pauses nightly and no-ops when already stopped.
- **AKS stop/start takes 5-10 minutes each way.** Resume is not instant.
- `scope: platform` stops the shared cluster, and therefore every deployment's workloads at once. `scope: <deployment>` scales one namespace and stops only its dedicated database. Same button, very different blast radius — the summary must state which one ran.

## Acceptance Criteria
- [ ] pause → every listed resource stopped; resume → all running
- [ ] Idempotent both ways: pausing a paused estate is a no-op, not an error (`az ... stop` on a stopped server *errors*, so state must be checked first)
- [ ] Runs under `gha-ops` and **fails** if attempted with a create or delete action — verify the role is genuinely narrow
- [ ] Summary lists what was stopped, what was skipped, and what cannot be paused
- [ ] Dedicated databases discovered dynamically, not hardcoded

## Tests
- **Integration:** pause, confirm `powerState: Stopped` and `state: Stopped`; resume, confirm Ready.
- **Negative:** attempt a delete as `gha-ops` and confirm it is refused.
- **Quality gate:** `--repo infra`.

## Report   ·   _filled on completion_
_not yet implemented_
