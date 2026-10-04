#!/usr/bin/env python3
"""Mirror the brain tracker onto GitHub: issues in sentinel-brain + the Sentinel project board.

    Epic (one per category)  →  Phase issue (sub-issue)  →  Task issue (sub-issue)

TODO.md + the task files stay the single source of truth; this is a one-way mirror, so the
board can never disagree with the tracker. Idempotent: every issue carries a hidden marker
(`<!-- sentinel-sync:task:infra-1.1 -->`) and re-runs update in place — titles, bodies,
labels, open/closed, parents, project fields — creating only what is missing.

    python3 scripts/board_sync.py --dry-run     # show what would change, write nothing
    python3 scripts/board_sync.py               # sync issues + project
    python3 scripts/board_sync.py --no-project  # issues only (token lacks `project` scope)

Issues live in sentinel-brain (the control plane), never in the code repos. Needs `gh`
logged in with `repo` + `project` scopes.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from where import (  # noqa: E402
    CATEGORY_ORDER, DONE, INTEGRATION, ROOT, STATE, TODO, _cells, flatten, parse_state,
)

OWNER, REPO, PROJECT = "Keshav0375", "sentinel-brain", 4
BLOB = f"https://github.com/{OWNER}/{REPO}/blob/main/"
CODE_REPO = {"infra": "Sentinel-infra", "deployment": "Sentinel-deployment", "backend": "Sentinel"}
EPIC = {
    "infra": ("Infra", "Terraform estate — 7 modules + the Entra/OIDC identity plane"),
    "deployment": ("Deployment", "Target FastAPI app, deploy pipeline + 30 scenario branches"),
    "backend": ("Backend", "Multi-agent incident-response pipeline on AKS"),
}
LABELS = {
    "epic": ("5319e7", "Category epic"), "phase": ("1d76db", "Phase — one branch + one PR"),
    "task": ("0e8a16", "Task — one commit"), "infra": ("c5def5", "sentinel-infra"),
    "deployment": ("bfdadc", "sentinel-deployment"), "backend": ("fef2c0", "sentinel (backend)"),
    "blocked": ("b60205", "Blocked — see STATE.md"),
    "needs-attention": ("fbca04", "Shipped but not fully proven"),
}
# tracker glyph -> (board Status, extra label)
TASK_STATUS = {
    "✅": ("Done", None), "\U0001f7e1": ("In review", None), "\U0001f535": ("In progress", None),
    "⛔": ("In progress", "blocked"), "⚠️": ("In review", "needs-attention"),
    "⚠": ("In review", "needs-attention"),
}
TRACKER_WORD = {"✅": "✅ verified", "\U0001f7e1": "🟡 done-pending-review",
                "\U0001f535": "🔵 in-progress", "⛔": "⛔ blocked", "⬜": "⬜ not-started",
                "⚠️": "⚠️ shipped-but-unexercised", "⚠": "⚠️ shipped-but-unexercised"}
MARK = "<!-- sentinel-sync:{} -->"
MARK_RE = re.compile(r"<!-- sentinel-sync:(\S+) -->")
DRY = False


# ── gh plumbing ────────────────────────────────────────────────────────────────

def gh(args: list[str], payload: dict | None = None) -> dict | list | None:
    for attempt in range(5):
        p = subprocess.run(["gh", *args], input=json.dumps(payload) if payload else None,
                           capture_output=True, text=True)
        if p.returncode == 0:
            return json.loads(p.stdout) if p.stdout.strip() else None
        if "rate limit" in (p.stderr + p.stdout).lower():
            time.sleep(60 * (attempt + 1))
            continue
        raise RuntimeError(f"gh {' '.join(args[:3])} failed: {p.stderr.strip() or p.stdout[:400]}")
    raise RuntimeError("gh: rate-limited five times, giving up")


def gql(query: str, **variables) -> dict:
    out = gh(["api", "graphql", "--input", "-"], {"query": query, "variables": variables})
    if out.get("errors"):
        raise RuntimeError(json.dumps(out["errors"])[:600])
    return out["data"]


def rest(method: str, path: str, body: dict | None = None):
    return gh(["api", "-X", method, path, "--input", "-"] if body else ["api", "-X", method, path],
              body)


# ── desired state from the tracker ─────────────────────────────────────────────

def rewrite_links(md: str, src: Path) -> str:
    """Relative markdown links → absolute blob URLs, so they work inside an issue."""
    def fix(m: re.Match) -> str:
        text, target = m.group(1), m.group(2)
        if re.match(r"^(https?:|mailto:|#)", target):
            return m.group(0)
        path, _, anchor = target.partition("#")
        resolved = (src.parent / path).resolve()
        try:
            rel = resolved.relative_to(ROOT).as_posix()
        except ValueError:
            return m.group(0)
        return f"[{text}]({BLOB}{rel}{'#' + anchor if anchor else ''})"
    return re.sub(r"(?<!!)\[([^\]]*)\]\(([^)\s]+)\)", fix, md)


def clean_title(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("**", "").replace("`", "")).strip()


def parse_tracker() -> list[dict]:
    """-> phases with tasks, sections, ledger PRs. Richer than where.parse_todo()."""
    lines = TODO.read_text(encoding="utf-8").splitlines()
    phases, cat, cur = [], None, None
    for raw in lines:
        m = re.match(r"^## Category \d+ — sentinel-(\w+)", raw)
        if m:
            cat, cur = m.group(1), None
            continue
        if raw.startswith("## "):
            cat, cur = None, None
            continue
        m = re.match(r"^### Phase (\d+) — (.+?)\s+·\s+branch `([^`]+)`\s+·\s+Gate:\s*(\S+)", raw)
        if m and cat:
            cur = {"category": cat, "phase": int(m.group(1)), "name": m.group(2).strip(),
                   "branch": m.group(3), "gate": m.group(4), "gate_line": raw.split("Gate:")[1],
                   "tasks": [], "section": []}
            phases.append(cur)
            continue
        if cur is None:
            continue
        if raw.strip() == "---":
            cur = None
            continue
        cur["section"].append(raw)
        if re.match(r"^\|\s*\d+\.\d+\s*\|", raw):
            c = _cells(raw)
            link = re.search(r"\]\(([^)]+)\)", c[2]) if len(c) > 2 else None
            cur["tasks"].append({"id": c[0], "title": clean_title(c[1]), "status": c[3].strip(),
                                 "file": (TODO.parent / link.group(1)).resolve() if link else None})
    ledger = STATE.read_text(encoding="utf-8")
    for p in phases:
        row = next((ln for ln in ledger.splitlines() if f"`{p['branch']}`" in ln), "")
        p["prs"] = re.findall(r"\[#(\d+)\]\((https://github\.com/[^)]+/pull/\d+)\)", row)
    return phases


def phase_status(p: dict, active: dict | None) -> str:
    if p["gate"] in DONE:
        return "Done"
    sts = [t["status"] for t in p["tasks"]]
    if sts and all(s in ("\U0001f7e1", "✅") for s in sts) and "\U0001f7e1" in sts:
        return "In review"
    if any(s in ("\U0001f535", "\U0001f7e1", "⛔", "✅") for s in sts):
        return "In progress"
    return "Ready" if p is active else "Backlog"


def task_status(t: dict, p_status: str) -> tuple[str, str | None]:
    if t["status"] in TASK_STATUS:
        return TASK_STATUS[t["status"]]
    return ("Ready" if p_status in ("Ready", "In progress") else "Backlog"), None


def gate_date(p: dict) -> str | None:
    m = re.search(r"\d{4}-\d{2}-\d{2}", p["gate_line"]) if p["gate"] in DONE else None
    return m.group(0) if m else None


def priority(p: dict, order: list[dict], active: dict | None, done: bool) -> str | None:
    """Build order IS the priority: the active phase is P0, the one after it P1, the rest P2.
    Leftovers in an earlier, already-signed phase (e.g. infra 6.8) are P1 — open, not gating."""
    if done or active is None:
        return None
    gap = order.index(p) - order.index(active)
    return "P0" if gap == 0 else "P1" if gap == 1 or gap < 0 else "P2"


def build_model() -> list[dict]:
    phases = parse_tracker()
    state = parse_state()
    order = sorted(phases, key=lambda p: (CATEGORY_ORDER.index(p["category"]), p["phase"]))
    active = next((p for p in order if any(t["status"] not in DONE and not t["status"].startswith("⚠")
                   for t in p["tasks"])), None)
    items: list[dict] = []
    for cat in CATEGORY_ORDER:
        mine = [p for p in phases if p["category"] == cat]
        short, blurb = EPIC[cat]
        readme = ROOT / "implementation" / "tasks" / cat / "README.md"
        pst = {id(p): phase_status(p, active) for p in mine}
        if all(s == "Done" for s in pst.values()):
            e_status = "Done"
        elif any(s in ("In progress", "In review", "Done") for s in pst.values()):
            e_status = "In progress"
        else:
            e_status = "Ready" if any(s == "Ready" for s in pst.values()) else "Backlog"
        rows = "\n".join(f"| {cat}-{p['phase']} | {flatten(p['name'])} | {pst[id(p)]} | "
                         f"`{p['branch']}` |" for p in mine)
        body = (f"**{blurb}**\n\n| | |\n|---|---|\n| **Code repo** | "
                f"[{OWNER}/{CODE_REPO[cat]}](https://github.com/{OWNER}/{CODE_REPO[cat]}) |\n"
                f"| **Integration branch** | `{INTEGRATION[cat]}` |\n| **Quality gate** | "
                f"`python3 scripts/gate.py {cat}` |\n| **Architecture** | "
                f"[architecture/{cat}.md]({BLOB}architecture/{cat}.md) |\n\n"
                f"| Phase | Name | Status | Branch |\n|---|---|---|---|\n{rows}\n\n---\n\n"
                + rewrite_links(readme.read_text(encoding="utf-8"), readme))
        epic_key = f"epic:{cat}"
        e_dates = [gate_date(p) for p in mine]
        e_prio = min((priority(p, order, active, pst[id(p)] == "Done") or "P9" for p in mine))
        items.append({"key": epic_key, "level": "Epic", "category": cat, "phase": None,
                      "priority": None if e_prio == "P9" else e_prio,
                      "target": max(e_dates) if e_status == "Done" and all(e_dates) else None,
                      "title": f"[Epic] {short} — {blurb}", "status": e_status,
                      "labels": ["epic", cat], "body": body, "parent": None, "task_id": ""})
        for p in mine:
            ref = f"{cat}-{p['phase']}"
            report = ROOT / "reports" / f"{cat}-phase-{p['phase']}.md"
            prs = " ".join(f"[#{n}]({u})" for n, u in p["prs"]) or "none yet"
            gating = [b["label"] for b in state["blockers"] + state["reconciliations"]
                      if re.search(rf"(?:{cat}\s+)?\b{p['phase']}\.\d\b", b["raw"], re.I)]
            body = (f"| | |\n|---|---|\n| **Phase** | {ref} — {flatten(p['name'])} |\n"
                    f"| **Code repo** | [{OWNER}/{CODE_REPO[cat]}](https://github.com/{OWNER}/"
                    f"{CODE_REPO[cat]}) |\n| **Branch** | `{p['branch']}` → PR into "
                    f"`{INTEGRATION[cat]}` |\n| **Gate** | {p['gate_line'].strip()} |\n"
                    f"| **PRs** | {prs} |\n| **Report** | "
                    + (f"[reports/{report.name}]({BLOB}reports/{report.name})" if report.exists()
                       else "written at phase close") + " |\n"
                    + ("\n**Gating items (STATE.md):**\n" + "\n".join(f"- {flatten(g)}" for g in gating)
                       + "\n" if gating else "")
                    + "\n### Tasks (from TODO.md)\n\n"
                    + rewrite_links("\n".join(p["section"]).strip(), TODO))
            items.append({"key": f"phase:{ref}", "level": "Phase", "category": cat, "phase": ref,
                          "priority": priority(p, order, active, pst[id(p)] == "Done"),
                          "target": gate_date(p),
                          "title": f"[{ref}] {flatten(p['name'])}", "status": pst[id(p)],
                          "labels": ["phase", cat], "body": body, "parent": epic_key,
                          "task_id": ""})
            for t in p["tasks"]:
                status, extra = task_status(t, pst[id(p)])
                tid = f"{cat} {t['id']}"
                src = t["file"]
                text = src.read_text(encoding="utf-8") if src and src.exists() else "_task file missing_"
                text = re.sub(r"\A# .*\n+", "", text)
                rel = src.relative_to(ROOT).as_posix() if src else "?"
                body = (f"| | |\n|---|---|\n| **Task** | {tid} |\n| **Phase** | {ref} — "
                        f"{flatten(p['name'])} |\n| **Code repo** | `{CODE_REPO[cat]}` · branch "
                        f"`{p['branch']}` |\n| **Tracker status** | "
                        f"{TRACKER_WORD.get(t['status'], t['status'])} |\n| **Source of truth** | "
                        f"[{rel}]({BLOB}{rel}) |\n\n> Mirrored by `scripts/board_sync.py` — edit "
                        f"the task file in sentinel-brain, not this issue.\n\n---\n\n"
                        + rewrite_links(text, src) if src else text)
                items.append({"key": f"task:{cat}-{t['id']}", "level": "Task", "category": cat,
                              "priority": priority(p, order, active, status == "Done"),
                              "target": gate_date(p) if status == "Done" else None,
                              "phase": ref, "title": f"[{tid}] {t['title']}", "status": status,
                              "labels": ["task", cat] + ([extra] if extra else []),
                              "body": body, "parent": f"phase:{ref}", "task_id": tid,
                              "stem": src.stem if src else None})
    return items


# ── issues ─────────────────────────────────────────────────────────────────────

ISSUES_Q = """query($owner:String!,$name:String!,$after:String){repository(owner:$owner,name:$name){
 issues(first:100,after:$after,states:[OPEN,CLOSED]){pageInfo{hasNextPage endCursor}
 nodes{id databaseId number title body state parent{number} labels(first:20){nodes{name}}}}}}"""


def existing_issues() -> dict[str, dict]:
    out, after = {}, None
    while True:
        d = gql(ISSUES_Q, owner=OWNER, name=REPO, after=after)["repository"]["issues"]
        for n in d["nodes"]:
            m = MARK_RE.search(n["body"] or "")
            if m:
                out[m.group(1)] = n
        if not d["pageInfo"]["hasNextPage"]:
            return out
        after = d["pageInfo"]["endCursor"]


def resolve_wikilinks(items: list[dict], have: dict[str, dict]) -> None:
    """[[task-2-app-tests]] → #N, when the stem is unique inside the category."""
    for it in items:
        def fix(m: re.Match, cat=it["category"]) -> str:
            hits = [o for o in items if o.get("stem") == m.group(1) and o["category"] == cat]
            if len(hits) == 1 and hits[0]["key"] in have:
                return f"#{have[hits[0]['key']]['number']}"
            return m.group(0)
        it["body"] = re.sub(r"\[\[([\w-]+)\]\]", fix, it["body"])
        it["body"] = it["body"].rstrip() + "\n\n" + MARK.format(it["key"]) + "\n"


