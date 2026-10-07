# deployment phase 3 — Scenario Branches

| | |
|---|---|
| **Repo** | `Sentinel-deployment` |
| **Branch → PR** | `dev/deploy-phase-3-scenario-branches` → `main` · PR #4 — https://github.com/Keshav0375/Sentinel-deployment/pull/4 |
| **Tasks** | 1/1 green (gate GREEN at cc36aa9, 248 tests) |
| **Gate** | ⬜ awaiting sign-off |

## What shipped

- **3.1 Scenario branches** — catalog of 30 scenario branches (pass/, deployfail/, runtime/), each one `scenario:` commit on e67e19d, plus test_scenarios checking catalog and fetched refs; GET / synthetic asserts content-type and body.

## What this unblocks

- Phase 4 and later can run any scenario by merging its own PR and reverting it; the catalog (§4.1) is deterministic and exhaustive.

## See it working

1. ```bash
   python3 scripts/gate.py deployment
   ```
   → expect: VERDICT GREEN
2. ```bash
   pytest tests/test_scenarios.py -q -rs
   ```
   → expect: all pass
3. ```bash
   git branch -r | grep -cE 'origin/(pass|deployfail|runtime)/'
   ```
   → expect: 30
4. Live smoke: apply → grant-db-access.sh → datadog/apply.sh → for each of pass/01, deployfail/03, runtime/01: open PR, merge, observe, revert → destroy.

## Not done / blocked

- **Merging this PR does not deploy** (only scenarios/, datadog/, tests/, requirements-dev.txt change). Scenario branches are never merged with it.
- **Not verified live:** per-case smoke (pass/01, deployfail/03, runtime/01); runtime/07 mtime anchor surviving zip + Oryx. Estate is destroyed.
- **Follow-ups:** ci_app_deployment.yml lines 136-137, 167, 202 say "old version still serving", wrong for no-boot (deployfail/07-10) and verify faults; fix in a PR merged when the estate is up (it triggers a deploy). Probe uses the branch tree, not the merge-tree. test_scenarios fails under a single-branch checkout (no CI runs it). DISPATCH_PAT expires in 90 days. After next apply, re-run datadog/apply.sh for the new GET / assertions.

## Decisions made during the build

- Catalog redesigned for determinism (decision 2026-10-07; §4.1 exhaustive; brain 32a8cfe, 71a1494, 35cc4b1).
- deployfail/07-10 fail at deploy, not verify, because az tracks startup; runtime/07 degrades after 10 min; deployfail/03 pins fastapi==0.0.0; pass/02 refactors the startup timestamp.
