"""Interactive REPL."""

from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

from .context import RunContext, StepResult, select_dialogue
from .pipeline import Aborted, Refused, DEFAULT_PIPELINE, PIPELINES, run_pipeline
from .registry import AgentRegistry, PipelineBook, RegistryError
from .runtime import BackendUnreachable, OllamaRuntime, RuntimeError_
from .skills import SkillExecutionEnv, SkillLibrary
from . import transcript
from . import memory as _mem
from . import seatlog as _log
from . import gitstate
from .drift import DriftChecker
from . import vram
from . import dotenv
from . import boot
from . import ink
from . import seating
from . import watch as _watch
from . import spelling
from . import parity
from . import voice
from .skills import EMBED_MODEL

ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = ROOT / "agents"
AGENTS_FILE = ROOT / "agents.md"
PIPELINES_FILE = ROOT / "pipelines.md"
PARITY_FILE = ROOT / "parity.md"
SKILLS_DIR = ROOT / "skills"
WORKSPACE_DIR = ROOT / "agent_workspace"
LOGS_DIR = ROOT / "logs"

BAR = "=" * 62
SENTINEL = "."


# THE GROUND FLAG (the operator, 2026-09-09: "go"; SPEC_CONTROL_CENTER.md
# §4.2, SYSTEM_DESIGN.md §3.2). Until now the ground was the package's
# parent, and only here: every function below takes a `ground` and reads
# these names at call time, so an engine could never sit INSIDE a world
# (worlds/<name>/) and write that world's own record. `--ground <path>`
# rebinds the eight names before Session() is built. Nothing else moves:
# a world is a folder carrying what Session() reads -- agents/, skills/,
# pipelines.md, its own sessions/, logs/, law/ -- and the origin's record
# is untouched by a sitting that opened elsewhere. The hands ledger, the
# whisper binaries and `us.py` keep the package's parent on purpose: those
# are the estate's, not a world's.
GROUND_FLAG = "--ground"


def set_ground(path) -> Path:
    """Rebind the ground THIS process runs on. Returns the resolved path."""
    global ROOT, AGENTS_DIR, AGENTS_FILE, PIPELINES_FILE, PARITY_FILE
    global SKILLS_DIR, WORKSPACE_DIR, LOGS_DIR
    ROOT = Path(path).resolve()
    AGENTS_DIR = ROOT / "agents"
    AGENTS_FILE = ROOT / "agents.md"
    PIPELINES_FILE = ROOT / "pipelines.md"
    PARITY_FILE = ROOT / "parity.md"
    SKILLS_DIR = ROOT / "skills"
    WORKSPACE_DIR = ROOT / "agent_workspace"
    LOGS_DIR = ROOT / "logs"
    return ROOT


USAGE = """Manjuel -- local multi-agent pipeline

  python manjuel.py                       the REPL, on this ground
  python manjuel.py --headless            the same sitting over stdin/stdout,
                                          JSON lines (PROTOCOL 1)
  python manjuel.py --ground <path>       either door, sitting INSIDE a world:
                                          its own agents/, skills/, sessions/,
                                          logs/ -- the origin's record untouched

  --help, -h                              print this and exit
  --version, -V                           print the version and exit

Nothing here opens a sitting. --help and --version read no ground, load no
model and write no record."""

# The whole vocabulary, spelled once. --ground takes a value; the rest are bare.
_FLAGS_WITH_VALUE = (GROUND_FLAG,)
_BARE_FLAGS = ("--headless", "--help", "-h", "--version", "-V")


def read_argv(argv) -> str:
    """What the operator asked for: repl | headless | help | version.

    REFUSES BY NAME anything it cannot read, because the entry point was the
    one door in this estate that did not. It accepted any argv and did the
    default, so `--help` opened a sitting and loaded models, `--heedless`
    silently gave the interactive REPL instead of the headless door, and
    `--gound worlds/x` silently ran on the estate's own record instead of the
    world he named. An unknown flag is never a request to do the default
    thing; it is a typo or a misunderstanding, and both deserve to be named.

    Pure: reads no ground, opens nothing, and is what the strokes hold.
    """
    argv = list(argv or [])
    known = set(_FLAGS_WITH_VALUE) | set(_BARE_FLAGS)
    mode = "repl"
    i = 0
    while i < len(argv):
        a = argv[i]
        name = a.split("=", 1)[0]
        if name not in known:
            raise ValueError(
                f"{a!r} is not a flag this door knows. It reads: "
                f"{', '.join(sorted(known))}. Nothing was opened.")
        if "=" in a and name not in _FLAGS_WITH_VALUE:
            raise ValueError(
                f"{a!r} takes no value. It reads: "
                f"{', '.join(sorted(known))}. Nothing was opened.")
        if name in ("--help", "-h"):
            return "help"
        if name in ("--version", "-V"):
            mode = "version" if mode != "help" else mode
        elif name == "--headless":
            mode = "headless" if mode == "repl" else mode
        if name in _FLAGS_WITH_VALUE and "=" not in a:
            i += 1                      # its value is not a flag
        i += 1
    return mode


def ground_from_argv(argv) -> Path | None:
    """`--ground <path>` or `--ground=<path>` from an argv, else None.

    A ground that is not a directory is REFUSED (ValueError), never
    created: a world is a place the operator named, and a typo must not
    become a folder (SITTING LAW 4). The flag is read wherever it stands
    -- `--headless --ground X` and `--ground X --headless` are the same."""
    argv = list(argv or [])
    raw = None
    for i, a in enumerate(argv):
        if a == GROUND_FLAG:
            if i + 1 >= len(argv) or argv[i + 1].startswith("--"):
                raise ValueError(f"{GROUND_FLAG} needs a path after it")
            raw = argv[i + 1]
            break
        if a.startswith(GROUND_FLAG + "="):
            raw = a[len(GROUND_FLAG) + 1:]
            break
    if raw is None:
        return None
    raw = raw.strip().strip('"')
    if not raw:
        raise ValueError(f"{GROUND_FLAG} needs a path after it")
    p = Path(raw).expanduser()
    if not p.is_dir():
        raise ValueError(f"{raw!r} is not a directory; a ground is never created by the flag")
    return p.resolve()


class Session:
    def __init__(self):
        self.runtime = OllamaRuntime()
        self.registry: AgentRegistry | None = None
        self.skills: SkillLibrary | None = None
        self.last: RunContext | None = None
        self.book: PipelineBook | None = None
        self.pipeline_name = "default"
        self.pipeline = list(DEFAULT_PIPELINE)
        self.session = _mem.new_session_id()
        self.last_run_ref = ""
        self.sitting = _log.open_sitting(ROOT, self.session)
        # THE STANDING, built once at open from DAYBOOK's last entry and
        # handed to the door and the court on every run (2026-09-07). Once:
        # a DAYBOOK edited mid-sitting is read at the next launch, which is
        # the RULE 9 shape -- nothing moves under his hands mid-sitting.
        self.standing = _log.standing_block(ROOT)
        self.speaking = False        # /say on -- read every delivery aloud
        self.dialogue: list = []     # the running conversation, typed or spoken
        self._dvecs: dict = {}       # (who, what) -> vector, for retrieval
        self.topic_start: int = 0    # index of the current topic's first turn
        self.watcher = None          # GroundWatch, when watchdog is present
        self.pending_feed = ""       # set by /paste, consumed by the next turn
        self.pending_spoken = ""     # transcribed by /listen, awaiting the loop
        self.pending_method = ""     # a palette command's procedure, same ride
        # /model <tag>: one model for every seat, for THIS sitting only. The
        # declared targets in agents/*.md are untouched -- reapplied on every
        # load so /reload and the ground watcher cannot silently drop it.
        self.model_override = ""

    # ---- loading ----------------------------------------------------

    def load(self) -> bool:
        """(Re)parse agents.md and skills/. Returns False on fatal error."""
        try:
            source = AGENTS_DIR if AGENTS_DIR.is_dir() else AGENTS_FILE
            self.registry = AgentRegistry.load(source)
        except RegistryError as exc:
            print(f"\nAgent manifest error:\n  {exc}\n")
            return False

        # An override survives a reload. Applied before validation so the
        # seat rack is checked in the state the run will actually use.
        if self.model_override:
            self.registry.override_model(self.model_override)

        seat_errors = seating.validate(self.registry)
        if seat_errors:
            print("\nSeat rack errors:")
            for e in seat_errors:
                print(f"  - {e}")
            print()
            return False

        self.skills = SkillLibrary.load(SKILLS_DIR)

        for w in self.registry.warnings:
            print(f"  warn: {w}")
        for w in self.skills.warnings:
            print(f"  warn: {w}")

        errors, warns = self.skills.validate()
        for w in warns:
            print(f"  warn: {w}")
        if errors:
            print("\nSkill binding errors:")
            for e in errors:
                print(f"  - {e}")
            print()
            return False

        # Pipeline order is markdown too. Seats it names must exist.
        if PIPELINES_FILE.exists():
            try:
                self.book = PipelineBook.load(PIPELINES_FILE, self.registry)
            except RegistryError as exc:
                print(f"\nPipeline error:\n  {exc}\n")
                return False
            for w in self.book.warnings:
                print(f"  warn: {w}")
            if self.pipeline_name not in self.book:
                self.pipeline_name = self.book.default
            self.pipeline = self.book.get(self.pipeline_name)
        else:
            print(f"  warn: {PIPELINES_FILE.name} not found; using built-in order")
            self.book = None
            try:
                for st in self.pipeline:
                    self.registry.get(str(st))
            except RegistryError as exc:
                print(f"\nPipeline error:\n  {exc}\n")
                return False

        return True

    # ---- pipelines --------------------------------------------------

    def pipeline_names(self) -> list[str]:
        return self.book.names() if self.book else sorted(PIPELINES)

    def pipeline_steps(self, name: str) -> list[str]:
        return self.book.get(name) if self.book else list(PIPELINES[name.lower()])

    rack_ok: bool = True

    def rack_check(self) -> bool:
        """Probe the rack. Ollama serves the models -- the operator's ruling,
        sitting 33: it is THE server, not one of several. Cheap and safe to
        repeat, so the CLI recovers the moment it comes up."""
        try:
            self.runtime.health()
            self.rack_ok = True
        except BackendUnreachable:
            self.rack_ok = False
        return self.rack_ok

    def preflight(self) -> bool:
        try:
            self.runtime.health()
        except BackendUnreachable as exc:
            print(f"\n{exc}\n")
            return False

        assert self.registry is not None
        needed = self.registry.models() | self.skills.models()
        missing = self.runtime.missing(needed)
        if missing:
            print("\nMissing model tags referenced by agents/ or skills/:")
            for tag in missing:
                print(f"  - {tag}      ollama pull {tag}")
            print()
            return False
        return True

    @property
    def env(self) -> SkillExecutionEnv:
        WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
        return SkillExecutionEnv(
            workspace=WORKSPACE_DIR, registry=self.registry,
            runtime=self.runtime, ground=ROOT,
            session=self.session, run_ref=self.last_run_ref,
            skills_ref=self.skills,
            objective=getattr(self.last, "objective", "") if self.last else "",
        )


