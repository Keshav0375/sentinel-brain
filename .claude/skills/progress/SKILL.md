---
name: progress
description: Show Sentinel Phase-2 build progress — tasks verified, phases signed, the active phase, blockers and open reconciliations — straight from the tracker.
allowed-tools: Bash(python3 scripts/where.py *)
---

## Tracker (computed live)
!`python3 scripts/where.py --all`

## Active phase
!`python3 scripts/where.py || true`

Report from the two blocks above only — read nothing else:

- **Progress bar** — `██████░░░░ 40%` for verified/total tasks, plus phases signed.
- **Where we are** — active phase, repo, branch, PR into.
- **This phase** — one line per task with its status.
- **Next up** — the next 3 actionable tasks; anything in a `locked` phase says why.
- **Blockers / open R-items** — every `!!` line, shortened to one line each. Open R-items halt the
  tasks they name, so call them out even when nothing is blocked yet.

Read-only. ≤ 25 lines.
