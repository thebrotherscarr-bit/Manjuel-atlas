"""THE RECORD, AND WHETHER IT STILL AGREES WITH THE GROUND. Reads; never writes.

Two questions the operator asks by hand and should not have to:

    doc_pass         where does this estate stand today, and what is on the
                     table? The DAYBOOK, the HANDOFF, the CHANGELOG's
                     Unreleased, the open TASKS lines, the repository and the
                     proofs -- gathered in one place instead of six.

    doctrine_check   do the foundational and functional docs still describe
                     what the system actually performs? His LAW 6, made
                     mechanical: "ensuring a review pass is made so that there
                     are no conflicts within what the system states and
                     actually performs."

WHY THIS IS ARITHMETIC AND NOT A SEAT. The estate already has `deep_research`,
which wakes the Deep Researcher persona and asks it to reason. That is the
wrong engine for this and would be actively harmful: a model asked to find
discrepancies in a corpus it cannot fully read will INVENT them, which is the
exact family -- invented numbers, parroting, a delivery that inverted its own
tool -- that this estate spent 2026-09-10 closing. Every finding below is a
comparison between two things on disk. Nothing here is generated.

THE LEDGER/LIVING SPLIT IS THE WHOLE DESIGN. A first cut flagged forty tallies
and every one was correct where it stood: they were in HANDOFF.md and
SEAT_LOG.md, which are DATED HISTORY. "1471/1471 on 2026-09-02" is not a stale
claim, it is a true record of that day, and LAW 1 keeps it. Only a LIVING doc
-- one that speaks in the present tense about what the estate IS -- can hold a
stale claim. So the ledgers are named and skipped, and a check that would have
cried forty times cries only where a number really does read as a claim
about now.

A SECOND CUT WAS WRONG TOO, and it is worth recording why. Comparing
`skills/*.md` STEMS against `@skill()` names reported five discrepancies --
fact_extractor, sentiment_classifier, syntax_lint, task_decomposer,
time_aligner -- and all five were false. A skill's identity is its declared
Action Keyword (`fact_extractor.md` declares `extract_facts`), and a skill with
no handler is a legitimate PROMPT SKILL dispatched against a Model Target. The
LIBRARY is asked here, never the filenames. A check that cries wolf is a check
he learns to skip, and then it is worse than no check at all.
"""
from __future__ import annotations

import re
from pathlib import Path

from manjuel import gitstate

# ---- which docs may hold a claim about NOW ------------------------------
#
# LEDGERS are dated, append-only history. A number in one of these is a record
# of the day it was written and is CORRECT there; flagging it would be flagging
# the estate for remembering. BUILDMAP is generated from the source every pass,
# so it cannot drift from the source by definition.
LEDGERS = frozenset({
    "CHANGELOG.md", "HANDOFF.md", "SEAT_LOG.md", "DAYBOOK.md",
    "REFUSALS.md", "TASKS.md", "memory.md", "BUILDMAP.md",
})

# `1971/1971`, `60/60` -- the same number twice is a suite tally, which is the
# shape his sitting-79 ruling named. Below 40 is a version fragment or a date,
# not a tally.
_TALLY = re.compile(r"\b(\d{2,5})\s*/\s*(\1)\b")

# A path counts only if it is written as one: backticked, with a separator and
# an extension. Bare prose words are not addresses, and guessing at them is how
# a check earns its false positives.
_PATH = re.compile(r"`([A-Za-z0-9_.\-]+(?:/[A-Za-z0-9_.\-]+)+\.[A-Za-z0-9]{1,5})`")


def living(ground: Path) -> list[Path]:
    """Every root doc that speaks in the present tense."""
    return sorted(p for p in Path(ground).glob("*.md") if p.name not in LEDGERS)


def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


# ---- the findings -------------------------------------------------------

def stale_tallies(ground: Path) -> list[tuple[str, int, str]]:
    """A living doc naming a suite tally.

    HIS RULING, sitting 79, after he swept six of these by hand: "No doc now
    names a suite tally except this file." The reason is in the same entry --
    `RUNBOOK:158  921/921 in the STALE example -> NNN/NNN, so a once-real
    number cannot read as a claim`. The number does not have to be WRONG to be
    a fault; it has to be a NUMBER, because the suites grow and the doc does
    not.
    """
    out: list[tuple[str, int, str]] = []
    for p in living(ground):
        for n, line in enumerate(read(p).splitlines(), 1):
            for m in _TALLY.finditer(line):
                if int(m.group(1)) >= 40:
                    out.append((p.name, n, line.strip()[:110]))
                    break
    return out


