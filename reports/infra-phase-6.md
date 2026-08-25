# infra phase 6 — Dynamic Deployments & Workflows

**Status:** done-pending-review · PR [#8](https://github.com/Keshav0375/Sentinel-infra/pull/8)
**Date:** 2026-08-25 · **Tasks:** 6.1–6.8 · **Gate:** ⬜ awaiting owner

---

## In plain language

Before this phase, building Sentinel's infrastructure meant running Terraform by hand and there
was exactly one of everything. Now there are **buttons**, and you can have many deployments.

**Three buttons, in the repo's Actions tab:**

| Button | What it does |
|---|---|
| **Sentinel Infra — Deploy** | Type a name, pick `apply` → you get a complete isolated deployment. Pick `destroy` → it's gone. |
| **Sentinel Infra — Validate & Plan** | Runs on every push and PR. Tells you what a change *would* do before it does it. |
| **Sentinel — Pause / Resume** | Stops everything that costs money, without deleting anything. |

**What "a deployment" is:** its own resource group, its own Key Vault, its own database, its own
slice of the Kubernetes cluster, its own identity. Deployments cannot see or affect each other,
and none of them can damage the shared platform underneath.

**The one number that shaped everything:** your subscription allows **6 CPUs total** in the
region, and a Kubernetes node uses 2. So deployments *share* one cluster and get a namespace
each, rather than each getting a cluster — which would have stopped at three.

**What you type to create one:** `demo1`. That's it. Everything else has a sensible default, and
the details live in `azure/config/deployment-config.yaml` where they can be reviewed in a pull
request instead of remembered.

---

## The acceptance test, run live

```
create     9 objects · kv-demo1-dev-8baf · database demo1_dev on the shared server
destroy    9 destroyed · vault PURGED (0 soft-deleted) · platform intact
recreate   9 added · same name, immediately
```

Destroying a deployment did not touch the shared platform, and the vault name was reusable at
once. That single cycle exercises naming determinism, the purge right, workspace isolation and
namespace teardown together — it is the phase in one command.

**A precision worth keeping:** "9" is Terraform objects, not Azure resources. In the portal,
`rg-demo1-dev-cc` holds exactly one thing (the vault). The database lives on the *platform's*
server as `demo1_dev`; the other five objects are guards, which are not Azure resources at all.

## CI, green on the real thing

```
Run Validate    success
Run Preflight   success
Run Plan        success — No changes, posted as a PR comment
```

Preflight earned its place immediately. On an earlier run it reported
`postgres servers running  WARN  stopped: psql-sentinel-plat-2fef — the plan will fail otherwise`
and then the plan failed exactly as predicted.

---

## Decisions

- **Entra RBAC on the cluster.** The kubernetes provider authenticates by Entra token through
  kubelogin, not a downloaded admin credential. Without `azure_rbac_enabled` that kubeconfig
  *is* cluster-wide access — giving it to a PR-reachable identity would repeat the
  `listCredentials` mistake phase 5 refused.
- **Preflight split by identity, not by widening one.** Name-availability is a POST `*/action`
  Reader cannot call, so it runs under `gha-deploy` at apply time.
- **`pause.sh` is a script, not an inline `run:` block.** It is linted by the gate's
  `scripts/*.sh` glob, reviewable, and runs locally.
- **The vault ships empty.** Terraform writes no secrets — one in state is readable by anything
  with state access. A deployment with an unseeded vault is a *valid* state.
- **`identity.tf` was written, then removed.** See below.

## Four things the linters caught that I introduced

Worth listing, because the pattern is the point: each was invisible locally.

| | |
|---|---|
| An inline `run:` block **hung actionlint outright** | gate went from timing out at 550s to 0.5s once extracted to a script |
| A comment beginning `# shellcheck glob ...` | parsed as a **directive**, not prose |
| All five scripts were **not executable in git** | `chmod +x` on Windows is a no-op to git; failure appears only in CI |
| A literal `\n` instead of a line continuation | two `-var` flags ran together; caught by shellcheck SC1012 |

## The one that cost the most

**A declared Terraform provider is configured whether or not any of its resources are planned.**
Every resource in `identity.tf` was `count = 0`, so I assumed the `azuread` provider would never
be reached. It was — and because it could not authenticate to the identity tenant, it broke
*every* plan in the repo, including the platform's, with an error naming a tenant the change
never touched.

Phase 5 recorded that an unused provider is dead weight the lock file still pins. This is that
lesson with teeth: not merely dead weight, actively fatal.

`identity.tf` is therefore **deleted, not disabled** — the per-deployment app registrations are
written and work (commit `65e35b9`) and return when `sentinel-tf-identity` carries federated
credentials for the `environment:*` subjects.

---

## Still open

| | | |
|---|---|---|
| ⛔ | **[Sentinel#18](https://github.com/Keshav0375/Sentinel/pull/18)** | until merged, `main`'s gate is 6 checks, not 11 |
| ⚠️ | **Pause and Destroy have never run** | a `workflow_dispatch` workflow must exist on the **default branch** before it can be dispatched — so they are untestable until this PR merges |
| ⚠️ | **`gha-ops` cannot-delete is proven by role inspection** | not by a refused delete |
| ⚠️ | **Per-deployment API identity** | needs the identity-tenant credentials |
| ⚠️ | **Namespaces have never been created** | `demo1` ran without the `namespace` component; the kubelogin path is unexercised |
| ⛔ | B4–B8 | secret values; vaults ship empty by design |

---

## See it working

```powershell
python ../Sentinel/scripts/quality_gate.py --repo infra --path .   # 11 ran
cd modules/naming; terraform test; cd ../..                        # 9 passed
bash ./scripts/preflight.sh --mode plan
```

**After merging**, in Actions:

1. **Sentinel — Pause / Resume** → `action: resume`, `scope: all`
2. **Sentinel Infra — Deploy** → `deployment: demo2`, `action: apply`, `layer: deployment`, `environment_name: dev`
3. **Sentinel Infra — Deploy** → `deployment: demo2`, `action: destroy`, `confirm: demo2`
4. **Sentinel — Pause / Resume** → `action: pause`, `scope: all`

Step 3 refuses to run unless `confirm` matches exactly, and refuses the `platform` layer
outright.