def sync_issues(items: list[dict]) -> dict[str, dict]:
    for name, (color, desc) in LABELS.items():
        if not DRY:
            gh(["label", "create", name, "-R", f"{OWNER}/{REPO}", "--color", color,
                "--description", desc, "--force"])
    have = existing_issues()
    created = 0
    for it in items:  # pass 1: create what is missing (parents first — items are ordered)
        if it["key"] in have:
            continue
        created += 1
        print(f"  + create {it['title'][:90]}")
        if DRY:
            continue
        body = it["body"].rstrip() + "\n\n" + MARK.format(it["key"]) + "\n"
        n = rest("POST", f"repos/{OWNER}/{REPO}/issues",
                 {"title": it["title"], "body": body, "labels": it["labels"]})
        have[it["key"]] = {"id": n["node_id"], "databaseId": n["id"], "number": n["number"],
                           "title": it["title"], "body": body, "state": "OPEN", "parent": None,
                           "labels": {"nodes": [{"name": x} for x in it["labels"]]}}
        time.sleep(1.2)  # stay under the content-creation secondary rate limit
    resolve_wikilinks(items, have)
    updated = linked = 0
    for it in items:  # pass 2: converge title/body/labels/state/parent
        cur = have.get(it["key"])
        if cur is None:
            continue
        want_state = "closed" if it["status"] == "Done" else "open"
        patch: dict = {}
        if cur["title"] != it["title"]:
            patch["title"] = it["title"]
        if (cur["body"] or "").strip() != it["body"].strip():
            patch["body"] = it["body"]
        if sorted(x["name"] for x in cur["labels"]["nodes"]) != sorted(it["labels"]):
            patch["labels"] = it["labels"]
        if cur["state"].lower() != want_state:
            patch["state"] = want_state
            if want_state == "closed":
                patch["state_reason"] = "completed"
        if patch:
            updated += 1
            print(f"  ~ update #{cur['number']} {', '.join(patch)}")
            if not DRY:
                rest("PATCH", f"repos/{OWNER}/{REPO}/issues/{cur['number']}", patch)
        if it["parent"]:
            parent = have[it["parent"]]
            if (cur.get("parent") or {}).get("number") != parent["number"]:
                linked += 1
                if not DRY:
                    rest("POST", f"repos/{OWNER}/{REPO}/issues/{parent['number']}/sub_issues",
                         {"sub_issue_id": cur["databaseId"], "replace_parent": True})
    print(f"issues: {created} created · {updated} updated · {linked} parent links")
    return have