# ---------------------------------------------------------------------
# Input helpers
# ---------------------------------------------------------------------


# Audible boundary acknowledgments -- the Steward's tone, spoken by the
# HARNESS, never placed in a prompt (a quoted line in a 3B's prompt becomes
# its output; a line printed by the engine cannot be parroted). The constant
# suffix is the testable part; the varied lead keeps it conversational.
ACK_TOPIC = ["Next topic, sounds like.", "New thread, then.",
             "A change of pace — alright.", "Different subject it is."]
ACK_SESSION = ["So — a new session, then.", "Fresh page.",
               "Clean slate, as asked."]
ACK_DETECTED = ["Different subject, looks like — new thread.",
                "That reads like a new topic — following you there.",
                "Seems you're after a change of pace — new thread."]
ACK_SUFFIX = "(the record keeps what came before)"


def _ack(sess: Session, lines: list) -> None:
    print(f"\n  {lines[len(sess.dialogue) % len(lines)]}  "
          f"{ink.dim(ACK_SUFFIX)}\n")


def _voice_for(sess: Session, ctx: RunContext) -> str | None:
    """The declared voice of the last seat that produced the delivery -- so
    the ruling sounds like Manjuel and the answer sounds like the Steward."""
    try:
        for st in reversed(ctx.steps):
            if st.ok and st.output.strip():
                return sess.registry.get(st.agent).voice
    except Exception:
        pass
    return None


def _apply_ground_changes(sess: Session) -> None:
    """Drain the watcher at a turn boundary: reload declarations, re-embed
    changed material. Audible, brief, and never mid-answer."""
    if sess.watcher is None:
        return
    reload_needed, changed = sess.watcher.drain()
    if reload_needed:
        if sess.load():
            print(ink.dim("  ground changed on disk — seats, skills and "
                          "pipelines reloaded"))
        else:
            print("  ground changed on disk and the reload FAILED — "
                  "fix the file above or /reload to retry")
    if changed and sess.rack_ok:
        try:
            from .vectors import VectorIndex
            idx = VectorIndex(ROOT / "index" / "vectors.db", EMBED_MODEL)
            st = idx.build(changed,
                           lambda c: sess.runtime.embed(EMBED_MODEL, c))
            idx.close()
            if st.embedded:
                names = ", ".join(p.name for p in changed[:3])
                more = f" +{len(changed) - 3}" if len(changed) > 3 else ""
                print(ink.dim(f"  reindexed on change: {names}{more}"))
        except Exception:
            pass                          # the index catches up at /index


def _topic_turn(sess: Session, objective: str) -> bool:
    """Handle spoken/typed boundary cues. True = turn fully handled."""
    from .intent import topic_cue, cue_only
    cue = topic_cue(objective)
    if not cue:
        return False
    if cue == "session":
        sess.dialogue.clear()
        sess.topic_start = 0
        sess.pending_feed = ""
        save_thread(ROOT, sess.session, sess.dialogue)
        _ack(sess, ACK_SESSION)
        return True                      # a wipe is the whole turn
    # topic: draw the line; the record stays
    sess.topic_start = len(sess.dialogue)
    _ack(sess, ACK_TOPIC)
    return cue_only(objective)           # pure cue = done; else run the rest


def _dialogue_for(sess: Session, objective: str) -> list:
    """Retrieval over carriage: relevant past + recent tail. Falls back to
    plain recency whenever the embedder cannot answer."""
    def embed(text: str):
        key = text[:200]
        if key not in sess._dvecs:
            sess._dvecs[key] = sess.runtime.embed(EMBED_MODEL, text)
        return sess._dvecs[key]

    try:
        from .context import detect_shift
        boundary = getattr(sess, "topic_start", 0)
        segment = sess.dialogue[boundary:]
        if detect_shift(segment, objective, embed=embed):
            sess.topic_start = len(sess.dialogue)
            boundary = sess.topic_start
            _ack(sess, ACK_DETECTED)
        return select_dialogue(sess.dialogue, objective, embed=embed,
                               boundary=boundary)
    except Exception:
        return list(sess.dialogue)[-8:]


def read_block(prompt: str) -> str | None:
    """Read multi-line input until a lone '.' line.

    The old code used a single input() call, so pasting multi-line text put
    line 1 in the feed and let the remaining lines be eaten as the NEXT
    prompt's answers -- silent data loss on exactly the paste-a-feed workflow.
    """
    print(prompt)
    print(f'  (end with a line containing only "{SENTINEL}", or blank to skip)')
    lines: list[str] = []
    while True:
        try:
            line = input("  | " if lines else "  > ")
        except EOFError:
            return None
        if line.strip() == SENTINEL:
            break
        if not lines and not line.strip():
            return ""
        lines.append(line)
    return "\n".join(lines).strip()


# ---------------------------------------------------------------------
# Slash commands
# ---------------------------------------------------------------------


THREAD_FILE = "sessions/thread.jsonl"


def save_thread(root: Path, session: str, dialogue: list) -> None:
    """The conversation, persisted with its sitting. Overwrites: the file
    holds the LATEST thread, and the transcripts hold history."""
    import json as _json
    path = root / THREAD_FILE
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\r\n") as fh:
            for e in dialogue[-80:]:
                who, what = e[0], e[1]
                ts = float(e[2]) if len(e) > 2 and e[2] else 0.0
                fh.write(_json.dumps({"session": session, "who": who,
                                      "what": what, "ts": ts}) + "\n")
    except OSError:
        pass


def load_thread(root: Path) -> tuple[str, list]:
    """(session it came from, the dialogue). Empty when there is none."""
    import json as _json
    path = root / THREAD_FILE
    if not path.exists():
        return "", []
    out, session = [], ""
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = _json.loads(line)
            session = row.get("session", session)
            out.append((row.get("who", "?"), row.get("what", ""),
                        float(row.get("ts") or 0.0)))
    except Exception:
        return "", []
    return session, out


# (name, group, blurb) -- the single source for /help and the / palette.
COMMANDS = [
    ("chat",      "talking",   "voice chat: talk, it answers aloud, any key cuts it off"),
    ("say",       "talking",   "speak deliveries: /say on | off | <words now>"),
    ("new",       "talking",   "drop the conversation thread"),
    ("resume",    "talking",   "pick up the previous sitting's thread"),
    ("paste",     "talking",   "stage source material for the next objective"),
    ("table",     "talking",   "round-table: counsel hears <q>, the Court rules"),
    ("@<seat>",   "talking",   "address one seat directly: @manjuel <question>"),
    ("last",      "record",    "reprint the previous answer"),
    ("remember",  "record",    "land an entry in memory.md (confirms first)"),
    ("memory",    "record",    "review what seats proposed; land or drop"),
    ("git",       "record",    "repository state"),
    ("toll",      "record",    "pay this sitting's toll"),
    ("sittings",  "record",    "past sittings"),
    ("brief",     "record",    "where the build is and what you said we are on; the door says it"),
    ("status",    "ground",    "boot report: ground, rack, record, gate, voice"),
    ("index",     "ground",    "refresh the semantic index"),
    ("find",      "ground",    "search the ground by meaning: /find <q>"),
    ("parity",    "ground",    "chain vs bare calls; references set per case"),
    ("models",    "rack",      "VRAM plan for this pipeline"),
    ("model",     "rack",      "run every seat on one model: /model <tag> | reset"),
    ("warm",      "rack",      "load this pipeline's models now"),
    ("rack",      "rack",      "resurvey Ollama, rewrite rack.md"),
    ("agents",    "plumbing",  "list seats, models, stages"),
    ("skills",    "plumbing",  "list skills and binding status"),
    ("pipeline",  "plumbing",  "the active running order, spine and rack"),
    ("pipelines", "plumbing",  "all declared pipelines"),
    ("use",       "plumbing",  "switch pipeline: /use <name>"),
    ("reload",    "plumbing",  "re-read agents/, skills/ and commands.md"),
    ("listen",    "plumbing",  "speak one question (superseded by /chat)"),
    ("help",      "plumbing",  "this palette; /help <q> filters it"),
    ("exit",      "plumbing",  "quit"),
]

