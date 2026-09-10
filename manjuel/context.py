"""Run context: the accumulating state that flows through a pipeline.

This replaces the old string-passing chain. The critical property is that
`objective` and `feed` survive to the LAST stage -- previously the Delivery
Agent only ever saw the Quality Evaluator's rewrite, so the original topic
was gone by the time the report was formatted.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class StepResult:
    agent: str
    model: str
    output: str
    elapsed: float = 0.0
    prompt: str = ""
    tool_calls: list[str] = field(default_factory=list)
    # What the tools RETURNED at this seat, raw, one entry per call (the
    # review of 2026-09-08). The standup's number check reads these: a
    # number in the delivery that is in none of them was invented.
    tool_results: list[str] = field(default_factory=list)
    # The seat's DELIBERATION, kept for the record and shown to no one.
    # Sitting 79, the operator's ruling: a thinking seat's chain of thought
    # is evidence about why it chose what it chose, and it was being
    # collected and thrown away. It goes in the transcript ONLY -- never
    # into a later seat's prompt, the thread, or the delivery (sitting 47).
    thinking: str = ""
    error: str | None = None
    skipped: bool = False
    drift: float | None = None      # cosine vs the source material
    drifted: bool = False

    @property
    def ok(self) -> bool:
        return self.error is None and not self.skipped


def _entry(e):
    """(who, what, ts) from either the old 2-shape or the new 3-shape."""
    who, what = e[0], e[1]
    ts = float(e[2]) if len(e) > 2 and e[2] else 0.0
    return who, what, ts


def now_block(ts: float | None = None) -> str:
    """The present moment, stated as fact.

    The estate stamps everything -- transcripts, memory, the ledger, search
    hits ("written 2h ago") -- and then asked models to reason about
    recency with NO ANCHOR. A model with no clock falls back on its
    training-data sense of the present, which is how sitting 26 narrated a
    two-hour-old transcript as news. An age is meaningless without a now.

    Harness-emitted, like every other environment fact: the seats are TOLD
    the time, they never generate it (facts are read, not generated).

    It lives HERE, beside _age(), because both the pipeline and the skill
    library need it and this module imports nothing of ours -- a lower
    layer reaching up into pipeline.py to fetch a clock would invert the
    containment rule for the sake of one string.
    """
    from datetime import datetime
    dt = datetime.fromtimestamp(ts) if ts else datetime.now()
    # KEPT SHORT ON PURPOSE. It rides on every seat's prompt including the
    # Router's, whose budget is already mostly manifest -- the first draft
    # of this block put that prompt one token over its cap. Two sentences:
    # the moment, and what it is for.
    return ("## Now\n"
            f"{dt.strftime('%A %d %B %Y, %H:%M')} (local). Ages and dates "
            f"you are shown are measured against this moment. The record "
            f"describes what happened THEN; only this run is now.")


def _age(ts: float) -> str:
    """How long ago, in the units a person thinks in. '' when unknown."""
    if not ts:
        return ""
    sec = time.time() - ts
    if sec < 90:
        return ""      # a fresh turn needs no age label -- and models were
                       # mimicking "steward (just now):" into their replies
    if sec < 5400:
        return f"{int(sec // 60)}m ago"
    if sec < 129600:
        return f"{sec / 3600:.0f}h ago"
    return f"{sec / 86400:.0f}d ago"


# Below this cosine, the past has nothing to say and silence is the honest
# recall. Without a floor, top-k dragged the least-irrelevant noise into
# every turn -- a score only means something above a threshold (same lesson
# as the drift floors).
RECALL_FLOOR = 0.30


def detect_shift(thread: list, objective: str, embed=None,
                 floor: float = RECALL_FLOOR, min_words: int = 4) -> bool:
    """Has the operator changed the subject without saying so?

    True when a SUBSTANTIVE turn relates to nothing in the recent tail.
    Two guards, because a wrong continuation is cheaper than a wrong wipe:
    short turns never shift, and neither does ANY turn that points back into
    the conversation -- "and what did I just ask you about" is long, scores
    near zero against everything, and is entirely about the thread. Words
    like that/it/just/again are the conversation referring to itself.
    """
    words = (objective or "").lower().split()
    if embed is None or len(words) < min_words:
        return False
    _ANAPHORA = {"that", "it", "this", "just", "again", "earlier", "before",
                 "said", "mean", "meant"}
    if any(w.strip(".,!?") in _ANAPHORA for w in words):
        return False
    recent = thread[-4:]
    if not recent:
        return False
    try:
        from . import mathkit
        qv = embed(objective)
        best = 0.0
        for e in recent:
            who, what, _ts = _entry(e)
            try:
                best = max(best, mathkit.cosine(qv, embed(f"{who}: {what}")))
            except Exception:
                continue
        return best < floor
    except Exception:
        return False


def select_dialogue(thread: list, objective: str, embed=None,
                    tail: int = 4, k: int = 3, budget: int = 2400,
                    floor: float = RECALL_FLOOR, boundary: int = 0) -> list:
    """Choose what the seats actually see: RELEVANCE plus a recency tail.

    Carriage spent the whole window on the last N turns whether they mattered
    or not -- recency as a proxy for relevance, and an invented fact rode the
    window for its full length. Retrieval asks the embedder which PAST
    exchanges bear on THIS objective: the top-k relevant older turns, marked
    as recalled, plus the last `tail` entries verbatim for continuity.

    `embed` is injected (text -> vector) so this stays pure and testable.
    Embedder missing or failing => the old recency trim, unchanged.
    """
    thread = list(thread or [])
    # A topic boundary stops CARRIAGE, never memory: the tail is drawn only
    # from the current topic's segment, while retrieval may still reach
    # across the line for anything genuinely relevant.
    segment = thread[max(0, boundary):]
    # ADJACENCY IS STRUCTURAL, NOT SEMANTIC -- and this is where that was
    # lost. At the moment a shift is detected, _dialogue_for sets
    # boundary = len(dialogue): nothing is after the line yet, so `segment`
    # is empty and there is no recency tail at all. Retrieval was then the
    # only source, and it judges on RECALL_FLOOR -- the SAME floor
    # detect_shift just used to declare this turn related to nothing. The
    # two cannot disagree, so the seat was handed a ZERO-CHARACTER
    # conversation block and answered as a stranger. Measured on the record
    # 2026-09-09: every shift, every time; the 1-2 turn ceiling.
    #
    # A turn is about the turn before it BY DEFAULT, whatever the cosine
    # says -- 'yup' scores 0.324 against everything and is entirely about
    # what was just said. So the last exchange is kept for WHERE it is, not
    # for what it scores. Relevance is untouched: this adds one pair, the
    # old topic still does not ride, and with nothing behind it nothing is
    # kept.
    if not segment and thread:
        segment = thread[-2:]
    if embed is None:
        return segment[-max(tail, 8):]
    recent = segment[-tail:] if segment else []
    older = thread[: len(thread) - len(recent)]
    if not older:
        return recent
    try:
        from . import mathkit
        qv = embed(objective)
        scored = []
        for i, e in enumerate(older):
            who, what, _ts = _entry(e)
            try:
                scored.append((mathkit.cosine(qv, embed(f"{who}: {what}")), i))
            except Exception:
                continue
        scored.sort(reverse=True)
        picks = sorted(i for c, i in scored[:k] if c >= floor)
        recalled = []
        for i in picks:
            who, what, ts = _entry(older[i])
            age = _age(ts)
            label = f"(recalled, {age}) {who}" if age else f"(recalled) {who}"
            recalled.append((label, what))
    except Exception:
        return thread[-max(tail, 8):]

    out, used = [], 0
    for e in recalled + list(recent):
        who, what, _ts = _entry(e)
        used += len(who) + len(what)
        if used > budget and out:
            break
        out.append((who, what))
    return out


@dataclass
class RunContext:
    objective: str
    feed: str = ""
    # (who, what) pairs from earlier turns of a conversation. Empty for a
    # one-shot run. The Steward reads this; other seats do not need it.
    dialogue: list = field(default_factory=list)
    named_tool: str = ""   # skill the objective names outright, per intent.py
    # HOW that skill was chosen, when something other than the objective
    # naming it did the choosing. Sitting 81: one run logged both
    # "nothing run" and "objective names `skill_search`" and a reader
    # could not tell which happened. One turn, one account of the route.
    named_by: str = ""
    # Arguments a named skill's own **Takes:** rules found in the operator's
    # words. Carried so the payload survives the moment of recognition --
    # before this, matching a keyword threw the rest of the sentence away.
    tool_args: dict = field(default_factory=dict)
    # EVERY TOOL CALL THIS RUN HAS ALREADY MADE, keyed on the DECLARED
    # arguments (sitting 77). It lives on the run, not on the seat's tool
    # loop, because a run can seat a tool-capable seat more than once and
    # each seating used to start empty: 18 of the 235 runs with tools
    # since the dedup landed ran a skill twice, one of them a DOUBLED
    # COMMIT. A write empties the READS from it -- see run_pipeline.
    ran_calls: dict = field(default_factory=dict)
    # THE FILE THE OPERATOR NAMED, and whether it is really in the ground
    # (sitting 88, the operator: "a step that checks to see if it's even
    # viable and a returned argument"). Set by the pipeline at intent; read
    # by the Router's prompt and by the tool loop, where the operator's
    # real file outranks a seat's path that does not resolve (LAW 5).
    named_file: str = ""
    named_file_ok: bool | None = None
    # (skill, what went wrong) for every tool that failed or was refused
    # this run. Collected as it happens so the recompose is ARITHMETIC and
    # not a seat's recollection -- twice a closing seat reported all-clear
    # over a record holding failures it could see.
    failures: list = field(default_factory=list)
    # Sub-runs: how deep this context already is (0 = the operator's own
    # turn), and what scoped tasks ran beneath it. Depth is the bound --
    # a sub-task that could start a sub-task is an unbounded tree, and
    # LAW 7 says bounded everything.
    depth: int = 0
    sub_runs: list = field(default_factory=list)
    # A palette command's **Method:** -- a procedure the operator wrote, in
    # markdown, that rides with this run and is shown to every seat in it.
    # It is INSTRUCTION FROM THE OPERATOR, which is why it may say how to
    # work; nothing a model produces ever lands here.
    method: str = ""
    # THE LAW GATE's block for this run (lawgate.Verdict.block()): what the
    # chain verified to and which checks the objective passed. Handed to
    # every seat as fact, the way the clock is. Empty only when the gate
    # did not run (it always runs in run_pipeline).
    law: str = ""
    # The same verdict with the TEN ESTATE LAWS verbatim (lawgate.Verdict
    # .block(full=...)), for the court -- the seats that rule read the law,
    # not sixty words about it (2026-09-07, the CLAUDE.md system).
    law_full: str = ""
    # THE STANDING: what this sitting is FOR, from DAYBOOK.md's last entry
    # (seatlog.standing_block), set by the CLI at sitting open and handed to
    # the door and the court. CLAUDE.md READ FIRST for the seats: "you begin
    # with total amnesia; this is the only file that carries intent."
    standing: str = ""
    # THE SITTING STORY (0.1.6): what THIS sitting has done so far, read
    # off the ledger (seatlog.story_block), set by the CLI on every turn
    # and handed to the door and the court beside the standing. Sitting
    # 93's "what happened?" is answered from this, never from a search
    # over the whole record. Empty on the first run of a sitting.
    story: str = ""
    # (skill, file, part n, of N, stamp) for every read this run that came
    # back in PART -- a numbered window, a section, one definition, or the
    # map. Recorded as it happens (pipeline.note_partial_read) so the
    # recompose can say READ IN PART without any seat remembering to.
    partials: list = field(default_factory=list)
    # THE TURN DEADLINE (the operator, 2026-09-08: "600 max for the whole
    # system. there should never be more than 10 minutes between a
    # response, thats absurd"). The wall-clock moment this run stops
    # seating anyone: set by run_pipeline from pipeline.TURN_DEADLINE, and
    # inherited by a sub-run so a child cannot outlive its parent's turn.
    # None = no deadline (the suites set it explicitly when they test it).
    deadline_at: float | None = None
    # Seats that were NOT seated because the deadline had passed -- one
    # name per seat, recorded as it happens so the recompose can say OUT OF
    # TIME without any seat remembering to. Same arithmetic as failures.
    out_of_time: list = field(default_factory=list)
    review_only: bool = False  # counsel mode: the table reviews, never acts
    steps: list[StepResult] = field(default_factory=list)
    flags: set[str] = field(default_factory=set)
    artifacts: list[Path] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)   # e.g. a skipped drift check
    started_at: float = field(default_factory=time.time)

    # ---- accessors -------------------------------------------------

    def last_output(self) -> str:
        """Most recent successful output, or the feed if nothing ran yet."""
        for step in reversed(self.steps):
            if step.ok and step.output.strip():
                return step.output
        return self.feed

    def output_of(self, agent_name: str) -> str | None:
        key = agent_name.strip().lower()
        for step in reversed(self.steps):
            if step.agent.strip().lower() == key and step.ok:
                return step.output
        return None

    def completed(self) -> list[StepResult]:
        return [s for s in self.steps if s.ok]

    @property
    def elapsed(self) -> float:
        return time.time() - self.started_at

    # ---- prompt fragments ------------------------------------------

    def dialogue_block(self, budget: int = 2400) -> str:
        """The conversation so far, newest turns kept when over budget.

        Without this every /chat turn was a stranger: the Steward could not
        answer "and what did I just ask you?" -- which is the whole difference
        between chat and a series of one-shots.
        """
        if not self.dialogue:
            return ""
        lines = []
        for e in self.dialogue:
            who, what, ts = _entry(e)
            age = _age(ts)
            lines.append(f"{who} ({age}): {what}" if age else f"{who}: {what}")
        out: list[str] = []
        used = 0
        for line in reversed(lines):
            used += len(line) + 1
            if used > budget and out:
                out.append("(earlier turns trimmed)")
                break
            out.append(line)
        return "## Conversation so far\n" + "\n".join(reversed(out))

    def source_block(self) -> str:
        """Objective + feed. Injected into EVERY stage so it is never lost.

        With no feed the Source Material heading is OMITTED entirely. Printing
        "(no source material provided)" made seats read an empty section as a
        blocker -- session 5's Router refused to commit because it believed it
        had nothing to work on, when the objective was the whole request.
        """
        head = f"## Original Objective\n{self.objective.strip()}"
        if not self.feed.strip():
            return (head + "\n\n(No source material was pasted — the objective "
                    "above IS the whole request, and is enough to act on.)")
        return f"{head}\n\n## Source Material\n{self.feed.strip()}"

    def history_block(self, limit: int | None = None) -> str:
        """Prior stage outputs, oldest first."""
        done = self.completed()
        if limit is not None:
            done = done[-limit:]
        if not done:
            return "(no prior stages)"
        return "\n\n".join(
            f"### Output of {s.agent}\n{s.output.strip()}" for s in done
        )

    def slug(self, maxlen: int = 40) -> str:
        safe = "".join(c if c.isalnum() else "_" for c in self.objective.lower())
        safe = "_".join(filter(None, safe.split("_")))
        return safe[:maxlen] or "run"