# THE BASES A DOC MAY BE WRITING FROM. SPEC_CONTROL_CENTER documents the Go
# tree and addresses it the way that tree addresses itself -- `webapp/db/db.go`
# means `atlas/webapp/db/db.go`, and `cmd/atlas-mcp/main.go` means
# `atlas/line/cmd/atlas-mcp/main.go`. A first cut resolved from the ground only
# and called 23 paths dead; 19 of them were alive one directory down. Reporting
# those would have buried the four that are really rotten.
_BASES = ("", "atlas", "atlas/line")


def dead_paths(ground: Path) -> list[tuple[str, int, str]]:
    """A living doc pointing at a file that is not there.

    The commonest way a doc rots with nobody noticing: the code moves and the
    sentence stays.

    ANYTHING UNDER .git/ IS SKIPPED. CLAUDE.md names `.git/index.lock` in the
    course of telling a hand never to create one; a file whose ABSENCE is the
    correct state must not be reported as a missing file.
    """
    ground = Path(ground)
    out: list[tuple[str, int, str]] = []
    for p in living(ground):
        for n, line in enumerate(read(p).splitlines(), 1):
            for m in _PATH.finditer(line):
                rel = m.group(1)
                if rel.startswith(("http", "//", ".git/")) or "/.git/" in rel:
                    continue
                if any((ground / b / rel).exists() for b in _BASES):
                    continue
                out.append((p.name, n, rel))
    return out


def skills_axis(ground: Path) -> list[str]:
    """Does the skill library agree with the code behind it?

    Asked of the LIBRARY, never of the filenames -- see the module docstring
    for the five false findings that rule bought.
    """
    from manjuel.skills import SkillLibrary, _HANDLERS

    faults: list[str] = []
    lib = SkillLibrary.load(Path(ground) / "skills")
    for w in lib.warnings:
        faults.append(f"skills/: {w}")
    declared = {s.keyword for s in lib.specs}
    for orphan in sorted(set(_HANDLERS) - declared):
        faults.append(f"handler `{orphan}` has no declaration in skills/ "
                      f"-- unreachable code")
    for s in lib.specs:
        if s.keyword not in _HANDLERS and not s.is_prompt_skill:
            faults.append(f"`{s.keyword}` ({s.filename}) has neither a handler "
                          f"nor a Model Target -- it cannot run either way")
    return faults


def versions(ground: Path) -> tuple[list[str], str]:
    """pyproject and the package must say the same number.

    Two places hold it, a bump touches one of them first, and the window
    between is exactly the conflict LAW 6 names.
    """
    ground = Path(ground)
    said: dict[str, str] = {}
    m = re.search(r'(?m)^version\s*=\s*"([^"]+)"',
                  read(ground / "pyproject.toml"))
    if m:
        said["pyproject.toml"] = m.group(1)
    m = re.search(r'(?m)^__version__\s*=\s*"([^"]+)"',
                  read(ground / "manjuel" / "__init__.py"))
    if m:
        said["manjuel/__init__.py"] = m.group(1)
    faults: list[str] = []
    if len(set(said.values())) > 1:
        faults.append("the version is not one number: "
                      + ", ".join(f"{k} says {v}"
                                  for k, v in sorted(said.items())))
    return faults, (sorted(said.values())[0] if said else "?")


def laws(ground: Path) -> tuple[str, list[str]]:
    """The chain, and any law sitting in law/ that it does not seal.

    Read IN-PROCESS through lawgate, never by spawning law.py: a child process
    inside the engine is measured unsafe here (2026-09-10, the boot gate that
    never returned). An unsealed law is not automatically a fault -- a law may
    be drafted before it is ruled -- so it is REPORTED, never failed.
    """
    from manjuel import lawgate

    ok, detail, sealed = lawgate.verify_chain(Path(ground))
    unsealed = sorted(p.name for p in (Path(ground) / "law").glob("*.md")
                      if p.name not in set(sealed))
    if ok is None:
        state = f"the chain could not be read: {detail}"
    elif ok:
        state = f"the chain is {detail}"
    else:
        state = f"THE CHAIN IS NOT WHOLE: {detail}"
    return state, unsealed


# ---- the record, for the doc pass ---------------------------------------

