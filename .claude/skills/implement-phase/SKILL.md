---
name: implement-phase
description: "Sentinel Phase 2 build orchestrator. Implements ONE whole phase end-to-end — identifies where we are, rebuilds full context (summarizing prior work), locks onto the architecture, then iterates task-by-task to a green phase, handing off to specialist subagents for context, architecture, code, and safety. Closes by asking the user to verify the phase works. Trigger: /implement-phase"
trigger: /implement-phase
---

# /implement-phase

The single build-time driver for Sentinel Phase 2. It owns **one phase at a time** and
reaches the phase goal through **iteration + handoffs** to a small team of specialist
subagents. You (the orchestrator) plan, sequence, edit code, and run gates; the subagents
each do one thing well and hand their result back to you.

> **This replaces `/sentinel-build` + `/phase-gate` + `/sentinel-planner`.** There is no
> separate task command and no separate gate command — a phase is planned, built, reviewed,
> and signed off inside this one loop.

## Core principles (do not violate)

- **Rebuild full context every run.** Never assume memory of prior phases. Summarize what's
  already done from the tracker + git, so each invocation starts from ground truth.
- **Architecture is law.** Everything you build conforms to `ARCHITECTURE.md` for the active
  repo. If the spec and the architecture disagree, **halt and ask** — never guess.
- **Iterate to the goal.** Track the phase's tasks as a live goal list (TodoWrite). Loop each
  task until its quality gate is green before moving on. The phase is done only when *all*
  its tasks are green.
- **Handoffs, not heroics.** Delegate context, architecture distillation, and review to the
  specialist subagents (below). You integrate their outputs; you don't re-do their jobs.
- **Read sections, not files.** `python scripts/arch.py <doc> <§...>` prints one architecture
  section (~1-3K tokens); `Read` on `architecture/*.md` costs 21-24K for the same content and
  is a defect. `arch.py <doc> --list` when you don't know the ref, `arch.py --map` for
  concern → file+§. **Never re-read what a subagent already handed you** — the context brief
  carries the task specs and the distilled contract carries the architecture. Re-reading the
  source is the single most common way this loop wastes a phase's budget.
- **Ask when unsure. Halt when blocked.** Ambiguity in a task or architecture → stop and ask.
  Missing prerequisite (tool, key, upstream task not verified) → write the blocker down, stop,
  do not partially build.
- **No Claude attribution — ever.** No `Co-Authored-By: Claude`, no "Generated with Claude
  Code" in any commit or PR, in any of the three repos. The user is sole author. (See
  CLAUDE.md Git Rule.)

## Reporting to the chat (binding — this is what the user actually sees)

Everything else in this skill happens in your context. The user sees a **terminal chat**, so
what you print is a **digest, never a transcript**.

- **Never paste a subagent's output.** The context brief and the architecture contract are
  working material for *you*. The user gets one line saying each landed.
- **Verdict first.** Their only question is "is it green?" — answer it on line 1, then show
  what is wrong.
- **One line per finding**, in the agents' house style: `<icon> <file:line>  <the defect>`.
  No paragraphs, no code blocks, no diff excerpts.
- **Merge the reviewers into ONE block.** Never print three reports back to back — the user
  does not care which agent found what, only what is broken.
- **🚨 and ⚠️ only.** Collapse every ℹ️ into a `+N notes` count. Cap at 10 printed findings.
- **Detail on request.** Close a findings block with `ask "why <n>" for detail`, and when they
  ask, `SendMessage` the reviewer that raised it instead of re-deriving it yourself.
- **No status narration.** Cut "Dispatching the warden…", "Now I'll review…", "Great, that
  passed!". Show the result, not the process.
- **Decisions you hand back for review get the same treatment** — the choice in one line, the
  options in one line each, your recommendation marked. Not an essay.

## The subagent team (handoff targets)

| Subagent | Role | You call it… |
|----------|------|--------------|
| `phase-context-builder` | The **contexter/summarizer** — reads the phase folder + STATE.md history + git log, returns a compact "where we are" brief summarizing prior completed work and this phase's shape. | **Step 1**, at the start of every run. |
| `architecture-warden` | The **architect** — `mode: distill` extracts the binding architecture constraints for this phase; `mode: review` checks the finished diff against spec + architecture. | **Step 2** (distill) and **Step 5** (review). |
| `code-reviewer` | The **code reviewer** — correctness, coding standards, style-match on the phase diff. | **Step 5**. |
| `safety-reviewer` | The **safety reviewer** — HITL gates, tool-call caps, destructive-action guards. | **Step 5**, for backend phases (or any diff touching tools/agents/orchestrator). |

