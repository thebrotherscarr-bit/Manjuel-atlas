"""Pipeline execution against a RunContext.

Every stage's prompt is built from the ORIGINAL objective and feed plus
selected prior outputs -- not just the previous stage's string. That is the
fix for the telephone-game failure in the original chain.
"""

from __future__ import annotations

import ast
import os
import re
import time
from dataclasses import replace

from .context import RunContext, StepResult, now_block
from . import intent
from . import seating
from .registry import Agent, AgentRegistry
from .runtime import OllamaRuntime, RuntimeError_, SALVAGE_MARK
from .runtime import SEAT_TIMEOUT as _SEAT_TIMEOUT
from .skills import (GATE_MARK, REVIEW_ONLY_SKILLS, WRITING_SKILLS,
                     SkillExecutionEnv, SkillLibrary, extract_tool_call,
                     args_from_words as skills_args_from_words,
                     _inside_ground as skills_inside_ground, unjail)
from .drift import DriftChecker
from . import ink
from . import lawgate
from . import gitstate as _gitstate

# A seat can raise a flag with <flags>technical</flags>. Flags drive `When:`
# steps -- this is how Expert Coder activates without a hardcoded branch
# (design doc section 5).
# A FLAG TAG NEED NOT BE WELL FORMED TO BE MEANT.
#
# SITTING 81. The Steward tried twice to hand work to the Router and both
# turns died on a missing slash:
#
#     "I need_tool<flags>list_directory<flags>"
#     "ground_list<flags>needs_tool<flags>tests<flags>"
#
# The old pattern required `</flags>`, so read_flags() found NOTHING --
# `needs_tool` was emitted and never rose, the Router never woke, and both
# runs ended at one stage. The operator's toll called that "steward being
# able to hand off to the router intentionally" and marked it THIN. He was
# reading a real failure; the seat was not unwilling, it was unreadable.
#
# The same miss published it. strip_control() removes what THIS pattern
# matches, so a malformed tag stripped to itself and sailed into the
# delivery -- sitting 42's ruling ("flags are the seat's channel to the
# ENGINE, never to the operator") undone by one character. The markup-only
# guard could not help either: the string carries letters, so it is not
# "only fencing".
#
# THREE SHAPES, ONE PATTERN: closed, unclosed-before-the-next-tag, and
# unclosed-at-the-end. BOUNDED ON PURPOSE -- content stops at `<` or a
# newline and at 80 characters, so a stray tag inside a long reply eats one
# short run and never the rest of the answer. `.*?` to `$` would have.
_FLAGS_RE = re.compile(r"<flags>([^<\n]{0,80})(?:</flags>)?",
                       re.IGNORECASE)
# The Router's control block, when it turns up in a seat that is not the
# Router (sitting 84). Stripped from anything a person reads; the handoff
# in run_pipeline reads it first.
_ACTION_RE = re.compile(r"<action>", re.IGNORECASE)
_JSON_CALL_RE = re.compile(
    r'^\s*(?:<\|python_tag\|>)?\s*\{\s*"(?:name|function)"\s*:\s*"[A-Za-z0-9_]+"',
    re.DOTALL)
_ACTION_BLOCK_RE = re.compile(
    r"<(action|filepath|content)>.*?</\1>\s*", re.IGNORECASE | re.DOTALL)
# The dialogue block's own furniture (context.dialogue_block): a heading a
# seat is SHOWN and must never say back, and the recalled-turn label.
# NARROWED 2026-09-07 after sitting 87. The first version fired on a
# "(recalled, ...)" label ANYWHERE, so a seat that answered FROM the recalled
# thread -- correctly, the one thing a follow-up needs -- was discarded as a
# recital, twice, and its words were lost. A recital OPENS with the
# scaffold: the heading, or a labelled turn as the first line. Anything
# else is a seat using what it was shown, which is what it is for.
_SCAFFOLD_RE = re.compile(
    r"^\s*(?:#{2,6}\s*Conversation so far\b|\(recalled(?:, [^)]*)?\) \w+:)",
    re.IGNORECASE)

# The router may call more than one skill before it is done, but never
# unboundedly -- a small model given an open loop will spin (design doc section 4).
# Five hops, not four (operator's ruling, sitting 63). The cap was doing the
# work of a rule: it bounded a Router that repeated itself. With identical
# calls now refused outright (see the dedup in the tool loop), the extra hop
# buys genuinely different work instead of another duplicate.
MAX_TOOL_STEPS = 5

# THE RULING LOOP'S CAP (the operator, 2026-09-07: "letting him give some
# room for thinking, but limit his turns ... kind of like the router is
# limited"). Sittings 86 and 87: Manjuel on gemma4:12b thought for 13-15k
# characters and ruled on nothing, twice; the court's delivery was the
# salvage line. A seat that deliberated and did not rule is now asked
# again -- its own deliberation in front of it, thinking switched OFF --
# and this is how many times in all it may sit on one question before
# what it has is what it has. Three at first (2026-09-07). Raised to
# TWELVE on the operator's word, 2026-09-08: "max of 12 'turns' ever
# within a reasoning model, pretty simple." The turn deadline (below) is
# what keeps twelve honest: a seat that keeps deliberating is cut by the
# clock, not by the count.
MAX_RULING_TURNS = 12

# THE TURN DEADLINE (the operator, 2026-09-08, in his words: "600 max for
# the whole system. there should never be more than 10 minutes between a
# response, thats absurd"). The seat bound (runtime.SEAT_TIMEOUT) caps ONE
# call; a turn seats several -- a court is four -- and sitting 95's `time
# align the logs` ran 1858s with no seat past its bound. So the run keeps
# a wall clock: a seat whose turn comes after the deadline is not seated
# and is named in the delivery (OUT OF TIME, the recompose's third block);
# a seat seated before it is handed the seconds LEFT as its budget, so
# nothing runs past the line. A sub-run inherits its parent's deadline.
# Parity cases are runs and take the same deadline ("not run often ...
# just for measurement", the operator, the same day).
try:
    TURN_DEADLINE = float(os.environ.get("MANJUEL_TURN_DEADLINE") or 600)
except ValueError:
    TURN_DEADLINE = 600.0


# A skill-shaped word: letters_with_underscores standing alone -- not a
# file name (`run_history.jsonl`, `test_manjuel.py`) and not a path part.
_SKILL_SHAPED = re.compile(r"(?<![\w/\\.])([a-z]+_[a-z_]+)(?![\w/\\.])")


def _unknown_skill_word(objective: str, skills) -> str:
    """A skill-shaped word (`index_workspace`) that names no skill, or ""."""
    try:
        known = set(skills.keywords())
    except Exception:
        return ""
    for m in _SKILL_SHAPED.finditer((objective or "").lower()):
        w = m.group(1)
        if w not in known:
            return w
    return ""


def _nearest_skills(word: str, skills, k: int = 3) -> list[str]:
    """The k skills sharing the most name-parts with `word` (no model)."""
    parts = set(word.split("_"))
    scored = []
    for kw in sorted(skills.keywords()):
        common = len(parts & set(kw.split("_")))
        if common:
            scored.append((-common, kw))
    return [kw for _, kw in sorted(scored)[:k]]


def _budget(ctx: RunContext) -> float | None:
    """Seconds left in this turn, or None when the run has no deadline."""
    at = getattr(ctx, "deadline_at", None)
    if at is None:
        return None
    return at - time.time()


def _within_deadline(seat: Agent, ctx: RunContext) -> Agent:
    """The seat with its `timeout` cut to the seconds left in the turn.

    A seat seated at minute nine of a ten-minute turn is bound at one
    minute, not its own 600: the runtime reads `timeout` and knows nothing
    of turns, so the cut is made here, on a copy. A seat with no time left
    is never handed to the runtime -- the loop above skips it by name.
    """
    left = _budget(ctx)
    if left is None:
        return seat
    own = float(getattr(seat, "timeout", None) or _SEAT_TIMEOUT)
    left = max(1.0, left)
    return replace(seat, timeout=min(own, left)) if left < own else seat

# The first line of a windowed read (skills.windowed): the shapes that mean
# "you were handed PART of this file". Read by the tool loop so the record
# and the delivery say so -- SITTING LAW 1 for the seats: a seat that read
# part 1 of 6 has not read the file, and sitting 87 run 7 answered "what
# does this system need" from 12,000 of DESIGN.md's 63,000 characters
# without saying so. The stamp is arithmetic over the tool's own words.
_PARTIAL_READ_RE = re.compile(
    r"^(?P<rel>\S[^\n]*?) [\u2014-]+ (?:part (?P<n>\d+) of (?P<total>\d+)"
    r"|section (?P<sec>'[^'\n]*'|\"[^\"\n]*\")"
    r"|`(?P<name>[^`\n]+)`, lines (?P<lo>\d+)-(?P<hi>\d+) of (?P<len>\d+)"
    r"|(?P<map>\d+ lines, \d+ definitions\. THIS IS THE MAP))")


_CODE_FENCE_RE = re.compile(r"```[a-zA-Z0-9_+-]*\n(.*?)```", re.DOTALL)
_FILEPATH_TAG_RE = re.compile(r"<filepath>(.*?)</filepath>", re.DOTALL)


# RULE 4 says the estate is local: no cloud service, no hosted model, no
# package that phones out. Until now that was a REQUEST -- a line in
# CLAUDE.md and a paragraph in a prompt, obeyed by whichever model happened
# to be on the coder's seat. These four names turn it into arithmetic. The
# list is EXACTLY what DESIGN 14.10 names and no more: widening it is one
# entry here, and should be earned by a landing that got through.
NETWORK_MODULES = frozenset({"requests", "urllib", "socket", "http"})

# eval/exec/__import__ execute a string as code, which is the one thing a
# reviewed artifact cannot be reviewed for -- the Quality Evaluator reads
# what is on disk, and these decide what runs at runtime.
DYNAMIC_CALLS = frozenset({"eval", "exec", "__import__"})

# THE NAMED HOLE, CLOSED 2026-09-03. inspect_code's docstring has said since
# it was built that "a module reached dynamically -- importlib,
# __import__("socket"), getattr on a module object -- is not caught by the
# import walk", and called importlib "a known hole, not an oversight".
# Writing a hole down is better than discovering it later; leaving it open
# once it is cheap to close is just leaving it open.
#
# `import importlib` is the whole route: import_module("socket") reaches
# every name NETWORK_MODULES refuses, and the walk cannot see the string.
# So the MODULE is refused, not the call -- a name is decidable, an
# argument that could be built at runtime is not.
#
# STILL NOT CLOSED, and still written down rather than claimed: a module
# object reached by getattr, a __builtins__ lookup, or an import spelled
# through a variable. This narrows the route; it does not seal it, and
# nothing here should be read as sealing it.
DYNAMIC_IMPORT = frozenset({"importlib"})


def inspect_code(name: str, code: str) -> tuple[bool, str]:
    """Refuse a landing BY PROOF rather than by prompt. Returns (ok, reason).

    Three verdicts, and the third is the one that keeps this honest:

      parses and is clean   -> (True,  "")
      parses, structure     -> (False, why, with the line number)
        says no
      NOT PYTHON            -> (True,  "not checked: <why>")

    THE GATE FAILS OPEN, DELIBERATELY (DESIGN 14.10's stated limit). A
    non-Python emission is landed with a note saying it was never inspected,
    because a gate that silently passes what it cannot read is worse than no
    gate: it spends the operator's trust on a check that did not happen. The
    caller is responsible for putting that note in the record.

    HONEST LIMITS, written here rather than discovered later:

      - `shell=True` is flagged on ANY call, not only subprocess's. DESIGN
        names subprocess, but the keyword is the dangerous thing and
        resolving the callee through imports and aliases is guesswork this
        does not need. It over-refuses in the rare case another API uses
        that keyword name; over-refusing on a WRITE gate is recoverable
        (the reason is named and the operator can land it by hand), and
        under-refusing is not.
      - a module reached dynamically. __import__ is refused by
        DYNAMIC_CALLS and `importlib` by DYNAMIC_IMPORT (2026-09-03), so
        the two named routes are shut. A module object reached by getattr,
        a __builtins__ lookup, or an import spelled through a variable is
        STILL NOT CAUGHT. That is narrowed, not sealed, and nothing here
        should be read as sealing it.
      - this proves what the SOURCE says. It does not prove what the code
        does when run. Nothing here executes the file, and nothing should.
    """
    if not name.lower().endswith(".py"):
        return True, f"not checked: {name} is not Python"
    try:
        tree = ast.parse(code, filename=name)
    except SyntaxError as exc:
        where = f"line {exc.lineno}" if exc.lineno else "position unknown"
        return False, f"does not parse: {exc.msg} ({where})"
    except (ValueError, RecursionError) as exc:
        # Null bytes and pathological nesting raise before SyntaxError does.
        return False, f"could not be parsed: {type(exc).__name__}: {exc}"

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                top = a.name.split(".")[0]
                if top in NETWORK_MODULES:
                    return False, (f"imports `{a.name}` (line {node.lineno}) "
                                   f"-- RULE 4: the estate is local")
                if top in DYNAMIC_IMPORT:
                    return False, (f"imports `{a.name}` (line {node.lineno}) "
                                   f"-- reaches any module by name at "
                                   f"runtime, which this gate cannot read")
        elif isinstance(node, ast.ImportFrom):
            # `from . import x` has no module name to judge; level > 0 is
            # relative and cannot reach the network by this route.
            if node.level == 0 and node.module:
                top = node.module.split(".")[0]
                if top in NETWORK_MODULES:
                    return False, (f"imports from `{node.module}` "
                                   f"(line {node.lineno}) -- RULE 4: the "
                                   f"estate is local")
                if top in DYNAMIC_IMPORT:
                    return False, (f"imports from `{node.module}` "
                                   f"(line {node.lineno}) -- reaches any "
                                   f"module by name at runtime, which this "
                                   f"gate cannot read")
        elif isinstance(node, ast.Call):
            fn = node.func
            called = fn.id if isinstance(fn, ast.Name) else (
                fn.attr if isinstance(fn, ast.Attribute) else "")
            if isinstance(fn, ast.Name) and called in DYNAMIC_CALLS:
                return False, (f"calls `{called}()` (line {node.lineno}) "
                               f"-- executes a string as code")
            for kw in node.keywords:
                if (kw.arg == "shell"
                        and isinstance(kw.value, ast.Constant)
                        and kw.value.value is True):
                    where = f"`{called}(shell=True)`" if called else "shell=True"
                    return False, (f"calls {where} (line {node.lineno}) "
                                   f"-- hands the string to a shell")
    return True, ""