def daybook_last(ground: Path) -> tuple[str, bool]:
    """The DAYBOOK's newest entry heading, and whether it was closed.

    READ FIRST names this the only file that carries INTENT, and release.py
    already gates a tag on its last entry carrying **At close**. Same rule
    here, reported rather than enforced.
    """
    text = read(Path(ground) / "DAYBOOK.md")
    heads = [ln.strip() for ln in text.splitlines() if ln.startswith("## ")]
    if not heads:
        return "", False
    last = heads[-1].lstrip("# ").strip()
    tail = text.rsplit(heads[-1], 1)[-1]
    return last, "**At close**" in tail


def handoff_today(ground: Path, today: str) -> str:
    """Is there a HANDOFF block for today, and what is the newest one?"""
    text = read(Path(ground) / "HANDOFF.md")
    heads = re.findall(r"(?m)^##\s*HANDOFF FOR\s*(.+?)\s*$", text)
    if not heads:
        return ""
    return heads[0].strip() if today in text else heads[0].strip()


def unreleased(ground: Path) -> list[str]:
    """The CHANGELOG entry headings that have landed since the last tag."""
    text = read(Path(ground) / "CHANGELOG.md")
    m = re.search(r"(?ms)^##\s*\[?Unreleased\]?.*?$(.*?)(?=^##\s|\Z)", text)
    if not m:
        return []
    return [ln.strip().lstrip("#").strip()
            for ln in m.group(1).splitlines() if ln.startswith("### ")]


def sittings(ground: Path) -> tuple[dict | None, float, int, float, int]:
    """The open sitting if there is one, and what idle engines have cost.

    THE MEASUREMENT THIS EXISTS FOR, taken 2026-09-10 across the whole record:

        standup (>=9 runs)   58 sittings   14.9 engine-hours   775 runs    69 s/run
        working  (3-8 runs)  23 sittings    3.8 engine-hours   112 runs   122 s/run
        idle     (0-2 runs)  63 sittings    5.3 engine-hours    91 runs   208 s/run

    A standup gets THREE TIMES more work per engine-second than anything else;
    it was never the expensive thing. The expensive thing is booting an engine
    and then not using it. Sitting 74 held one thirty minutes for 2 runs, 82
    held one fifty-four minutes for 5, and 166 held one SIXTEEN MINUTES FOR
    ZERO -- that last was this hand, while the operator watched.

    Twenty-two sittings were never closed at all.

    `sessions.jsonl` has known all of this for weeks and NOTHING READ IT. The
    operator's word: "add the line." It is one line, and it would have caught
    this hand today.

    A closing line supersedes an opening one, so the file is folded by `n`
    before anything is counted -- reading it as a flat list would report every
    closed sitting as open.
    """
    import json as _json

    path = Path(ground) / "sessions" / "sessions.jsonl"
    if not path.is_file():
        return None, 0.0, 0, 0.0, 0
    seen: dict = {}
    for line in read(path).splitlines():
        if not line.strip():
            continue
        try:
            r = _json.loads(line)
        except ValueError:
            continue
        seen[r.get("n")] = r

    import datetime as _dt

    live, never, idle_secs, idle_runs, age = None, 0, 0.0, 0, 0.0

    # ONLY THE NEWEST SITTING CAN BE OPEN. A first cut took "the last unclosed
    # row" and reported sitting 99 -- ABANDONED the previous day -- as open for
    # 1,698 minutes. An older unclosed row is a sitting nobody ever tolled, not
    # an engine standing right now, and the two need different words. This is
    # the rule CLAUDE.md states: the LAST line without `ended` is the lock.
    newest = max(seen) if seen else None
    if newest is not None and not seen[newest].get("ended"):
        live = seen[newest]

    for r in seen.values():
        runs = len(r.get("runs") or ())
        if not r.get("ended"):
            never += 1
            continue
        try:
            a = _dt.datetime.fromisoformat(r["started"])
            b = _dt.datetime.fromisoformat(r["ended"])
        except (KeyError, ValueError):
            continue
        if runs <= 2:
            idle_secs += (b - a).total_seconds()
            idle_runs += runs
    if live:
        try:
            age = (_dt.datetime.now()
                   - _dt.datetime.fromisoformat(live["started"])).total_seconds()
        except (KeyError, ValueError):
            age = 0.0
    return live, age, never, idle_secs, idle_runs


