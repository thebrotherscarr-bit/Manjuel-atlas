"""Skills: markdown declares the interface, Python registers the implementation.

The old design generated the manifest from skills/*.md but dispatched through a
hardcoded if/elif chain. Adding a .md file therefore advertised a tool to the
router that could never execute. Here the two halves verify each other at
startup instead of drifting silently.
"""

from __future__ import annotations

import os
import ast
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .registry import AgentRegistry
from .vectors import VectorIndex, load_roots
from . import memory as _mem
from . import gitstate as _git
from . import mathkit
from . import vram as _vram
from . import rack as _rack
from . import voice as _voice

# One embedder, used consistently. Vectors from two different models cannot be
# compared -- the spaces are unrelated -- so changing this tag invalidates every
# stored vector and they must be rebuilt.
# 2026-09-02: the operator's rack housekeeping took `nomic-embed-text` off
# and left `nomic-embed-text-v2-moe`. Preflight does NOT catch this -- it
# checks tags named by agents/ and skills/, and the embedder is named by
# neither -- so a wrong value here boots clean and fails at index, drift
# and parity instead.
#
# CHANGING THIS INVALIDATES THE INDEX. Each embedder's vector space is its
# own; cosine between two of them is noise, not a weak signal (DESIGN 11).
# Run `index ground` after any change here -- the index is rebuildable by
# design, which is exactly why this is safe to change and not safe to
# leave half-changed.
EMBED_MODEL = "nomic-embed-text-v2-moe:latest"
EMBED_CHAR_LIMIT = 4000
MEMORY_FILE = "memory.md"

# Action keyword -> handler
_HANDLERS: dict[str, Callable] = {}

_ACTION_KEY_RE = re.compile(r"\*\*Action Keyword:\*\*\s*(?P<kw>[A-Za-z0-9_\-]+)")
# A skill that names a model is a PROMPT SKILL: its markdown body IS the
# instruction, and it needs no Python handler at all.
_SKILL_MODEL_RE = re.compile(r"\*\*Model Target:\*\*\s*(?P<m>\S+)")
_DESC_RE = re.compile(r"\*\*Description:\*\*\s*(?P<d>.*?)(?=\n[ \t]*[-*][ \t]*\*\*|\Z)",
                      re.DOTALL)
_PARAMS_RE = re.compile(r"\*\*Parameters Needed:\*\*\s*(?P<p>.*?)(?=\n[ \t]*[-*][ \t]*\*\*|\Z)",
                        re.DOTALL)
# `<content>The note to propose</content>` -- the NAME and the author's own
# description of it. The backreference keeps `<a>x</b>` from matching.
_PARAM_PAIR_RE = re.compile(r"<(?P<n>\w+)>(?P<d>.*?)</(?P=n)>", re.DOTALL)
# LAW 8: one write-path per chain. A skill that resolves a CALLER-SUPPLIED path
# declares which argument carries it and which jail it belongs to, so the gate
# at dispatch can check the RESOLVED path before any handler runs. Declared,
# never inferred: `remember`'s <filepath> is an entry title, `rack_load`'s is a
# model tag, and `deep_research` falls back to it for prose. An argument's NAME
# is not evidence of what it holds.
#     - **Path Args:** filepath -> workspace
#     - **Path Args:** content -> ground, filepath -> ground
_PATH_ARGS_RE = re.compile(r"\*\*Path Args:\*\*\s*(?P<p>.*?)(?=\n[ \t]*[-*][ \t]*\*\*|\Z)",
                           re.DOTALL)
_PATH_PAIR_RE = re.compile(r"(?P<arg>[a-z_]+)\s*(?:->|→)\s*(?P<jail>workspace|ground)")
JAILS = ("workspace", "ground")
# A refusal names the authority that made it, and the engine can find its own
# firings without reading prose: a gate whose firings are invisible cannot be
# measured, and guardrail performance that is never measured is a claim.
GATE_MARK = "[LAW 8]"

# LAW 7: bounded everything -- timeouts on calls, caps on loops. voice.py
# bounds its subprocesses at 180s and gitstate.py at 60, but execute() -- the
# one function every model-directed request passes through -- had no bound at
# all, so a handler that hung took the REPL with it and Ctrl-C was the only
# way out. Overridable with MANJUEL_SKILL_TIMEOUT for a legitimately slow
# ground (index_ground over thousands of documents).
try:
    SKILL_TIMEOUT = float(os.environ.get("MANJUEL_SKILL_TIMEOUT") or 300)
except ValueError:
    SKILL_TIMEOUT = 300.0


def _run_bounded(handler, env, args, seconds: float):
    """Run a handler with a bound on the WAIT. Raises TimeoutError past it.

    HONEST LIMIT, stated rather than papered over: Python cannot kill a
    running thread. This bounds how long the chain waits, not how long the
    work runs -- on a timeout the run is handed a refusal and carries on
    while the handler may still be going behind it. That is strictly better
    than a dead REPL and strictly worse than a real kill.

    A handler that must be genuinely killable spawns a child process and
    bounds THAT, the way voice.py already does. The thread is a daemon so a
    hung skill can never keep the REPL from exiting, and each call gets its
    own, so one hang cannot starve the next call of a worker.
    """
    box: dict = {}

    def work():
        try:
            box["ok"] = handler(env, args)
        except Exception as exc:          # re-raised on the caller's thread
            box["err"] = exc

    t = threading.Thread(target=work, daemon=True, name="skill")
    t.start()
    t.join(seconds)
    if t.is_alive():
        raise TimeoutError(f"still running after {seconds:.0f}s")
    if "err" in box:
        raise box["err"]
    return box.get("ok", "")


# The router prompt carries EVERY skill, and is sent twice per tool call. That
# cost grows with the library, so the per-skill budget has to shrink as the
# library grows -- trimming the surrounding prose only buys one more skill.
#
# 240 -> 170 -> 130 -> 112. The last cut is 2026-09-02, when `sitting`,
# `when` and `subtask` landed in one day and pushed the Router's prompt to
# ~1830 tokens against a ~1800 cap. This is the DIAL the tech-debt review
# named for exactly this moment, and the arithmetic is plain: the window is
# fixed, so a bigger library means a smaller entry each. What the Router
# gets here is WHAT exists, never HOW -- the chosen skill's full body is
# injected after it is called, which is where the detail belongs.
#
# When this can shrink no further without the entries going useless, the
# answer is a shortlist rather than a smaller cap -- MEASURED unnecessary
# in 2026-09-01 (79% of dispatch is already deterministic), and to be
# re-measured before it is built.
ROUTING_DESC_CHARS = 112

# THE SHORTLIST. Six candidates at ~300 characters cost fewer tokens than
# thirty-odd at 112, and say far more about the ones that matter. The full
# roster still travels as bare keywords, so nothing is hidden -- this
# narrows what is DESCRIBED, never what may be CALLED.
SHORTLIST_KEEP = 6
SHORTLIST_DESC_CHARS = 300


def parse_path_args(body: str) -> tuple[tuple[str, str], ...]:
    """(argument, jail) pairs a skill declares. Empty tuple when it names none."""
    m = _PATH_ARGS_RE.search(body)
    if not m:
        return ()
    return tuple((p.group("arg"), p.group("jail"))
                 for p in _PATH_PAIR_RE.finditer(m.group("p")))


# A SKILL OWNS ITS OWN DISPATCH (the operator's ruling, sitting 66).
#
# Two faults with one cause showed up the same afternoon. `index_ground
# rebuild` matched the keyword and the word `rebuild` had NOWHERE TO GO --
# the handler had to be taught about it in Python, one skill at a time.
# And the alias table in intent.py kept growing because every phrasing was
# hand-carved in code, far from the skill it described, which is how bare
# adverbs ended up dispatching on ordinary talk.
#
# Both are the same shape: dispatch knowledge living somewhere other than
# the skill. So a skill may now declare it, in its own file, the way
# **Path Args:** already declares its jails:
#
#     - **Says:** index, reindex, run the index
#     - **Takes:** rebuild | from scratch -> content
#
# `Says` are alias phrases -- matched whole, word-boundary, exactly as the
# table in intent.py matches. `Takes` maps words the operator might use to
# the ARGUMENT that should carry them, so the payload survives the moment
# of recognition instead of being thrown away with the rest of the
# sentence. Markdown declares; Python only runs it.
# A BLANK LINE ENDS THE LIST, and that is not cosmetic. This used to run to
# the next `- **` bullet or to END OF FILE, so a skill whose `Says:` was the
# LAST bullet swallowed every word of prose beneath it and claimed it, comma
# and newline split, as trigger phrases. Measured 2026-09-10: `doc_pass`
# claimed 35 phrases where 8 were declared, and among the 27 it invented was
# `what does the covenant say?` -- lifted out of a paragraph EXPLAINING that
# very failure. It would have hijacked the standup case it was written about.
# In markdown a bullet list ends at a blank line; the parser now agrees.
_SAYS_RE = re.compile(
    r"\*\*Says:\*\*\s*(?P<p>.*?)(?=\n[ \t]*[-*][ \t]*\*\*|\n[ \t]*\n|\Z)",
    re.DOTALL)
_TAKES_RE = re.compile(r"\*\*Takes:\*\*\s*(?P<p>.*?)(?=\n[ \t]*[-*][ \t]*\*\*|\Z)",
                       re.DOTALL)
# "rebuild | from scratch -> content"  /  "2, part N -> content"
_TAKES_RULE_RE = re.compile(
    r"(?P<words>[^->\n→]+?)\s*(?:->|→)\s*(?P<arg>[a-z_]+)")

TAKES_ARGS = ("content", "filepath")


# A phrase this long, or ending in a full stop, is a SENTENCE that leaked out
# of a paragraph -- not something an operator says at a door. It is reported at
# load rather than silently claimed, because a claimed sentence is a phrase the
# Router weighs on every single turn.
_PROSE_PHRASE = 45


def parse_says(body: str) -> tuple[str, ...]:
    """Alias phrases a skill claims for itself. Lowercased, deduped.

    `|` IS ACCEPTED BESIDE THE COMMA. The declared format is comma-separated
    (the header above this module's parsers shows it), and `|` is `Takes:`'s
    separator -- but two skills written on 2026-09-10, `git_cycle` and
    `search_transcripts`, used `|` here by mistake and the parser read the
    whole line as ONE phrase. A phrase of eleven clauses matches nothing, so
    BOTH SKILLS' ALIASES WERE DEAD from the day they were written, silently:
    `git_cycle` routed only when its name was typed outright, which is exactly
    why `git_cycle the whole version-control turn` reached no tool that
    morning. Accepting both separators costs nothing -- neither character can
    appear inside a phrase an operator would say -- and turns a silent
    misdeclaration into a working one.
    """
    m = _SAYS_RE.search(body)
    if not m:
        return ()
    seen, out = set(), []
    for raw in re.split(r"[,|\n]", m.group("p")):
        phrase = " ".join(raw.strip().strip("`'\"").split()).lower()
        if phrase and phrase not in seen:
            seen.add(phrase)
            out.append(phrase)
    return tuple(out)


def parse_takes(body: str) -> tuple[tuple[tuple[str, ...], str], ...]:
    """((trigger words...), argument) rules a skill declares.

    Refuses an argument the tool grammar has no tag for: there are three
    tags and no fourth, and a rule pointing at a name nothing can carry
    would be a promise the engine cannot keep -- which is the exact fault
    this was built after (an error naming a cure that did not exist)."""
    m = _TAKES_RE.search(body)
    if not m:
        return ()
    rules = []
    for r in _TAKES_RULE_RE.finditer(m.group("p")):
        arg = r.group("arg").strip().lower()
        if arg not in TAKES_ARGS:
            continue
        words = tuple(w for w in
                      (" ".join(p.strip().strip("`'\"").split()).lower()
                       for p in r.group("words").split("|")) if w)
        if words:
            rules.append((words, arg))
    return tuple(rules)


def args_from_words(spec, said: str) -> dict:
    """The arguments a skill's own **Takes:** rules find in a sentence.

    This is the payload surviving the moment of recognition. Sitting 66:
    "index_ground rebuild" matched the keyword and the word `rebuild` was
    discarded with the rest of the sentence, so the handler could not have
    obeyed it however it was written."""
    found: dict = {}
    low = f" {' '.join((said or '').lower().split())} "
    for words, arg in getattr(spec, "takes", ()) or ():
        for w in words:
            if re.search(rf"(?<![a-z0-9_]){re.escape(w)}(?![a-z0-9_])", low):
                found.setdefault(arg, w)
                break
    return found


class SkillError(Exception):
    pass


def skill(keyword: str):
    """Register a handler for an action keyword declared in skills/*.md."""

    def wrap(fn: Callable) -> Callable:
        _HANDLERS[keyword.strip().lower()] = fn
        return fn

    return wrap


@dataclass(frozen=True)
class SkillSpec:
    keyword: str
    filename: str
    body: str
    model: str = ""          # set => prompt skill, no Python handler needed
    path_args: tuple = ()    # ((arg, jail), ...) from **Path Args:**; see LAW 8
    says: tuple = ()         # alias phrases the skill claims, **Says:**
    takes: tuple = ()        # ((words...), arg) payload rules, **Takes:**

    @property
    def is_prompt_skill(self) -> bool:
        return bool(self.model)

    @property
    def declared_args(self) -> frozenset:
        """The argument names this skill SAYS it takes, read off its own
        `**Parameters Needed:**` line.

        Sitting 77 needed this and did not have it: the tool loop's dedup was
        keying on whatever the Router emitted, so an argument a skill DOES
        NOT HAVE was enough to make two identical calls look different.
        `list_directory` declares `Parameters Needed: None` and its handler
        reads no args at all -- two calls to it are the same work by
        definition, and both ran.

        A skill's own file is the record of what it takes; nothing else is.
        Read from the body rather than a hand-maintained table, because a
        table beside the files is a second place to forget.
        """
        pm = _PARAMS_RE.search(self.body)
        if not pm:
            return frozenset()
        return frozenset(re.findall(r"<(\w+)>", pm.group("p")))

    @property
    def param_notes(self) -> dict:
        """{argument: the skill's OWN words for it}, off **Parameters Needed:**.

        `declared_args` reads the NAMES out of `<content>...</content>`; this
        reads what is written BETWEEN the tags, which is the author describing
        the argument to whoever has to supply it. The tool schema hands those
        words to the Router rather than a sentence invented in Python, so the
        description a model reads is the one the skill's author wrote.
        """
        pm = _PARAMS_RE.search(self.body)
        if not pm:
            return {}
        return {m.group("n"): " ".join(m.group("d").split())
                for m in _PARAM_PAIR_RE.finditer(pm.group("p"))}

    @property
    def summary(self) -> str:
        """The ROUTING view: keyword, what it does, what it takes.

        Deliberately not the whole body. Output-format rules and CRITICAL
        CONSTRAINT blocks are instructions for the skill's own execution --
        to the router they are noise, and on the first live run they made the
        manifest 90% of a 2,861-token prompt that the tool loop then sent
        twice per skill call.
        """
        d = _DESC_RE.search(self.body)
        desc = " ".join(d.group("d").split()) if d else ""
        if len(desc) > ROUTING_DESC_CHARS:
            cut = desc[:ROUTING_DESC_CHARS]
            desc = cut[:cut.rfind(" ")] + "..."
        pm = _PARAMS_RE.search(self.body)
        params = " ".join(pm.group("p").split()) if pm else "None"
        params = re.sub(r"<(\w+)>[^<]*</\1>", r"<\1>", params)
        if len(params) > 80:
            params = params[:80] + "..."
        return f"- {self.keyword}  takes: {params}\n    {desc}"


def declares(spec) -> set:
    """Every argument name a skill's OWN markdown declares.

    One expression, THREE readers now: the dedup keys a call on it (an
    undeclared argument cannot vary a signature, sitting 77), `decided_call`
    asks it whether anything is left for the Router to choose, and
    `tool_schemas` builds each skill's parameters from it. A second copy
    would drift the first time a skill grows a parameter.

    MOVED HERE FROM pipeline.py, 2026-09-10. It reads nothing but SkillSpec
    fields, and `tool_schemas` -- a SkillLibrary method -- needed it; pipeline
    imports skills, so skills cannot import pipeline back. It belongs beside
    the thing it describes. pipeline.py re-exports the name, so every existing
    caller is untouched.
    """
    if spec is None:
        return set()
    return ({a for a, _ in (spec.path_args or ())}
            | {a for _, a in (spec.takes or ())}
            | set(spec.declared_args or ()))


# What counsel may call: eyes, never hands. The operator's ruling,
# sitting 39: "give it the ability to review, never write."
REVIEW_ONLY_SKILLS = {
    "semantic_search", "search_transcripts",
    "ground_read", "ground_list", "ground_report",
    "read_file", "list_directory", "git_status", "rack_list",
    "skill_report", "extract_facts", "classify_sentiment", "statistics",
    "sitting", "when", "skill_search",
    # `proved` reads tests/last_run.json, run_history.jsonl and the manifest
    # and writes nothing. It was left out when it was added on 2026-09-03,
    # and the stroke that should have caught that had an `or` clause which
    # could not fail -- so counsel at the table could not ask the estate what
    # it had proved, which is exactly the question a reviewing seat should be
    # able to ask.
    "proved",
    # `inspect` reads a file's FACTS and never its contents (2026-09-07).
    "inspect",
}

