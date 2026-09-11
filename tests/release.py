"""THE RELEASE GATE -- may this ground be tagged? Reads; never writes.

    python tests/release.py --check          exit 0 = the tag may be cut
    python tests/release.py --check v0.1.5   name the version being cut

The operator's ask, 2026-09-08 ("the documentation within the estate gets
reviewed, updated, and logged, at all times"), and the shape from TASKS
"THE PATH TO 0.1.8": one command, run before every tag, that REFUSES BY
NAME unless every check below holds. Until today these were seven scripts
and two habits; a habit is a rule that has not failed yet.

WHAT IT READS (nothing it decides is generated -- LAW 1 for the hands):

    strokes    tests/last_run.json  -- green, finished, and stamped AFTER the
               newest edit under manjuel/ agents/ skills/ tests/ (a green
               older than the code is not a green; boot.suite_tally's rule)
    smoke      the same file, the same rule
    buildmap   tests/buildmap.py --check, run here
    standup    tests/run_history.jsonl's newest "standup" line -- LIVE (dry
               runs never write it), green, and after the newest edit
    law        law/law.py --prove, run here, exit 0
    manifest   manjuel.us.report(): 0 undeclared, 0 drifted (the rack is
               asked; if it cannot be, that one line is reported, not failed)
    spec       every SPEC.md section-4 line whose MET/OPEN/RULED OUT status
               differs from the last tag's copy has a CHANGELOG entry under
               "Unreleased" naming its section (4.x); no tagged copy = first
               tag with a SPEC, counted and passed
    daybook    DAYBOOK.md's last entry carries **At close**
    handoff    HANDOFF.md has "## HANDOFF FOR <today>"

THE OPERATOR'S TERMINAL IS THE PROOF. A hand runs this on a mirror as its
own check (CLAUDE.md's rule); last_run.json there is the mirror's stamp,
not his. The tag is cut only where this passes on the real ground.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# EVERY CHILD HERE CLOSES STDIN, AND IT IS LOAD-BEARING (2026-09-10).
#
# `subprocess.run()` with no `stdin` hands the child the PARENT's stdin. From a
# shell that is a console and harmless. Inside the engine under `manjuel.py
# --headless` it is the pipe `serve.Inbox` has a thread permanently blocked
# reading -- two readers on one pipe, and git never returns. Worse than a slow
# call: `run(timeout=N)` raises TimeoutExpired, then kills the child and calls
# communicate() AGAIN with no timeout, which blocks for the life of the process.
#
# boot.py's `_gate()` loads this module and calls `spec(ROOT, None)` at EVERY
# boot, and spec() with no tag calls last_tag() -> `git tag`. So this omission
# froze the engine during boot: nine sittings on 2026-09-10 opened, hung, and
# were closed by THE LINE's timeout with nothing run. gitstate.py was given
# this same fix on 2026-09-09 and calls it load-bearing; this file was not.
#
# No command here ever reads stdin, so closing it costs nothing.
DEVNULL = subprocess.DEVNULL

CODE_DIRS = ("manjuel", "agents", "skills", "tests")
# What the suites write into tests/ as they run. Counting these as edits
# made the strokes STALE the moment smoke finished after them.
STAMPS = {"last_run.md", "last_run.json", "run_history.jsonl", "last_audit.md"}
SPEC_LINE = re.compile(r"^- \*{0,2}(MET|OPEN|RULED OUT)\b", re.M)
SPEC_HEAD = re.compile(r"^### (4\.\d+)\b", re.M)


class Check:
    def __init__(self, name: str, ok: bool, why: str = ""):
        self.name, self.ok, self.why = name, bool(ok), why

    def line(self) -> str:
        mark = "ok " if self.ok else "REFUSED"
        return f"  {mark:8} {self.name:10} {self.why}"


# ---- what the ground says --------------------------------------------

def newest_edit(root: Path = ROOT) -> float:
    """The newest mtime under the code dirs -- boot.suite_tally's rule."""
    touched = 0.0
    for d in CODE_DIRS:
        for f in (root / d).rglob("*"):
            if f.name in STAMPS:
                continue          # the suites' own writes are not edits
            if f.suffix in (".py", ".md") and "__pycache__" not in f.parts:
                try:
                    touched = max(touched, f.stat().st_mtime)
                except OSError:
                    pass
    return touched


