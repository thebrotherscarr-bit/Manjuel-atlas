"""rack.md — the written record of what is on this machine.

`/status` shows the rack at a moment. This writes it down, so it can be read
later, diffed against a previous sitting, searched by the index, and quoted
back by a seat that was not present when it was taken.

It is DERIVED, not a record in the LAW 1 sense: regenerated whole from what
Ollama reports rather than appended to. State = fold(record), and Ollama is the
record here. The file carries the timestamp it was taken so nobody mistakes a
stale copy for the truth.

The two lines that matter are the mismatches:

  DECLARED BUT MISSING   a seat names a model that is not installed. That seat
                         fails the moment it is called.
  INSTALLED BUT UNUSED   on disk, named by nothing. Not a fault -- just weight
                         you may not have meant to keep.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from . import vram

RACK_FILE = "rack.md"


def survey(runtime, registry, skills, embed_model: str) -> dict:
    """Ask Ollama fresh. Never the cache -- a model pulled in another terminal
    must show up here without restarting the REPL.

    The seats are read from what `agents/*.md` DECLARES, not from what they
    happen to be running. Sitting 57 ran under `/model gemma4:12b` and a sync
    in that sitting wrote the override to disk as the declaration: rack.md
    then named one model for all fifteen seats and filed the Router, the
    Reasoner and others under "installed but unused -- weight you may not have
    meant to keep." An override is one sitting's choice; this file outlives
    the sitting, so the override is REPORTED (see `override`) and never folded
    in. `missing`/`unused` follow the declaration for the same reason.
    """
    installed = runtime.installed_models(refresh=True)
    sizes = vram.installed_sizes(runtime)
    resident = dict(runtime.resident())

    # Falls back to the live seats only for a registry too old to know the
    # difference; the real one has answered declared_models() since s59.
    seats = (registry.declared_models() if hasattr(registry, "declared_models")
             else {a.name: a.model for a in registry.all()})

    declared: dict[str, list[str]] = {}
    for name, model in seats.items():
        declared.setdefault(model, []).append(name)
    for s in skills.specs:
        if s.model:
            declared.setdefault(s.model, []).append(f"skill:{s.keyword}")
    declared.setdefault(embed_model, []).append("drift + index")

    return {
        "taken": datetime.now().isoformat(timespec="seconds"),
        "host": getattr(runtime, "host", "ollama"),
        "installed": sorted(installed),
        "sizes": sizes,
        "resident": resident,
        "declared": declared,
        "override": getattr(registry, "override", "") or "",
        "missing": sorted(m for m in declared if m not in installed),
        "unused": sorted(m for m in installed if m not in declared),
    }


def render(s: dict) -> str:
    out = [
        "# The Rack",
        "",
        f"Taken {s['taken']} from `{s['host']}`. DERIVED — regenerated whole by",
        "`rack_sync`, never edited by hand. Ollama is the record; this is the fold.",
        "",
        f"{len(s['installed'])} models installed · {len(s['resident'])} loaded in VRAM",
        "",
    ]
    if s.get("override"):
        out += [
            f"**A `/model` override was active when this was taken: "
            f"`{s['override']}`.** Every seat was RUNNING that model. The table",
            "below is what `agents/*.md` DECLARES, which is what survives the "
            "sitting.",
            "",
        ]
    out += [
        "## Declared by this ground",
        "",
        "| model | size | in VRAM | used by |",
        "|---|---|---|---|",
    ]
    for m in sorted(s["declared"]):
        size = vram.gb(s["sizes"][m]) if s["sizes"].get(m) else "—"
        loaded = "yes" if m in s["resident"] else "no"
        who = ", ".join(sorted(s["declared"][m]))
        flag = "" if m in s["installed"] else "  **NOT INSTALLED**"
        out.append(f"| `{m}`{flag} | {size} | {loaded} | {who} |")

    if s["missing"]:
        out += ["", "## Declared but missing", "",
                "These seats fail the moment they are called.", ""]
        out += [f"- `{m}` — needed by {', '.join(sorted(s['declared'][m]))}"
                f"  ·  `ollama pull {m}`" for m in s["missing"]]

    if s["unused"]:
        total = sum(s["sizes"].get(m, 0) for m in s["unused"])
        out += ["", "## Installed but unused", "",
                f"On disk, named by nothing here — about {vram.gb(total)} of weight.",
                "Not a fault; just weight you may not have meant to keep.", ""]
        out += [f"- `{m}` — {vram.gb(s['sizes'][m]) if s['sizes'].get(m) else '—'}"
                for m in s["unused"]]

    foreign = [t for t in s["resident"] if t not in s["declared"]]
    if foreign:
        fb = sum(s["resident"][t] for t in foreign)
        out += ["", "## In VRAM but not ours", "",
                f"About {vram.gb(fb)} held by another client. Do not unload these —",
                "evicting one charges them the reload.", ""]
        out += [f"- `{t}` — {vram.gb(s['resident'][t])}" for t in foreign]

    return "\n".join(out) + "\n"


def write(ground: Path, s: dict) -> Path:
    p = Path(ground) / RACK_FILE
    p.write_text(render(s), encoding="utf-8", newline="\r\n")
    return p


def diff(old: str, s: dict) -> list[str]:
    """What changed since the last written rack. Names only, no sizes."""
    if not old:
        return []
    was = {ln.split("`")[1] for ln in old.splitlines()
           if ln.startswith("| `") and "`" in ln[3:]}
    now = set(s["installed"])
    added = sorted(now - was - {m for m in was})
    gone = sorted(m for m in was if m not in now)
    lines = []
    if added:
        lines.append(f"new since last sync: {', '.join(added)}")
    if gone:
        lines.append(f"no longer installed: {', '.join(gone)}")
    return lines