_CUSTOM_RE = __import__("re").compile(
    r"^##[ \t]+Command:[ \t]*(?P<name>\S+)[ \t]*$(?P<body>.*?)(?=^##[ \t]+Command:|\Z)",
    __import__("re").MULTILINE | __import__("re").DOTALL)
_FIELD_RE2 = __import__("re").compile(
    r"^-[ \t]+\*\*(?P<k>Does|Runs):?\*\*:?[ \t]*(?P<v>.+)$", __import__("re").MULTILINE)


_METHOD_RE = __import__("re").compile(
    r"^-?[ \t]*\*\*Method:?\*\*:?[ \t]*$", __import__("re").MULTILINE)

# `/name the rest of the line` -- what follows the command IS the argument.
ARGS_TOKEN = "$ARGS"


def fill_args(runs: str, arg: str) -> str:
    """Put the operator's words into the command's objective.

    `$ARGS` is replaced where he placed it; with no token the argument is
    appended, because "/debug 63" plainly means the command plus 63. An
    unused token is removed rather than left to reach a seat as literal
    text -- a model handed `$ARGS` will try to interpret it."""
    arg = (arg or "").strip()
    if ARGS_TOKEN in runs:
        return " ".join(runs.replace(ARGS_TOKEN, arg).split())
    return f"{runs} {arg}".strip() if arg else runs


def custom_commands() -> dict:
    """Operator additions from commands.md: {name: (blurb, runs, method)}.

    `**Method:**` on a line of its own works the way `**System Prompt:**`
    does in a seat file: everything after it, to the end of the block, is
    the text. The estate already had that convention; this reuses it rather
    than inventing a second one."""
    path = ROOT / "commands.md"
    out = {}
    if not path.exists():
        return out
    for m in _CUSTOM_RE.finditer(path.read_text(encoding="utf-8")):
        body = m.group("body")
        method = ""
        marker = _METHOD_RE.search(body)
        if marker:
            method = body[marker.end():].strip()
            body = body[:marker.start()]
        fields = dict((k.lower(), v.strip())
                      for k, v in _FIELD_RE2.findall(body))
        out[m.group("name").strip().lower()] = (
            fields.get("does", ""), fields.get("runs", ""), method)
    return out


def palette(sess: Session, query: str = "") -> str:
    """The live index: built-ins + skills + pipelines + operator commands.

    Autofilled from what the ground actually holds, filtered by the query --
    typing an unknown /thing searches this instead of erroring.
    """
    q = query.strip().lower()
    rows: list[tuple[str, str, str]] = []
    for name, group, blurb in COMMANDS:
        rows.append((f"/{name}", group, blurb))
    for name, (blurb, runs, method) in sorted(custom_commands().items()):
        note = blurb or (runs[:50] + "...")
        if method:
            note += "   (carries a method)"
        rows.append((f"/{name}", "yours", note))
    if sess.skills:
        for spec in sorted(sess.skills.specs, key=lambda x: x.keyword):
            rows.append((spec.keyword, "skill",
                         "say it in a sentence; the chain routes it"))
    for pname in (sess.pipeline_names() if sess.book else []):
        rows.append((f"/use {pname}", "pipeline", "switch the running order"))

    if q:
        rows = [r for r in rows if q in r[0].lower() or q in r[2].lower()
                or q in r[1].lower()]
    if not rows:
        return f"  nothing in the palette matches '{query}'.\n"

    out = [""]
    last_group = None
    for name, group, blurb in rows:
        if group != last_group:
            out.append(f"  {group}")
            last_group = group
        out.append(f"    {name:<22} {blurb}")
    out.append("")
    out.append("  /<letters> filters this list. Anything else you type is a"
               " turn in the conversation.")
    return "\n".join(out) + "\n"


def handle_command(cmd: str, sess: Session) -> bool:
    """Return True if the input was a command."""
    if not cmd.startswith("/"):
        return False

    parts = cmd[1:].strip().split(None, 1)
    name = parts[0].lower() if parts else ""
    arg = parts[1].strip() if len(parts) > 1 else ""

    if name in ("exit", "quit", "q"):
        raise SystemExit(0)

    if name == "help":
        print(palette(sess, arg))
        return True

    # (An `if False:` block of 33 lines -- the old /help text -- stood here
    # until 2026-09-08; palette() is /help now.)
    if name == "pipelines":
        print()
        for pname in sess.pipeline_names():
            mark = "*" if pname == sess.pipeline_name else " "
            names = " → ".join(ink.seat(str(x)) if not getattr(x, "when", None)
                               else ink.dim(str(x))
                               for x in sess.pipeline_steps(pname))
            print(f"  {mark} {pname:<10} {names}")
        src = sess.book.source.name if sess.book else "built-in"
        print(f"\n  from {src}; edit it and /reload to add one\n")
    elif name == "use":
        try:
            steps = sess.pipeline_steps(arg)
        except (RegistryError, KeyError):
            print(f"  unknown pipeline '{arg}'. Available: "
                  f"{', '.join(sess.pipeline_names())}\n")
        else:
            sess.pipeline_name = arg.strip().lower()
            sess.pipeline = steps
            print(f"  pipeline: {' -> '.join(str(x) for x in sess.pipeline)}\n")
    elif name == "agents":
        print()
        for a in sess.registry.all():
            active = "*" if a.name in sess.pipeline else " "
            cond = f"  when:{a.when}" if a.when else ""
            pad = " " * max(0, 20 - len(a.name))
            print(f"  {active} {ink.seat(a.name)}{pad} {ink.dim(a.model):<24} "
                  f"[{a.stage}]{cond}")
        print("\n  * = in the active pipeline\n")
    elif name == "skills":
        print()
        errors, _ = sess.skills.validate()
        broken = {e.split(" ")[0] for e in errors}
        for s in sess.skills.specs:
            mark = "!" if s.filename in broken else "+"
            print(f"  {mark} {s.keyword:<18} ({s.filename})")
        print()
    elif name == "pipeline":
        print()
        print("  spine — runs every time")
        for i, st in enumerate(sess.pipeline, 1):
            gate = getattr(st, "when", None)
            print(f"    {i}. {ink.seat(str(st))}"
                  + (f"   (rests until '{gate}')" if gate else ""))
        racked = seating.rack_for(sess.registry, sess.pipeline)
        if racked:
            print()
            print("  rack — summoned by flag, not written into the order")
            spine_seats = {str(x).strip().lower() for x in sess.pipeline}
            for a in racked:
                flags = ", ".join(seating.wake_flags(a))
                where = seating.parse_anchor(a.wakes)
                note = ""
                if (where.kind == seating.ANCHOR_AFTER
                        and where.target.strip().lower() not in spine_seats):
                    # Not an error -- it slots in at the next opening. Say so,
                    # because silently landing somewhere else reads as a bug.
                    note = ink.dim(f"  (no {where.target} here — takes the next slot)")
                print(f"    · {ink.seat(a.name)}   on {flags}   → {where}{note}")
        print()
    elif name == "reload":
        if sess.load():
            print("  reloaded.\n")
    elif name == "remember":
        _cmd_remember(sess, arg)
    elif name == "memory":
        _cmd_memory(sess)
    elif name == "say":
        want = arg.strip().lower()
        cap = voice.can_speak()
        if want in ("on", "yes"):
            if not cap.ok:
                print(f"\n  cannot speak: {cap}\n")
            else:
                sess.speaking = True
                print(f"\n  speaking every delivery — {cap.how}\n")
        elif want in ("off", "no"):
            sess.speaking = False
            print("\n  back to text only.\n")
        elif want:
            try:
                said = voice.speak(want)
                print(f"\n  said: {said}\n")
            except voice.VoiceError as exc:
                print(f"\n  {exc}\n")
        else:
            state = "on" if sess.speaking else "off"
            print(f"\n  /say is {state}   ({cap})")
            print("  /say on | /say off | /say <words to speak now>\n")

    elif name == "listen":
        cap = voice.can_listen()
        if not cap.ok:
            print(f"\n  cannot listen: {cap}\n")
        else:
            seconds = voice.MAX_TURN_SECONDS
            if arg.strip().isdigit():
                seconds = max(5, min(300, int(arg.strip())))
            print()
            try:
                said = voice.listen(seconds, report=print)
            except voice.VoiceError as exc:
                print(f"  {exc}\n")
                return True
            if not said:
                print("  nothing recognised.\n")
                return True
            # Heard, not assumed. The operator confirms before it becomes the
            # objective -- a misheard command is still a command.
            print(f'\n  heard: "{said}"')
            try:
                ok = input("  run this? [Y/n] ").strip().lower()
            except EOFError:
                ok = "n"
            if ok in ("", "y", "yes"):
                sess.pending_spoken = said
                print()
            else:
                print("  dropped.\n")

    elif name == "paste":
        fed = read_block("Source material:")
        if fed:
            sess.pending_feed = fed
            print(f"\n  {len(fed)} chars staged — the next objective runs "
                  f"against it (Guardian gates it first).\n")
        else:
            print("\n  nothing staged.\n")

    elif name == "new":
        n = len(sess.dialogue) // 2
        sess.dialogue.clear()
        sess.topic_start = 0
        sess.pending_feed = ""
        save_thread(ROOT, sess.session, sess.dialogue)
        print(f"\n  thread dropped ({n} turns forgotten).\n")

    elif name == "resume":
        origin, thread = load_thread(ROOT)
        if not thread:
            print("\n  no saved thread to resume.\n")
        else:
            sess.dialogue = thread
            print(f"\n  resumed {len(thread) // 2} turns from {origin}. "
                  f"/new drops them again.\n")

    elif name == "chat":
        _cmd_chat(sess, arg)

    elif name == "table":
        _cmd_table(sess, arg)

    elif name == "parity":
        _cmd_parity(sess, arg)

    elif name == "git":
        _cmd_git(sess)
    elif name == "toll":
        _cmd_toll(sess, attended=True)
    elif name == "sittings":
        _cmd_sittings(sess)
    elif name == "models":
        _cmd_models(sess, arg)
    elif name == "model":
        _cmd_model(sess, arg)
    elif name == "warm":
        _cmd_warm(sess)
    elif name == "rack":
        print("\n  " + sess.skills.execute("rack_sync", {}, sess.env).replace("\n", "\n  ") + "\n")
    elif name == "status":
        print()
        for line in boot.report(sess, ROOT, EMBED_MODEL):
            print(line)
        print()
    elif name == "brief":
        _cmd_brief(sess)
    elif name == "index":
        print("\n  indexing (this uses the embedder, not a chat model)...")
        print("  " + sess.skills.execute("index_ground", {}, sess.env).replace("\n", "\n  "))
        print()
    elif name == "find":
        if not arg:
            print("  /find <what you are looking for>\n")
        else:
            print("\n  " + sess.skills.execute(
                "semantic_search", {"content": arg}, sess.env).replace("\n", "\n  ") + "\n")
    elif name == "last":
        if sess.last is None:
            print("  no previous run.\n")
        else:
            print("\n" + sess.last.last_output() + "\n")
    else:
        custom = custom_commands().get(name)
        if custom and custom[1]:
            blurb, runs, method = custom
            objective = fill_args(runs, arg)
            if objective.lstrip().startswith("/"):
                # A palette command whose Runs: is another command would
                # come back through this door next turn, and a cycle has
                # no floor (the REPL read, 2026-09-08). Refused, not run.
                print(f"\n  /{name} refused: its Runs: line is a command "
                      f"({objective.split()[0]}), and a command may not run "
                      f"a command. Write the objective in words in "
                      f"commands.md.\n")
                return True
            print(f"\n  /{name} → {objective}"
                  + ("   (+ method)" if method else "") + "\n")
            sess.pending_spoken = objective
            sess.pending_method = method
        else:
            # An unknown /thing is a QUERY against the palette, not an error.
            print(palette(sess, name))

    return True


