"""Deterministic pre-routing: does the objective plainly name a tool?

Session 5c. Three runs of `git commit` in a row never reached the Router,
because the Router only wakes on `needs_tool` and that flag was left entirely
to a 2b Steward's willingness to emit an exact XML string. It refused, then
excused, then returned nothing at all -- three different failures of the same
single point.

A request that literally says "git commit" should not need a language model's
permission to reach the git skill. This scan is free, runs before any model
is loaded, and only ever OPENS the door: the Router still decides what (if
anything) actually runs, and may still answer in prose instead.
"""

from __future__ import annotations

import re

# Natural phrasings that map to a keyword the operator will not type verbatim.
# Deliberately short: a wrong guess here costs one Router turn, but a missing
# one costs the whole request.
ALIASES: dict[str, tuple[str, ...]] = {
    "git_commit": ("commit", "check in", "check it in"),
    "git_status": ("git status", "dirty", "untracked", "what changed",
                   "the repo like", "state of the repo", "repo status",
                   "hows the repo", "how is the repo"),
    "git_push":   ("push",),
    "git_pull":   ("pull",),
    "git_init":   ("init the repo", "initialise the repo", "initialize the repo"),
    "rack_list":  ("what models", "which models", "list models", "the rack",
                   "whats on the card", "whats loaded", "what is loaded",
                   "whats in vram", "is opencode running", "whats warm",
                   "what is available"),
    "rack_sync":  ("sync the rack", "refresh the rack", "update the rack"),
    # A sitting is named by NUMBER and its runs are filed by timestamp, so
    # without this the Router guesses at filenames (sitting 63 guessed
    # `logs/sitting_63.md`, twice). The word is the whole alias -- the
    # skill pulls the number out of the objective itself.
    "sitting":    ("sitting", "the sitting"),
    # Periods, not sittings. "what ran yesterday" was unanswerable: the
    # estate stamped every transcript and nothing read the stamps as a
    # range.
    #
    # EVERY FORM CARRIES A VERB, and that is the whole point. The bare
    # adverbs were aliased first -- "yesterday", "recently", "lately" --
    # and they match ANYWHERE in an objective, so "yesterday was rough,
    # let's fix the router" would have listed transcripts. That is the
    # estate's oldest recurring fault (s23 "cool" -> classify_sentiment,
    # s31 "heloo stewy" -> the coder): a word is not an intent. A period
    # only asks for the record when something is said to have HAPPENED in
    # it.
    # "what did we DO yesterday" is how a person actually asks, and "did
    # yesterday" does not match it -- the words are "did we do". `we do
    # <period>` is the exact discriminator: "what did we do today" carries
    # it, and "what do we have to do today" -- a question about the FUTURE,
    # which this skill cannot answer -- does not.
    "when":       ("we do yesterday", "we do today", "we do last night",
                   "ran yesterday", "ran today", "ran this week",
                   "ran last week", "ran this month", "ran lately",
                   "ran recently", "ran on",
                   "did yesterday", "did today", "did this week",
                   "did lately", "did recently",
                   "happened yesterday", "happened today",
                   "happened this week", "happened last night",
                   "happened on", "happened lately", "happened recently",
                   "been doing lately", "been doing recently",
                   "went on yesterday", "went on this week"),
    "list_directory": ("the workspace", "list the workspace"),
    "ground_list": ("this place", "this archive", "this folder",
                    "this directory", "this repo", "in here", "around here",
                    "review the logs", "check the logs", "read the logs",
                    "look at the logs", "the logs",
                    "can you list it", "list it", "the full repo",
                    "list the repo", "list the full repo", "review the repo",
                    "what files", "list the files", "list the dir",
                    "list the directory", "list dir", "in this repo",
                    "in the repo", "whats in the repo", "what is in this repo",
                    "list the ground", "whats in the ground"),
    "ground_read": ("read the file", "open the file", "show me the file",
                    "this file", "that file", "the file",
                    "read pipelines", "read memory.md"),
    "skill_report": ("what skills", "your skills", "what tools", "your tools",
                     "available tools", "what can you do", "what can you actually do",
                     "list your tools", "list the skills"),
    "ground_report": ("working dir", "working directory", "where are we",
                      "where am i", "what ground", "which folder",
                      "what directory are"),
    "semantic_search": ("search for", "find anything about", "look up",
                        "who is manjuel", "who is jesster", "who is neiro",
                        "who is steward", "what is manjuel",
                        "who is the coder", "what is the coder",
                        "who is the smith", "who is the router",
                        "who is the guardian", "who is the reasoner",
                        "who is the evaluator", "who is the proofreader",
                        "who is the delivery agent",
                        "what is jesster", "what is neiro", "what is steward",
                        "who is aurora", "what is aurora",
                        "the mythos", "the creed", "the temper", "the veil",
                        "the glass", "the forge", "the weighing",
                        "the servants law", "the servant's law", "the dictum",
                        "what do you know about",
                        "founding documents", "the foundation",
                        "the covenant", "the covenants", "the doctrine",
                        "the estate laws", "founding docs"),
    # index_ground's phrases MOVED OUT of this table on 2026-09-02 and into
    # skills/index_ground.md, where a person editing the skill can see them
    # (`**Says:**`). It is the first skill to own its own dispatch, and the
    # pattern this table should shrink toward: what belongs to one skill
    # lives in that skill's file; what belongs to no single skill -- the
    # here-words, the cross-skill vocabulary -- stays here.
}

_WORD = re.compile(r"[a-z0-9_]+")


def _norm(text: str) -> str:
    return " ".join(_WORD.findall((text or "").lower()))


_FILENAME_RE = re.compile(
    r"\b[\w./\\-]+\.(md|py|txt|json|jsonl|us|toml|yml|yaml|csv)\b")


def names_a_file(objective: str) -> str:
    """A filename-shaped token in the objective, or "". Sitting 40: 'look at
    jesster.md' invented the file's contents instead of reading the file."""
    m = _FILENAME_RE.search(objective or "")
    return m.group(0) if m else ""