def land_code(output: str, env, ctx) -> str:
    """Write the coder's declared file into the workspace jail. Returns the
    landed name, or "" when there is nothing well-formed to land.

    2026-09-03: the file is now PARSED before it is written (inspect_code).
    Code that does not parse used to land anyway and be reviewed as prose by
    the Quality Evaluator, which reads whatever is on disk and has no way to
    know the difference."""
    fp = _FILEPATH_TAG_RE.search(output)
    fence = _CODE_FENCE_RE.search(output)
    if not fp or not fence:
        return ""
    name = fp.group(1).strip()
    code = fence.group(1)
    if not name or not code.strip():
        return ""
    ok, why = inspect_code(name, code)
    if not ok:
        ctx.notes.append(f"coder file REFUSED ({name}): {why}")
        return ""
    if why:
        # Fails open, and says so. Silence here would be the gate lying.
        ctx.notes.append(f"coder file {name} landed UNINSPECTED -- {why}")
    try:
        path = env.safe_path(name)
        path.write_text(code, encoding="utf-8", newline="\r\n")
    except Exception as exc:
        ctx.notes.append(f"coder file NOT landed ({name}): {exc}")
        return ""
    n = len(code.splitlines())
    ctx.artifacts.append(path)
    ctx.notes.append(f"coder landed {path.name} ({n} lines) -- review raised")
    return f"{path.name} ({n} lines)"


_CODEISH = re.compile(
    r"(?i)\b(code|script|function|program|write|build|implement|fix|debug|"
    r"refactor|class|module|test|regex|python|py\b|json|parse|compute|"
    r"algorithm|bug|error|compile)\b|[(){}=<>\[\]]")


def _is_mention(text: str, m) -> bool:
    """A tag TALKED ABOUT rather than raised. Sitting 87, run 6: the Steward
    described the estate's flags in prose -- "I'll use the <flags>suspicious
    </flags> flag to mark..." -- and raised `suspicious` and `hard` for real;
    the Reasoner woke for 235s and a court took 475s. A raise stands on its
    own: at a line's edge, or between spaces. A mention sits in backticks
    or quotes, or is followed by the word "flag". A tag GLUED to a word is
    NOT a mention -- sitting 81's malformed raise ("I need_tool<flags>
    list_directory<flags>") is exactly that shape and must still raise."""
    before = text[max(0, m.start() - 1):m.start()]
    after = text[m.end():m.end() + 12].lstrip()
    if before in ("`", "'", '"') or after.startswith(("`", "'", '"')):
        return True
    if re.match(r"(?i)(?:flag|tag|marker)s?\b", after):
        return True
    return False


def read_flags(text: str) -> set[str]:
    out: set[str] = set()
    for m in _FLAGS_RE.finditer(text or ""):
        if _is_mention(text or "", m):
            continue
        for part in re.split(r"[,\s]+", m.group(1)):
            part = part.strip().lower()
            if part:
                out.add(part)
    return out


def strip_control(text: str) -> str:
    """Flags are the seat's channel to the ENGINE, never to the operator.

    2026-09-01: "What's the condition of the dir" was answered, in full, with
    `<flags>needs_tool</flags> read_file` -- and that string was the delivery.
    read_flags() only READS the tags; nothing removed them, so a seat that
    replied in markup had its markup published verbatim.

    <think> has been stripped in runtime.py since sitting 47 for exactly this
    reason. This is its twin, and it is MECHANISM rather than prompt on
    purpose: no wording makes a 3B reliably silent about a tag it was told to
    emit, but the engine can make an emitted tag never reach a person.
    """
    cleaned = _FLAGS_RE.sub("", text or "")
    # The action block goes too -- but ONLY when there is an <action>. The
    # Expert Coder declares a bare <filepath> line that land_code() reads
    # AFTER this strip; a <filepath> with no <action> is a declaration, not
    # a call, and stays.
    if _ACTION_RE.search(cleaned):
        cleaned = _ACTION_BLOCK_RE.sub("", cleaned)
    cleaned = cleaned.strip()
    # And llama's JSON-in-the-text call: a text that IS a tool call is
    # markup, not words, whatever its costume.
    if _JSON_CALL_RE.match(cleaned):
        return ""
    # A reply that was ONLY markup leaves its fencing behind. Tested on the
    # WHOLE remainder, never line by line: a per-line version of this ate the
    # Expert Coder's ``` fences and land_code stopped finding any code at all.
    if not re.sub(r"[\s`*_~-]", "", cleaned):
        return ""
    return cleaned

# Pipeline ORDER now lives in pipelines.md (PipelineBook). These remain only as
# a fallback if that file is missing, so the REPL can still start and say so.
#
# The Security Guardian leads every pipeline: the input is judged before any
# other seat reads it. Its verdict is parsed fail-closed (see read_verdict) and
# a refusal ends the run -- an inert safety gate was defect #4 in the design doc.
DEFAULT_PIPELINE = [
    "Security Guardian",
    "Morning Reviewer",
    "Router",
    "Quality Evaluator",
    "Delivery Agent",
]

# The estate seats, in the operator's order: plan -> file -> check the record
# -> refute. Manjuel and Jesster are both advisory gates; neither rewrites.
ESTATE_PIPELINE = [
    "Security Guardian",
    "Steward",
    "Neiro",
    "Manjuel",
    "Jesster",
]

# THE LAW's order: the court hears all counsel, then rules. Manjuel last.
COURT_PIPELINE = [
    "Security Guardian",
    "Steward",
    "Neiro",
    "Jesster",
    "Manjuel",
]

PIPELINES: dict[str, list[str]] = {
    "default": DEFAULT_PIPELINE,
    "estate": ESTATE_PIPELINE,
    "court": COURT_PIPELINE,
}


class Aborted(Exception):
    pass


class Refused(Aborted):
    """The guard refused the input. Distinct from a stage that merely failed."""


def bogus_citations(results_text: str, prose: str) -> list:
    """THE CITATION-CHECK's arithmetic: cited pairs that are not results.

    A cited path is REAL if its basename matches a returned result's
    basename (seats cite `SEAT_LOG.md` where the result printed a longer
    relative path). Everything else the prose presents as a scored hit is
    bogus -- the results text is exhaustive for this turn. A score cited
    against the WRONG real path is let pass for now: narrow and certainly
    right beats broad and crying wolf."""
    from manjuel import intent
    returned = intent.search_result_pairs(results_text)
    real_names = {p.rsplit("/", 1)[-1].lower() for p, _ in returned}
    return [(p, s) for p, s in intent.cites_search_results(prose)
            if p.rsplit("/", 1)[-1].lower() not in real_names]


def read_verdict(text: str) -> tuple[bool, str]:
    """Parse a guard's verdict. FAIL CLOSED.

    SAFE       -> (True, "")
    UNSAFE: x  -> (False, "x")
    anything   -> (False, reason) -- a small model that cannot follow a
                  two-token format is not a signal to lean on, so an
                  unreadable verdict is refused rather than waved through.
    """
    head = (text or "").strip()
    if not head:
        return False, "the guard returned nothing"

    # Look only at the first non-empty line; models like to add commentary.
    first = next((l.strip() for l in head.splitlines() if l.strip()), "")
    upper = first.upper()

    if upper.startswith("UNSAFE"):
        reason = first[len("UNSAFE"):].lstrip(" :-").strip()
        return False, reason or "no reason given"
    if upper.startswith("SAFE") and len(first) <= 16:
        return True, ""
    return False, f"unreadable verdict: {first[:120]!r}"


# ---------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------


def _default_prompt(agent: Agent, ctx: RunContext, skills: SkillLibrary) -> str:
    return (
        f"{ctx.source_block()}\n\n"
        f"## Prior Stage Outputs\n{ctx.history_block()}\n\n"
        f"## Your Task\n"
        f"Apply your role to the material above. The Original Objective is the "
        f"authoritative statement of intent -- if a prior stage drifted from it, "
        f"correct toward the objective."
    )


def _indented(text: str) -> str:
    """Recorded material rendered as quotation, not template. Sitting 39's
    router echoed a greeting back verbatim; indentation is the shape that
    does not invite imitation."""
    return "\n".join(f"    {l}" for l in (text or "").splitlines())


def _router_prompt(agent: Agent, ctx: RunContext, skills: SkillLibrary) -> str:
    # Sitting 24: intent named `semantic_search`; the Router spent 73s calling
    # classify_sentiment instead. What the objective names outright is not a
    # suggestion to weigh -- it is the call, unless it is plainly wrong.
    named_line = (f"\nThe objective names the skill `{ctx.named_tool}`. "
                  f"Call `{ctx.named_tool}` unless it is plainly wrong for "
                  f"the request." if ctx.named_tool else "")
    # THE NAMED FILE, CHECKED (sitting 88). The engine looked: the file the
    # operator named either IS in the ground -- then it is the argument,
    # and the Router is told the exact path rather than left to spell one
    # -- or is NOT, and the Router is told that too, so it does not guess.
    if getattr(ctx, "named_file", ""):
        if ctx.named_file_ok:
            named_line += (f"\nThe file named, `{ctx.named_file}`, IS in the "
                           f"ground at exactly that path. Use "
                           f"<filepath>{ctx.named_file}</filepath> -- no "
                           f"folder in front of it, no other spelling.")
        else:
            named_line += (f"\nThe file named, `{ctx.named_file}`, is NOT in "
                           f"the ground at that path (the engine looked). Do "
                           f"not guess another path; say so, or list the "
                           f"ground first.")
    # ...and when one IS named, hand over its markdown. The manifest above
    # truncates every description to ROUTING_DESC_CHARS, which says WHAT a
    # skill is and never HOW to use it. All 31 bodies are ~4,000 tokens; the
    # one already chosen is 70-135. The operator's words: the Router figures
    # out what is needed, pulls in the skill markdown, works out how to use
    # it, and forwards.
    named_spec = skills.spec(ctx.named_tool) if ctx.named_tool else None
    manual = (f"\n\n## How `{ctx.named_tool}` works\n{named_spec.body.strip()}\n"
              if named_spec and not named_spec.is_prompt_skill else "")
    return f"""{ctx.source_block()}

## Prior Stage Outputs (record, not template)
{_indented(ctx.history_block())}

## Available Skills
{skills.shortlist(ctx.objective)}{manual}

## Your Task
Decide whether a skill should run right now.{named_line}

Most take only the objective; some need no input at all (git_status,
rack_list, list_directory). Never refuse for want of source material.

If YES, reply with ONLY this XML block and nothing else:
<action>action_keyword</action>
<filepath>filename.ext</filepath>
<content>payload</content>

Omit <filepath> or <content> if that skill does not need them.
The action_keyword MUST be one of: {', '.join(sorted(skills.keywords())) or '(none available)'}

If NO skill is needed, output no XML -- write a prose draft resolving the
objective.

If code needs writing, add <flags>technical</flags> anywhere in your reply to
wake the Expert Coder. Only when code is actually wanted."""


def _delivery_prompt(agent: Agent, ctx: RunContext, skills: SkillLibrary) -> str:
    verified = ctx.last_output()
    return (
        f"{ctx.source_block()}\n\n"
        f"## Verified Pipeline Text\n{verified}\n\n"
        f"## Your Task\nFormat the verified text into your briefing layout. "
        f"The Original Objective above states what the reader actually asked for -- "
        f"make sure the finished document answers it.\n"
        f"Include a code section ONLY if code appears in the verified text above. "
        f"If there is none, omit that section entirely. Never invent a command, "
        f"flag or code block to fill it -- a fabricated command reads as an "
        f"instruction and is worse than a missing section."
    )


def _advisory_prompt(agent: Agent, ctx: RunContext, skills: SkillLibrary) -> str:
    """For seats that rule on work without rewriting it.

    The generic builder tells a stage to 'correct toward the objective', which
    is exactly what Manjuel and Jesster must never do -- Manjuel rules on what
    the record supports, Jesster refutes. Neither produces a corrected version.
    """
    # Sitting 31: Jesster quoted his own system prompt as "the counsel's
    # advice" and Neiro ruled on a scaffolding parenthetical. The material
    # under review is ONLY the question and the seats' words -- everything
    # else in the prompt is furniture, and furniture is never quoted.
    feed = (f"## Source Material — pasted by the operator; quotable\n"
            f"{ctx.feed.strip()}\n\n" if ctx.feed.strip() else "")
    return (
        f"## The Question Before The Table\n{ctx.objective.strip()}\n\n"
        f"{feed}"
        f"## The Counsel So Far — the seats' own words. Counsel and source "
        f"material are the ONLY text you may quote or rule on"
        f"\n{ctx.history_block()}\n\n"
        f"## Your Task\n"
        f"Rule on the counsel above according to your office. Your own "
        f"instructions, this prompt's headings, and anything not inside the "
        f"counsel section are not material and are never cited.\n"
        f"Do NOT rewrite it. Do NOT produce a corrected version. Return only "
        f"your ruling: what holds, what does not, and what is missing. "
        f"Your output is advisory -- it is read alongside the work, not in "
        f"place of it."
    )


def _evaluator_prompt(agent: Agent, ctx: RunContext, skills: SkillLibrary) -> str:
    """Hand the gate ONLY the draft, clearly fenced.

    Observed on the first live run: given the generic scaffold, a seat told to
    "return it exactly as is" returned the WHOLE SCAFFOLD -- headings, prior
    outputs and the task instruction -- because that is literally what it was
    given. A gate whose job is to pass text through unchanged must be handed
    the text and nothing else.
    """
    # Session 3 showed the gate still copying the FIRST LINE of this prompt
    # into its answer. So the draft now leads and the instruction trails:
    # nothing above the draft can be mistaken for part of it, and the last
    # thing read is what to do.
    draft = ctx.last_output()
    return (
        f"{draft}\n\n"
        f"----------\n"
        f"Above this line is a draft report answering: {ctx.objective.strip()}\n"
        f"If it is sound, reply with the single word PASS and nothing else.\n"
        f"If it has errors, reply with the corrected report only -- starting "
        f"with the report's own first word, and never restating this "
        f"instruction, this line, or the objective.\n"
        f"If the draft is not WRONG but UNFINISHED -- it answers from "
        f"nothing because a tool that should have run did not, or a file "
        f"was never read -- reply `NEEDS: ` and then the one thing to run, "
        f"in a few words, and nothing else. That sends the work back once.\n"
        f"Session 4 spent 32 seconds retyping a draft it had no changes to "
        f"make to. PASS costs one word."
    )