def _cmd_brief(sess: Session) -> None:
    """THE BRIEF, said by the door. The facts are read off the record
    (boot.brief_facts) and printed as they are; then the Steward is handed
    them -- material first, the ask last, told nothing else happened -- and
    says where the build is and what the operator said we are on. The
    exchange is a run: it goes to the record like any other."""
    facts = boot.brief_facts(sess, ROOT)
    print()
    for line in facts:
        print(line)
    print()
    if not sess.rack_ok and not sess.rack_check():
        print("  (the rack is unreachable; the facts above are the brief)\n")
        return
    try:
        door = sess.registry.get("Steward")
    except Exception:
        print("  (no Steward seat; the facts above are the brief)\n")
        return
    material = "\n".join(f"    {l}" for l in facts)
    prompt = (f"{material}\n\n----------\n"
              f"Above this line is THE RECORD, read off the files this morning: "
              f"what this sitting is for, where the build stands, the operator's "
              f"own last words, what is open, what waits. Tell him, in your own "
              f"plain voice and under 200 words, where we are and what he said we "
              f"are working on today. Say only what is above; NOTHING ELSE "
              f"HAPPENED. No headings, no labels copied, no tool names.")
    ctx = RunContext(objective="the brief", standing=getattr(sess, "standing", ""),
                     story=_log.story_block(sess.sitting))
    print()
    started = time.time()
    try:
        out = sess.runtime.chat(door, prompt,
                                stream_to=lambda p: print(p, end="", flush=True))
        print("\n")
    except RuntimeError_ as exc:
        print(f"\n  the door could not speak the brief: {exc}\n")
        return
    out = (out or "").strip()
    # THE DOOR'S NUMBERS ARE CHECKED AGAINST THE FACTS (the review of
    # 2026-09-08). Sitting 94's brief said "master@0917c6d4a, clean at
    # open ... no tasks since sitting 87" over facts that said f1da1a4
    # DIRTY (16) and sittings 88-93 in the ledger. A number, a hash or a
    # sitting the door names that is not in the facts block it was handed
    # is named beneath its words; the facts printed first remain the brief.
    made_up = _unsourced(out, material)
    if made_up:
        stamp = ("(the door named these and the record does not: "
                 + ", ".join(made_up[:6]) + " -- the facts printed above are the brief)")
        print("  " + ink.warn(stamp) + "\n")
        out = f"{out}\n\n{stamp}"
        ctx.notes.append("brief: the door's numbers were not in the facts: "
                         + ", ".join(made_up[:6]))
    ctx.steps.append(StepResult(agent=door.name, model=door.model, output=out,
                                elapsed=time.time() - started, prompt=prompt))
    _record_turn(sess, ctx)


_NUM_OR_HASH = re.compile(r"(?<![\w.])([0-9a-f]{7,40}|\d[\d,]*\.?\d*)(?![\w.])")

# A DATE OR A CLOCK IS NOT A FABRICATED QUANTITY, and the guards below exist
# for fabricated quantities. The clock reaches a seat through its brief, so a
# guard that sources numbers only from tool results can never let a seat say
# what time it is -- it flagged "Wednesday 09 September 2026, 12:15" as two
# invented numbers, and the seat was telling the truth. A guard that fires on
# true statements gets ignored, and an ignored guard catches nothing.
#
# So numbers written AS a date or a clock are blanked before judgement. This
# is a matter of SHAPE, not of loosening: a fabricated count is not shaped
# like a date, so everything caught before is still caught. A bare four-digit
# number is deliberately NOT exempt -- 1858 is a stroke count, and 2026
# outside a date phrase is not obviously a year.
_MONTHS = (r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
           r"jul(?:y)?|aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|"
           r"nov(?:ember)?|dec(?:ember)?")

CLOCK_SHAPES = re.compile(r"""
      \d{4}-\d{2}-\d{2}(?:[T ]\d{1,2}:\d{2}(?::\d{2})?)?      # 2026-09-09, with time
    | \d{1,2}[/]\d{1,2}[/]\d{2,4}                              # 09/09/2026
    | \d{1,2}:\d{2}(?::\d{2})?(?:\s*[ap]\.?m\.?)?              # 12:15, 12:15:30, 3:04 pm
    | \b\d{1,2}\s+(?:""" + _MONTHS + r""")\b\.?(?:,?\s*\d{4})?   # 09 September 2026
    | \b(?:""" + _MONTHS + r""")\b\.?\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s*\d{4})?
    """, re.IGNORECASE | re.VERBOSE)


def without_clock(text: str) -> str:
    """`text` with every date and clock expression blanked out.

    Used by both number guards -- this one and the standup's -- so the two can
    never disagree about what a date looks like.
    """
    return CLOCK_SHAPES.sub(" ", text or "")


def _unsourced(said: str, facts: str) -> list[str]:
    """Numbers and hashes in `said` that appear nowhere in `facts`.

    Small integers (0-12) are words in prose and are not judged, and
    numbers written as a date or a clock are not judged either (see
    CLOCK_SHAPES). Everything else is.
    """
    have = {m.group(1).replace(",", "").rstrip(".") for m in _NUM_OR_HASH.finditer(facts or "")}
    out = []
    # `facts` keeps its dates -- they are a SOURCE. Only what is judged is
    # stripped, so the door may say the date without being called a liar.
    for m in _NUM_OR_HASH.finditer(without_clock(said)):
        tok = m.group(1).replace(",", "").rstrip(".")
        if tok.isdigit() and int(tok) <= 12:
            continue
        if tok in have or any(tok in h or h in tok for h in have if len(tok) >= 7):
            continue
        if tok not in out:
            out.append(tok)
    return out


def _cmd_warm(sess: Session, quiet: bool = False) -> None:
    """Pay the model-load cost HERE, at a moment the operator expects a wait,
    rather than inside the first question."""
    sizes = vram.installed_sizes(sess.runtime)
    # SPINE ONLY -- the operator's ruling, sitting 30: racked specialists load
    # when their flag wakes them, and a ~7s cold start on the rare technical
    # turn is a fair price for 4.7GB of VRAM not held hostage the rest of the
    # time. rack_list prices each seat's wake cost live, so the trade stays
    # visible.
    steps = [s for s in sess.pipeline if not getattr(s, "when", None)]
    plan = vram.build_plan(sess.pipeline_name, steps, sess.registry, sizes=sizes)
    resident = sess.runtime.resident()
    already = {t for t, _ in resident}
    todo = [m for m in plan.distinct if m not in already]

    if not todo:
        if not quiet:
            print(f"  already warm: {', '.join(plan.distinct)}\n")
        return

    # Somebody else may be holding this card. Warming ours would evict theirs
    # and charge THEM the reload -- not a cost manjuel gets to spend quietly.
    # Foreign means NOT DECLARED BY THIS GROUND -- never merely "not in the
    # current warm plan". With spine-only warming, the coder and embedder sit
    # resident because THIS chain used them; calling the estate's own models
    # another client's was wrong, and printed a phantom second session.
    declared = (set(sess.registry.models()) | sess.skills.models()
                | {EMBED_MODEL})
    others = vram.foreign(resident, declared)
    if others:
        need = sum(plan.estimate(m) for m in todo)
        free = vram.budget_bytes() - sum(b for _, b in others)
        if need > free:
            print(f"  not warming: {', '.join(t for t, _ in others)} is resident "
                  f"(~{vram.gb(sum(b for _, b in others))}) and belongs to another")
            print(f"  client. Loading {', '.join(todo)} (~{vram.gb(need)}) would evict it.")
            print("  /models shows the split. MANJUEL_VRAM_GB sets the budget.\n")
            return

    for m in todo:
        ctxs = [a.context or 0 for a in sess.registry.all() if a.model == m]
        run_ctx = max(ctxs) if ctxs else None
        print(f"  warming {m} (ctx {run_ctx or 2048}) ...", end="", flush=True)
        try:
            print(f" {sess.runtime.warm(m, num_ctx=run_ctx):.1f}s")
        except RuntimeError_ as exc:
            print(f" failed ({exc})")
    if not quiet:
        print()


