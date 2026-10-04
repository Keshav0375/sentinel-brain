---
name: new-ticket
description: Create a Sentinel ticket the Jira way but tracker-first — a new task (child), phase (parent) or epic-level note is written into the brain tracker (task file from the template + TODO.md row), then mirrored to GitHub issues + the project board with scripts/board_sync.py. Use when the user wants to add a ticket, task, story or phase.
argument-hint: "<task|phase> <category> <title> [details]"
disable-model-invocation: true
context: fork
agent: tracker-clerk
background: false
---

Create a ticket from: **$ARGUMENTS**

The tracker is the source of truth; the board is a mirror. Never create the GitHub issue by hand.

1. Parse type (`task` | `phase`), category (`infra` | `deployment` | `backend`), title, details.
   Anything missing that you cannot infer (which phase a task belongs to, its spec) → stop and
   return `HALT` with the exact question.
2. **task** — next free id `M.K` in that phase (from `python3 scripts/where.py <cat>-<M>`):
   - copy `implementation/_templates/task-template.md` to
     `implementation/tasks/<cat>/phase-<M>-<slug>/task-<K>-<kebab-title>.md`; fill the header table
     (Status `not-started`, Repo, Local path, Phase branch from TODO.md, Commit prefix, Arch refs,
     Depends on) and Spec / Acceptance Criteria / Tests / How to Verify from the details. Leave
     Report empty. Arch refs must be real § (`python3 scripts/arch.py <cat> --list`).
   - add the row `| M.K | <title> | [task-K](tasks/<cat>/phase-<M>-<slug>/<file>) | ⬜ |` to that
     phase's table in `implementation/TODO.md`.
   **phase** — add a `### Phase <M> — <name>  ·  branch \`dev/<…>\`  ·  Gate: 🔒` heading + empty
   task table at the end of the category in TODO.md and create its folder. Ask for the branch
   slug if not given.
3. `python3 scripts/board_sync.py` — creates the issue, links it under its parent, sets board fields.
4. Commit `docs: add <cat> <id> — <title>` to brain `main` (no attribution) and push.

Return: the new file path, the TODO row, and the issue URL printed by the sync.
