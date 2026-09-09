"""Memory: append-only, per-entry, tied to the session that produced it.

Two files, and the split is the point:

  memory.md            the LANDED record. Append-only (LAW 1). Indexed.
  memory/pending.jsonl entries a seat PROPOSED. Staged, not remembered.

A model calling `remember` stages; it does not land. The operator lands, and
is shown the entry before it goes in (LAW 6: the gate is final; "packets
prepare, the operator lands"). That keeps model testimony out of the record
unless a person put it there, without losing the proposal.

Entries carry their session and the run that produced them, so memory chunks
per entry rather than as one growing blob, and a retrieved line can be traced
back to the sitting it came from.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

MEMORY_FILE = "memory.md"
PENDING_FILE = Path("memory") / "pending.jsonl"

GENERATED = "GENERATED"   # model testimony
OPERATOR = "OPERATOR"     # the operator's own word

# THE KIND (2026-09-07, the operator: "we can parse through the memories and
# sort them later on ... guidance decision ruling learning, etc."). One word
# on each entry, set by the operator at landing, so memory can be sorted by
# what it IS. `note` when he does not say.
KINDS = ("guidance", "decision", "ruling", "learning", "outcome", "note")
DEFAULT_KIND = "note"

HEADER = (
    "# Memory\n\n"
    "Append-only. One entry per sitting-worth of thought, newest at the bottom.\n"
    "Entries stamped GENERATED are model testimony and are not fact until the\n"
    "record proves them. Entries stamped OPERATOR are the operator's own word.\n"
)

# "## <iso stamp> - <title>"  (the separator may be an em dash or a hyphen)
_ENTRY_RE = re.compile(
    r"^##[ \t]+(?P<stamp>\d{4}-\d{2}-\d{2}T[0-9:+\-Z.]+)[ \t]*[—-][ \t]*(?P<title>.*?)[ \t]*$",
    re.MULTILINE,
)


def new_session_id(ts: float | None = None) -> str:
    dt = datetime.fromtimestamp(ts) if ts else datetime.now()
    return "S" + dt.strftime("%Y%m%d-%H%M%S")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Entry:
    title: str
    body: str
    provenance: str = GENERATED
    session: str = ""
    run: str = ""
    stamp: str = ""
    kind: str = DEFAULT_KIND

    def __post_init__(self):
        if not self.stamp:
            self.stamp = _now()
        if not self.title:
            self.title = " ".join(self.body.split()[:8]) or "untitled"
        self.kind = (self.kind or DEFAULT_KIND).strip().lower() or DEFAULT_KIND

    def render(self) -> str:
        lines = [f"\n## {self.stamp} — {self.title}", f"- provenance: {self.provenance}",
                 f"- kind: {self.kind}"]
        if self.session:
            lines.append(f"- session: {self.session}")
        if self.run:
            lines.append(f"- run: {self.run}")
        lines += ["", self.body.strip(), ""]
        return "\n".join(lines)

    def preview(self) -> str:
        head = f"  {self.stamp}  [{self.provenance}]  kind: {self.kind}"
        if self.session:
            head += f"  session {self.session}"
        body = self.body.strip()
        if len(body) > 500:
            body = body[:500] + " ..."
        return f"{head}\n  title: {self.title}\n\n" + "\n".join(
            "    " + l for l in body.splitlines()
        )


# ---------------------------------------------------------------------
# landing
# ---------------------------------------------------------------------


def land(ground: Path, entry: Entry) -> Path:
    """Append one entry to memory.md. Never rewrites what is already there."""
    mem = Path(ground) / MEMORY_FILE
    if not mem.exists():
        mem.write_text(HEADER, encoding="utf-8", newline="\r\n")
    with mem.open("a", encoding="utf-8", newline="\r\n") as f:
        f.write(entry.render())
    return mem


# ---------------------------------------------------------------------
# staging
# ---------------------------------------------------------------------


def stage(ground: Path, entry: Entry) -> int:
    p = Path(ground) / PENDING_FILE
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8", newline="\r\n") as f:
        f.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
    return len(pending(ground))


def pending(ground: Path) -> list[Entry]:
    p = Path(ground) / PENDING_FILE
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(Entry(**json.loads(line)))
        except Exception:
            continue
    return out


def _write_pending(ground: Path, entries: list[Entry]) -> None:
    p = Path(ground) / PENDING_FILE
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "".join(json.dumps(asdict(e), ensure_ascii=False) + "\n" for e in entries),
        encoding="utf-8", newline="\r\n",
    )


def land_pending(ground: Path, index: int, countersign: bool = True,
                 kind: str = "") -> Entry | None:
    """Move one staged entry into memory.md. The operator's act, so the entry
    records that a person landed model testimony rather than silently
    promoting it to the operator's own word. `kind`, if given, is his word
    for what the entry is."""
    items = pending(ground)
    if not (0 <= index < len(items)):
        return None
    e = items.pop(index)
    if countersign:
        e.provenance = f"{GENERATED} (landed by OPERATOR)"
    if kind:
        e.kind = kind
    land(ground, e)
    _write_pending(ground, items)
    return e


def drop_pending(ground: Path, index: int) -> Entry | None:
    items = pending(ground)
    if not (0 <= index < len(items)):
        return None
    e = items.pop(index)
    _write_pending(ground, items)
    return e


# ---------------------------------------------------------------------
# reading back — per-entry chunking for the index
# ---------------------------------------------------------------------


def split_entries(text: str):
    """Split memory.md into one piece per entry.

    Returns (start_offset, text, label, stamp, session). Falls back to a single
    piece when the file has no entry headings, so a hand-written memory file
    still indexes rather than being skipped.
    """
    marks = list(_ENTRY_RE.finditer(text))
    if not marks:
        body = text.strip()
        return [(0, body, "", "", "")] if body else []

    out = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        block = text[m.start():end].strip()
        if not block:
            continue
        sess = re.search(r"^-[ \t]*session:[ \t]*(\S+)", block, re.MULTILINE)
        out.append(
            (
                m.start(),
                block,
                m.group("title").strip(),
                m.group("stamp").strip(),
                sess.group(1) if sess else "",
            )
        )
    return out