def _cmd_model(sess: Session, arg: str = "") -> None:
    """Run the whole roster on one model for this sitting.

    The seats declare their defaults in agents/*.md and those files are never
    written to here -- the operator asked to try a bigger model without an
    edit he then has to remember to undo. `/model` alone reports; `/model
    reset` restores the declared targets; `/model <tag>` moves everything.

    Fail closed on an uninstalled tag: RULE 4 says nothing is fetched at
    runtime, so a tag Ollama does not have would fail every seat on the next
    turn, one at a time, with the cause four stages back.
    """
    arg = (arg or "").strip()

    if not arg:
        print()
        if sess.model_override:
            print(f"  override: every seat on {sess.model_override} "
                  f"(this sitting only)")
            print("  /model reset restores what agents/*.md declares")
        else:
            print("  no override -- every seat on its declared Model Target")
        for a in sess.registry.all():
            print(f"    {a.name:22} {a.model}")
        print()
        return

    if arg.lower() in ("reset", "off", "default", "declared"):
        if not sess.model_override:
            print("\n  no override to clear\n")
            return
        sess.model_override = ""
        sess.load()
        print("\n  override cleared -- seats back on their declared targets\n")
        return

    try:
        installed = sess.runtime.installed_models(refresh=True)
    except Exception as exc:                     # ollama down: say so, do nothing
        print(f"\n  cannot reach the rack to check '{arg}' ({exc}).\n"
              f"  Refusing rather than setting a target that may not exist.\n")
        return

    tag = arg if ":" in arg else f"{arg}:latest"
    if tag not in installed:
        near = sorted(m for m in installed if arg.split(":")[0] in m)
        print(f"\n  '{tag}' is not installed. Nothing changed.")
        if near:
            print(f"  installed and close: {', '.join(near)}")
        print("  RULE 4: models are never pulled at runtime. "
              "/rack lists what is here.\n")
        return

    sess.model_override = tag
    moved = sess.registry.override_model(tag)
    print(f"\n  every seat now runs {tag} -- this sitting only.")
    print("  agents/*.md is untouched; /model reset restores it.")
    specialists = [(n, was) for n, was, _ in moved
                   if not was.startswith(("llama3.2", "phi4-mini"))]
    if specialists:
        print("\n  moved OFF a purpose-chosen model:")
        for n, was in specialists:
            print(f"    {n:22} was {was}")
    print()


def _cmd_models(sess: Session, arg: str = "") -> None:
    """What each pipeline costs in model loads and VRAM."""
    sizes = vram.installed_sizes(sess.runtime)
    budget = None
    if arg:
        try:
            budget = int(float(arg.rstrip("gG")) * 1e9)
        except ValueError:
            print(f"  '{arg}' is not a size in GB\n")
            return

    names = [sess.pipeline_name] if not arg else sess.pipeline_names()
    print()
    for n in (names if len(names) > 1 else sess.pipeline_names()):
        plan = vram.build_plan(n, sess.pipeline_steps(n), sess.registry, sizes=sizes)
        print(vram.render(plan, budget=budget or vram.budget_bytes(),
                          resident=sess.runtime.resident()))
        print()

    extra = sorted(sess.skills.models() - {m for n in sess.pipeline_names()
                                           for _, m in vram.build_plan(
                                               n, sess.pipeline_steps(n),
                                               sess.registry).order})
    if extra:
        print(f"  prompt skills add: {', '.join(extra)}")
    print(f"  the embedder is always live: {EMBED_MODEL} (drift + index)")
    print()
    from .runtime import KEEP_ALIVE
    res = sess.runtime.resident()
    if res:
        print("  resident now: " + ", ".join(f"{t} ({vram.gb(b)})" for t, b in res))
    print()
    print(f"  manjuel SETS per request:   keep_alive={KEEP_ALIVE}, num_ctx and")
    print( "                               num_predict from each seat's markdown.")
    print( "  manjuel CANNOT set these -- the ollama SERVER reads them at its own")
    print( "  startup, so exporting them here would do nothing:")
    print( "    OLLAMA_NUM_PARALLEL=1        >1 multiplies KV cache per model")
    print( "    OLLAMA_MAX_LOADED_MODELS=3   how many stay resident at once")
    print( "  Set those where Ollama starts, then restart it.")
    print()


def _cmd_chat(sess: Session, arg: str = "") -> None:
    """Voice chat: speak, it answers aloud, speak again. No typing.

    /listen was dictation -- one utterance, confirmed, then back to the
    prompt. This is the conversation: the loop holds until the operator ends
    it, and the answer is spoken rather than read.
    """
    hear, say = voice.can_listen(), voice.can_speak()
    if not hear.ok:
        print(f"\n  cannot listen: {hear}\n")
        return
    if not say.ok:
        print(f"\n  cannot speak: {say}\n")
        return

    seconds = int(arg.strip()) if arg.strip().isdigit() else voice.MAX_TURN_SECONDS
    seconds = max(5, min(300, seconds))

    print(f"\n  voice chat — {hear.how}, {say.how}")
    print("  Speak; each turn ends when you go quiet. Any key cuts off its "
          "answer.\n  Say 'stop' or press Ctrl+C to end.\n")

    dialogue = sess.dialogue     # voice and typed turns share one thread
    turn = 0
    misheard = 0                 # consecutive listen failures
    while True:
        turn += 1
        print(BAR)
        try:
            said = voice.listen(seconds, report=lambda m: print(ink.dim(m)))
            misheard = 0
        except voice.VoiceError as exc:
            print(f"  {exc}")
            # A bad turn ends the turn, never the conversation -- a cough or a
            # quiet moment should not drop the operator back to a text prompt.
            # But three in a row is a dead microphone, not a cough, and a
            # loop with no floor printed the same error until Ctrl-C (the
            # REPL read, 2026-09-08). LAW 7.
            misheard += 1
            if misheard >= 3:
                print("\n  three listens failed in a row -- ending voice chat; "
                      "check the microphone and /chat again.\n")
                return
            continue
        except KeyboardInterrupt:
            print("\n  ending voice chat.\n")
            return

        if not said:
            print("  (nothing heard)")
            continue
        print(f'  you: "{said}"')
        low = said.strip().lower()
        from .intent import wants_out
        if (low.rstrip(".!").split()[-1] in ("stop", "exit", "quit", "goodbye")
                or wants_out(said)):
            print("  ending voice chat.\n")
            return
        # Sitting 25: four spoken attempts to pay the toll went to the chain,
        # which cannot pay it -- the toll is the operator's own act, reached
        # only as a command. A spoken request for it runs the command.
        if "pay the toll" in low or low.rstrip(".!?") in ("the toll", "toll"):
            _cmd_toll(sess, attended=True)
            continue
        cued, words = remember_cue(said)
        if cued:
            _cmd_remember_that(sess, words)
            continue
        if _topic_turn(sess, said):
            continue

        ctx = RunContext(objective=said, feed="",
                         dialogue=_dialogue_for(sess, said),
                         standing=getattr(sess, "standing", ""),
                         story=_log.story_block(sess.sitting))
        try:
            # The same live view as a typed run: seats stream, the spinner
            # spins, the coder's code scrolls. Voice mode is this terminal
            # with a microphone, not a different program that hides the work.
            run_pipeline(ctx, sess.registry, sess.runtime, sess.skills, sess.env,
                         steps=sess.pipeline, stream=True,
                         drift=DriftChecker(sess.runtime, EMBED_MODEL))
        except (Aborted, Refused) as exc:
            spoken = f"I stopped. {exc}"
            print(f"  manjuel: {spoken}")
            try:
                voice.speak(spoken)
            except voice.VoiceError:
                pass
            continue
        except KeyboardInterrupt:
            print("\n  ending voice chat.\n")
            return

        answer = spelling.check(ctx.last_output().strip()).text
        if not answer:
            answer = "No seat produced an answer."
        dialogue.append(("operator", said, time.time()))
        dialogue.append(("steward", answer, time.time()))
        save_thread(ROOT, sess.session, sess.dialogue)
        # The stages already streamed above; the delivery is spoken, not
        # reprinted in full.
        print()
        try:
            # Interruptible, and it waits until the speech ends or is cut, so
            # the next turn cannot start recording while the machine is still
            # talking and hear itself. Any keypress takes the floor back.
            voice.speak_interruptible(answer, report=print,
                                      voice=_voice_for(sess, ctx))
        except voice.VoiceError as exc:
            print(ink.dim(f"  (not spoken: {exc})"))

        _record_turn(sess, ctx)


def _record_turn(sess: Session, ctx: RunContext) -> None:
    """A spoken turn is still a run: it goes in the record like any other."""
    sess.last = ctx
    try:
        record, _ = transcript.write(ctx, LOGS_DIR, pipeline=sess.pipeline_name)
        sess.last_run_ref = f"logs/{record.name}"
        sess.sitting.runs.append(vars(_log.note_for(
            ctx, sess.pipeline_name, f"logs/{record.name}")))
    except Exception:
        pass


