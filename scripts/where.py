#!/usr/bin/env python3
"""Cheap phase locator for /implement-phase Step 0.

Step 0 used to `Read` STATE.md + TODO.md + the category README — ~9.6K tokens that then
sit in the orchestrator's context for the whole session and get re-sent every turn. All
Step 0 actually needs is: which phase is next, is its predecessor signed off, what is
open against it, and where the repo is. This prints exactly that, in ~350 tokens.

    python3 scripts/where.py           # resolve the active phase
    python3 scripts/where.py infra-4   # locate a named phase
    python3 scripts/where.py --json    # same, machine-readable
    python3 scripts/where.py --all     # every phase + every open blocker (/progress)

WAVES is the phase's open tasks as a dependency graph, in layers: every task in a wave
depends only on tasks in earlier waves (or already built ones), so /implement-phase can
build a whole wave in parallel. Edges come from each task file's `Depends on` row —
`[[task-N-slug]]` links that name a task file of the SAME phase; cross-phase links are
already ordered by the phase sequence and are ignored. A task file without a `Depends on`
row depends on every earlier task (safe: sequential). A cycle is never guessed through:
its tasks run one per wave in id order and a CYCLE line names them.

Everything else — prior-phase summaries, task specs, deps — comes from
`phase-context-builder`. Do not Read STATE.md or TODO.md in the orchestrator.

Exit code 0 = safe to enter the phase; 1 = halt (gate unsigned, would skip work, or
nothing to build).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "implementation" / "STATE.md"
TODO = ROOT / "implementation" / "TODO.md"

CATEGORY_ORDER = ["infra", "deployment", "backend"]
REPO = {
    "infra": "../Sentinel/infra",  # monorepo subdir since infra phase 7 (2026-10-25)
    "deployment": "../Sentinel-deployment",
    "backend": "../Sentinel",
}
INTEGRATION = {"infra": "main", "deployment": "main", "backend": "main"}  # release-phase-2 frozen 2026-10-25

DONE = {"✅"}                                              # verified
OPEN_STATUS = {"⬜", "\U0001f535", "⛔", "\U0001f7e1"}  # not-started/in-progress/blocked/pending-review


# The tracker is written for humans (emoji); this output is read by a model on a cp1252
# console. ASCII tokens survive the console AND cost ~1 token instead of ~3.
GLYPH = {
    "✅": "ok", "⬜": "todo", "\U0001f535": "wip",
    "⛔": "blocked", "\U0001f7e1": "review", "\U0001f512": "locked",
}


def ascii_status(glyph: str) -> str:
    return GLYPH.get(glyph, glyph)


def flatten(text: str) -> str:
    """Strip emoji / box glyphs so the line prints on any console."""
    return re.sub(r"[^\x20-\x7e]", lambda m: GLYPH.get(m.group(), " "), text).strip()


def _cells(line: str) -> list[str]:
    # \\| is an ESCAPED pipe inside a cell, not a column break. Task 6.3's title
    # is `Database `shared` \\| `dedicated``, and splitting on the raw character turned
    # one row into two malformed ones -- the task rendered as a broken line and,
    # worse, went uncounted, so the verified total read one short of the tracker
    # for the whole of infra phase 6.
    SENTINEL = "\u0001"
    line = line.strip().strip("|").replace(r"\|", SENTINEL)
    return [c.strip().replace(SENTINEL, "|") for c in line.split("|")]


def parse_todo() -> list[dict]:
    """-> [{category, phase, name, branch, gate, tasks:[{id,title,status}]}] in file order."""
    phases: list[dict] = []
    category = None
    current = None
    for raw in TODO.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^## Category \d+ — sentinel-(\w+)", raw)
        if m:
            category = m.group(1)
            continue
        m = re.match(
            r"^### Phase (\d+) — (.+?)\s+·\s+branch `([^`]+)`\s+·\s+Gate:\s*(\S+)",
            raw,
        )
        if m and category:
            current = {
                "category": category,
                "phase": int(m.group(1)),
                "name": m.group(2).strip(),
                "branch": m.group(3),
                "gate": m.group(4),
                "tasks": [],
            }
            phases.append(current)
            continue
        if current is not None and re.match(r"^\|\s*\d+\.\d+\s*\|", raw):
            c = _cells(raw)
            if len(c) >= 4:
                link = re.search(r"\]\(([^)]+\.md)\)", c[2])
                current["tasks"].append({
                    "id": c[0], "title": c[1], "status": c[3],
                    "file": str(TODO.parent / link.group(1)) if link else None,
                })
    return phases


def parse_state() -> dict:
    """Pull only the live rows: position, OPEN blockers, OPEN reconciliations.

    Closed items (struck through or ticked) are history and live in history.md — they are
    deliberately not returned, because the loop never needs them.
    """
    text = STATE.read_text(encoding="utf-8")
    pos: dict[str, str] = {}
    for m in re.finditer(r"^\|\s*\*\*(.+?)\*\*\s*\|\s*(.+?)\s*\|$", text, re.M):
        pos[m.group(1)] = m.group(2)

    def section(head: str) -> str:
        m = re.search(rf"^## {re.escape(head)}.*?$(.*?)(?=^## |\Z)", text, re.M | re.S)
        return m.group(1) if m else ""

    def open_rows(head: str) -> list[dict]:
        """-> [{label, raw}]. `raw` keeps the Blocks/Affects columns so the phase filter
        can see which task an item gates; `label` is what we actually print."""
        out = []
        for line in section(head).splitlines():
            if not re.match(r"^\|\s*\*{0,2}[BR]\d+", line):
                continue
            if "✅" in line or "~~" in line:
                continue
            c = _cells(line)
            if len(c) >= 3:
                out.append({"label": f"{c[0]} - {c[1]} [blocks: {c[2]}]", "raw": line})
        return out

    return {
        "position": pos,
        "blockers": open_rows("Blockers"),
        "reconciliations": open_rows("Open Reconciliations"),
    }


def task_deps(tasks: list[dict]) -> dict[str, set[str]]:
    """-> {task id: ids of SAME-phase tasks it depends on}, from each file's `Depends on` row."""
    by_slug = {Path(t["file"]).stem: t["id"] for t in tasks if t.get("file")}
    deps: dict[str, set[str]] = {}
    for i, t in enumerate(tasks):
        path = Path(t["file"]) if t.get("file") else None
        row = None
        if path and path.is_file():
            row = re.search(r"^\|\s*\*\*Depends on\*\*\s*\|(.*)\|\s*$",
                            path.read_text(encoding="utf-8"), re.M)
        if row is None:  # no declared deps -> after everything before it
            deps[t["id"]] = {x["id"] for x in tasks[:i]}
            continue
        deps[t["id"]] = {by_slug[s] for s in re.findall(r"\[\[([\w-]+)\]\]", row.group(1))
                         if s in by_slug and by_slug[s] != t["id"]}
    return deps