# THE CLAIM-CHECK. A seat that presents a file's contents when nothing read
# that file is asserting something the engine can already disprove -- so make
# it arithmetic rather than a matter of the model's character.
#
# NARROW ON PURPOSE. Each pattern is a construction that PRESENTS contents,
# not one that merely mentions a file: "the contents of x.md", "here is x.md",
# "x.md says". A seat discussing a file it did not read ("we should check
# x.md") is not claiming anything and must pass. HANDOFF, 2026-09-01: narrow
# and certainly right beats broad and crying wolf.
_F = r"[`'\"*]?(?P<f>[\w./\\-]+\.(?:md|py|txt|json|jsonl|us|toml|yml|yaml|csv))[`'\"*]?"
_CLAIM_RES = tuple(re.compile(p, re.I) for p in (
    rf"\bcontents?\s+of\s+(?:the\s+file\s+)?{_F}",
    rf"\bhere\s*(?:is|are|'s)\s+(?:the\s+)?"
    rf"(?:contents?|text|body|file|poem|note)\b[^.\n]{{0,40}}?{_F}",
    rf"{_F}\s+(?:says|reads|contains|states)\b",
    rf"\b(?:according\s+to|as\s+written\s+in|quoting|straight\s+from)\s+{_F}",
    rf"\bfile\s+{_F}\s*(?::|\bcontains\b|\bsays\b)",
))


def claims_file_contents(text: str) -> str:
    """The file a seat's own output claims to be SHOWING, or "".

    Point this at the SEAT'S OUTPUT, never at the objective: the objective
    asking for a file is a request, and only the reply can make a claim.

    HONEST LIMITS, written here rather than discovered later:
      - It catches a claim that NAMES A FILE. Invention that cites nothing
        still passes, and always will.
      - It proves a claim is UNSUPPORTED, never that it is FALSE. That is
        enough: LAW 5 says testimony is not fact, and an unsupported claim of
        fact is exactly what must not reach the operator.
      - A seat legitimately quoting a file read in an EARLIER turn trips it.
        The caller scopes it to THIS turn's reads and accepts that cost.
    """
    for rx in _CLAIM_RES:
        m = rx.search(text or "")
        if m:
            return m.group("f")
    return ""


# THE CITATION-CHECK's two halves (named sitting 61, built 2026-09-02).
# semantic_search prints one header line per hit:
#     1. logs/x.md  [chunk 3 @ 120]  written 2h ago  cosine 0.5140
# so the tool output IS the exhaustive list of (path, cosine) this turn.
_RESULT_LINE = re.compile(
    r"(?m)^\s*\d+\.\s+(?P<p>\S+)\s+\[[^\]]*\][^\n]*?\bcosine\s+(?P<s>\d\.\d+)\s*$")

# A filename with a score-like number near it on the same line. Narrow BY
# DESIGN, like the claim-check: it wants a path CITED AS A SCORED RESULT,
# not any mention of a file near any number.
_CITED_PAIR = re.compile(
    r"[`'\"*]?(?P<f>[\w./\\-]+\.(?:md|py|txt|json|jsonl|us|toml|yml|yaml|csv))"
    r"[`'\"*]?[^\n]{0,80}?\b(?P<s>[01]\.\d{2,4})")


def search_result_pairs(results_text: str) -> list:
    """Every (path, cosine) a search actually returned, parsed from the
    result header lines. Snippets are indented and never match."""
    return [(m.group("p").replace("\\", "/"), m.group("s"))
            for m in _RESULT_LINE.finditer(results_text or "")]


def cites_search_results(prose: str) -> list:
    """Every (path, score) a seat's prose presents as a scored hit.

    Sitting 61: the Router lifted a filename out of one result's SNIPPET
    and reported it as "Most Relevant" carrying ANOTHER result's cosine.
    Unlike uncited invention this has ground truth -- the cited pair either
    appears in the tool output or it does not. HONEST LIMIT: prose that
    fabricates without naming a path and a number still passes; that class
    is the claim-check's, and beyond both when it cites nothing at all."""
    return [(m.group("f").replace("\\", "/"), m.group("s"))
            for m in _CITED_PAIR.finditer(prose or "")]


# ---------------------------------------------------------------------
# Numbers a seat said that no tool returned
# ---------------------------------------------------------------------
#
# MOVED HERE FROM cli.py 2026-09-10, UNCHANGED. It lived beside `/brief` and
# ran only there, so the one place a seat most often invents a number -- an
# ordinary turn, speaking after a tool returned -- was never checked by the
# engine at all. SPEC 4.7's "the door invents numbers (35 for 37)", and
# 2026-09-09's "37 markdown files, ranging from 300 to 1200 bytes in size"
# with 300 and 1200 in no tool result that run.
#
# It belongs in this module because this is where the estate reads the SHAPE
# of text, and because `cites_search_results` and `search_result_pairs` above
# are the CITED half of the same question. cli.py keeps the old names as
# aliases; /brief, tests/standup.py and the strokes are untouched.

_NUM_OR_HASH = re.compile(r"(?<![\w.])([0-9a-f]{7,40}|\d[\d,]*\.?\d*)(?![\w.])")

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


def unsourced_numbers(said: str, facts: str) -> list[str]:
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


# Asking to be ADVISED, not to be told. `rack_report` gives facts only
# unless a judgement is asked for (the operator, 2026-09-09: "4.3 facts
# only"), and this is the test.
#
# THE BURDEN IS ON ASKING, deliberately. The default is the observed numbers,
# so a question that does not plainly ask for an opinion gets them; being
# wrong that way costs a reading he can ask for again, and being wrong the
# other way is a seat's prose the Router will summarise instead of the facts
# -- which is the fault this exists to close (sitting 85, three times).
#
# Every frame here is first-person-addressed or explicitly evaluative. A bare
# "what is the state of the rack?" is a FACTS question and must not match.
_JUDGEMENT_RE = re.compile(
    r"\bshould\s+(?:i|we|you|it|he|they|the)\b"
    r"|\bwhat\s+should\b"
    r"|\bwould\s+you\s+(?:recommend|advise|suggest|keep|drop|pull)\b"
    r"|\b(?:recommend|advise|suggest|evaluate|assess|critique|appraise)\b"
    r"|\byour\s+(?:opinion|read|view|assessment|judgement|judgment|take|advice)\b"
    r"|\bwhat\s+do\s+you\s+(?:think|make\s+of|reckon)\b"
    r"|\bdo\s+you\s+think\b"
    r"|\bis\s+it\s+(?:worth|wise|sensible|safe|a\s+good\s+idea)\b"
    r"|\bany\s+(?:concerns?|worries|problems?|issues?)\b"
    r"|\bwhat\s+would\s+you\b",
    re.IGNORECASE)


def asks_for_a_judgement(question: str) -> bool:
    """Does this question ask to be ADVISED, rather than told?

    Used by rack_report to decide whether a seat is woken at all. False is the
    safe answer and the default: the caller gets the observed numbers, which
    are never wrong, instead of a reading that has been (SPEC 4.7 -- the
    Quartermaster on llama3.2 invented in three of three readings).
    """
    return bool(_JUDGEMENT_RE.search(question or ""))