def _address_seat(sess: Session, raw: str) -> bool:
    """`@manjuel <question>` -- one seat, directly, no pipeline around it."""
    parts = raw[1:].split(None, 1)
    if not parts:
        return False
    name = parts[0].strip().lower()
    question = parts[1].strip() if len(parts) > 1 else ""
    try:
        agent = sess.registry.get(name)
    except Exception:
        print(f"\n  no seat called '{parts[0]}'. /agents lists them.\n")
        return True
    if not question:
        print(f"\n  @{agent.name} <what you want to ask him>\n")
        return True

    ctx = RunContext(objective=question, dialogue=list(sess.dialogue))
    talk = ctx.dialogue_block()
    prompt = (f"{talk}\n\n" if talk else "") + (
        f"The operator addresses you directly, by name.\n\n"
        f"{question}\n\n"
        f"Answer as yourself, from your own office. You are speaking, not "
        f"acting: no tools run from this exchange, and a thing you cannot "
        f"know from the conversation or your office, say you cannot know.")
    print()
    try:
        out = sess.runtime.chat(agent, prompt,
                                stream_to=lambda p: print(p, end="", flush=True))
        print("\n")
    except RuntimeError_ as exc:
        print(f"\n  {agent.name} could not answer: {exc}\n")
        return True
    out = (out or "").strip()
    if out:
        # Sitting 46: three @seat exchanges entered the shared thread and the
        # Steward COSPLAYED that seat off them, introducing himself as the
        # head of somebody else's office.
        #
        # A direct address is a private office visit: it goes in the
        # transcript record, never into the conversation other seats read.
        # (That phrase is an anchor a stroke greps for, and it must stay on
        # ONE line -- rewrapping it is how this went red twice.)
        ctx.steps.append(StepResult(agent=agent.name, model=agent.model,
                                    output=out))
        _record_turn(sess, ctx)
    return True


def _warm_reasoner_later(sess: Session):
    """The operator's ruling, sitting 33: the Steward's model warms at boot;
    the Reasoner's warms in the BACKGROUND once he is in -- boot never waits
    on a 6.6GB load, and by the time a `hard` question arrives the big seat
    is usually already seated. The coder stays lazy by the same ruling.
    Failure here is silent: a cold Reasoner still wakes on demand."""
    import threading

    def _go():
        try:
            reasoner = sess.registry.get("Reasoner")
        except Exception:
            return
        try:
            if reasoner.model not in sess.runtime.installed_models():
                return
            sess.runtime.warm(reasoner.model, num_ctx=reasoner.context)
        except Exception:
            pass

    t = threading.Thread(target=_go, daemon=True, name="warm-reasoner")
    t.start()
    return t


def _cmd_table(sess: Session, arg: str = "") -> None:
    """Convene the round-table on one question, without switching pipelines.

    The court order: the Steward answers, Neiro holds the whole, Jesster
    refutes, and Manjuel rules last on everything said. Each seat reads all
    the counsel before it. The ruling is the delivery.
    """
    question = arg.strip()
    if not question:
        print("\n  /table <the question to put before the seats>\n")
        return
    try:
        steps = sess.book.get("court") if sess.book else None
    except Exception:
        steps = None
    if not steps:
        print("\n  no `court` pipeline declared in pipelines.md\n")
        return

    seats = " → ".join(str(x) for x in steps)
    print(f"\n  convening: {seats}\n")

    ctx = RunContext(objective=question, feed=sess.pending_feed,
                     dialogue=_dialogue_for(sess, question), review_only=True,
                     standing=getattr(sess, "standing", ""),
                     story=_log.story_block(sess.sitting))
    sess.pending_feed = ""
    sess.last_run_ref = f"logs/{transcript.name_for(ctx)}"
    try:
        run_pipeline(ctx, sess.registry, sess.runtime, sess.skills, sess.env,
                     steps=steps, stream=True,
                     drift=DriftChecker(sess.runtime, EMBED_MODEL))
    except (Aborted, Refused) as exc:
        print(f"\n  the table did not sit: {exc}\n")
        return
    except KeyboardInterrupt:
        print("\n  table adjourned.\n")
        return

    # The whole counsel joins the thread, each voice under its own name --
    # not just the ruling. A follow-up to @manjuel about what Jesster said
    # is only possible if Jesster's words are still in the room.
    sess.dialogue.append(("operator", f"(convened the table) {question}",
                          time.time()))
    for st in ctx.steps:
        if st.skipped or st.error or not st.output.strip():
            continue
        who = st.agent.strip().lower()
        if who == "security guardian":
            continue                     # SAFE/UNSAFE is a gate, not counsel
        said = " ".join(st.output.split())
        if len(said) > 400:
            said = said[:400] + "..."
        sess.dialogue.append((who, said, time.time()))
    save_thread(ROOT, sess.session, sess.dialogue)
    sess.last = ctx
    try:
        record, _ = transcript.write(ctx, LOGS_DIR, pipeline="court")
        sess.last_run_ref = f"logs/{record.name}"
        note = _log.note_for(ctx, "court", f"logs/{record.name}")
        note.objective = question
        sess.sitting.runs.append(vars(note))
        print(f"\n  the table's record: logs/{record.name}\n")
    except Exception as exc:
        print(f"\n  (record not written: {exc})\n")


def _cmd_parity(sess: Session, arg: str = "") -> None:
    """Measure the local chain against a reference. Costs money; asks first."""
    try:
        cases = parity.load_cases(PARITY_FILE)
    except parity.ParityError as exc:
        print(f"\n  {exc}\n")
        return

    if arg.strip():
        want = arg.strip().lower()
        cases = [c for c in cases if want in c.name.lower()]
        if not cases:
            print(f"\n  no case matching '{arg.strip()}'\n")
            return

    # A reference call is a paid API call. The operator authorises the spend,
    # not the chain -- the gate is final, and that includes his wallet.
    needed = parity.models_needed(cases)
    missing = sess.runtime.missing(needed)
    if missing:
        print("\n  reference models not pulled yet:")
        for tag in sorted(missing):
            print(f"    - {tag}      ollama pull {tag}")
        print()
        return

    print(f"\n  {len(cases)} case(s), each answered twice on THIS machine: "
          f"once by the seats, once by a larger local model.\n")
    for c in cases:
        print(f"    · {c.name:30} -> {c.model}")
    print(f"\n  reference models: {', '.join(sorted(needed))}")
    print("  Nothing leaves the box and nothing is billed. Costs time and VRAM —")
    print("  a big reference will spill to CPU on a 16GB card and run slowly.")
    try:
        go = input("\n  run them? [y/N] ").strip().lower()
    except EOFError:
        go = "n"
    if go not in ("y", "yes"):
        print("  nothing run.\n")
        return

    def answer_locally(case: parity.Case) -> str:
        ctx = RunContext(objective=case.objective, feed=case.feed)
        run_pipeline(ctx, sess.registry, sess.runtime, sess.skills, sess.env,
                     steps=sess.pipeline, report=lambda _s: None, stream=False)
        return ctx.last_output()

    def embed(text: str):
        return sess.runtime.embed(EMBED_MODEL, text)

    print()
    rep = parity.run(cases, answer_locally, embed, sess.runtime, report=print)

    # THE SEAT MAP FIRST, because render() needs it to read the scores the
    # right way round (sitting 81). It used to be gathered after printing.
    seats = {}
    try:
        seats = {a.name: a.model for a in sess.registry.all()}
    except Exception:
        pass
    print(rep.render(seats))

    # Beside the score, WHAT PRODUCED IT. Parity has always measured and
    # never remembered, so nobody could see whether quality moved when the
    # seats did -- and they have moved a great deal. The seat map is
    # stamped with the mean so a later reading has both halves.
    if rep.stamp(ROOT, seats):
        print("  (stamped to sessions/parity_history.jsonl — the mean beside "
              "the seats that produced it)\n")

    out = LOGS_DIR / f"parity_{time.strftime('%Y-%m-%d_%H%M%S')}.md"
    try:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        body = ["# Parity run", "", rep.render(seats), "", "## Pairs", ""]
        for o in rep.outcomes:
            body += [f"### {o.case}", "",
                     f"score: {o.score if o.score is not None else 'n/a'}", "",
                     "**local**", "", o.local or f"(none: {o.error})", "",
                     "**reference**", "", o.reference or "(none)", ""]
        out.write_text("\n".join(body), encoding="utf-8", newline="\r\n")
        print(f"  pairs written to logs/{out.name}\n")
    except Exception as exc:
        print(f"  (pairs not written: {exc})\n")


def _cmd_git(sess: Session) -> None:
    g = gitstate.read(ROOT)
    print()
    print(f"  {g.stamp()}")
    if g.is_repo and g.subject:
        print(f"  last: {g.subject}")
    if not g.is_repo and not g.error:
        print("  This ground is not under version control. To start:")
        print(f'    git -C "{ROOT}" init && git -C "{ROOT}" add -A && '
              f'git -C "{ROOT}" commit -m "manjuel: initial"')
    elif g.is_repo and g.dirty:
        print("  To version this sitting, run this YOURSELF:")
        print("    " + gitstate.suggest_commit(ROOT, f"manjuel: sitting {sess.sitting.n}"))
        print("  manjuel never commits (LAW 6: the gate is final).")
    print()


