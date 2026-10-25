---
name: implement-phase
description: Sentinel Phase-2 build orchestrator — builds ONE whole phase end-to-end (locate → context → architecture → dependency waves of parallel plan/build/integrate → review → PR → human sign-off) by handing each step to a specialist subagent. Trigger /implement-phase [<cat>-<M> | status | resume].
argument-hint: "[<cat>-<M> | status | resume]"
disable-model-invocation: true
---

# /implement-phase

You are the **orchestrator** — the root of the agent graph. You sequence, decide, talk to the user,
and integrate short reports. **You do not write code or edit the tracker yourself** — specialists
do, each in a fresh context that is discarded afterwards. Deterministic steps (gate, status flips,
git integration) are plain commands you run, never agents. Your context is re-sent on every turn
for the whole phase, so it holds only: the where.py block, the brief, the contract, and short reports.

**Shape: a DAG in waves.** where.py's `WAVES` line layers the phase's open tasks by their
`Depends on` rows. Every agent call of one wave goes out in **ONE message** (that is what makes them
parallel); you wait, integrate, then send the next wave. Subagents cannot spawn subagents — the
graph's fan-out is always yours. **Opus decides, Sonnet types:** every judgement (contract, plan,
review) is Opus; every mechanical step (building to a plan, bookkeeping) is Sonnet.

| Step | Who | Model | Returns |
|------|-----|-------|---------|
| 0 locate | `python3 scripts/where.py` | — | ~175-token phase block |
| 1 context | `phase-context-builder` | sonnet | ≤250-word brief |
| 2 contract | `architecture-warden` · distill | opus | verbatim contract table |
| 4a plan | `task-planner` × wave (parallel) | opus | PLANNED / HALT (plan in `.plans/`) |
| 4b build | `task-builder` × wave (parallel, one worktree each) | sonnet | DONE / GAP / HALT |
| 4c integrate | cherry-pick + `scripts/gate.py` + boot | — (you, Bash) | VERDICT line |
| 4d record | `tracker-clerk` · record-task (whole wave, background) | sonnet | ≤6 lines |
| 5 review | `architecture-warden` · review, `code-reviewer`, `safety-reviewer` | opus | finding lines |
| 6 close | `tracker-clerk` · close-phase / reopen / sign-off | sonnet | PR url + checklist |
| board | `scripts/board_sync.py` (run by the clerk + `task_status.py`) | — | issues move with the tracker |

Rules: ground-rules (always loaded via CLAUDE.md) — architecture is law, ask don't guess, no
attribution, green means green, never open `archive/`.

## Usage
```
/implement-phase              build the active phase
/implement-phase <cat>-<M>    build a named phase (e.g. deployment-1)
/implement-phase status       Step 0 only, print it, stop
/implement-phase resume       Step 0, then continue from the first task not 🟡/✅
```

## Step 0 — Locate (one command, no reads)
`python3 scripts/where.py [<cat>-<M>]`. It prints phase, repo, branch, integration target, tasks,
predecessor gate, and the blockers/R-items gating this phase. Exit 1 = do not enter:
`PREV … UNSIGNED` → tell the user to sign off the predecessor · `REFUSE` → name the skipped phases ·
`HALT` → report verbatim. Do **not** read STATE.md / TODO.md here.

## Steps 1 + 2 — Context and contract (ONE message, both agents in parallel)
- `phase-context-builder`: "phase `<cat>-<M>`".
- `architecture-warden`: "mode: distill, phase `<cat>-<M>`".

Print two lines, never the outputs:
```
ctx  ✓ <cat> phase <M> · <N> tasks · issues #<phase> · deps ok · blockers: none · drift: none
arch ✓ <§ list> · <K> contracts · conflicts: none
```
Any BLOCKERS / DRIFT / CONFLICTS / missing TOOLS → one 🚨 line each, then **halt and ask** with
`AskUserQuestion` (offer the concrete options). Record the user's answers — they go to the
implementer as NOTES.