# ── project board ──────────────────────────────────────────────────────────────

PROJECT_Q = """query($login:String!,$num:Int!){user(login:$login){projectV2(number:$num){id
 fields(first:50){nodes{... on ProjectV2FieldCommon{id name dataType}
  ... on ProjectV2SingleSelectField{options{id name}}}}
 views(first:50){nodes{id name number}}}}}"""
ITEMS_Q = """query($id:ID!,$after:String){node(id:$id){... on ProjectV2{items(first:100,after:$after){
 pageInfo{hasNextPage endCursor} nodes{id content{... on Issue{id}}
 fieldValues(first:20){nodes{
  ... on ProjectV2ItemFieldSingleSelectValue{name field{... on ProjectV2FieldCommon{name}}}
  ... on ProjectV2ItemFieldTextValue{text field{... on ProjectV2FieldCommon{name}}}
  ... on ProjectV2ItemFieldDateValue{date field{... on ProjectV2FieldCommon{name}}}}}}}}}}"""

CUSTOM_FIELDS = {
    "Level": ["Epic", "Phase", "Task"],
    "Category": CATEGORY_ORDER,
}
COLORS = ["PURPLE", "BLUE", "GREEN", "YELLOW", "ORANGE", "RED", "PINK", "GRAY"]


def project_meta() -> dict:
    return gql(PROJECT_Q, login=OWNER, num=PROJECT)["user"]["projectV2"]