def _cmd_sittings(sess: Session) -> None:
    rows = _log.all_sittings(ROOT)
    if not rows:
        print(f"\n  no prior sittings. this is sitting {sess.sitting.n}.\n")
        return
    seen = {}
    for r in rows:
        seen[r.get("n")] = r          # later line supersedes earlier
    print()
    for n in sorted(seen):
        r = seen[n]
        g = (r.get("git_start") or {}).get("short", "")
        toll = "toll paid" if r.get("toll_paid") else "no toll"
        print(f"  {n:>3}. {r.get('id','')}  {r.get('started','')[:16]}  "
              f"{len(r.get('runs') or [])} run(s)  {g}  {toll}")
    print(f"\n  current: sitting {sess.sitting.n} ({sess.session})\n")


_TOLL_NOT_AN_ANSWER = {"y", "n", "yes", "no", "yep", "nope", "yeah", "nah"}


def _toll_answer(question: str, hint: str) -> str:
    """One open question of the toll. A bare yes/no is not an answer to it.

    The toll asks three open questions and then confirms, and every prompt was
    the same bare `>`. A `y` meant for the confirm landed in the field instead,
    and `render_toll` makes the first field the SEAT_LOG HEADING -- so sittings
    28, 41, 42, 44 and 58 are titled `y` or `n` in the record. Blank still
    skips; only a yes/no is sent back, because it is never what was meant.
    """
    while True:
        print(f"  {question} {hint}")
        answer = input("  (text, not y/n) > ").strip()
        if answer.lower() not in _TOLL_NOT_AN_ANSWER:
            return answer
        print("    '" + answer + "' is a yes/no, and this asks for words. "
              "Leave it blank to skip it.")


def _cmd_toll(sess: Session, attended: bool = True) -> None:
    st = sess.sitting
    if st.toll_paid:
        if not _confirm("  a toll was already paid this sitting. Pay another?"):
            return
    if not st.runs and attended:
        if not _confirm("  nothing ran this sitting. Pay a toll anyway?"):
            return

    print("\n  --- the sitting, as observed ---")
    print(_log.summarize(st))
    print()

    proved = thin = owed = ""
    if attended:
        try:
            proved = _toll_answer("What proved?", "(one line; blank to skip)")
            thin = _toll_answer("What is thin?", "(blank to skip)")
            owed = _toll_answer("What is owed?", "(blank to skip)")
        except (EOFError, KeyboardInterrupt):
            print()
            return

    _log.close_sitting(ROOT, st)
    text = _log.render_toll(st, proved, thin, owed, attended=attended)
    print("  --- about to append to SEAT_LOG.md ---")
    print(text)
    if attended and not _confirm("  Append this toll?"):
        print("  toll not paid.\n")
        return

    _log.pay(ROOT, text)
    st.toll_paid = True
    _log.record(ROOT, st)
    print(f"  toll paid into SEAT_LOG.md (sitting {st.n}).")

    g = gitstate.read(ROOT)
    if g.is_repo and g.dirty:
        print("  the ground is dirty. To version it, run this yourself:")
        print("    " + gitstate.suggest_commit(ROOT, f"manjuel: sitting {st.n}"))
    print()


def _confirm(question: str) -> bool:
    try:
        return input(f"{question} [y/N] ").strip().lower().startswith("y")
    except (EOFError, KeyboardInterrupt):
        print()
        return False


# "REMEMBER THAT" AT THE DOOR (2026-09-07, the operator: "make sure i can
# actually say things like 'remember that' when a good idea is proposed, or
# i like the result of an outcome"). The cue is matched on the OPERATOR'S
# TYPED TURN, before any model reads it -- the same door "pay the toll" goes
# through. A seat's output never passes this way, so a seat saying
# "remember that X" is still only a proposal. The keyboard is the trust
# boundary, not the words.
_REMEMBER_CUE = __import__("re").compile(
    r"\b(?:remember|land)\s+(?:that|this|it)(?:\s+one)?\b\s*[:,\-]?\s*(?P<text>.*)$",
    __import__("re").IGNORECASE | __import__("re").DOTALL)
REMEMBER_CUE_MAX_WORDS = 15


def remember_cue(objective: str) -> tuple[bool, str]:
    """(is the cue, the words after it). "remember that" alone lands the
    newest proposal, or the last delivery; "remember that: X" lands X.

    Sitting 89: "thank you. good job remember that!" -- the cue mid-turn,
    in praise. So it is matched ANYWHERE in a short turn (the way it is
    said), and at the START of a long one ("remember that: <the words>").
    A long turn that merely contains the phrase ("do you remember that time
    the router...") is conversation and goes to the seats."""
    text = (objective or "").strip()
    m = _REMEMBER_CUE.search(text)
    if not m:
        return False, ""
    words_before = len(text[:m.start()].split())
    if words_before and len(text.split()) > REMEMBER_CUE_MAX_WORDS:
        return False, ""
    return True, m.group("text").strip().strip("!.?")


