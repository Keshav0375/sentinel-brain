# {category} phase {M} — {phase name}

<!-- Written at the phase gate, saved as reports/{cat}-phase-{M}.md.
     This is the USER-FACING summary. Short. Scannable. No essays.
     The blow-by-blow detail already lives in each task file's Report section —
     link to it, don't repeat it. Target: one screen. -->

| | |
|---|---|
| **Repo** | `Sentinel` \| `Sentinel-deployment` \| `Sentinel-infra` |
| **Branch → PR** | `dev/{cat}-phase-{M}-{slug}` → `release-phase-2` · PR #N — `<paste the PR url>` |
| **Tasks** | N/N green |
| **Gate** | ⬜ awaiting sign-off \| ✅ verified {date} |

## What shipped

<!-- One line per task: what it is, in plain language. Not the commit subject. -->

- **{task id} {title}** — {what it is and what it does, one sentence}.
- …

## What this unblocks

<!-- Why the next phase can now start. Name the contracts this phase left behind
     that downstream tasks consume (a table, an endpoint, an action, an output). -->

- …

## See it working

<!-- The exact steps the user runs. Copy-pasteable. Ordered. No hand-waving. -->

1. ```bash
   {command}
   ```
   → expect: {observable result}
2. …

## Not done / blocked

<!-- Be explicit. A phase gate on partial work is worse than no gate.
     If nothing is outstanding, write "Nothing — the phase is complete." -->

- **{item}** — blocked on {blocker id + what is missing}, owner {who}.
- **Skipped checks:** {any quality-gate check that was SKIPPED rather than passed}.

## Decisions made during the build

<!-- Only decisions a future reader would be surprised by, with the one-line why.
     Anything that changed the architecture must ALSO be logged in
     architecture/decisions.md — link it here. -->

- …