def ensure_fields(proj: dict, phases: list[str]) -> dict:
    names = {f["name"] for f in proj["fields"]["nodes"] if f}
    wanted = {**CUSTOM_FIELDS, "Phase": phases}
    for name, opts in wanted.items():
        if name in names:
            continue
        print(f"  + field {name}")
        if not DRY:
            gql("""mutation($p:ID!,$n:String!,$o:[ProjectV2SingleSelectFieldOptionInput!]!){
              createProjectV2Field(input:{projectId:$p,dataType:SINGLE_SELECT,name:$n,
              singleSelectOptions:$o}){clientMutationId}}""", p=proj["id"], n=name,
                o=[{"name": o, "color": COLORS[i % len(COLORS)], "description": ""}
                   for i, o in enumerate(opts)])
    if "Task ID" not in names:
        print("  + field Task ID")
        if not DRY:
            gql("""mutation($p:ID!){createProjectV2Field(input:{projectId:$p,dataType:TEXT,
              name:"Task ID"}){clientMutationId}}""", p=proj["id"])
    return project_meta()


def sync_project(items: list[dict], have: dict[str, dict]) -> None:
    proj = project_meta()
    phases = [it["phase"] for it in items if it["level"] == "Phase"]
    proj = ensure_fields(proj, phases)
    if DRY and not all(n in {f["name"] for f in proj["fields"]["nodes"] if f}
                       for n in ("Level", "Category", "Phase", "Task ID")):
        print("project: fields would be created first; skipping item diff in --dry-run")
        return
    fields = {f["name"]: f for f in proj["fields"]["nodes"] if f}
    current, after = {}, None
    while True:
        d = gql(ITEMS_Q, id=proj["id"], after=after)["node"]["items"]
        for n in d["nodes"]:
            if n["content"]:
                vals = {v["field"]["name"]: v.get("name") or v.get("text") or v.get("date")
                        for v in n["fieldValues"]["nodes"] if v and v.get("field")}
                current[n["content"]["id"]] = {"item": n["id"], "vals": vals}
        if not d["pageInfo"]["hasNextPage"]:
            break
        after = d["pageInfo"]["endCursor"]

    added = changed = 0
    for it in items:
        issue = have.get(it["key"])
        if issue is None:
            continue
        cur = current.get(issue["id"])
        if cur is None:
            added += 1
            if DRY:
                continue
            item_id = gql("""mutation($p:ID!,$c:ID!){addProjectV2ItemById(input:{projectId:$p,
              contentId:$c}){item{id}}}""", p=proj["id"], c=issue["id"])["addProjectV2ItemById"]["item"]["id"]
            cur = {"item": item_id, "vals": {}}
        want = {"Status": it["status"], "Level": it["level"], "Category": it["category"],
                "Phase": it["phase"], "Task ID": it["task_id"] or None,
                "Priority": it["priority"], "Target date": it["target"]}
        ops = []
        for i, (fname, val) in enumerate(want.items()):
            if val is None or cur["vals"].get(fname) == val:
                continue
            f = fields[fname]
            if f.get("dataType") == "DATE":
                value = f"{{date:{json.dumps(val)}}}"
            elif f.get("options") is not None:
                opt = next(o["id"] for o in f["options"] if o["name"] == val)
                value = f'{{singleSelectOptionId:{json.dumps(opt)}}}'
            else:
                value = f"{{text:{json.dumps(val)}}}"
            ops.append(f"f{i}: updateProjectV2ItemFieldValue(input:{{projectId:{json.dumps(proj['id'])},"
                       f"itemId:{json.dumps(cur['item'])},fieldId:{json.dumps(f['id'])},"
                       f"value:{value}}}){{clientMutationId}}")
        if ops:
            changed += 1
            if not DRY:
                gql("mutation{" + " ".join(ops) + "}")
    print(f"project: {added} items added · {changed} items with field updates")
    ensure_views(project_meta())