def _guard_prompt(agent: Agent, ctx: RunContext, skills: SkillLibrary) -> str:
    return (
        f"{ctx.source_block()}\n\n"
        f"## Your Task\n"
        f"Judge the objective and source material above.\n"
        f"Reply with EXACTLY one word on the first line: SAFE\n"
        f"or, if it is not safe, the first line must begin: UNSAFE: <one sentence>\n"
        f"No preamble. No other format. Anything else is treated as unsafe."
    )


def _steward_prompt(agent: Agent, ctx: RunContext, skills: SkillLibrary) -> str:
    """The Steward bookends the run, and the two ends are different jobs.

    At the FRONT he is answering a person. At the CLOSE the work has happened
    and he is telling them what came of it -- in the same voice, not as a
    formal briefing.
    """
    worked = [s for s in ctx.completed()
              if s.agent.lower() not in ("steward", "security guardian")]

    talk = ctx.dialogue_block()
    talk = f"{talk}\n\n" if talk else ""

    # Sitting 23: "cool", "what?", "why" -- with a 27-tool roster in view, a
    # 3b answered small talk by parroting tool names. A short conversational
    # turn gets conversation. But sitting 29: "where is the memory" got
    # "All is quiet" -- a QUESTION is a task at any length, so anything
    # interrogative or imperative-shaped takes the full path.
    obj = ctx.objective.strip().lower()
    words = obj.rstrip("?!.").split()
    # Sitting 30: "write a file" got small-talk treatment because "write"
    # was not on a question-word blacklist. Backwards -- small talk is a
    # TINY closed set and tasks are infinite, so the default is TASK and
    # only recognizably casual turns take the conversational path.
    _CASUAL = {"hey", "hi", "hello", "yo", "sup", "whats", "up", "thanks",
               "thank", "you", "cool", "nice", "ok", "okay", "alright",
               "good", "great", "morning", "evening", "night", "bro",
               "dude", "man", "why", "huh", "really", "wow", "lol",
               "haha", "no", "yes", "yeah", "yea", "nah", "stew",
               "homie", "homey", "bud", "buddy", "dawg", "fam", "bruh",
               "brother", "gang", "chief", "boss", "peace", "later",
               "night", "goodnight", "bye", "goodbye", "hmm", "hmmm",
               "thanx", "thx", "ty", "bet", "aight", "word",
               "steward", "there", "how", "it", "going", "hows", "the",
               "void", "treating", "a", "job", "work", "today", "that",
               "this", "so", "well", "damn", "sweet", "love"}
    def _near_casual(w: str) -> bool:
        w = w.strip(",'!.")
        if w in _CASUAL:
            return True
        # "heloo", "stewy": one edit off a casual word is still casual.
        # Bounded and deterministic -- length must be close and one pass.
        for c in _CASUAL:
            if abs(len(c) - len(w)) > 1:
                continue
            if len(w) >= 3 and (w in c or c in w):
                return True
            if len(c) == len(w) and sum(a != b for a, b in zip(c, w)) == 1:
                return True
            # one char dropped or added mid-word: "helo" ~ "hello"
            if abs(len(c) - len(w)) == 1 and len(w) >= 3:
                a, b = (c, w) if len(c) > len(w) else (w, c)
                for i in range(len(a)):
                    if a[:i] + a[i + 1:] == b:
                        return True
        return False

    is_casual = bool(words) and all(_near_casual(w) for w in words)
    # Anaphora is conversation: "say that again", "what was that" point at
    # the dialogue, not at a mission. Sitting 46 sent "say that again?"
    # through the roster and a Router odyssey; the answer was in the thread.
    _ANA = {"that", "it", "this", "again", "repeat"}
    # ...but an ACTION beats anaphora: "commit it" is a task wearing a
    # pronoun, not a follow-up. Tool-naming and write-shapes disqualify.
    is_followup = (len(words) <= 5
                   and any(w.strip(".,!?'") in _ANA for w in words)
                   and not intent.wants_writing(obj)
                   and not intent.names_a_tool(obj, skills))
    if (not worked and len(ctx.objective.strip()) < 40
            and not ctx.feed.strip() and (is_casual or is_followup)):
        if not agent.system_prompt:
            # BAKED seat: the compile knows how to behave -- instruction
            # text here is redundant, and redundant instructions are parrot
            # food (sitting 46: he recited the scaffold back out loud).
            return (f"{talk}The operator just said: "
                    f"{ctx.objective.strip()}")
        return (
            f"{talk}The operator just said: {ctx.objective.strip()}\n\n"
            f"Reply briefly, as yourself, in plain words -- this is "
            f"conversation, not a task. Never answer with tool names or "
            f"flag names. If it genuinely needs a tool, raise "
            f"`<flags>needs_tool</flags>` and say in one line what for.\n\n"
            f"NOTHING IS HAPPENING except what is written above -- no "
            f"visitors, no intrusions, no incidents unless the record states "
            f"them, and never treat earlier speculation as fact. But absence "
            f"of events is not your ANSWER, it is your constraint: respond "
            f"to what he actually said, in fresh words, this turn's words. "
            f"Never answer with a stock phrase, and never repeat a line you "
            f"already used earlier in the conversation -- a door that says "
            f"the same thing every time has stopped listening. A farewell "
            f"('peace', 'later', 'thanks man') gets a brief goodbye in kind "
            f"-- never a tool, and never close anything yourself; the door "
            f"stays open until the operator himself shuts it."
        )

    if not worked:
        # Session 5: the Steward told the operator to run `git add` by hand
        # rather than raising needs_tool -- it knew its own limits but not the
        # chain's reach. Naming the tools closed that gap and opened another.
        #
        # PHRASES FOR THE DOOR, KEYWORDS FOR THE ROUTER (the operator,
        # 2026-09-09: "that's what the chat/router gating is for"). This line
        # was `", ".join(sorted(skills.keywords()))` -- thirty-seven callable
        # tokens in front of a 3b model asked to say good morning, and it
        # answered them: sitting 88's "morning, what's on the board?" came back
        # as "our objective is to answer a question about sentiment
        # classification... we'll use the `classify_sentiment` tool", a whole
        # mission built around a name it had just been shown. It was not
        # hallucinating; `classify_sentiment` is ours. The roster WAS the
        # provocation.
        #
        # So the door is told the SHAPE of the reach and not one callable name.
        # It only ever needed to know that handing off is possible -- which
        # tool is the Router's question, and the Router still gets the list
        # (_router_prompt). A phrase per skill was measured and refused:
        # 4,617 characters against the keyword list's 451, ten times the prompt
        # at the one seat whose value is answering in under a second, and a
        # long description is its own bait.
        #
        # A stroke asserts NO KEYWORD survives here, derived from the library,
        # so a skill added tomorrow cannot quietly reappear at the door.
        return (
            f"{talk}{ctx.source_block()}\n\n"
            f"Answer this.\n\n"
            f"You are not alone: the chain behind you can read and write files "
            f"in the ground, search the record, drive the repository, look at "
            f"the rack, and run the suites. Hand any of that off by raising "
            f"`<flags>needs_tool</flags>`.\n\n"
            f"Do not tell the operator to run something himself when the chain "
            f"could do it. Raise the flag instead, and say in one line what "
            f"you are passing along -- in plain words, never a tool name.\n\n"
            f"Answer in plain words. Never answer with tool names or flag "
            f"names -- the flag is for the chain, the sentence is for him, "
            f"and a reply that is only a flag has said nothing."
        )

    # Sitting 24: the closer copied "[Router]" bracket labels straight into
    # the delivery. The record is indented like a quotation so its shape does
    # not read as a template to imitate.
    done = "\n\n".join(
        f"{s.agent} produced:\n" + "\n".join(f"    {l}" for l in
                                               s.output.strip().splitlines())
        for s in worked)
    # SITTING 69. "what does deep research do?" got a plain DESCRIPTION
    # from the Router -- no tool called -- and the closer announced "Deep
    # research conducted an intensive analytical evaluation... the outcome
    # was a detailed breakdown", past tense, over a run in which nothing
    # ran. The closer was left to infer whether work happened from a
    # heading that says "Work was done on it". Now it is TOLD, from the
    # record, the way it is told the time: an observation, not an
    # inference. Dropping `route` from the `worked` flag was tried first
    # and reverted -- that flag seats this seat, and half of ordinary
    # conversation runs through a tool-less Router.
    ran = sorted({k for s in ctx.steps for k in (s.tool_calls or ())})
    if ran:
        did = (f"TOOLS THAT ACTUALLY RAN THIS TURN: {', '.join(ran)}. "
               f"Report what they returned, and nothing beyond it.")
    else:
        did = ("NO TOOL RAN THIS TURN. Nothing was performed, fetched, "
               "written or checked. What is above is a seat's WORDS — a "
               "description or an opinion — and your answer must not put "
               "it in the past tense as though it were done. Say what was "
               "said, not what was accomplished.")
    return (
        f"{talk}They asked: {ctx.objective.strip()}\n\n"
        f"Work was done on it:\n\n{done}\n\n"
        f"----------\n"
        f"{did}\n\n"
        f"Tell them what came of it, in your own plain voice — what happened, "
        f"what it means for what they asked, and anything that is still open. "
        f"Do not re-run the work or restate it verbatim; they want the upshot, "
        f"not the transcript. If a result looks wrong or thin, say so.\n\n"
        f"Write plain sentences. Never reproduce the layout, labels or "
        f"indentation of the record above — no seat names in brackets, no "
        f"copied headings. "
        f"Report ONLY what appears in the record above. The earlier "
        f"conversation is context for tone, never a source of events: a tool "
        f"mentioned in it did not run now unless it is listed above. Never "
        f"report a status code, push, search or result you cannot point to "
        f"in the work shown — sitting 22 delivered three invented tool runs "
        f"that way, and an invented success is worse than a plain failure."
    )


_BUILDERS = {
    "security guardian": _guard_prompt,
    "steward": _steward_prompt,
    "router": _router_prompt,
    "quality evaluator": _evaluator_prompt,
    "delivery agent": _delivery_prompt,
    "manjuel": _advisory_prompt,
    "jesster": _advisory_prompt,
    # Neiro provides for every part and decides for none -- the generic
    # "correct toward the objective" is a rewrite instruction, which is
    # exactly what a counsel seat must not receive.
    "neiro": _advisory_prompt,
}


def build_prompt(agent: Agent, ctx: RunContext, skills: SkillLibrary) -> str:
    """Assemble one seat's prompt: the builder's own shape, then the blocks
    that belong to the whole run.

    WHERE THESE BLOCKS GO IS LOAD-BEARING, and both ends are spoken for.
    The Quality Evaluator's prompt must OPEN with the draft and nothing
    else -- a label above it is a thing to copy, which is what it was
    caught doing -- so nothing may be prepended. Every builder also puts
    its material first and its instruction last, which the small models
    depend on, so what is appended must be short and must not read as the
    task. The clock and the method are therefore APPENDED, briefly, after
    the seat's own shape is complete and undisturbed.
    """
    builder = _BUILDERS.get(agent.key, _default_prompt)
    prompt = builder(agent, ctx, skills)

    # The present moment, stamped from THIS RUN's start so the whole chain
    # agrees on when "now" was -- a later stage must not believe it is a
    # minute further into the future than the first.
    prompt += "\n\n" + now_block(getattr(ctx, "started_at", None))

    # THE LAW and THE STANDING ride in the SYSTEM ROLE (carried_blocks) for
    # a seat that has one. A BAKED seat has none -- sending one would
    # overwrite the bake -- so it takes them here, on the user prompt, the
    # shape every seat had until 2026-09-07.
    if not agent.system_prompt:
        carried = carried_blocks(agent, ctx)
        if carried:
            prompt += "\n\n" + carried

    # A command's METHOD rides with the whole run, so every seat that sits
    # works the operator's procedure rather than only the first one. One
    # insertion point, the same text for all, and labelled as HIS: the one
    # thing a seat must never do is mistake a procedure for something a
    # model said (LAW 5 cuts both ways -- testimony is not fact, and
    # instruction is not testimony).
    if getattr(ctx, "method", "").strip():
        prompt += ("\n\n## Method — the operator's procedure for this run\n"
                   "Follow it. It came from him, not from a model.\n\n"
                   + ctx.method.strip() + "\n")
    return prompt


def _is_court(agent: Agent) -> bool:
    """The seats that RULE -- the advisory builder is the mark, so this
    cannot drift from _BUILDERS."""
    return _BUILDERS.get(agent.key) is _advisory_prompt


def carried_blocks(agent: Agent, ctx: RunContext) -> str:
    """What a seat is handed BESIDE its own prompt, as the hand is handed
    CLAUDE.md: the law, and the standing. The operator, 2026-09-07: "make
    sure we are looking at how the claude.md works and implementing that
    system into the chain."

    THE LAW, to every seat -- the short verdict block. The COURT (the
    seats that rule) is handed the ten estate laws VERBATIM instead: the
    hand reads 3KB of law every turn (CLAUDE.md RULE 0); a seat that rules
    on the record was reading sixty words about it. The door and the
    Router keep the short form; cost matters there.

    THE STANDING, to the door and the court -- what this sitting is FOR,
    from DAYBOOK.md's last entry (seatlog.standing_block). CLAUDE.md READ
    FIRST: "you begin with total amnesia; this is the only file that
    carries intent." Every seat began with amnesia too, and sitting 87's
    toll said so: "needs more context and reasoning intent." Not the
    Router: its prompt is budget, and it routes, it does not interpret.

    WHERE IT GOES is the point. Sittings 86 and 87 saw the `## The law`
    block recited as content, three times, because it rode in the USER
    prompt beside the material. CLAUDE.md reaches the hand as system
    text, not inside the operator's message; the same for the seats
    (run_pipeline puts this in the system role; build_prompt appends it
    to the user prompt only for a BAKED seat, which has no system role).
    """
    blocks: list[str] = []
    court = _is_court(agent)
    door = agent.key == "steward"
    full = getattr(ctx, "law_full", "").strip()
    short = getattr(ctx, "law", "").strip()
    if court and full:
        blocks.append(full)
    elif short:
        blocks.append(short)
    standing = getattr(ctx, "standing", "").strip()
    if standing and (door or court):
        blocks.append(standing)
    # THE STORY (0.1.6), to the same seats: what this sitting has done.
    story = getattr(ctx, "story", "").strip()
    if story and (door or court):
        blocks.append(story)
    return "\n\n".join(blocks)


