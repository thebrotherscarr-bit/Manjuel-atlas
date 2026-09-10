"""The boot report: what is actually here, before you ask for anything.

Four questions, answered from observation rather than assumption:

  GROUND  what markdown declared -- seats, skills, pipelines
  RACK    what Ollama has, what this pipeline needs, what is loaded RIGHT NOW,
          and which of it belongs to somebody else
  RECORD  the index, the memory, the transcripts
  GATE    git, whether remote operations are permitted, and the release
          gate's nine checks (tests/release.py) -- so the ground says at
          every boot whether it could be tagged, not only when one is cut

Every section degrades on its own. If Ollama is unreachable the RACK section
says so and the rest still prints -- a boot report that vanishes when one thing
is down is worse than no boot report.
"""

from __future__ import annotations

from pathlib import Path

from . import gitstate
from . import voice, memory as _mem, vram
from . import seatlog as _seatlog


def _rule(title: str) -> str:
    return f"  {title}"


def _models(sess, EMBED_MODEL: str) -> list[str]:
    out: list[str] = []
    try:
        installed = sess.runtime.installed_models()
    except Exception as exc:
        return [_rule("RACK"), f"    unreachable — {exc}"]

    sizes = vram.installed_sizes(sess.runtime)
    resident = dict(sess.runtime.resident())

    live = [s for s in sess.pipeline if not getattr(s, "when", None)]
    plan_live = vram.build_plan(sess.pipeline_name, live, sess.registry, sizes=sizes)
    plan_all = vram.build_plan(sess.pipeline_name, sess.pipeline, sess.registry, sizes=sizes)

    needed: list[tuple[str, str]] = []
    for m in plan_live.distinct:
        needed.append((m, "needed every run"))
    for m in plan_all.distinct:
        if m not in plan_live.distinct:
            seats = [s for s in sess.pipeline
                     if getattr(s, "when", None)
                     and sess.registry.get(str(s)).model == m]
            gate = getattr(seats[0], "when", "on demand") if seats else "on demand"
            needed.append((m, f"on `{gate}`"))
    for m in sorted(sess.skills.models()):
        if m not in [x for x, _ in needed]:
            needed.append((m, "needed by prompt skills"))
    if EMBED_MODEL not in [x for x, _ in needed]:
        needed.append((EMBED_MODEL, "drift + index"))

    host = getattr(sess.runtime, "host", "ollama")
    out.append(_rule(f"RACK   {host} · {len(installed)} models installed"))
    for m, why in needed:
        state = "RESIDENT" if m in resident else "cold"
        size = vram.gb(sizes[m]) if sizes.get(m) else "?"
        missing = "" if m in installed else "   ** NOT INSTALLED **"
        out.append(f"    {state:<9} {m:<26} {size:>7}   {why}{missing}")

    # Ours = everything this ground DECLARES, not just what this pipeline
    # needs -- a model resident because the estate used it an hour ago is
    # not another client.
    ours = ({m for m, _ in needed} | set(sess.registry.models())
            | sess.skills.models() | {EMBED_MODEL})
    others = [(t, b) for t, b in resident.items() if t not in ours]
    if others:
        ob = sum(b for _, b in others)
        for t, b in others:
            out.append(f"    {'RESIDENT':<9} {t:<26} {vram.gb(b):>7}   another client")
        free = vram.budget_bytes() - ob
        out.append(f"    {'':<9} {'':<26} {'':>7}   ~{vram.gb(free)} free of "
                   f"{vram.gb(vram.budget_bytes())}")
    elif resident:
        out.append(f"    {'':<9} {'':<26} {'':>7}   the card is ours alone")
    return out


# THE CODE DIRS, AND THE FILES A RUN WRITES INTO THEM.
#
# tests/release.py holds its own copy of this on purpose -- the release gate
# must still be able to report on a tree where manjuel/ will not import, and
# importing the engine into the gate would mean a broken engine kills the gate
# instead of being reported by it. A stroke proves the two agree, because a
# comment claiming they agree is exactly what failed here.
CODE_DIRS = ("manjuel", "agents", "skills", "tests")
STAMPS = {"last_run.md", "last_run.json", "run_history.jsonl", "last_audit.md"}


