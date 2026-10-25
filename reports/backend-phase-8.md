# backend phase 8 — CI/CD Workflows

| | |
|---|---|
| **Repo** | `Sentinel` |
| **Branch → PR** | `dev/backend-phase-8-cicd` → `release-phase-2` · PR #27 — https://github.com/Keshav0375/Sentinel/pull/27 |
| **Tasks** | 4/4 done-pending-review |
| **Gate** | ⬜ awaiting sign-off (VERDICT GREEN on 7b82bfe, full run, 7 ran, 0 skipped; boot OK) |

## What shipped

- **8.1 ci_validation** — read-only PR gate (build, migrate, run, probe, pytest, actionlint pinned and checksum-verified); guard-main-source injection fixed.
- **8.2 ci_backend_deployment** — build, deploy, live smoke (GUID-first audience), promote or rollback, scale down.
- **8.3 ci_incident_response** — incident dispatch, `GET /incidents/{id}/rollback-spec`, revert PR as the human gate, Teams notice.
- **8.4 ci_backend_scale** — manual up/down toggle and nightly scale-to-zero.
- Shared `resolve-stable-tag` composite action; every action pinned by SHA.

## What this unblocks

Phase 9 (cleanup and docs). The workflows, the rollback-spec endpoint and the composite actions are the contract it documents.

## See it working

1. `cd ../Sentinel && poetry run pytest tests/test_infra tests/test_scripts -q` → all pass
2. `cd ../Sentinel && actionlint .github/workflows/*.yml` → no output
3. PR #27 Checks tab → ci_validation green (first real run)

## Not done / blocked (all gate LIVE runs)

- (a) User runs /new-ticket for the infra CI-identity ticket; full list in decisions 2026-10-24 phase 8 "Names the infra CI-identity ticket must create", including the PG SELECT(id) grant.
- (b) User sets release-phase-2 as Sentinel's default branch (back to main at the final merge).
- (c) User creates REVERT_PR_PAT (fine-grained, Sentinel-deployment only, Contents and PRs RW, 90 days) as a sentinel-dev environment secret.
- (d) Real Anthropic/OpenAI keys in KV (B4/B5).
- (e) Estate is down (B1): nothing in phase 8 has run live.
- (f) Known limitation: the sentinel-backend concurrency group holds one pending run.
- (g) The PR's own CI is the first real run of ci_validation.yml.

## Decisions made during the build

- 29edfa7 release-phase-2 live branch, REVERT_PR_PAT, rollback-spec endpoint, CI-identity names; 8b72023 path filters include alembic and scripts; 61178fa gha PG SELECT(id) grant, concurrency limitation; e1cdbf0 audience list, SHA pins, shared stable lookup, PR-first reporting.
- Reviews: architecture CONFORMS (3 warnings fixed); safety SAFE (1 fixed); code CHANGES REQUESTED (2 blockers) then LGTM after 2 fix rounds.