def _seat_for_call(agent: Agent, ctx: RunContext) -> tuple[Agent, str]:
    """(the seat as it sits, what rode in its system role). A prompted seat
    sits with its own prompt plus the carried blocks in the SYSTEM role; a
    BAKED seat sits as declared and build_prompt has already put the
    blocks on its user prompt. The Agent is frozen; `replace` makes the
    seat for this call and leaves the registry's declaration untouched."""
    if not agent.system_prompt:
        return agent, ""
    carried = carried_blocks(agent, ctx)
    if not carried:
        return agent, ""
    return replace(agent, system_prompt=f"{agent.system_prompt.rstrip()}\n\n{carried}"), carried


def _press_for_ruling(seat: Agent, prompt: str, output: str, thoughts: list,
                      runtime, sink, ctx: RunContext, report, started: float) -> str:
    """THE RULING LOOP. A seat that came back with the salvage line thought
    and did not rule. It is asked again, up to MAX_RULING_TURNS sittings in
    all: the same prompt, its own deliberation appended as ITS OWN WORDS
    (never as material), and the instruction to rule now. Thinking is
    switched off for the retry (runtime.chat think=False) so the model has
    to write rather than think a second time; a runtime that cannot switch
    it off still gets the bounded retry.

    The record says what happened at every turn. If the last turn is still
    the salvage line, that line stands -- the same shape as before this was
    built, and the note says the turns were spent."""
    turn = 1
    while output.startswith(SALVAGE_MARK) and turn < MAX_RULING_TURNS:
        turn += 1
        note = (f"{seat.name} deliberated without ruling ({time.time() - started:.0f}s); "
                f"turn {turn} of {MAX_RULING_TURNS} -- asked to rule on its own "
                f"deliberation, thinking off")
        ctx.notes.append(note)
        report("      " + ink.warn(note))
        tail = " ".join("".join(thoughts).split()[-600:])
        follow = (
            f"{prompt}\n\n"
            f"## Your own deliberation so far (your words, not material; never "
            f"quote it as counsel)\n{_indented(tail) if tail else '    (none recorded)'}\n\n"
            f"You deliberated and did not rule. RULE NOW, in plain words, in "
            f"under 400 words. Do not deliberate again; do not restate the "
            f"material. Begin with the ruling.")
        output = runtime.chat(_within_deadline(seat, ctx), follow, stream_to=sink,
                              think_to=thoughts.append, think=False)
        if not (output or "").strip():
            output = SALVAGE_MARK + " (and the retry returned nothing)"
    if output.startswith(SALVAGE_MARK):
        note = (f"{seat.name} spent {turn} of {MAX_RULING_TURNS} turns and did not "
                f"rule; the deliberation stands as the record")
        ctx.notes.append(note)
        report("      " + ink.warn(note))
    elif turn > 1:
        note = f"{seat.name} ruled on turn {turn} of {MAX_RULING_TURNS}"
        ctx.notes.append(note)
        report("      " + ink.dim(note))
    return output


def note_partial_read(action: str, result: str, ctx: RunContext, report=print) -> str:
    """Stamp a read that returned PART of a file. Returns the stamp or "".

    Arithmetic over the tool's own first line (skills.windowed says "part
    n of N", "section 'x'", "`name`, lines a-b of L", or "THIS IS THE MAP").
    Recorded as it happens, the failures' shape, so the recompose can put
    it in the delivery without any seat remembering to."""
    first = (result or "").lstrip().split("\n", 1)[0]
    m = _PARTIAL_READ_RE.match(first)
    if not m:
        return ""
    rel = m.group("rel").strip()
    if m.group("n"):
        stamp = f"{rel} -- part {m.group('n')} of {m.group('total')}"
    elif m.group("sec"):
        stamp = f"{rel} -- one section ({m.group('sec')})"
    elif m.group("name"):
        stamp = (f"{rel} -- one definition (`{m.group('name')}`, lines "
                 f"{m.group('lo')}-{m.group('hi')} of {m.group('len')})")
    else:
        stamp = f"{rel} -- the map of its definitions, not its text"
    ctx.partials.append((action, rel, m.group("n"), m.group("total"), stamp))
    note = f"partial read: {stamp}"
    if note not in ctx.notes:
        ctx.notes.append(note)
    report("      " + ink.dim(note))
    return stamp


def decided_call(ctx: RunContext) -> str:
    """The Router's markup for a call the ENGINE has fully decided, or "".

    Decided means: the tool is named AND its argument was checked on disk
    -- a folder that exists (names_a_folder) or a file that exists
    (named_file_ok). Nothing softer: a tool named with no argument, or an
    argument the engine only guessed, still goes to the Router to choose."""
    tool = getattr(ctx, "named_tool", "")
    if not tool:
        return ""
    args = dict(getattr(ctx, "tool_args", None) or {})
    by = getattr(ctx, "named_by", "")
    ok = ((by == "names_a_folder" and (args.get("content") or tool == "list_directory"))
          or (tool == "ground_read" and getattr(ctx, "named_file_ok", None)
              and args.get("filepath"))
          # the operator's own words carried the argument (Takes:, or the
          # words after the name) -- the review of 2026-09-08
          or (by == "the words" and str(args.get("content") or "").strip()
              and tool != "ground_read"))
    if not ok:
        return ""
    xml = f"<action>{tool}</action>"
    for k in ("filepath", "content"):
        if str(args.get(k) or "").strip():
            xml += f"<{k}>{args[k]}</{k}>"
    return xml


def _refuse_testimony(agent: Agent, evidence: str, refusal: str) -> str:
    """A refused claim takes the seat's WORDS and leaves the tools' RESULTS.

    Sitting 88, the court: semantic_search returned five real passages --
    one of them a prior ruling on the very question -- and the Router's
    prose said it had written memory.md. The write-claim check replaced
    the Router's whole output, results included, with REFUSED; the court
    got no evidence and three seats spent 440s arguing about memory.md.
    The results are facts and were never the claim. Same shape as the
    scaffold guard's fault of 09-04: a guard must not destroy evidence."""
    if not (evidence or "").strip():
        return refusal
    return (f"{evidence}\n\n--- {agent.name} reading the above (testimony, "
            f"not tool output) ---\n\n{refusal}")


def unread_parts(ctx: RunContext) -> list[str]:
    """The partial reads that did not add up to a whole file this run. A
    file whose every numbered part was read IS read whole and is not
    listed; a section, a definition or a map never adds up to the file."""
    parts: dict[str, set] = {}
    totals: dict[str, int] = {}
    stamps: list[tuple[str, str]] = []
    for _action, rel, n, total, stamp in getattr(ctx, "partials", ()):
        if n and total:
            parts.setdefault(rel, set()).add(int(n))
            totals[rel] = int(total)
        stamps.append((rel, stamp))
    whole = {rel for rel, seen in parts.items()
             if seen >= set(range(1, totals[rel] + 1))}
    out: list[str] = []
    for rel, stamp in stamps:
        if rel in whole or stamp in out:
            continue
        out.append(stamp)
    return out


# ---------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------