Repo locations (you already know these — do not ask). **You run from `sentinel-brain`; all
three code repos are siblings:**
- **infra** → `../Sentinel-infra`
- **deployment** → `../Sentinel-deployment`
- **backend** → `../Sentinel` (`Keshav0375/Sentinel` — the `Sentinel` repo *is* the backend)

Never write code into `sentinel-brain`, and never write planning docs, agents or reports into
a code repo. Brain drives; the code repos stay clean.

## Branch model

**The integration branch differs per repo. Resolve it BEFORE you branch:**

| Category | Repo | Integration branch (branch from **and** PR into) |
|----------|------|--------------------------------------------------|
| infra | `../Sentinel-infra` | **`main`** |
| deployment | `../Sentinel-deployment` | **`main`** |
| backend | `../Sentinel` | **`release-phase-2`** |

```
infra / deployment          main ──►  dev/<cat>-phase-<M>-<slug>  ──PR──►  main

backend (Sentinel)   release-phase-2 ──┬──►  dev/backend-phase-<M>-<slug> ──PR──► release-phase-2
                                       └──────────────────────────────────────────►  main
                                              (ONE final merge, end of Phase 2)
```

- **Every phase branches fresh from its repo's integration branch**, pulled up to date first.
- Branch prefix is **`dev/`** — `ci.yml`'s branch-convention check accepts only
  `dev|feat|fix|refactor|ci|docs|test|chore|planning|ai|hotfix`.
- The phase PR targets that **same** integration branch.
- **In `Sentinel` only**, `guard-main-source.yml` enforces `release-phase-2 <- dev/*` and
  `main <- release-phase-2`. **A PR from `dev/*` straight to `Sentinel` `main` will be
  rejected** — never open one. `release-phase-2` → `main` happens once, at the end of Phase 2,
  and the user drives it. `Sentinel` `main` accepts nothing else.
- `Sentinel-infra` and `Sentinel-deployment` have **no release branch and no guard** — their
  `dev/*` PRs merge straight into their own `main`. Do not create a `release-phase-2` there.
- `planning/phase-2-e2e` is **retired** (merged to `Sentinel` `main` 2026-07-26). Never branch
  from it or PR to it.

**In `sentinel-brain` (the tracker):** commit straight to `main`. Brain has no CI, no branch
protection, and no release train — its history *is* the build log. One phase therefore produces
**one code PR** plus **tracker commits on brain `main`**. Push brain after each task so
`implementation/STATE.md` never lags the code.

---

## Usage

```
/implement-phase              # Build the current active phase to completion
/implement-phase <cat-phase>  # Build a specific phase, e.g. infra-2 or backend-4
/implement-phase status       # Report where we are + the phase's task states (no changes)
/implement-phase resume       # Resume the active phase from its last green task
```

---

## Step 0 — Locate ourselves

Read, in order:
1. `implementation/STATE.md` — current category/phase/branch/PR, blockers, ledger.
2. `implementation/TODO.md` — the 58-task master checklist + phase-gate locks.
3. The active category's `README.md` under `implementation/tasks/{infra,deployment,backend}/`.

Resolve the target phase:
- No arg → the first phase (category order infra → deployment → backend; then phase order)
  that has any `not-started`/`in-progress` task **and** whose predecessor phase is signed off.
- **Never enter a phase whose predecessor gate is unsigned.** If the previous phase is only
  `done-pending-review`, stop and tell the user to complete Step 6 sign-off on it first.
- Explicit `<cat-phase>` → that phase, but refuse (and explain) if it would skip a locked phase.

## Steps 1 + 2 — Context and architecture (dispatch BOTH in one message)

`phase-context-builder` and `architecture-warden` both need only the category + phase, which
Step 0 already resolved. Neither consumes the other's output, so **dispatch them in parallel
in a single message** — sequential dispatch doubles the wall-clock for no benefit.

