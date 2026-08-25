# task-5.5 — Rewrite infra.md; supersede R5, R6, C1   ·   [infra / phase-5-dynamic-foundations]

| Field | Value |
|-------|-------|
| **Status** | `not-started` |
| **Repo** | `Sentinel-infra` |
| **Phase branch** | `dev/infra-phase-5-dynamic-foundations` |
| **Commit prefix** | `docs:` |
| **Arch refs** | infra.md §2-§10, decisions.md |
| **Depends on** | [[task-4-workspaces-and-remote-state]] |

## ⚠ RESOLVED 2026-08-25 — pre-build audit

Two additions to the supersession list, both consequences the original entry did not price in:

- **`apply` becomes dispatch-only.** Dropping `ref:refs/heads/main` from every identity means no
  push can apply. This is a deliberate consequence of multi-deployment, not an oversight — a push
  cannot know which deployment it means. Record it beside the R5/R6 supersessions.
- **`github-repo-config.tf` is deleted in 5.0**, so §5 (cross-repo distribution) describes
  nothing that exists until phase 6 rebuilds it per-deployment. Mark §5 superseded rather than
  leaving it as a description of live code.

Also record the **per-deployment API identity** decision (owner, 2026-08-25) in §4.4: one backend
app registration and one GHA client per deployment, with tenant-qualified identifier URIs, so a
token minted for one deployment fails audience validation at another's backend.

## Spec
The architecture describes a single static estate. After phase 5 that is false in enough places
that leaving it would make it actively misleading — the failure mode this project has already
paid for ten times in phase 4's pre-build audit.

**Rewrite:** §2 (repo layout + two layers), §3 (platform vs deployment resources), §4 (three
identities, environment-scoped subjects), §8 (workspaces + remote state), §9 (config file
replaces most repo variables), §10 (bootstrap: state → identities → platform).

**Supersede in `decisions.md`, each with its original reasoning preserved and what changed:**

| | Was | Now |
|---|---|---|
| **R5** | Contributor + RBAC Admin scoped to `sentinel-rg`; deliberately narrow because PR-reachable | Subscription scope, split across three identities; the narrowness moves from *scope* to *reachability* |
| **R6** | No CI destroy — purge needs subscription scope CI should not hold | CI destroys, behind `environment: destroy`. Purge is required for the destroy→recreate cycle to work at all |
| **C1** | Resource groups bootstrap-created, read-only | Managed, except the state RG which can never manage itself |
| **§3.7** | One cluster per estate | One cluster, namespace per deployment — forced by the 6-vCPU ceiling |

**Rewrite `docs/BOOTSTRAP.md`** — the new order is state storage → identities → platform → first
deployment. Keep the Day-2 sections; both are still true and both were learned the hard way.

## Prerequisites
- [ ] 5.0-5.4 complete, so the docs describe what exists rather than what is intended

## Acceptance Criteria
- [ ] No section of `infra.md` describes the pre-phase-5 model without marking it superseded
- [ ] R5, R6, C1 each carry a supersession entry naming what replaced them and why
- [ ] `python scripts/arch.py infra --list` resolves; no dangling `§` references
- [ ] No `0375` and no `ci_destroy_infra` anywhere outside a historical note

## Tests
- **Link check:** every `§` in the task files resolves via `arch.py`.
- **Quality gate:** `--repo infra`.

## Report   ·   _filled on completion_
_not yet implemented_