def run_pipeline(
    ctx: RunContext,
    registry: AgentRegistry,
    runtime: OllamaRuntime,
    skills: SkillLibrary,
    env: SkillExecutionEnv,
    steps: list[str] | None = None,
    report=print,
    stream: bool = False,
    drift: DriftChecker | None = None,
) -> RunContext:
    steps = steps or DEFAULT_PIPELINE

    # A request that literally names a tool reaches the Router without needing
    # the Steward to raise the flag. The Router still chooses; this only opens
    # the door that three consecutive runs failed to open on their own.
    # Noise never reaches a seat. A model improvises on it; arithmetic does not.
    if intent.gibberish(ctx.objective):
        ctx.notes.append("gate: objective did not parse as language; no seat sat")
        ctx.steps.append(StepResult(
            agent="Gate", model="(none)",
            output="I didn't catch a request in that — say it again?"))
        report("  gate: not language — no seat woken")
        return ctx

    # THE TURN DEADLINE starts here, the first moment a seat could sit. A
    # sub-run arrives with its parent's deadline already set and keeps it.
    if getattr(ctx, "deadline_at", None) is None and TURN_DEADLINE > 0:
        ctx.deadline_at = time.time() + TURN_DEADLINE

    # THE LAW GATE (the operator's ruling, 2026-09-04): every run passes
    # through the law before any seat sits. The chain is walked, the
    # objective is checked against what a regex can decide, every seat is
    # handed the verdict as fact, and the record is stamped. A refusal here
    # is the same event as the injection gate's: no seat read it.
    verdict = lawgate.run(ctx.objective, getattr(env, "ground", None) or ".",
                          remote_allowed=_gitstate.remote_allowed())
    ctx.notes.append(verdict.note())
    if not verdict.ok:
        report("  " + ink.bad(verdict.note()))
        raise Refused("THE LAW: " + "; ".join(
            f"{law} -- {why}" for law, why in verdict.refusals)
            + ". No seat sat. (This gate is arithmetic over the sealed laws; "
              "the Guardian sits behind it for everything softer.)")
    ctx.law = verdict.block()
    # The court reads the ten verbatim (carried_blocks says who).
    ctx.law_full = verdict.block(full=lawgate.laws_text(
        getattr(env, "ground", None) or "."))

    # The LIBRARY, not just its keywords: that is what lets a skill's own
    # `**Says:**` phrases be seen alongside the table in intent.py.
    named = intent.names_a_tool(ctx.objective, skills)

    # AN UNKNOWN SKILL NAME IS SAID SO (the review of 2026-09-08). Sitting
    # 95: `index_workspace rebuild` -- a word shaped like a skill that is
    # not one. names_a_tool matched nothing, needs_tool was never raised,
    # the Router rested, and the door answered the PREVIOUS objective with
    # an empty flag scaffold in the delivery. Facts are read, not
    # generated: the engine answers, names the nearest real skills, and no
    # seat sits on a name that does not exist.
    if not named:
        unknown = _unknown_skill_word(ctx.objective, skills)
        if unknown:
            near = _nearest_skills(unknown, skills)
            ctx.notes.append(f"gate: `{unknown}` is not a skill here; no seat sat")
            ctx.steps.append(StepResult(
                agent="Gate", model="(none)",
                output=(f"`{unknown}` is not a skill in this ground. "
                        + (f"Nearest by name: {', '.join(near)}. " if near else "")
                        + "`/skills` lists the thirty-seven; say the one you mean.")))
            report(f"  gate: `{unknown}` is not a skill — no seat woken")
            return ctx

    # 2026-09-01: "write a note about the rack, then read it back" matched the
    # `the rack` alias and was dispatched to rack_list -- a READING skill --
    # while the front Steward was skipped as already-dispatched, so no seat
    # was left to notice. Same for "save a summary of the rack to a file" and
    # "write down what models we have". Since sitting 24 named_tool is a
    # DIRECTIVE ("call X unless plainly wrong"), so a false-positive alias
    # does not merely suggest the wrong tool, it instructs it.
    #
    # A write-shaped objective is never dispatched to a reading skill by
    # arithmetic. The flag is still raised and the Router still runs -- it is
    # simply not told to go and read something when the operator asked for a
    # file to be written. REVIEW_ONLY_SKILLS is already the maintained list of
    # what only reads, so this rule cannot drift away from the skills.
    # SITTING 69: asking ABOUT a tool ran the tool. "what does deep
    # research do?" matched the spaced keyword, dispatched, and the closing
    # seat narrated the Router's description as work completed. A question
    # about a skill is answered FROM ITS OWN MARKDOWN -- authoritative,
    # already written, and read rather than generated.
    asked = intent.asks_about_a_tool(ctx.objective, skills)
    if asked and "skill_search" in skills.keywords():
        # SAY WHICH THING DID NOT RUN. Sitting 81: this note read
        # "nothing run" while the line below set named = skill_search, so
        # the record carried "nothing run" and, four lines later, "objective
        # names `skill_search` -- Router woken directly". Both were emitted,
        # they contradict, and a reader cannot tell which path was taken.
        # `skill_search` DOES run; the skill being ASKED ABOUT does not.
        ctx.notes.append(f"intent: this ASKS ABOUT `{asked}` rather than "
                         f"asking for it -- `skill_search` reads its "
                         f"declaration; `{asked}` itself is NOT run")
        ctx.tool_args = {"content": asked.replace("_", " ")}
        ctx.named_by = "asks_about_a_tool"
        named = "skill_search"

    if named in REVIEW_ONLY_SKILLS and intent.wants_writing(ctx.objective):
        ctx.notes.append(f"intent: `{named}` set aside -- it only reads and the "
                         f"objective is write-shaped; the Router decides")
        named = ""

    # THE DECOMPOSER (the operator's chain, sitting 64). Chaining cannot
    # widen a model's window; it can only widen the material the SYSTEM
    # covers, and it does that by giving each act its OWN full window over
    # DIFFERENT material -- map, not reduce. Summarising forward is the
    # other thing, and it compounds error (DESIGN 11).
    #
    # So a plainly multi-act objective gets a ROUTE first: decompose_task
    # lays out the steps (it is forbidden to perform them), the route rides
    # in the record, and the Router then works one act at a time with the
    # steps in front of it instead of holding the whole request in one
    # head. The gate is hard to trip on purpose -- see is_big_objective.
    if not named and intent.is_big_objective(ctx.objective):
        named = "decompose_task"        # the `if named:` block below arms it
        ctx.notes.append("intent: several acts in one objective -- routed "
                         "first, then worked step by step (decompose_task)")
    elif not named and intent.wants_writing(ctx.objective):
        # A write is a decision; the Router thinks, nothing is presumed.
        ctx.flags.add("needs_tool")
        ctx.notes.append("intent: write-shaped -- Router decides the tool")
    elif not named and intent.names_a_file(ctx.objective):
        # A named file WITHOUT a write verb is a read request.
        named = "ground_read"
        ctx.notes.append(f"intent: objective names the file "
                         f"`{intent.names_a_file(ctx.objective)}`")
    elif not named and intent.names_a_folder(ctx.objective):
        # A FOLDER NAMED WITH A LISTING VERB IS A LISTING (sittings 86, 88,
        # 90: "what is in the skills dir" went to the reader three standups
        # running). The folder is checked on disk first -- a real one lists;
        # the workspace lists as the workspace; a name that is no folder
        # falls through to the reader as before.
        folder = unjail(intent.names_a_folder(ctx.objective))
        low = folder.lower()
        if low in ("workspace", "agent_workspace", "the workspace"):
            named = "list_directory"
            ctx.named_by = "names_a_folder"
            ctx.notes.append("intent: asks what is in the workspace -- list_directory")
        else:
            try:
                p = skills_inside_ground(env, folder)
                real = bool(p is not None and p.is_dir())
            except Exception:
                real = False
            if real:
                named = "ground_list"
                ctx.named_by = "names_a_folder"
                ctx.tool_args = {"content": folder}
                ctx.notes.append(f"intent: asks what is in `{folder}`, a folder in "
                                 f"the ground -- ground_list, the folder as the argument")
            else:
                ctx.notes.append(f"intent: names `{folder}` as a folder, which is "
                                 f"not one in the ground -- the reader decides")
                if intent.asks_the_ground(ctx.objective):
                    named = "semantic_search"
                    ctx.notes.append("intent: question carries a term worth looking "
                                     "up -- dispatched to the reader (asks_the_ground)")
    elif not named and intent.wants_action(ctx.objective):
        ctx.flags.add("needs_tool")
        ctx.notes.append("intent: action-shaped -- Router decides the tool")
    elif not named and intent.decomposes_to_search(ctx.objective):
        # THE DECOMPOSER (sitting 62): verb class + object class beats
        # phrase-matching. "search the ground find the warden estate!"
        # dispatched NOTHING twice in sitting 61 because no alias was
        # exact. An order to search the ground now routes by structure;
        # anything that is not an imperative falls through to conversation
        # -- the operator's balance, ruled in the same conversation.
        named = "semantic_search"
        ctx.notes.append(
            f"intent: decomposed as an order to search the ground "
            f"(payload: {intent.decomposes_to_search(ctx.objective)!r})")
    elif not named and intent.asks_the_ground(ctx.objective):
        # Sitting 60: substantive questions skipped every tool and a seat
        # invented a client narrative from nothing. A question carrying a
        # real term reaches the reader; what the ground holds (or that it
        # holds NOTHING, s61) comes back as evidence instead of a void the
        # front seat fills from its own head.
        named = "semantic_search"
        ctx.notes.append("intent: question carries a term worth looking up "
                         "-- dispatched to the reader (asks_the_ground)")
    if named:
        ctx.flags.add("needs_tool")
        ctx.named_tool = named
        # ...and do not say the OBJECTIVE named it when an earlier branch
        # chose it. One turn, one account of how the tool was picked.
        why = getattr(ctx, "named_by", "")
        ctx.notes.append(
            f"intent: `{named}` chosen by {why} -- Router woken directly"
            if why else
            f"intent: objective names `{named}` -- Router woken directly")
        # THE PAYLOAD SURVIVES RECOGNITION (operator's ruling, sitting 66).
        # Dispatch used to be keyword matching and nothing more: the moment
        # a tool was recognised, the REST of the sentence was thrown away.
        # "index_ground rebuild" became "call index_ground", and the word
        # `rebuild` had nowhere to go -- so the handler could not obey it
        # however it was written. A skill's own **Takes:** rules now read
        # the operator's words at the boundary, and the arguments travel
        # with the directive instead of being invented by a model.
        spec = skills.spec(named)
        found = skills_args_from_words(spec, ctx.objective) if spec else {}
        if found:
            ctx.tool_args = dict(found)
            shown = ", ".join(f"{k}={v!r}" for k, v in sorted(found.items()))
            ctx.notes.append(f"intent: `{named}` takes {shown} from the words")
            if not getattr(ctx, "named_by", ""):
                ctx.named_by = "the words"
        # THE WORDS AFTER THE NAME ARE THE ARGUMENT (the review of
        # 2026-09-08). "time_align the logs", "semantic_search covenant",
        # "extract_facts about manjuel": the operator typed the skill and
        # then what it should take, and five times that day qwen3.5:4b was
        # handed the name and called something else. When the objective
        # opens with the keyword itself and words follow, those words are
        # `content`, checked by the plainest arithmetic there is, and the
        # call is DECIDED (decided_call) -- the Router reads the result.
        # READING and PROMPT skills only: a writer's argument (`remember
        # two things`, `write_file notes`) is never decided by arithmetic
        # over the words -- the Router chooses, and the gate is final.
        elif (spec and not getattr(ctx, "named_by", "")
              and (named in REVIEW_ONLY_SKILLS or getattr(spec, "model", ""))
              and named not in WRITING_SKILLS):
            low = " ".join(ctx.objective.lower().split())
            if low.startswith(named + " ") and len(low) > len(named) + 1:
                rest = ctx.objective.strip()[len(named):].strip(" :-")
                if rest and "content" not in (ctx.tool_args or {}):
                    ctx.tool_args = dict(ctx.tool_args or {}, content=rest)
                    ctx.named_by = "the words"
                    ctx.notes.append(f"intent: `{named}` takes content={rest!r} "
                                     f"-- the words after the name")
        # THE NAMED FILE, CHECKED FOR VIABILITY (sitting 88, the operator:
        # "a step that checks to see if it's even viable and a returned
        # argument"). `read pipelines.md` cost five hops because the Router
        # spelled the path `ground/pipelines.md` and the engine, which had
        # read `pipelines.md` out of the operator's own words, only filled
        # an argument the seat left EMPTY. Now the engine LOOKS: if the
        # named file is a real file in the ground, its path is the argument
        # -- the floor for an empty <filepath>, and (in the tool loop) the
        # replacement for a seat's path that does not resolve. If it is not,
        # the record and the Router both say so, and nothing is guessed.
        if named == "ground_read":
            rel = unjail(intent.names_a_file(ctx.objective))
            if rel:
                ctx.named_file = rel
                try:
                    p = skills_inside_ground(env, rel)
                    ctx.named_file_ok = bool(p is not None and p.is_file())
                except Exception:
                    ctx.named_file_ok = False
                if ctx.named_file_ok:
                    ctx.tool_args.setdefault("filepath", rel)
                    ctx.notes.append(f"intent: `{rel}` is a file in the ground "
                                     f"-- handed to the Router as the path")
                else:
                    ctx.notes.append(f"intent: objective names `{rel}`, which is "
                                     f"NOT a file in the ground -- the Router "
                                     f"is told, not left to guess")

    # A FOLLOW-UP KEEPS THE DOOR (sitting 87). If the turn points back at
    # the conversation -- an anaphor, a follow-up lead, or the previous
    # delivery quoted back -- the Steward is the one seat that can answer
    # it, because the Router never sees the dialogue. So the door is not
    # skipped, and a dispatch that came from asks_the_ground (a guess that
    # the question was about the GROUND) is withdrawn; a tool the operator
    # NAMED outright still goes to the Router. The door may still raise
    # needs_tool; this only stops it being skipped.
    followup = intent.is_followup(ctx.objective, getattr(ctx, "dialogue", None))
    # A QUESTION ABOUT THIS SITTING keeps the door too (0.1.6): the story
    # rides with the door, and a reader dispatch guessed from the words
    # ("what happened?" -> semantic_search, sitting 93) is withdrawn. A
    # tool the operator named outright is still his order.
    if (getattr(ctx, "story", "") and intent.asks_the_sitting(ctx.objective)
            and not intent.names_a_tool(ctx.objective, skills)):
        if ctx.named_tool:
            ctx.notes.append(f"intent: `{ctx.named_tool}` withdrawn -- the question is "
                             f"about THIS sitting, and the door holds the story")
            ctx.named_tool = ""
            ctx.flags.discard("needs_tool")
        else:
            ctx.notes.append("intent: a question about this sitting -- the door "
                             "answers from the story")
        followup = True
    if followup and ctx.named_tool and getattr(ctx, "named_by", "") in (
            "", "asks_about_a_tool") and not intent.names_a_tool(ctx.objective, skills):
        ctx.notes.append(f"intent: `{ctx.named_tool}` withdrawn -- this turn "
                         f"points back at the conversation, and the Router "
                         f"cannot see it; the door answers")
        ctx.named_tool = ""
        ctx.flags.discard("needs_tool")
    elif followup and any("asks_the_ground" in n or "decomposed as" in n
                          for n in ctx.notes) and ctx.named_tool == "semantic_search":
        ctx.notes.append("intent: `semantic_search` withdrawn -- a follow-up, "
                         "not a question about the ground; the door answers")
        ctx.named_tool = ""
        ctx.flags.discard("needs_tool")

    # The front Steward has nothing to add to a run arithmetic already
    # dispatched -- his "I'll pass this along" was ceremony, a model call
    # spent narrating a decision nobody asked him to make. He fronts only
    # conversation and genuine judgment; on pre-named runs the Router leads.
    if ctx.named_tool and steps and not followup:
        first = steps[0]
        if (str(first).strip().lower() == "steward"
                and not getattr(first, "when", None)):
            steps = list(steps)[1:]
            ctx.notes.append("intent: front Steward skipped -- "
                             "arithmetic already dispatched")
    elif ctx.named_tool and followup:
        ctx.notes.append("intent: a follow-up -- the door is kept in front "
                         "of the Router")

    # The spine is what runs every time (post-skip). Everything else rests on
    # the rack and is pulled in when its flag is raised -- see seating.py.
    seats = seating.Seating(list(steps), seating.rack_for(registry, list(steps)))

    # Skills that fall back to the objective need it available while the run
    # is happening, not only after the transcript is written.
    try:
        env.objective = ctx.objective
        env.review_only = bool(getattr(ctx, "review_only", False))
        env.dialogue = list(getattr(ctx, "dialogue", []) or [])
        # The door to a scoped sub-run, opened for THIS context's depth.
        # Injected rather than imported: skills.py must not reach up into
        # the pipeline (the containment rule), so the pipeline hands the
        # capability down instead.
        env.sub_run = _sub_runner(ctx, registry, runtime, skills, env, report)
    except Exception:
        pass

    # Set before the first stage so `When:` can gate on it. The Morning
    # Reviewer compresses a noisy feed; with no feed it spent 40s in session 3
    # saying so, and every later stage read that non-answer.
    if ctx.feed.strip():
        markers = intent.injection_markers(ctx.feed)
        if markers:
            ctx.notes.append("hard gate: " + "; ".join(markers))
            raise Refused(
                "the pasted material was refused at the hard gate: "
                + "; ".join(markers)
                + ". No seat read it. (This gate is arithmetic; the Guardian "
                  "model sits behind it for everything softer.)")
        ctx.flags.add("has_feed")

    # Embed the source once; each stage is then scored against it. ONLY when
    # there is a feed: drift measures fidelity to SOURCE MATERIAL, and with
    # none, sitting 27 scored a reply against the words "good job stew",
    # found it "drifted", and woke the Quality Evaluator to review a
    # compliment. An objective alone is a request, not a source.
    #
    # A TOOL RESULT IS ALSO SOURCE MATERIAL, and is primed as one when it
    # arrives -- see `_prime_on_tool_result` below. That is the citation
    # check (SPEC 4.3): a claim about what a tool result SAID, measured
    # against what it actually said. It does not weaken the rule above; an
    # objective is still a request, and a tool result is still material.
    if drift is not None and ctx.feed.strip():
        drift.prime(f"{ctx.objective}\n\n{ctx.feed}")

    # `has_feed` is known before anything runs, so a `first`-anchored guard is
    # genuinely first -- it reads the material before any other seat does.
    for who in seats.summon(ctx.flags):
        ctx.notes.append(f"rack: {who}")

    i = 0
    while True:
        step = seats.advance()
        if step is None:
            break
        i += 1
        total = len(seats.queue)
        name = getattr(step, "seat", step)
        # A condition written on the STEP wins over the seat's own default --
        # that is how one seat can sit twice in a chain under different rules.
        gate = getattr(step, "when", None)
        agent = registry.get(name)
        if gate is None:
            gate = agent.when

        if gate and gate.lower() == "always":
            gate = None          # the step overrides the seat's own rest
        if gate and gate.lower() not in ctx.flags:
            ctx.steps.append(
                StepResult(agent=agent.name, model=agent.model, output="", skipped=True)
            )
            report(ink.dim(f"  [{i}/{total}] {agent.name} — resting (needs '{gate}')"))
            continue

        # OUT OF TIME: the deadline passed before this seat's turn. Not
        # seated, named in the record, and (via the recompose) in the
        # delivery. The loop keeps draining the queue so every unseated
        # seat is named, not just the first.
        left = _budget(ctx)
        if left is not None and left <= 0:
            ctx.out_of_time.append(agent.name)
            ctx.steps.append(
                StepResult(agent=agent.name, model=agent.model, output="", skipped=True)
            )
            over = time.time() - ctx.started_at
            note = (f"{agent.name} not seated: the turn's deadline passed "
                    f"({over:.0f}s of {TURN_DEADLINE:.0f}s)")
            if note not in ctx.notes:
                ctx.notes.append(note)
            report("  " + ink.warn(f"[{i}/{total}] {note}"))
            continue

        report(f"  [{i}/{total}] {ink.seat(agent.name)}  {ink.dim(agent.model)}")
        prompt = build_prompt(agent, ctx, skills)
        started = time.time()

        try:
            # The spinner runs until the FIRST token, then erases itself and
            # the seat's own words take over -- a long silence should read as
            # work, not as a hang.
            spin = ink.Spinner(f"{agent.name} thinking") if stream else None
            if spin:
                spin.start()
            first = [True]
            # SITTING 70: the operator watched `<action>ground_list</action>
            # <content>list available files in ground</content>` scroll past
            # in his terminal, between two tool lines. Control markup is the
            # seat's channel to the ENGINE (strip_control, sitting 42's
            # ruling) -- and streaming was publishing it live, one chunk at
            # a time, before any of that machinery could see it.
            #
            # A tag can be split across chunks, so this is a one-character
            # state machine rather than a regex: once a '<' is seen nothing
            # prints until its '>' arrives. The words either side still
            # stream, so the terminal stays alive.
            inside = [False]

            def sink(piece, _n=agent.name, _s=spin, _f=first, _in=inside):
                shown = []
                for ch in str(piece or ""):
                    if _in[0]:
                        if ch == ">":
                            _in[0] = False
                        continue
                    if ch == "<":
                        _in[0] = True
                        continue
                    shown.append(ch)
                text = "".join(shown)
                if not text:
                    return
                if _f[0]:
                    _f[0] = False
                    if _s:
                        _s.stop()
                    print("      ", end="")
                print(ink.body(_n, text), end="", flush=True)

            # What this seat is cleared to call, and the schemas for exactly
            # those. A seat never sees a tool it may not use.
            #
            # AND ONLY THE EXECUTOR SEES SCHEMAS AT ALL. Sitting 84 (the
            # door on llama3.2): the Steward has a May Call list, llama3.2
            # supports native tools, so it was handed schemas -- and it did
            # the natively-correct thing and CALLED one. The runtime rendered
            # that call into the estate's <action> block, and nothing ran it:
            # only the route stage executes (below). The block reached the
            # operator verbatim. phi4-mini had hidden this for three days by
            # mostly obeying "never answer with tool names". A seat that is
            # not the executor is not handed tools it cannot use; if it asks
            # for one anyway (in markup), the handoff below carries the ask
            # to the Router instead of printing it. One executor, kept.
            allowed = agent.callable_set(skills.keywords())
            executes = agent.stage == "route" or agent.key == "router"
            tools = (skills.tool_schemas(allowed)
                     if allowed and executes and runtime.supports_tools(agent.model)
                     else None)
            env.caller, env.caller_allowed = agent.name, (allowed or None)

            # THE DELIBERATION, KEPT (sitting 79, the operator's ruling).
            # A thinking seat's reasoning was collected in runtime.chat and
            # discarded unless it was needed as a salvage fallback. It is
            # evidence about WHY a seat chose what it chose -- and the
            # Router, the one seat whose choices route everything, is the
            # one that thinks. It goes to the transcript and NOWHERE ELSE:
            # sitting 47's ruling that thinking is never displayed and never
            # reaches a later seat is untouched.
            thoughts: list[str] = []
            # The seat as it sits THIS call: its own prompt plus the law
            # and the standing in the system role (carried_blocks). The
            # registry's declaration is untouched.
            seat, carried = _seat_for_call(agent, ctx)
            # THE DECIDED CALL (sitting 91, 2026-09-07; SPEC 4.2's open line
            # since 09-04). When the engine has the TOOL and the ARGUMENT --
            # a folder checked on disk, a file checked on disk -- the Router
            # is not asked to choose: sittings 86, 88, 90 and 91 asked it,
            # and four times running qwen3.5:4b was told "call ground_list"
            # and called skill_report. Arithmetic decided; a 4B overrode it.
            # So the call is written by the engine, in the Router's own
            # markup, and the loop below runs it exactly as if the Router
            # had emitted it -- the dedup, the gates and the record all see
            # the same shape. The Router then sits ONCE to read the result.
            decided = bool(executes and decided_call(ctx))
            if decided:
                output = decided_call(ctx)
                note = (f"the call was decided by arithmetic "
                        f"({ctx.named_by or 'the objective'}): `{ctx.named_tool}` "
                        f"runs first; the Router reads the result, it does not choose")
                ctx.notes.append(note)
                report("      " + ink.dim(note))
            else:
                output = runtime.chat(_within_deadline(seat, ctx), prompt,
                                      stream_to=sink if stream else None,
                                      tools=tools,
                                      think_to=thoughts.append)
            # THE RULING LOOP (2026-09-07). A seat that thought and did not
            # rule is pressed, bounded. Never the executor: its loop is the
            # tool loop below, and a Router that thinks past its budget is
            # a different fault with its own stroke.
            if (output or "").startswith(SALVAGE_MARK) and not executes:
                output = _press_for_ruling(seat, prompt, output, thoughts, runtime,
                                           sink if stream else None, ctx, report,
                                           started)
            if spin:
                spin.stop()
            if stream:
                print()
            # Session 5c: a seat returned "" and the chain delivered silence
            # for 56 seconds without ever saying anything had gone wrong. An
            # empty seat is a fault, and must read as one.
            if not (output or "").strip():
                note = f"{agent.name} returned an empty reply ({time.time()-started:.0f}s)"
                ctx.notes.append(note)
                report(f"  !! {note}")
        except RuntimeError_ as exc:
            step = StepResult(
                agent=agent.name,
                model=agent.model,
                output="",
                elapsed=time.time() - started,
                prompt=prompt,
                error=str(exc),
            )
            ctx.steps.append(step)
            _handle_failure(agent, exc, report)
            continue

        # A gate that says PASS keeps the draft as it stands -- there is no
        # point paying to regenerate text the gate has no changes to make to.
        if agent.key == "quality evaluator" and output.strip().upper().startswith("PASS"):
            kept = ctx.last_output()
            report("      " + ink.good("verdict: PASS — draft kept unchanged"))
            ctx.steps.append(
                StepResult(agent=agent.name, model=agent.model, output=kept,
                           elapsed=time.time() - started, prompt=prompt)
            )
            continue

        # A guard's verdict decides whether the run continues at all.
        if agent.stage == "guard":
            ok, reason = read_verdict(output)
            ctx.steps.append(
                StepResult(agent=agent.name, model=agent.model,
                           output=("SAFE" if ok else f"UNSAFE: {reason}"),
                           elapsed=time.time() - started, prompt=prompt)
            )
            if ok:
                report("      " + ink.good("verdict: SAFE"))
                continue
            report("      " + ink.bad(f"verdict: REFUSED — {reason}"))
            if agent.on_fail == "skip":
                report("      (on-fail: skip -- continuing despite refusal)")
                continue
            raise Refused(reason)

        tool_calls: list[str] = []
        tool_results: list[str] = []
        # What the tools RETURNED this stage, kept apart from what the seat
        # SAID about it -- so a refused claim below can take the testimony
        # and leave the evidence (sitting 88: the write-claim check threw
        # five real search results out with the Router's claim, and the
        # court ruled on nothing).
        evidence = ""

        # A routing stage may call several skills in turn, feeding each result
        # back before deciding again -- bounded, so it cannot spin.
        if agent.stage == "route" or agent.key == "router":
            results: list[str] = []
            # THE DEDUP (sitting 63). "remember the operator rules" staged the
            # SAME rule three times in one turn: the Router emitted the action,
            # the follow-up asked whether another skill was needed, and it
            # answered by repeating itself. The cap bounded the damage at 4 and
            # was doing its job -- but a bound is not a rule. An identical call
            # is now REFUSED rather than re-run, which is what lets the cap
            # rise to 5 without buying more duplicates: the extra hop is for
            # genuinely different work. This is arithmetic, and it covers every
            # skill -- a doubled write or a doubled commit dies here too.
            # PER RUN, NOT PER SEATING (TASKS, built 2026-09-10). This was
            # `{}` here, so a run that seats a tool-capable seat twice started
            # empty the second time and could repeat a call. Measured across
            # the 235 runs with tools since the dedup landed: 18 ran a skill
            # more than once, including a doubled `git_commit` -- the exact
            # thing the comment above says this exists to kill.
            ran: dict[tuple, str] = ctx.ran_calls
            repeats = 0
            for hop in range(MAX_TOOL_STEPS):
                action, args = extract_tool_call(output)
                if not action:
                    break
                # After a DECIDED call the Router reads; it does not pick
                # another tool. Sitting 91's Router would have called
                # skill_report on the follow-up too. Its reply is kept as
                # words only when it is words; a second call is set aside
                # and the result stands on its own.
                if decided and hop >= 1:
                    note = (f"{agent.name} asked for `{action}` after the decided "
                            f"call ran -- set aside; the result stands on its own")
                    ctx.notes.append(note)
                    report("      " + ink.warn(note))
                    output = ""
                    break

                # Arguments the OPERATOR's own words carried, for the skill
                # he named. They fill only what the seat left empty: a model
                # that supplied a value is answering a question it can see,
                # and this is a floor under it, not an override of it. Done
                # BEFORE the signature so the dedup compares the call as it
                # will actually be made.
                if action == ctx.named_tool:
                    for k, v in (getattr(ctx, "tool_args", None) or {}).items():
                        if not str(args.get(k) or "").strip():
                            args[k] = v
                    # THE OPERATOR'S REAL FILE OUTRANKS A PATH THAT DOES
                    # NOT RESOLVE (sitting 88). The seat's spelling is
                    # testimony; the file on disk is fact (LAW 5). Only
                    # when the seat's path is NOT a file and the named one
                    # IS -- a seat that named a different real file is
                    # answering a question it can see, and is left alone.
                    theirs = str(args.get("filepath") or "").strip()
                    if (getattr(ctx, "named_file_ok", None) and theirs
                            and unjail(theirs).lower() != ctx.named_file.lower()):
                        try:
                            tp = skills_inside_ground(env, theirs)
                            resolves = bool(tp is not None and tp.is_file())
                        except Exception:
                            resolves = False
                        if not resolves:
                            note = (f"{agent.name}'s path `{theirs}` is not a "
                                    f"file in the ground; the operator named "
                                    f"`{ctx.named_file}`, which is -- used")
                            if note not in ctx.notes:
                                ctx.notes.append(note)
                            report("      " + ink.warn(note))
                            args["filepath"] = ctx.named_file

                # THE SIGNATURE IS THE DECLARED CALL, NOT THE EMITTED ONE.
                # Sitting 77: the Router called `list_directory` twice in one
                # turn and both ran, burning 2 of 5 hops on byte-identical
                # output. The dedup had keyed on whatever the model emitted,
                # so a field the skill DOES NOT HAVE was enough to make two
                # identical calls look different -- and list_directory
                # declares `Parameters Needed: None` and its handler reads no
                # args at all. Two calls to it are the same work by
                # definition. Keying on the skill's OWN declaration closes
                # that: an undeclared argument cannot vary a signature,
                # because it was never part of the call.
                _spec = skills.spec(action)
                if _spec is None:
                    keyed = dict(args or {})      # unknown skill: judge it whole
                else:
                    declared = ({a for a, _ in (_spec.path_args or ())}
                                | {a for _, a in (_spec.takes or ())}
                                | _spec.declared_args)
                    keyed = {k: v for k, v in (args or {}).items()
                             if k in declared}
                sig = (action, repr(sorted(keyed.items())))
                fresh = sig not in ran
                if not fresh:
                    repeats += 1
                    note = (f"{agent.name} called `{action}` again with the "
                            f"same arguments; it ran once and was not re-run")
                    if note not in ctx.notes:
                        ctx.notes.append(note)
                    report("      " + ink.warn(
                        f"dedup: {action} already ran this turn"))
                    # Told once. A seat that repeats itself AFTER being told is
                    # spinning, and the results in hand are what it has.
                    if repeats > 1:
                        break
                    results.append(
                        f"Tool NOT re-run: {action}\n\n"
                        f"IT ALREADY RAN THIS TURN with these exact arguments "
                        f"and its result stands above. Calling it again would "
                        f"repeat the work, not add to it. Call a DIFFERENT "
                        f"skill if the objective still needs one, or write the "
                        f"prose answer with no XML.")
                else:
                    # Arguments the OPERATOR's own words carried, for the
                    # (the operator's arguments were filled in above the
                    # signature, so the dedup sees the call as it is made)
                    report("      " + ink.dim(f"→ skill: {action}"))
                    result = skills.execute(action, args, env)
                    tool_calls.append(action)
                    ran[sig] = result
                    # A WRITE REOPENS THE READS. The ground has moved, so a
                    # read taken before it may legitimately be taken again --
                    # `git_status`, `git_commit`, `git_status` is three real
                    # facts, and it is in the measured list above. The WRITES
                    # stay, so a doubled commit is still refused by its own
                    # signature. Which skills write is WRITING_SKILLS' answer,
                    # already imported here; a second list would drift from it.
                    reopen_reads(ran, action)
                    # A read that came back in PART is stamped as it
                    # happens (note_partial_read); the recompose carries
                    # it into the delivery.
                    note_partial_read(action, result, ctx, report)
                    # A gate firing is an OBSERVED event, not a judgement: it
                    # goes in the record beside the stage counts, machine-
                    # emitted, so guardrail performance is a measured quantity
                    # rather than something the operator only learns by
                    # catching it himself.
                    if GATE_MARK in result:
                        ctx.notes.append(f"LAW 8 gate refused {action}: "
                                         f"a path resolved outside its jail")
                        report("      " + ink.warn(f"LAW 8 refused {action}"))
                    # Sitting 40: an errored read was narrated as "successfully
                    # opened" and the file's contents were invented. A failure
                    # wears a sign no seat can misread or quietly omit.
                    tool_results.append(str(result))

                    # THE CITATION CHECK (SPEC 4.3). A tool result is source
                    # material -- text handed to a seat, which the seat then
                    # speaks about -- so from here the stages after it are
                    # measured against WHAT THE TOOL ACTUALLY SAID, not
                    # against the objective. A failed result is never primed:
                    # scoring a seat's words against "Error: no such file"
                    # would call every honest report of a failure a drift.
                    if (drift is not None
                            and not result.lstrip().startswith(
                                ("Error", "Refused", "Cannot"))):
                        drift.prime(str(result))

                    if result.lstrip().startswith(("Error", "Refused", "Cannot")):
                        # Recorded as a FACT the moment it happens, so the
                        # recompose does not depend on any seat remembering
                        # it (sittings 66 and 68).
                        ctx.failures.append(
                            (action, " ".join(result.split())[:160]))
                        results.append(
                            f"Tool attempted: {action}\n\n"
                            f"THIS TOOL FAILED — NOTHING WAS DONE. Do not report "
                            f"success, contents, or findings from it. The error:\n"
                            f"{result}")
                    else:
                        results.append(f"Tool executed: {action}\n\nResult:\n{result}")

                if hop == MAX_TOOL_STEPS - 1:
                    report(f"      (tool loop capped at {MAX_TOOL_STEPS})")
                    break
                try:
                    # Only the results and the bare keyword list. Re-sending
                    # the whole router prompt here doubled the token cost of
                    # every skill call for no added information.
                    # The routing manifest truncates every description to
                    # ROUTING_DESC_CHARS, so a seat is told WHAT exists and
                    # never HOW to use it: 31 bodies are ~4,000 tokens and
                    # were rightly left out. But ONE body is 70-135 tokens.
                    # The skill just called gets its own markdown back here,
                    # so a second hop can correct a misuse instead of
                    # repeating it -- selective, not wholesale.
                    used = skills.spec(action) if fresh else None
                    manual = (f"\n\n## How `{action}` works\n{used.body.strip()}\n"
                              if used and not used.is_prompt_skill else "")
                    if decided:
                        follow = (
                            f"Objective: {ctx.objective.strip()}\n\n"
                            "## Results So Far\n" + "\n\n".join(results) + "\n\n"
                            "The tool the objective asked for has run and its result "
                            "is above. Write the plain answer FROM THAT RESULT, in "
                            "words, with no XML and no other tool. Report only what "
                            "the result shows."
                        )
                    else:
                        follow = (
                            f"Objective: {ctx.objective.strip()}\n\n"
                            "## Results So Far\n" + "\n\n".join(results) + manual + "\n\n"
                            f"Skills available: "
                            f"{', '.join(sorted(allowed or skills.keywords())) or '(none)'}\n\n"
                            "If the objective still needs another skill, emit the XML "
                            "block for it. Otherwise write the prose answer, with no XML."
                        )
                    # The follow-up hops think too, and a tool loop's
                    # deliberation is where a wrong route is decided.
                    output = runtime.chat(_within_deadline(seat, ctx), follow,
                                          stream_to=sink if stream else None,
                                          tools=tools,
                                          think_to=thoughts.append)
                    if stream:
                        print()
                except RuntimeError_ as exc:
                    report(f"      ! follow-up failed: {exc}")
                    break
            # THE CITATION-CHECK (named sitting 61, built 2026-09-02).
            # The Router lifted a filename out of one result's snippet and
            # reported it as a hit carrying another result's cosine; from
            # that misread it built "'warden' relates to jesster" and the
            # closer delivered it. The results ARE the exhaustive list of
            # (path, cosine) this turn, so a cited pair either appears in
            # them or does not. When it does not, the prose is withheld and
            # the results stand on their own -- facts first, the
            # rack_report shape, LAW 5 at the boundary.
            if (results and "semantic_search" in tool_calls
                    and output.strip() and not extract_tool_call(output)[0]):
                bogus = bogus_citations("\n\n".join(results), output)
                if bogus:
                    shown = "; ".join(f"`{p}` at {s}" for p, s in bogus)
                    note = (f"{agent.name} cited {shown} as a search result; "
                            f"the search returned no such result this turn")
                    if note not in ctx.notes:
                        ctx.notes.append(note)
                    report("      " + ink.warn(note))
                    output = (
                        f"REFUSED — the prose cited {shown} as a search "
                        f"result, and the results above are the exhaustive "
                        f"list of what this turn's search returned. The "
                        f"citation is unsupported, so the prose is not "
                        f"delivered; the results stand on their own (LAW 5: "
                        f"testimony is never fact)."
                    )

            if results:
                evidence = "\n\n".join(results)
                # THE SEAM (sitting 63). A `memory.md` read came back with the
                # file's own headings demoted to h5 -- and the Router's summary
                # ABOVE it, "##### Rules in memory.md", demoted to h5 too. In
                # the record the two were indistinguishable, so a paraphrase
                # read as part of the file. The fix is not more demotion: it is
                # a named boundary. What the tool returned is a fact; what the
                # seat says about it is testimony (LAW 5), and the record now
                # says which is which at the line where they meet.
                said = output if not extract_tool_call(output)[0] else ""
                output = "\n\n".join(results) + (
                    f"\n\n--- {agent.name} reading the above (testimony, "
                    f"not tool output) ---\n\n{said}" if said.strip() else ""
                )

        # Something other than talk actually happened. The closing seat waits
        # on this, so a plain question is answered once and not summarised
        # back to the person who just read it.
        # TRIED AND REVERTED, 2026-09-02. Sitting 69 showed the closing
        # seat narrating a Router's DESCRIPTION as completed work, so I
        # dropped `route` from this test -- a router that routed nothing
        # did nothing. Seven strokes went red across four unrelated areas:
        # `worked` is what seats the closing Steward, and half the estate's
        # ordinary conversation runs through a Router that calls no tool.
        # The blast radius was the answer: this flag means "the run has
        # something to report", not "a tool ran".
        #
        # The real fault was the closer being left to GUESS whether work
        # happened. It is now TOLD, as fact, below -- the same shape as the
        # clock: a harness-emitted observation, not a flag reinterpreted.
        if tool_calls or agent.stage in ("route", "transform") and agent.key != "steward":
            ctx.flags.add("worked")

        # THE DOOR'S HANDOFF (sitting 84). A seat that is NOT the executor
        # and answers with an <action> block is a seat asking for a tool. The
        # ask is carried, not printed: needs_tool rises, the skill it named
        # becomes the Router's named tool (with whatever arguments it gave,
        # as a floor), and the markup leaves the text. The Router applies its
        # own clearance -- this is a request, never an execution, so a door
        # naming a skill it may not call still gets a refusal from the seat
        # that holds the gate, not a silent run. Model-agnostic on purpose:
        # whichever model sits at the door, its tool call is not lost.
        if not (agent.stage == "route" or agent.key == "router"):
            asked_for, asked_args = extract_tool_call(output)
            if asked_for and "worked" in ctx.flags:
                # THE CLOSING SEAT (sitting 84, 09:19). The work is DONE and
                # the seat that must report it answered with another tool
                # call -- llama3.2's JSON shape, twice. A call after the
                # work is not a request, it is a seat that said nothing.
                # The last real output (the Router's reading of the tool
                # result) stands as the delivery, and the record says why.
                note = (f"{agent.name} answered with a tool call "
                        f"(`{asked_for}`) after the work was already done "
                        f"-- discarded; the last real output stands")
                if note not in ctx.notes:
                    ctx.notes.append(note)
                report("      " + ink.warn(note))
                output = ctx.last_output() or ""
                asked_for = None
            if asked_for:
                if asked_for in skills.keywords():
                    ctx.flags.add("needs_tool")
                    if not ctx.named_tool:
                        ctx.named_tool = asked_for
                        ctx.named_by = f"{agent.name} asked for it in markup"
                        if asked_args:
                            ctx.tool_args = dict(asked_args)
                    note = (f"{agent.name} answered with a tool call "
                            f"(`{asked_for}`) instead of words -- carried to "
                            f"the Router as needs_tool, not printed")
                else:
                    note = (f"{agent.name} answered with a tool call to "
                            f"`{asked_for}`, which is not a skill -- dropped, "
                            f"nothing run")
                if note not in ctx.notes:
                    ctx.notes.append(note)
                report("      " + ink.warn(note))
                bare = _ACTION_BLOCK_RE.sub("", output).strip()
                output = bare or (f"Passing that along -- the Router has "
                                  f"`{asked_for}`." if asked_for in skills.keywords()
                                  else "")

        # THE SCAFFOLD PARROT (sitting 85, 2026-09-04, run 8). The closing
        # Steward on llama3.2 answered with its own prompt's dialogue block:
        # "##### Conversation so far / (recalled, 4m ago) operator: ..." --
        # the whole thread, verbatim, delivered as the answer. Sitting 46
        # was the same fault in the front seat. The prompt already indents
        # and labels the block; no wording stops a 3B from copying what it
        # was shown. So the ENGINE refuses it: an output that carries the
        # conversation scaffold's own heading or its recalled-turn labels
        # is a seat reciting, not answering. The last real output stands
        # (after work) or the seat is recorded as having said nothing.
        if _SCAFFOLD_RE.match(output or ""):
            # KEEP THE EVIDENCE. The discarded words go in the record, so a
            # wrong discard (sitting 87 had two) can be seen for what it was.
            kept = " ".join((output or "").split())[:300]
            note = (f"{agent.name} recited the conversation scaffold instead "
                    f"of answering -- discarded; it said: {kept!r}")
            if note not in ctx.notes:
                ctx.notes.append(note)
            report("      " + ink.warn(note.split('; it said')[0]))
            output = ctx.last_output() if "worked" in ctx.flags else ""

        # Any seat may raise a flag; flags gate `When:` steps later in the run.
        raised = read_flags(output)
        if raised:
            ctx.flags |= raised
            report("      " + ink.dim(f"flags raised: {', '.join(sorted(raised))}"))

        # The flag has been read; close the channel before the text reaches a
        # transcript, a delivery, or the thread. A seat whose whole reply was
        # markup said nothing, and that is a fault with a name -- not an empty
        # string handed to the operator as an answer.
        spoken = strip_control(output)
        if output.strip() and not spoken:
            note = (f"{agent.name} replied with control markup and no words "
                    f"({', '.join(sorted(raised)) or 'no flags'} raised)")
            if note not in ctx.notes:
                ctx.notes.append(note)
            report("      " + ink.warn(note))
        output = spoken

        # THE REVIEW -> REPEAT EDGE (the operator's chain, sitting 64).
        # The Evaluator could say a draft was WRONG (return it corrected) but
        # never that it was UNFINISHED, so a critique naming missing work had
        # nowhere to go and the run ended on an answer sourced from nothing.
        # `NEEDS: <thing>` sends it back through the Router ONCE, with the
        # critique and the real prior results in the record before it --
        # EVIDENCE carried forward, never a summary. Bounded by the same
        # (seat, flag) arithmetic that stops a flag looping: a second pass
        # over a compressed view is exactly the error-compounding this estate
        # is built to avoid (DESIGN 11).
        if output.strip().upper().startswith("NEEDS:"):
            want = output.strip()[6:].strip().rstrip(".") or "the missing work"
            if seats.repeat("Router"):
                ctx.flags.add("needs_tool")
                note = (f"{agent.name} judged the work unfinished and named "
                        f"what is missing: {want}. One more pass.")
                output = (f"UNFINISHED — {want}. Sent back to the Router for "
                          f"one more pass; the results already in this record "
                          f"stand and are not re-derived.")
            else:
                note = (f"{agent.name} asked for another pass ({want}) and one "
                        f"has already been spent; the work stands as it is")
                output = (f"UNFINISHED — {want}. A repeat was already spent "
                          f"this run, so this is the answer as it stands, "
                          f"with the gap named rather than filled.")
            if note not in ctx.notes:
                ctx.notes.append(note)
            report("      " + ink.warn(note))

        # THE CLAIM-CHECK (agreed 2026-09-01, built 2026-09-02).
        #
        # s56: "Can you read me the poem?" -- one stage, no flags, no tool ran.
        # The seat composed a new poem and wrote "Here is the content of
        # `poem_about_jesster.md`:" above it. The file existed and said
        # something else. The operator caught it, which is the part that must
        # not be the mechanism. s58 proves the variable was dispatch, not
        # model size: the SAME model said "not found" correctly once a read
        # actually ran. So the fix is the guard, not the rack.
        #
        # Both conditions, THIS TURN only: the output claims to be showing a
        # file's contents, AND no reading skill ran. The claim is refused
        # rather than delivered -- same shape as THIS TOOL FAILED and the
        # LAW 8 note: a fault named in the record, machine-emitted, so it is
        # a measured quantity and not something the operator must catch.
        # THE WRITE-CLAIM CHECK (sitting 70), the claim-check's sibling.
        # Its closer said "Yesterday, I compiled a poem about autumn, saved
        # it as 'poem.txt' in the Research folder, and successfully read it
        # back to you" -- an invented yesterday, an invented file, an
        # invented reading. The claim-check wants a CONTENTS claim and this
        # claimed a SAVE, so nothing saw it. Same arithmetic, new place: a
        # seat says a file was written; the turn's tool calls say whether
        # any writer ran.
        wrote = intent.claims_wrote_a_file(output)
        if wrote:
            ran_this_turn = {k for s in ctx.steps for k in (s.tool_calls or ())}
            ran_this_turn |= set(tool_calls)
            if not (ran_this_turn & WRITING_SKILLS):
                note = (f"{agent.name} said it wrote `{wrote}`; no writing "
                        f"skill ran this turn")
                if note not in ctx.notes:
                    ctx.notes.append(note)
                report("      " + ink.warn(note))
                output = _refuse_testimony(agent, evidence, (
                    f"REFUSED — an unsupported claim that `{wrote}` was "
                    f"written.\n\n{agent.name} said so, and no writing skill "
                    f"ran this turn: nothing was saved, created or committed. "
                    f"The claim is not shown because nothing supports it "
                    f"(LAW 5: testimony is never fact). This proves it "
                    f"UNSUPPORTED, not false — ask again and let a write run."))

        claimed = intent.claims_file_contents(output)
        if claimed:
            read_this_turn = {k for s in ctx.steps for k in (s.tool_calls or ())}
            read_this_turn |= set(tool_calls)
            if not (read_this_turn & REVIEW_ONLY_SKILLS):
                note = (f"{agent.name} claimed the contents of `{claimed}`; "
                        f"no read ran this turn")
                if note not in ctx.notes:
                    ctx.notes.append(note)
                report("      " + ink.warn(note))
                output = _refuse_testimony(agent, evidence, (
                    f"REFUSED — an unsupported claim about `{claimed}`.\n\n"
                    f"{agent.name} presented that file's contents, and no "
                    f"reading skill ran this turn. The claim is not shown "
                    f"because nothing supports it (LAW 5: testimony is never "
                    f"fact). This proves the claim UNSUPPORTED, not false — "
                    f"ask again and let a read run."))

        # The coder's code lands on disk, deterministically. The seat only
        # DECLARES <filepath> + a fenced block; the harness does the writing
        # (inside the workspace jail) and raises `review` so the Quality
        # Evaluator reads the code that was actually saved. Code that stayed
        # in a transcript was the operator's complaint: written, then lost.
        if agent.key == "expert coder" and output.strip():
            saved = land_code(output, env, ctx)
            if saved:
                ctx.flags.add("review")
                report("      " + ink.dim(f"code landed: {saved}"))

        # Sitting 31: "heloo stewy" raised `technical` and woke the coder on
        # a greeting. The flag is testimony; the objective is fact -- when a
        # short objective carries nothing code-shaped, the flag is noted and
        # set aside rather than obeyed.
        if ("technical" in ctx.flags
                and len(ctx.objective) < 60
                and not _CODEISH.search(ctx.objective)):
            ctx.flags.discard("technical")
            note = "technical flag set aside: nothing code-shaped in the objective"
            if note not in ctx.notes:
                ctx.notes.append(note)

        # The needs_tool set-aside gate stood here from sitting 48 until
        # 2026-09-01, when the operator ruled it out. Kept as the record of
        # why, per LAW 1 -- corrections append, they do not erase.
        #
        # It discarded needs_tool when the OBJECTIVE looked untool-shaped,
        # using intent.names_a_tool as its evidence. Its cost was ~10s of
        # Router deliberation on a greeting. Its price was correctness: on
        # "What's the condition of the dir" that same lookup missed, the
        # Steward read the roster and raised the flag correctly, and the gate
        # then cited its own miss as grounds to throw the flag away. The
        # Router never sat, no tool ran, and the delivery was the seat's own
        # markup. It had done the same to "try speaking ..." a sitting
        # earlier. A gate whose evidence is the failure it is meant to catch
        # cannot be tuned into correctness.
        #
        # OPERATOR RULING, 2026-09-01: a raised needs_tool always reaches the
        # Router. Seconds on a greeting are cheaper than a tool that never
        # runs. The `technical` set-aside above is untouched -- it answers a
        # different failure (s31, a typo'd greeting waking the coder) and
        # _CODEISH is not the same lookup that routes.

        # A flag raised now may call a racked seat. Summoning happens HERE,
        # after the step that raised it, so the seat lands in the same run
        # rather than the next one.
        for who in seats.summon(ctx.flags):
            ctx.notes.append(f"rack: {who}")
            report("      " + ink.dim(f"rack: summoning {who}"))

        # Advisory measurement: did this stage wander from the source?
        d_score = d_flag = None
        if drift is not None and agent.stage in ("transform", "gate", "deliver"):
            ds = drift.score(output)
            if ds is None:
                note = drift.note_once("drift: not scored this run (no usable source)")
                if note:
                    report(f"      {note}")
                    ctx.notes.append(note)
            elif ds.reason:
                # Say so once. Silence would read as a pass.
                note = drift.note_once(ds.stamp())
                if note:
                    report(f"      {note}")
                    ctx.notes.append(note)
            else:
                d_score, d_flag = ds.score, not ds.ok
                if not ds.ok:
                    report("      " + ink.warn(f"{ds.stamp()}") +
                           ink.dim("  (advisory — nothing was changed)"))
                    ctx.flags.add("drifted")

        ctx.steps.append(
            StepResult(
                agent=agent.name,
                model=agent.model,
                output=output,
                elapsed=time.time() - started,
                # THE RECORD KEEPS WHAT RODE IN THE SYSTEM ROLE. The prompts
                # companion (transcript.py) shows this field; the law and
                # the standing must stay visible there, or a later reader
                # cannot see the seat was told.
                prompt=(prompt + "\n\n[carried in the system message, beside "
                        "the seat's own prompt]\n" + carried) if carried else prompt,
                tool_calls=tool_calls,
                tool_results=tool_results,
                # JOINED WITHOUT SEPARATORS. Sitting 80: this was
                # "\n".join(...) and the transcripts came out one token per
                # line -- 7,212 characters of the Router's deliberation
                # rendered as a column of single words, captured and
                # unreadable. The NON-streaming path hands back one whole
                # field, where a newline join looks right; the STREAMING
                # path appends per token, and the fragments already carry
                # their own spacing. I built the streaming path and never
                # opened a rendered transcript.
                thinking="".join(thoughts).strip(),
                drift=d_score,
                drifted=bool(d_flag),
            )
        )

    recompose(ctx, report)
    return ctx