def suites(root: Path = ROOT, edited: float | None = None) -> list[Check]:
    edited = newest_edit(root) if edited is None else edited
    out: list[Check] = []
    stamp = root / "tests" / "last_run.json"
    try:
        book = json.loads(stamp.read_text(encoding="utf-8"))
    except Exception as exc:
        return [Check("strokes", False, f"tests/last_run.json unreadable ({exc})"),
                Check("smoke", False, "the same stamp")]
    for suite in ("strokes", "smoke"):
        r = book.get(suite) or {}
        if not r:
            out.append(Check(suite, False, "never stamped"))
            continue
        if r.get("state") == "running":
            out.append(Check(suite, False, "DID NOT FINISH (state: running)"))
            continue
        tally = f"{r.get('passed')}/{r.get('total')}"
        if not r.get("green"):
            out.append(Check(suite, False, f"{tally} RED"))
        elif (r.get("at") or 0) < edited:
            out.append(Check(suite, False, f"{tally} green but STALE: the ground "
                                            f"changed since; re-run"))
        else:
            out.append(Check(suite, True, f"{tally} green, after the newest edit"))
    return out


def standup(root: Path = ROOT, edited: float | None = None) -> Check:
    edited = newest_edit(root) if edited is None else edited
    hist = root / "tests" / "run_history.jsonl"
    last = None
    if not hist.exists():
        return Check("standup", False, "never run LIVE (a --dry run does not count)")
    try:
        for line in hist.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if rec.get("suite") == "standup":
                last = rec
    except Exception as exc:
        return Check("standup", False, f"run_history.jsonl unreadable ({exc})")
    if last is None:
        return Check("standup", False, "never run LIVE (a --dry run does not count)")
    tally = f"{last.get('passed')}/{last.get('total')}"
    if not last.get("green"):
        return Check("standup", False, f"{tally} -- failed: {', '.join(last.get('failed') or [])}")
    if (last.get("at") or 0) < edited:
        return Check("standup", False, f"{tally} green but before the newest edit; run it live again")
    return Check("standup", True, f"{tally} live, {last.get('report', '')}")


def buildmap(root: Path = ROOT) -> Check:
    r = subprocess.run([sys.executable, str(root / "tests" / "buildmap.py"), "--check"],
                       capture_output=True, text=True, cwd=str(root), timeout=120,
                       stdin=DEVNULL)      # see DEVNULL, above -- load-bearing
    tail = (r.stdout or r.stderr).strip().splitlines()[-1:] or [""]
    return Check("buildmap", r.returncode == 0, tail[0])


def law(root: Path = ROOT) -> Check:
    r = subprocess.run([sys.executable, str(root / "law" / "law.py"), "--prove"],
                       capture_output=True, text=True, cwd=str(root), timeout=120,
                       stdin=DEVNULL)      # see DEVNULL, above -- load-bearing
    tail = (r.stdout or r.stderr).strip().splitlines()[-1:] or [""]
    return Check("law", r.returncode == 0, tail[0][:100])


def manifest(root: Path = ROOT) -> Check:
    try:
        from manjuel import us
        from manjuel.registry import AgentRegistry
        from manjuel.skills import SkillLibrary
        installed, why = us.rack_tags()
        text = us.report(root, AgentRegistry.load(root / "agents"),
                         SkillLibrary.load(root / "skills"), installed)
    except Exception as exc:
        return Check("manifest", False, f"could not reconcile ({exc})")
    findings = [l for l in text.splitlines() if l.startswith(("  GAP ", "  DRIFT "))]
    if installed is None:
        # The rack could not be asked. That is a fact about this machine
        # (a mirror, a box without Ollama), not a drift in the manifest;
        # the line is reported and the other findings still gate.
        findings = [l for l in findings if "the rack" not in l]
    if findings:
        return Check("manifest", False, f"{len(findings)} finding(s): "
                     + "; ".join(l.split()[1] for l in findings))
    return Check("manifest", True, "agrees with the disk"
                 + ("" if installed is not None else f" (rack not asked: {why[:60]})"))


def spec_statuses(text: str) -> dict[str, list[str]]:
    """{'4.1': ['MET', 'MET', 'OPEN'], ...} in order of appearance."""
    out: dict[str, list[str]] = {}
    section = ""
    for line in text.splitlines():
        h = SPEC_HEAD.match(line)
        if h:
            section = h.group(1)
            out.setdefault(section, [])
            continue
        if not section:
            continue
        m = SPEC_LINE.match(line)
        if m:
            out[section].append(m.group(1))
    return out


def last_tag(root: Path = ROOT) -> str:
    try:
        r = subprocess.run(["git", "tag", "--sort=-v:refname"], capture_output=True,
                           text=True, cwd=str(root), timeout=30,
                           stdin=DEVNULL)  # see DEVNULL, above -- load-bearing
        tags = [t for t in r.stdout.split() if t.startswith("v")]
        return tags[0] if tags else ""
    except Exception:
        return ""