VIEWS = [  # (name, layout, filter, visible fields) — grouping/sorting is UI-only in the API
    ("All tickets", "TABLE_LAYOUT", "",
     ["Title", "Status", "Level", "Category", "Phase", "Task ID", "Parent issue",
      "Sub-issues progress", "Linked pull requests"]),
    ("Task board", "BOARD_LAYOUT", "level:Task", ["Title", "Category", "Phase", "Task ID"]),
    ("Epics & phases", "TABLE_LAYOUT", "level:Epic,Phase",
     ["Title", "Status", "Level", "Category", "Sub-issues progress", "Linked pull requests"]),
    ("Infra", "TABLE_LAYOUT", "category:infra level:Task",
     ["Title", "Status", "Phase", "Task ID", "Parent issue", "Labels"]),
    ("Deployment", "TABLE_LAYOUT", "category:deployment level:Task",
     ["Title", "Status", "Phase", "Task ID", "Parent issue", "Labels"]),
    ("Backend", "TABLE_LAYOUT", "category:backend level:Task",
     ["Title", "Status", "Phase", "Task ID", "Parent issue", "Labels"]),
    ("Blocked & attention", "TABLE_LAYOUT", "label:blocked,needs-attention",
     ["Title", "Status", "Category", "Phase", "Labels"]),
]