## Step 1 — Rebuild context (handoff → `phase-context-builder`)

Dispatch `phase-context-builder` with the active category + phase. It returns a brief:
what prior phases delivered (summarized, not dumped), this phase's tasks and their specs in
one place, upstream dependencies + their status, and any standing blockers from STATE.md.
**Do this every run** — it is how we start from ground truth instead of stale memory.

**Print one line, not the brief:**
`ctx ✓ <cat> phase <M> · <N> tasks · deps ok · blockers: none`
Anything the brief flags under BLOCKERS or DRIFT gets its own 🚨 line and you halt.

## Step 2 — Lock onto the architecture (handoff → `architecture-warden` · `mode: distill`)

Dispatch `architecture-warden` in **distill** mode for this phase. It returns the exact
architecture sections, contracts (resource/env/endpoint/table/model names, tool I/O types,
Pydantic fields), and binding decisions this phase must honor. Keep this brief open — it is
your conformance contract for the whole phase.

**Print one line, not the contract:**
`arch ✓ §3.2, §3.4 · 11 contracts locked · conflicts: none`
The contract table is your working reference, not chat content. Conflicts get a 🚨 line each.

If the context brief or the architecture reveals ambiguity or a spec/arch conflict → **halt
and ask the user** before writing any code.

## Step 3 — Set the goal (TodoWrite) + branch

- Write one todo per task in the phase (this is the "goal" you iterate toward). Mark the first
  `in_progress`.
- Print a compact phase header so the user always sees the plan:
  ```
  ▶ <category> · phase <M> (<slug>)  —  <N> tasks
    goal:   <one line: what this phase delivers>
    repo:   <repo> (<local path>)
    branch: dev/<cat>-phase-<M>-<slug>
    tasks:  <K.1 …> · <K.2 …> · …
  ```
- Resolve the integration branch from the **Branch model** table above (`main` for
  infra/deployment, `release-phase-2` for backend), then branch off a fresh copy of it:
  ```
  git -C <repo> checkout <integration> && git -C <repo> pull
  git -C <repo> checkout -b dev/<cat>-phase-<M>-<slug>
  ```
  If that integration branch does not exist in the target repo, **stop and ask** — never
  substitute a different base, and never create an integration branch yourself.
- **No branch is needed in `sentinel-brain`** — tracker updates commit to brain `main`
  directly. Make sure brain is clean and pulled before you start.

## Step 4 — Iterate the phase, task by task

For each task in order, run this loop (the "keep-checking" loop):

1. **Prerequisite check** — tools present, keys present (per STATE.md blockers), upstream
   tasks `verified`, **and every STATE.md "Open Reconciliation" (R-item) that names this
   task or its phase is RESOLVED**. An open R-item is a decision the user owes you — a value
   you would otherwise silently invent (region, owner, repo name). If any is missing →
   **halt**: write a BLOCKED note into the task file, mirror it to STATE.md Blockers, set
   the task `blocked`, and STOP. Do not partially build, and never default an open R-item.
2. **Implement** strictly to the task Spec + the `architecture-warden` contract. Match the
   surrounding code's style. Do not exceed scope. Ambiguity or arch conflict → **halt and ask.**
   **Do not re-read the task file or the architecture** — Steps 1 and 2 already put both in
   your context. Re-read only if you hit something neither brief covered, and then pull the
   one section (`arch.py <doc> <§>`), never the file.
3. **Test** — add the unit + integration tests the task names.
4. **Quality gate** — `python ../Sentinel/scripts/quality_gate.py --repo <infra|deployment|backend> --path <repo>`.
   Red → fix and re-run. **Loop until green.** Green is mandatory before commit.
   - `RESULT: INCONCLUSIVE` is **not** green — nothing ran. Say so and stop; don't commit.
   - `PASS` with a `NOT verified (skipped)` line is a **partial** pass. Report exactly which
     checks were skipped and why; never present it as a clean gate.
   - If the task added a `tests/` package that isn't in `quality_gate.py`'s `MATRIX`, its tests
     never ran — add the path to `MATRIX` in the same commit.
5. **Commit** — one task = one commit, conventional prefix (`feat|fix|refactor|test|docs`).
   **No Claude attribution.** Author is the user.
