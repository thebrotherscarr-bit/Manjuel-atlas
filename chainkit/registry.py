"""Parse agents.md into Agent objects.

This module is the ONLY place that knows about the agents.md file format.
Everything downstream consumes Agent dataclasses, which makes the pipeline
testable without a markdown file and the parser testable without a model.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from pathlib import Path

# "## Agent Name" at the start of a line.
_HEADING_RE = re.compile(r"^##[ \t]+(?P<name>.+?)[ \t]*$", re.MULTILINE)

# "- **Key:** value"  -- colon INSIDE the bold markers, as agents.md writes it.
# The trailing ':?' also tolerates "- **Key**: value" so either style parses.
_FIELD_RE = re.compile(
    r"^[ \t]*[-*][ \t]*\*\*(?P<key>[^*]+?)\*\*[ \t]*:?[ \t]*(?P<val>.*?)[ \t]*$",
    re.MULTILINE,
)


def _clean_key(raw: str) -> str:
    return raw.strip().rstrip(":").strip().lower()

_KNOWN_FIELDS = {"model target", "system prompt", "stage", "on fail", "when",
                 "context", "max tokens", "wakes on", "wakes", "voice",
                 "may call", "timeout"}

_VALID_STAGES = {"guard", "transform", "route", "gate", "deliver"}
_VALID_ON_FAIL = {"abort", "skip", "prompt"}

# ``` ... ``` fenced regions
_FENCE_RE = re.compile(r"^[ \t]*```.*?^[ \t]*```[ \t]*$", re.MULTILINE | re.DOTALL)


def _mask_code_fences(text: str) -> str:
    """Blank out fenced code blocks, preserving length and line structure.

    Documentation in agents.md legitimately contains example '## Agent Name'
    and '- **Model Target:**' lines inside fences. Masking (rather than
    stripping) keeps every character offset valid, so the system-prompt
    slices taken later still line up with the original text.
    """

    def blank(m: re.Match) -> str:
        return "".join("\n" if c == "\n" else " " for c in m.group(0))

    return _FENCE_RE.sub(blank, text)


class RegistryError(Exception):
    """Raised when agents.md cannot be parsed into a usable registry."""


@dataclass(frozen=True)
class Agent:
    name: str
    model: str
    system_prompt: str
    stage: str = "transform"
    on_fail: str = "prompt"
    when: str | None = None
    # A racked seat: rests off the spine until `wakes_on` is raised, then
    # slots in where `wakes` says. See seating.py.
    wakes_on: str | None = None
    wakes: str | None = None
    # SAPI voice for anything this seat says aloud. A substring is enough
    # ("zira" finds "Microsoft Zira Desktop"); absent = the system default.
    voice: str | None = None
    context: int | None = None  # num_ctx; None = leave Ollama's default
    max_tokens: int | None = None  # num_predict; caps how long a seat may run on
    # Seconds one call to this seat may take, at most. None = the ceiling
    # (runtime.SEAT_TIMEOUT). The operator's shape, 2026-09-08: a door and a
    # router bounded tight, the court's seats given the room they measure.
    timeout: float | None = None
    # Skills this seat may call natively. Absent = NONE, deliberately: a
    # capability is granted, never assumed. `all` gives the whole library --
    # the Router's job. The same shape as REVIEW_ONLY_SKILLS, which has
    # confined the counsel table since sitting 39; this makes it per-seat.
    may_call: tuple = ()

    def can_call(self, keyword: str, every: set[str] | None = None) -> bool:
        """Whether this seat is cleared for one skill."""
        if not self.may_call:
            return False
        if "all" in self.may_call:
            return keyword in every if every is not None else True
        return keyword.strip().lower() in self.may_call

    def callable_set(self, every: set[str]) -> set[str]:
        """What this seat may call, resolved against the live library."""
        if not self.may_call:
            return set()
        if "all" in self.may_call:
            return set(every)
        return {k for k in self.may_call if k in every}

    @property
    def key(self) -> str:
        return self.name.strip().lower()


def _normalize_model(tag: str) -> str:
    """Ollama treats a bare name as ':latest'. Normalize so lookups match."""
    tag = tag.strip()
    return tag if ":" in tag else f"{tag}:latest"


def _parse_section(name: str, body: str, body_raw: str, warnings: list[str]) -> Agent | None:
    """`body` is fence-masked (for scanning); `body_raw` is original (for slicing)."""
    fields: dict[str, str] = {}
    prompt_start: int | None = None
    prompt_field_end: int | None = None

    for m in _FIELD_RE.finditer(body):
        key = _clean_key(m.group("key"))
        val = m.group("val").strip()

        if key == "system prompt":
            # The prompt is the free text that follows this marker line.
            prompt_start = m.end()
            prompt_field_end = m.end()
            continue

        if key not in _KNOWN_FIELDS:
            warnings.append(f"[{name}] ignoring unknown field '{m.group('key').strip()}'")
            continue

        fields[key] = val

    # A heading with no declaration lines at all is prose, not a malformed
    # agent -- index files and doc sections use headings freely. Sections that
    # DO carry fields are held to the full contract, so a typo'd Model Target
    # still errors rather than vanishing.
    if not fields and prompt_start is None:
        return None

    if "model target" not in fields or not fields["model target"]:
        raise RegistryError(f"Agent '{name}' is missing a '- **Model Target:**' line.")

    if prompt_start is None:
        raise RegistryError(f"Agent '{name}' is missing a '- **System Prompt:**' line.")

    # Guard against a field appearing AFTER the system prompt marker, which
    # would silently get swallowed into the prompt text.
    trailing = _FIELD_RE.search(body, prompt_field_end or 0)
    if trailing is not None:
        raise RegistryError(
            f"Agent '{name}': '- **{_clean_key(trailing.group('key'))}:**' appears after "
            f"'System Prompt'. System Prompt must be the LAST field in a section, "
            f"because everything after it is treated as prompt text."
        )

    # Slice from the RAW body so fenced examples inside a prompt survive intact.
    system_prompt = body_raw[prompt_start:].strip()
    # A seat whose prompt is exactly BAKED carries its soul in its model's
    # own weights (a compiled Modelfile). The harness then sends NO system
    # message at all -- sending one, even empty, would REPLACE the bake.
    if system_prompt.upper() == "BAKED":
        system_prompt = ""
    elif not system_prompt:
        raise RegistryError(f"Agent '{name}' has an empty system prompt.")

    stage = fields.get("stage", "transform").strip().lower()
    if stage not in _VALID_STAGES:
        warnings.append(
            f"[{name}] unrecognized stage '{stage}', treating as 'transform'. "
            f"Valid: {', '.join(sorted(_VALID_STAGES))}"
        )
        stage = "transform"

    on_fail = fields.get("on fail", "prompt").strip().lower()
    if on_fail not in _VALID_ON_FAIL:
        warnings.append(
            f"[{name}] unrecognized on-fail '{on_fail}', treating as 'prompt'. "
            f"Valid: {', '.join(sorted(_VALID_ON_FAIL))}"
        )
        on_fail = "prompt"

    when = fields.get("when") or None
    wakes_on = (fields.get("wakes on") or "").strip() or None
    wakes = (fields.get("wakes") or "").strip() or None
    voice = (fields.get("voice") or "").strip() or None

    max_tokens: int | None = None
    raw_max = fields.get("max tokens", "").strip()
    if raw_max:
        try:
            max_tokens = int(raw_max.replace("_", "").replace(",", ""))
            if max_tokens <= 0:
                raise ValueError
        except ValueError:
            warnings.append(f"[{name}] max tokens '{raw_max}' is not a positive integer; ignoring.")
            max_tokens = None

    context: int | None = None
    raw_ctx = fields.get("context", "").strip()
    if raw_ctx:
        try:
            context = int(raw_ctx.replace("_", "").replace(",", ""))
            if context <= 0:
                raise ValueError
        except ValueError:
            warnings.append(f"[{name}] context '{raw_ctx}' is not a positive integer; ignoring.")
            context = None

    timeout: float | None = None
    raw_to = fields.get("timeout", "").strip()
    if raw_to:
        try:
            timeout = float(raw_to.replace("_", "").replace(",", "").rstrip("s"))
            if timeout <= 0:
                raise ValueError
        except ValueError:
            warnings.append(f"[{name}] timeout '{raw_to}' is not a positive number of seconds; ignoring.")
            timeout = None

    return Agent(
        name=name.strip(),
        model=_normalize_model(fields["model target"]),
        system_prompt=system_prompt,
        stage=stage,
        on_fail=on_fail,
        when=when,
        wakes_on=wakes_on,
        wakes=wakes,
        voice=voice,
        context=context,
        max_tokens=max_tokens,
        timeout=timeout,
        may_call=_parse_may_call(fields.get("may call", "")),
    )


def _parse_may_call(raw: str) -> tuple:
    """`- **May Call:** ground_read, read_file` -> ('ground_read','read_file').

    Absent or empty is an empty tuple, and an empty tuple means NONE. A seat
    is granted a capability; it never inherits one by silence.
    """
    return tuple(k for k in
                 (p.strip().lower().strip("`") for p in
                  re.split(r"[,\s]+", str(raw or ""))) if k)


# "## Pipeline: name"  /  "## Pipeline name"
_PIPELINE_RE = re.compile(r"^##[ \t]+Pipeline[ \t]*:?[ \t]+(?P<name>.+?)[ \t]*$", re.MULTILINE)
# "1. Seat Name   (when: flag)"  /  "1. Seat Name   (any note)"  /  "- Seat Name"
# The parenthetical is a note UNLESS it says `when:` -- a step-level condition,
# which is what lets one seat appear twice in a pipeline under different rules
# (the Steward answers at the front, then reports back only if work happened).
_STEP_RE = re.compile(
    r"^[ \t]*(?:\d+[.)]|[-*])[ \t]+(?P<seat>[^(\n]+?)[ \t]*(?:\((?P<note>[^)]*)\))?[ \t]*$",
    re.MULTILINE)
_STEP_WHEN_RE = re.compile(r"when[ \t]*:[ \t]*(?P<flag>[A-Za-z0-9_\-]+)", re.IGNORECASE)


@dataclass(frozen=True)
class Step:
    """One line of a pipeline: which seat, and any condition set HERE."""
    seat: str
    when: str | None = None

    def __str__(self) -> str:
        return self.seat


class PipelineBook:
    """Pipeline order, read from markdown instead of hardcoded in Python.

    Adding a pipeline becomes editing a file and running /reload -- the last
    piece of "the markdown is the source of truth, Python is only the engine".
    """

    def __init__(self, order: dict[str, list[str]], default: str, source: Path,
                 warnings: list[str]):
        self.order = order
        self.default = default
        self.source = source
        self.warnings = warnings

    @classmethod
    def load(cls, path: str | Path, registry: "AgentRegistry" | None = None) -> "PipelineBook":
        path = Path(path)
        if not path.exists():
            raise RegistryError(f"Pipeline book not found: {path.resolve()}")

        text = _mask_code_fences(path.read_text(encoding="utf-8"))
        marks = list(_PIPELINE_RE.finditer(text))
        if not marks:
            raise RegistryError(
                f"No pipelines found in {path.name}. Expected '## Pipeline: <name>' sections."
            )

        # A later heading of ANY level ends the section, so prose after the
        # step list is not swallowed as steps.
        stops = [m.start() for m in re.finditer(r"^##+[ \t]", text, re.MULTILINE)]
        order: dict[str, list[str]] = {}
        warnings: list[str] = []

        for m in marks:
            name = m.group("name").strip().lower()
            end = next((s for s in stops if s > m.start()), len(text))
            # Only the FIRST contiguous run of step lines counts. Prose
            # bullets below the list are commentary, not seats -- without this
            # a line like "- an ordinary question: Guardian -> Steward" is read
            # as a seat and refuses the whole book.
            steps: list[Step] = []
            started = False
            for line in text[m.end():end].splitlines():
                if not line.strip():
                    # A blank line CLOSES the list. Prose bullets further down
                    # are commentary; without this they are read as seats.
                    if started:
                        break
                    continue
                sm = _STEP_RE.match(line)
                if sm and sm.group("seat").strip():
                    started = True
                    wm = _STEP_WHEN_RE.search(sm.group("note") or "")
                    steps.append(Step(sm.group("seat").strip(),
                                      wm.group("flag").lower() if wm else None))
                elif started:
                    break
            if not steps:
                warnings.append(f"pipeline '{name}' lists no seats; ignored")
                continue
            if name in order:
                raise RegistryError(f"{path.name}: pipeline '{name}' is defined twice.")
            order[name] = steps

        if not order:
            raise RegistryError(f"{path.name}: no usable pipelines.")

        if registry is not None:
            for pname, steps in order.items():
                for st in steps:
                    seat = st.seat
                    if not registry.has(seat):
                        raise RegistryError(
                            f"{path.name}: pipeline '{pname}' names seat '{seat}', "
                            f"which no file in agents/ declares."
                        )

        default = "default" if "default" in order else next(iter(order))
        return cls(order, default, path, warnings)

    def get(self, name: str) -> list[Step]:
        steps = self.order.get(name.strip().lower())
        if steps is None:
            raise RegistryError(
                f"Unknown pipeline '{name}'. Available: {', '.join(sorted(self.order))}"
            )
        return list(steps)

    def names(self) -> list[str]:
        return sorted(self.order)

    def __contains__(self, name: str) -> bool:
        return name.strip().lower() in self.order

    def __len__(self) -> int:
        return len(self.order)


class AgentRegistry:
    """Case-insensitive lookup over the agents defined in agents.md."""

    def __init__(self, agents: list[Agent], warnings: list[str], source: Path):
        self._agents = {a.key: a for a in agents}
        self.warnings = warnings
        self.source = source
        # What agents/*.md DECLARES, kept apart from what the seats are
        # running. `override_model` moves the live seats for one sitting; it
        # must not be able to move the record. Anything that WRITES a file
        # about this ground reads the declaration, never the live model --
        # rack.md folded a `/model` override to disk as ground truth on
        # 2026-09-01 (sitting 57) precisely because it read the live one.
        self._declared = {k: a.model for k, a in self._agents.items()}
        self.override = ""

        if not self._agents:
            raise RegistryError(f"No agents found in {source}. Expected '## Agent Name' sections.")

    @classmethod
    def _parse_file(cls, path: Path, warnings: list[str]) -> list[Agent]:
        text = path.read_text(encoding="utf-8")
        masked = _mask_code_fences(text)
        agents: list[Agent] = []

        headings = list(_HEADING_RE.finditer(masked))
        for i, m in enumerate(headings):
            name = m.group("name").strip()

            # Reserved for the pipeline-order section (design doc section 3, build step 6).
            if name.lower().startswith("pipeline"):
                continue

            end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
            try:
                agent = _parse_section(name, masked[m.end():end], text[m.end():end], warnings)
            except RegistryError as exc:
                raise RegistryError(f"{path.name}: {exc}") from exc
            if agent is not None:
                agents.append(agent)

        return agents

    @classmethod
    def load(cls, path: str | Path = "agents") -> AgentRegistry:
        """Load from a directory of per-agent .md files, or a single .md file.

        A directory keeps one seat per file, which scales past the point where
        a single manifest becomes unreadable. Files are read in sorted order;
        two files defining the same agent name is an error, not a silent
        last-one-wins.
        """
        path = Path(path)
        if not path.exists():
            raise RegistryError(f"Agent manifest not found: {path.resolve()}")

        warnings: list[str] = []
        agents: list[Agent] = []
        origin: dict[str, str] = {}

        files = sorted(path.glob("*.md")) if path.is_dir() else [path]
        if path.is_dir() and not files:
            raise RegistryError(f"No .md agent files found in {path.resolve()}")

        for f in files:
            for agent in cls._parse_file(f, warnings):
                if agent.key in origin:
                    raise RegistryError(
                        f"Agent '{agent.name}' is defined twice: "
                        f"{origin[agent.key]} and {f.name}."
                    )
                origin[agent.key] = f.name
                agents.append(agent)

        return cls(agents, warnings, path)

    def get(self, name: str) -> Agent:
        agent = self._agents.get(name.strip().lower())
        if agent is None:
            available = ", ".join(sorted(a.name for a in self._agents.values()))
            raise RegistryError(
                f"Pipeline references agent '{name}', which is not defined in "
                f"{self.source}. Available: {available}"
            )
        return agent

    def has(self, name: str) -> bool:
        return name.strip().lower() in self._agents

    def all(self) -> list[Agent]:
        return sorted(self._agents.values(), key=lambda a: a.name)

    def models(self) -> set[str]:
        return {a.model for a in self._agents.values()}

    def declared_models(self) -> dict[str, str]:
        """seat name -> the model `agents/*.md` declares for it.

        Unmoved by `override_model`. Use this, never `all()`, when writing a
        file that describes this ground: an override is one sitting's choice
        and a written record outlives the sitting.
        """
        return {a.name: self._declared.get(k, a.model)
                for k, a in self._agents.items()}

    def override_model(self, tag: str) -> list[tuple[str, str, str]]:
        """Run every seat on ONE model for this sitting.

        The declared `Model Target:` in agents/*.md stays the default and is
        never written to: an override lives in the session and dies with it,
        so a sitting can be tried on a bigger model without a file edit the
        operator then has to remember to undo. `/reload` reapplies it; the
        next launch does not.

        `self.override` carries the tag so a writer can SAY an override is on
        rather than silently record it as the declaration -- see
        `declared_models`.

        Returns (seat, from, to) for every seat it moved -- including the
        specialists. A seat is on qwen2.5-coder or qwen3.5:9b for a reason,
        and swapping it must be visible rather than quietly total.
        """
        tag = _normalize_model(tag)
        moved: list[tuple[str, str, str]] = []
        for k, a in list(self._agents.items()):
            if a.model != tag:
                moved.append((a.name, a.model, tag))
                self._agents[k] = replace(a, model=tag)
        self.override = tag
        return sorted(moved)

    def __len__(self) -> int:
        return len(self._agents)