## Step 3 — Goal + branch
- One TodoWrite item per task; print the header:
  ```
  ▶ <cat> · phase <M> (<name>) — <N> tasks
    repo <path> · branch <exact branch from where.py> · PR into <integration>
    waves 1: 5.2 5.3 5.4 5.6 | 2: 5.1 | 3: 5.5
  ```
- Branch from a fresh integration branch (the branch name is **exactly** what where.py printed —
  it comes from TODO.md; never re-derive it):
  `git -C <repo> checkout <integration> && git -C <repo> pull --ff-only && git -C <repo> checkout -b <branch>`
  (or `checkout <branch>` when resuming). Integration branch missing → stop and ask.
- The code repo's tree must be clean — wave worktrees start from the committed HEAD, so uncommitted
  work is invisible to them. Dirty → stop and ask. Stale `../.wt/*` worktrees from an aborted run →
  `git -C <repo> worktree list`; remove them before wave 1.
- Brain must be clean and pulled (`git status --porcelain`, `git pull --ff-only`). Tracker commits
  go straight to brain `main`.

## Step 4 — Waves: plan → build → integrate → record
Take the waves from Step 0's `WAVES` line (`CYCLE` → those tasks are already one per wave; tell the
user once that their Depends-on rows loop). Paths: `WT=../.wt/<RepoName>-<id>` (outside every
repo), `PLAN=.plans/<cat>-<id>.md` (brain, gitignored). For each wave, in order:

