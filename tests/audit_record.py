"""Audit the record the estate has actually written.

    python tests/audit_record.py

THIS IS NOT THE STROKE SUITE, and the difference is the point.

The strokes test CODE: offline, deterministic, stubbed, and they gate a
change. This reads the REAL record -- 500+ transcripts, the seat log, the
sessions, the memory -- and REPORTS. It never gates anything, because the
corpus is the most ambient thing in the ground: it grows every sitting, and
an assertion over it would go red because the operator ran the CLI rather
than because code broke. Six of seven reds on 2026-09-02 came from strokes
reading ambient state; putting the corpus in there would have been the same
mistake at a larger scale.

What it is for:

  1. WELL-FORMEDNESS. Every transcript parses, every delivery is present,
     every field the format promises is there.
  2. CROSS-REFERENCES. Every path the seat log cites exists; every
     transcript has its prompts twin; every sitting is accounted for.
  3. THE SHIELD, over the whole accumulated record rather than a fixture.
     A secret or a client tag in any transcript is a real leak, and the
     corpus is where it would show.
  4. THE RETROACTIVE GUARD SWEEP -- the headline. Every fabrication gate
     in this estate was built from ONE transcript. Sweeping the corpus for
     the shape each gate now refuses turns "we fixed it" into "it happened
     N times in 532 runs, here are the paths, and this is what refuses it
     now." Evidence, in the estate's own idiom.

It writes tests/last_audit.md the way the suites write last_run.md: the
findings, with paths, and nothing about what was fine beyond the count.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from manjuel.vectors import is_protected, is_secret          # noqa: E402

REPORT = ROOT / "tests" / "last_audit.md"

# --- the transcript format, as transcript.py writes it ----------------
_WHEN = re.compile(r"^- \*\*when:\*\*\s*(?P<v>\S+)", re.MULTILINE)
_STAGES = re.compile(r"^- \*\*stages:\*\*\s*(?P<n>\d+)", re.MULTILINE)
_ELAPSED = re.compile(r"^- \*\*elapsed:\*\*\s*(?P<v>[\d.]+)s", re.MULTILINE)
_SECTION = re.compile(r"^## (?P<name>Objective|Stages|Delivery)\s*$", re.MULTILINE)
_STAGE_HEAD = re.compile(r"^### \d+\. (?P<seat>.+?) — `(?P<model>[^`]+)`\s*$",
                         re.MULTILINE)
_SKILLS = re.compile(r"^_[\d.]+s(?: · skills: (?P<s>[^_]*))?_\s*$", re.MULTILINE)

# --- the shapes the gates now refuse ----------------------------------
_FAILED_BANNER = "THIS TOOL FAILED"
_ALL_CLEAR = re.compile(
    r"(?i)\b(no (?:new )?(?:issues|concerns|problems|errors)"
    r"|everything (?:is|looks|seems) (?:as it should|fine|good|in order)"
    r"|all (?:is )?(?:well|clear|good)"
    r"|no discrepancies|functioning optimally|nothing to report)\b")
_CLAIMS_FILE = re.compile(
    r"(?i)(?:here (?:is|are) the (?:content|contents)|"
    r"the (?:content|contents) of|as on disk right now|"
    r"the file (?:says|reads|contains))\s*[:\-]?\s*[`'\"]?"
    r"(?P<f>[\w./\\-]+\.(?:md|py|txt|json|jsonl|us|toml|yml|yaml|csv))")
_RESULT_LINE = re.compile(
    r"(?m)^\s*\d+\.\s+(?P<p>\S+)\s+\[[^\]]*\][^\n]*?\bcosine\s+(?P<s>\d\.\d+)")
_CITED_PAIR = re.compile(
    r"[`'\"*]?(?P<f>[\w./\\-]+\.(?:md|py|txt|json|jsonl))[`'\"*]?"
    r"[^\n]{0,80}?\b(?P<s>[01]\.\d{2,4})")
READERS = {"semantic_search", "ground_read", "ground_list", "ground_report",
           "read_file", "list_directory", "git_status", "rack_list",
           "skill_report", "sitting", "when"}


class Finding:
    def __init__(self, kind, path, detail):
        self.kind, self.path, self.detail = kind, path, detail


def _sections(text: str) -> dict:
    """Split a transcript into its named sections."""
    marks = list(_SECTION.finditer(text))
    out = {}
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        out[m.group("name")] = text[m.end():end].strip()
    return out


def _skills_run(text: str) -> set:
    ran = set()
    for m in _SKILLS.finditer(text):
        for s in (m.group("s") or "").split(","):
            s = s.strip()
            if s:
                ran.add(s)
    return ran


def audit_transcripts(logs: Path) -> tuple[list, Counter]:
    findings: list[Finding] = []
    tally = Counter()
    prompts = logs / "_prompts"

    for f in sorted(logs.glob("*.md")):
        # logs/ holds MORE THAN RUNS. A parity report is a different kind of
        # document that lives in the same folder, and auditing it against
        # the run format produced six findings apiece about a file that was
        # never claiming to be a transcript. An audit that does not know
        # what it is reading is just a complaint.
        if f.name.startswith("parity_"):
            tally["parity reports"] += 1
            continue
        tally["transcripts"] += 1
        rel = f"logs/{f.name}"
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            findings.append(Finding("unreadable", rel, str(exc)))
            continue

        # 1. well-formedness. ONE finding per file, not one per field: a
        # document that is not in this format at all is a single fact, and
        # six lines saying so is noise that buries the three findings that
        # matter.
        missing = [n for n, rx in (("when", _WHEN), ("stages", _STAGES),
                                   ("elapsed", _ELAPSED)) if not rx.search(text)]
        secs = _sections(text)
        missing += [f"## {w}" for w in ("Objective", "Stages", "Delivery")
                    if w not in secs]
        if len(missing) >= 4:
            findings.append(Finding(
                "not a transcript", rel,
                f"missing {len(missing)} of the format's parts — written "
                f"before this format existed, or not a run at all"))
            continue
        if missing:
            findings.append(Finding("malformed", rel,
                                    f"missing: {', '.join(missing)}"))
        st = _STAGES.search(text)
        produced = int(st.group("n")) if st else 0
        if produced and not (secs.get("Delivery") or "").strip():
            findings.append(Finding("empty delivery", rel,
                                    f"{produced} stages and nothing delivered"))

        # 2. its prompts twin
        if prompts.is_dir() and not (prompts / f.name).exists():
            findings.append(Finding("no prompts twin", rel,
                                    "logs/_prompts/ has no file of this name"))

        # 3. the shield, over the real record
        if is_secret(f.name):
            findings.append(Finding("SECRET NAME", rel, "a transcript named as a secret"))
        head = text[:4000]
        if "[[CLIENT]]" in head:
            findings.append(Finding("CLIENT TAG", rel,
                                    "a transcript carrying the client tag"))

        # 4. the retroactive guard sweep
        body = secs.get("Stages", "") + "\n" + secs.get("Delivery", "")
        delivery = secs.get("Delivery", "")
        ran = _skills_run(text)

        if _FAILED_BANNER in text:
            tally["runs with a failed tool"] += 1
            hit = _ALL_CLEAR.search(delivery)
            if hit:
                tally["s68: all-clear over a failure"] += 1
                findings.append(Finding(
                    "s68 OMITTED FAILURE", rel,
                    f"a tool failed and the delivery says {hit.group(0)!r} "
                    f"— recompose now appends the failures to every such run"))

        claim = _CLAIMS_FILE.search(delivery)
        if claim and not (ran & READERS):
            tally["s56: file contents claimed with no read"] += 1
            findings.append(Finding(
                "s56 UNSUPPORTED CLAIM", rel,
                f"delivery presents `{claim.group('f')}` and no reading skill "
                f"ran — the claim-check now refuses this"))

        returned = {p.rsplit("/", 1)[-1].lower()
                    for p, _ in ((m.group("p").replace("\\", "/"), m.group("s"))
                                 for m in _RESULT_LINE.finditer(body))}
        if returned:
            for m in _CITED_PAIR.finditer(delivery):
                name = m.group("f").replace("\\", "/").rsplit("/", 1)[-1].lower()
                if name not in returned:
                    tally["s61: cited a result that did not exist"] += 1
                    findings.append(Finding(
                        "s61 BOGUS CITATION", rel,
                        f"delivery cites `{m.group('f')}` at {m.group('s')}, "
                        f"which this turn's search did not return — the "
                        f"citation-check now refuses this"))
                    break

    if prompts.is_dir():
        for p in sorted(prompts.glob("*.md")):
            tally["prompt files"] += 1
            if not (logs / p.name).exists():
                findings.append(Finding("orphan prompt", f"logs/_prompts/{p.name}",
                                        "no transcript of this name"))
    return findings, tally


def audit_seat_log(root: Path, logs: Path) -> tuple[list, Counter]:
    findings, tally = [], Counter()
    sl = root / "SEAT_LOG.md"
    if not sl.is_file():
        return [Finding("missing", "SEAT_LOG.md", "the toll book is not here")], tally
    text = sl.read_text(encoding="utf-8", errors="replace")
    tally["sittings tolled"] = len(re.findall(r"^## .+ — sitting \d+", text,
                                              re.MULTILINE))
    # ONLY the machine-written run lines:
    #     default · 2 stages · 34.7s · logs/<stamp>_<slug>.md
    # The first pass matched every `logs/...md` anywhere in the file, which
    # swept up paths written in PROSE -- including an outside hand's
    # abbreviated `logs/..._084646_run_the_rack.md` -- and reported a real
    # file as missing because a person had elided its middle. A citation in
    # a sentence is not a reference the machine made.
    for m in re.finditer(r"(?m)^\s+\S+ · \d+ stages? · [\d.]+s · "
                         r"(?P<p>logs/[^\s`]+\.md)\s*$", text):
        tally["run lines"] += 1
        if not (root / m.group("p")).exists():
            findings.append(Finding("dangling reference", "SEAT_LOG.md",
                                    f"cites {m.group('p')}, which is not on disk"))
    return findings, tally


def audit_sessions(root: Path) -> tuple[list, Counter]:
    findings, tally = [], Counter()
    p = root / "sessions" / "sessions.jsonl"
    if not p.is_file():
        return findings, tally
    for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        tally["session lines"] += 1
        try:
            json.loads(line)
        except ValueError as exc:
            findings.append(Finding("unparseable", f"sessions/sessions.jsonl:{i}",
                                    str(exc)[:100]))
    return findings, tally


def audit_memory(root: Path) -> tuple[list, Counter]:
    findings, tally = [], Counter()
    mem = root / "memory.md"
    if mem.is_file():
        text = mem.read_text(encoding="utf-8", errors="replace")
        entries = re.findall(r"^#{2,6} .+$", text, re.MULTILINE)
        tally["memory entries"] = max(0, len(entries) - 1)
        for block in re.split(r"(?m)^#{2,6} ", text)[2:]:
            head = block.splitlines()[0].strip() if block.strip() else "(blank)"
            if "provenance:" not in block:
                findings.append(Finding("unstamped memory", "memory.md",
                                        f"{head[:60]!r} carries no provenance"))
    pend = root / "memory" / "pending.jsonl"
    if pend.is_file():
        for i, line in enumerate(pend.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            tally["pending proposals"] += 1
            try:
                e = json.loads(line)
            except ValueError as exc:
                findings.append(Finding("unparseable",
                                        f"memory/pending.jsonl:{i}", str(exc)[:80]))
                continue
            if e.get("provenance") != "GENERATED":
                findings.append(Finding(
                    "pending not GENERATED", f"memory/pending.jsonl:{i}",
                    f"provenance is {e.get('provenance')!r}; a proposal a seat "
                    f"made is testimony until the operator lands it"))
    return findings, tally


def audit_worlds(root: Path) -> tuple[list, Counter]:
    """The shield where it matters most: nothing sealed may be indexed."""
    findings, tally = [], Counter()
    roots_file = root / "index_roots.txt"
    listed = []
    if roots_file.is_file():
        listed = [l.strip() for l in roots_file.read_text(encoding="utf-8").splitlines()
                  if l.strip() and not l.strip().startswith("#")]
    # Stated as a PROPERTY, naming no world: the bare parent is never a
    # root, and no listed root may reach into anything holding a vault/.
    # A rule written around one folder's name protects only that folder.
    for entry in listed:
        e = entry.replace("\\", "/").strip("/")
        p = root / e
        if e == "worlds" or (p.is_dir() and any(p.rglob("vault"))):
            findings.append(Finding(
                "SEALED WORLD INDEXED", "index_roots.txt",
                f"{entry!r} would sweep sealed data into the index"))
    # Every vault, wherever it is, is checked against the shield -- the
    # audit does not need to know whose it is, and must not read what is
    # inside one. Names and contents are never opened here: only the count,
    # and whether the shield claims each item.
    worlds = root / "worlds"
    if worlds.is_dir():
        for vault in worlds.rglob("vault"):
            if not vault.is_dir():
                continue
            for f in vault.rglob("*"):
                if f.is_file():
                    tally["sealed items"] += 1
                    if not is_protected(f, peek=False):
                        findings.append(Finding(
                            "SEALED ITEM UNPROTECTED",
                            "(a sealed item; path withheld)",
                            "inside a vault/ but is_protected() says "
                            "otherwise — check it by hand"))
    return findings, tally


def render(findings: list, tally: Counter) -> str:
    out = ["# Record audit", ""]
    for k in sorted(tally):
        out.append(f"- **{k}**: {tally[k]:,}")
    out.append("")
    if not findings:
        out.append("Nothing to report. The record is well-formed, its "
                   "references resolve, nothing sealed is exposed, and no "
                   "run in it shows a shape the gates now refuse.")
        return "\n".join(out) + "\n"

    by_kind: dict = {}
    for f in findings:
        by_kind.setdefault(f.kind, []).append(f)
    out.append(f"## {len(findings)} finding"
               f"{'' if len(findings) == 1 else 's'}, by kind")
    out.append("")
    for kind in sorted(by_kind, key=lambda k: -len(by_kind[k])):
        rows = by_kind[kind]
        out.append(f"### {kind} — {len(rows)}")
        out.append("")
        for f in rows[:25]:
            out.append(f"- `{f.path}` — {f.detail}")
        if len(rows) > 25:
            out.append(f"- ... and {len(rows) - 25} more")
        out.append("")
    return "\n".join(out) + "\n"


def main() -> int:
    logs = ROOT / "logs"
    findings, tally = [], Counter()
    if logs.is_dir():
        f, t = audit_transcripts(logs)
        findings += f
        tally += t
    for fn in (lambda: audit_seat_log(ROOT, logs), lambda: audit_sessions(ROOT),
               lambda: audit_memory(ROOT), lambda: audit_worlds(ROOT)):
        f, t = fn()
        findings += f
        tally += t

    page = render(findings, tally)
    try:
        REPORT.write_text(page, encoding="utf-8", newline="\r\n")
    except OSError:
        pass

    print()
    print("  manjuel — record audit")
    print()
    for k in sorted(tally):
        print(f"    {tally[k]:>7,}  {k}")
    print()
    print(f"  {len(findings)} finding{'' if len(findings) == 1 else 's'}."
          + ("  THE RECORD IS CLEAN." if not findings
             else f"  Written to tests/last_audit.md"))
    print()
    # REPORTS, NEVER GATES: a finding is a fact about the past, and the past
    # is not a reason to fail a run of the present. Exit 0 always.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
