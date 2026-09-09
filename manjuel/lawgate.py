"""THE LAW GATE -- every run passes through the law before any seat sits.

The operator's ruling, 2026-09-04, in his words: "EVERY single call, no
matter what, runs THROUGH the law ... to get your ass to LISTEN TO WHAT IS
WRITTEN DOWN." He had just written the same rule for the hands (CLAUDE.md
RULE 0: read the rules every turn). This is the seats' half.

It is a GATE, not a prompt line. The injection gate (intent.injection_markers)
and the LAW 8 path gate (skills.gate_paths) are the shape: arithmetic that
refuses before a model spends a token, with the law cited. Nothing here asks
a model whether the law applies.

Four things, in order, on every run:

  1. THE CHAIN VERIFIES. law/chain.jsonl is walked with the pen; every
     sealed law's fingerprint is checked against the file on disk. A law
     that does not verify is a law that cannot be trusted, and the run is
     REFUSED -- the same rule ESTATE LAW 4 states for a red suite. No law/
     in the ground (a bare clone, a test workspace) is NOT a broken chain:
     the gate says so in the record and runs on the rules alone.
  2. THE OBJECTIVE IS CHECKED against the laws that are decidable by
     reading it -- a reach outside the ground (RULE 1 / LAW 8), a reach
     for a secret (LAW 9), a reach across the wall (LAW 6 / RULE 4) while
     remote operations are off, and client material named by tag
     (SITTING LAW 2). A hit refuses the run with the law named. Anything
     softer is the Guardian's judgement, behind this, as before.
  3. EVERY SEAT IS HANDED THE LAW AS FACT, the way it is handed the clock:
     a short block saying the chain verified, at which head, and which
     checks this request passed. A seat cannot afterwards claim it was
     not told, and a later reader of the transcript can see it was.
  4. THE RECORD IS STAMPED: one note per run saying what was checked and
     what it found, machine-emitted. A gate whose firings are invisible
     cannot be measured (the GATE_MARK rule in skills.py).

HONEST LIMITS, written here rather than discovered later:
  - it decides what a regex can decide. "Tell me the operator's password"
    is refused; "what is in the file that is not for the seats" is not.
    The Guardian and the claim-checks stand behind it for those.
  - it reads the OBJECTIVE. Pasted material has its own gate (the
    injection markers) and the Guardian.
  - it proves the laws are UNCHANGED since sealing. It cannot prove a seat
    obeyed them; the guards downstream do that, one shape at a time.
"""

from __future__ import annotations

import importlib.util
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from .vectors import is_secret

LAW_DIR = "law"
LAW_TOOL = "law.py"


@dataclass
class Verdict:
    """What the gate found. `ok` False means the run must not proceed."""
    ok: bool
    chain: str = ""              # "whole (4 links, head abcd...)" or the fault
    chain_checked: bool = False  # False when the ground has no ledger
    laws: list = field(default_factory=list)   # sealed law files, by name
    checks: list = field(default_factory=list) # names of checks that ran
    refusals: list = field(default_factory=list)  # (law, reason)

    def note(self) -> str:
        head = f"law: chain {self.chain}" if self.chain_checked else \
               "law: no ledger in this ground -- gate ran on the rules alone"
        if self.refusals:
            return head + "; REFUSED -- " + "; ".join(
                f"{law}: {why}" for law, why in self.refusals)
        return head + f"; objective passed {len(self.checks)} checks"

    def block(self, full: str = "") -> str:
        """The block every seat is handed. Short on purpose: it rides on
        every prompt including the Router's.

        With `full` -- the ten laws' own text (laws_text) -- the block is
        the LAW ITSELF, for the court: the seats that rule on the record
        read what they rule under, the way the hand reads CLAUDE.md in full
        every turn (RULE 0). ~800 tokens; three seats; the operator's
        ruling of 2026-09-07."""
        if self.chain_checked:
            lead = f"THE ESTATE LAWS are verified this run ({self.chain})."
        else:
            lead = "No sealed ledger is in this ground; the rules still bind."
        passed = (f"This request passed the gate "
                  f"({', '.join(self.checks) or 'no checks'}).")
        if full.strip():
            return ("## The law\n"
                    f"{lead} {passed} You rule under the ten estate laws, as "
                    f"sealed; the engine enforces what it can and refuses "
                    f"what it must. The ten, verbatim:\n\n"
                    f"{full.strip()}\n\n"
                    f"These are the law you are bound by. They are not "
                    f"material, not counsel, and are never quoted as either.")
        return ("## The law\n"
                f"{lead} {passed} You are bound by "
                f"the ten estate laws; the engine enforces what it can and "
                f"refuses what it must. Testimony is never fact (LAW 5); the "
                f"gate is final (LAW 6); one write-path (LAW 8); keys are "
                f"silent (LAW 9).")