def source_files(root: Path):
    """Every file under the code dirs whose mtime counts as an EDIT.

    THE FAULT THIS CLOSES, measured on the operator's ground 2026-09-10 and
    seen by him "for a while": three copies of this rule existed -- here, in
    `proved`, and in tests/release.py -- and only release.py excluded the
    stamps. tests/last_run.md is a .md under tests/ that THE SUITE ITSELF
    WRITES as it finishes, so `touched > newest_run` held the instant any
    green run ended. The boot report announced STALE after EVERY successful
    suite, and `proved` went further and NAMED last_run.md as a file that had
    changed since the run that wrote it.

    Boot's newest edit measured 0.0s after the run; release.py read the same
    tree as 86s OLDER. Not a timing flake -- structural.

    A WARNING THAT ALWAYS FIRES IS ONE HE STOPS READING, which makes it worse
    than no warning: STALE is the line that would have told him a green number
    was about old code.

    last_run.json and run_history.jsonl are not .py/.md and so were never
    caught by the suffix filter anyway. They are named regardless, because
    relying on a suffix filter to exclude them is luck, and luck is what this
    whole report exists to stop presenting as proof.
    """
    for d in CODE_DIRS:
        for f in (root / d).rglob("*"):
            if f.name in STAMPS or "__pycache__" in f.parts:
                continue
            if f.suffix in (".py", ".md"):
                yield f


def suite_tally(ROOT: Path) -> str:
    """What the suites last proved, and WHEN -- read from the stamp they
    write themselves (tests/last_run.json). No count is written into a doc
    (the operator's ruling, 2026-09-02): the suites grow with the system,
    so the only honest number is the one a run produced.

    STALE IS THE POINT. If the newest source edit is younger than the last
    run, the tally is reported as stale and named as such: a green number
    from before the current code proves nothing about it."""
    import json
    import time
    p = ROOT / "tests" / "last_run.json"
    if not p.exists():
        return "not run here yet   python tests/test_manjuel.py"
    try:
        book = json.loads(p.read_text(encoding="utf-8") or "{}")
    except Exception:
        return "unreadable stamp   re-run the suites"
    if not book:
        return "not run here yet   python tests/test_manjuel.py"

    newest_run = max((r.get("at") or 0) for r in book.values())
    parts, red = [], False
    for suite in sorted(book):
        r = book[suite]
        # A stamp still saying `running` means the process never reached the
        # end -- a crash, or a kill. It used to leave the previous
        # SUCCESSFUL numbers standing, so a dead run read as green here and
        # was reported as green to the operator (2026-09-02, twice in one
        # message). A number nobody finished earning is not a number.
        if r.get("state") == "running":
            parts.append(f"{suite} DID NOT FINISH")
            red = True
            continue
        parts.append(f"{r.get('passed')}/{r.get('total')} {suite}")
        red = red or not r.get("green")

    touched = 0.0
    for f in source_files(ROOT):
        try:
            touched = max(touched, f.stat().st_mtime)
        except OSError:
            pass

    ago = max(0.0, time.time() - newest_run)
    when = (f"{int(ago // 60)}m ago" if ago < 5400
            else f"{int(ago // 3600)}h ago" if ago < 172800
            else f"{int(ago // 86400)}d ago")
    line = ", ".join(parts) + f"   {when}"
    if red:
        line += "   ** RED **"
    if touched > newest_run:
        line += "   ** STALE: the ground changed since; re-run **"
    return line