def waves(tasks: list[dict]) -> tuple[list[list[str]], list[str]]:
    """-> (layers of open task ids, ids caught in a dependency cycle).

    Tasks already built (pending review or verified) satisfy their dependents and are
    left out of the layers.
    """
    built = {t["id"] for t in tasks if t["status"] in DONE | {"\U0001f7e1"}}
    todo = [t["id"] for t in tasks if t["id"] not in built]
    deps = task_deps(tasks)
    layers: list[list[str]] = []
    have = set(built)
    while todo:
        ready = [i for i in todo if deps.get(i, set()) <= have]
        if not ready:  # cycle: never guess an order -> one at a time, id order
            cyc = list(todo)
            layers.extend([i] for i in cyc)
            return layers, cyc
        layers.append(ready)
        have |= set(ready)
        todo = [i for i in todo if i not in have]
    return layers, []


def _key(p: dict) -> tuple[int, int]:
    return (CATEGORY_ORDER.index(p["category"]), p["phase"])


def resolve(phases: list[dict], want: str | None) -> tuple[dict | None, str | None]:
    """-> (phase, refusal). Active phase = first phase with any unfinished task."""
    ordered = sorted(phases, key=_key)
    unfinished = [p for p in ordered if any(t["status"] in OPEN_STATUS for t in p["tasks"])]

    if want:
        m = re.match(r"^(\w+)[-_ ](\d+)$", want.strip())
        if not m:
            return None, f"cannot parse phase ref {want!r} — expected e.g. infra-4"
        cat = {"deploy": "deployment"}.get(m.group(1), m.group(1))
        num = int(m.group(2))
        target = next((p for p in ordered if p["category"] == cat and p["phase"] == num), None)
        if target is None:
            return None, f"no such phase: {want}"
        skipped = [p for p in unfinished if _key(p) < _key(target)]
        if skipped:
            names = ", ".join(f"{p['category']}-{p['phase']}" for p in skipped)
            return target, f"would skip unfinished phase(s): {names}"
        return target, None

    if not unfinished:
        return None, "every phase is verified — nothing to build"
    return unfinished[0], None


def predecessor(phases: list[dict], p: dict) -> dict | None:
    ordered = sorted(phases, key=_key)
    idx = ordered.index(p)
    return ordered[idx - 1] if idx else None