# A scoped sub-run gets its OWN window over its OWN material -- the map
# half of the chain (DESIGN 14.9), and the only honest way to cover more
# ground than one context holds. Both numbers are bounds, not preferences:
# a sub-task that can start a sub-task is an unbounded tree.
SUB_DEPTH_MAX = 1
SUB_RUNS_MAX = 3
SUB_PIPELINE = ["Router"]


def _sub_runner(parent: RunContext, registry, runtime, skills, env, report):
    """Build the `sub_run` capability for one context's depth.

    THE OPERATOR, sitting 68: "scoped subagents ... run, deliver output,
    then be reviewed and delivered on." The estate already had the seed --
    an `@`-addressed seat whose exchange went to the transcript and never
    into the shared dialogue -- and this generalises it: a sub-objective
    runs on its own RunContext with its own full window, and only its
    RESULT comes back.

    Two rules that are not negotiable:

    BOUNDED. Depth 1 and at most three per turn. A sub-task that could
    start a sub-task is a tree with no floor (LAW 7).

    ITS FAILURES ARE THE PARENT'S. Anything that failed down there is
    lifted into the parent's record, so the recompose above carries it into
    the delivery. A sub-run that could fail quietly would be a way to
    launder a failure out of the answer, which is the exact fault the
    recompose was built for.
    """
    def sub_run(objective: str) -> str:
        objective = " ".join((objective or "").split())
        if not objective:
            return "Error: a sub-task needs an objective to work on."
        if getattr(parent, "depth", 0) >= SUB_DEPTH_MAX:
            return (f"Refused: a sub-task may not start another sub-task "
                    f"(depth {SUB_DEPTH_MAX}). An unbounded tree of them is "
                    f"exactly what LAW 7 forbids. Do this work here.")
        if len(parent.sub_runs) >= SUB_RUNS_MAX:
            return (f"Refused: {SUB_RUNS_MAX} sub-tasks have already run this "
                    f"turn, which is the cap. Answer with what they returned.")

        child = RunContext(objective=objective,
                           method=getattr(parent, "method", ""),
                           depth=getattr(parent, "depth", 0) + 1)
        child.deadline_at = getattr(parent, "deadline_at", None)
        child.flags.add("needs_tool")
        report("      " + ink.dim(f"→ sub-task: {objective[:60]}"))

        # The env is SHARED, and run_pipeline writes its own objective and
        # dialogue into it. Put the parent's back afterwards or the rest of
        # this turn works on the sub-task's words.
        keep = (getattr(env, "objective", ""), list(getattr(env, "dialogue", []) or []),
                getattr(env, "sub_run", None))
        try:
            run_pipeline(child, registry, runtime, skills, env,
                         steps=list(SUB_PIPELINE), report=lambda m: None)
        except Exception as exc:
            parent.failures.append(("sub-task", f"{type(exc).__name__}: {exc}"))
            return f"The sub-task failed: {type(exc).__name__}: {exc}"
        finally:
            try:
                env.objective, env.dialogue, env.sub_run = keep
            except Exception:
                pass

        # Whatever failed down there failed in this run.
        parent.failures.extend(child.failures)
        parent.out_of_time.extend(f"{n} (sub-task)" for n in child.out_of_time)
        parent.sub_runs.append((objective, child))
        ran = [k for s in child.steps for k in (s.tool_calls or ())]
        answer = (child.last_output() or "").strip() or "(the sub-task said nothing)"
        return (f"Sub-task: {objective}\n"
                f"Tools it ran: {', '.join(ran) if ran else 'none'}\n"
                f"--- what it returned (another seat's words, LAW 5) ---\n"
                f"{answer}")

    return sub_run


