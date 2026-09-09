"""The capability manifest, parsed and reconciled against the code.

    python -m manjuel.us

`us/*.us` declares what a thing MAY REACH -- `wall`, `writes`, `remote`,
`lands`, `can_approve` -- rather than what it does. That is the estate's
security claim in one readable place, and until 2026-09-03 NOTHING CHECKED
IT. The manifest was indexed and retrievable, so a seat could quote it; no
code compared it to the implementation, and it had drifted badly: twenty of
thirty-five skills carried no record at all, ten of eleven seat records
named a model the seat had not run in weeks, and the two seats that
actually touch the disk both UNDERSTATED their reach.

A declaration nobody checks is a promise. LAW 5 applies to the manifest
exactly as it applies to a seat: a claim is not a fact until the record
proves it. This module is that proof.

IT REPORTS AND NEVER GATES, for audit_record.py's reason and not a weaker
one: a manifest describes a ground that the operator edits by hand, so an
assertion over it would go red because he added a skill rather than because
something broke. The STROKES gate; this informs. What it must never do is
be silently green -- a reconciler that finds nothing because it looked at
nothing is worse than no reconciler, which is why every finding names the
field, the record and the disk fact that disagree.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

US_DIR = "us"

# A record is a fenced json block. The prose around it is for people; the
# block is the declaration. Both are kept in one file on purpose -- a
# machine-readable field with no argument beside it is how a manifest
# becomes a checkbox nobody reads.
_BLOCK_RE = re.compile(r"```json\s*\n(.*?)```", re.DOTALL)

# What a git skill needs before it may leave the machine, and the three
# skills that CAN. Kept here beside the check rather than imported, because
# skills.py has no opinion about `remote` -- the gate lives in the handlers.
REMOTE_SKILLS = {"git_pull", "git_push", "rack_pull"}


@dataclass(frozen=True)
class Finding:
    """One disagreement between a declaration and the disk.

    `where` is the file a reader should open. `field` is the thing that
    lied. Both are required: a finding that says only "router is wrong"
    sends someone hunting, and hunting is where a fix becomes a guess.
    """
    level: str          # "GAP" (undeclared) | "DRIFT" (declared wrongly)
    where: str
    field: str
    said: str
    disk: str

    def line(self) -> str:
        return (f"  {self.level:5} {self.where:28} {self.field:14} "
                f"declared {self.said!r} / disk {self.disk!r}")


def load(ground) -> tuple[list[dict], list[Finding]]:
    """Every record in us/, and every block that would not parse.

    A malformed block is NAMED, never swallowed. The whole point of this
    module is that a claim gets checked; a parser that quietly drops the
    one record it could not read would defeat it in the least visible way
    available.
    """
    root = Path(ground) / US_DIR
    records: list[dict] = []
    broken: list[Finding] = []
    if not root.is_dir():
        return records, [Finding("GAP", US_DIR, "directory", "declared", "missing")]
    for path in sorted(root.glob("*.us")):
        text = path.read_text(encoding="utf-8", errors="replace")
        blocks = _BLOCK_RE.findall(text)
        if not blocks:
            broken.append(Finding("GAP", path.name, "record", "a .us file",
                                  "no json block in it"))
            continue
        for i, raw in enumerate(blocks):
            try:
                rec = json.loads(raw)
            except ValueError as exc:
                broken.append(Finding("GAP", path.name, f"block {i + 1}",
                                      "valid json", f"{type(exc).__name__}: {exc}"))
                continue
            rec["_file"] = path.name
            records.append(rec)
    return records, broken


def reconcile(ground, registry, library, installed: set | None = None
              ) -> list[Finding]:
    """Compare every record to the thing it names. Report; change nothing.

    `installed` is the rack's model tags. It is OPTIONAL and its absence is
    REPORTED rather than passed over -- a check that silently skips is the
    failure this module exists to prevent, one level up.

    But "absent" must not be reported as "unreachable". Those are different
    facts and the module said the wrong one on the operator's own machine
    with Ollama running, because main() never asked. `rack_tags()` asks,
    and names the error when the answer is no.
    """
    from .skills import WRITING_SKILLS

    records, findings = load(ground)
    by_id = {r["id"]: r for r in records}

    skills_on_disk = set(library.keywords())
    seats_on_disk = {a.name.lower().replace(" ", "_") for a in registry.all()}

    skill_recs = {r["id"] for r in records if r.get("kind") == "skill"}
    seat_recs = {r["id"][len("seat_"):] for r in records
                 if r.get("kind") == "agent" and r["id"].startswith("seat_")}

    # --- 1. everything on disk is declared, and nothing declared is absent
    for k in sorted(skills_on_disk - skill_recs):
        findings.append(Finding("GAP", f"skills/{k}", "record", "nothing",
                                "a skill with no declared wall"))
    for k in sorted(skill_recs - skills_on_disk):
        findings.append(Finding("DRIFT", f"us/{k}", "record", "a skill",
                                "no such skill on disk"))
    for a in sorted(seats_on_disk - seat_recs):
        findings.append(Finding("GAP", f"agents/{a}", "record", "nothing",
                                "a seat with no declared permission"))
    for a in sorted(seat_recs - seats_on_disk):
        findings.append(Finding("DRIFT", f"us/seat_{a}", "record", "a seat",
                                "no such seat on disk"))

    # --- 2. the fields a machine can check ------------------------------
    for k in sorted(skills_on_disk & skill_recs):
        rec = by_id[k]
        spec = library.spec(k)

        if not str(rec.get("wall", "")).strip():
            findings.append(Finding("GAP", f"us/{k}", "wall", "", "no wall declared"))

        writes = bool(rec.get("writes"))
        if writes != (k in WRITING_SKILLS):
            findings.append(Finding("DRIFT", f"us/{k}", "writes", str(writes),
                                    str(k in WRITING_SKILLS)))

        if "remote" in rec and bool(rec["remote"]) != (k in REMOTE_SKILLS):
            findings.append(Finding("DRIFT", f"us/{k}", "remote",
                                    str(bool(rec["remote"])),
                                    str(k in REMOTE_SKILLS)))

        declared_model = rec.get("model")
        real_model = getattr(spec, "model", "") or ""
        if declared_model and declared_model != real_model:
            findings.append(Finding("DRIFT", f"us/{k}", "model",
                                    declared_model, real_model or "(none)"))

        if rec.get("source") and not (Path(ground) / rec["source"]).exists():
            findings.append(Finding("DRIFT", f"us/{k}", "source",
                                    rec["source"], "no such file"))

    # --- 3. the seats: the model, and the reach it actually holds -------
    for name in sorted(seats_on_disk & seat_recs):
        rec = by_id[f"seat_{name}"]
        seat = next(a for a in registry.all()
                    if a.name.lower().replace(" ", "_") == name)
        if rec.get("model") != seat.model:
            findings.append(Finding("DRIFT", f"us/seat_{name}", "model",
                                    str(rec.get("model")), seat.model))
        may = sorted(seat.callable_set(skills_on_disk))
        if sorted(rec.get("may_call") or []) != may:
            findings.append(Finding("DRIFT", f"us/seat_{name}", "may_call",
                                    str(len(rec.get("may_call") or [])),
                                    f"{len(may)} from May Call"))
        # A seat cleared for a WRITING skill and declaring edit: deny is the
        # exact shape that made this module necessary -- the Router said it
        # read only the workspace while holding every ground reader.
        # A PERMISSION MAY BE A MAP OR A BARE WORD. Older records wrote
        # `"edit": "deny"`; the reconciled ones write a map of path to
        # verdict. The first draft of this assumed the map and CRASHED on
        # the old manifest -- which is the one shape it most needed to
        # survive, because reporting on a stale manifest is the entire job.
        # A reconciler that dies on the input it was written to judge has
        # judged nothing.
        perm = rec.get("permission") or {}
        edits = perm.get("edit")
        if isinstance(edits, str):
            allows_edit = edits.startswith("allow")
        elif isinstance(edits, dict):
            allows_edit = any(isinstance(v, str) and v.startswith("allow")
                              for k2, v in edits.items() if k2 != "*")
        else:
            allows_edit = False
        if set(may) & WRITING_SKILLS and not allows_edit:
            findings.append(Finding("DRIFT", f"us/seat_{name}", "permission.edit",
                                    "deny", "cleared for a writing skill"))

    # --- 4. THE INVARIANT. No record, ever, may approve anything --------
    for r in records:
        if r.get("can_approve"):
            findings.append(Finding("DRIFT", f"us/{r['id']}", "can_approve",
                                    "true", "RULE 6: no agent approves"))

    # --- 5. the rack, when there is one to ask --------------------------
    #
    # THE UNASKED QUESTION IS NOT AN UNREACHABLE RACK. This finding used to
    # read "not checked - no rack was reachable" whenever `installed` was
    # None -- and main() never passed it, so on the operator's own machine,
    # with Ollama running, the reconciler ASSERTED A FACT IT HAD NOT
    # CHECKED. That is precisely the class of lie this module exists to
    # catch, committed by the module itself.
    #
    # Two different states, said differently, and neither pretends to be
    # the other: nothing asked, or the rack was asked and did not answer
    # (with the error named).
    declared = {r["model"] for r in records if r.get("model")}
    if installed is None:
        findings.append(Finding("GAP", "the rack", "model tags",
                                f"{len(declared)} declared",
                                "NOT ASKED - no rack was offered to this "
                                "check; that is not the same as unreachable"))
    else:
        for tag in sorted(declared - set(installed)):
            findings.append(Finding("DRIFT", "the rack", "model", tag,
                                    "not installed"))
    return findings


def report(ground, registry, library, installed=None) -> str:
    findings = reconcile(ground, registry, library, installed)
    records, _ = load(ground)
    head = (f"the manifest: {len(records)} records in {US_DIR}/, "
            f"{len(findings)} finding(s)")
    if not findings:
        return head + "\n  the manifest agrees with the disk."
    gaps = sum(1 for f in findings if f.level == "GAP")
    return "\n".join([head, f"  {gaps} undeclared, {len(findings) - gaps} drifted", ""]
                     + [f.line() for f in findings])


def rack_tags() -> tuple[set | None, str]:
    """What is installed on the rack, or None and the reason why not.

    ASK, DO NOT ASSUME. The reconciler's rack finding used to say "no rack
    was reachable" whenever nobody handed it a list -- and nobody ever did,
    so it said that on a machine where Ollama was running fine. A module
    that checks other people's claims does not get to make an unchecked one.
    """
    try:
        from .runtime import OllamaRuntime
        return OllamaRuntime().installed_models(), ""
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def main() -> int:
    from .registry import AgentRegistry
    from .skills import SkillLibrary
    ground = Path(__file__).resolve().parent.parent
    installed, why = rack_tags()
    out = report(ground, AgentRegistry.load(ground / "agents"),
                 SkillLibrary.load(ground / "skills"), installed)
    if installed is None:
        # Say WHICH failure, with the error, rather than leaving the
        # reconciler's generic "not asked" to stand for a real refusal.
        out += (f"\n\n  the rack could not be asked: {why}\n"
                f"  (every other check above ran; only the model tags are "
                f"unverified.)")
    print(out)
    return 0          # REPORTS, NEVER GATES.


if __name__ == "__main__":
    raise SystemExit(main())
