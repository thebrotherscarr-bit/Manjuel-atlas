"""The seat rack: seats that rest until a flag calls them.

Session 6. `pipelines.md` listed eight steps and skipped six of them on an
ordinary run -- the transcript was mostly `_skipped_`, and adding a specialist
meant editing the pipeline even though the pipeline had nothing to say about
when it should fire. Models rest on a rack and load on call; skills rest in a
folder and bind on call; seats were the only one of the three that had to be
written into the running order in advance.

Now a seat declares its own summons, in its own file:

    **Wakes On:** technical
    **Wakes:** after Router

and never appears in `pipelines.md` at all. The spine holds only what runs
every time. Everything else is racked, and the engine pulls it in when the
flag is raised.

Placement is declared rather than emergent because one seat genuinely needs
it: `has_feed` is set before any seat runs, and the Security Guardian must go
FIRST or it is not a gate -- it would be reviewing material the Steward had
already read. `Wakes: first` is what keeps that guarantee.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .registry import Step

ANCHOR_FIRST = "first"
ANCHOR_LAST = "last"
ANCHOR_AFTER = "after"

_AFTER_RE = re.compile(r"^after[ \t]+(?P<seat>.+?)[ \t]*$", re.IGNORECASE)


class SeatingError(Exception):
    pass


@dataclass(frozen=True)
class Anchor:
    kind: str                 # first | last | after
    target: str | None = None  # seat name, for `after`

    def __str__(self) -> str:
        return f"{self.kind} {self.target}" if self.target else self.kind


def parse_anchor(text: str | None) -> Anchor:
    """`first` / `last` / `after <Seat>`. Absent means `last`.

    `last` is the safe default: a seat whose placement nobody thought about
    runs after the work rather than in front of the gate.
    """
    raw = " ".join((text or "").split()).strip()
    if not raw:
        return Anchor(ANCHOR_LAST)
    low = raw.lower()
    if low == ANCHOR_FIRST:
        return Anchor(ANCHOR_FIRST)
    if low == ANCHOR_LAST:
        return Anchor(ANCHOR_LAST)
    m = _AFTER_RE.match(raw)
    if m:
        return Anchor(ANCHOR_AFTER, m.group("seat").strip())
    raise SeatingError(
        f"unreadable Wakes anchor {raw!r} -- expected `first`, `last`, "
        f"or `after <Seat Name>`")


def wake_flags(agent) -> list[str]:
    """The flags that summon this seat.

    Comma-separated, because one seat can have genuinely distinct roles: the
    Security Guardian is a GATE on `has_feed` (untrusted material, before any
    seat reads it) and a REVIEW on `suspicious` (a seat saw something wrong in
    what a skill fetched). Same seat, same prompt, two different moments.
    """
    raw = getattr(agent, "wakes_on", None) or ""
    return [f.strip().lower() for f in raw.replace(";", ",").split(",") if f.strip()]


def rack_for(registry, spine: list[Step]) -> list:
    """Seats that rest off this pipeline's spine.

    A seat named explicitly in the pipeline is NOT racked for that run: the
    operator wrote it into the order on purpose, and an explicit listing beats
    a declared summons.
    """
    listed = {str(s).strip().lower() for s in spine}
    out = []
    for agent in registry.all():
        if not getattr(agent, "wakes_on", None):
            continue
        if agent.key in listed:
            continue
        out.append(agent)
    return out


def validate(registry) -> list[str]:
    """Check every racked seat's declaration at LOAD time.

    A seat whose anchor cannot be read must be refused when the ground is
    parsed, not discovered three seats into a conversation.
    """
    errors: list[str] = []
    names = {a.key for a in registry.all()}
    for agent in registry.all():
        flags = wake_flags(agent)
        if agent.wakes and not flags:
            errors.append(f"{agent.name}: has `Wakes:` but no `Wakes On:` -- "
                          f"it declares where to sit but nothing that seats it")
        if not flags:
            continue
        try:
            anchor = parse_anchor(agent.wakes)
        except SeatingError as exc:
            errors.append(f"{agent.name}: {exc}")
            continue
        if anchor.kind == ANCHOR_AFTER and anchor.target.strip().lower() not in names:
            errors.append(f"{agent.name}: wakes after `{anchor.target}`, "
                          f"which is not a seat in agents/")
    return errors


class Seating:
    """The running order, as it actually unfolds.

    Holds a mutable queue: the spine to begin with, plus whatever the rack
    hands over as flags are raised. A racked seat sits at most once per run --
    a seat that could re-summon itself on a flag it raises is an unbounded
    loop, and this chain already caps its tool steps for the same reason.
    """

    def __init__(self, spine: list[Step], rack: list):
        self.queue: list[Step] = list(spine)
        self.rack = list(rack)
        # (seat, flag) rather than seat: a seat with two distinct triggers may
        # sit twice, once per role, and still cannot loop on a single flag.
        self.summoned: set[tuple[str, str]] = set()
        self.cursor = -1

    # -- iteration ----------------------------------------------------

    def advance(self) -> Step | None:
        self.cursor += 1
        if self.cursor >= len(self.queue):
            return None
        return self.queue[self.cursor]

    def ran(self) -> set[str]:
        return {str(s).strip().lower() for s in self.queue[: self.cursor + 1]}

    def repeat(self, seat: str) -> bool:
        """Send ONE more pass through a seat that has already sat.

        The review->repeat edge of the operator's chain (sitting 64): the
        Evaluator could say a draft was wrong but never that it was
        UNFINISHED, so a critique naming missing work had nowhere to go.
        This gives it somewhere: the named seat takes the very next slot
        and works again with the critique in the record before it.

        ONCE. The same (seat, "repeat") key the summoner uses, so a second
        request is refused by the same arithmetic that stops a flag
        looping. A critique loop that could run twice would be a serial
        chain compounding its own error, which is the thing the estate is
        built not to do.
        """
        key = (str(seat).strip().lower(), "repeat")
        if key in self.summoned:
            return False
        self.summoned.add(key)
        self.queue.insert(self.cursor + 1, Step(seat=str(seat), when=None))
        return True

    # -- summoning ----------------------------------------------------

    def summon(self, flags: set[str]) -> list[str]:
        """Pull in every racked seat whose flag is now raised.

        Returns the names inserted, so the run can say WHY a seat appeared --
        a seat that shows up unannounced is worse than one that never came.
        """
        added: list[str] = []
        for agent in self.rack:
            for flag in wake_flags(agent):
                if (agent.key, flag) in self.summoned:
                    continue
                if flag not in flags:
                    continue
                self.summoned.add((agent.key, flag))
                self._insert(agent)
                added.append(f"{agent.name} (on {flag})")
        return added

    def _summoned_keys(self) -> set[str]:
        return {k for k, _ in self.summoned}

    def _insert(self, agent) -> None:
        anchor = parse_anchor(getattr(agent, "wakes", None))
        step = Step(seat=agent.name, when=None)

        if anchor.kind == ANCHOR_LAST:
            self.queue.append(step)
            return

        if anchor.kind == ANCHOR_FIRST:
            # As early as it can still legally go. Before anything has run
            # that is genuinely first; mid-run the past is not rewritable, so
            # it takes the very next slot and the run records that it was late.
            self.queue.insert(self.cursor + 1, step)
            return

        target = (anchor.target or "").strip().lower()
        racked = self._summoned_keys()
        for i in range(self.cursor + 1, len(self.queue)):
            if str(self.queue[i]).strip().lower() != target:
                continue
            # Skip past seats already summoned behind this same anchor, so two
            # seats both anchored `after Router` keep their rack order instead
            # of the second one jumping in front of the first.
            j = i + 1
            while j < len(self.queue) and str(self.queue[j]).strip().lower() in racked:
                j += 1
            self.queue.insert(j, step)
            return
        # Anchor seat is behind us (or absent): next slot is as close as we get.
        self.queue.insert(self.cursor + 1, step)
