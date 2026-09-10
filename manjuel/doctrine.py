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
                    "rack and are not asked from inside the engine")


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
