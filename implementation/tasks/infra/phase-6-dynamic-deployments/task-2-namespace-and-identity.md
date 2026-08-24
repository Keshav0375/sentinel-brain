# task-6.2 — Kubernetes namespace + per-namespace workload identity   ·   [infra / phase-6-dynamic-deployments]

| Field | Value |
|-------|-------|
| **Status** | `not-started` |
| **Repo** | `Sentinel-infra` |
| **Phase branch** | `dev/infra-phase-6-dynamic-deployments` |
| **Commit prefix** | `feat:` |
| **Arch refs** | infra.md §3.7, §4 (rewritten) |
| **Depends on** | [[task-1-deployment-layer]] |

## Spec
The deployment's slice of the shared cluster. Adds provider `hashicorp/kubernetes ~> 2.0`,
authenticated from the AKS admin credential in the platform remote state.

```
namespace/<d>-<env>
  ResourceQuota    cpu/memory from config — one deployment cannot starve the others
  NetworkPolicy    default-deny ingress; explicit allows only
  ServiceAccount   sentinel-backend, annotated with the UAMI client id
```

**The isolation argument, precisely.** The federated credential subject is
`system:serviceaccount:<d>-<env>:sentinel-backend`. Different namespace → different subject →
different UAMI → different Key Vault and database grants. A pod in `t2-dev` presenting its token
cannot obtain `t1-dev`'s vault access, because Entra matches the subject string exactly and
there is no wildcard form. This is cryptographic separation, not a convention.

**A `ResourceQuota` is not optional here.** With one shared cluster, an unbounded namespace can
exhaust the node and take every other deployment down with it. The quota is what makes "shared
cluster" acceptable rather than merely cheap.

## Acceptance Criteria
- [ ] Namespace, quota, netpolicy and annotated ServiceAccount all created
- [ ] The FIC subject contains the namespace; two deployments have provably different subjects
- [ ] **Negative test:** a pod in namespace A cannot read namespace B's Key Vault — run it, do not assume it
- [ ] Deleting a deployment deletes its namespace and leaves the cluster healthy

## Tests
- **Integration:** `kubectl get ns`, `kubectl describe quota -n <ns>`.
- **Negative:** cross-namespace token attempt fails. This is the acceptance test that matters.
- **Quality gate:** `--repo infra`.

## Report   ·   _filled on completion_
_not yet implemented_