def _record(sess, ROOT: Path, EMBED_MODEL: str) -> list[str]:
    out = [_rule("RECORD")]

    db = ROOT / "index" / "vectors.db"
    if not db.exists():
        out.append(f"    index    empty                 /index builds it ({EMBED_MODEL})")
    else:
        try:
            import sqlite3
            c = sqlite3.connect(str(db))
            d = c.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
            k = c.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
            c.close()
            out.append(f"    index    {d} docs / {k} passages")
        except Exception as exc:
            out.append(f"    index    unreadable ({exc})")

    mem = ROOT / _mem.MEMORY_FILE
    n = len(_mem.split_entries(mem.read_text(encoding='utf-8'))) if mem.exists() else 0
    pending = len(_mem.pending(ROOT))
    line = f"    memory   {n} entr{'y' if n == 1 else 'ies'}"
    if pending:
        line += f"   ** {pending} proposed, awaiting you — /memory **"
    out.append(line)

    logs = list((ROOT / "logs").glob("*.md")) if (ROOT / "logs").exists() else []
    out.append(f"    logs     {len(logs)} transcript{'' if len(logs) == 1 else 's'}")
    out.append(f"    proved   {suite_tally(ROOT)}")
    return out


# ---------------------------------------------------------------------
# THE BRIEF -- where the build is, and what the operator said we are on
# ---------------------------------------------------------------------
#
# The operator, 2026-09-07: the standup "needs to ... actually give me some
# good 'this is your day' or 'we are here on the build, and this is what you
# said we are working on today' type of behaviour ... it needs to be able to
# review where it's at." CLAUDE.md READ FIRST, for the sitting: DAYBOOK's
# last entry (intent), HANDOFF's newest block (state), the last toll (his
# own words), TASKS (what is open), memory (what is landed and what waits),
# the workspace (what arrived), the last standup (what missed). EVERY LINE
# IS READ OFF A FILE. No model touches this; `/brief` hands it to the door
# to say in his voice, and the door is told nothing else happened.

BRIEF_CHARS = 700


def _clip(text: str, n: int = BRIEF_CHARS) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[:n].rsplit(" ", 1)[0] + " ..."


def _last_toll(ROOT: Path) -> list[str]:
    import re
    p = ROOT / "SEAT_LOG.md"
    if not p.exists():
        return ["    no SEAT_LOG yet"]
    text = p.read_text(encoding="utf-8", errors="replace")
    heads = list(re.finditer(r"^## (?P<date>\S+) — sitting (?P<n>\d+)[^\n]*$", text, re.M))
    if not heads:
        return ["    no toll paid yet"]
    h = heads[-1]
    block = text[h.start():]
    out = [f"    sitting {h.group('n')} ({h.group('date')}): {h.group(0).split('—', 2)[-1].strip()[:90]}"]
    for field, label in (("WHAT PROVED", "proved"), ("WHAT IS THIN", "thin"),
                         ("WHAT IS OWED", "owed"), ("WHAT IS THIN / OWED", "thin/owed")):
        m = re.search(rf"\*\*{re.escape(field)}\*\*\s*\n(.*?)(?=\n\*\*|\Z)", block, re.S)
        if m and m.group(1).strip():
            out.append(f"    {label:<7}: {_clip(m.group(1), 300)}")
    return out


def _handoff_head(ROOT: Path) -> str:
    p = ROOT / "HANDOFF.md"
    if not p.exists():
        return ""
    text = p.read_text(encoding="utf-8", errors="replace")
    at = text.find("\n## HANDOFF FOR ")        # the HEADING, not the preamble naming it
    if at == -1:
        return ""
    body = text[at + 1:].split("\n", 1)[1] if "\n" in text[at + 1:] else ""
    paras = [para for para in body.split("\n\n") if para.strip() and not para.startswith("## ")]
    return _clip(paras[0]) if paras else ""


def _open_tasks(ROOT: Path) -> tuple[int, list[str]]:
    import re
    p = ROOT / "TASKS.md"
    if not p.exists():
        return 0, []
    text = p.read_text(encoding="utf-8", errors="replace")
    opens = re.findall(r"^\s+\[ \]\s+(.+)$", text, re.M)
    last = text.rfind("\n## ")
    tail = text[last:] if last != -1 else text
    recent = re.findall(r"^\s+\[ \]\s+(.+)$", tail, re.M)
    if "Appended by the operator" in tail and not recent:
        prev = text.rfind("\n## ", 0, last)
        recent = re.findall(r"^\s+\[ \]\s+(.+)$", text[prev:last], re.M)
    return len(opens), [_clip(r, 90) for r in recent[:4]]