# What actually puts something on disk. The write-claim check (sitting 70)
# asks whether any of these ran before a seat is allowed to say a file was
# saved. Maintained beside REVIEW_ONLY_SKILLS for the same reason: a rule
# about "writers" that drifts from the writers is worse than no rule.
WRITING_SKILLS = {
    "write_file", "remember", "embed_text", "git_commit", "git_init",
    # git_cycle commits AND pushes; it is the most writing thing here.
    "git_cycle",
    "index_ground", "rack_sync",
    # 2026-09-08 (the REPL read): pull and push were missing, so the
    # write-claim check refused a TRUE claim on a turn where only one of
    # them ran. Both change the repo; both belong here.
    "git_pull", "git_push",
}


@dataclass
class SkillExecutionEnv:
    """Everything a skill handler is allowed to touch."""

    workspace: Path
    registry: AgentRegistry
    runtime: object  # OllamaRuntime; untyped to avoid a circular import
    ground: Path = None      # manjuel's own dir: index + config live here
    session: str = ""        # the sitting that produced this run
    run_ref: str = ""        # transcript this run will be written to
    objective: str = ""      # what the operator actually asked for
    review_only: bool = False  # counsel mode: reading skills only
    # The seat currently holding the hands, and what it is cleared for.
    # None = unrestricted (the engine's own calls, /rack, /index). A SET,
    # even an empty one, is a grant and is enforced. Granting by omission
    # from tools= keeps a seat from seeing what it may not use; this is the
    # backstop, because a model can name a tool nobody offered it.
    caller: str = ""
    caller_allowed: set | None = None
    dialogue: list = None      # recent thread, for context-resolved names
    skills_ref: object = None  # the SkillLibrary, for skills that survey the ground
    default_roots: list = None
    # Run one scoped sub-objective on its own context and return its
    # result. INJECTED by the pipeline, because skills.py reaching up into
    # pipeline.py would invert the containment rule. None outside a running
    # chain, and `subtask` says so plainly rather than pretending.
    sub_run: object = None

    def __post_init__(self):
        if self.dialogue is None:
            self.dialogue = []
        if self.ground is None:
            self.ground = self.workspace.parent
        if self.default_roots is None:
            self.default_roots = [self.workspace, self.ground / "logs"]

    def safe_path(self, filename: str) -> Path:
        """Jail file access to the workspace -- SUBDIRECTORIES included.

        Sitting 32: the operator put python-3.14-docs-text/ in the workspace
        and basename() made every file in it unreachable -- seats then
        narrated reads that never happened. Relative paths now resolve, but
        only to targets that stay inside the workspace; anything that
        escapes collapses to its basename as before.
        """
        clean = (filename or "").strip().strip("\'\"`")
        candidate = (self.workspace / clean).resolve()
        ws = self.workspace.resolve()
        if ws == candidate or ws in candidate.parents:
            return candidate
        # THE JAIL ANSWERS IN ONE FORM. This returned
        # `self.workspace / base` -- UNRESOLVED -- while the branch
        # above returns a resolved path, so the same jail gave two
        # spellings of one directory depending on which way a call
        # went. On Windows that is not cosmetic: the CI runner works
        # under a path carrying an 8.3 SHORT NAME (RUNNER~1), so this
        # branch answered the short form while workspace.resolve()
        # gives the long one, and a caller comparing the jailed answer
        # against the jail saw a mismatch for a correctly jailed path.
        # Linux has no short names -- which is why only the two Windows
        # legs were red and both Ubuntu legs passed (2026-09-10).
        return ws / os.path.basename(clean)


# =====================================================================
# Handlers
# =====================================================================


# THE JAIL'S OWN NAME IS NOT A PATH INTO IT (sitting 88, 2026-09-07). The
# Router asked ground_read for `ground/pipelines.md`: the schema says "the
# ground (the Research folder)", so it wrote the folder's name in front of
# the file, and the read looked for Research/ground/pipelines.md. Five hops
# and three refusals to read a file the operator named in two words. The
# law gate already treats the ground's own absolute path as "not a reach";
# this is the same ruling for the relative spellings a seat produces.
_JAIL_NAMES = ("ground/", "ground\\", "research/", "research\\", "./", ".\\")


def unjail(rel: str) -> str:
    """Strip the jail's own name(s) off the front of a relative path."""
    rel = (rel or "").strip()
    changed = True
    while changed and rel:
        changed = False
        low = rel.lower()
        for name in _JAIL_NAMES:
            if low.startswith(name):
                rel = rel[len(name):].lstrip("/\\")
                changed = True
                break
    return rel


def find_by_name(env, name: str, limit: int = 5) -> list[str]:
    """Real files in the ground whose basename matches `name`, case-
    insensitively, as ground-relative paths. For the cure in a "not a
    file" error (sitting 88: the Router asked for `estate_laws.md` at the
    root; it is `law/ESTATE_LAWS.md`, and the error said only "not a file").

    NEVER NAMES what a seat may not read: dot-folders, __pycache__, the
    index, `worlds/` (SITTING LAW 2 -- client material is never named),
    any `vault/`, secrets, protected files. Bounded by `limit`."""
    from .vectors import is_protected, is_secret
    want = os.path.basename((name or "").strip().strip("'\"`")).lower()
    if not want:
        return []
    ground = Path(env.ground)
    out: list[str] = []
    for root, dirs, files in os.walk(ground):
        dirs[:] = sorted(d for d in dirs
                         if not d.startswith(".") and d != "__pycache__"
                         and d.lower() not in ("index", "worlds", "vault",
                                               "agent_workspace"))
        for f in files:
            if f.lower() != want or is_secret(f):
                continue
            p = Path(root) / f
            if is_protected(p, peek=False):
                continue
            out.append(p.relative_to(ground).as_posix())
            if len(out) >= limit:
                return out
    return out


def _inside_ground(env, rel: str) -> Path | None:
    """Resolve a relative path and refuse anything that escapes the ground."""
    rel = unjail(rel)
    if not rel or rel.startswith(("/", "\\")) or ":" in rel:
        return None
    cand = (Path(env.ground) / rel).resolve()
    ground = Path(env.ground).resolve()
    if ground not in cand.parents and cand != ground:
        return None
    return cand


def gate_paths(spec, args: dict, env) -> str:
    """LAW 8 -- one write-path per chain. Refuse a declared path argument that
    resolves outside its jail, BEFORE any handler runs. Returns the refusal
    text, or "" to allow.

    Containment used to live inside the handlers: safe_path() for writes,
    _inside_ground() for reads, called by discipline, once per handler. Five of
    twenty-six called one of them; the other twenty-one called neither, and
    nothing in the ground distinguished "has no path to jail" from "forgot to
    jail it". Dispatch is the one place that cannot be forgotten, because
    everything a model asks for goes through it.

    Gate the RESOLVED path, never the stated one -- an intent-reading check
    passes a bad path written under a good intention.

    Fail closed, the doctrine vram.py already states for its own resource:
    guessing turns the guard into a rubber stamp. An unknown jail, a drive
    letter, a leading separator, or a path that will not resolve all refuse.
    """
    if spec is None or not spec.path_args:
        return ""
    for name, jail in spec.path_args:
        raw = (args.get(name) or "").strip().strip("'\"`")
        if not raw:
            continue                    # absent is the handler's business
        # PROSE IS NOT A PATH (sitting 70, and the third time this month).
        # The Router asked ground_list for the folder 'list available files
        # in ground'; earlier it asked ground_read for 'review sitting 63
        # transcripts in logs/ directory' and read_file for a sentence.
        # Every one was refused DOWNSTREAM with "is not a folder", which is
        # true and useless -- the seat had described what it wanted instead
        # of naming it, and nothing told it so.
        #
        # A real path is one thing: it has a separator, or an extension, or
        # it is a single name. Three or more bare words is a description.
        if (len(raw.split()) >= 3 and "/" not in raw and "\\" not in raw
                and "." not in raw):
            return (f"Refused: `{name}` must be a PATH, and {raw!r} is a "
                    f"description of one. Name the folder or file itself — "
                    f"`agents`, `manjuel/intent.py`, `pipelines.md` — or "
                    f"leave it empty to take the default. Nothing was run.")
        if jail not in JAILS:
            return (f"Refused {GATE_MARK}: '{spec.keyword}' declares an unknown jail "
                    f"{jail!r} for <{name}>. Known jails: {', '.join(JAILS)}.")
        root = env.workspace if jail == "workspace" else Path(env.ground)
        # A rooted path is not a path INTO the jail: joining one drops the root
        # on posix and keeps the drive on Windows. Refused before the join,
        # same test _inside_ground already makes for the same reason.
        if raw.startswith(("/", "\\")) or ":" in raw:
            return (f"Refused {GATE_MARK}: <{name}> '{raw}' is an absolute path, and so is "
                    f"outside the {jail}. Give a path relative to it. "
                    f"Nothing was done.")
        try:
            cand = (Path(root) / raw).resolve()
            base = Path(root).resolve()
        except (OSError, ValueError) as exc:
            return (f"Refused {GATE_MARK}: <{name}> '{raw}' could not be resolved "
                    f"({type(exc).__name__}: {exc}), so it cannot be shown to "
                    f"be inside the {jail}. Nothing was done.")
        if cand != base and base not in cand.parents:
            return (f"Refused {GATE_MARK}: <{name}> '{raw}' resolves outside the {jail}. "
                    f"Nothing was done.")
    return ""


@skill("ground_list")
def _ground_list(env: SkillExecutionEnv, args: dict) -> str:
    """The ground as it stands on disk. Live, read-only.

    The index is a snapshot; this is the floor. `list_directory` shows only
    the seats' scratch, which kept answering repo questions with one file.
    """
    rel = unjail((args.get("content") or "").strip().strip("\'\"`").strip("/\\"))
    # Sitting 77: the Router passed the WHOLE OBJECTIVE as the folder --
    # "what is in the /skills dir" -- and the refusal came back as
    # "'what is in the /skills dir' is not a folder inside the ground."
    # That was accurate and it was also read as a verdict about the
    # DIRECTORY: the Router concluded it had "no evidence that a /skills
    # directory exists", with three tool hops still in hand and having
    # already written down the correct next call. A sentence is never a
    # folder name and that is decidable here, before the disk is touched,
    # so the refusal names WHICH mistake was made and what to send instead.
    if rel and (len(rel.split()) > 1 or "\n" in rel):
        return (f"Error: a folder NAME was expected here, not a sentence. "
                f"Got {rel[:60]!r}. This says nothing about whether that "
                f"folder exists -- it was never looked up. Call ground_list "
                f"again with the bare folder, e.g. "
                f"<content>skills</content>, or with no content at all for "
                f"the top level.")
    base = _inside_ground(env, rel) if rel else Path(env.ground)
    if base is None or not base.is_dir():
        return (f"Error: '{rel}' is not a folder inside the ground. "
                f"Call ground_list with no content to see what is.")
    from .vectors import is_protected, is_secret
    dirs, files = [], []
    for item in sorted(base.iterdir(), key=lambda x: x.name.lower()):
        if item.name.startswith(".") or item.name == "__pycache__":
            continue
        if is_secret(item.name):
            continue
        if item.is_dir() and item.name.lower() == "vault":
            try:
                n = sum(1 for _ in item.iterdir())
            except OSError:
                n = 0
            dirs.append(f"  vault/  ({n} protected items — contents never listed)")
            continue
        if is_protected(item, peek=False):
            continue
        if item.is_dir():
            try:
                n = sum(1 for _ in item.iterdir())
            except OSError:
                n = 0
            dirs.append(f"  {item.name}/  ({n} items)")
        else:
            files.append(f"  {item.name}  ({item.stat().st_size:,} bytes)")
    where = rel or "the ground"
    # THE TOTAL IS PART OF THE RESULT. Without it the closing seat counts
    # the lines itself, and on 2026-09-08 and 2026-09-09 it counted 35 and
    # 36 against a true 37 -- twice blocking a tag, because the standup's
    # number guard rightly refuses a figure no tool returned. A number a
    # seat can QUOTE cannot be miscounted. It counts what is LISTED: the
    # filters above drop secrets and protected items, and a total that
    # included them would not reconcile against the lines beneath it.
    n = len(dirs) + len(files)
    tally = (f"{n} entr{'y' if n == 1 else 'ies'} listed "
             f"({len(dirs)} folder{'' if len(dirs) == 1 else 's'}, "
             f"{len(files)} file{'' if len(files) == 1 else 's'})")
    return (f"Contents of {where}, live from disk (read-only) -- {tally}:\n"
            + "\n".join(dirs + files))


READ_WINDOW = 12000

_HEADING = re.compile(r"^(#{1,6})[ \t]+(?P<t>.+?)[ \t]*$", re.MULTILINE)


def _windowed_python(text: str, rel: str, want: str):
    """A .py cut by definition. None => caller falls back to the char path.

    Returns None when the file does not parse, when it declares nothing
    top-level worth mapping, or when `want` is a number -- a numbered part
    is a request about CHARACTERS and the caller already answers it.
    """
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError, RecursionError) as exc:
        # Named, not swallowed: a seat reading a broken file should be told
        # the file is broken, which is usually why it is being read.
        return (f"{rel} does not parse ({type(exc).__name__}: {exc}), so it "
                f"cannot be cut by definition. Falling back to character "
                f"windows.\n\n" + _windowed_chars(text, rel, ""))

    lines = text.splitlines(keepends=True)
    defs: list[tuple[str, int, int]] = []

    def add(node, prefix=""):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            end = getattr(node, "end_lineno", None) or node.lineno
            defs.append((prefix + node.name, node.lineno, end))
            if isinstance(node, ast.ClassDef):
                for child in node.body:
                    add(child, prefix + node.name + ".")

    for node in tree.body:
        add(node)
    if not defs:
        return None

    if want and not want.isdigit():
        low = want.lower()
        # Exact name first, then a containing match -- so `execute` finds
        # `execute` and not `SkillLibrary.execute_all` by accident.
        hit = next((d for d in defs if d[0].lower() == low), None) \
            or next((d for d in defs if low in d[0].lower()), None)
        if hit:
            name, lo, hi = hit
            body = "".join(lines[lo - 1:hi])
            note = ""
            if len(body) > READ_WINDOW:
                body = body[:READ_WINDOW]
                note = (f"\n... ({name} is {hi - lo + 1} lines; this is its "
                        f"first window)")
            return (f"{rel} — `{name}`, lines {lo}-{hi} of {len(lines)}"
                    f" (a WHOLE definition, not a character range):\n\n"
                    f"{body}{note}")
        return (f"No definition in {rel} is called {want!r}. It declares:\n  "
                + "\n  ".join(f"{n}  (lines {a}-{b})" for n, a, b in defs[:60])
                + (f"\n  ... and {len(defs) - 60} more" if len(defs) > 60 else ""))

    if want.isdigit():
        return None          # a numbered part is a character request

    top = [d for d in defs if "." not in d[0]]
    return (f"{rel} — {len(lines)} lines, {len(defs)} definitions. THIS IS "
            f"THE MAP, NOT THE FILE.\n\n"
            f"Ask for any one BY NAME and get the whole definition:\n  "
            + "\n  ".join(f"{n}  (lines {a}-{b})" for n, a, b in top[:60])
            + (f"\n  ... and {len(top) - 60} more" if len(top) > 60 else "")
            + (f"\n\nMethods are addressable too, as Class.method — "
               f"{len(defs) - len(top)} of them."
               if len(defs) > len(top) else "")
            + f"\n\nOr ask for a numbered part, 1 to "
              f"{(len(text) - 1) // READ_WINDOW + 1}, for raw character "
              f"windows.")


def _windowed_chars(text: str, rel: str, want: str) -> str:
    """The original character-window path, unchanged, reachable on its own."""
    heads = [(m.start(), m.group("t").strip()) for m in _HEADING.finditer(text)]
    total = (len(text) - 1) // READ_WINDOW + 1
    n = max(1, min(total, int(want) if want.isdigit() else 1))
    lo = (n - 1) * READ_WINDOW
    body = text[lo:lo + READ_WINDOW]
    out = [f"{rel} — part {n} of {total} "
           f"(chars {lo:,}-{min(len(text), lo + READ_WINDOW):,} "
           f"of {len(text):,}). THIS IS NOT THE WHOLE FILE.", "", body, ""]
    if n < total:
        out.append(f"To continue, read it again asking for part {n + 1}.")
    return "\n".join(out)


