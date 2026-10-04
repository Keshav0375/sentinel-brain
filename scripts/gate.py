#!/usr/bin/env python3
"""Run the Sentinel quality gate for one category — the right gate, with the right tools.

The gate itself is `../Sentinel/scripts/quality_gate.py` (CI calls it there). Running it
directly from brain has two traps, and this wrapper closes both:

1. Gate source. The local `Sentinel` checkout can sit on any branch. On `main` it is
   behind `release-phase-2` and lacks fixes such as IMPLICIT_PATHS — without which
   deployment phase 1 can never report green. So:
     backend            → the working-tree copy (a phase branch may add to MATRIX in the
                          same commit as the tests it adds)
     infra / deployment → the copy at `origin/release-phase-2`, extracted to a temp file
2. Tool resolution. The gate looks every tool up on PATH and SKIPS what it cannot find.
   ruff / pytest / pyright live in the target repo's `.venv`, and macOS ships `python3`
   but no `python` (infra's py-unittest calls `python`). So PATH gets the repo's
   `.venv/bin` first, then a `python` shim.

    python3 scripts/gate.py deployment         # full gate — must be green before commit
    python3 scripts/gate.py backend --fast     # skip slow/network checks while iterating
    python3 scripts/gate.py infra --json

The gate's own exit code is 0 even for INCONCLUSIVE ("nothing was verified"), so this
wrapper ends with one machine-readable verdict line and its own exit code:

    VERDICT GREEN                     exit 0   every applicable check ran and passed
    VERDICT GREEN · n/a: a, b         exit 0   same; a, b had no input yet (see below)
    VERDICT PARTIAL · skipped: a, b   exit 3   passed, but checks did not run — NOT green
    VERDICT INCONCLUSIVE              exit 3   nothing ran
    VERDICT RED · failed: a, b        exit 1   fix and re-run

A check the gate skips with "no such path yet" is n/a — not a gap — only when the repo
has not BUILT its input yet: every missing path has never been tracked in the target
repo's history (`git log --all -- <path>` is empty), e.g. `tests/` or `.github/workflows`
before the task that adds them. n/a is named on the verdict line (`· n/a: …`, on
PARTIAL too) and explained on a NOTE line after the gate's report (which still lists it
as skipped), but does not demote the verdict. A missing path that was ever tracked was
LOST (deleted, renamed) — that check stays a skip and the verdict is PARTIAL. So does
every other skip (tool not on PATH, …). The missing paths are resolved statically —
the gate module is loaded (no check runs) and its own IMPLICIT_PATHS + resolve_argv
are applied to MATRIX[cat] — never parsed from the truncated human text, and only when
the verdict is not already RED. Anything that cannot be resolved counts as a skip.

With --fast, skips caused by --fast itself are expected and do not demote the verdict;
the line then reads `GREEN (fast — not final)`. Only a full run can be final.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from where import REPO, ROOT  # noqa: E402  (single source for repo locations)

SENTINEL = (ROOT / REPO["backend"]).resolve()
GATE_REF = "origin/release-phase-2"
GATE_PATH = "scripts/quality_gate.py"
NO_PATH = "no such path yet: "  # the gate's skip detail for a check whose paths are missing


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=60, check=True
    ).stdout.strip()


def gate_source(cat: str, tmp: Path) -> tuple[Path, str]:
    """-> (path to quality_gate.py, human label of where it came from)."""
    if cat == "backend":
        branch = _git(SENTINEL, "rev-parse", "--abbrev-ref", "HEAD")
        sha = _git(SENTINEL, "rev-parse", "--short", "HEAD")
        if branch == "main":
            print("WARN    ../Sentinel is on `main` — backend work belongs on dev/* or "
                  "release-phase-2; this gate copy is stale")
        return SENTINEL / GATE_PATH, f"working tree {branch}@{sha}"

    note = ""
    try:
        _git(SENTINEL, "fetch", "--quiet", "origin", "release-phase-2")
    except (subprocess.SubprocessError, OSError):
        note = " (fetch failed — cached ref)"
    sha = _git(SENTINEL, "rev-parse", "--short", GATE_REF)
    out = tmp / "quality_gate.py"
    out.write_text(_git(SENTINEL, "show", f"{GATE_REF}:{GATE_PATH}") + "\n", encoding="utf-8")
    return out, f"{GATE_REF}@{sha}{note}"


def tool_path(repo: Path, tmp: Path) -> tuple[str, str]:
    """-> (PATH value, label). Repo venv first, then a `python` -> python3 shim."""
    shim = tmp / "shim"
    shim.mkdir()
    (shim / "python").symlink_to(sys.executable)
    venv = repo / ".venv" / "bin"
    parts = [str(shim), os.environ.get("PATH", "")]
    if venv.is_dir():
        parts.insert(0, str(venv))
        return os.pathsep.join(parts), f"{venv.relative_to(repo.parent)}"
    return os.pathsep.join(parts), "system PATH (no .venv)"


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] not in REPO:
        print(__doc__)
        print(f"usage: python3 scripts/gate.py <{'|'.join(REPO)}> [--fast] [--json]")
        return 2
    cat, passthrough = args[0], args[1:]
    repo = (ROOT / REPO[cat]).resolve()
    if not repo.is_dir():
        print(f"HALT    {repo} does not exist")
        return 2

    with tempfile.TemporaryDirectory(prefix="sentinel-gate-") as t:
        tmp = Path(t)
        src, src_label = gate_source(cat, tmp)
        path, tools_label = tool_path(repo, tmp)
        print(f"GATE    {cat} · {repo.name} · source {src_label} · tools {tools_label}")
        if "(no .venv)" in tools_label and cat in ("backend", "deployment"):
            print(f"NOTE    no {repo.name}/.venv — ruff/pytest will be SKIPPED unless on PATH. "
                  "Create it with python3.12 -m venv .venv and install the repo's deps + ruff.")
        sys.stdout.flush()
        env = {**os.environ, "PATH": path}
        env.pop("VIRTUAL_ENV", None)  # never let the caller's venv shadow the repo's
        cmd = [sys.executable, str(src), "--repo", cat, "--path", str(repo), *passthrough]
        proc = subprocess.run(cmd, env=env, cwd=repo, capture_output=True, text=True)
        sys.stdout.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        if "--json" in passthrough:
            return proc.returncode
        return verdict(proc.stdout, proc.returncode, "--fast" in passthrough,
                       lambda: never_built(src, cat, repo))


def _ever_tracked(repo: Path, path: str) -> bool:
    """True if any commit on any ref touched `path` — or if git cannot say (fail safe)."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), "log", "--all", "-1", "--format=%H", "--", path],
            capture_output=True, text=True, timeout=60, check=False,
        )
    except (subprocess.SubprocessError, OSError):
        return True
    return proc.returncode != 0 or bool(proc.stdout.strip())


