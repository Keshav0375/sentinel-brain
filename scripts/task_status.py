#!/usr/bin/env python3
"""Flip one task's status in the tracker (TODO.md cell + task file) and mirror it to the board.

The orchestrator needs to move a task to in-progress the moment a build starts, without paying
for an agent dispatch or touching the tracker by hand. One deterministic command does it:

    python3 scripts/task_status.py deployment 1.1 in-progress
    python3 scripts/task_status.py backend 3.4 blocked --no-sync

Statuses: not-started · in-progress · blocked · done-pending-review · verified.
Does not commit — the next tracker-clerk commit picks the change up with the rest.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from where import ROOT, TODO  # noqa: E402

GLYPH = {"not-started": "⬜", "in-progress": "\U0001f535", "blocked": "⛔",
         "done-pending-review": "\U0001f7e1", "verified": "✅"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("category", choices=["infra", "deployment", "backend"])
    ap.add_argument("task", help="e.g. 1.1")
    ap.add_argument("status", choices=list(GLYPH))
    ap.add_argument("--no-sync", action="store_true", help="skip scripts/board_sync.py")
    a = ap.parse_args()

    lines = TODO.read_text(encoding="utf-8").splitlines(keepends=True)
    in_cat, hit = False, None
    for i, raw in enumerate(lines):
        if raw.startswith("## "):
            in_cat = bool(re.match(rf"^## Category \d+ — sentinel-{a.category}\b", raw))
        elif in_cat and re.match(rf"^\|\s*{re.escape(a.task)}\s*\|", raw):
            hit = i
            break
    if hit is None:
        print(f"HALT    no row {a.category} {a.task} in TODO.md")
        return 1
    row = lines[hit]
    lines[hit] = re.sub(r"\|[^|]*\|\s*$", f"| {GLYPH[a.status]} |\n", row.rstrip("\n") + "\n")
    TODO.write_text("".join(lines), encoding="utf-8")

    link = re.search(r"\]\((tasks/[^)]+\.md)\)", row)
    task_file = (TODO.parent / link.group(1)) if link else None
    if task_file and task_file.exists():
        text = task_file.read_text(encoding="utf-8")
        text, n = re.subn(r"(\|\s*\*\*Status\*\*\s*\|\s*)`[^`]*`", rf"\1`{a.status}`", text, count=1)
        if n:
            task_file.write_text(text, encoding="utf-8")
    print(f"STATUS  {a.category} {a.task} → {a.status} ({GLYPH[a.status]})"
          f" · {task_file.relative_to(ROOT) if task_file else 'task file not found'}")

    if not a.no_sync:
        out = subprocess.run([sys.executable, str(ROOT / "scripts" / "board_sync.py")],
                             capture_output=True, text=True)
        summary = [ln for ln in out.stdout.splitlines() if ln.startswith(("issues:", "project:"))]
        print("BOARD   " + (" · ".join(summary) if out.returncode == 0
                            else f"sync failed: {out.stderr.strip()[-200:]}"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