def windowed(text: str, rel: str, part: str = "") -> str:
    """A big file as a MOVABLE WINDOW, never a silent first slice.

    The old rule was `text[:12000] + "(truncated)"`. SEAT_LOG.md is 136KB,
    so a seat asked to review it was handed the first 9% and reasoned about
    the top of the file without feeling the rest. A longer model window
    does not fix that -- 136KB does not fit in 8192 tokens either. What
    fixes it is letting the seat MOVE:

      no part      the first window, plus a MAP of the file's own headings
                   with the part-name to ask for
      part=2       the second window (parts are 1-based, in order)
      part=<text>  the section whose heading contains that text

    Each part is a FULL window over DIFFERENT material -- the map half of
    the chain's context, and the only kind of expansion that loses nothing
    inside the slice it reads (DESIGN 11: serial chains compound error).
    """
    if len(text) <= READ_WINDOW:
        return f"{rel} as on disk right now:\n\n{text}"

    want = (part or "").strip().strip("'\"`")

    # A PYTHON FILE IS CUT BY DEFINITION, NOT BY CHARACTER (DESIGN 14.10,
    # use 3). `_HEADING` matches a markdown `#`, and in Python that is a
    # COMMENT -- so a 99KB module offered its docstring prose as navigable
    # "sections", and a seat asking for one got a fragment of a sentence.
    # A char offset is worse still: it lands mid-expression, so the window
    # a seat reads may not be valid Python at either end.
    #
    # The right slice is a def. `ast` gives exact line bounds, so the
    # window is a WHOLE function and the map is the file's real shape.
    #
    # A FILE THAT DOES NOT PARSE STILL READS, and that matters more than
    # the feature: a broken .py is exactly the file you open to fix the
    # break. On SyntaxError this falls through to the char path and says
    # why, rather than refusing the one read that was needed.
    if rel.lower().endswith(".py"):
        out = _windowed_python(text, rel, want)
        if out is not None:
            return out

    heads = [(m.start(), m.group("t").strip()) for m in _HEADING.finditer(text)]

    # A named section: the heading that matches, up to the next one of the
    # same depth or shallower. Named beats numbered when both are given.
    if want and not want.isdigit():
        low = want.lower()
        for i, (pos, title) in enumerate(heads):
            if low in title.lower():
                end = len(text)
                for npos, _ in heads[i + 1:]:
                    end = npos
                    break
                body = text[pos:end]
                if len(body) > READ_WINDOW:
                    body = (body[:READ_WINDOW]
                            + f"\n... (section is {len(body):,} chars; this is "
                              f"its first window)")
                return (f"{rel} — section {title!r}, "
                        f"chars {pos:,}-{min(end, pos + READ_WINDOW):,} "
                        f"of {len(text):,}:\n\n{body}")
        return (f"No heading in {rel} contains {want!r}. Its headings are:\n  "
                + "\n  ".join(t for _, t in heads[:40])
                + f"\n\nOr ask for a numbered part, 1 to "
                  f"{(len(text) - 1) // READ_WINDOW + 1}.")

    total = (len(text) - 1) // READ_WINDOW + 1
    n = max(1, min(total, int(want) if want.isdigit() else 1))
    lo = (n - 1) * READ_WINDOW
    body = text[lo:lo + READ_WINDOW]

    out = [f"{rel} — part {n} of {total} "
           f"(chars {lo:,}-{min(len(text), lo + READ_WINDOW):,} "
           f"of {len(text):,}). THIS IS NOT THE WHOLE FILE.",
           ""]
    out.append(body)
    out.append("")
    if n < total:
        out.append(f"To continue, read it again asking for part {n + 1}.")
    if heads and n == 1:
        out.append("")
        out.append("Its sections, if you want one directly by name:")
        for _, t in heads[:40]:
            out.append(f"  {t}")
        if len(heads) > 40:
            out.append(f"  ... and {len(heads) - 40} more")
    return "\n".join(out)


_SITTING_HEAD = re.compile(
    r"^##[ \t]+(?P<date>\S+)[ \t]+—[ \t]+sitting[ \t]+(?P<n>\d+)\b[^\n]*$",
    re.MULTILINE)
_RUN_LINE = re.compile(
    r"^\s{2,}(?P<i>\d+)\.\s+(?P<what>.+?)\n\s+(?P<meta>[^\n]*?)"
    r"(?P<path>logs/[^\s]+\.md)\s*$", re.MULTILINE)


@skill("sitting")
def _sitting(env: SkillExecutionEnv, args: dict) -> str:
    """Resolve a SITTING NUMBER to the runs it held and their transcripts.

    Sitting 63 asked the chain to review sitting 63 and it could not: runs
    are filed by timestamp, sittings are numbered, and NOTHING mapped one
    to the other. The Router guessed `logs/sitting_63.md`, then passed
    whole sentences as filepaths. Every guess was refused correctly -- but
    guarding a guess is not answering the question.

    SEAT_LOG.md already holds the map; it is 136KB, so reading it whole is
    not a sane tool call. This reads the ONE block that belongs to the
    sitting and returns its run list with paths, which `ground_read` can
    then open. Facts read, never generated: if the toll for a sitting was
    never paid, that is what comes back, because an unpaid toll is a fact
    about the record and not a licence to invent one.
    """
    raw = (args.get("content") or args.get("filepath") or "").strip()
    if not raw:
        raw = getattr(env, "objective", "") or ""
    m = re.search(r"\d+", raw)
    if not m:
        return ("Error: name the sitting by number, e.g. "
                "<content>63</content>.")
    n = int(m.group(0))

    log = Path(env.ground) / "SEAT_LOG.md"
    if not log.is_file():
        return "Error: SEAT_LOG.md is not in the ground; no sittings recorded."
    text = log.read_text(encoding="utf-8", errors="replace")

    blocks = []
    heads = list(_SITTING_HEAD.finditer(text))
    for i, h in enumerate(heads):
        if int(h.group("n")) != n:
            continue
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        # An "outside hand" reading is filed under its own ## heading and is
        # not a toll; stop at the first one so a reading is not read as runs.
        cut = text.find("\n## ", h.end(), end)
        blocks.append(text[h.start():cut if cut != -1 else end])

    if not blocks:
        highest = max((int(h.group("n")) for h in heads), default=0)
        return (f"No toll for sitting {n} is in SEAT_LOG.md. The record runs "
                f"to sitting {highest}. A sitting with no toll still has its "
                f"transcripts in logs/ -- they are filed by timestamp, not by "
                f"number, so name a date or read the folder.")

    out = [f"Sitting {n} — from SEAT_LOG.md, the paid record"]
    if len(blocks) > 1:
        out.append(f"({len(blocks)} tolls stand for this sitting; the later "
                   f"supersedes, both are kept — LAW 1)")
    for b in blocks:
        head = b.splitlines()[0].lstrip("# ").strip()
        out.append("")
        out.append(head)
        seat = re.search(r"^\*\*The seat:\*\*[ \t]*(.+)$", b, re.MULTILINE)
        if seat:
            out.append(f"  {seat.group(1).strip()}")
        runs = list(_RUN_LINE.finditer(b))
        if not runs:
            out.append("  (the toll records no runs)")
        for r in runs:
            out.append(f"  {r.group('i')}. {r.group('what').strip()}")
            out.append(f"     {r.group('path')}")
    out.append("")
    out.append("Read any of those with ground_read to see the run in full.")
    return "\n".join(out)


# The most a hit's age may move it in the search ranking. Small by design:
# it breaks ties between comparably relevant passages and never outvotes
# meaning. See _rank() in semantic_search for why the doctrine is exempt.
RECENCY_WEIGHT = 0.04

_STAMPED = re.compile(r"^(?P<d>\d{4}-\d{2}-\d{2})_(?P<t>\d{6})_(?P<slug>.+)\.md$")

# What a person says, in days back from today. `None` means "since", not a
# single day. Deliberately small: an unrecognised phrase is answered with
# the list of what IS understood, never guessed at.
_WHEN_WORDS = {
    "today": (0, 0), "this morning": (0, 0), "tonight": (0, 0),
    "yesterday": (1, 1), "last night": (1, 1),
    "this week": (7, 0), "the last week": (7, 0), "past week": (7, 0),
    "this month": (30, 0), "the last month": (30, 0), "past month": (30, 0),
    "recently": (3, 0), "lately": (3, 0), "the last few days": (3, 0),
}


@skill("when")
def _when(env: SkillExecutionEnv, args: dict) -> str:
    """What ran in a WINDOW OF TIME, from the transcript filenames.

    Runs are stamped `<date>_<time>_<slug>.md`, so a period is answerable
    by ARITHMETIC over the folder -- no model, no index, no embedding. The
    estate stamped everything and could still not answer "what did we do
    yesterday", because nothing read the stamps as a range.

    Pairs with `sitting`: that resolves a NUMBER to its runs, this resolves
    a PERIOD to its runs. The timestamp is the atom; the sitting is the
    molecule the operator declares by opening the REPL.
    """
    from datetime import date, datetime, timedelta

    raw = (args.get("content") or args.get("filepath") or "").strip().lower()
    if not raw:
        raw = (getattr(env, "objective", "") or "").lower()

    today = date.today()
    lo = hi = None
    label = ""

    exact = re.search(r"(\d{4}-\d{2}-\d{2})", raw)
    if exact:
        try:
            d = datetime.strptime(exact.group(1), "%Y-%m-%d").date()
            lo = hi = d
            label = f"on {d.isoformat()}"
        except ValueError:
            pass
    if lo is None:
        for phrase in sorted(_WHEN_WORDS, key=len, reverse=True):
            if phrase in raw:
                back, fwd = _WHEN_WORDS[phrase]
                lo, hi = today - timedelta(days=back), today - timedelta(days=fwd)
                label = phrase
                break
    if lo is None:
        m = re.search(r"(?:last|past)\s+(\d+)\s+day", raw)
        if m:
            lo, hi = today - timedelta(days=int(m.group(1))), today
            label = f"the last {m.group(1)} days"
    if lo is None:
        return ("Error: name the period. Understood: today, yesterday, this "
                "week, this month, recently, 'the last N days', or a date "
                "as YYYY-MM-DD. For a numbered sitting use the `sitting` "
                "skill instead -- a sitting is a unit of work, not a period.")

    logs = Path(env.ground) / "logs"
    if not logs.is_dir():
        return "No logs/ folder in the ground; nothing has been transcribed."

    found = []
    for f in logs.glob("*.md"):
        m = _STAMPED.match(f.name)
        if not m:
            continue
        try:
            d = datetime.strptime(m.group("d"), "%Y-%m-%d").date()
        except ValueError:
            continue
        if lo <= d <= hi:
            found.append((m.group("d"), m.group("t"), m.group("slug"), f.name))

    if not found:
        return (f"Nothing ran {label} — no transcript in logs/ carries a date "
                f"in that window ({lo.isoformat()} to {hi.isoformat()}). That "
                f"is the record being empty, not a search failing.")

    found.sort()
    out = [f"What ran {label} — {len(found)} run"
           f"{'' if len(found) == 1 else 's'} "
           f"({lo.isoformat()} to {hi.isoformat()}), from the transcripts",
           ""]
    day = ""
    for d, t, slug, name in found:
        if d != day:
            day = d
            out.append(f"{d}")
        clock = f"{t[:2]}:{t[2:4]}"
        out.append(f"  {clock}  {slug.replace('_', ' ')}")
        out.append(f"         logs/{name}")
    out.append("")
    out.append("Read any of those with ground_read to see the run in full.")
    return "\n".join(out)


def _describe(spec) -> str:
    """A skill's own words about itself, whole -- not the routing stub."""
    m = _DESC_RE.search(spec.body)
    desc = " ".join((m.group("d") if m else spec.body).split())
    return desc[:700]


@skill("skill_search")
def _skill_search(env: SkillExecutionEnv, args: dict) -> str:
    """What the chain can do about a subject, from the skills' own files.

    Two jobs, one mechanism. The operator asking "what can you do about
    invoices" gets candidates; and a question ABOUT a named tool ("what
    does deep research do?") is answered from that tool's markdown rather
    than by RUNNING it -- which is what sitting 69 did, before reporting
    the description as work completed.

    Scored by word overlap, not by embedding: the corpus is thirty-odd
    short descriptions, the query is a handful of words, and an embedder
    on text that short buys noise and a model load. Arithmetic is enough
    here, and it cannot hallucinate a match.
    """
    lib = getattr(env, "skills_ref", None)
    if lib is None:
        return "Error: the skill library is not available here."
    q = (args.get("content") or args.get("filepath") or "").strip()
    if not q:
        q = (getattr(env, "objective", "") or "").strip()
    if not q:
        return "Error: name what you want the chain to do, e.g. <content>read a file</content>."

    words = {w for w in re.findall(r"[a-z0-9_]+", q.lower()) if len(w) > 2}
    rows = []
    for s in lib.specs:
        hay = f"{s.keyword} {s.keyword.replace('_', ' ')} {_describe(s)} " \
              f"{' '.join(s.says or ())}".lower()
        hit = sum(1 for w in words if w in hay)
        exact = 2 if (s.keyword in q.lower().replace(" ", "_")
                      or s.keyword.replace("_", " ") in q.lower()) else 0
        if hit or exact:
            rows.append((hit + exact * 3, s))
    if not rows:
        return (f"No skill in this ground matches {q!r}. The chain has "
                f"{len(lib.specs)} of them; `skill_report` lists every one.")

    rows.sort(key=lambda r: (-r[0], r[1].keyword))
    out = [f"Skills matching {q!r}, from their own declarations:"]
    for _, s in rows[:5]:
        out.append("")
        out.append(f"  {s.keyword}   ({s.filename})")
        out.append(f"    {_describe(s)}")
        if s.says:
            out.append(f"    also answers to: {', '.join(s.says)}")
    if len(rows) > 5:
        out.append("")
        out.append(f"  ... and {len(rows) - 5} more; `skill_report` lists all.")
    out.append("")
    out.append("These are DESCRIPTIONS, read from the files. Nothing was run.")
    return "\n".join(out)


@skill("subtask")
def _subtask(env: SkillExecutionEnv, args: dict) -> str:
    """Hand one scoped piece of work to a fresh run of its own.

    The map half of the chain: the sub-task gets its OWN full window over
    its OWN material, rather than this turn's window being asked to hold
    everything. Only its result comes back, marked as another seat's words.

    The capability is INJECTED by the pipeline (`env.sub_run`), not
    imported: skills.py knowing about pipeline.py would invert the
    containment rule for one call. Absent it -- a skill run outside a
    pipeline, as the suites do -- this says so instead of pretending.
    """
    run = getattr(env, "sub_run", None)
    if run is None:
        return ("Error: sub-tasks are not available here — this skill was "
                "called outside a running chain.")
    objective = (args.get("content") or args.get("filepath") or "").strip()
    if not objective:
        return ("Error: name the sub-task, e.g. <content>read pipelines.md "
                "and list the seats in the default spine</content>. It must "
                "be ONE piece of work, stated whole: the sub-task cannot see "
                "this conversation.")
    return run(objective)


@skill("ground_read")
def _ground_read(env: SkillExecutionEnv, args: dict) -> str:
    """One real file, as it is right now. Read-only; secrets refused."""
    # BOTH tags present => filepath is the file and content is the PART
    # (a name or a number). Only one present => it is the file. The tool
    # grammar has three tags and no fourth, so the part rides on <content>
    # rather than inventing a <part> the parser would drop on the floor --
    # and this way "read x.md" still means the whole of x.md.
    part = args.get("filepath", "").strip() and args.get("content", "").strip()
    rel = (args.get("filepath") or args.get("content") or "").strip()
    if not rel:
        from .intent import names_a_file, last_file_in
        rel = names_a_file(getattr(env, "objective", "") or "")
        if not rel:
            # "read the file" / "this file": the one we were just discussing.
            rel = last_file_in(getattr(env, "dialogue", []) or [])
    # Sitting 30: the Router quoted the filename -- '"pipelines.md"' -- and
    # the read failed on a file that was right there. Quoting is not part
    # of a name.
    rel = unjail(rel.strip("\'\"`").strip())
    if not rel:
        return "Error: name the file, relative to the ground (e.g. pipelines.md)."
    path = _inside_ground(env, rel)
    if path is None:
        return f"Error: '{rel}' is outside the ground; only Research is readable."
    from .vectors import is_protected, is_secret
    if is_secret(path.name):
        return f"Refused: '{path.name}' is a secret and is never read aloud (LAW 9)."
    if is_protected(path):
        return ("Refused: that is CLIENT DATA — tagged protected, never read "
                "into the chain, never indexed, never cross-referenced. The "
                "operator handles it by hand.")
    if not path.is_file():
        # NAME THE CURE (sitting 88). The file may exist elsewhere in the
        # ground under this name; if it does, say where, so the next hop
        # reads instead of guessing again.
        found = find_by_name(env, rel)
        if len(found) == 1:
            return (f"Error: '{rel}' is not a file at that path. A file of "
                    f"that name IS in the ground: `{found[0]}` -- call "
                    f"ground_read with <filepath>{found[0]}</filepath>.")
        if found:
            return (f"Error: '{rel}' is not a file at that path. Files of "
                    f"that name in the ground: "
                    + ", ".join(f"`{f}`" for f in found)
                    + " -- name one of them.")
        return f"Error: '{rel}' is not a file in the ground."
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return f"Read error: {exc}"
    return windowed(text, rel, part or "")


# THE INSPECTION (2026-09-07, the operator: "a skill that is able to review
# the files before it does anything with them ... 'its x bytes' 'its y
# filetype' 'its timestamped this' ... so it knows how to not be prompt
# injected, it knows how to safely review what it is working on, even if it
# may be something from an unverified source" -- "like open source code from
# github"). The ruling it makes into a tool is from 2026-08-29, sittings
# 18-27: outside material lands in the WORKSPACE, and the workspace is the
# quarantine. FACTS ONLY, never contents; no model; the reader decides.
_MAGIC = (
    (b"%PDF", "pdf"), (b"PK\x03\x04", "zip (or docx/xlsx/jar)"),
    (b"\x89PNG", "png"), (b"\xff\xd8\xff", "jpeg"), (b"GIF8", "gif"),
    (b"MZ", "windows executable"), (b"\x7fELF", "elf executable"),
    (b"\x1f\x8b", "gzip"), (b"SQLite format 3", "sqlite database"),
    (b"#!", "script with a shebang"),
)
INSPECT_TEXT_CAP = 2_000_000


