---
description: Run the Sentinel quality gate — the exact body CI runs — and fix what it reports
allowed-tools: Read, Write, Edit, Bash, Grep
model: sonnet
---

Run the category-aware quality gate and drive it to green. **This is the same body CI and
`/implement-phase` Step 4 run**, so local "green" and pipeline "green" mean the same thing —
never substitute an ad-hoc `ruff`/`pytest` invocation for it.

1. Pick the repo from where the changed files live. You run from `sentinel-brain`; the gate
   script and all three code repos are siblings, so **always pass `--path`**:

   ```bash
   python ../Sentinel/scripts/quality_gate.py --repo backend    --path ../Sentinel
   python ../Sentinel/scripts/quality_gate.py --repo infra      --path ../Sentinel-infra
   python ../Sentinel/scripts/quality_gate.py --repo deployment --path ../Sentinel-deployment
   ```
   Add `--fast` to skip the slow/network checks while iterating; the **full** run must be green
   before you report done.

2. Fix every ❌ and re-run until `RESULT: PASS`. Formatting/lint failures: apply
   `ruff check --fix` / `ruff format` and re-run. Type and test failures: fix the cause, not the
   assertion.

3. Read the ⏭️ SKIPPED lines — they are not free passes:
   - *"<tool> not on PATH"* → say so explicitly in your summary; that check did **not** run.
   - *"no such path yet: …"* → expected mid-build, but if a test file you just wrote sits in a
     pruned path, the gate never ran it. Add the directory to `MATRIX` in
     `../Sentinel/scripts/quality_gate.py` in the same commit.

4. **Backend only** — after any change to `pyproject.toml`, dependencies, imports, or
   module-level code, confirm the app still boots (CLAUDE.md, non-negotiable). Run this
   **from `../Sentinel`**: `poetry lock && poetry install` if deps changed, then
   `poetry run sentinel serve`. A green test suite does not prove the import chain is intact.

5. Print a compact summary: one line per check (✅ / ❌ / ⏭️), what you fixed, and anything
   that was skipped rather than passed.
