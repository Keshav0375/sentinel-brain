# Phase reports

One short, user-facing report per completed phase — written at the gate, before the user is
asked to sign off. Named `<category>-phase-<M>.md` (e.g. `infra-phase-1.md`).

These are the **summary** layer. The detailed per-task record (spec, what actually changed,
deviations, test results, commit SHAs) lives in the task file itself under
`implementation/tasks/<category>/phase-*/task-*.md`. Reports link to those; they do not repeat them.

Template: `implementation/_templates/phase-report-template.md`.

A report is honest or it is worthless. If a task was deferred, a check was skipped rather than
passed, or a verification step needs a resource that does not exist yet, the report says so.

| Report | Phase | Gate |
|--------|-------|------|
| _none yet_ | — | — |
