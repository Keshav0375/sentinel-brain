#!/usr/bin/env python3
"""Section-addressed reader for the Sentinel architecture docs.

The architecture files total ~270 KB (~70K tokens). Almost every question needs one
section of one file. `Read`ing the file to find that section costs 20-24K tokens; this
prints the section alone, typically 0.3-2K.

Line offsets are computed at call time, never stored, so nothing here goes stale when a
doc is edited.

    arch.py infra 3.2 3.3        one or more sections, in order
    arch.py backend 4            a whole section, subsections included
    arch.py infra --list         table of contents + token cost per section
    arch.py decisions R6         the decision entry(s) matching a keyword
    arch.py decisions --list     all 61 entries, one line each
    arch.py --map                concern -> file+section (architecture/README.md §4)
    arch.py --list               every doc's top-level TOC

Docs: infra | backend | deployment | decisions | index
"""
from __future__ import annotations

import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = {
    "infra": "architecture/infra.md",
    "backend": "architecture/backend.md",
    "deployment": "architecture/deployment.md",
    "decisions": "architecture/decisions.md",
    "index": "architecture/README.md",
}
NUM = re.compile(r"^(\d+(?:\.\d+)*)[.\s]")
HEAD = re.compile(r"^(#{1,6})\s+(.*)")


def _lines(doc: str) -> list[str]:
    path = os.path.join(ROOT, DOCS[doc])
    if not os.path.exists(path):
        sys.exit("no such doc file: %s" % path)
    with open(path, encoding="utf-8") as fh:
        return fh.read().split("\n")


def headings(doc: str) -> list[dict]:
    """Every heading outside a fenced code block, with its full span.

    Fence-awareness is load-bearing: these docs embed Terraform and shell whose `#`
    comments would otherwise parse as headings and shred the section map.
    """
    lines = _lines(doc)
    fence = False
    raw: list[tuple[int, int, str]] = []
    for i, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            fence = not fence
            continue
        if fence:
            continue
        m = HEAD.match(line)
        if m:
            raw.append((i + 1, len(m.group(1)), m.group(2).strip()))

    out: list[dict] = []
    for j, (start, level, title) in enumerate(raw):
        end = len(lines)
        for k in range(j + 1, len(raw)):
            if raw[k][1] <= level:      # span runs to the next same-or-higher heading,
                end = raw[k][0] - 1     # so asking for §3 includes §3.1 .. §3.8
                break
        num = NUM.match(title)
        out.append({
            "start": start, "end": end, "level": level, "title": title,
            "num": num.group(1) if num else None,
            "text": "\n".join(lines[start - 1:end]).rstrip(),
        })
    return out


def emit(doc: str, h: dict) -> None:
    print("== %s L%d-%d ==" % (DOCS[doc], h["start"], h["end"]))
    print(h["text"])
    print()


def cmd_section(doc: str, refs: list[str]) -> int:
    hs = headings(doc)
    missed: list[str] = []
    for ref in refs:
        hit = [h for h in hs if h["num"] == ref]
        if not hit:                                    # fall back to a title match
            low = ref.lower()
            hit = [h for h in hs if low in h["title"].lower()]
        if not hit:
            missed.append(ref)
            continue
        for h in hit:
            emit(doc, h)
    if missed:
        print("NOT FOUND in %s: %s" % (doc, ", ".join(missed)), file=sys.stderr)
        print("run: arch.py %s --list" % doc, file=sys.stderr)
        return 1
    return 0


def cmd_list(doc: str, depth: int) -> None:
    total = os.path.getsize(os.path.join(ROOT, DOCS[doc]))
    print("== %s | %.0f KB | ~%.0fK tok if read whole ==" % (DOCS[doc], total / 1024.0, total / 4000.0))
    for h in headings(doc):
        if h["level"] > depth:
            continue
        size = len(h["text"])
        print("  %s%-52s L%-5d-%-5d ~%.1fK tok" % (
            "  " * (h["level"] - 1), h["title"][:52], h["start"], h["end"], size / 4000.0))
    print()


def cmd_decisions(keywords: list[str]) -> int:
    """Decision entries are `### YYYY-MM-DD: title`; match on keyword, not number."""
    hs = [h for h in headings("decisions") if h["level"] == 3]
    found = False
    for h in hs:
        blob = h["text"].lower()
        if all(k.lower() in blob for k in keywords):
            emit("decisions", h)
            found = True
    if not found:
        print("no decision entry matching: %s" % " ".join(keywords), file=sys.stderr)
        print("run: arch.py decisions --list", file=sys.stderr)
        return 1
    return 0


def cmd_map() -> None:
    for h in headings("index"):
        if h["num"] == "4":
            emit("index", h)
            return
    print("architecture/README.md has no section 4", file=sys.stderr)


def main() -> int:
    # Windows consoles default to cp1252, which cannot encode the arrows, §, ≠ and box
    # glyphs the architecture docs are full of — every invocation died on a UnicodeEncodeError
    # part-way through, so the caller fell back to `Read`ing the whole 21-24K-token file.
    # That defeated the entire point of this reader. Force UTF-8 before printing anything.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):  # pragma: no cover - non-reconfigurable stream
        pass
    ap = argparse.ArgumentParser(prog="arch.py", add_help=True,
                                 description="Read one architecture section instead of a whole file.")
    ap.add_argument("doc", nargs="?", help="infra | backend | deployment | decisions | index")
    ap.add_argument("refs", nargs="*", help="section numbers (3.2) or decision keywords (R6)")
    ap.add_argument("--list", action="store_true", help="table of contents with token cost")
    ap.add_argument("--depth", type=int, default=3, help="heading depth for --list (default 3)")
    ap.add_argument("--map", action="store_true", help="concern -> file+section map")
    a = ap.parse_args()

    if a.map:
        cmd_map()
        return 0
    if a.doc is None:
        if a.list:
            for d in DOCS:
                cmd_list(d, 2)
            return 0
        ap.print_help()
        return 2
    if a.doc not in DOCS:
        print("unknown doc %r — expected one of: %s" % (a.doc, ", ".join(DOCS)), file=sys.stderr)
        return 2
    if a.list:
        cmd_list(a.doc, a.depth)
        return 0
    if not a.refs:
        print("give at least one section ref, or --list", file=sys.stderr)
        return 2
    if a.doc == "decisions":
        return cmd_decisions(a.refs)
    return cmd_section(a.doc, a.refs)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:  # `arch.py ... | head` is a normal way to sample a section
        sys.stderr.close()
        sys.exit(0)
