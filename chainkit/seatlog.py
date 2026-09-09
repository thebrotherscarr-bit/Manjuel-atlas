"""Sessions and the toll.

A SITTING is one REPL launch. Sittings are numbered monotonically and recorded
in `sessions/sessions.jsonl` (append-only, one line each), so a session id is
not just a timestamp but a version with an ordinal, a git stamp, and the runs
it produced.

Every sitting pays its toll: an entry in `SEAT_LOG.md` saying WHAT PROVED,
WHAT IS THIN, and WHAT IS OWED (LAW 10). The log is append-only -- entries are
added below, never rewritten above.

What the toll states as fact is only what was observed: runs, stages, models,
timings, git state. "Thin" and "owed" are judgment, so they come from the
operator, and an unattended close says so rather than inventing them.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path

from . import gitstate

SEAT_LOG = "SEAT_LOG.md"
SESSIONS = Path("sessions") / "sessions.jsonl"

HEADER = (
    "# SEAT_LOG — chainkit\n\n"
    "### The toll of every sitting. Append below; never rewrite above.\n"
    "### The full record of a sitting is its transcripts in `logs/`;\n"
    "### this is the spine, not the body.\n\n"
    "---\n"
)


@dataclass
class RunNote:
    objective: str
    pipeline: str
    stages: int
    failed: int
    elapsed: float
    transcript: str
    # THE STORY'S FIELDS (0.1.6, 2026-09-08). The ledger line is the WAL
    # -- the operator: "the WAL, and the on-turn indexing ... is just
    # building out empirical context for the agent to run on." A run's
    # tools, the guards that fired, the seats that failed or ran out of
    # time, and the first line of what was delivered are written as the
    # run ends, so the sitting story (story_block) is READ off the ledger
    # and never remembered by a seat. Older lines lack them; they read
    # as empty.
    tools: list = field(default_factory=list)
    guards: list = field(default_factory=list)
    seats_failed: list = field(default_factory=list)
    out_of_time: list = field(default_factory=list)
    delivery: str = ""


# Notes that mean a guard fired. Kept as substrings of the notes as the
# pipeline writes them (tests/standup.py keeps the same list for the same
# reason: a renamed note shows up as a miss, not as silence).
GUARD_MARKS = (
    "carried to the Router", "discarded", "recited the conversation scaffold",
    "replied with control markup", "REFUSED", "claimed the contents",
    "said it wrote", "cited", "already ran this turn", "LAW 8 gate refused",
    "recompose:", "hard gate:", "gate:", "technical flag set aside",
    "judged the work unfinished", "empty reply", "not seated", "decided by arithmetic",
)


def note_for(ctx, pipeline: str, transcript: str) -> RunNote:
    """The ledger line for one run, read off its RunContext as it ends."""
    steps = list(getattr(ctx, "steps", []) or [])
    notes = list(getattr(ctx, "notes", []) or [])
    delivery = ""
    try:
        delivery = " ".join((ctx.last_output() or "").split())[:200]
    except Exception:
        pass
    return RunNote(
        objective=str(getattr(ctx, "objective", "")),
        pipeline=pipeline,
        stages=len(steps),
        failed=sum(1 for s in steps if getattr(s, "error", None)),
        elapsed=float(getattr(ctx, "elapsed", 0.0) or 0.0),
        transcript=transcript,
        tools=sorted({k for s in steps for k in (getattr(s, "tool_calls", None) or ())}),
        guards=[n[:120] for n in notes if any(m in n for m in GUARD_MARKS)][:8],
        seats_failed=[s.agent for s in steps if getattr(s, "error", None)],
        out_of_time=list(getattr(ctx, "out_of_time", []) or []),
        delivery=delivery,
    )


@dataclass
class Sitting:
    n: int
    id: str
    started: str
    ground: str = ""
    git_start: dict = field(default_factory=dict)
    runs: list = field(default_factory=list)
    ended: str = ""
    git_end: dict = field(default_factory=dict)
    toll_paid: bool = False

    @property
    def label(self) -> str:
        return f"sitting {self.n} · {self.id}"


def _sessions_path(ground: Path) -> Path:
    return Path(ground) / SESSIONS


def all_sittings(ground: Path) -> list[dict]:
    p = _sessions_path(ground)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def next_number(ground: Path) -> int:
    prior = all_sittings(ground)
    return (max((s.get("n", 0) for s in prior), default=0)) + 1


def open_sitting(ground: Path, session_id: str) -> Sitting:
    ground = Path(ground)
    st = Sitting(
        n=next_number(ground),
        id=session_id,
        started=datetime.now().isoformat(timespec="seconds"),
        ground=str(ground),
        git_start=gitstate.read(ground).as_dict(),
    )
    return st


def record(ground: Path, sitting: Sitting) -> None:
    """Append/refresh the sitting's line. The ledger is append-only, so a
    closing line supersedes an opening one rather than editing it."""
    p = _sessions_path(ground)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8", newline="\r\n") as f:
        f.write(json.dumps(asdict(sitting), ensure_ascii=False) + "\n")


def close_sitting(ground: Path, sitting: Sitting) -> Sitting:
    sitting.ended = datetime.now().isoformat(timespec="seconds")
    sitting.git_end = gitstate.read(ground).as_dict()
    return sitting


# ---------------------------------------------------------------------
# the standing
# ---------------------------------------------------------------------

DAYBOOK = "DAYBOOK.md"
STANDING_CHARS = 1800
_SESSION_HEAD = "\n## Session "
# The fields of a DAYBOOK entry that say what the sitting is FOR. The
# rest of an entry is what happened, and the transcripts hold that.
_STANDING_FIELDS = ("**Standing**", "**The plan**", "**Next session**")


def standing_block(ground: Path, chars: int = STANDING_CHARS) -> str:
    """What this sitting is for, from the LAST entry of DAYBOOK.md.

    CLAUDE.md READ FIRST, for the seats (the operator, 2026-09-07): the
    hand begins every turn with total amnesia and DAYBOOK's last entry is
    "the only file that carries intent". The seats begin every run the same
    way, and sitting 87's toll named the cost: "needs more context and
    reasoning intent." This is that entry's Standing, plan and next-session
    lines, bounded, labelled as RECORD -- built once at sitting open by the
    CLI and handed to the door and the court (pipeline.carried_blocks).

    Read, never generated: no model touches it, and a DAYBOOK with no
    entry yields "" and no block. Bounded on purpose -- an entry can run to
    pages, and this rides on prompts whose windows are 8192."""
    path = Path(ground) / DAYBOOK
    if not path.is_file():
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    at = text.rfind(_SESSION_HEAD)
    if at == -1:
        return ""
    entry = text[at + 1:]
    head, _, body = entry.partition("\n")
    keep: list[str] = []
    take = False
    for line in body.splitlines():
        line = line.rstrip()
        if line.startswith("**"):
            take = line.startswith(_STANDING_FIELDS)
        if take and line.strip():
            keep.append(line)
    if not keep:
        return ""
    picked = "\n".join(keep)
    if len(picked) > chars:
        picked = picked[:chars].rsplit(" ", 1)[0] + " ..."
    return ("## Standing -- what this sitting is for, from DAYBOOK.md "
            "(the record, not a model's words)\n"
            f"{head.strip()}\n{picked}")


# ---------------------------------------------------------------------
# the story
# ---------------------------------------------------------------------

STORY_CHARS = 1800


def story_block(sitting: Sitting, chars: int = STORY_CHARS) -> str:
    """What THIS sitting has done so far, read off its ledger runs.

    THE SITTING STORY (0.1.6; the operator, 2026-09-07 and 2026-09-08).
    Sitting 93: "What happened? Why did you suck so bad?" went to a
    semantic search over the whole record and came back "the operator
    doesn't have access to see previous outputs in this session." No
    seat was handed what this sitting had done -- the standing carries
    the SESSION's intent, the dialogue carries the words, and the runs
    between them were nowhere. This block is those runs: objective,
    seconds, tools, the guards that fired, seats that failed or ran out
    of time, and the first line delivered -- the WAL, bounded like a
    window. Newest last. When the runs outgrow the budget the OLDEST are
    folded into one counted line and the seat is told where the rest
    is: the transcripts in logs/, reachable by semantic_search. Read,
    never generated; a sitting with no runs yields "" and no block.

    Handed to the door and the court beside the law and the standing
    (pipeline.carried_blocks). Not the Router: it routes; it does not
    narrate the day."""
    runs = list(getattr(sitting, "runs", []) or [])
    if not runs:
        return ""
    lines: list[str] = []
    for i, r in enumerate(runs, 1):
        bits = [f"{float(r.get('elapsed') or 0):.0f}s"]
        if r.get("tools"):
            bits.append("tools: " + ", ".join(r["tools"]))
        if r.get("seats_failed"):
            bits.append("FAILED: " + ", ".join(r["seats_failed"]))
        elif r.get("failed"):
            bits.append(f"{r['failed']} stage(s) FAILED")
        if r.get("out_of_time"):
            bits.append("OUT OF TIME: " + ", ".join(r["out_of_time"]))
        line = f"{i}. {str(r.get('objective', ''))[:80]}  ({'; '.join(bits)})"
        guards = [g for g in (r.get("guards") or [])
                  if not g.startswith("law: chain whole")]
        if guards:
            line += "\n   guards: " + " | ".join(g[:80] for g in guards[:3])
        if r.get("delivery"):
            line += f"\n   -> {r['delivery'][:140]}"
        lines.append(line)
    # Fold the oldest until the newest fit the window.
    folded = 0
    while lines and sum(len(l) + 1 for l in lines) > chars and len(lines) > 1:
        lines.pop(0)
        folded += 1
    head = ("## The sitting so far -- what THIS sitting has done, from the "
            "ledger (the record, not a model's words)\n"
            f"sitting {sitting.n}, {len(runs)} run{'' if len(runs) == 1 else 's'} "
            f"since it opened at {sitting.started[11:16] if len(sitting.started) > 15 else sitting.started}. "
            "When asked what happened, answer from this and name the run.")
    if folded:
        head += (f"\n({folded} earlier run{'' if folded == 1 else 's'} folded; "
                 f"their transcripts are in logs/ and reachable by semantic_search)")
    return head + "\n" + "\n".join(lines)


# ---------------------------------------------------------------------
# the hands
# ---------------------------------------------------------------------

HANDS = Path("sessions") / "hands.jsonl"
_HAND_READS = ("CLAUDE.md", "law/SITTING_LAWS.md", "law/SITTING_LAWS_2.md",
               "law/ESTATE_LAWS.md", "law/LAW_001_FOUNDING.md", "law/LAW_002_THE_TWELVE.md")


def _sha(path: Path) -> str:
    import hashlib
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    except OSError:
        return ""


def _last_heading(path: Path, prefix: str) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    at = text.rfind("\n" + prefix)
    if at == -1:
        return ""
    return text[at + 1:].split("\n", 1)[0].strip()[:100]


def _first_heading(path: Path, prefix: str) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    at = text.find("\n" + prefix)
    if at == -1:
        return ""
    return text[at + 1:].split("\n", 1)[0].strip()[:100]


def hands_path(ground: Path) -> Path:
    return Path(ground) / HANDS

# What the ledger will NOT attribute to a hand: derived state, files the
# engine rewrites every run, and trees that are not the estate's source.
_EDIT_SKIP_DIRS = {".git", "logs", "index", "sessions", "__pycache__",
                   "agent_workspace", "bin", "worlds", ".venv", "build",
                   "dist", "node_modules", "target"}
_EDIT_SKIP_FILES = {"tests/last_run.json", "tests/last_run.md",
                    "tests/last_audit.md", "tests/run_history.jsonl",
                    "SEAT_LOG.md", "memory.md", "rack.md", "BUILDMAP.md"}
_EDIT_CAP = 200


def edits_since(ground: Path, since: str) -> list[str]:
    """Ground-relative paths whose mtime falls at or after `since`.

    0.1.6+, G4 (the operator, 2026-09-09: "make sure every step taken is
    recorded in the logs ... keep everything on record and usable by the
    next agent"). Every close before this one recorded `0 file(s) edited`
    unless the hand remembered a flag, and a close that says nothing tells
    the next hand nothing.

    NO GIT, DELIBERATELY. `git status` and `git diff` refresh the index and
    from a sandboxed mount leave `.git/index.lock` the mount cannot remove
    -- CLAUDE.md's first trap, and the exact fault the first hand_close
    ever run committed (2026-09-08 12:56). mtime needs no repository,
    leaves no lock, and answers on a ground that is not one.

    IT CANNOT SEE WHO. A file the operator changed while a hand was open is
    reported here too. That is the honest trade: an over-report a reader can
    discount beats a silent empty list claiming a hand that rewrote four
    files touched nothing. The line stamps `edited_by: observed` so the
    number is never read as the hand's own claim -- a named `--edited`
    stamps `named` and always wins (LAW 5: what a hand says of itself is
    testimony; what the disk says is fact, and this says which is which).
    """
    import os
    try:
        cut = datetime.fromisoformat(since).timestamp()
    except (TypeError, ValueError):
        return []
    ground = Path(ground)
    out: list[str] = []
    for root, dirnames, filenames in os.walk(ground):
        dirnames[:] = [d for d in dirnames
                       if d not in _EDIT_SKIP_DIRS and not d.endswith(".egg-info")]
        for fn in filenames:
            p = Path(root) / fn
            try:
                rel = p.relative_to(ground).as_posix()
                if rel in _EDIT_SKIP_FILES:
                    continue
                if p.stat().st_mtime >= cut:
                    out.append(rel)
            except (OSError, ValueError):
                continue
            if len(out) > _EDIT_CAP:
                return sorted(out)[:_EDIT_CAP]
    return sorted(out)


def hand_open(ground: Path, hand: str = "claude", note: str = "") -> dict:
    """THE HANDS LEDGER, the opening line (0.1.6; the operator, 2026-09-08:
    "every new session with you 'restarts' the process, there has to be a
    way to get you back in line with the actual build").

    A seat's sitting has a ledger line (sessions.jsonl) and a hand's did
    not: what a hand read, in what order, before it touched anything was
    recorded only in prose it wrote about itself afterwards -- and on
    2026-09-08 a hand ran `git status` before reading CLAUDE.md and left
    the lock the file warns of. This line is written FIRST, and records
    the rules AS READ (their fingerprints), HEAD, the DAYBOOK entry and
    the HANDOFF block the hand read, and the newest sitting it saw. A hand
    with no opening line has not opened -- the same rule as RULE 9's "no
    `ended`, no edit". Append-only; a closing line supersedes it."""
    ground = Path(ground)
    # head_only, NEVER read(): a hand writes this from a sandbox, and
    # `git status` from there leaves the lock (2026-09-08 12:56, the first
    # hand_close ever run did exactly that).
    g = gitstate.head_only(ground)
    line = {
        "hand": hand,
        "id": f"H{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "opened": datetime.now().isoformat(timespec="seconds"),
        "read": {name: _sha(ground / name) for name in _HAND_READS},
        "head": g.short,
        "daybook": _last_heading(ground / DAYBOOK, "## Session "),
        "handoff": _first_heading(ground / "HANDOFF.md", "## HANDOFF FOR "),
        "sitting_seen": next_number(ground) - 1,
        "note": note,
        "closed": "",
    }
    p = hands_path(ground)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8", newline="\r\n") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")
    return line


def open_hands(ground: Path) -> list[dict]:
    """Every hand line whose id has no closing line yet, oldest first."""
    p = hands_path(ground)
    if not p.is_file():
        return []
    by_id: dict = {}
    for raw in p.read_text(encoding="utf-8", errors="replace").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            line = json.loads(raw)
        except ValueError:
            continue
        by_id[line.get("id", raw[:20])] = line       # the last line for an id wins
    return [l for l in by_id.values() if not l.get("closed")]


def hand_close(ground: Path, edited: list | None = None, strokes: str = "",
               restart_required: bool = False, note: str = "",
               hand: str = "", hand_id: str = "") -> dict:
    """The closing line: the same id, plus what the hand did.

    Two hands can be open at once (the operator's and a sandbox hand's,
    2026-09-08 13:04 and 13:05). The one closed is the one named by
    `hand_id`, else the newest open line for `hand`, else the newest open
    line -- never the newest line regardless, which closed the wrong hand."""
    ground = Path(ground)
    opened = open_hands(ground)
    if hand_id:
        opened = [l for l in opened if l.get("id") == hand_id]
    elif hand:
        opened = [l for l in opened if l.get("hand") == hand] or opened
    if not opened:
        raise RuntimeError("no open hand session to close (hand-open first)")
    last = opened[-1]
    g = gitstate.head_only(ground)
    # G4: a hand that names its edits is believed; a hand that names
    # none is OBSERVED off the disk rather than recorded as nothing.
    named = sorted(e for e in (edited or []) if str(e).strip())
    seen = named or edits_since(ground, last.get("opened", ""))
    line = dict(last)
    line.update({
        "closed": datetime.now().isoformat(timespec="seconds"),
        "head_at_close": g.short,
        "edited": seen,
        "edited_by": "named" if named else "observed",
        "strokes": strokes,
        "restart_required": bool(restart_required),
        "close_note": note,
    })
    with hands_path(ground).open("a", encoding="utf-8", newline="\r\n") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")
    return line


def last_hand(ground: Path) -> dict | None:
    p = hands_path(ground)
    if not p.is_file():
        return None
    last = None
    for raw in p.read_text(encoding="utf-8", errors="replace").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            last = json.loads(raw)
        except ValueError:
            # NAMED, not swallowed: a corrupt line is a fact about the file.
            last = {"hand": "?", "corrupt": raw[:60], "closed": ""}
    return last


def hands_line(ground: Path) -> str:
    """One line for the brief: the last hand, open or closed, and what it did.
    Every OPEN hand is named, not just the newest line."""
    h = last_hand(ground)
    if not h:
        return "    hands    none recorded yet (sessions/hands.jsonl)"
    if h.get("corrupt"):
        return f"    hands    !! a corrupt line in hands.jsonl: {h['corrupt']}"
    still = open_hands(ground)
    if still:
        names = ", ".join(f"{l.get('hand')} {l.get('id')} since {str(l.get('opened', '?'))[11:16]}"
                          for l in still)
        return (f"    hands    !! OPEN: {names} -- a hand that did not close left work "
                f"unrecorded (hand-close --id <id>)")
    if h.get("closed"):
        n = len(h.get("edited") or [])
        return (f"    hands    {h.get('hand')} closed {h['closed'][:16]} at {h.get('head_at_close', '?')}; "
                f"edited {n} file{'' if n == 1 else 's'}; strokes {h.get('strokes') or '?'}"
                f"{'; RESTART REQUIRED' if h.get('restart_required') else ''}")
    return f"    hands    {h.get('hand')} {h.get('id')} (state unclear)"


# ---------------------------------------------------------------------
# the toll
# ---------------------------------------------------------------------


def summarize(sitting: Sitting) -> str:
    """The observed facts of the sitting. No judgment in here."""
    if not sitting.runs:
        return "  no runs."
    lines = []
    for i, r in enumerate(sitting.runs, 1):
        flag = f"  {r['failed']} stage(s) FAILED" if r.get("failed") else ""
        lines.append(
            f"  {i}. {r['objective'][:64]}\n"
            f"     {r['pipeline']} · {r['stages']} stages · "
            f"{r['elapsed']:.1f}s · {r['transcript']}{flag}"
        )
    return "\n".join(lines)


def render_toll(
    sitting: Sitting,
    proved: str = "",
    thin: str = "",
    owed: str = "",
    attended: bool = True,
) -> str:
    g0 = gitstate.GitState(**sitting.git_start) if sitting.git_start else gitstate.GitState()
    g1 = gitstate.GitState(**sitting.git_end) if sitting.git_end else g0

    day = (sitting.ended or sitting.started)[:10]
    title = proved.strip().splitlines()[0][:70] if proved.strip() else "a sitting"

    # A sitting may be tolled more than once: pay, run one more thing, pay
    # again (`_cmd_toll` offers it). Sitting 57 did exactly that and the two
    # entries came out byte-identical in the head, so a reader could not tell
    # a deliberate re-toll from a double write. Say which it is. The earlier
    # entry stands -- LAW 1, nothing above is rewritten.
    retoll = sitting.toll_paid

    out = [
        f"\n## {day} — sitting {sitting.n}{' (re-tolled)' if retoll else ''} — {title}",
        "",
        f"**The seat:** chainkit REPL, session `{sitting.id}`, "
        f"{sitting.started[11:16]}–{(sitting.ended or sitting.started)[11:16]}. "
        f"{'Operator present.' if attended else 'Closed unattended.'}",
        "",
    ]
    if retoll:
        out += [
            "**A toll for this sitting already stands above.** This one is later "
            "and supersedes it; the earlier entry is kept, not corrected.",
            "",
        ]
    out += [
        f"**Version:** {g0.stamp()}",
    ]
    if g1.head and g1.head != g0.head:
        out.append(f"**At close:** {g1.stamp()}")
    elif g1.dirty != g0.dirty:
        out.append(f"**At close:** {g1.stamp()}")

    out += ["", "**WHAT RAN** (observed)", "", summarize(sitting), ""]

    if proved.strip():
        out += ["**WHAT PROVED**", "", proved.strip(), ""]
    if thin.strip():
        out += ["**WHAT IS THIN**", "", thin.strip(), ""]
    if owed.strip():
        out += ["**WHAT IS OWED**", "", owed.strip(), ""]

    if not attended and not (thin.strip() or owed.strip()):
        out += [
            "**WHAT IS THIN / OWED**", "",
            "Not stated — the sitting closed without the operator paying the "
            "toll by hand. What ran above is observed; nothing here is a "
            "judgment about it.", "",
        ]
    return "\n".join(out)


def pay(ground: Path, text: str) -> Path:
    """Append the toll. Never rewrites what stands above it."""
    p = Path(ground) / SEAT_LOG
    if not p.exists():
        p.write_text(HEADER, encoding="utf-8", newline="\r\n")
    with p.open("a", encoding="utf-8", newline="\r\n") as f:
        f.write(text)
    return p


def main(argv: list | None = None) -> int:
    """The hand's own door to the ledger.

        python -m chainkit.seatlog hand-open  [--hand NAME] [--note WORDS]
        python -m chainkit.seatlog hand-close [--edited a,b,c] [--strokes N/N]
                                              (no --edited: the ledger reads
                                               mtimes since the open and says
                                               `observed` -- never `nothing`)
                                              [--restart] [--note WORDS]
                                              [--hand NAME | --id H...]
        python -m chainkit.seatlog hands              the last hand line
    """
    import sys
    argv = list(sys.argv[1:] if argv is None else argv)
    ground = Path(__file__).resolve().parent.parent
    if not argv or argv[0] not in ("hand-open", "hand-close", "hands"):
        print(main.__doc__)
        return 2
    cmd, rest = argv[0], argv[1:]
    opts: dict = {}
    i = 0
    while i < len(rest):
        k = rest[i]
        if k == "--restart":
            opts["restart"] = True
            i += 1
        elif k.startswith("--") and i + 1 < len(rest):
            opts[k[2:]] = rest[i + 1]
            i += 2
        else:
            i += 1
    if cmd == "hands":
        print(hands_line(ground))
        return 0
    if cmd == "hand-open":
        line = hand_open(ground, hand=opts.get("hand", "claude"), note=opts.get("note", ""))
        print(f"  hand {line['id']} opened at {line['head']}; read "
              + ", ".join(f"{k} {v}" for k, v in line["read"].items())
              + f"; DAYBOOK: {line['daybook'][:50]}; sitting seen {line['sitting_seen']}")
        return 0
    try:
        line = hand_close(ground,
                          edited=[e for e in (opts.get("edited") or "").split(",") if e],
                          strokes=opts.get("strokes", ""),
                          restart_required=bool(opts.get("restart")),
                          note=opts.get("note", ""),
                          hand=opts.get("hand", ""), hand_id=opts.get("id", ""))
    except RuntimeError as exc:
        print(f"  {exc}")
        return 1
    print(f"  hand {line['id']} closed at {line['head_at_close']}; "
          f"{len(line['edited'])} file(s) edited ({line.get('edited_by', 'named')})"
          f"; strokes {line['strokes'] or '?'}"
          f"{'; RESTART REQUIRED' if line['restart_required'] else ''}")
    if line["edited"] and line.get("edited_by") == "observed":
        print("    observed off mtimes since the open, not claimed by the "
              "hand: " + ", ".join(line["edited"][:8])
              + (" ..." if len(line["edited"]) > 8 else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