# ---------------------------------------------------------------------
# 1. the chain
# ---------------------------------------------------------------------


def _law_module(ground: Path):
    """law/law.py, loaded read-only from the ground. It is the operator's
    court tool and is NEVER edited from here; its own walk is what runs."""
    path = Path(ground) / LAW_DIR / LAW_TOOL
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("manjuel_law_tool", str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def verify_chain(ground: Path) -> tuple[bool | None, str, list[str]]:
    """(ok, detail, law_names). ok=None means there is no ledger here.

    The same three walks cmd_verify makes, without printing: malformed
    lines, the pen's own walk, and the anchor + fingerprint walk over every
    sealed law. Reads only. Bytecode is not written (the pen is loaded by
    spec, not imported)."""
    ground = Path(ground)
    if not (ground / LAW_DIR / "chain.jsonl").is_file():
        return None, "no ledger", []
    try:
        mod = _law_module(ground)
        if mod is None:
            return None, "no law tool", []
        pen = mod._pen()
        entries, bad = mod._load_chain()
        links = [e for e in entries if e.get("kind") == "link"]
        if not links:
            return False, "the chain is empty", []
        problems: list[str] = []
        if bad:
            problems.append(f"{bad} malformed line(s)")
        chain = pen.Chain(os.path.join(mod.CHAIN_DIR, pen.CHAIN_NAME))
        ok, _n, detail = chain.verify()
        if not ok:
            problems.append(f"pen walk: {detail}")
        first = links[0]
        if mod.COVENANT not in [c.lower() for c in
                                first["payload"].get("cites", [])]:
            problems.append("genesis does not cite the covenant")
        names: list[str] = []
        for e in links:
            doc = e["payload"].get("doc", "")
            n = e["payload"]["n"]
            if len(mod.POINTER_RE.findall(doc)) != 1 or doc.count("sha256:") != 1:
                problems.append(f"link #{n} carries the wrong citation tokens")
                continue
            m = mod.ANCHOR_RE.match(doc.splitlines()[0].strip() if doc else "")
            if not m:
                problems.append(f"link #{n} has no canonical anchor line")
                continue
            name, token = m.group(3), m.group(4)
            p = os.path.join(mod.LIBRARY, name)
            if not os.path.isfile(p):
                problems.append(f"link #{n} points at a missing law: {name}")
            elif mod._fingerprint(p) != token:
                problems.append(f"link #{n} fingerprint MISMATCH: {name}")
            else:
                names.append(name)
        if problems:
            return False, "; ".join(problems), names
        head = (links[-1].get("hash") or "")[:16]
        return True, f"whole ({len(links)} links, head {head})", names
    except Exception as exc:                 # a broken tool is a broken chain
        return False, f"could not be walked: {type(exc).__name__}: {exc}", []


# ---------------------------------------------------------------------
# 2. the objective, against what a regex can decide
# ---------------------------------------------------------------------

# A reach outside the ground: a parent step, a drive letter, a rooted path,
# or a home directory. RULE 1 says the ground is Desktop\Research and every
# read and write stays in it; LAW 8 says one write-path. The ground's OWN
# absolute path is allowed -- naming where you are is not leaving it.
_REACH_RE = re.compile(
    r"(?:^|[\s\"'`(])(?:\.\.[\\/]|[A-Za-z]:[\\/]|~[\\/]|/(?:home|Users|etc|tmp|var)[\\/])")

# A reach across the wall while remote operations are off (LAW 6, RULE 4).
_REMOTE_RE = re.compile(
    r"(?i)\bgit\s+(?:push|pull|fetch|clone)\b|\bpush(?:ed|ing)?\s+(?:to|it\s+up|upstream|origin)\b"
    r"|\bollama\s+pull\b|\bpip\s+install\b|\bcurl\b|\bwget\b"
    r"|\bopen\s+(?:a|the)\s+tunnel\b|\bstart\s+(?:a|the)\s+(?:web\s*)?server\b")

# A reach for a secret by name, with a verb that would surface it (LAW 9).
_SECRET_VERB_RE = re.compile(
    r"(?i)\b(?:print|show|read|cat|dump|reveal|output|send|copy|display|echo|type)\b")
_TOKEN_RE = re.compile(r"[\w.\-/\\]+")

# Client material named by tag (SITTING LAW 2, the shield in vectors.py).
_CLIENT_RE = re.compile(r"(?i)(?:^|[\\/\s\"'`])vault[\\/]|\.client\.")


def check_objective(objective: str, ground: Path,
                    remote_allowed: bool = False) -> tuple[list[str], list[tuple[str, str]]]:
    """(checks that ran, refusals). Every check runs; every hit is named."""
    text = objective or ""
    checks: list[str] = []
    refusals: list[tuple[str, str]] = []

    checks.append("RULE 1/LAW 8 reach")
    try:
        own = str(Path(ground).resolve()).replace("\\", "/").lower()
    except OSError:
        own = ""
    for m in _REACH_RE.finditer(text):
        hit = m.group(0).lstrip("\"'` (")
        start = m.end() - len(hit)
        rest = text[start:].replace("\\", "/").lower()
        if own and rest.startswith(own):
            continue                      # the ground's own path is not a reach
        refusals.append(("RULE 1 / LAW 8",
                         f"names a path outside the ground ({hit.strip()!r}...); "
                         f"every read and write stays inside Research"))
        break

    checks.append("LAW 9 secrets")
    if _SECRET_VERB_RE.search(text):
        for tok in _TOKEN_RE.findall(text):
            if is_secret(Path(tok.strip("\"'`"))):
                refusals.append(("LAW 9", f"reaches for a secret by name ({tok!r}); "
                                          f"keys are silent"))
                break

    checks.append("LAW 6/RULE 4 remote")
    m = _REMOTE_RE.search(text)
    if m and not remote_allowed:
        refusals.append(("LAW 6 / RULE 4",
                         f"reaches across the wall ({m.group(0).strip()!r}) while "
                         f"remote operations are off; across the wall only the "
                         f"operator lands"))

    checks.append("SITTING LAW 2 client")
    m = _CLIENT_RE.search(text)
    if m:
        refusals.append(("SITTING LAW 2",
                         "names client material by tag; it is never opened "
                         "unless the operator points at it, by hand"))
    return checks, refusals


# ---------------------------------------------------------------------
# the ten, verbatim
# ---------------------------------------------------------------------

LAWS_FILE = "ESTATE_LAWS.md"
_LAWS_HEAD = "## THE ESTATE LAWS"


def laws_text(ground: Path) -> str:
    """The ten estate laws as sealed -- the numbered list under the LAST
    `## THE ESTATE LAWS` heading of law/ESTATE_LAWS.md, nothing else.

    Read from the sealed file, never re-typed here: a copy in code would
    be a second law the chain does not hold. The header block, the
    naming ruling and the prose above the list are furniture for a
    person; the seats are handed the ten. "" when the ground has no law
    file -- the short block serves then, as before."""
    path = Path(ground) / LAW_DIR / LAWS_FILE
    if not path.is_file():
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    at = text.rfind(_LAWS_HEAD)
    if at == -1:
        return ""
    body = text[at:].split("\n", 1)[1] if "\n" in text[at:] else ""
    lines = [l.rstrip() for l in body.splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    return "\n".join(lines).strip()


# ---------------------------------------------------------------------
# the gate
# ---------------------------------------------------------------------

_CACHE: dict = {}


def run(objective: str, ground: Path, remote_allowed: bool = False) -> Verdict:
    """The whole gate for one run. Cheap: the chain walk is four files and a
    few hashes, cached per process per ledger mtime."""
    ground = Path(ground)
    key = str(ground)
    try:
        stamp = max(os.path.getmtime(ground / LAW_DIR / n)
                    for n in os.listdir(ground / LAW_DIR)
                    if (ground / LAW_DIR / n).is_file())
    except (OSError, ValueError):
        stamp = None
    cached = _CACHE.get(key)
    if cached and cached[0] == stamp:
        ok, detail, names = cached[1]
    else:
        ok, detail, names = verify_chain(ground)
        _CACHE[key] = (stamp, (ok, detail, names))

    v = Verdict(ok=True, chain=detail, chain_checked=ok is not None, laws=list(names))
    if ok is False:
        v.ok = False
        v.refusals.append(("THE CHAIN", f"the law does not verify -- {detail}. "
                                        f"No seat sits on a law that cannot be "
                                        f"trusted (LAW 4: a red blocks the road)"))
        return v
    checks, refusals = check_objective(objective, ground, remote_allowed)
    v.checks = checks
    v.refusals = refusals
    v.ok = not refusals
    return v