6. **Record** — fill the task file's Report / Tests / How to Verify, set status
   `done-pending-review`, update its TODO.md cell, mark its todo `completed`, advance to the next.

Never skip step 1 or step 4.

## Step 5 — Review the finished phase (handoffs → reviewers)

When every task is `done-pending-review` + green, run the review team over the whole phase diff
— all three in **one** dispatch, in parallel, since none depends on another:

1. `architecture-warden` · `mode: review` — spec + architecture conformance.
2. `code-reviewer` — correctness + standards.
3. `safety-reviewer` — **only** for backend phases or any diff touching tools/agents/orchestrator.

**Relay them as ONE merged block — never three reports back to back.** Verdicts on line 2,
then every 🚨 and ⚠️ from all three reviewers on one line each, blockers first, deduped
(two reviewers flagging the same line = one line). Notes collapse to a count:

```
▪ review · infra phase 2 — 2 blockers, 1 warning
  arch ✗ 2 · code ✓ LGTM · safety — n/a

🚨 modules/keyvault/main.tf:23  soft-delete off — §3.4 requires 90d
🚨 modules/acr/main.tf:11       sku Basic — §3.2 says Standard
⚠️ modules/aks/main.tf:64       node pool max_count unset — unbounded scale
+4 notes · ask "why 2" for detail
```

Clean phase → two lines, nothing more:
```
▪ review · infra phase 2 — clean
  arch ✓ CONFORMS · code ✓ LGTM · safety ✓ SAFE
```

Then fix: every 🚨 BLOCKER is resolved before proceeding (loop back into Step 4 for fixes on
the same branch); ⚠️ findings get fixed or consciously noted. When you re-run the reviewers
after fixes, print **only the delta** — what cleared and what is still open — not the whole
block again. If the user asks about a finding, `SendMessage` the reviewer that raised it;
do not re-derive it. If a reviewer surfaces a real gap the spec missed, raise it with the
user in one line rather than silently expanding scope.

## Step 6 — Close the phase (human verification — the gate)

1. Push the branch and open the PR **to the repo's integration branch** —
   `gh pr create --base main` for infra/deployment, `gh pr create --base release-phase-2` for
   backend (never `--base main` in `Sentinel`):
   - Title: `<cat> phase <M> — <phase name>`.
   - Body: one bullet per task (with commit subject) + the aggregated **How to Verify** steps.
     **No Claude attribution in the body.** If `gh`/remote is unavailable, say so and give the
     manual push/PR commands — never fabricate a PR URL.
2. **Write the phase report** — `reports/<cat>-phase-<M>.md` from
   `implementation/_templates/phase-report-template.md`. Short: what shipped, what it does,
   what it unblocks, what is still blocked. Commit it to brain `main` with the tracker updates.
3. Present the **"see it working" checklist** — this is the one thing the user acts on, so it
   is the one thing that gets space. Still capped: **one line per task** for what shipped, then
   the exact commands/URLs/UI steps to confirm it, ordered top-to-bottom, **copy-pasteable and
   nothing else**. No recap of the build, no explanation of what each command does. Anything
   deferred or BLOCKED gets its own 🚨 line (e.g. infra that needs a live Azure account) —
   never bury it in prose and never present partial work as complete.
4. **Ask the user to verify** with `AskUserQuestion` — "Does <phase> work as expected?":
   - **Approve & merge** — verified → merge the code PR **into that repo's integration branch**
     (`gh pr merge --squash --delete-branch` unless they prefer a merge commit), mark every task
     `verified` (task files + TODO cells ✅), append a row to the Phase Gate Ledger in
     `implementation/STATE.md`, unlock the next phase (drop its 🔒), push brain, state what's next.
     **Never merge a backend phase into `Sentinel` `main`** — `release-phase-2` → `main` is a
     single, separate merge at the end of Phase 2 and the user drives it. Infra and deployment
     phases *do* merge into their own `main`; that is their integration branch.
   - **Changes needed** — record their feedback into the relevant task(s) (`in_progress`) +
     STATE.md, do NOT merge, loop back to Step 4; the same PR updates as fix commits land.
   - **Hold** — leave the PR open, don't merge.

**Never** merge without an explicit Approve. **Never** mark a phase `verified` the user hasn't
confirmed with their own eyes. **Never** add Claude as a contributor to any commit, PR, or
merge commit.
