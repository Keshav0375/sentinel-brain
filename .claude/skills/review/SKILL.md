---
name: review
description: Quick ad-hoc review of uncommitted or last-commit changes in a Sentinel code repo for correctness, standards and Phase-2 safety invariants. Mid-task check; the authoritative review is /implement-phase Step 5.
argument-hint: "[infra|deployment|backend]"
context: fork
agent: code-reviewer
background: false
---

Ad-hoc review. Target: $ARGUMENTS (empty → the active category from `python3 scripts/where.py`).
Repos: infra `../Sentinel-infra` · deployment `../Sentinel-deployment` · backend `../Sentinel`.

Scope: `git -C <repo> diff` (uncommitted); if empty, `git -C <repo> diff HEAD~1`.

Besides your normal correctness/standards review, flag these as 🚨 (you are standing in for the
safety reviewer on this quick pass):
- a backend tool/agent that modifies external state (opens a PR, posts to Teams, deploys,
  restarts, rolls back) — the backend drafts, GitHub Actions executes;
- an approval tool, `/approvals` endpoint or `request_human_approval` (Phase-1, deleted);
- a tool-call budget (20) or reflexion cap (2) that is declared but not enforced;
- `db-password`, `X-Sentinel-Token`, `SENTINEL_API_TOKEN`, or any secret in code/logs;
- an eval judge on the same model family as the agents it scores.

Reply in your standard format only.