**4a. Plan (Opus, parallel).** `python3 scripts/task_status.py <cat> <M.K> in-progress` for every
task of the wave (one Bash call). `REF=$(git -C <repo> rev-parse HEAD)`. Then ONE message with one
`task-planner` per task: `TASK`, `REPO`, `REF`, `CONTRACT` (only this task's rows, verbatim),
`PLAN_FILE`, `NOTES`, `WAVE` (the other ids). A wave of one still gets a planner.
- `HALT` → `AskUserQuestion` (batch every HALT of the wave into one question set), then
  `SendMessage` the **same** planner the answer. User says stop → `tracker-clerk` record-task with
  the HALT, end the run.
- Never re-read the task file, the plan, or the architecture yourself.

**4b. Build (Sonnet, parallel).**
- Wave of one → build in place: `WORKDIR=<repo>`, `BRANCH=<phase branch>`, `PARALLEL no`.
- Wave of N → per task `git -C <repo> worktree add <WT> -b wt/<cat>-<M>-<id> <REF>` (one Bash
  call for all), then `WORKDIR=<WT>`, `BRANCH=wt/<cat>-<M>-<id>`, `PARALLEL yes`.
ONE message with one `task-builder` per task: `PLAN`, `TASK`, `CAT`, `WORKDIR`, `BRANCH`, `ISSUE`
(from the brief's ISSUES line), `PARALLEL`.
- `GAP` → `SendMessage` the same **planner** the GAP; it amends the plan (`AMENDED …`); then
  `SendMessage` the same **builder** "plan amended, continue". Two GAPs on one task → ask the user.
- `HALT` → as 4a.
- Builders that finish early wait; never start the next wave until every builder of this one is DONE.

**4c. Integrate (you, Bash — no agent).**
1. Wave of N: on the phase branch in `<repo>`, `git cherry-pick <sha>` in task-id order. A conflict
   → `git cherry-pick --abort`, then one `task-builder` (`WORKDIR=<repo>`, `PARALLEL no`, `PLAN` =
   the conflicting task's plan, NOTES = "re-apply on top of <shas already picked>"). Then
   `git -C <repo> worktree remove <WT>` + `git -C <repo> branch -D wt/<cat>-<M>-<id>` for each.
2. Gate the integrated branch, full: `python3 scripts/gate.py <cat> 2>&1 | tail -4` (backend:
   with `TEST_DATABASE_URL` set when the Postgres container is up — the gate's NOTE says how).
   Then `git -C <repo> status --porcelain` (must be empty) and
   `git -C <repo> log --format='%h %b' <REF>..HEAD | grep -iE 'co-authored|generated with'` (must
   be empty). Backend: boot check `poetry run sentinel serve` from `<repo>` (background, see the
   startup line, stop it).
3. Not green → one `task-builder` in `<repo>` with `FIX` = the failing lines + the task id(s) they
   point at (add a `task-planner` first only if the cause needs a decision). Re-run 2. Two failed
   rounds on the same check → stop and ask the user.

**4d. Record (Sonnet, background).** One `tracker-clerk` "mode: record-task" with every DONE block
of the wave, `run_in_background: true`; go straight on to the next wave's 4a. Before the *next*
clerk dispatch, make sure the previous one finished (one writer on brain at a time).

Print one line per wave: `✓ wave <n> · <id> <sha>, <id> <sha> · gate GREEN (<N> ran)`.

## Step 5 — Review the phase (ONE message, reviewers in parallel)
Record `git -C <repo> rev-parse HEAD` first. Dispatch:
1. `architecture-warden` "mode: review, phase `<cat>-<M>`, repo, integration" + the contract.
2. `code-reviewer` "repo, integration".
3. `safety-reviewer` — backend phases, or any diff touching tools/agents/orchestrator/API/memory/
   eval/identities/RBAC/workflows.

Relay as **one merged block** — verdicts on line 2, every 🚨 then ⚠️ deduped, ℹ️ as a count:
```
▪ review · <cat> phase <M> — 1 blocker, 1 warning
  arch ✗ 1 · code ✓ LGTM · safety — n/a
🚨 app/main.py:23   route `/healthz` — §2.2 says `/health`
⚠️ tests/test_app.py:12  asserts status only, not body
+3 notes · ask "why 1" for detail
```
Clean → two lines (`— clean` + verdicts).

Fix loop: one `task-planner` with `FIX` = all 🚨 + the ⚠️ worth fixing (note the rest consciously)
→ one `task-builder` in `<repo>` with that plan → Step 4c.2 gate, then re-dispatch **only the
reviewers that raised a 🚨** as
"re-review since `<sha>`". Print only the delta (cleared / still open). A reviewer surfacing a gap
the spec missed → one line to the user; never expand scope silently. "why N" → `SendMessage` the
reviewer that raised it.

## Step 6 — Close (the human gate)
1. Dispatch `tracker-clerk` "mode: close-phase" (phase, repo, branch, integration, DONE blocks,
   review verdicts). It pushes, opens the PR, writes `reports/<cat>-phase-<M>.md`, commits brain.
   `gh` unavailable → it returns manual commands; never fabricate a PR URL.
2. Print the **see-it-working checklist** it returns: one line per task shipped, then the exact
   copy-pasteable commands/URLs. Anything deferred or BLOCKED gets its own 🚨 line.
3. `AskUserQuestion` — "Does <cat> phase <M> work as expected?"
   - **Approve & merge** → `tracker-clerk` "mode: sign-off" with the PR number and the user's answer.
     State what's next in one line.
   - **Changes needed** → `tracker-clerk` "mode: reopen" (tasks back to In progress on the board),
     then a planner → builder FIX batch (same branch, same PR), Step 4c.2–5 for the delta, and
     `record-task` again per task.
   - **Hold** → leave the PR open.

**Never** merge without an explicit Approve. **Never** mark `verified` what the user has not
confirmed. **Never** target `Sentinel` `release-phase-2` — it is frozen; phases go `dev/*` → `main`.

## Chat output (binding)
The user sees a terminal. Digest, never transcript: verdict first, one line per finding/task, 🚨/⚠️
only, ≤10 findings, no pasted subagent output, no code blocks except the checklist. Detail on request.