def _file_type(head: bytes) -> str:
    for magic, name in _MAGIC:
        if head.startswith(magic):
            return name
    if head.startswith((b"\xff\xfe", b"\xfe\xff")):
        return "utf-16 text"
    if b"\x00" in head[:4096]:
        return "binary (unknown)"
    try:
        head.decode("utf-8")
        return "utf-8 text"
    except UnicodeDecodeError:
        return "text, not utf-8"


def _terminator(data: bytes) -> str:
    crlf = data.count(b"\r\n")
    lf = data.count(b"\n") - crlf
    if crlf and lf:
        return f"MIXED ({crlf} CRLF, {lf} LF)"
    if crlf:
        return "CRLF"
    if lf:
        return "LF"
    return "none"


def _git_tracks(ground: Path, rel: str) -> str:
    try:
        rc, out = _git._run(["ls-files", "--error-unmatch", "--", rel], ground)
    except Exception:
        return "git: not available"
    if rc == 0 and out:
        return "git: tracked"
    if not (Path(ground) / ".git").exists():
        return "git: this ground is not a repository"
    return "git: UNTRACKED (not versioned; arrived outside a commit)"


def _indexed(env, path: Path) -> str:
    db = Path(env.ground) / "index" / "vectors.db"
    if not db.exists():
        return "index: no index built"
    try:
        import sqlite3
        c = sqlite3.connect(str(db))
        n = c.execute("SELECT COUNT(*) FROM docs WHERE path = ?", (str(path),)).fetchone()[0]
        c.close()
    except Exception as exc:
        return f"index: unreadable ({type(exc).__name__})"
    return "index: held" if n else "index: NOT held (nothing has embedded it)"


def _age(ts: float) -> str:
    import time as _t
    sec = max(0.0, _t.time() - ts)
    if sec < 90:
        return "just now"
    if sec < 5400:
        return f"{int(sec // 60)}m ago"
    if sec < 129600:
        return f"{sec / 3600:.0f}h ago"
    return f"{sec / 86400:.0f}d ago"


def inspect_file(env, rel: str) -> str:
    """The facts about one file, as a block. The workspace is tried first,
    then the ground. A secret or client file is named as such and NOTHING
    else about it is read."""
    from .vectors import is_protected, is_secret
    from .intent import injection_markers
    from datetime import datetime
    rel = unjail((rel or "").strip().strip("'\"`"))
    if not rel:
        return "Error: name the file to inspect, or leave it out for what is new in the workspace."
    if rel.startswith(("/", "\\")) or ":" in rel:
        return f"Refused {GATE_MARK}: '{rel}' is an absolute path; give one relative to the workspace or the ground."
    ws = Path(env.workspace).resolve()
    cand = (ws / rel).resolve()
    if (ws == cand or ws in cand.parents) and cand.is_file():
        path, jail = cand, "workspace"
    else:
        p = _inside_ground(env, rel)
        if p is None:
            return f"Error: '{rel}' is outside the ground; only Research is inspectable."
        if not p.is_file():
            found = find_by_name(env, rel)
            hint = (f" A file of that name IS in the ground: `{found[0]}`."
                    if len(found) == 1 else "")
            return f"Error: '{rel}' is not a file in the workspace or the ground.{hint}"
        path, jail = p, "ground"
    try:
        shown = path.relative_to(Path(env.ground).resolve()).as_posix()
    except ValueError:
        shown = rel
    if is_secret(path.name):
        return (f"{shown}: a SECRET by name. Nothing about it is read, shown or "
                f"indexed (LAW 9: keys are silent). Do not read it.")
    if is_protected(path):
        return (f"{shown}: CLIENT DATA by tag. Never read into the chain, never "
                f"indexed, never cross-referenced (SITTING LAW 2). Do not read it.")
    try:
        st = path.stat()
        with path.open("rb") as fh:
            data = fh.read(INSPECT_TEXT_CAP + 1)
    except OSError as exc:
        return f"Read error: {exc}"
    kind = _file_type(data[:8192])
    lines = [f"{shown} -- inspected, not read",
             f"  where     : the {jail}" + ("" if jail == "ground" else
                                             " (agent_workspace/; the quarantine for outside material)"),
             f"  size      : {st.st_size:,} bytes",
             f"  type      : {kind} (extension {path.suffix or 'none'})",
             f"  modified  : {datetime.fromtimestamp(st.st_mtime).strftime('%Y-%m-%d %H:%M')} ({_age(st.st_mtime)})",
             f"  {_git_tracks(Path(env.ground), shown)}",
             f"  {_indexed(env, path)}"]
    text_like = kind.endswith("text") or kind == "script with a shebang"
    if text_like:
        text = data[:INSPECT_TEXT_CAP].decode("utf-8", errors="replace")
        n_lines = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
        first = next((l.strip() for l in text.splitlines() if l.strip()), "")
        marks = injection_markers(text)
        lines.append(f"  lines     : {n_lines:,}; terminator {_terminator(data)}")
        lines.append(f"  first line: {first[:120]!r}")
        lines.append(f"  injection : " + (f"{len(marks)} marker(s) -- " + "; ".join(marks)
                                          if marks else "0 markers found by the hard gate"))
        if st.st_size > INSPECT_TEXT_CAP:
            lines.append(f"  (only the first {INSPECT_TEXT_CAP:,} bytes were scanned)")
    else:
        lines.append("  lines     : n/a (not text); nothing inside it was scanned")
    reader = "read_file" if jail == "workspace" else "ground_read"
    lines.append(f"  to read it: {reader} <filepath>{rel if jail == 'workspace' else shown}</filepath>")
    lines.append("These are facts read off the file. Whether to trust it is the reader's call.")
    return "\n".join(lines)


def inspect_line(env, rel: str) -> str:
    """One line of the facts, for the stamp a workspace read carries."""
    block = inspect_file(env, rel)
    if block.startswith(("Error", "Refused")) or "-- inspected" not in block:
        return ""
    got = {}
    for l in block.splitlines()[1:]:
        if ":" in l:
            k, v = l.strip().split(":", 1)
            got[k.strip()] = v.strip()
    parts = [got.get("size", ""), got.get("type", ""),
             (got.get("modified", "").split("(")[-1].rstrip(")") if got.get("modified") else ""),
             next((l.strip() for l in block.splitlines() if l.strip().startswith("git:")), ""),
             got.get("injection", "")]
    return "inspected: " + "; ".join(p for p in parts if p)


@skill("inspect")
def _inspect(env: SkillExecutionEnv, args: dict) -> str:
    rel = (args.get("filepath") or args.get("content") or "").strip()
    if rel:
        return inspect_file(env, rel)
    # No path: what is NEW in the workspace since this sitting opened --
    # "review the new files". The sitting's start is the last opening line
    # of the ledger; with none, the last hour.
    import json as _json
    import time as _t
    since = _t.time() - 3600
    ledger = Path(env.ground) / "sessions" / "sessions.jsonl"
    try:
        for line in ledger.read_text(encoding="utf-8").splitlines():
            row = _json.loads(line) if line.strip() else {}
            if row.get("started"):
                from datetime import datetime
                since = datetime.fromisoformat(row["started"]).timestamp()
    except Exception:
        pass
    ws = Path(env.workspace)
    fresh = []
    try:
        for p in sorted(ws.rglob("*")):
            if p.is_file() and p.stat().st_mtime >= since and "__pycache__" not in p.parts:
                fresh.append(p)
    except OSError as exc:
        return f"Directory error: {exc}"
    if not fresh:
        return ("Nothing new in the workspace since this sitting opened. "
                "Name a file to inspect one.")
    out = [f"{len(fresh)} new file(s) in the workspace since this sitting opened:"]
    for p in fresh[:20]:
        out.append("")
        out.append(inspect_file(env, p.relative_to(ws).as_posix()))
    if len(fresh) > 20:
        out.append(f"\n... and {len(fresh) - 20} more; inspect them by name.")
    return "\n".join(out)


@skill("skill_report")
def _skill_report(env: SkillExecutionEnv, args: dict) -> str:
    """The chain's actual reach, read from the loaded library.

    Deterministic for the same reason as ground_report: a generated
    capability list invents capabilities. This one cannot -- it is the same
    manifest the Router routes against, so it is true by construction.
    """
    lib = getattr(env, "skills_ref", None)
    if lib is None:
        return "Error: the skill library is not attached to this run."
    lines = [f"The chain executes {len(lib.keywords())} skills:", ""]
    for spec in sorted(lib.specs, key=lambda x: x.keyword):
        d = _DESC_RE.search(spec.body)
        desc = " ".join(d.group("d").split()) if d else "(no description)"
        first = desc.split(". ")[0].rstrip(".") + "."
        if len(first) > 110:
            first = first[:110] + "..."
        lines.append(f"  {spec.keyword:20} {first}")
    lines.append("")
    lines.append("Each is declared in skills/*.md; the operator also has "
                 "/skills for binding status.")
    return "\n".join(lines)


@skill("ground_report")
def _ground_report(env: SkillExecutionEnv, args: dict) -> str:
    """Where the chain stands. Read, not generated -- a guessed path is a
    broken seal, and the harness holds every one of these as plain fact."""
    lines = [
        f"ground        : {env.ground}",
        f"workspace     : {env.workspace}  (seat scratch -- writes land here)",
        f"session       : {env.session or '(none)'}",
    ]
    try:
        n = sum(1 for x in env.workspace.iterdir())
        lines.append(f"workspace has : {n} item(s)")
    except Exception:
        pass
    try:
        res = env.runtime.resident()
        if res:
            lines.append("resident now  : " + ", ".join(t for t, _ in res))
    except Exception:
        pass
    return "\n".join(lines)


@skill("list_directory")
def _list_directory(env: SkillExecutionEnv, args: dict) -> str:
    try:
        items = sorted(p.name for p in env.workspace.iterdir())
    except Exception as exc:
        return f"Directory error: {exc}"
    scope = ("the agent workspace (agent_workspace/) -- scratch files only, "
             "NOT the whole repository")
    if not items:
        return f"Empty: {scope}."
    return (f"Contents of {scope}:\n"
            + "\n".join(f" - {i}" for i in items))


@skill("read_file")
def _read_file(env: SkillExecutionEnv, args: dict) -> str:
    filename = args.get("filepath", "").strip()
    if not filename:
        return "Error: missing <filepath> parameter."
    path = env.safe_path(filename)
    from .vectors import is_protected as _prot
    if _prot(path):
        return ("Refused: that is CLIENT DATA — tagged protected, never read "
                "into the chain. The operator handles it by hand.")
    if path.is_dir():
        try:
            items = sorted(x.name for x in path.iterdir())[:40]
        except OSError:
            items = []
        return (f"'{filename}' is a DIRECTORY, not a file -- nothing was "
                f"read. It contains: {', '.join(items) or '(empty)'}. "
                f"Name one of those files, or run index_ground and use "
                f"semantic_search to search inside them.")
    if not path.exists():
        return f"Error: workspace file '{filename}' not found."
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return f"Read error: {exc}"
    # Same grammar as ground_read: <filepath> names the file, <content>
    # names the part when both are given. THE STAMP (2026-09-07): a
    # workspace read carries one line of the file's facts in front of it,
    # so a seat reading outside material is told what it holds before the
    # words -- the inspection the operator asked for, made automatic at the
    # one door outside material comes through.
    stamp = inspect_line(env, filename)
    body = windowed(text, filename, args.get("content", "").strip())
    return f"{stamp}\n\n{body}" if stamp else body


@skill("write_file")
def _write_file(env: SkillExecutionEnv, args: dict) -> str:
    filename = args.get("filepath", "").strip()
    if not filename:
        return "Error: missing <filepath> parameter."
    path = env.safe_path(filename)
    try:
        path.write_text(args.get("content", ""), encoding="utf-8", newline="\r\n")
    except Exception as exc:
        return f"Write error: {exc}"
    return f"Saved to workspace: {path.name}"


@skill("embed_text")
def _embed_text(env: SkillExecutionEnv, args: dict) -> str:
    """Index ONE workspace file now, without a full sweep.

    This used to write a standalone `<name>_vector.json` that nothing ever
    read. It now writes into the same index semantic_search queries, so a
    freshly written file becomes findable immediately.
    """
    filename = args.get("filepath", "").strip()
    if not filename:
        return "Error: missing <filepath> parameter."
    path = env.safe_path(filename)
    if not path.exists():
        return f"Error: workspace file '{path.name}' not found."
    if not path.read_text(encoding="utf-8", errors="replace").strip():
        return f"Error: '{path.name}' is empty; nothing to embed."

    busy = _index_busy()
    if busy:
        return busy
    if not _INDEX_BUSY.acquire(blocking=False):
        return _index_busy() or "Refused: an index build is already running."
    try:
        try:
            idx = _open_index(env)
        except Exception as exc:
            return f"Index refused: {exc}"
        try:
            st = idx.build([path], lambda c: env.runtime.embed(EMBED_MODEL, c))
            info = idx.stats()
        except Exception as exc:
            return f"Embedding failed: {exc}"
        finally:
            idx.close()
    finally:
        _INDEX_BUSY.release()

    if st.errors:
        return "Embedding failed: " + "; ".join(st.errors)
    if st.skipped_unchanged and not st.embedded:
        return f"'{path.name}' is unchanged since it was last indexed; nothing to do."
    return (
        f"Indexed '{path.name}' with {EMBED_MODEL}: {st.chunks} passages.\n"
        f"  index now: {info['docs']} docs / {info['chunks']} chunks\n"
        f"  searchable via semantic_search."
    )


@skill("remember")
def _remember(env: SkillExecutionEnv, args: dict) -> str:
    """PROPOSE a memory entry. Staged, not landed.

    A seat may not write the record on its own. This stages the entry in
    memory/pending.jsonl stamped GENERATED; the operator sees it and lands it
    with /memory (LAW 6: the gate is final -- packets prepare, the operator
    lands). Nothing here reaches memory.md without a person.
    """
    body = (args.get("content") or "").strip()
    if not body:
        return "Error: missing <content> parameter -- nothing to remember."

    entry = _mem.Entry(
        title=(args.get("filepath") or "").strip(),
        body=body,
        provenance=_mem.GENERATED,
        session=env.session,
        run=env.run_ref,
    )
    n = _mem.stage(env.ground, entry)
    return (
        f"Proposed for memory: {entry.title!r}\n"
        f"  staged as GENERATED, NOT yet remembered.\n"
        f"  {n} entr{'y' if n == 1 else 'ies'} pending -- the operator lands "
        f"them with /memory."
    )


@skill("git_status")
def _git_status(env: SkillExecutionEnv, args: dict) -> str:
    g = _git.read(env.ground)
    # Sitting 38: the closer read counts from two moments and narrated a
    # "discrepancy" that three later turns kept investigating. The numbers
    # carry their moment so there is no before/after to invent.
    out = [g.stamp(),
           "(counts are AS OF THIS INSTANT; any commit already made is "
           "already reflected in them)"]
    if g.is_repo and g.subject:
        out.append(f"last commit: {g.subject}")
    if g.is_repo and g.dirty:
        out.append(f"{g.changed} changed, {g.untracked} untracked -- "
                   f"git_commit WILL include all {g.changed + g.untracked} of them "
                   f"(it runs `add -A` first). Untracked does not mean excluded.")
    out.append(f"remote operations: {'ALLOWED' if _git.remote_allowed() else 'OFF'}")
    # The seat you ask when you are stuck must be the seat that says why.
    blocked = _git.lock_state(env.ground) if g.is_repo else ""
    if blocked:
        out.append("")
        out.append(blocked)
    return "\n".join(out)