def _last_standup(ROOT: Path) -> list[str]:
    logs = sorted((ROOT / "logs").glob("standup_*.md")) if (ROOT / "logs").exists() else []
    if not logs:
        return ["    none run yet   python tests/standup.py"]
    text = logs[-1].read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    head = lines[2] if len(lines) > 2 else ""
    out = [f"    {logs[-1].name}: {_clip(head, 120)}"]
    if "## REVIEW THESE FIRST" in text:
        sect = text.split("## REVIEW THESE FIRST", 1)[1].split("\n## ", 1)[0]
        names = [l[4:].strip() for l in sect.splitlines() if l.startswith("### ")]
        if names:
            out.append(f"    review first: {', '.join(names[:6])}")
    return out


def _arrivals(sess, ROOT: Path) -> list[str]:
    """Files in the workspace newer than the previous sitting's close."""
    import json
    from datetime import datetime
    since = None
    ledger = ROOT / "sessions" / "sessions.jsonl"
    try:
        for line in ledger.read_text(encoding="utf-8").splitlines():
            row = json.loads(line) if line.strip() else {}
            if row.get("ended"):
                since = datetime.fromisoformat(row["ended"]).timestamp()
    except Exception:
        since = None
    ws = ROOT / "agent_workspace"
    if since is None or not ws.exists():
        return []
    fresh = [p for p in ws.rglob("*") if p.is_file() and p.stat().st_mtime > since
             and "__pycache__" not in p.parts]
    if not fresh:
        return []
    names = ", ".join(p.relative_to(ws).as_posix() for p in fresh[:5])
    more = f" +{len(fresh) - 5}" if len(fresh) > 5 else ""
    return [f"    {len(fresh)} new in the workspace since the last sitting closed: {names}{more}",
            "    (inspect them before anything reads them: `inspect <name>`)"]


def brief_facts(sess, ROOT: Path, git=None) -> list[str]:
    """The brief's facts, one block, read off the record.

    `git` is the GitState already read at open, when the caller has one:
    the open path read the repo five times (twenty subprocesses) for one
    stamp (the REPL read, 2026-09-08). None reads it fresh, as /brief
    mid-sitting should."""
    out: list[str] = []
    g = git or gitstate.read(ROOT)
    out.append(_rule(f"THE BRIEF -- sitting {sess.sitting.n} · {g.stamp()}"))
    # THE LAST HAND (0.1.6): who worked the ground between sittings, what
    # they read, whether they closed -- beside the last sitting, so the
    standing = (getattr(sess, "standing", "") or "").strip()
    if standing:
        out.append(_rule("what this sitting is for (DAYBOOK's last entry)"))
        for l in standing.splitlines()[1:12]:
            out.append(f"    {l.rstrip()[:110]}")
    hand = _handoff_head(ROOT)
    if hand:
        out.append(_rule("where the build stands (HANDOFF's newest block)"))
        out.append(f"    {hand}")
    out.append(_rule("the last toll -- your own words"))
    out += _last_toll(ROOT)
    n, recent = _open_tasks(ROOT)
    out.append(_rule(f"open in TASKS: {n}"))
    for r in recent:
        out.append(f"    [ ] {r}")
    mem = ROOT / _mem.MEMORY_FILE
    landed = len(_mem.split_entries(mem.read_text(encoding="utf-8"))) if mem.exists() else 0
    waiting = len(_mem.pending(ROOT))
    out.append(_rule(f"memory: {landed} landed"
                     + (f", {waiting} proposed and waiting -- `remember that` or /memory" if waiting else "")))
    arrived = _arrivals(sess, ROOT)
    if arrived:
        out.append(_rule("arrivals"))
        out += arrived
    out.append(_rule("the last standup"))
    out += _last_standup(ROOT)
    return out


