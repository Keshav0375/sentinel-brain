---
name: check
description: Run the Sentinel quality gate (the exact body CI runs, pinned to the right gate source and the repo's venv) for infra, deployment or backend, and report the verdict. Use when asked to check, lint, test or verify a code repo.
argument-hint: "<infra|deployment|backend> [--fast]"
context: fork
agent: gate-runner
background: false
---

Category and flags: $ARGUMENTS

If no category was given, use the active one from `python3 scripts/where.py` (its PHASE line).
Repo paths: infra `../Sentinel-infra` · deployment `../Sentinel-deployment` · backend `../Sentinel`.

Run your checks for that category and reply with your verdict block. A `PARTIAL` or
`INCONCLUSIVE` verdict is not green — list what did not run.
