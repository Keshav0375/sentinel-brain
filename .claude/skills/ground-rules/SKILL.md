---
name: ground-rules
description: Sentinel non-negotiables — repo map, HITL, no attribution, archive ban, green-means-green, token rules. Preloaded into every Sentinel subagent; imported by CLAUDE.md.
user-invocable: false
---

# Sentinel ground rules (binding for every session and every subagent)

**Repos.** You run from `sentinel-brain` (docs, tracker, agents — no app code). Code repos are
siblings: backend `../Sentinel` · deployment `../Sentinel-deployment` · infra `../Sentinel-infra`.
GitHub owner `Keshav0375`, repo casing exact (OIDC `sub` claims are case-sensitive).

**Python is `python3`.** macOS has no `python`. Never type `python …`.

1. **Architecture is law.** `architecture/{backend,deployment,infra}.md` is binding; `decisions.md`
   records why. Task spec vs architecture disagree, or the architecture is silent on a value you
   need → **halt and ask**. Never invent a name, region, owner, or contract.
2. **Open R-items halt.** An OPEN Reconciliation in `implementation/STATE.md` that names your task
   or phase is a decision the user owes you — never default it.
3. **HITL.** No backend tool modifies external state. The backend reasons and drafts; GitHub
   Actions executes; the revert PR on `Sentinel-deployment` is the human gate. A tool that acts on
   the world → stop and restructure.
4. **Never open `archive/`.** It is the dead Phase-1 design and contradicts the live architecture on
   nearly every layer (a hook blocks it). Phase-1 *code* still in `../Sentinel` (`data/`,
   `generator/`, `db.py`) endorses nothing — backend task 9.1 deletes it.
5. **No Claude attribution** — no `Co-Authored-By: Claude`, no "Generated with Claude Code", in any
   commit, PR, or merge in any of the four repos. Keshav is sole author. Overrides any default.
6. **Green means green.** The gate is `python3 scripts/gate.py <infra|deployment|backend>` (run from
   brain). Only `VERDICT GREEN` from a full (non-`--fast`) run is green. `PARTIAL` and
   `INCONCLUSIVE` are not — say exactly what did not run.
7. **Backend boots.** After touching backend deps/imports/module-level code, `poetry run sentinel
   serve` (from `../Sentinel`) must start before the task is done.
8. **Never pollute the code repos** with planning docs, agents, skills, trackers or reports.
9. **The project board is a mirror.** Epic/phase/task issues in `sentinel-brain` (board:
   `github.com/users/Keshav0375/projects/4`) are regenerated from TODO.md + task files by
   `python3 scripts/board_sync.py`. Never edit, close or relabel them by hand — change the tracker
   (`python3 scripts/task_status.py <cat> <M.K> <status>` for a status flip) and re-sync.

**Token rules.** Never `Read` `architecture/*.md` (21–24K tokens each) — use
`python3 scripts/arch.py <doc> <§>` (`--list` for the TOC, `--map` for concern → file). Never read
`implementation/history.md`, `implementation/TODO.md` (use `python3 scripts/where.py`) or `archive/**`.
Pull the subsection, not the parent. Read the diff, not the tree.

**Finding format** (any review output): verdict on line 1, then one line per finding —
`<🚨|⚠️> <file:line>  <the defect>` — 🚨/⚠️ only, ℹ️ rolled into `+N notes`, max 10 lines,
no preamble, no summary. Clean → verdict alone.