def ensure_views(proj: dict) -> None:
    fields = {f["name"]: f["id"] for f in proj["fields"]["nodes"] if f}
    have = {v["name"]: v for v in proj["views"]["nodes"]}
    for name, layout, flt, visible in VIEWS:
        ids = [fields[v] for v in visible if v in fields]
        if name in have:
            continue
        print(f"  + view {name}")
        if DRY:
            continue
        v = gql("""mutation($p:ID!,$n:String!,$l:ProjectV2ViewLayout!,$ids:[ID!]!){
          createProjectV2View(input:{projectId:$p,name:$n,layout:$l,
          configuration:{visibleFieldIds:$ids}}){projectV2View{id}}}""",
                p=proj["id"], n=name, l=layout, ids=ids)["createProjectV2View"]["projectV2View"]
        if flt:
            gql("""mutation($v:ID!,$f:String!){updateProjectV2View(input:{viewId:$v,filter:$f})
              {clientMutationId}}""", v=v["id"], f=flt)


def main() -> int:
    global DRY
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-project", action="store_true")
    ap.add_argument("--issues", metavar="CAT-M",
                    help="read-only: print the issue numbers for a phase and its tasks, e.g. deployment-1")
    a = ap.parse_args()
    DRY = a.dry_run
    if a.issues:
        have = existing_issues()
        ref = a.issues.replace("deploy-", "deployment-")
        cat, _, num = ref.rpartition("-")
        keys = [f"phase:{ref}"] + sorted(k for k in have if k.startswith(f"task:{cat}-{num}."))
        print(f"ISSUES  {OWNER}/{REPO} · epic #{have[f'epic:{cat}']['number']}"
              if f"epic:{cat}" in have else "ISSUES  none synced yet — run board_sync.py")
        for k in keys:
            if k in have:
                print(f"  {k:<26} #{have[k]['number']}")
        return 0
    items = build_model()
    print(f"model: {sum(i['level'] == 'Epic' for i in items)} epics · "
          f"{sum(i['level'] == 'Phase' for i in items)} phases · "
          f"{sum(i['level'] == 'Task' for i in items)} tasks{'  (dry run)' if DRY else ''}")
    have = sync_issues(items)
    if not a.no_project:
        sync_project(items, have)
    print(f"board: https://github.com/users/{OWNER}/projects/{PROJECT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