def proofs(ground: Path) -> tuple[list, str]:
    """The file-readable half of the release gate, and why the rest is absent.

    THE SAME SIX git_cycle ASKS, and for the same reason: the other three
    (buildmap, law-by-the-tool, manifest) need a child process or the rack, and
    spawning python inside the engine is measured unsafe here -- a first cut of
    the boot gate did it on 2026-09-10 and never returned. These six are read
    off what the suites already stamped.
    """
    import importlib.util

    path = Path(ground) / "tests" / "release.py"
    spec = importlib.util.spec_from_file_location("_release_for_docpass", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    edited = mod.newest_edit(Path(ground))
    checks = list(mod.suites(Path(ground), edited))
    checks.append(mod.standup(Path(ground), edited))
    checks.append(mod.spec(Path(ground), None))
    checks.append(mod.daybook(Path(ground)))
    checks.append(mod.handoff(Path(ground)))
    return checks, ("buildmap, law and manifest need a child process or the "
                    "rack; this report spawns nothing and asks neither")


def open_tasks(ground: Path) -> list[tuple[str, str]]:
    """The lines of TASKS.md that are still on the table, as (mark, text).

    READ FIRST, item 6: a hand does not add work to this file. It is read here
    and never written, which is the only way a tool can keep that rule.

    `[~]` COUNTS. The file's own legend reads `[ ] open  [~] in hand  [x]
    landed, stroked` -- something in hand is on the table as much as something
    untouched, and dropping it would under-report his day.

    THE LEGEND ITSELF IS NOT A TASK. It carries all three marks on one line,
    and a first cut reported it as the first open item. One mark per line is
    what tells a task from the key that explains them.
    """
    out: list[tuple[str, str]] = []
    for ln in read(Path(ground) / "TASKS.md").splitlines():
        s = ln.strip()
        if sum(s.count(m) for m in ("[ ]", "[~]", "[x]")) != 1:
            continue
        for mark in ("[ ]", "[~]"):
            if s.startswith(mark):
                out.append((mark, s[3:].strip()[:120]))
                break
    return out


# =====================================================================
# THE TWO REPORTS
#
# THESE ARE NOT SKILLS, AND THAT IS THE POINT.
#
# They were skills for about an hour on 2026-09-10 and the cost landed
# somewhere nobody would look for it: THE ROUTER'S SHORTLIST. Both describe
# the record -- DAYBOOK, CHANGELOG, law chain, doctrine, foundational docs --
# and this estate's commonest question IS about the record, so they outranked
# the right answer on every doc question the moment they existed:
#
#     what does the covenant say?  ->  doc_pass, doctrine_check, git_commit,
#                                      skill_search, git_cycle, inspect
#     what do the laws say         ->  search_transcripts, doc_pass,
#                                      doctrine_check, git_commit, git_cycle
#     read the spec                ->  doc_pass, git_cycle, inspect, read_file
#
# `semantic_search` -- the correct tool -- was not offered AT ALL. The Router
# reached it only by reasoning off the raw keyword line, and burned its whole
# thinking budget doing so: 1,625 chars against the 7,400-9,400 of every run
# that had worked that morning, cut off mid-sentence just after concluding it
# should search. A standup case green at 09:05 and 09:33 went to no tool at
# 09:59 and 10:10.
#
# THE OPERATOR NAMED THE FAULT BEFORE I DID: "you have too many knobs" --
# the core was being tuned to serve a control-plane feature, and every turn
# the engine will ever run was paying for it. Tuning the descriptions was one
# more knob on the same screw.
#
# So they are arithmetic that atlas calls, not skills the Router weighs. No
# model, no judgement, no roster cost, no seat. Run them directly:
#
#     python -m manjuel.doctrine            where the estate stands
#     python -m manjuel.doctrine --check    the doctrine check
# =====================================================================

def doc_pass_report(ground: Path) -> str:
    """WHERE THIS ESTATE STANDS, AND WHAT IS ON THE TABLE.

    His ask, 2026-09-10: "a review of the current daybook runbook, etc. and
    then a check of where the repo is at, and a short brief about whats on the
    table." That is a pass a hand did by opening six files in order, and a pass
    done by hand is a pass that gets skipped on the day it matters.

    EVERY LINE IS READ. The DAYBOOK's newest heading and whether it was closed,
    the HANDOFF's newest block, the CHANGELOG's Unreleased entries, the OPEN
    lines of TASKS, the repository through gitstate, and the six proofs the
    boot report reads. Nothing here is generated, and no seat is asked what it
    thinks the state is -- which is the whole reason the skill exists rather
    than a prompt.

    IT NEVER WRITES TASKS.md. READ FIRST, item 6, is explicit that a hand does
    not add work to that file; a tool that could would be the fastest possible
    way to break it.
    """
    import datetime as _dt

    ground = Path(ground)
    out: list[str] = []

    # ---- 1. THE RECORD --------------------------------------------------
    out.append("THE RECORD")
    entry, closed = daybook_last(ground)
    if entry:
        out.append(f"  DAYBOOK    {entry[:88]}")
        out.append("             " + ("closed (**At close** is written)" if closed
                                       else "NOT CLOSED -- the last entry has no **At close**"))
    else:
        out.append("  DAYBOOK    no entry found")
    today = _dt.date.today().isoformat()
    text = read(ground / "HANDOFF.md")
    newest = handoff_today(ground, today)
    out.append(f"  HANDOFF    newest block: {newest or 'none'}"
               + ("" if f"HANDOFF FOR {today}" in text
                  else f"   (nothing for {today})"))
    rel = unreleased(ground)
    out.append(f"  CHANGELOG  {len(rel)} entries under Unreleased")
    tasks = open_tasks(ground)
    in_hand = sum(1 for m, _ in tasks if m == "[~]")
    out.append(f"  TASKS      {len(tasks)} on the table"
               + (f" ({in_hand} in hand)" if in_hand else ""))

    # THE LINE. An engine that is open and doing nothing is the most expensive
    # thing in this record -- 63 idle sittings cost 5.3 engine-hours for 91
    # runs, against a standup's 69 seconds per run -- and nothing has ever read
    # sessions.jsonl to say so. An open sitting with no runs is named outright,
    # because that is the shape the fault takes every time.
    live, age, never, idle_secs, idle_runs = sittings(ground)
    if live:
        runs = len(live.get("runs") or ())
        mins = age / 60.0
        line = (f"  SITTING    {live.get('n')} OPEN — {mins:.0f} min, "
                f"{runs} run{'' if runs == 1 else 's'}")
        if runs == 0 and mins >= 5:
            line += "   ** an engine open and doing nothing **"
        elif runs and age / runs > 300:
            line += f"   ** {age / runs / 60:.0f} min per run **"
        out.append(line)
    else:
        out.append("  SITTING    none open")
    if never or idle_secs:
        out.append(f"             {never} never closed · {idle_secs / 3600:.1f} "
                   f"engine-hours in sittings of 2 runs or fewer "
                   f"({idle_runs} runs)")

    # ---- 2. THE REPO ----------------------------------------------------
    out.append("")
    out.append("THE REPO")
    st = gitstate.read(ground)
    out.append(f"  {st.stamp()}")
    local, remote, why = gitstate.head_and_remote(ground)
    if remote and local:
        agree = "they agree" if local == remote else "** THEY DISAGREE **"
        out.append(f"  local {local} · remote {remote} — {agree}")
    else:
        out.append(f"  the remote head could not be read"
                   + (f" ({why})" if why else ""))
    _v, version = versions(ground)
    out.append(f"  version {version}")

    # ---- 3. THE PROOFS --------------------------------------------------
    out.append("")
    try:
        checks, caveat = proofs(ground)
    except Exception as exc:
        out.append(f"THE PROOFS  could not be read ({type(exc).__name__}: {exc})")
    else:
        bad = [c for c in checks if not c.ok]
        out.append(f"THE PROOFS  {len(checks) - len(bad)}/{len(checks)} read here "
                   f"({caveat})")
        for c in checks:
            out.append(f"  {'ok     ' if c.ok else 'REFUSED'} {c.name:9} {c.why}")

    # ---- 4. ON THE TABLE ------------------------------------------------
    out.append("")
    out.append("ON THE TABLE")
    if rel:
        out.append(f"  landed since the last tag ({len(rel)}):")
        for e in rel:
            out.append(f"    · {e[:96]}")
    else:
        out.append("  nothing under Unreleased -- the last tag is current.")
    if tasks:
        out.append(f"  open in TASKS ({len(tasks)}) — his list, read and never written:")
        for mark, t in tasks[:12]:
            out.append(f"    {mark} {t}")
        if len(tasks) > 12:
            out.append(f"    … and {len(tasks) - 12} more in TASKS.md")
    else:
        out.append("  TASKS has nothing on the table.")
    return "\n".join(out)


def doctrine_report(ground: Path) -> str:
    """DOES THE RECORD STILL DESCRIBE WHAT THE SYSTEM PERFORMS?

    HIS LAW 6, made mechanical: "all version bumps and iterative changes come
    with an update to the documentation and reflection within the system,
    ensuring a review pass is made so that there are no conflicts within what
    the system states and actually performs."

    IT IS ARITHMETIC, NOT A READING. `deep_research` would seat the Deep
    Researcher and ask it to reason about the corpus; that is the wrong engine
    and a dangerous one, because a model asked to find discrepancies it cannot
    verify will invent them. Every finding here is a comparison between two
    things on disk, and each one prints its own address so he can check it.

    WHAT IT DOES NOT DUPLICATE. release.py already gates the law chain, the
    manifest, SPEC against the CHANGELOG, the DAYBOOK and the HANDOFF, and
    `proved` already reports the suites. This asks the axis nothing else does:
    whether the LIVING docs -- the ones speaking in the present tense -- still
    match the ground under them.
    """
    ground = Path(ground)
    out: list[str] = []
    findings = 0

    docs = living(ground)
    out.append("THE DOCTRINE CHECK — what the docs state vs what the ground performs")
    out.append(f"  read across {len(docs)} living docs; {len(LEDGERS)} dated "
               f"ledgers skipped, because a number in a ledger is a true record "
               f"of its day, not a claim about now")

    # ---- the sealed laws ------------------------------------------------
    out.append("")
    try:
        state, unsealed = laws(ground)
    except Exception as exc:
        out.append(f"THE LAW CHAIN   could not be read ({type(exc).__name__}: {exc})")
    else:
        out.append(f"THE LAW CHAIN   {state}")
        if unsealed:
            out.append(f"  drafted but NOT SEALED: {', '.join(unsealed)}")
            out.append("  (not a fault — a law may be written before it is ruled. "
                       "Sealing is his, RULE 6.)")

    # ---- the skills -----------------------------------------------------
    try:
        faults = skills_axis(ground)
    except Exception as exc:
        out.append(f"THE SKILLS      could not be read ({type(exc).__name__}: {exc})")
    else:
        if faults:
            findings += len(faults)
            out.append("THE SKILLS      DISAGREE with the code behind them:")
            for f in faults:
                out.append(f"  {f}")
        else:
            out.append("THE SKILLS      the library and the handlers agree")

    # ---- the version ----------------------------------------------------
    vfaults, version = versions(ground)
    if vfaults:
        findings += len(vfaults)
        for f in vfaults:
            out.append(f"THE VERSION     {f}")
    else:
        out.append(f"THE VERSION     {version}, said the same by every file that holds it")

    # ---- a tally in a living doc ----------------------------------------
    out.append("")
    tallies = stale_tallies(ground)
    if tallies:
        findings += len(tallies)
        out.append(f"A SUITE TALLY IN A LIVING DOC ({len(tallies)})")
        out.append("  His ruling, sitting 79: no doc names a suite tally, because "
                   "the suites grow and the doc does not — so a once-real number "
                   "comes to read as a claim.")
        for f, n, line in tallies:
            out.append(f"  {f}:{n}")
            out.append(f"      {line}")
    else:
        out.append("A SUITE TALLY IN A LIVING DOC   none — the sitting-79 ruling holds")

    # ---- a path that is not there ---------------------------------------
    out.append("")
    dead = dead_paths(ground)
    if dead:
        findings += len(dead)
        out.append(f"A PATH THAT IS NOT THERE ({len(dead)})")
        out.append("  Resolved against the ground, atlas/ and atlas/line/ before "
                   "being called dead, because the Go docs address their own tree.")
        for f, n, rel in dead:
            out.append(f"  {f}:{n}   {rel}")
    else:
        out.append("A PATH THAT IS NOT THERE   none — every address in the living docs resolves")

    out.append("")
    out.append(f"{findings} finding(s). Each names its file and line; none is a judgement."
               if findings else
               "No findings. What the docs state and what the ground performs agree.")
    return "\n".join(out)

def main(argv: list[str] | None = None) -> int:
    """Both reports, from the command line and from atlas. Reads; never writes."""
    import sys
    argv = list(sys.argv[1:] if argv is None else argv)
    ground = Path(".")
    if "--ground" in argv:
        ground = Path(argv[argv.index("--ground") + 1])
    print(doctrine_report(ground) if "--check" in argv
          else doc_pass_report(ground))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