def tagged_file(root: Path, tag: str, rel: str) -> str | None:
    """A file as it was at `tag`, or None if the tag did not hold it.
    `git show` reads objects and never touches the index (CLAUDE.md)."""
    if not tag:
        return None
    try:
        r = subprocess.run(["git", "show", f"{tag}:{rel}"], capture_output=True,
                           text=True, cwd=str(root), timeout=30,
                           stdin=DEVNULL)  # see DEVNULL, above -- load-bearing
    except Exception:
        return None
    return r.stdout if r.returncode == 0 else None


def unreleased(changelog: str) -> str:
    """The text under '## Unreleased' up to the next '## '."""
    m = re.search(r"^## Unreleased[^\n]*\n(.*?)(?=^## |\Z)", changelog, re.M | re.S)
    return m.group(1) if m else ""


def spec(root: Path = ROOT, tag: str | None = None) -> Check:
    tag = last_tag(root) if tag is None else tag
    try:
        now = (root / "SPEC.md").read_text(encoding="utf-8")
        log = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    except Exception as exc:
        return Check("spec", False, f"SPEC/CHANGELOG unreadable ({exc})")
    cur = spec_statuses(now)
    n_lines = sum(len(v) for v in cur.values())
    before_text = tagged_file(root, tag, "SPEC.md")
    if before_text is None:
        return Check("spec", True, f"{n_lines} section-4 lines; no SPEC at {tag or 'any tag'} "
                                   f"to compare -- first tag with one")
    before = spec_statuses(before_text)
    changed = [s for s in sorted(set(cur) | set(before)) if cur.get(s) != before.get(s)]
    if not changed:
        return Check("spec", True, f"{n_lines} section-4 lines, none changed since {tag}")
    unlogged = [s for s in changed if s not in unreleased(log)]
    if unlogged:
        return Check("spec", False, f"changed since {tag} with no Unreleased CHANGELOG line "
                                    f"naming them: {', '.join(unlogged)}")
    return Check("spec", True, f"changed since {tag}: {', '.join(changed)} -- each in CHANGELOG")


def daybook(root: Path = ROOT) -> Check:
    try:
        text = (root / "DAYBOOK.md").read_text(encoding="utf-8")
    except Exception as exc:
        return Check("daybook", False, f"unreadable ({exc})")
    entries = re.split(r"^## Session ", text, flags=re.M)
    if len(entries) < 2:
        return Check("daybook", False, "no session entry")
    last = entries[-1]
    head = last.splitlines()[0].strip()
    ok = "**At close**" in last
    return Check("daybook", ok, f"Session {head[:50]}" + ("" if ok else " -- no **At close** line"))


def handoff(root: Path = ROOT, today: str | None = None) -> Check:
    today = today or time.strftime("%Y-%m-%d")
    try:
        text = (root / "HANDOFF.md").read_text(encoding="utf-8")
    except Exception as exc:
        return Check("handoff", False, f"unreadable ({exc})")
    ok = f"## HANDOFF FOR {today}" in text
    return Check("handoff", ok, f"HANDOFF FOR {today}" + ("" if ok else " -- missing"))


# ---- the gate ----------------------------------------------------------

def checks(root: Path = ROOT, tag: str | None = None) -> list[Check]:
    edited = newest_edit(root)
    out: list[Check] = []
    out += suites(root, edited)
    out.append(buildmap(root))
    out.append(standup(root, edited))
    out.append(law(root))
    out.append(manifest(root))
    out.append(spec(root, tag))
    out.append(daybook(root))
    out.append(handoff(root))
    return out


def render(results: list[Check], version: str = "") -> str:
    head = f"THE RELEASE GATE{(' -- ' + version) if version else ''}"
    lines = [head, "=" * len(head)] + [c.line() for c in results]
    bad = [c for c in results if not c.ok]
    if bad:
        lines.append("")
        lines.append(f"REFUSED: {len(bad)} of {len(results)} -- "
                     + ", ".join(c.name for c in bad) + ". The tag is not cut.")
    else:
        lines.append("")
        lines.append(f"PASSED: {len(results)} of {len(results)}. The tag may be cut -- by the operator (RULE 6).")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--check" not in argv:
        print(__doc__)
        return 2
    version = next((a for a in argv if a.startswith("v")), "")
    results = checks(ROOT)
    print(render(results, version))
    return 0 if all(c.ok for c in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