def _gate(ROOT: Path) -> list[str]:
    """The release gate's verdict, from what can be READ. Never raises.

    tests/release.py is the authority on every check; this asks the ones that
    read a file and prints what it said. It re-judges nothing and counts
    nothing of its own -- the same rule as the rest of this file.

    SIX OF NINE, AND IT SAYS SO. buildmap and law each spawn a fresh python,
    and manifest dials the rack. Measured 2026-09-09: all nine run in 1.4s
    from a shell and NEVER RETURNED inside the engine -- two python processes
    blocked for three minutes on 0.6 CPU seconds between them, and no engine
    opened. atlas spawns this door with PROTOCOL 1 on its stdio and those
    children inherit it. Whatever the exact hold, the shape is the fault: boot
    is a door being opened under somebody, and spawning interpreters inside it
    is fragile by construction. The three are named as not asked, with the
    command that asks them; a report that checked six and implied nine would be
    a number the record cannot prove.

    LOADED BY PATH. tests/ has no __init__.py; it imports as a namespace
    package, which works from the ground and is a coin-flip from anywhere else.
    A boot report that dies on an import is worse than one that says the gate
    could not be read.
    """
    import importlib.util

    path = ROOT / "tests" / "release.py"
    if not path.is_file():
        return ["    gate     tests/release.py is not in this ground"]
    try:
        spec = importlib.util.spec_from_file_location("_release_at_boot", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        edited = mod.newest_edit(ROOT)
        results = list(mod.suites(ROOT, edited))
        results.append(mod.standup(ROOT, edited))
        results.append(mod.spec(ROOT, None))
        results.append(mod.daybook(ROOT))
        results.append(mod.handoff(ROOT))
    except Exception as exc:
        # Every reason this can fail -- a missing file, an import error, a
        # check that raises -- is one line, and the boot continues.
        return [f"    gate     could not be asked ({type(exc).__name__}: {exc})"]

    DEFERRED = "buildmap, law, manifest"
    bad = [c for c in results if not c.ok]
    if not bad:
        return [f"    gate     {len(results)}/{len(results)} read here -- "
                f"{DEFERRED} not asked (python tests/release.py --check)"]

    out = [f"    gate     {len(results) - len(bad)}/{len(results)} read here -- "
           f"REFUSED: {', '.join(c.name for c in bad)}"]
    for c in bad:
        out.append(f"      !! {c.name:9} {c.why}")
    out.append(f"      .. {DEFERRED} not asked at boot -- "
               f"python tests/release.py --check")
    return out


def report(sess, ROOT: Path, EMBED_MODEL: str, git=None) -> list[str]:
    live = [str(s) for s in sess.pipeline if not getattr(s, "when", None)]
    resting = len(sess.pipeline) - len(live)

    out: list[str] = []
    out.append(_rule("GROUND"))
    out.append(f"    {len(sess.registry)} seats · {len(sess.skills.specs)} skills · "
               f"{len(sess.pipeline_names())} pipelines")
    out.append(f"    '{sess.pipeline_name}': {' -> '.join(live)}"
               + (f"   (+{resting} resting)" if resting else ""))
    out.append("")

    out += _models(sess, EMBED_MODEL)
    out.append("")
    out += _record(sess, ROOT, EMBED_MODEL)
    out.append("")

    g = git or gitstate.read(ROOT)
    out.append(_rule("GATE"))
    out.append(f"    {g.stamp()}")
    out.append(f"    remote git operations: "
               f"{'ALLOWED' if gitstate.remote_allowed() else 'off'}")
    lock = gitstate.lock_state(ROOT) if g.is_repo else ""
    if lock:
        out.append(f"    !! {lock.splitlines()[0]}")
    out += _gate(ROOT)

    # Voice is optional everywhere. Say what is available rather than leaving
    # the operator to discover a missing library mid-sentence.
    out.append(_rule("VOICE"))
    out.append(f"    speak : {voice.can_speak()}")
    out.append(f"    listen: {voice.can_listen()}")
    return out