def _commit_subject(env: SkillExecutionEnv, args: dict) -> str:
    """Pick a commit subject a human will still understand in six months.

    Session 6 landed 98 files under the subject `git_commit` -- a 3b Router
    echoed the skill's own keyword into <content>. A message that only names
    the tool that wrote it carries no information at all, so a degenerate
    subject is discarded in favour of what the operator actually asked for.
    """
    known = set()
    lib = getattr(env, "skills_ref", None)
    if lib is not None:
        try:
            known = {k.lower() for k in lib.keywords()}
        except Exception:
            known = set()

    # SITTING 72: the previous subject was in the Router's results (git_status
    # prints `last commit: X`) and it copied X into the new one, so the
    # history became each commit quoting its predecessor -- with a STALE
    # description of different work. Same disease as sitting 61's lifted
    # citation: material from a tool result reused as this turn's fact.
    prior = ""
    try:
        prior = " ".join((_git.read(env.ground).subject or "").split()).lower()
    except Exception:
        prior = ""

    # A subject that describes the ACT of committing is true of every commit
    # ever made and tells a reader nothing. Sitting 6's guard caught a bare
    # tool name (`git_commit`); this one is a fluent sentence -- "Committing
    # 13 changed files locally" -- and sailed straight through it.
    _ACT = re.compile(
        r"(?i)^(?:please\s+)?(?:just\s+)?"
        r"(?:commit(?:ting|s|ed)?|saving|save|check(?:ing)?\s+in|"
        r"push(?:ing)?|updat(?:e|ing)|writ(?:e|ing))\b"
        # The determiner and the noun are BOTH optional, so each needs its
        # own leading space -- without it "saving work" fell through the
        # gap between them and passed as a real subject.
        r"(?:\s+(?:the|all|my|these|those|\d+))?"
        r"(?:\s+(?:changes?|files?|work|everything|it|them|repo|repository|"
        r"changed\s+files?))?"
        r"(?:\s+(?:locally|to\s+git|in\s+git|now))?\s*$")

    def degenerate(text: str) -> bool:
        t = " ".join((text or "").split()).strip().lower().strip("<>`\"'")
        if len(t) < 4:
            return True
        if t in known or t.replace(" ", "_") in known:
            return True
        if _ACT.match(t):
            return True                 # says what git does, not what changed
        # The previous subject, whole or embedded. A new commit that repeats
        # the last one is not a description of this work.
        if prior and len(prior) > 8 and prior in t:
            return True
        # A lone snake_case token is a tool name by shape, never a sentence.
        # Checked independently of the library: relying on skills_ref alone
        # made this whole guard a no-op wherever the env was built without it.
        return bool(re.fullmatch(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)+", t))

    # THE OPERATOR'S WORDS, OR GIT'S FACT. NEVER THE MODEL'S.
    #
    # SITTING 80, and the operator caught it from the transcripts: two
    # commits carried invented subjects.
    #
    #   0bb1b99  "add git repository initialization and basic ignore rules"
    #            ACTUAL DIFF: sessions/thread.jsonl, 4 insertions.
    #            Nothing was initialised. No ignore rule was touched.
    #   06ebdc1  "commit local changes without context - requires
    #            specifying what changed"  -- the Router's COMPLAINT about
    #            the request, committed as the message, over a 14-file diff
    #            that included us.py and the whole manifest.
    #
    # `args["content"]` was tried FIRST and both subjects came from there.
    # The three guards above all ask "is this string degenerate?" -- a
    # question about the STRING. None can ask "is it TRUE?", which is a
    # question about the DIFF, and the obvious arithmetic version of that
    # question DOES NOT WORK: matching subject words against changed paths
    # refuses "fix the greeting dispatch" over manjuel/intent.py exactly
    # as fast as it refuses the fabrications. Overlap was measured on real
    # subjects before this was written; it was zero for all of them. The
    # semantic truth of a commit message is not decidable here, and a guard
    # that pretends otherwise would discard good messages to catch bad ones.
    #
    # WHAT *IS* DECIDABLE: whether the operator gave a subject at all. Both
    # fabrications happened on a bare `git commit`, where the model had
    # nothing to anchor to and filled the space. So the model's <content>
    # is no longer a candidate. It is testimony about work it did not do
    # (LAW 5), and the fallback below is FACT read from git -- a worse
    # sentence and a true one.
    operator = " ".join((getattr(env, "objective", "") or "").split()).strip()
    # THE OPERATOR TYPES THE COMMAND AND THE SUBJECT IN ONE BREATH.
    # Sitting 81: `git commit " i ran a session, found a bug in the router.`
    # became the subject WHOLE -- command word, stray quote and all. The
    # `_ACT` guard is anchored `^...$`, so it catches a subject that is
    # ONLY an act-description and cannot see one used as a PREFIX. Strip
    # the invocation, keep the sentence; if nothing is left, it was a bare
    # command and falls through to git's own account below.
    #
    # NARROW ON PURPOSE, and the first draft was not. It stripped a leading
    # `commit` too, and THREE EXISTING STROKES went red -- "a real objective
    # is used when content is empty", "a commit with no message borrows the
    # objective", and one named "even one that merely mentions committing in
    # passing", which exists precisely to protect a subject that starts that
    # way. "commit the seam fix before the rack moves" is a real subject and
    # must survive whole. The defect was the INVOCATION form -- the literal
    # `git commit` with the operator's quote after it -- so that is all this
    # removes.
    # SITTING 85 (2026-09-04): `git commit -m parity ran, review the models
    # seats` landed as the subject `m parity ran, ...` -- the invocation
    # strip above took `git commit` and left the flag. And `update the git
    # status and git commit -m the router is working ...` landed WHOLE,
    # because the strip is anchored at the start. When the operator writes
    # `-m` / `--message`, what follows IS the subject, wherever it sits.
    m_flag = re.search(r"\bgit\s+commit\s+(?:-m|--message)\s*[=:]?\s*(.+)$",
                       operator, flags=re.IGNORECASE | re.DOTALL)
    if m_flag:
        operator = m_flag.group(1).strip()
    operator = re.sub(r"^(?:please\s+)?git\s+commit\b[\s:,-]*", "",
                      operator, flags=re.IGNORECASE).strip()
    operator = re.sub(r"^(?:-m|--message)\b\s*[=:]?\s*", "", operator).strip()
    operator = operator.strip('"“”\'`').strip()
    if operator and not degenerate(operator):
        return operator
    # No subject from the operator. Rather than a placeholder or a guess,
    # say what actually moved -- read from git, so it is fact.
    try:
        where = _git.areas(env.ground)
    except Exception:
        where = []
    if where:
        return "chain: " + ", ".join(where)
    return "chain commit (no subject given)"


@skill("git_commit")
def _git_commit(env: SkillExecutionEnv, args: dict) -> str:
    """Local, additive, recoverable -- so a seat may do it."""
    msg = _commit_subject(env, args)
    st = _git.read(env.ground)
    trailer = []
    if st.is_repo and st.dirty:
        trailer.append(f"{st.changed} changed, {st.untracked} untracked")
    if env.session:
        trailer.append(f"sitting: {env.session}")
    if trailer:
        msg = msg + "\n\n" + "\n".join(trailer)
    try:
        out = _git.commit(env.ground, msg)
    except _git.GitRefused as exc:
        return f"Refused: {exc}"
    # SAY WHICH DIRECTION THE COUNT POINTS. Sitting 81: the result carried
    # "1 changed, 0 untracked" -- meaning INCLUDED IN THIS COMMIT -- and the
    # Router read it forward: "the repository shows one file changed since
    # this commit was made." Both readings fit the words, and the wrong one
    # tells the operator his tree is dirty when it is clean. git_status
    # already carries its own disambiguation line ("counts are AS OF THIS
    # INSTANT"); this one had none, so the ambiguity was the tool's, not the
    # seat's.
    if st.is_repo and st.dirty:
        out += (f"\n\nThose {st.changed} changed and {st.untracked} untracked "
                f"were WHAT WENT IN, not what remains. This is the state "
                f"BEFORE the commit; run git_status for the state after.")
    return out


@skill("proved")
def _proved(env: SkillExecutionEnv, args: dict) -> str:
    """What the suites last proved, read from what they stamped.

    SITTING 81. The operator asked "have you run a full test suite on these
    skills?" and the chain answered out of its own head, because it had no
    way to read its own standing. 1,375 strokes test the ENGINE from
    outside; none of them let the ESTATE say what it has proved. A harness
    whose whole claim is an honest record could not answer the one question
    that record exists to answer.

    EVERY NUMBER HERE IS READ, NEVER REMEMBERED -- tests/last_run.json and
    last_run.md are written by the suites, run_history.jsonl by each run,
    and the manifest report by manjuel.us. No count is stored in a prompt
    or a doc (the operator's ruling): the suites grow with the system, so
    the only honest number is one a run produced.

    STALE IS REPORTED, NOT HIDDEN, and it is the whole point: a green tally
    from before the current code proves nothing about the current code.
    """
    import json as _json
    import time as _time
    ground = Path(env.ground)
    out: list[str] = []

    stamp = ground / "tests" / "last_run.json"
    if not stamp.exists():
        return ("No suite has ever stamped this ground. Nothing here has been "
                "proved on this machine.\n"
                "    python tests/test_manjuel.py && python tests/smoke_cli.py")
    try:
        book = _json.loads(stamp.read_text(encoding="utf-8") or "{}")
    except ValueError:
        return "tests/last_run.json is unreadable -- re-run the suites."
    if not book:
        return "No suite has ever stamped this ground."

    newest = max((r.get("at") or 0) for r in book.values())
    red = False
    for suite in sorted(book):
        r = book[suite]
        if r.get("state") == "running":
            out.append(f"  {suite:8} DID NOT FINISH -- a crash or a kill. "
                       f"Not a number anyone earned.")
            red = True
            continue
        mark = "GREEN" if r.get("green") else "RED"
        out.append(f"  {suite:8} {r.get('passed')}/{r.get('total')}  {mark}")
        red = red or not r.get("green")
        for name in (r.get("failures") or [])[:8]:
            out.append(f"             failed: {name}")

    # STALE: is anything on disk younger than the run that proved it?
    #
    # WHICH FILES COUNT IS boot.source_files' RULE, not a third copy of it.
    # This loop used to walk the code dirs itself with no exclusions, and
    # tests/last_run.md is a .md under tests/ that the SUITE WRITES as it
    # finishes -- so this said CHANGED SINCE after every green run and then
    # named `last_run.md` as the file that had changed, which is the stamp of
    # the very run it was reporting on. Three copies of one rule existed and
    # only tests/release.py had it right; a stroke now proves all three agree.
    from manjuel.boot import source_files as _source_files
    touched, newer = 0.0, []
    for f in _source_files(ground):
        try:
            m = f.stat().st_mtime
        except OSError:
            continue
        if m > touched:
            touched = m
        if m > newest:
            newer.append(f.name)
    ago = max(0.0, _time.time() - newest)
    when = (f"{int(ago // 60)} minutes ago" if ago < 5400 else
            f"{int(ago // 3600)} hours ago" if ago < 172800 else
            f"{int(ago // 86400)} days ago")
    head = [f"Last proved {when}.", ""]
    if touched > newest:
        head = [f"Last proved {when}, and the ground has CHANGED SINCE.",
                f"    {len(newer)} source file(s) are younger than that run "
                f"-- {', '.join(sorted(set(newer))[:4])}"
                + (" ..." if len(set(newer)) > 4 else ""),
                "    The tally below is honest about the PAST and says "
                "nothing about now. Re-run.", ""]
    elif red:
        head = [f"Last proved {when}. A suite is RED -- read "
                f"tests/last_run.md, not the scrollback.", ""]

    # the recent history, so a green now is not read as a green always
    hist = ground / "tests" / "run_history.jsonl"
    tail: list[str] = []
    if hist.exists():
        lines = [l for l in hist.read_text(encoding="utf-8").splitlines() if l.strip()]
        for l in lines[-4:]:
            try:
                h = _json.loads(l)
            except ValueError:
                continue
            state = h.get("state", "?")
            tail.append(f"  {h.get('suite','?'):8} {h.get('passed')}/"
                        f"{h.get('total')} {state}"
                        + ("" if h.get("green") else "  NOT GREEN"))

    # the manifest: does the declaration still match the disk?
    man = ""
    try:
        from . import us as _us
        findings = _us.reconcile(ground, env.registry, env.skills_ref)
        gaps = [f for f in findings if f.where != "the rack"]
        man = ("  the capability manifest agrees with the disk."
               if not gaps else
               f"  the manifest has {len(gaps)} finding(s) -- "
               f"run `python -m manjuel.us`.")
    except Exception as exc:
        man = f"  the manifest could not be checked: {type(exc).__name__}"

    body = head + ["THE SUITES"] + out
    if tail:
        body += ["", "RECENT RUNS (so a green now is not read as a green always)"] + tail
    body += ["", "THE MANIFEST", man,
             "", "WHAT THESE DO NOT COVER -- read REFUSALS.md for the whole list.",
             "  The suites prove the ENGINE offline with every model stubbed.",
             "  They cannot prove that a model writes a good answer, and",
             "  nothing here claims they do."]
    return "\n".join(body)


@skill("speak")
def _speak(env: SkillExecutionEnv, args: dict) -> str:
    text = (args.get("content") or "").strip()
    if not text:
        return "Error: missing <content> -- nothing to say."
    try:
        said = _voice.speak(text)
    except _voice.VoiceError as exc:
        return f"Cannot speak: {exc}"
    if not said:
        return "Nothing speakable in that text."
    # SITTING 70, THE OPERATOR: "speak ran, it just doesnt put the output
    # into that log, which is pretty concerning in and of itself."
    #
    # It is. The estate spoke 311 characters into his room and wrote down
    # only the number. Everything else the chain does leaves its words in
    # the record; the one output that reaches him THROUGH THE AIR left a
    # receipt. A transcript that cannot show what was said cannot be
    # reviewed, and LAW 10 is honest logs -- an audit of a spoken run had
    # nothing to audit.
    shown = " ".join(said.split())
    if len(shown) > 1500:
        shown = shown[:1500] + f"... ({len(said):,} characters in all)"
    return f"Spoke {len(said)} characters aloud. What was said:\n\n{shown}"


@skill("git_init")
def _git_init(env: SkillExecutionEnv, args: dict) -> str:
    try:
        return _git.init(env.ground)
    except _git.GitRefused as exc:
        return f"Refused: {exc}"


@skill("git_pull")
def _git_pull(env: SkillExecutionEnv, args: dict) -> str:
    try:
        return _git.pull(env.ground)
    except _git.GitRefused as exc:
        return f"Refused: {exc}"


@skill("git_push")
def _git_push(env: SkillExecutionEnv, args: dict) -> str:
    try:
        return _git.push(env.ground)
    except _git.GitRefused as exc:
        return f"Refused: {exc}"


@skill("git_cycle")
def _git_cycle(env: SkillExecutionEnv, args: dict) -> str:
    """The whole version-control turn: prove, status, commit, push, VERIFY.

    ZERO SEATS PAST THE GATE (his ruling 2026-09-10). The law gate stamps the
    objective, this runs, and what comes back is what the tools said. Nothing
    narrates a commit hash.

    IT READS THE SUITES' VERDICT; IT DOES NOT RUN THEM. Running them means
    spawning python inside the engine, and that is measured unsafe here: a
    first cut of the boot gate did it on 2026-09-10 and never returned -- two
    processes blocked for three minutes, no engine opened. So the same six
    file-readable checks the boot report asks are read here. buildmap, law and
    manifest need a child process or the rack; they are named as not asked, as
    boot names them.

    ONLY TWO OF THE SIX GATE A COMMIT: strokes and smoke, green AND fresh. The
    other four -- standup, SPEC against the CHANGELOG, DAYBOOK, HANDOFF -- are
    read and printed but do not refuse, because a commit does not cut a tag,
    close a session or end a day, and it must never need a live rack. They all
    came from tests/release.py, which is the RELEASE gate; lifting the whole
    set put tag ceremony on every commit and cost a live standup each time.

    AND IT VERIFIES THE PUSH. `git push` exiting 0 is not proof the remote
    moved, and the fault this closes is a push that never ran while everything
    downstream reported success. The local and remote heads are compared and
    both are printed.
    """
    message = (args.get("content") or "").strip()
    if not message:
        return ("Refused: git_cycle needs a commit message. The message is the "
                "one part of this a machine cannot supply -- everything else "
                "is read from the ground.")

    out = []

    # ---- 1. THE PROOFS, READ ------------------------------------------
    try:
        import importlib.util
        path = env.ground / "tests" / "release.py"
        spec = importlib.util.spec_from_file_location("_release_for_cycle", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        edited = mod.newest_edit(env.ground)
        checks = list(mod.suites(env.ground, edited))
        checks.append(mod.standup(env.ground, edited))
        checks.append(mod.spec(env.ground, None))
        checks.append(mod.daybook(env.ground))
        checks.append(mod.handoff(env.ground))
    except Exception as exc:
        return (f"Refused: the proofs could not be read "
                f"({type(exc).__name__}: {exc}). Nothing ships unproven.")

    # A COMMIT REFUSES ON WHAT A COMMIT CAN BREAK, AND ONLY THAT.
    #
    # All six came from tests/release.py, which is THE RELEASE GATE -- it gates
    # a TAG. One of them wants a LIVE standup stamped after the newest edit, so
    # lifting the whole set put tag-level ceremony on every commit: any code
    # edit staled it, and shipping meant nine cases of live model work on a
    # single rack, again and again. The operator, watching it: "the live
    # standup is the issue". It never took the twenty minutes it looked like --
    # every nine-case run that morning finished in 62 to 135 seconds -- but he
    # was right that it had no business gating a commit at all.
    #
    # THE LINE IS WHAT A COMMIT INVALIDATES. A commit changes code, so the
    # suites must be green AND fresh: those two REFUSE. A commit does not close
    # a session (DAYBOOK), does not end a day (HANDOFF), does not cut a tag
    # (SPEC against the CHANGELOG) and does not need a live rack (standup).
    # Those four are still READ and still PRINTED -- they cost nothing, and
    # they are the only warning he gets before a tag -- but they no longer stop
    # a commit. Trading one bad gate for a blind one would be no better.
    #
    # tests/release.py is UNCHANGED. The tag still wants all nine.
    GATES = ("strokes", "smoke")
    bad = [c for c in checks if not c.ok and c.name in GATES]
    noted = [c for c in checks if not c.ok and c.name not in GATES]
    out.append(f"THE PROOFS  {sum(1 for c in checks if c.ok)}/{len(checks)} green "
               f"(strokes and smoke gate a commit; the rest are read and "
               f"reported. buildmap, law and manifest need a child process or "
               f"the rack and are not asked from inside the engine)")
    for c in checks:
        mark = "ok     " if c.ok else ("REFUSED" if c.name in GATES else "note   ")
        out.append(f"  {mark} {c.name:9} {c.why}")
    if bad:
        return ("\n".join(out) + "\n\nREFUSED: " + ", ".join(c.name for c in bad)
                + ". Nothing was committed and nothing was pushed.")
    if noted:
        out.append("  (" + ", ".join(c.name for c in noted) + " are the TAG's to "
                   "answer, not this commit's -- run `python tests/release.py "
                   "--check` before you cut one.)")

    # ---- 2. WHAT IS ABOUT TO BE COMMITTED ------------------------------
    st = _git.read(env.ground)
    if not st.is_repo:
        return "\n".join(out) + "\n\nRefused: this ground is not a git repository."
    out.append("")
    out.append(f"THE GROUND  {st.stamp()}")
    if not st.dirty:
        return ("\n".join(out) + "\n\nNothing to commit; the ground is clean. "
                "No commit, no push.")

    # ---- 3. THE COMMIT --------------------------------------------------
    before = st.head or ""
    try:
        out.append("")
        out.append("THE COMMIT")
        out.append("  " + _git.commit(env.ground, message).replace("\n", "\n  "))
    except _git.GitRefused as exc:
        return "\n".join(out) + f"\n\nRefused at the commit: {exc}"

    after = _git.read(env.ground)
    if (after.head or "") == before:
        return ("\n".join(out) + "\n\nRefused: the head did not move, so no "
                "commit was made. Nothing was pushed.")

    # ---- 4. THE PUSH ----------------------------------------------------
    try:
        out.append("")
        out.append("THE PUSH")
        out.append("  " + _git.push(env.ground).replace("\n", "\n  "))
    except _git.GitRefused as exc:
        return ("\n".join(out) + f"\n\nCommitted at {after.head}, NOT PUSHED: "
                f"{exc}")

    # ---- 5. VERIFY IT ACTUALLY LANDED -----------------------------------
    # A push exiting 0 is not proof the remote moved, and a report of success
    # that nobody checked is the fault this skill exists to end.
    local, remote, why = _git.head_and_remote(env.ground)
    out.append("")
    out.append("THE PROOF IT LANDED")
    out.append(f"  local  {local or '?'}")
    out.append(f"  remote {remote or '?'}" + (f"   ({why})" if why else ""))
    if not remote:
        out.append("  ** the remote head could not be read; the push is UNVERIFIED **")
    elif local != remote:
        out.append("  ** THEY DISAGREE: the push did not land. **")
    else:
        out.append("  they agree: the work is on the remote.")
    return "\n".join(out)


@skill("linear_regression")
def _linear_regression(env: SkillExecutionEnv, args: dict) -> str:
    """Ordinary least squares over numbers found in the text.

    The numbers are SCANNED out with a regex and fed to mathkit. They are never
    interpolated into source and executed -- a handler that builds a script
    from model output and runs it is a code-injection hole, not a calculator
    (LAW 5: testimony is never executed as instruction).
    """
    raw = (args.get("content") or "").strip()
    if not raw:
        return "Error: missing <content> -- give the numbers to fit."

    try:
        ys = mathkit.parse_numbers(raw)
        fit = mathkit.linear_regression(ys)
    except mathkit.MathError as exc:
        return f"Cannot fit: {exc}"

    n = fit.n
    nxt = [fit.predict(n), fit.predict(n + 1), fit.predict(n + 2)]
    trend = "rising" if fit.slope > 0 else ("falling" if fit.slope < 0 else "flat")

    strength = (
        "the line explains the points well" if fit.r2 >= 0.9 else
        "the line explains the points loosely" if fit.r2 >= 0.5 else
        "the points do NOT lie on a line -- treat any forecast as weak"
    )
    return "\n".join([
        f"Fit over {n} points: {fit}",
        f"  trend: {trend} by {abs(fit.slope):.4g} per step",
        f"  R2 {fit.r2:.4f} -- {strength}",
        "  next three steps: " + ", ".join(f"{v:.4g}" for v in nxt),
        f"  (x defaults to 0..{n-1}; a forecast is extrapolation, not evidence)",
    ])


@skill("statistics")
def _statistics(env: SkillExecutionEnv, args: dict) -> str:
    """Descriptive statistics over numbers found in the text."""
    raw = (args.get("content") or "").strip()
    if not raw:
        return "Error: missing <content> -- give the numbers."
    try:
        xs = mathkit.parse_numbers(raw)
        if len(xs) < 2:
            return f"Only {len(xs)} number found; need at least 2."
        return "\n".join([
            f"n        {len(xs)}",
            f"mean     {mathkit.mean(xs):.6g}",
            f"median   {mathkit.median(xs):.6g}",
            f"min/max  {min(xs):.6g} / {max(xs):.6g}",
            f"stdev    {mathkit.stdev(xs, ddof=1):.6g}   (sample, ddof=1)",
            f"variance {mathkit.variance(xs, ddof=1):.6g}   (sample, ddof=1)",
        ])
    except mathkit.MathError as exc:
        return f"Cannot compute: {exc}"


# =====================================================================
# The rack: what is on the shelf, what is in VRAM, and moving between them
# =====================================================================

RACK_PULL_ENV = "MANJUEL_RACK_PULL"


def _pipeline_models(env: SkillExecutionEnv) -> set[str]:
    """Tags this ground declares -- seats, prompt skills, and the embedder."""
    return set(env.registry.models()) | {EMBED_MODEL}


@skill("rack_list")
def _rack_list(env: SkillExecutionEnv, args: dict) -> str:
    """Read-only: the shelf and the card."""
    try:
        # refresh=True: a model pulled in another terminal must appear here
        # without restarting the REPL.
        installed = env.runtime.installed_models(refresh=True)
        sizes = _vram.installed_sizes(env.runtime)
        resident = dict(env.runtime.resident())
    except Exception as exc:
        return f"Rack unreachable: {exc}"

    ours = _pipeline_models(env)
    lines = [f"{len(installed)} models installed, {len(resident)} loaded in VRAM:"]
    for tag in sorted(installed):
        size = _vram.gb(sizes[tag]) if sizes.get(tag) else "?"
        state = "LOADED " if tag in resident else "       "
        mine = "declared here" if tag in ours else ""
        lines.append(f"  {state} {tag:<30} {size:>7}  {mine}")

    foreign = [t for t in resident if t not in ours]
    if foreign:
        lines.append("")
        lines.append(f"In VRAM but NOT declared here: {', '.join(foreign)}")
        lines.append("Another client is using the card. Do not unload these.")

    # What waking each SEAT costs RIGHT NOW. The Reasoner rides a model this
    # ground does not keep warm itself -- when the other client leaves, its
    # "free" seat silently becomes a 6.6GB cold load. That change of price
    # must be visible, not discovered mid-question.
    lines.append("")
    lines.append("Seats, priced as the card stands:")
    seen: set[str] = set()
    for agent in env.registry.all():
        if agent.model in seen:
            continue
        seen.add(agent.model)
        who = [a.name for a in env.registry.all() if a.model == agent.model]
        if agent.model in resident:
            price = "warm — answers at once"
        else:
            gb = _vram.gb(sizes[agent.model]) if sizes.get(agent.model) else "?"
            price = f"COLD — waking loads {gb}"
        lines.append(f"  {', '.join(who)}: {agent.model}  ({price})")

    used = sum(b for b in resident.values() if b)
    budget = _vram.budget_bytes()
    lines.append("")
    lines.append(f"Card: {_vram.gb(used)} of ~{_vram.gb(budget)} in use, "
                 f"~{_vram.gb(max(0, budget - used))} headroom.")
    return "\n".join(lines)


@skill("rack_report")
def _rack_report(env: SkillExecutionEnv, args: dict) -> str:
    """The rack's OBSERVED state. FACTS ONLY unless a judgement is asked for.

    The facts are collected in Python -- a model is never asked what is
    installed, only what the inventory means. That keeps the numbers real.

    AND A READING IS ONLY TAKEN WHEN ONE IS ASKED FOR (the operator,
    2026-09-09: "4.3 facts only"). Before this, the Quartermaster was woken on
    every call and its prose appended beneath the numbers; the join was
    labelled after sitting 59, but the Router still summarised THE READING
    rather than the facts, three times in sitting 85. A reading nobody asked
    for is one the Router will summarise however it is fenced -- so the fix is
    the default, not a better label.
    """
    facts = _rack_list(env, {})
    if facts.startswith("Rack unreachable"):
        return facts

    declared = sorted(_pipeline_models(env))
    try:
        missing = env.runtime.missing(set(declared))
    except Exception:
        missing = []
    budget = _vram.gb(_vram.budget_bytes())

    question = (args.get("content") or "What is the state of the rack?").strip()
    inventory = (
        f"{facts}\n\n"
        f"Declared by this ground: {', '.join(declared)}\n"
        f"Declared but NOT installed: {', '.join(missing) or 'none'}\n"
        f"VRAM budget: {budget}\n"
        f"Question: {question}"
    )

    if not env.registry.has("Quartermaster"):
        return inventory

    # FACTS ONLY UNLESS A JUDGEMENT IS ASKED FOR. The test lives in intent.py
    # with the estate's other question shapes rather than as a second copy
    # here, and it answers False by default -- so a question that does not
    # plainly ask to be advised gets the numbers, which are never wrong.
    # The line below is not decoration: it tells whatever reads this that
    # there is no opinion in it, which is exactly what the Router got wrong.
    from .intent import asks_for_a_judgement
    if not asks_for_a_judgement(question):
        return (f"{inventory}\n\n"
                f"(FACTS ONLY -- no seat was asked to read them. Ask for a "
                f"judgement in the question and the Quartermaster reads the "
                f"same inventory beside it.)")

    # 2026-09-02, sitting 59: this returned ONLY the Quartermaster's prose, and
    # the transcript labelled it `Tool executed: rack_report / Result:` -- so a
    # model's retyping of the inventory reached the Router wearing a machine
    # label. It had renamed qwen3.5:4b to qwen2.5-coder:4b and qwen3.5:9b to
    # qwen2.5-coder:9b (sizes preserved, tags invented), dropped ten installed
    # models including the one it was running on, put phi4:latest in VRAM when
    # it was not, and invented a VRAM total. The docstring above promises "a
    # model is never asked what is installed" and the return path broke it.
    #
    # LAW 5: testimony is never fact. The seat's reading is worth having, but
    # it goes BESIDE the observed numbers, never instead of them, and it is
    # labelled as what it is. Anything downstream can now check it.
    try:
        reading = env.runtime.chat(env.registry.get("Quartermaster"), inventory)
    except Exception as exc:
        return f"{inventory}\n\n(Quartermaster unavailable: {exc})"

    return (f"{inventory}\n\n"
            f"--- OBSERVED ABOVE (collected in python). "
            f"BELOW IS THE QUARTERMASTER'S READING (a seat's words, LAW 5) ---\n\n"
            f"{(reading or '').strip() or '(the Quartermaster returned nothing)'}")


@skill("rack_sync")
def _rack_sync(env: SkillExecutionEnv, args: dict) -> str:
    """Pull a current list from Ollama and rewrite rack.md.

    The written rack is DERIVED -- regenerated whole rather than appended to,
    because Ollama is the record and this is the fold of it.
    """
    try:
        survey = _rack.survey(env.runtime, env.registry, env.skills_ref, EMBED_MODEL)
    except Exception as exc:
        return f"Could not survey the rack: {exc}"

    path = env.ground / _rack.RACK_FILE
    before = path.read_text(encoding="utf-8") if path.exists() else ""
    changes = _rack.diff(before, survey)
    _rack.write(env.ground, survey)

    out = [f"Rack synced to {_rack.RACK_FILE} at {survey['taken']}.",
           f"  {len(survey['installed'])} installed · "
           f"{len(survey['resident'])} in VRAM · "
           f"{len(survey['declared'])} declared here"]
    if survey["missing"]:
        out.append(f"  ** declared but MISSING: {', '.join(survey['missing'])} — "
                   f"those seats fail when called **")
    if survey["unused"]:
        total = sum(survey["sizes"].get(m, 0) for m in survey["unused"])
        out.append(f"  installed but unused: {len(survey['unused'])} models, "
                   f"about {_vram.gb(total)}")
    out.extend(f"  {c}" for c in changes)
    if not changes and before:
        out.append("  nothing changed since the last sync")
    out.append("  run index_ground to make it searchable")
    return "\n".join(out)


@skill("rack_load")
def _rack_load(env: SkillExecutionEnv, args: dict) -> str:
    """Bring a model into VRAM so the next call does not pay the load."""
    tag = (args.get("content") or args.get("filepath") or "").strip()
    if not tag:
        return "Error: name the model to load, e.g. <content>qwen3.5:4b</content>"
    try:
        if tag not in env.runtime.installed_models():
            return f"'{tag}' is not installed. rack_pull would fetch it."
        if tag in dict(env.runtime.resident()):
            return f"'{tag}' is already loaded."
        return f"Loaded '{tag}' in {env.runtime.warm(tag):.1f}s."
    except Exception as exc:
        return f"Load failed: {exc}"


@skill("rack_unload")
def _rack_unload(env: SkillExecutionEnv, args: dict) -> str:
    """Free VRAM. REFUSES a model this ground does not declare, because it
    would then belong to another client and evicting it charges them the
    reload -- not a cost a seat gets to spend on someone else's behalf."""
    tag = (args.get("content") or args.get("filepath") or "").strip()
    if not tag:
        return "Error: name the model to unload."
    try:
        resident = dict(env.runtime.resident())
        if tag not in resident:
            return f"'{tag}' is not loaded; nothing to free."
        if tag not in _pipeline_models(env):
            return (f"Refused: '{tag}' is loaded but is NOT declared in this "
                    f"ground, so it belongs to another client. Unloading it "
                    f"would cost them a reload. The operator can do it by hand.")
        freed = _vram.gb(resident[tag])
        env.runtime.unload(tag)
        return f"Unloaded '{tag}', freeing about {freed}."
    except Exception as exc:
        return f"Unload failed: {exc}"


@skill("rack_pull")
def _rack_pull(env: SkillExecutionEnv, args: dict) -> str:
    """Download a model. Crosses the wall and can move gigabytes, so it is
    OFF unless the operator turns it on."""
    tag = (args.get("content") or args.get("filepath") or "").strip()
    if not tag:
        return "Error: name the model to pull."
    if os.environ.get(RACK_PULL_ENV, "").strip() not in ("1", "true", "yes", "on"):
        return (f"Refused: pulling reaches the network and can move gigabytes "
                f"onto this machine. That is the operator's call. Set "
                f"{RACK_PULL_ENV}=1 to allow it, or run: ollama pull {tag}")
    try:
        if tag in env.runtime.installed_models(refresh=True):
            return f"'{tag}' is already installed."
        return f"Pulled '{tag}': {env.runtime.pull(tag)}"
    except Exception as exc:
        return f"Pull failed: {exc}"


# ONE BUILD AT A TIME (sitting 94, 2026-09-08). `_run_bounded` cannot kill
# a thread, so an index_ground refused at the 300s bound is STILL RUNNING
# behind the refusal; the operator asked again eight minutes later, both
# threads wrote one vectors.db, and the second failed in 39s with `UNIQUE
# constraint failed: docs.path` -- which the seat log then called
# "finished". This lock is held for the life of the build, refusal or not,
# so a second call is refused by name while the first is alive. Module-
# level on purpose: the two handlers that write the index share it, and a
# lock per env would be two locks on one file.
_INDEX_BUSY = threading.Lock()


def _index_busy() -> str:
    """The refusal for a second build while one is running, or ""."""
    if _INDEX_BUSY.locked():
        return ("Refused: an index build is still running behind an earlier "
                "call (a build refused at the skill bound keeps working; "
                "LAW 7 bounds the wait, not the work). Two builds on one "
                "vectors.db corrupt both (sitting 94). Wait for it, or "
                "restart the REPL to end it.")
    return ""


def _open_index(env: SkillExecutionEnv, rebuild: bool = False) -> VectorIndex:
    path = env.ground / "index" / "vectors.db"
    if rebuild:
        # The index is DISPOSABLE BY DESIGN -- that is the whole reason a
        # changed embedder is safe to survive. Take the WAL and shm files
        # with it, or sqlite reopens the old content behind a new header.
        for p in (path, Path(str(path) + "-wal"), Path(str(path) + "-shm")):
            try:
                p.unlink()
            except FileNotFoundError:
                pass                      # absent: nothing to discard
            except OSError as exc:
                # HELD. Sitting 94: this was `pass`, the old file stayed
                # under a new handle, and the "rebuild" wrote into the
                # index it was meant to discard. A rebuild that cannot
                # discard is refused, not pretended.
                raise RuntimeError(
                    f"rebuild refused: {p.name} is held open by another "
                    f"process or a build still running ({exc}); nothing was "
                    f"discarded and nothing was written") from exc
    return VectorIndex(path, EMBED_MODEL)


def _wants_rebuild(env: SkillExecutionEnv, args: dict) -> bool:
    """Did the operator ask for the index to be built from scratch?

    Sitting 66, and this is the fault worth naming: the index refused --
    correctly -- because it had been built with a different embedder, and
    its refusal said "Rebuild with index_ground <rebuild>". THE HANDLER DID
    NOT READ ITS ARGUMENTS AT ALL. The error named a cure that did not
    exist, the operator typed the magic word twice, and nothing could have
    worked. An error message is a promise; this one could not be kept.

    The word is taken from the parameters OR from the objective, by the
    standing rule that the objective is the payload (sittings 26 and 39):
    the operator typed `index_ground rebuild` and meant it."""
    said = " ".join([
        str(args.get("content") or ""), str(args.get("filepath") or ""),
        str(getattr(env, "objective", "") or ""),
    ]).lower()
    return any(w in said for w in ("rebuild", "reindex", "from scratch",
                                   "start over", "fresh"))


@skill("index_ground")
def _index_ground(env: SkillExecutionEnv, args: dict) -> str:
    """Build or refresh the semantic index over the configured roots."""
    rebuild = _wants_rebuild(env, args)
    roots = load_roots(env.ground / "index_roots.txt", env.default_roots, base=env.ground)
    live = [r for r in roots if r.exists()]
    missing = [r for r in roots if not r.exists()]

    if not live:
        return (
            "Error: no readable roots. Listed: "
            + ", ".join(str(r) for r in roots)
            + "\nEdit index_roots.txt (one path per line)."
        )

    busy = _index_busy()
    if busy:
        return busy
    if not _INDEX_BUSY.acquire(blocking=False):
        return _index_busy() or "Refused: an index build is already running."
    try:
        return _index_ground_locked(env, rebuild, live, missing)
    finally:
        _INDEX_BUSY.release()


def _index_ground_locked(env: SkillExecutionEnv, rebuild: bool, live: list,
                         missing: list) -> str:
    """The build itself; the caller holds _INDEX_BUSY for its whole life."""
    try:
        idx = _open_index(env, rebuild)
    except Exception as exc:
        return f"Index refused: {exc}"

    # SITTING 81: this banner was appended to `lines` -- which is then
    # handed to idx.build() as its REPORT CALLBACK and never read again.
    # Collected and discarded, so the result never said which mode ran, and
    # both seats guessed: the Router reported "built (not rebuilt) ... a
    # normal refresh operation" and the closing Steward said "this rebuild
    # is not a full rebuild; it's a refresh that discards the old index
    # vectors" -- a sentence that contradicts itself. Discarding the old
    # vectors IS the rebuild. The operator was told his eviction had not
    # happened while it had.
    #
    # A tool that does not name what it did leaves the seat to invent an
    # account of it. Same fault as git_commit's count (sitting 80).
    banner = ("Rebuilt from scratch: the old vectors were discarded, "
              "not merged. Vectors from two embedders are not "
              "comparable, so a partial rebuild would be worse than "
              "none.") if rebuild else ""
    lines: list[str] = []
    try:
        st = idx.build(live, lambda c: env.runtime.embed(EMBED_MODEL, c), lines.append)
        info = idx.stats()
    except Exception as exc:
        return f"Indexing failed: {exc}"
    finally:
        idx.close()

    # THE MODE, IN THE FIRST LINE, as a word and not an inference.
    out = [
        f"{'REBUILT' if rebuild else 'Refreshed'} with {EMBED_MODEL}.",
        f"  roots:     {', '.join(str(r) for r in live)}",
        f"  scanned:   {st.scanned} files",
        f"  embedded:  {st.embedded} changed  ({st.chunks} chunks)",
        f"  unchanged: {st.skipped_unchanged} skipped by hash",
    ]
    if st.skipped_big:
        out.append(f"  oversized: {st.skipped_big} skipped")
    if missing:
        out.append(f"  absent:    {', '.join(str(r) for r in missing)}")
    out.append(f"  index now: {info['docs']} docs / {info['chunks']} chunks")
    if st.errors:
        out.append("  errors:")
        out.extend(f"    - {e}" for e in st.errors[:10])
    if banner:
        # `unchanged: 0 skipped by hash` is the SIGNATURE of a rebuild and
        # was read as the opposite. Say it in words beside the numbers.
        out.append("")
        out.append(banner)
        out.append("  (that is why `unchanged` is 0: there was no old index "
                   "left to skip against.)")
    return "\n".join(out)


def _age_of(path) -> str:
    """How old a file is, in the units a person thinks in.

    "The record" was one undifferentiated past; a passage from two hours ago
    and one from last month read identically. Age on every hit lets a seat --
    and the operator -- weigh recency instead of guessing at it.
    """
    import time as _t
    try:
        sec = _t.time() - Path(path).stat().st_mtime
    except OSError:
        return ""
    if sec < 90:
        return "just now"
    if sec < 5400:
        return f"{int(sec // 60)}m ago"
    if sec < 129600:
        return f"{sec / 3600:.0f}h ago"
    return f"{sec / 86400:.0f}d ago"


@skill("semantic_search")
def _semantic_search(env: SkillExecutionEnv, args: dict) -> str:
    return _search_scoped(env, args, "sources")


@skill("search_transcripts")
def _search_transcripts(env: SkillExecutionEnv, args: dict) -> str:
    """What was SAID on a past run, as opposed to what the estate holds."""
    # THE WHOLE RECORD, not only logs/. The ledgers -- CHANGELOG, HANDOFF,
    # SEAT_LOG, DAYBOOK, TASKS, REFUSALS, memory, BUILDMAP -- are dated history
    # that happens not to live under logs/, and they left `sources` on
    # 2026-09-10 for the same reason transcripts did: a CHANGELOG entry ABOUT
    # the covenant is not the covenant. They have to be reachable somewhere or
    # the split hides them, and this is the reach that already means "what
    # happened".
    #
    # THE KEYWORD DOES NOT CHANGE. `search_transcripts` is now narrower than
    # what it does, and renaming it would churn the shortlist, the us record
    # and every transcript that names it -- for a word. The DESCRIPTION says
    # what it actually covers, which is the part a caller reads.
    return _search_scoped(env, args, "record")


def _search_scoped(env: SkillExecutionEnv, args: dict, scope: str) -> str:
    query = (args.get("content") or "").strip()
    if not query:
        # Sitting 26: the Router called search with no query, the error came
        # back, and a seat invented "a name from various Asian cultures" over
        # it -- while agents/manjuel.md sat in the index. The objective IS the
        # query, same ruling as git_commit borrowing its message.
        query = (env.objective or "").strip()
    if not query:
        return "Error: no query given and no objective to borrow one from."

    try:
        idx = _open_index(env)
    except Exception as exc:
        return f"Index refused: {exc}"

    try:
        info = idx.stats()
        if not info["chunks"]:
            return "Error: the index is empty. Run index_ground first."

        try:
            qvec = env.runtime.embed(EMBED_MODEL, query)
        except Exception as exc:
            return f"Query embedding failed: {exc}"

        hits = idx.search(qvec, limit=8, per_doc=2, scope=scope)
    finally:
        idx.close()

    # Doctrine outranks plumbing. Sitting 28 asked "what is the covenant"
    # and got the alias table in intent.py -- source code that mentions the
    # covenant beat the covenant itself on lexical overlap. At comparable
    # similarity, the founding record and the operator's rulings come first.
    import time as _t

    def _rank(h):
        path = str(h["path"]).replace("\\", "/")
        bonus = 0.0
        if "/foundation/" in path or path.endswith("memory.md"):
            bonus = 0.06
        elif "/us/" in path or "/agents/" in path:
            bonus = 0.03
        elif "/manjuel/" in path or "/tests/" in path:
            bonus = -0.03
        # RECENCY, added 2026-09-02. Age was DISPLAYED on every hit and
        # counted for nothing in the ordering, so a fortnight-old log
        # competed evenly with this morning's. Small on purpose: at most
        # +0.04, decaying to nothing over a month, so it BREAKS TIES and
        # never outvotes meaning. Recency as a proxy for relevance is the
        # mistake the dialogue selector was built to escape (context.py);
        # this is a thumb on the scale, not a second opinion.
        #
        # The doctrine is exempt: the founding documents are old BY
        # NATURE, and decaying them would bury the ground's own law under
        # whatever ran this morning.
        if "/foundation/" not in path:
            try:
                days = (_t.time() - Path(h["path"]).stat().st_mtime) / 86400
                bonus += RECENCY_WEIGHT * max(0.0, 1.0 - days / 30.0)
            except (OSError, KeyError):
                pass
        return h["score"] + bonus

    hits = sorted(hits, key=_rank, reverse=True)[:5]

    if not hits:
        return f"No passages matched {query!r}."

    # Sitting 26: passages from an old run transcript were narrated as if
    # they were happening NOW -- "the coder ran but produced nothing" was a
    # two-hour-old log, read aloud as news. The results say what they are.
    lines = [
        f"Semantic results for {query!r}",
        f"({info['docs']} docs / {info['chunks']} chunks, {EMBED_MODEL})",
        "These are passages from the WRITTEN RECORD -- past runs, notes and "
        "declarations. They describe what happened THEN, not what is "
        "happening in this run.",
        "-" * 58,
    ]
    for i, h in enumerate(hits, 1):
        try:
            shown = Path(h["path"]).relative_to(env.ground)
        except ValueError:
            shown = Path(h["path"])
        snippet = " ".join(h["text"].split())
        if len(snippet) > 240:
            snippet = snippet[:240] + "..."
        if h.get("label"):
            where = f"\"{h['label']}\""
            if h.get("session"):
                where += f"  session {h['session']}"
            if h.get("stamp"):
                where += f"  {h['stamp'][:16]}"
        else:
            where = f"chunk {h['ord']} @ {h['start']}"
        age = _age_of(h["path"])
        stamp = f"  written {age}" if age else ""
        lines.append(f"{i}. {shown}  [{where}]{stamp}  cosine {h['score']:.4f}")
        lines.append(f"   {snippet}")
    return "\n".join(lines)


@skill("deep_research")
def _deep_research(env: SkillExecutionEnv, args: dict) -> str:
    """Delegate to the Deep Researcher persona defined in agents.md.

    Previously this hardcoded a model tag and an inline prompt, bypassing
    agents.md entirely.
    """
    payload = (args.get("content") or args.get("filepath") or "").strip()
    if not payload:
        # The standing ruling: the objective IS the payload. Sitting 39
        # starved this skill five times in a row.
        payload = (getattr(env, "objective", "") or "").strip()
    if not payload:
        return "Error: deep_research needs a <content> payload."

    if not env.registry.has("Deep Researcher"):
        return "Error: no 'Deep Researcher' agent defined in agents.md."

    agent = env.registry.get("Deep Researcher")
    try:
        out = env.runtime.chat(agent, f"Investigate the following in depth:\n\n{payload}")
    except Exception as exc:
        return f"Deep research failed: {exc}"
    return f"Deep research findings:\n{out}"


# =====================================================================
# MCP — the one skill that speaks to another server
# =====================================================================
#
# THE ESTATE IS LOCAL, AND THIS IS THE FIRST SKILL THAT COULD BREAK THAT.
# Thirty-four handlers stood here before this one and not one of them opened a
# socket; the only thing this ground talked to was Ollama on loopback. So the
# wall is written here, in code, and not left to a dial or to good intentions:
# a declared address that is not loopback is REFUSED BY NAME, and there is no
# flag that turns that off. RULE 4 -- "if it needs someone else's server, it
# does not go in" -- is the whole reason this skill can exist at all.
#
# A SERVER IS A DIAL, NOT A NEW FILE. `MANJUEL_MCP_<NAME>` in .env names one,
# which is the mechanism every other wall in this estate already uses
# (MANJUEL_GIT_REMOTE, MANJUEL_RACK_PULL). No new folder, no registry file, no
# second place to forget -- RULE 8.
#
# AND THE ADDRESS IS NEVER SPOKEN. It comes out of .env, and .env is never
# printed (RULE 7). Every line this skill returns names the SERVER, never the
# URL behind it, including the refusals.
#
# WHAT THIS IS FOR. atlas serves 78 tools over MCP and the engine could not
# reach one of them; the door pointed outward only. This turns any local MCP
# server into a skill -- which means it inherits the law gate, the dedup, the
# recompose, the clearances and the transcript, for free, because it IS a
# skill. Nothing new had to be taught to the Router.

_MCP_DIAL = "MANJUEL_MCP_"
# Bounded, like everything else (ESTATE LAW 7). Short enough that a wedged
# server is a refusal a seat can read rather than a turn that dies on the
# skill timeout with nothing to say.
_MCP_TIMEOUT = 60
_MCP_LOOPBACK = {"127.0.0.1", "localhost", "::1", "[::1]"}


def _mcp_servers() -> dict:
    """{name: url} for every server this ground declares. Names only ever
    leave this function paired with the url for the caller that must dial it;
    nothing that returns to a seat carries the url."""
    out = {}
    for k, v in os.environ.items():
        if k.startswith(_MCP_DIAL) and v.strip():
            out[k[len(_MCP_DIAL):].strip().lower()] = v.strip()
    return out


def _mcp_rpc(url: str, method: str, params: dict) -> tuple[dict | None, str]:
    """One JSON-RPC call. Returns (result, error-in-plain-words).

    stdlib only: urllib, because a dependency for one POST is a dependency the
    whole estate then carries (LAW 6, and the atlas law beside it).
    """
    import json as _json
    import urllib.error
    import urllib.request
    body = _json.dumps({"jsonrpc": "2.0", "id": 1,
                        "method": method, "params": params}).encode("utf-8")
    req = urllib.request.Request(url, body, {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=_MCP_TIMEOUT) as r:
            row = _json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.URLError as exc:
        return None, f"it did not answer ({exc.reason})"
    except TimeoutError:
        return None, f"it did not answer inside {_MCP_TIMEOUT}s"
    except ValueError:
        return None, "it answered with something that is not JSON"
    except Exception as exc:                     # the transport died
        return None, f"{type(exc).__name__}: {exc}"
    if isinstance(row, dict) and row.get("error"):
        err = row["error"]
        return None, f"it refused: {err.get('message') or err}"
    return (row or {}).get("result") or {}, ""


def _mcp_text(result: dict) -> str:
    """An MCP result's own words. The content blocks are the answer; the
    envelope is not."""
    parts = []
    for block in (result.get("content") or []):
        if isinstance(block, dict) and block.get("text"):
            parts.append(str(block["text"]))
    return "\n".join(parts).strip()


@skill("mcp_call")
def _mcp_call(env: SkillExecutionEnv, args: dict) -> str:
    """Call one tool on a local MCP server this ground declares.

    Every way this can fail names what would answer it, because a seat that
    gets "refused" and nothing else will invent the rest.
    """
    import json as _json
    from urllib.parse import urlparse

    servers = _mcp_servers()
    name = (args.get("server") or "").strip().strip("'\"`").lower()

    # NO SERVER NAMED: say which are declared. Names only -- never the address.
    if not name:
        if not servers:
            return ("Refused: this ground declares no MCP server. Declare one "
                    "as a dial in .env -- MANJUEL_MCP_<NAME>=<loopback url> -- "
                    "and it becomes callable by <NAME>. The address must be "
                    "loopback; the estate is local.")
        return ("The MCP servers this ground declares: "
                + ", ".join(sorted(servers)) + ".\nName one as <server>, and "
                "leave <tool> blank to see what it carries.")

    if name not in servers:
        return (f"Refused: this ground declares no MCP server called "
                f"{name!r}. It declares: "
                + (", ".join(sorted(servers)) if servers else "none")
                + f". A server is declared as {_MCP_DIAL}{name.upper()} in .env.")

    url = servers[name]

    # THE WALL. RULE 4, enforced here rather than trusted to whoever wrote the
    # dial. A hostname that is not loopback does not get dialled, and the
    # refusal does not repeat the address back (RULE 7).
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        host = ""
    if host not in _MCP_LOOPBACK:
        return (f"Refused: the address declared for {name!r} is not on this "
                f"machine, and the estate is local (RULE 4). Only loopback is "
                f"dialled: {', '.join(sorted(_MCP_LOOPBACK))}. Nothing was sent.")

    tool = (args.get("tool") or "").strip().strip("'\"`")

    # NO TOOL, OR A TOOL IT DOES NOT CARRY: answer with what it does carry.
    # This is why there is one skill here and not two -- discovery is what a
    # refusal already has to say to be worth reading.
    if not tool:
        result, err = _mcp_rpc(url, "tools/list", {})
        if err:
            return f"Refused: {name} could not be read -- {err}."
        tools = result.get("tools") or []
        if not tools:
            return f"{name} carries no tools."
        lines = [f"{name} carries {len(tools)} tools:"]
        for t in tools:
            desc = " ".join(str(t.get("description") or "").split())
            lines.append(f"  - {t.get('name')}"
                         + (f"  {desc[:100]}" if desc else ""))
        return "\n".join(lines)

    # THE ARGUMENTS. A tool's arguments are its own contract, so they arrive as
    # the JSON object that contract describes rather than being guessed at here.
    raw = (args.get("content") or "").strip()
    payload: dict = {}
    if raw:
        try:
            payload = _json.loads(raw)
        except ValueError:
            return (f"Refused: the arguments for {tool!r} must be a JSON "
                    f"object, e.g. {{\"project\": \"research\"}}. Got: "
                    f"{raw[:120]!r}")
        if not isinstance(payload, dict):
            return (f"Refused: the arguments for {tool!r} must be a JSON "
                    f"OBJECT, not {type(payload).__name__}.")

    # The handshake first, as the protocol asks. A server that does not need it
    # is not harmed by it, and one that does would refuse everything without it.
    from . import __version__ as _ver
    _mcp_rpc(url, "initialize", {
        "protocolVersion": "2025-06-18", "capabilities": {},
        "clientInfo": {"name": "manjuel", "version": _ver}})

    result, err = _mcp_rpc(url, "tools/call",
                           {"name": tool, "arguments": payload})
    if err:
        # An unknown tool is the commonest miss, so it is answered with the
        # roster rather than with the word "refused" and nothing else.
        listing, lerr = _mcp_rpc(url, "tools/list", {})
        if not lerr:
            known = [str(t.get("name")) for t in (listing.get("tools") or [])]
            if tool not in known:
                return (f"Refused: {name} carries no tool called {tool!r}. "
                        f"It carries: {', '.join(sorted(known))}.")
        return f"Refused: {name} could not run {tool!r} -- {err}."

    text = _mcp_text(result)
    # THE TOOL'S OWN WORDS OUTRANK THE ENVELOPE. atlas learned this on
    # 2026-09-11 (ADR-006 item 2): a tool that fails has usually said why, and
    # replacing that with a transport-shaped message throws away the answer.
    if result.get("isError"):
        return (f"Refused: {name}'s {tool!r} refused -- "
                + (text or "and said nothing about why."))
    return text or f"{name}'s {tool!r} ran and returned nothing."


# =====================================================================
# Manifest
# =====================================================================


class SkillLibrary:
    def __init__(self, specs: list[SkillSpec], warnings: list[str], source: Path):
        self.specs = specs
        self.warnings = warnings
        self.source = source

    @classmethod
    def load(cls, skills_dir: str | Path = "skills") -> SkillLibrary:
        skills_dir = Path(skills_dir)
        specs: list[SkillSpec] = []
        warnings: list[str] = []

        if not skills_dir.exists():
            skills_dir.mkdir(parents=True, exist_ok=True)
            warnings.append(f"Created empty skills directory: {skills_dir.resolve()}")
            return cls(specs, warnings, skills_dir)

        for path in sorted(skills_dir.glob("*.md")):
            body = path.read_text(encoding="utf-8").strip()
            m = _ACTION_KEY_RE.search(body)
            if not m:
                warnings.append(
                    f"{path.name}: no '**Action Keyword:**' line found; skill not loadable."
                )
                continue
            mm = _SKILL_MODEL_RE.search(body)
            model = mm.group("m").strip() if mm else ""
            if model and ":" not in model:
                model = f"{model}:latest"
            says = parse_says(body)
            # A SENTENCE IS NOT A PHRASE. Every claimed phrase is weighed by
            # the Router on every turn, so prose that leaks out of a paragraph
            # and into this list is not a cosmetic fault -- it is a permanent
            # tax on routing, and it is invisible unless somebody counts. On
            # 2026-09-10 `doc_pass` claimed 35 phrases where 8 were declared,
            # and one of the 27 it invented was the standup question it had
            # just broken. Reported, never dropped: the hand that wrote the
            # file fixes it, the loader does not guess what was meant.
            for p in says:
                if len(p) > _PROSE_PHRASE or p.endswith("."):
                    warnings.append(
                        f"{path.name}: `**Says:**` claims a phrase that reads "
                        f"like prose, not something said at a door: "
                        f"\"{p[:60]}{'...' if len(p) > 60 else ''}\". The list "
                        f"ends at the first BLANK LINE -- put commentary below "
                        f"one.")
            specs.append(SkillSpec(m.group("kw").strip().lower(), path.name, body,
                                   model, parse_path_args(body),
                                   says, parse_takes(body)))

        return cls(specs, warnings, skills_dir)

    def validate(self) -> tuple[list[str], list[str]]:
        """Return (errors, warnings) for the md <-> handler binding."""
        errors: list[str] = []
        warns: list[str] = []

        declared = {s.keyword for s in self.specs}

        for spec in self.specs:
            if spec.is_prompt_skill:
                # Its body is the instruction; the model does the work.
                continue
            if spec.keyword not in _HANDLERS:
                errors.append(
                    f"{spec.filename} declares action '{spec.keyword}' but has neither a "
                    f"registered handler nor a '- **Model Target:**' line. A skill must "
                    f"either DO something (handler) or SAY something (prompt skill)."
                )

        for kw in sorted(_HANDLERS):
            if kw not in declared:
                warns.append(
                    f"Handler '{kw}' has no skills/*.md file, so no model can discover it."
                )

        return errors, warns

    def manifest(self, full: bool = False) -> str:
        """Compact by default -- this is what the router reads to pick a tool.

        `full=True` returns the whole markdown, which is what a prompt skill's
        own system prompt needs.
        """
        if not self.specs:
            return "No skills are currently available."
        if full:
            return "\n\n".join(f"--- Skill File: {s.filename} ---\n{s.body}"
                                for s in self.specs)
        return "\n".join(s.summary for s in sorted(self.specs, key=lambda x: x.keyword))

    def shortlist(self, objective: str, keep: int = SHORTLIST_KEEP,
                  chars: int = SHORTLIST_DESC_CHARS) -> str:
        """The manifest, narrowed to what bears on THIS objective.

        THE ARGUMENT IS BUDGET, NOT ACCURACY, and that is a change since
        the shortlist was last considered. It was measured unnecessary on
        2026-09-01 because dispatch already resolves 79% of tool turns
        deterministically and the residual is mostly turns wanting NO tool.
        That still holds. What changed is the other end: the Router's
        prompt carries EVERY skill and hit its ceiling twice on
        2026-09-02, so every description was cut to 112 characters -- the
        whole library paying full price for total irrelevance, and each
        entry getting thinner as the library grows.

        So: a handful of candidates at ~300 characters each costs FEWER
        tokens than thirty-odd at 112, and says far more about the ones
        that matter. Scored by word overlap over the skill's own words --
        arithmetic, no embedder, nothing to hallucinate.

        ADVISORY, NEVER DECIDING. The full roster still travels as bare
        keywords, so nothing is hidden from the Router: it is told what
        LOOKS relevant and can still name anything it likes. Same standing
        as drift and parity -- they measure, they never rule.
        """
        specs = sorted(self.specs, key=lambda x: x.keyword)
        if len(specs) <= keep:
            return self.manifest()
        words = {w for w in re.findall(r"[a-z0-9_]+", (objective or "").lower())
                 if len(w) > 2}
        if not words:
            return self.manifest()

        def score(s) -> int:
            hay = (f"{s.keyword} {s.keyword.replace('_', ' ')} {s.body} "
                   f"{' '.join(s.says or ())}").lower()
            n = sum(1 for w in words if w in hay)
            if s.keyword in (objective or "").lower().replace(" ", "_"):
                n += 5
            return n

        ranked = sorted(specs, key=lambda s: (-score(s), s.keyword))
        picked = [s for s in ranked[:keep] if score(s) > 0]
        if not picked:
            return self.manifest()

        lines = [f"These {len(picked)} look closest to this objective, in their "
                 f"own words:"]
        for s in picked:
            m = _DESC_RE.search(s.body)
            desc = " ".join((m.group("d") if m else s.body).split())[:chars]
            lines.append(f"- {s.keyword}  {desc}")
        rest = [s.keyword for s in specs if s not in picked]
        if rest:
            lines.append("")
            lines.append("Every other skill in this ground, by name only — "
                         "name any of them and it will run: " + ", ".join(rest))
        return "\n".join(lines)

    def keywords(self) -> set[str]:
        return {s.keyword for s in self.specs}

    def spec(self, keyword: str) -> SkillSpec | None:
        k = keyword.strip().lower()
        return next((s for s in self.specs if s.keyword == k), None)

    def models(self) -> set[str]:
        """Model tags prompt skills depend on, for the startup check."""
        return {s.model for s in self.specs if s.model}

    def tool_schemas(self, allowed: set[str]) -> list[dict]:
        """Ollama `tools=` schemas -- each skill offered ONLY what it declares.

        EVERY SKILL USED TO BE HANDED THE SAME TWO ARGUMENTS. `content` and
        `filepath`, on all thirty-nine, whatever their markdown said. The old
        docstring called that "the estate's calling convention" and it was
        really the absence of one: the schema was a constant, so a skill that
        takes nothing was still asked for two strings, and a skill that takes
        only a query was still offered a file.

        MEASURED 2026-09-10, off the library rather than by eye:

            10 skills declare NOTHING          git_status, git_init, git_pull,
                                               git_push, rack_list, rack_sync,
                                               proved, ground_report,
                                               skill_report, list_directory
            24 more declare only `content`     and were offered `filepath` too
             5 genuinely take a file           embed_text, ground_read, inspect,
                                               read_file, write_file

        WHAT IT COST, in the record. The standup sat at 8/9 on `a question
        about the ground` because the Router spent 62 seconds and 3,233
        characters deliberating whether `filepath` was required for
        `semantic_search` -- which does not take one -- and then gave up. The
        same thing on a live commit the same evening: "git_commit needs a
        filepath (which file changed) and content (what changed). I don't know
        what file changed", 5,357 characters of it. Neither model was
        confused; both were answering the schema they were given, and the
        schema was wrong.

        SO IT IS GENERATED FROM `declares(spec)` -- the one expression the
        dedup and `decided_call` already use. A skill's own file is the record
        of what it takes; nothing else is.

        THE DESCRIPTIONS ARE THE AUTHOR'S OWN WORDS, read from between the
        tags on the `**Parameters Needed:**` line (`param_notes`), falling
        back to the declared jail for a path argument. A sentence written in
        Python here would be a second place to describe an argument, and it
        would be the one that drifts.

        `required` STAYS EMPTY, deliberately. Every handler falls back to the
        objective when its argument is absent (s6/s26: a missing arg got
        narrated over by seats inventing results), so a required argument
        would refuse calls the estate currently completes. What was wrong was
        offering arguments that do not exist, not failing to demand the ones
        that do.

        The USAGE rules still live in the skill's markdown body and reach the
        model by injection when it picks one -- a JSON schema cannot carry
        "reads only", "refuses secrets", or "the objective IS the payload".
        """
        out = []
        for s in sorted(self.specs, key=lambda x: x.keyword):
            if s.keyword not in allowed:
                continue
            d = _DESC_RE.search(s.body)
            desc = " ".join(d.group("d").split()) if d else s.keyword
            notes = s.param_notes
            jails = dict(s.path_args or ())
            props: dict = {}
            for arg in sorted(declares(s)):
                said = notes.get(arg, "")
                if not said:
                    said = (f"the path this skill acts on, relative to the "
                            f"{jails[arg]}" if arg in jails else
                            f"the {arg} this skill acts on")
                props[arg] = {"type": "string", "description": said[:200]}
            out.append({
                "type": "function",
                "function": {
                    "name": s.keyword,
                    "description": desc[:400],
                    "parameters": {
                        "type": "object",
                        "properties": props,
                        "required": [],
                    },
                },
            })
        return out

    def execute(self, action: str, args: dict, env: SkillExecutionEnv) -> str:
        key = action.strip().lower()

        # A prompt skill runs the model named in its own markdown, using its
        # body as the system prompt. Adding one is writing a file -- no Python.
        if getattr(env, "review_only", False) and key not in REVIEW_ONLY_SKILLS:
            return (f"Refused: the table reviews; it does not act. "
                    f"'{key}' changes things, and counsel has eyes, not "
                    f"hands. Reading skills available: "
                    f"{', '.join(sorted(REVIEW_ONLY_SKILLS & set(self.keywords())))}.")

        # A capability is granted, never assumed. Same shape as the table's
        # review_only refusal above, resolved per seat: the Steward may read
        # the ground and nothing else until the record shows he handles it.
        allowed = getattr(env, "caller_allowed", None)
        if allowed is not None and key not in allowed:
            who = getattr(env, "caller", "") or "this seat"
            return (f"Refused: {who} is not cleared to call '{key}'. "
                    f"Cleared: {', '.join(sorted(allowed)) or 'nothing'}. "
                    f"Hand it to a seat that is.")

        spec = self.spec(key)

        # LAW 8: the one write-path. Every path a model names is resolved and
        # checked against its declared jail HERE, before a handler can act on
        # it. A skill declaring no Path Args passes untouched.
        refusal = gate_paths(spec, args, env)
        if refusal:
            return refusal

        if spec is not None and spec.is_prompt_skill and key not in _HANDLERS:
            return _run_prompt_skill(spec, args, env)

        handler = _HANDLERS.get(key)
        if handler is None:
            return (
                f"Error: '{action}' is not a known skill. "
                f"Available: {', '.join(sorted(self.keywords())) or 'none'}"
            )
        try:
            return _run_bounded(handler, env, args, SKILL_TIMEOUT)
        except TimeoutError:
            # Loudly, with the cure in the message -- never "" on failure.
            return (f"Refused: '{action}' did not finish within "
                    f"{SKILL_TIMEOUT:.0f}s and the run has stopped waiting "
                    f"(LAW 7: bounded everything). It may still be running "
                    f"behind this. Nothing it did is reported here. Raise the "
                    f"bound with MANJUEL_SKILL_TIMEOUT if this skill is "
                    f"legitimately slow.")
        except Exception as exc:
            return f"Skill '{action}' raised {type(exc).__name__}: {exc}"


def _run_prompt_skill(spec: SkillSpec, args: dict, env: SkillExecutionEnv) -> str:
    """Send <content> to the skill's own model, with its markdown as the rules.

    The body is passed verbatim as the system prompt, so every constraint the
    author wrote -- output shape, 'no conversational filler', the worked
    example -- reaches the model exactly as written.
    """
    payload = (args.get("content") or args.get("filepath") or "").strip()
    from_objective = False
    if not payload:
        # The standing ruling (search, commit, and now every prompt skill):
        # the objective IS the payload. deep_research starved five times in
        # sitting 39 waiting for a <content> nobody was going to type twice.
        payload = (getattr(env, "objective", "") or "").strip()
        from_objective = True
    if not payload:
        return f"Error: {spec.keyword} needs a <content> payload."
    # AN OBJECTIVE THAT IS ONLY THE ORDER IS NOT MATERIAL (the review of
    # 2026-09-08). Sitting 95: "time align the logs" -- four words, no log
    # text, no file -- became the payload by the fallback above, and
    # phi4-mini was asked to align them for 900s, twice. When the payload
    # is the OBJECTIVE (nothing was handed in) and it is under eight words,
    # it is a request for material, not material ("the logs" refers to
    # material; it is not material). An explicit <content>, however short,
    # is the caller's and is sent.
    if from_objective and len(payload.split()) < 8:
        return (f"Error: {spec.keyword} was given no material -- only the "
                f"order {payload!r}. Paste the text into <content>, or name a "
                f"file in the workspace with <filepath>.")

    from .registry import Agent
    seat = Agent(
        name=spec.keyword,
        model=spec.model,
        system_prompt=(
            f"{spec.body.strip()}\n\n"
            f"Follow the rules above exactly. Output only what they ask for: "
            f"no preamble, no sign-off, no conversational filler."
        ),
        stage="transform",
    )
    # A prompt skill runs OUTSIDE the pipeline -- its body is the system
    # message and the payload is the user turn, so build_prompt never sees
    # it and the clock it appends never arrived here. That left the estate
    # with two classes of model call, one time-aware and one not, and
    # nothing saying so: `time_align` was written promising to find what is
    # OVERDUE while forbidden to know today's date. The same block, from
    # the same function, so there is one clock in the ground.
    from .context import now_block
    try:
        return env.runtime.chat(seat, f"{now_block()}\n\n{payload}")
    except Exception as exc:
        return f"{spec.keyword} failed: {exc}"


# =====================================================================
# XML tool-call parsing
# =====================================================================

_ACTION_RE = re.compile(r"<action>(.*?)</action>", re.DOTALL)
_FILEPATH_RE = re.compile(r"<filepath>(.*?)</filepath>", re.DOTALL)
# Greedy on purpose: payloads frequently contain angle-bracketed text, so we
# match through to the LAST closing tag rather than the first.
_CONTENT_RE = re.compile(r"<content>(.*)</content>", re.DOTALL)


# Llama 3.x writes its tool call INTO THE TEXT when it sees tool names in
# context: `{"name": "git_status", "parameters": {...}}`, sometimes behind a
# `<|python_tag|>`. Sitting 84 (2026-09-04): the closing Steward on llama3.2
# delivered exactly that as its answer, twice in two minutes. It is a tool
# call in a different costume, and the engine reads it as one. Only a text
# that IS the call (starts with the brace or the tag) counts -- prose that
# happens to contain JSON is prose.
_JSON_CALL_RE = re.compile(
    r'^\s*(?:<\|python_tag\|>)?\s*\{\s*"(?:name|function)"\s*:\s*"([A-Za-z0-9_]+)"',
    re.DOTALL)


def _json_call(text: str) -> tuple[str | None, dict]:
    m = _JSON_CALL_RE.match(text or "")
    if not m:
        return None, {}
    args: dict[str, str] = {}
    body = (text or "").strip()
    if body.startswith("<|python_tag|>"):
        body = body[len("<|python_tag|>"):].strip()
    try:
        import json as _json
        obj = _json.loads(body)
        params = obj.get("parameters") or obj.get("arguments") or {}
        if isinstance(params, dict):
            for k in ("filepath", "content"):
                if str(params.get(k) or "").strip():
                    args[k] = str(params[k]).strip()
    except Exception:
        pass
    return m.group(1), args


def extract_tool_call(text: str) -> tuple[str | None, dict]:
    m = _ACTION_RE.search(text)
    if not m:
        return _json_call(text)

    args: dict[str, str] = {}
    fp = _FILEPATH_RE.search(text)
    if fp:
        args["filepath"] = fp.group(1).strip()
    ct = _CONTENT_RE.search(text)
    if ct:
        args["content"] = ct.group(1).strip()

    return m.group(1).strip(), args