# Asking ABOUT a tool, not asking FOR it. The frames are deliberately
# narrow and all interrogative: a question about a thing, never an order
# involving it. "read pipelines.md" must keep dispatching.
_ABOUT_FRAMES = (
    "what does", "what do", "what is", "what are", "whats", "what can",
    "how does", "how do", "how is", "how would", "when do", "when should",
    "when would", "why would", "why does", "tell me about", "explain",
    "describe", "what happens when", "what would happen",
)
_ABOUT_TAIL = ("do", "does", "mean", "work", "works", "used for", "for",
               "good for", "about")


def asks_about_a_tool(objective: str, keywords) -> str:
    """The tool a question is ASKING ABOUT, or "".

    SITTING 69: "what does deep research do?" matched the spaced keyword
    form, dispatched the skill, and the closing seat then narrated the
    Router's DESCRIPTION as completed work -- "Deep research conducted an
    intensive analytical evaluation", past tense, over a run in which
    nothing ran. Every skill in the library is a landmine for a question
    about it, and the library is the thing the operator most needs to ask
    about.

    A question about a tool is answered FROM THE SKILL'S OWN MARKDOWN,
    which is authoritative and already written: facts read, not generated.
    """
    named = names_a_tool(objective, keywords)
    if not named:
        return ""
    text = " ".join((objective or "").lower().split())
    if not (text.endswith("?") or any(text.startswith(f) for f in _ABOUT_FRAMES)):
        return ""
    if not any(text.startswith(f) for f in _ABOUT_FRAMES):
        return ""
    # An order can still wear a question mark ("can you read pipelines.md?"),
    # so the frame must be ABOUT-shaped: it asks what the thing is or does,
    # rather than asking the thing to happen.
    if wants_writing(text) or names_a_file(text):
        return ""
    tail = text.rstrip("?").split()
    if tail and (tail[-1] in _ABOUT_TAIL or text.startswith(
            ("what is", "what are", "whats", "tell me about", "explain",
             "describe"))):
        return named
    return ""


_WROTE_RES = tuple(re.compile(p, re.I) for p in (
    r"\b(?:saved|wrote|created|stored|committed|added)\s+(?:it\s+)?"
    r"(?:as|to|into|in)?\s*[`'\"]?(?P<f>[\w./\\-]+\.\w{1,6})",
    r"\bI\s+(?:have\s+)?(?:saved|wrote|written|created|stored)\s+"
    r"[^.\n]{0,40}?[`'\"]?(?P<g>[\w./\\-]+\.\w{1,6})",
))


def claims_wrote_a_file(text: str) -> str:
    """The file a seat says it WROTE, or "".

    SITTING 70's closer: "Yesterday, I compiled a poem about autumn, saved
    it as 'poem.txt' in the Research folder, and successfully read it back
    to you." There is no yesterday, no poem.txt, and no earlier reading --
    a whole invented history, of which the one true clause was that
    `speak` had run.

    None of the existing gates could see it. The claim-check wants a
    CONTENTS claim and this claims a SAVE; the citation-check wants a
    search result; the recompose only appends failures. But it is the same
    arithmetic in a new place: a seat says a file was written, and the
    turn's tool calls say whether any writer ran.

    Same honest limits as its sibling: it wants a NAMED FILE, so invention
    that cites nothing still passes, and it proves a claim UNSUPPORTED
    rather than false. Narrow and certainly right beats broad and crying
    wolf."""
    for rx in _WROTE_RES:
        m = rx.search(text or "")
        if m:
            return (m.groupdict().get("f") or m.groupdict().get("g") or "")
    return ""


# KEYWORDS THAT ARE ALSO GRAMMAR. A skill may be called `when`, and then the
# word "when" appears in every third sentence anyone writes -- as a
# conjunction, doing a job that has nothing to do with the skill. On
# 2026-09-12 the coder flow's `verify` objective carried a brief that said
# "...when executed, it should print 55", and intent dispatched the `when`
# skill: a transcript-window reader, woken to answer a question about a
# Python file, because of a subordinate clause.
#
# A CONTENT word is different. "inspect", "remember", "statistics" are also
# keywords, and someone who writes them usually does mean the thing; they are
# left alone. These are FUNCTION words: they carry no subject of their own, so
# they are grammar unless the sentence is plainly ABOUT them.
#
# Only `when` is a keyword today. The rest are here because a skill named
# `how` or `where` would arrive with the same fault already fixed.
_FUNCTION_WORDS = frozenset({
    "when", "where", "what", "who", "whom", "why", "how", "which",
    "if", "then", "while", "until", "after", "before", "since", "unless",
})

# `when`, `'when'`, "when" -- a word wearing quotes is a word being NAMED
# rather than used. Checked against the RAW objective, because _norm strips
# exactly the marks that carry the distinction.
_QUOTED = "`'\"*"


# A KEYWORD WHOSE ARGUMENT IS A NUMBER WANTS A NUMBER BESIDE IT.
#
# `when` was fixed by asking whether a function word was NAMED or merely
# spoken. `sitting` is the next collision and needs a different question,
# because it is a CONTENT word: `skills/sitting.md` resolves a numbered
# sitting -- "review sitting 63", "what ran in sitting 47" -- and this estate
# says the bare word constantly. CLAUDE.md and `law/` alone carry it 58 times:
# "while the operator's sitting is open", "mid-sitting", "the sitting laws".
#
# THE SKILL'S OWN DECLARATION IS THE TEST, not a list beside it. `sitting.md`
# says its argument is "The sitting number alone, e.g. 63", so a naming has a
# number next to it and a mention does not. Read off `param_notes` -- the
# author's own words -- which is the same doctrine that put phrases in
# `**Says:**` (sitting 66: markdown declares, Python only runs it).
_NUMERIC_PARAM = re.compile(r"\bnumber\b", re.I)

# How far after the keyword a digit may sit and still be its argument:
# "sitting 63", "sitting number 63", "sitting #63" all count; "sitting is
# open" does not.
_NUMBER_WINDOW = 2


def _wants_a_number(spec) -> bool:
    """Does this skill's own markdown describe its argument as a number?"""
    if spec is None:
        return False
    try:
        notes = spec.param_notes or {}
    except Exception:
        return False
    return any(_NUMERIC_PARAM.search(str(v or "")) for v in notes.values())


def _number_follows(form: str, hay: str) -> bool:
    """Is there a digit within `_NUMBER_WINDOW` words after this form in hay?

    `hay` is normalised, so punctuation is already gone and "sitting 84's
    toll" reads as "sitting 84 s toll" -- which is still a naming, and still
    finds its number.
    """
    words = hay.split()
    n = len(form.split())
    for i in range(len(words) - n + 1):
        if words[i:i + n] == form.split():
            for w in words[i + n:i + n + _NUMBER_WINDOW]:
                if any(ch.isdigit() for ch in w):
                    return True
    return False


