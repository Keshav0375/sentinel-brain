#!/usr/bin/env python3
"""PreToolUse guard for sentinel-brain sessions. Exit 2 blocks the call; stderr tells Claude why.

Two rules that permission patterns alone cannot enforce:

1. archive/ is dead Phase-1 design. `Read(archive/**)` in settings stops the Read tool, but
   not `cat archive/…`, `grep -r … archive`, `git show HEAD:archive/…`, Grep or Glob.
2. No Claude attribution in any commit or PR, in any of the four repos — including commit
   messages passed with -F, PR bodies passed with --body-file, and GitHub MCP writes.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

BRAIN = Path(os.environ.get("CLAUDE_PROJECT_DIR", Path(__file__).resolve().parents[2]))
ARCHIVE = (BRAIN / "archive").resolve()

ATTRIBUTION = re.compile(
    r"co-authored-by:\s*claude|generated with \[?claude code|noreply@anthropic\.com", re.I
)
# `archive/` as a path segment, or a bare `archive` path argument. For grep-likes the word is
# usually the search PATTERN, so only a trailing `archive` (the path position) counts.
ARCHIVE_PATH = re.compile(r"(?<![\w.-])(?:\./|sentinel-brain/)?archive/")
ARCHIVE_ARG = re.compile(
    r"\b(?:ls|cat|head|tail|less|more|bat|find|fd|tree|du|open|code)\b[^|;&]*\s(?:\./)?archive\b"
    r"|\b(?:grep|rg|ag)\b(?:\s+-\S+)*\s+\S+[^|;&]*\s(?:\./)?archive\s*(?:$|[|;&])"
)
FILE_FLAG = re.compile(r"(?:-F|--file|--body-file)[=\s]+(['\"]?)([^\s'\"]+)\1")


def block(msg: str) -> None:
    print(f"Blocked by sentinel-brain guard: {msg}", file=sys.stderr)
    sys.exit(2)


def in_archive(path: str | None, cwd: str) -> bool:
    if not path:
        return False
    p = Path(path)
    if not p.is_absolute():
        p = Path(cwd) / p
    try:
        return p.resolve().is_relative_to(ARCHIVE)
    except (OSError, ValueError):
        return False


def check_bash(cmd: str, cwd: str) -> None:
    writes_history = re.search(r"\bgit\s+commit\b|\bgh\s+(?:pr|release)\s+(?:create|edit|merge)\b|\bgh\s+api\b", cmd)
    if writes_history:
        text = cmd
        for _, f in FILE_FLAG.findall(cmd):
            fp = Path(f) if Path(f).is_absolute() else Path(cwd) / f
            if fp.is_file():
                text += "\n" + fp.read_text(encoding="utf-8", errors="replace")
        if ATTRIBUTION.search(text):
            block("Claude attribution in a commit/PR. Keshav is sole author — remove the "
                  "Co-Authored-By / 'Generated with Claude Code' line (CLAUDE.md, ground rule 5).")
        if re.search(r"\bgit\s+commit\b", cmd):
            return  # a commit message may legitimately mention the word archive
    if ARCHIVE_PATH.search(cmd) or ARCHIVE_ARG.search(cmd):
        block("archive/ is the dead Phase-1 design — never read it. Use architecture/ "
              "(python3 scripts/arch.py) instead.")


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return
    tool = data.get("tool_name", "")
    ti = data.get("tool_input") or {}
    cwd = data.get("cwd") or str(BRAIN)

    if tool == "Bash":
        check_bash(ti.get("command", ""), cwd)
    elif tool in ("Read", "Edit", "Write", "NotebookEdit"):
        if in_archive(ti.get("file_path") or ti.get("notebook_path"), cwd):
            block("archive/ is the dead Phase-1 design — never read or edit it.")
    elif tool in ("Grep", "Glob"):
        if in_archive(ti.get("path"), cwd) or "archive/" in (ti.get("glob") or ti.get("pattern") or ""):
            block("archive/ is the dead Phase-1 design — search architecture/ instead.")
    elif tool.startswith("mcp__github__"):
        if ATTRIBUTION.search(json.dumps(ti)):
            block("Claude attribution in a GitHub write. Keshav is sole author.")


if __name__ == "__main__":
    main()
