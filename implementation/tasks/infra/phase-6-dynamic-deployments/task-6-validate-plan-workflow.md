# task-6.6 — Rebuild `Sentinel Infra — Validate & Plan`   ·   [infra / phase-6-dynamic-deployments]

| Field | Value |
|-------|-------|
| **Status** | `not-started` |
| **Repo** | `Sentinel-infra` |
| **Phase branch** | `dev/infra-phase-6-dynamic-deployments` |
| **Commit prefix** | `ci:` |
| **Arch refs** | infra.md §7.1 (rewritten) |
| **Depends on** | [[task-5-preflight]] |

## Spec
Rewrite `ci_infra_dry.yml`. `workflow_dispatch` caps at **10 inputs**, which is the constraint
that shaped the whole config design: the form carries *shape and intent*, the YAML carries *size
and detail*.

```
deployment    (required)  demo1
action        plan
environment   dev | prod
components    ______      blank = from config
database_mode default | shared | dedicated
location      ______      blank = default
target        ______
```

**Jobs:** `preflight` → `run-validate` → `run-plan`.

`environment: plan` on every job, deliberately. A dispatch from a feature branch presents
`:ref:refs/heads/<branch>`, which has no credential; declaring the environment rewrites the
subject to `:environment:plan` and makes config-from-any-branch work. Same mechanism that broke
the first apply, used on purpose.

Keep from phase 4, all of it learned live: values reach Terraform through `env:` not `${{ }}`
splicing; `ARM_*` on every terraform step; the Postgres start-guard; `run-validate` runs
`-backend=false` so it needs no credential at all and works before anything is bootstrapped.

## Acceptance Criteria
- [ ] ≤10 inputs; `deployment` alone is sufficient for a run
- [ ] Dispatch from a non-main branch reads that branch's config and authenticates
- [ ] `run-validate` still requires no Azure credential
- [ ] Plan posted as a PR comment, truncated at 60000 chars
- [ ] `actionlint` clean

## Report   ·   _filled on completion_
_not yet implemented_