def never_built(src: Path, cat: str, repo: Path) -> set[str]:
    """Names of checks whose missing paths were never tracked in `repo`.

    Loads the gate module (definitions only — no check runs) and applies its own path
    logic (IMPLICIT_PATHS, resolve_argv) to MATRIX[cat], so the paths are exactly the
    ones the gate found missing. Anything that cannot be resolved is left out, so it
    counts as a skip (PARTIAL) — never as n/a.
    """
    name = "_sentinel_quality_gate"
    try:
        spec = importlib.util.spec_from_file_location(name, src)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod  # dataclasses resolve annotations through sys.modules
        spec.loader.exec_module(mod)
        implicit = getattr(mod, "IMPLICIT_PATHS", {})
        unbuilt = set()
        for check, argv, _required in mod.MATRIX[cat]:
            if check in implicit and not (repo / implicit[check]).exists():
                paths = [implicit[check]]
            elif mod.resolve_argv(argv, repo) is None:
                paths = [a for a in argv if mod._is_path_arg(a)]
            else:
                continue
            if paths and not any(_ever_tracked(repo, p) for p in paths):
                unbuilt.add(check)
        return unbuilt
    except Exception:  # noqa: BLE001 — fail safe: unresolved means skip, never n/a
        return set()
    finally:
        sys.modules.pop(name, None)


def verdict(out: str, code: int, fast: bool, resolve_unbuilt: Callable[[], set[str]]) -> int:
    """Turn the gate's human report into one unambiguous line + exit code.

    `resolve_unbuilt` is called only when the verdict is not RED and some check was skipped
    for a missing path.
    """
    failed, missing, other, ran = [], [], [], 0
    for line in out.splitlines():
        s = line.strip()
        if not s or s[0] not in "✅❌⏭":
            continue
        name = s.split()[1]
        if s.startswith("❌"):
            failed.append(name)
            ran += 1
        elif s.startswith("✅"):
            ran += 1
        elif NO_PATH.strip() in s:
            missing.append(name)
        elif not (fast and "(--fast)" in s):
            other.append(name)
    if failed or (code != 0 and not ran):
        print(f"VERDICT RED · failed: {', '.join(failed) or f'gate exit {code}'}")
        return 1
    unbuilt = resolve_unbuilt() if missing else set()
    na = [n for n in missing if n in unbuilt]
    lost = [n for n in missing if n not in unbuilt]
    skipped = other + lost
    if na:
        print("NOTE    n/a = target path never existed in repo history (not yet built): "
              f"{', '.join(na)}")
    if lost:
        print("NOTE    missing path was tracked before (deleted/renamed?) or could not be "
              f"checked — still a skip: {', '.join(lost)}")
    if not ran:
        print("VERDICT INCONCLUSIVE · nothing ran")
        return 3
    na_note = f" · n/a: {', '.join(na)}" if na else ""
    if skipped:
        print(f"VERDICT PARTIAL · skipped: {', '.join(skipped)}{na_note} — NOT green")
        return 3
    print(f"VERDICT GREEN{' (fast — not final)' if fast else ''}{na_note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