def _wears_quotes(form: str, raw: str) -> bool:
    """A word wearing quotes is a word being NAMED rather than used."""
    return any(f"{q}{form}{q}" in raw.lower() for q in _QUOTED)


def _named_not_used(form: str, hay: str, raw: str) -> bool:
    """Is this FUNCTION-WORD form being NAMED here, rather than spoken?

    Two ways, both structural: it OPENS the objective ("when did we last
    commit" is a question about time; "...when executed" is a clause), or it
    wears quotes in the raw text ("call `when`").

    THE OPENING CLAUSE IS FOR FUNCTION WORDS ONLY, and the numeric rule below
    must not borrow it -- see `_wants_a_number`'s use. A WH-word at the front
    of a sentence IS the question; a content word at the front is just a
    sentence. `ALIASES` carries "the sitting", so "the sitting laws bind any
    hand" opens with the form and means nothing of the kind.
    """
    if hay == form or hay.startswith(form + " "):
        return True
    return _wears_quotes(form, raw)


def names_a_tool(objective: str, keywords) -> str:
    """Return the keyword the objective names, or "" if none does.

    Matches the keyword itself (`git_commit`), its spaced form (`git commit`),
    and any declared alias. Longest match wins so `git_commit` beats `commit`.

    A ONE-WORD KEYWORD THAT IS ENGLISH GRAMMAR must be named, not merely
    spoken -- see `_FUNCTION_WORDS`. A declared `**Says:**` phrase is never
    subject to that: a phrase is already a naming, which is why the cure for a
    skill caught by this is to declare its phrases in its own markdown.

    A skill may declare its OWN phrases in its markdown (`**Says:**`), and
    those are read here alongside the table below. The table came first and
    stays -- it holds the here-words and the cross-skill vocabulary that
    belong to no single file -- but a phrase that is plainly one skill's
    business now lives in that skill's file, where a person editing the
    skill will see it (the operator's ruling, sitting 66: markdown declares,
    Python only runs it).

    `keywords` may be a plain set of keywords or a SkillLibrary; passing the
    library is what makes the declared phrases visible.
    """
    hay = _norm(objective)
    if not hay:
        return ""

    lib = keywords if hasattr(keywords, "keywords") else None
    kws = lib.keywords() if lib is not None else keywords

    hits: list[tuple[int, str]] = []
    for kw in kws:
        declared: tuple = ()
        spec = None
        if lib is not None:
            spec = lib.spec(kw)
            declared = tuple(getattr(spec, "says", ()) or ()) if spec else ()
        bare = [kw, kw.replace("_", " ")] + list(ALIASES.get(kw, ()))
        # A DECLARED PHRASE IS ALREADY A NAMING, so it is never held to the
        # function-word rule below -- `says` and `bare` are kept apart for
        # exactly that reason.
        for form, is_phrase in ([(f, False) for f in bare]
                                + [(f, True) for f in declared]):
            f = _norm(form)
            if not f:
                continue
            if not re.search(rf"(?<![a-z0-9_]){re.escape(f)}(?![a-z0-9_])", hay):
                continue
            if (not is_phrase and f in _FUNCTION_WORDS
                    and not _named_not_used(f, hay, objective or "")):
                continue
            # A bare keyword whose declared argument is a NUMBER is only a
            # naming with a number beside it. A declared PHRASE is exempt for
            # the same reason it is exempt above: a phrase is already a naming.
            if (not is_phrase and _wants_a_number(spec)
                    and not _number_follows(f, hay)
                    and not _wears_quotes(f, objective or "")):
                continue
            hits.append((len(f), kw))
    if not hits:
        return ""
    return max(hits)[1]


# ---------------------------------------------------------------------
# Gibberish: measured, not judged
# ---------------------------------------------------------------------

_VOWELS = set("aeiouy")
_WORDISH = re.compile(r"[a-z]+")