def reopen_reads(ran: dict, action: str) -> int:
    """A write reopens the reads. Returns how many were dropped.

    When a writing skill runs the ground has moved, so a read taken before it
    may legitimately be taken again -- `git_status`, `git_commit`,
    `git_status` is three real facts, and it is in the measured record. The
    WRITES stay in the set, so a doubled commit is still refused by its own
    signature.

    Which skills write is `WRITING_SKILLS`' answer, not a second list here.
    A non-write drops nothing, so this is safe to call on every call.
    """
    if action not in WRITING_SKILLS:
        return 0
    stale = [k for k in ran if k[0] not in WRITING_SKILLS]
    for k in stale:
        del ran[k]
    return len(stale)


def recompose(ctx: RunContext, report=print) -> bool:
    """Put what actually happened back into what is delivered.

    THE OPERATOR'S RULING, sitting 68: "that's the second time in a row
    we've proven we need to recompose and then deliver."

      s66  the Quartermaster read its own numbers -- 15.0GB of ~15.0GB,
           ~0.0 headroom -- and called the card "comfortable and
           functioning optimally".
      s68  two tools failed, one of them a 326-second timeout wearing a
           THIS TOOL FAILED banner, and the closing seat delivered
           "Everything is as it should be. No new issues or concerns."

    Both are the same fault and NEITHER IS INVENTION: nothing false was
    made up. Failure was OMITTED, which the claim-check cannot catch
    because nothing was cited and the citation-check cannot catch because
    no result was quoted.

    So the recompose is NOT another seat. A model summarising a record and
    dropping the failures is the disease; a second model summarising would
    be more of it. This is arithmetic: if anything failed this run, the
    delivery carries the list, appended from what was recorded AS IT
    HAPPENED. No judgement about whether the seat mentioned it, no reading
    of its prose for all-clear language -- the facts simply travel with the
    answer, every time, and a seat that did mention them is merely
    corroborated.
    """
    fails = list(getattr(ctx, "failures", ()) or [])
    partial = unread_parts(ctx)
    late = list(getattr(ctx, "out_of_time", ()) or [])
    # A NUMBER NO TOOL RETURNED (SPEC 4.7, built 2026-09-10). The same
    # arithmetic as the lists below, on the other half of the fault: those
    # catch what was OMITTED, this catches what was INVENTED. Sitting 94's
    # brief said "master@0917c6d4a, clean at open" over facts reading f1da1a4
    # DIRTY; 2026-09-09's standup had the door report "37 markdown files,
    # ranging from 300 to 1200 bytes in size" with 300 and 1200 in no tool
    # result that run. The check existed and ran in ONE place, /brief, never
    # on an ordinary turn.
    #
    # ONLY WHEN A TOOL RAN. With no tool results there is nothing to check
    # against, and stamping a plain conversational answer would be sitting
    # 27's compliment-drift again.
    made_up = []
    # FROM THE STEPS, which is where tool results live. This read `ctx`
    # directly and got nothing: `tool_results` is a StepResult field ("what
    # the tools RETURNED at this seat"), not a RunContext one, so the check
    # silently never ran in a live turn. The stroke passed because it SET
    # that field on the context -- a test proving its own fixture. Found
    # 2026-09-10 when the standup caught an invented "196 to 1,200 bytes"
    # and the stamp was absent from the delivery. Same read the standup
    # uses (tests/standup.py:297), so the two cannot disagree.
    results = [str(r) for st in ctx.steps
               for r in (getattr(st, "tool_results", None) or [])
               if str(r).strip()]
    if results:
        from .intent import unsourced_numbers
        spoken = next((s.output for s in reversed(ctx.steps)
                       if s.ok and (s.output or "").strip()), "")
        made_up = unsourced_numbers(spoken, "\n".join(str(r) for r in results))
    # A SEAT THAT FAILED (the review of 2026-09-08). ctx.failures held
    # tools only; a seat cut at its bound or errored was in the toll and
    # nowhere in the delivery -- sitting 96's court said OUT OF TIME for
    # Manjuel and nothing about Jesster's 577s. Same arithmetic.
    cut = [(s.agent, s.error) for s in ctx.steps if s.error]
    if not fails and not partial and not late and not cut and not made_up:
        return False
    last = next((s for s in reversed(ctx.steps)
                 if s.ok and (s.output or "").strip()), None)
    if last is None:
        if not late and not cut:
            return False
        # NO SEAT SAT: the deadline was already past at the first seat (a
        # sub-run late in a long turn, or a stroke). The delivery is the
        # block itself, from the Gate, so the operator is told rather than
        # handed silence.
        last = StepResult(agent="Gate", model="(none)", output="")
        ctx.steps.append(last)

    blocks: list[str] = []
    if made_up:
        blocks.append(
            "A NUMBER NO TOOL RETURNED. These appear in the words above and in "
            "none of this run's tool results: " + ", ".join(made_up[:8]) + ". "
            "Dates, clock times and small numbers are not judged. Machine-"
            "emitted by comparing the two, not a seat's account of itself.")
    if fails:
        lines = [f"NOT EVERYTHING RAN. {len(fails)} "
                 f"tool{'' if len(fails) == 1 else 's'} failed or were refused "
                 f"in this run, whatever the words above say:"]
        for skill, why in fails:
            lines.append(f"  - {skill}: {why}")
        lines.append("This list is machine-emitted from what happened, not a "
                     "seat's account of it.")
        blocks.append("\n".join(lines))
    if partial:
        # THE PARTIAL-READ STAMP (2026-09-07; SITTING LAW 1 for the seats).
        # Sitting 87 run 7 answered from part 1 of 6 of DESIGN.md and did
        # not say so. Same arithmetic as the failures: it happened, it is
        # in the record, it travels with the answer.
        lines = [f"READ IN PART, NOT WHOLE. {len(partial)} "
                 f"read{'' if len(partial) == 1 else 's'} this run returned a "
                 f"piece of a file, and the words above rest on the piece:"]
        for stamp in partial:
            lines.append(f"  - {stamp}")
        lines.append("A seat that read part of a file has not read the file. "
                     "Ask for the other parts if the answer depends on them.")
        blocks.append("\n".join(lines))
    if cut:
        lines = [f"SEATS THAT FAILED. {len(cut)} seat{'' if len(cut) == 1 else 's'} "
                 f"did not finish this run; the words above are from the seats that did:"]
        for name, err in cut:
            lines.append(f"  - {name}: {' '.join((err or '').split())[:200]}")
        blocks.append("\n".join(lines))
    if late:
        # OUT OF TIME (2026-09-08, the operator's ten minutes). The seats
        # named here never sat; the words above are the seats that did.
        lines = [f"OUT OF TIME. {len(late)} seat{'' if len(late) == 1 else 's'} "
                 f"did not sit this run because the turn's {TURN_DEADLINE:.0f}s "
                 f"deadline had passed:"]
        for name in late:
            lines.append(f"  - {name}")
        lines.append("What is above is the seats that sat. Ask again for the "
                     "rest, or raise MANJUEL_TURN_DEADLINE.")
        blocks.append("\n".join(lines))
    block = "\n\n".join(blocks)

    last.output = f"{(last.output or '').rstrip()}\n\n{block}"
    what = []
    if fails:
        what.append(f"{len(fails)} failure(s)")
    if partial:
        what.append(f"{len(partial)} partial read(s)")
    if late:
        what.append(f"{len(late)} seat(s) out of time")
    if cut:
        what.append(f"{len(cut)} seat(s) failed")
    note = (f"recompose: {' and '.join(what)} appended to the delivery; "
            f"the closing seat's words were not the whole record")
    if note not in ctx.notes:
        ctx.notes.append(note)
    report("      " + ink.warn(note))
    return True


def _handle_failure(agent: Agent, exc: Exception, report) -> None:
    report("      " + ink.bad(f"! {agent.name} failed: {exc}"))

    if agent.on_fail == "abort":
        raise Aborted(f"{agent.name} failed and is marked on-fail: abort")

    if agent.on_fail == "skip":
        report("      (on-fail: skip -- continuing with prior context)")
        return

    try:
        choice = input("      retry / skip / abort? [s] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        raise Aborted("cancelled at failure prompt")

    if choice.startswith("a"):
        raise Aborted("aborted by user")
    # retry is handled by the caller re-running; for now treat as skip
