---
name: implement-phase
description: Sentinel Phase-2 build orchestrator — builds ONE whole phase end-to-end (locate → context → architecture → per-task build/verify/record → review → PR → human sign-off) by handing each step to a specialist subagent. Trigger /implement-phase [<cat>-<M> | status | resume].
argument-hint: "[<cat>-<M> | status | resume]"
disable-model-invocation: true
---

# /implement-phase

You are the **orchestrator**. You sequence, decide, talk to the user, and integrate short reports.
**You do not write code, run the gate, or edit the tracker yourself** — specialists do, each in a
fresh context that is discarded afterwards. Your context is re-sent on every turn for the whole
phase, so it holds only: the where.py block, the context brief, the contract, and ≤12-line reports.

| Step | Who | Model | Returns |
|------|-----|-------|---------|
| 0 locate | `python3 scripts/where.py` | — | ~175-token phase block |
| 1 context | `phase-context-builder` | sonnet | ≤250-word brief |
| 2 contract | `architecture-warden` · distill | opus | verbatim contract table |
| 4a build | `task-implementer` (one per task) | opus | DONE / HALT block |
| 4b verify | `gate-runner` | haiku | verdict block |
| 4c record | `tracker-clerk` · record-task | sonnet | ≤6 lines |
| 5 review | `architecture-warden` · review, `code-reviewer`, `safety-reviewer` | opus | finding lines |
| 6 close | `tracker-clerk` · close-phase / sign-off | sonnet | PR url + checklist |

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
ctx  ✓ <cat> phase <M> · <N> tasks · deps ok · blockers: none · drift: none
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
  ```
- Branch from a fresh integration branch (the branch name is **exactly** what where.py printed —
  it comes from TODO.md; never re-derive it):
  `git -C <repo> checkout <integration> && git -C <repo> pull --ff-only && git -C <repo> checkout -b <branch>`
  (or `checkout <branch>` when resuming). Integration branch missing → stop and ask.
- Brain must be clean and pulled (`git status --porcelain`, `git pull --ff-only`). Tracker commits
  go straight to brain `main`.

## Step 4 — Per task: build → verify → record
For each task in order:

**4a. Build** — dispatch `task-implementer` (foreground) with `TASK` (file path), `REPO`, `BRANCH`,
`CONTRACT` (only the rows relevant to this task, verbatim), `NOTES` (user answers so far).
- `HALT` → show its `ASK` to the user via `AskUserQuestion`; then `SendMessage` the **same**
  implementer the answer (its context is intact). If the user says stop → dispatch
  `tracker-clerk` record-task with the HALT and end the run.
- Never re-read the task file or the architecture yourself.

**4b. Verify** — dispatch `gate-runner`: "category `<cat>`, repo `<repo>`, expected sha `<sha>`".
- Must be `VERDICT GREEN`, `TREE clean`, `attribution none`, `MATCH ok`.
- Anything else → `SendMessage` the implementer the gate-runner block to fix; re-verify. Two
  failed rounds on the same check → stop and ask the user.

**4c. Record** — dispatch `tracker-clerk` "mode: record-task" with the task path and the DONE block,
`run_in_background: true`; continue to the next task. Before the *next* clerk dispatch, make sure
the previous one finished (one writer on brain at a time).

Print one line per task: `✓ <id> <title> · <sha> · gate GREEN (<N> ran)`.

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

Fix loop: dispatch **one** `task-implementer` with `FIX` = all 🚨 + the ⚠️ worth fixing (note the
rest consciously), then `gate-runner`, then re-dispatch **only the reviewers that raised a 🚨** as
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
   - **Changes needed** → their feedback goes to a `task-implementer` FIX batch (same branch, same
     PR), then Step 4b–5 for the delta; the clerk records it.
   - **Hold** → leave the PR open.

**Never** merge without an explicit Approve. **Never** mark `verified` what the user has not
confirmed. **Never** merge a backend phase into `Sentinel` `main`.

## Chat output (binding)
The user sees a terminal. Digest, never transcript: verdict first, one line per finding/task, 🚨/⚠️
only, ≤10 findings, no pasted subagent output, no code blocks except the checklist. Detail on request.