def _wordlike(token: str) -> bool:
    """Does this token look like a word a person meant to type?"""
    if not (2 <= len(token) <= 24):
        return False
    # Real words are roughly a fifth vowels; "tgjergnn" is not.
    if sum(c in _VOWELS for c in token) / len(token) < 0.2:
        return False
    # aaaaabbbb / qwcooooooo: a third of the token as one repeated char
    for ch in set(token):
        if token.count(ch) > max(3, len(token) * 2 // 3):
            return False
    return True


def gibberish(objective: str) -> bool:
    """True when the objective does not parse as language at all.

    Sitting 22: keyboard mash ("9 sjdnfjnjn ghagga abbbbb...") raised
    `technical`, woke the Expert Coder, and produced four stages of invented
    work about a request that meant nothing. Seats IMPROVISE on noise -- so
    noise is stopped by arithmetic before any seat sees it. Deliberately
    lenient: one real word in a short line passes ("vram?", "ok"), and typos
    pass, because a typo is still language.
    """
    text = (objective or "").lower()
    solid = [c for c in text if not c.isspace()]
    if solid and sum(c.isdigit() for c in solid) / len(solid) > 0.4:
        return True                      # mostly digits is a mash, not a sum
    tokens = _WORDISH.findall(text)
    if not tokens:
        return True                      # digits and symbols only
    words = sum(1 for t in tokens if _wordlike(t))
    if len(tokens) <= 2:
        return words == 0
    return words / len(tokens) < 0.5


# ---------------------------------------------------------------------
# Injection markers: the gate before the Guardian
# ---------------------------------------------------------------------

# Sitting 39: the injection test feed sailed past the model Guardian and
# moved the chain's hands -- classify ran, speak said 76 characters aloud.
# The docs held at the bottom (secrets refuse by name), but the front gate
# rolled dice. These patterns refuse by ARITHMETIC, before any model reads
# a word. The Guardian model remains behind this as the judgment layer.
_INJECTION_MARKERS = [
    (re.compile(r"(?i)\b(ignore|disregard|forget)\b.{0,40}\b(previous|prior|all|above|earlier)\b.{0,20}\binstructions?\b"),
     "an instruction to ignore instructions"),
    (re.compile(r"(?i)\byou (must|will) now\b|\bnew instructions\s*:"),
     "an attempt to re-instruct the machine"),
    (re.compile(r"(?i)\b(print|reveal|show|output|read|send|dump)\b.{0,60}\.(env|netrc|npmrc|pypirc)\b"),
     "a reach for a secrets file"),
    (re.compile(r"(?i)\b(api[ _-]?keys?|passwords?|credentials?|secret keys?|tokens?)\b.{0,40}\b(print|reveal|show|send|list|dump|output)\b"),
     "a reach for credentials"),
    (re.compile(r"(?i)\b(print|reveal|show|send|dump|list)\b.{0,40}\b(api[ _-]?keys?|passwords?|credentials?|secret keys?)\b"),
     "a reach for credentials"),
    (re.compile(r"(?i)\bsystem prompt\b.{0,40}\b(print|reveal|show|repeat|output)\b"),
     "a reach for the machine's own instructions"),
    (re.compile(r"(?i)\b(print|reveal|show|repeat|output)\b.{0,40}\bsystem prompt\b"),
     "a reach for the machine's own instructions"),
]


def injection_markers(feed: str) -> list[str]:
    """Named markers found in pasted material. Empty list = no hard match.

    Deliberately about UNAMBIGUOUS shapes only -- prose ABOUT injection
    ("the guardian catches injection attacks") matches nothing here. The
    model Guardian judges everything softer.
    """
    text = feed or ""
    return [name for rx, name in _INJECTION_MARKERS if rx.search(text)]


# ---------------------------------------------------------------------
# Topic boundaries: the operator says so, or the drift shows it
# ---------------------------------------------------------------------

_SESSION_CUES = ("new session", "fresh session", "start over", "clean slate",
                 "start fresh", "wipe the thread")
_TOPIC_CUES = ("new topic", "next topic", "new thread", "next thread",
               "switch gears", "switching gears", "change of pace",
               "different thing", "something different", "moving on",
               "next subject", "new subject", "change the subject")


def topic_cue(objective: str) -> str:
    """"session", "topic", or "". The operator's own words draw the line."""
    low = " ".join((objective or "").lower().split())
    if any(c in low for c in _SESSION_CUES):
        return "session"
    if any(c in low for c in _TOPIC_CUES):
        return "topic"
    return ""


def cue_only(objective: str) -> bool:
    """True when the turn is the cue and nothing else -- no question rides
    along, so no seat needs to sit."""
    low = " ".join((objective or "").lower().split()).strip(".!?, ")
    for c in _SESSION_CUES + _TOPIC_CUES:
        if low == c or low in (f"ok {c}", f"okay {c}", f"alright {c}",
                               f"{c} then", f"lets {c}", f"let's {c}"):
            return True
    return False


# ---------------------------------------------------------------------
# Action shapes: route without presuming
# ---------------------------------------------------------------------

# Write-shaped verbs: a filename after one of these is a thing to MAKE or
# CHANGE, never a thing to read. Sitting 42's lesson inverted a fix: the
# bare filename rule presumed ground_read, so "write hello.md" would have
# READ hello.md. A write is a decision -- what file, what content, which
# skill -- and deciding is the Router's office, so these raise needs_tool
# with NO named tool.
_WRITE_VERBS = re.compile(
    r"(?i)\b(write|make|create|save|generate|build|add|append|update|edit|"
    r"fix|change|modify|refactor|implement|delete|remove|rename)\b")

# Action-verb + object shapes that plainly want hands, without naming which.
_ACTION_SHAPE = re.compile(
    r"(?i)\b(check|verify|test|run|execute|analyze|analyse|compare|count|"
    r"measure|calculate|compute|scan|inspect|audit)\b.{0,50}"
    r"\b(file|files|folder|dir|directory|repo|code|ground|workspace|log|"
    r"logs|index|record|this|it|that)\b")


def wants_writing(objective: str) -> bool:
    """A write-shaped verb near the request. Router decides the rest."""
    return bool(_WRITE_VERBS.search(objective or ""))


def wants_action(objective: str) -> bool:
    """Action-verb + object: the turn wants hands, tool unspecified."""
    return bool(_ACTION_SHAPE.search(objective or ""))


# AN ORDER TO RUN SOMETHING. Narrow on purpose: the verb has to mean
# EXECUTE, not "run through it" or "run a check on the record".
_RUN_VERBS = re.compile(r"(?i)\b(run|execute|rerun|re-run)\b")


def wants_running(objective: str) -> str:
    """The `.py` this objective orders RUN, or "".

    EARNED 2026-09-12, from the coder flow. `verify`'s objective was "Run the
    .py file this task names and report exactly what it said", the file was
    named in the text, and the Router answered "NO skill is needed" -- twice,
    for two different reasons, on two different runs. Once it wrote the file
    and never ran it; once it decided the answer was already in the thread.
    Both times a seat's judgement stood where arithmetic was available: the
    objective says RUN, it names a `.py`, and whether that file exists is a
    fact on disk. The estate's own pattern for that is to DECIDE the call and
    wake the Router to read the result -- "it does not choose".

    `.py` ONLY, because `run_python` runs Python and nothing else; a "run
    notes.md" is not an order this can answer, and it falls through to the
    reader exactly as it did before.
    """
    text = objective or ""
    if not _RUN_VERBS.search(text):
        return ""
    got = names_a_file(text)
    return got if got.lower().endswith(".py") else ""


# A FOLLOW-UP POINTS AT THE CONVERSATION. Sitting 87 (2026-09-04, runs 8,
# 9, 13): "what does that last part mean? Refused: `content` must be a
# PATH..." -- the operator pasting the line he had just been shown -- was
# dispatched to the reader by asks_the_ground, the front Steward was
# skipped as already-dispatched, and the Router, which by design never
# sees the dialogue, answered "there is no conversation history in this
# run". The one seat that holds the thread was the one seat not asked.
# The toll that night: "needs more context".
#
# Three shapes, all decidable without a model: a short question built on
# an anaphor (the sitting-71 rule, already used by asks_the_ground); a
# question that OPENS with a follow-up lead ("what does that", "what do
# you mean", "that last part", "say that again"); and a turn that QUOTES
# the previous delivery -- forty characters of it verbatim is not a
# coincidence. Any of these, with a dialogue to point at, keeps the door
# in the run. It does not stop the Router from waking if the door raises
# the flag; it stops the door from being skipped.
_FOLLOWUP_LEADS = (
    "what does that", "what do you mean", "what did you mean", "what was that",
    "that last part", "the last part", "say that again", "explain that",
    "what does it mean", "what's that mean", "whats that mean", "meaning what",
    "and that", "so that", "why is that", "how so", "in what way", "such as",
    "like what", "for example", "which one", "which ones", "that one",
)
_QUOTE_MIN = 40

# A TURN THAT NAMES AN EARLIER TURN -- BY EITHER SPEAKER. The third way a
# turn can point back, and the one that was missing: _ANAPHORA covers
# pointing words ("that", "it"), _FOLLOWUP_LEADS covers fixed openings
# ("say that again"), and neither covers "what colour did you just say"
# or "what were the two colours I asked you for".
#
# BOTH HALVES WERE MEASURED, a fix apart. The seat's half first: "what
# colour did you just say" was routed as a fresh objective. Then the
# operator's own half, live and after that fix: "What were the two colours
# I asked you for?" answered "I don't have access to the conversation
# history", and "And which one did I ask for first?" ran a semantic_search
# over past sessions -- both had asks_the_ground TRUE, so the guess that
# the question was about the GROUND claimed them. pipeline.py withdraws
# that guess for a follow-up; only the recognition was missing.
#
# PAST TENSE ONLY on the operator's half, and that is the whole guard
# against false positives: "what should i ask the router" is a real
# question about the ground, and a present-tense "i ask" would claim it,
# keep the door, and stop his work reaching the Router.
#
# Measured through the glass 2026-09-09: that exact question was routed as
# a fresh objective, so the Steward was skipped, and the Router -- which
# never sees the dialogue, by design -- answered truthfully that it had no
# memory of the previous turn. Everything beneath was working; the door was
# simply not kept.
#
# A RULE, NOT MORE PHRASES: second person plus a speech verb. A list of
# literal leads would have caught that one sentence and missed the next
# phrasing of it.
_SPOKE_BACK = re.compile(
    r"\byou(?:'ve| have)?\s+(?:just\s+)?"
    r"(?:said|say|says|told|tell|answered|answer|wrote|mentioned|called)\b"
    r"|\bdid\s+you\s+(?:just\s+)?(?:say|said|tell|mention|call|answer)\b"
    r"|\byour\s+(?:last|previous|first|own)\s+"
    r"(?:answer|reply|response|word|words|message|line)\b"
    r"|\bthe\s+last\s+thing\s+you\s+(?:said|wrote|told)\b"
    # the operator's own earlier turn: "I asked", "did I say", "my last
    # question". Past tense only -- see the note above.
    r"|\bi\s+(?:just\s+)?(?:asked|said|told|mentioned|requested|wanted)\b"
    r"|\bdid\s+i\s+(?:just\s+)?(?:ask|say|tell|mention|request)\b"
    r"|\bwas\s+i\s+(?:just\s+)?(?:asking|saying|telling)\b"
    r"|\bmy\s+(?:last|previous|first|own)\s+"
    r"(?:question|request|words?|message|line|ask)\b",
    re.IGNORECASE,
)

# A QUESTION ABOUT THIS SITTING (0.1.6, the sitting story). Sitting 93:
# "what happened? why did you suck so bad?" went to semantic_search over
# the whole record. The door now holds the sitting story (seatlog.
# story_block), so a question about what THIS sitting did is the door's
# to answer from it -- a reader dispatch is withdrawn, as a follow-up's
# is. Leads only; a question that also names a tool or a file is still
# the operator's order.
_SITTING_LEADS = (
    "what happened", "what just happened", "what did you do", "what did you just",
    "what have you done", "what went wrong", "why did that fail", "why did you",
    "what did we do", "what have we done", "so far", "this sitting",
    "what ran", "what did that run", "recap", "where were we", "what were we",
)


def asks_the_sitting(objective: str) -> bool:
    """Whether the turn asks what THIS sitting has done -- the story's turf."""
    low = " ".join((objective or "").lower().split()).strip(" ?!.")
    if not low or len(low.split()) > 14:
        return False
    return any(lead in low for lead in _SITTING_LEADS)


def is_followup(objective: str, dialogue: list | None) -> bool:
    """Whether this turn points back at the conversation rather than at
    the ground. Needs a dialogue to point at; with none it is never one."""
    if not dialogue:
        return False
    text = " ".join((objective or "").split())
    low = text.lower().strip()
    if not low:
        return False
    words = _WORD.findall(_norm(low))
    if len(words) <= 8 and any(w in _ANAPHORA for w in words):
        return True
    if any(low.startswith(lead) for lead in _FOLLOWUP_LEADS):
        return True
    # either speaker's earlier turn: "what colour did you just say",
    # "your last answer", "what were the two colours I asked you for"
    if _SPOKE_BACK.search(low):
        return True
    # a turn that carries the previous delivery's own words
    last = ""
    for e in reversed(list(dialogue)):
        who = str(e[0]).lower() if len(e) else ""
        if who != "operator":
            last = " ".join(str(e[1]).split()) if len(e) > 1 else ""
            break
    if len(last) >= _QUOTE_MIN:
        # any 40-char window of the last delivery appearing verbatim
        step = 20
        for i in range(0, max(1, len(last) - _QUOTE_MIN + 1), step):
            piece = last[i:i + _QUOTE_MIN]
            if len(piece) == _QUOTE_MIN and piece.lower() in low:
                return True
    return False


def last_file_in(thread: list) -> str:
    """The most recently MENTIONED filename in the conversation, newest
    first -- so "read the file" means the file we were just talking about,
    the way it does between people."""
    for e in reversed(list(thread or [])):
        what = e[1] if len(e) > 1 else ""
        m = None
        for m in _FILENAME_RE.finditer(str(what)):
            pass                          # keep the LAST match in the entry
        if m:
            return m.group(0)
    return ""


# Words a question can be made of WITHOUT being about anything in
# particular. Function words, casual words, question leads. Deliberately
# small: an unlisted word is treated as a term worth looking up, because
# sitting 60 showed what fills the gap when a real term ISN'T looked up --
# a seat invented a client narrative from nothing. Missing common words
# cost a search; missing content terms cost the truth.
_COMMON_ENOUGH = frozenset("""
a an the is are was were be been being am do does did doing done can could
will would should shall may might must have has had having i you we they he
she it me us them him her my your our their its mine yours this that these
those there here now then and or but not no yes if so of in on at to for
from with about into onto over under out up down off again once right just
like some any all both each few more most other such only own same too very
also than as how what who whom whose which when where why whats whos hows
dont cant wont didnt doesnt isnt arent im ive youre weve theyve thats whats
hey hi hello sup yo howdy dude bro man bud buddy homie fam boss chief stew
steward thanks thank please cool ok okay good nice well fine great alright
yeah yea nah hmm huh oh ah wow damn really actually basically literally
gonna wanna gotta let lets go going come came get got give take make know
think say said see look want need feel mean tell told ask
up down out in on off over here there back again still even ever
fuck fucking fucked shit shitty damn damned hell crap wtf ass bloody
sup yo dawg fam bruh homie buddy pal chief boss stew stewy
""".split())

# A question that opens with a greeting is a greeting. Sitting 48's law
# (greetings stay at the door) survives its gate being dropped.
# Words that point BACKWARD, at the conversation, rather than at anything
# in the ground. Defined here because this module is where dispatch is
# decided; pipeline.py keeps its own copy for the follow-up branch and
# context.py a wider one for dialogue boundaries -- three sets for three
# jobs, and worth collapsing the day a fourth appears.
_ANAPHORA = {"that", "it", "this", "those", "these", "them", "again",
             "repeat", "he", "she", "they"}

_GREETING_LEADS = {"hey", "hi", "hello", "sup", "yo", "howdy", "morning",
                   "evening", "afternoon", "greetings", "good", "gday",
                   "mornin", "afternoon", "salutations"}

_QUESTION_LEADS = {"who", "whos", "what", "whats", "where", "wheres", "when",
                   "which", "why", "how", "hows", "tell", "explain",
                   "describe", "find"}


_COURTESY_LEADS = {
    "thanks", "thank", "ok", "okay", "kk", "cool", "nice", "great", "right",
    "sure", "alright", "sweet", "awesome", "perfect", "gotcha", "understood",
    "noted", "interesting", "appreciate", "yes", "yeah", "yep", "fine",
}


def _after_courtesy(text: str) -> str:
    """Drop ONE leading courtesy clause, so the question behind it is seen.

    SITTING 81, and it is the greeting bug's mirror image. asks_the_ground
    requires words[0] to be a question lead, or the text to end in `?`. A
    polite lead-in moves the question word off position 0, and someone who
    opens with "thanks" usually does not close with a question mark:

        "where do i find a list or description of the existing tools"
            -> dispatched
        "thank you for the clarification, where do i find a list or
         description of the existing tools"
            -> NOT dispatched

    Same sentence. The second ran no tool, and the Steward -- with nothing
    dispatched and only the thread to go on -- answered a question from TWO
    turns earlier and invented the contents of `pipeline_steps.py` doing it.
    The greeting bug cost 155 seconds; this one cost a confident wrong
    answer, which is dearer.

    ONE CLAUSE, AND ONLY FROM THE FRONT. If the first word is a courtesy,
    everything up to the first comma goes -- or just the courtesy words when
    there is no comma. Bounded to the opening: a "thanks" in the middle of a
    sentence is part of the sentence, and a second clause is content.

    The greeting test still runs on what is left, so "thanks, good morning"
    is still a greeting and still reaches no reader.
    """
    raw = (text or "").strip()
    if not raw:
        return raw
    first = _WORD.findall(_norm(raw))
    if not first or first[0] not in _COURTESY_LEADS:
        return raw
    head, sep, tail = raw.partition(",")
    if sep and tail.strip() and len(_WORD.findall(_norm(head))) <= 8:
        return tail.strip()
    # No comma: peel the courtesy words themselves off the front.
    out = raw
    for _ in range(3):
        m = re.match(r"^\s*([A-Za-z']+)\b[\s,:-]*", out)
        if not m or _norm(m.group(1)) not in _COURTESY_LEADS:
            break
        out = out[m.end():]
    return out.strip() or raw


# "WHAT IS IN THE <X> DIR" IS A LISTING, NOT A LOOKUP. Sittings 86, 88 and
# 90 -- three standups in a row -- sent "what is in the skills dir" to the
# reader (asks_the_ground: a question carrying a term), and the Router then
# listed the WORKSPACE and reported the skills folder missing. The shape is
# a folder named by the operator with a listing verb around it; the folder
# is checked on disk (the same viability step as the named file), and a real
# one is a ground_list with its name as the argument. The operator, sitting
# 90: "9/10 on the dry run, what the fuck dude." Third sighting; built.
_FOLDER_RE = re.compile(
    r"(?i)\b(?:what(?:'s|s| is| are)?\s+(?:in|inside|under)|list|show(?: me)?|"
    r"contents? of|look (?:in|inside|at))\s+(?:the\s+|my\s+|our\s+)?"
    r"(?P<name>[A-Za-z0-9_][A-Za-z0-9_.\-]*(?:/[A-Za-z0-9_.\-]+)*)"
    r"(?:/(?!\S)|\s+(?:dir|directory|folder)\b)")


def names_a_folder(objective: str) -> str:
    """The folder an objective asks to see, or "". `what is in the skills
    dir` -> `skills`; `list manjuel/` -> `manjuel`; `show me the law
    folder` -> `law`. The caller checks it is a real folder in the ground."""
    m = _FOLDER_RE.search(objective or "")
    if not m:
        return ""
    name = m.group("name").strip().strip("/")
    if name.lower() in ("the", "a", "this", "that"):
        return ""
    return name


def asks_the_ground(objective: str) -> bool:
    """A question carrying a term worth looking up. Sitting 60: five
    questions about the estate's own contents -- "what is the ledger?",
    "who is X?", "what is the ledger work?" -- raised no flag, ran no
    tool, and one produced a confident invented paragraph about a real
    client. A question about the ground must reach a reader; an empty
    search result is the honest answer (s61 proved what that looks like).

    Shape: question-led or question-marked, not a greeting, not an exit,
    not gibberish, and at least one word that is NOT common conversational
    furniture. "what are you doing right now" is all furniture -- no
    dispatch. "who is warden?" carries `warden` -- dispatched. The common
    list errs small ON PURPOSE: an over-match costs one search; an
    under-match is sitting 60 again."""
    text = _after_courtesy((objective or "").strip())
    words = _WORD.findall(_norm(text))
    # A GREETING IS THE FIRST TWO WORDS, NOT THE FIRST. Sitting 79: "good
    # morning, sunshine, how are ya?" was dispatched to the reader and cost
    # 155 seconds, because this test read words[0] -- and the whole `good X`
    # family, the commonest greeting form in English, leads with `good`.
    # "good morning, sir" escaped only by luck: it carries no question mark.
    # The set had `morning`/`evening`/`afternoon` and could never reach them.
    if len(words) < 2 or _GREETING_LEADS & set(words[:2]):
        return False
    if not (text.endswith("?") or words[0] in _QUESTION_LEADS):
        return False
    if wants_out(text) or gibberish(text):
        return False
    # A SHORT QUESTION ABOUT THE SEAT ITSELF IS CONVERSATION (the keyword
    # bait, fifth sighting, sitting 93: "can you hear me" -> the reader ->
    # the Router called `speak` with nothing, 84s). "are you there", "can
    # you hear me", "you awake" -- four words or fewer, addressed to
    # "you", carrying no noun the ground would hold -- reach the door.
    if len(words) <= 4 and "you" in words:
        return False
    # AN ANAPHOR POINTS AT THE CONVERSATION, NOT AT THE GROUND. Sitting 71:
    # "what does that even mean?" was dispatched to the reader, and the
    # Router -- which by design never sees the dialogue -- answered "there
    # is no prior exchange and nothing to refer to as 'that'". It was
    # right, and it should never have been asked. A short question built
    # around `that`/`it`/`this` is a FOLLOW-UP: the Steward holds the
    # conversation and is the seat that can answer it.
    if len(words) <= 8 and any(w in _ANAPHORA for w in words):
        return False
    return any(len(w) >= 3 and w not in _COMMON_ENOUGH for w in words)


# THE DECOMPOSER (operator's design, sitting 62 conversation): dispatch by
# VERB-OBJECT STRUCTURE, not by pre-carved phrases. "search the ground find
# the warden estate!" matched no alias twice in sitting 61 -- every word was
# understood and no pattern was exact, so nothing ran. Decomposition moves
# the match from phrases to structure, and stays pure arithmetic.
#
# THE BALANCE, his ruling: matched executes, everything else FALLS THROUGH
# TO CONVERSATION. So this is imperative-lead only -- the verb must open
# the sentence (after politeness filler). "i cant find anything in this
# repo man" is a complaint; "that search was garbage" is a review; neither
# is an order, and neither dispatches. Reader-verbs only for now: the
# write/action shapes above already carry their own classes.
_READER_VERBS = {"search", "find", "grep", "locate", "query", "look", "dig"}
_GROUND_OBJECTS = {"ground", "dir", "directory", "estate", "repo",
                   "repository", "record", "records", "archive", "index",
                   "folder", "workspace", "place", "files"}
_LEAD_FILLER = {"please", "ok", "okay", "now", "hey", "yo", "alright",
                "just", "go", "then", "and", "so", "can", "you", "u",
                "through", "up", "in", "into", "at", "the", "this", "that",
                "my", "our"}


# Conjunctions and enumerations that join SEPARATE acts. "and" alone is
# not one of them -- "read the rack and tell me" is one act described
# twice, and treating it as two is how a chain talks itself into work
# nobody asked for.
# Verbs that name an ACT this estate can perform. Counting acts with
# _WRITE_VERBS + _ACTION_SHAPE was wrong and the strokes caught it: those
# two were built for other jobs and between them know nothing of `read`,
# `search`, `index` or `commit`, so "read the rack, then write a note,
# then commit it" counted as ONE act. The estate's own working vocabulary
# is the right list.
_ACT_VERB = re.compile(
    r"(?i)\b(read|write|make|create|save|generate|build|add|append|update|"
    r"edit|fix|change|modify|refactor|implement|delete|remove|rename|"
    r"search|find|look|index|commit|push|pull|list|show|open|check|verify|"
    r"test|run|execute|review|analyz|analys|compare|count|measure|scan|"
    r"inspect|audit|summaris|summariz|report|remember|speak|load|unload)\b")

_MULTI_ACT = re.compile(
    r"(?i)(,\s*then\b|\bthen\b|\bafter that\b|\bnext,|\bfollowed by\b|"
    r"\bonce that\b|\band then\b|;\s*\w)")


def is_big_objective(objective: str, verbs: int = 2) -> bool:
    """Whether an objective is plainly SEVERAL acts, not one.

    The gate for waking the decomposer. It is deliberately hard to trip:
    a long sentence is not a big objective, and neither is a bare "and".
    What counts is sequencing language ("then", "after that", "followed
    by") carrying at least two act-shaped verbs, or a numbered list the
    operator wrote himself.

    Erring shut is the right error. A decomposition that fires on one act
    spends a model call to restate the request, and every unnecessary
    stage is another chance to drift (DESIGN 11: serial chains compound
    error). A missed decomposition just means the chain does the work the
    ordinary way."""
    text = (objective or "").strip()
    if len(text) < 40:
        return False
    if re.search(r"(?m)^\s*(?:\d+[.)]|[-*])\s+\S+.*\n\s*(?:\d+[.)]|[-*])\s+\S",
                 text):
        return True                      # a list the operator wrote himself
    if not _MULTI_ACT.search(text):
        return False
    return len(_ACT_VERB.findall(text)) >= verbs


def decomposes_to_search(objective: str) -> str:
    """The remainder-as-payload when the words are an ORDER to search the
    ground, else "". Verb class + object class + remainder: an opening
    reader-verb, a ground-object somewhere after it, and whatever is left
    becomes the query (may be empty -- the skill falls back to the
    objective, its own law since sitting 26)."""
    words = _WORD.findall(_norm(objective))
    while words and words[0] in _LEAD_FILLER:
        words = words[1:]
    if not words or words[0] not in _READER_VERBS:
        return ""
    rest = words[1:]
    hit = next((i for i, w in enumerate(rest) if w in _GROUND_OBJECTS), -1)
    if hit < 0:
        return ""
    # The payload sits on either side of the object ("search the ground
    # for X" / "find X in the records"). Only the FIRST object is the
    # frame -- a later object-class word belongs to the payload: in
    # "search the ground find the warden estate", `estate` is the client's
    # own word, not structure (the stroke that caught this scrubbed it to
    # "warden"). Filler, verbs and "for" stay structural throughout.
    payload = [w for i, w in enumerate(rest)
               if i != hit
               and w not in _LEAD_FILLER and w not in _READER_VERBS
               and w != "for"]
    return " ".join(payload) or objective.strip()


_LEAVE_WORDS = {"exit", "quit", "leave", "bye", "goodbye", "peace", "out",
                "done", "go"}
_VOCATIVES = {"bro", "man", "dude", "homie", "bud", "buddy", "fam", "dawg",
              "stew", "steward", "chief", "boss", "im", "i'm", "gotta",
              "gonna", "later", "yall", "now", "ok", "okay", "alright"}


def wants_out(objective: str) -> bool:
    """An exit command wearing casual clothes. "exit bro" means exit.

    Strict on purpose: EVERY word must be a leave-word or a vocative, and at
    least one leave-word must appear -- "let me exit the loop in this code"
    never matches, because "let", "the", "loop"... are neither.
    """
    words = [w.strip(".!?,") for w in (objective or "").lower().split()]
    words = [w for w in words if w]
    if not words:
        return False
    if not any(w in _LEAVE_WORDS for w in words):
        return False
    return all(w in _LEAVE_WORDS or w in _VOCATIVES for w in words)