def _ask_kind() -> str:
    """One word from the list. Sitting 94 typed "outcome failed due to
    timeout, as stated." and the whole sentence became the kind; the entry
    carries it still. The first word is taken if it is a kind; anything
    else is asked again, twice, then the default -- a kind is a word."""
    for _ in range(3):
        try:
            raw = input(f"  kind ({'/'.join(_mem.KINDS)}) [{_mem.DEFAULT_KIND}]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return _mem.DEFAULT_KIND
        if not raw:
            return _mem.DEFAULT_KIND
        first = raw.split()[0].strip(".,:;!")
        if first in _mem.KINDS:
            return first
        print(f"  a kind is one word from the list; {raw!r} is not one.")
    return _mem.DEFAULT_KIND


def _cmd_remember_that(sess: Session, text: str) -> None:
    """The cue's work. Three sources, in order: the operator's own words
    after the cue; else the newest PROPOSAL a seat staged; else the last
    DELIVERY. Shown back, a kind asked, one confirm, then landed -- the
    operator's act every time (LAW 6)."""
    if text:
        entry = _mem.Entry(title="", body=text, provenance=_mem.OPERATOR,
                           session=sess.session, run=sess.last_run_ref)
        source = "your words"
    else:
        items = _mem.pending(ROOT)
        if items:
            entry = items[-1]
            source = f"the newest proposal ({len(items)} pending)"
        elif sess.last is not None and (sess.last.last_output() or "").strip():
            entry = _mem.Entry(title=f"outcome: {sess.last.objective[:60]}",
                               body=sess.last.last_output().strip(),
                               provenance=_mem.OPERATOR,
                               session=sess.session, run=sess.last_run_ref)
            source = "the last delivery"
        else:
            print("\n  nothing to remember yet -- no proposal, no delivery. "
                  "Say `remember that: <the words>`.\n")
            return
    print(f"\n  --- about to remember ({source}) ---")
    print(entry.preview())
    print()
    entry.kind = _ask_kind()
    if not _confirm("  Land this in memory.md?"):
        print("  not remembered.\n")
        return
    if source.startswith("the newest proposal"):
        _mem.land_pending(ROOT, len(_mem.pending(ROOT)) - 1, kind=entry.kind)
    else:
        _mem.land(ROOT, entry)
    print(f"  remembered in memory.md as {entry.kind} ({entry.stamp}).")
    print("  run index_ground to make it searchable.\n")


def _cmd_remember(sess: Session, arg: str) -> None:
    """Operator-written memory. Shown back, then confirmed, then landed."""
    body = arg or read_block("What should be remembered?")
    if not body or not body.strip():
        print("  nothing written; not remembered.\n")
        return

    title = ""
    try:
        title = input("  title (blank = first words): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return

    entry = _mem.Entry(title=title, body=body, provenance=_mem.OPERATOR,
                       session=sess.session, run=sess.last_run_ref)
    print("\n  --- about to remember ---")
    print(entry.preview())
    print()
    entry.kind = _ask_kind()
    if not _confirm("  Land this in memory.md?"):
        print("  not remembered.\n")
        return
    _mem.land(ROOT, entry)
    print(f"  remembered in memory.md as {entry.kind} ({entry.stamp}, session {sess.session}).")
    print("  run index_ground to make it searchable.\n")


def _cmd_memory(sess: Session) -> None:
    """Review what seats proposed. Each is landed or dropped by hand."""
    items = _mem.pending(ROOT)
    if not items:
        mem = ROOT / _mem.MEMORY_FILE
        n = len(_mem.split_entries(mem.read_text(encoding="utf-8"))) if mem.exists() else 0
        print(f"\n  nothing pending. memory.md holds {n} entr{'y' if n == 1 else 'ies'}.\n")
        return

    print(f"\n  {len(items)} proposed by seats, none remembered yet:\n")
    landed = dropped = 0
    while _mem.pending(ROOT):
        e = _mem.pending(ROOT)[0]
        print(e.preview())
        print()
        try:
            choice = input("  [l]and  [d]rop  [s]top: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if choice.startswith("l"):
            _mem.land_pending(ROOT, 0, kind=_ask_kind())
            landed += 1
            print("  landed.\n")
        elif choice.startswith("d"):
            _mem.drop_pending(ROOT, 0)
            dropped += 1
            print("  dropped.\n")
        else:
            break
    print(f"  {landed} landed, {dropped} dropped, {len(_mem.pending(ROOT))} still pending.\n")


# ---------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------


def _close(sess: Session) -> None:
    """Every sitting pays its toll (LAW 10). If the operator did not pay it by
    hand, an unattended toll records what was observed and says plainly that
    thin and owed were never stated -- rather than inventing them."""
    if getattr(sess, "watcher", None) is not None:
        sess.watcher.stop()
    st = sess.sitting
    waiting = len(_mem.pending(ROOT))
    if waiting:
        print(f"\n  {waiting} memory proposal{'' if waiting == 1 else 's'} waiting "
              f"-- /memory next sitting, or `remember that`.")
    if st.runs and not st.toll_paid:
        try:
            _log.close_sitting(ROOT, st)
            _log.pay(ROOT, _log.render_toll(st, attended=False))
            st.toll_paid = True
            # SITTING 84 (2026-09-04, found reading this file whole). The
            # attended path records the closing line (`_cmd_toll`); this
            # path paid the toll and NEVER wrote it back, so every sitting
            # that closed unattended stayed OPEN in sessions.jsonl with
            # toll_paid:false and zero runs -- fourteen of them by the
            # morning's count, and the record and the ledger disagreed on
            # which sittings had been paid. The ledger is append-only; a
            # closing line supersedes the opening one.
            _log.record(ROOT, st)
            print(f"\n  toll paid unattended into SEAT_LOG.md (sitting {st.n}).")
        except Exception as exc:
            print(f"\n  (toll not written: {exc})")
    elif not st.toll_paid:
        # No runs, no toll: close the empty sitting. A PAID sitting was
        # already closed and recorded by _cmd_toll -- this branch used to
        # run for it too, and `/toll` then exit left two closing lines
        # with two timestamps (the REPL read, 2026-09-08).
        try:
            _log.close_sitting(ROOT, st)
            _log.record(ROOT, st)
        except Exception:
            pass
    print("bye")


def main() -> int:
    # THE GROUND, first: every line below reads ROOT, so the flag is
    # honoured before the banner. A bad path is a refusal, not a folder.
    try:
        ground = ground_from_argv(sys.argv[1:])
    except ValueError as exc:
        print(f"\n  {GROUND_FLAG} refused: {exc}\n")
        return 1
    if ground is not None:
        set_ground(ground)

    print("\nManjuel -- local multi-agent pipeline")
    if ground is not None:
        print(f"  ground: {ROOT}")

    env_lines = dotenv.report(*dotenv.load(ROOT / ".env"))
    for line in env_lines:
        print(line)

    sess = Session()
    if not sess.load():
        return 1
    # The ground opens with or without the rack. Ollama down means models
    # are down -- the record, the palette, git state and the ground's own
    # skills are not, and the CLI recovers the moment the rack appears.
    if not sess.rack_check():
        print("\n  RACK UNREACHABLE — the ground is open, the models are not.")
        print("  Start `ollama serve` whenever; Manjuel reconnects on the "
              "next turn.\n")
    elif not sess.preflight():
        return 1

    _log.record(ROOT, sess.sitting)
    # ONE read of the repo at open (the REPL read, 2026-09-08: this line was
    # written twice, and boot.report and boot.brief_facts each read again --
    # five reads, twenty git subprocesses, three printings of one stamp).
    g0 = gitstate.read(ROOT)
    print(f"  sitting {sess.sitting.n} · session {sess.session} · {g0.stamp()}")
    print()

    if os.environ.get("MANJUEL_NO_WARM", "").strip() not in ("1", "true", "yes"):
        # manjuel does NOT start Ollama -- it connects to the one already
        # running. The lag is the MODEL loading into VRAM on first use, which
        # otherwise lands inside the first question. Pay it here instead.
        if sess.rack_ok:
            _cmd_warm(sess, quiet=True)      # spine only: the Steward's model
            sess._bg_warm = _warm_reasoner_later(sess)

        sess.watcher = _watch.GroundWatch(ROOT)
        if sess.watcher.start():
            print(ink.dim("  watching the ground — edits reload and reindex "
                          "themselves between turns"))
        else:
            sess.watcher = None

    for line in boot.report(sess, ROOT, EMBED_MODEL, git=g0):
        print(line)
    print()
    # THE BRIEF'S FACTS, at every open, no model (2026-09-07). /brief has
    # the door say them.
    try:
        for line in boot.brief_facts(sess, ROOT, git=g0):
            print(line)
        print("  /brief has the door say it\n")
    except Exception as exc:
        print(ink.dim(f"  (the brief could not be read: {exc})\n"))
    origin, prior = load_thread(ROOT)
    if prior:
        print(f"  a thread from {origin} is on file "
          f"({len(prior) // 2} turns) — /resume picks it up")
    print("  /help for commands\n")

    try:
        return _loop(sess)
    except Exception as exc:
        # An exception nothing below caught. Before 2026-09-08 it escaped to
        # manjuel.py, which catches only KeyboardInterrupt: the watcher thread
        # stayed up and the sitting stayed OPEN in the ledger with
        # toll_paid:false -- the sitting-84 fault by another door. The
        # sitting is closed and its toll paid unattended, THEN the fault
        # is shown whole.
        print(f"\n  !! unhandled: {type(exc).__name__}: {exc}")
        print("  closing the sitting so the ledger does not hold it open.")
        try:
            _close(sess)
        finally:
            raise


def _loop(sess: Session) -> int:
    """The typed turn loop. main() wraps it so any escape still closes."""
    while True:
        print(BAR)
        if sess.pending_spoken:
            # /listen already asked whether to run it, so it goes straight in.
            objective = sess.pending_spoken
            sess.pending_spoken = ""
            print(f"Objective: {objective}")
        else:
            try:
                objective = input("Objective: ").strip()
            except (EOFError, KeyboardInterrupt):
                _close(sess)
                return 0

        if not objective:
            continue
        from .intent import wants_out
        if objective.lower() in ("exit", "quit") or wants_out(objective):
            print(f"\n  Alright — closing the sitting. "
                  f"{ink.dim('(the record keeps)')}\n")
            _close(sess)
            return 0

        _apply_ground_changes(sess)

        if _topic_turn(sess, objective):
            continue

        low = objective.lower().strip()
        if "pay the toll" in low or low.rstrip(".!?") == "the toll":
            _cmd_toll(sess, attended=True)
            continue
        cued, words = remember_cue(objective)
        if cued:
            _cmd_remember_that(sess, words)
            continue

        # Sitting 29: "let me talk to manjuel" had no door. @seat opens one:
        # that seat alone, its own voice, the shared conversation thread.
        if objective.startswith("@"):
            if _address_seat(sess, objective):
                continue
        try:
            if handle_command(objective, sess):
                continue
        except SystemExit:
            _close(sess)
            return 0

        # No rack, no run -- but re-probe first, so a freshly started Ollama
        # is picked up mid-session without a restart.
        if not sess.rack_ok and not sess.rack_check():
            print("\n  The rack is still unreachable — `ollama serve`, then "
                  "just ask again.\n")
            continue

        # One prompt, no second Enter. Untrusted material still has a door --
        # /paste asks for a feed and the Guardian still gates it -- but the
        # everyday turn is: type, Enter, answer.
        ctx = RunContext(objective=objective, feed=sess.pending_feed,
                         dialogue=_dialogue_for(sess, objective),
                         method=sess.pending_method,
                         review_only=sess.pipeline_name in ("court", "estate"),
                         standing=getattr(sess, "standing", ""),
                         story=_log.story_block(sess.sitting))
        sess.pending_feed = ""
        sess.pending_method = ""     # one run, then it is spent
        # Known before the first stage, so a mid-run `remember` cites THIS run.
        sess.last_run_ref = f"logs/{transcript.name_for(ctx)}"
        print("\nRunning pipeline...")

        try:
            run_pipeline(
                ctx,
                sess.registry,
                sess.runtime,
                sess.skills,
                sess.env,
                steps=sess.pipeline,
                stream=True,
                drift=DriftChecker(sess.runtime, EMBED_MODEL),
            )
        except Refused as exc:
            # Three gates raise this: the law gate and the injection gate
            # (arithmetic, before any seat) and the Guardian (a seat's
            # verdict). The message says which; this line no longer
            # credits the Guardian for the engine's refusals.
            print(f"\n  REFUSED: {exc}")
            print("  The run did not proceed. Nothing downstream saw this input.\n")
            continue
        except Aborted as exc:
            print(f"\nRun aborted: {exc}\n")
            continue
        except KeyboardInterrupt:
            print("\n\nRun cancelled.\n")
            continue
        except BackendUnreachable as exc:
            print(f"\n{exc}\n")
            continue
        except RuntimeError_ as exc:
            print(f"\nRuntime error: {exc}\n")
            continue

        sess.last = ctx
        _final = ctx.last_output().strip()
        if _final:
            sess.dialogue.append(("operator", ctx.objective, time.time()))
            sess.dialogue.append(("steward", _final, time.time()))
            save_thread(ROOT, sess.session, sess.dialogue)

        name = sess.pipeline_name
        try:
            record, _ = transcript.write(ctx, LOGS_DIR, pipeline=name)
            where = f"  logged: logs/{record.name}"
            sess.sitting.runs.append(vars(_log.note_for(
                ctx, name, f"logs/{record.name}")))
        except Exception as exc:
            where = f"  (transcript not written: {exc})"

        print("\n" + ink.dim(f"--- delivery · {ctx.elapsed:.1f}s ---") + "\n")
        body = ctx.last_output().strip()
        if body:
            # Correct the DELIVERY only. The transcript keeps what each seat
            # actually said -- testimony is the record, and is not edited.
            result = spelling.check(body)
            if result.changed:
                body = result.text
                ctx.notes.append(result.note())
        if not body:
            # Never print nothing and call it an answer. Session 5c handed the
            # operator a blank screen and no reason for it.
            print("  (no seat produced an answer this run)")
            for n in ctx.notes:
                print(f"  - {n}")
        else:
            print(body)
        print()
        print(where)
        print()

        if sess.speaking and body:
            try:
                voice.speak(body, blocking=False,
                            voice=_voice_for(sess, ctx))
            except voice.VoiceError as exc:
                print(ink.dim(f"  (not spoken: {exc})"))
                print()


if __name__ == "__main__":
    sys.exit(main())