def overview(phases: list[dict], state: dict) -> int:
    """`--all`: the whole tracker in ~30 lines, for /progress. Counts are computed, never
    hardcoded — the task and phase totals have changed before (58 → 72 tasks)."""
    verified = sum(1 for p in phases for t in p["tasks"] if t["status"] in DONE)
    total = sum(len(p["tasks"]) for p in phases)
    merged = sum(1 for p in phases if p["gate"] in DONE)
    active, _ = resolve(phases, None)
    print(f"COUNT   {verified}/{total} tasks verified · {merged}/{len(phases)} phases signed")
    for p in sorted(phases, key=_key):
        done = sum(1 for t in p["tasks"] if t["status"] in DONE)
        mark = "  <- NEXT" if p is active else ""
        print(f"  {p['category'] + '-' + str(p['phase']):<13}{ascii_status(p['gate']):<8}"
              f"{done}/{len(p['tasks']):<4}{flatten(p['name'])[:60]}{mark}")
    print("BLOCKERS" if state["blockers"] else "BLOCKERS: none")
    for b in state["blockers"]:
        print(f"  !! {flatten(b['label'])[:140]}")
    print("OPEN-R" if state["reconciliations"] else "OPEN-R: none")
    for r in state["reconciliations"]:
        print(f"  !! {flatten(r['label'])[:140]}")
    return 0


def main() -> int:
    try:  # Windows consoles default to cp1252 and would die on a tracker glyph
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):  # pragma: no cover - non-reconfigurable stream
        pass
    ap = argparse.ArgumentParser(description="Locate the phase /implement-phase should build")
    ap.add_argument("phase", nargs="?", help="e.g. infra-4, backend-2 (default: active phase)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--all", action="store_true", help="one line per phase + every open blocker")
    a = ap.parse_args()

    phases = parse_todo()
    state = parse_state()
    if a.all:
        return overview(phases, state)
    target, refusal = resolve(phases, a.phase)

    if target is None:
        print(f"HALT  {refusal}")
        return 1

    prev = predecessor(phases, target)
    cat, num = target["category"], target["phase"]
    verified = sum(1 for p in phases for t in p["tasks"] if t["status"] in DONE)
    total = sum(len(p["tasks"]) for p in phases)
    gate_ok = prev is None or prev["gate"] in DONE

    # Only the blockers / R-items whose Blocks/Affects column names this phase can halt it.
    # Match on `<cat> <M>.<n>` or a bare `<M>.<n>` — "infra" alone would drag in every
    # infra-wide blocker regardless of phase.
    pat = re.compile(rf"(?:{cat}\s+)?\b{num}\.\d\b", re.I)
    mine_b = [b for b in state["blockers"] if pat.search(b["raw"])]
    mine_r = [r for r in state["reconciliations"] if pat.search(r["raw"])]
    layers, cycle = waves(target["tasks"])

    if a.json:
        print(json.dumps({
            "category": cat, "phase": num, "name": target["name"],
            "branch": target["branch"], "repo": REPO[cat],
            "integration": INTEGRATION[cat], "gate_unlocked": gate_ok,
            "predecessor": f"{prev['category']}-{prev['phase']}" if prev else None,
            "predecessor_gate": prev["gate"] if prev else None,
            "verified": verified, "total": total,
            "tasks": [{k: v for k, v in t.items() if k != "file"} for t in target["tasks"]],
            "waves": layers, "cycle": cycle,
            "blockers": [b["label"] for b in mine_b],
            "reconciliations": [r["label"] for r in mine_r],
            "refusal": refusal,
        }, ensure_ascii=False, indent=1))
        return 0 if gate_ok and not refusal else 1

    print(f"PHASE   {cat} phase {num} - {flatten(target['name'])}")
    print(f"REPO    {REPO[cat]} | branch {target['branch']} | PR into {INTEGRATION[cat]}")
    print(f"COUNT   {verified}/{total} tasks verified")
    if prev:
        warn = "" if gate_ok else "   !! UNSIGNED - do not enter this phase"
        print(f"PREV    {prev['category']}-{prev['phase']} gate "
              f"{ascii_status(prev['gate'])}{warn}")
    print("TASKS")
    for t in target["tasks"]:
        print(f"  {ascii_status(t['status']):<8}{t['id']}  {flatten(t['title'])[:88]}")
    if layers:
        print("WAVES   " + " | ".join(f"{n}: {' '.join(w)}" for n, w in enumerate(layers, 1)))
    if cycle:
        print(f"CYCLE   {' '.join(cycle)} - Depends-on rows loop; built one at a time in id order")
    print("BLOCKERS" if mine_b else "BLOCKERS: none")
    for b in mine_b:
        print(f"  !! {flatten(b['label'])[:140]}")
    print("OPEN-R" if mine_r else "OPEN-R: none")
    for r in mine_r:
        print(f"  !! {flatten(r['label'])[:140]}")
    if refusal:
        print(f"REFUSE  {refusal}")
    elsewhere = len(state["blockers"]) - len(mine_b)
    if elsewhere > 0:
        print(f"NOTE    {elsewhere} blocker(s) open elsewhere, none gating this phase")
    return 0 if gate_ok and not refusal else 1


if __name__ == "__main__":
    sys.exit(main())
