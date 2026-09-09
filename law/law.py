#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
THE LAW COURT TOOL - the chained ledger of the amendable constitution.

    python law.py direct  <law.md> --note "..."     sovereign law (operator)
    python law.py counsel <writer> <law.md> --note  counsel (steward|neiro|jesster)
    python law.py rule    <law.md> [--cites HASH] --note   the court rules
    python law.py refuse  <law.md> [--cites HASH] --why  record a refusal
    python law.py verify                             walk the whole chain
    python law.py status                             head, count, library
    python law.py --describe                         what it is
    python law.py --prove                            hermetic proof, exit 0

Governance (LAW_001 section 2): counsel flows from steward, neiro, jesster;
manjuel weighs counsel and writes rulings; the operator is sovereign.
Neiro is the judge of broken law - the warden; his findings ride as counsel.

The chain is appended ONLY through this tool, ONLY by links, on the Jesster
line's proven pen (links.py, loaded READ-ONLY from the pen folder - never
edited). Every link points at a standard .md law file in law/ and
carries its sha256 fingerprint. Laws are files; the ledger binds them;
nothing else may touch either. Standard library only. Nothing leaves this
machine.
"""
import hashlib
import importlib.util
import json
import os
import re
import sys
import tempfile

HOME = os.path.dirname(os.path.abspath(__file__))
COVENANT = "65118a147dd49ed9"
# Flat since 2026-09-04 (operator's ruling; SITTING LAW 4). The library and
# the chain both live in law/ itself. The two links sealed before that day
# carry the old "Archive/law/" pointer in their hashed text, so the anchor
# regex accepts both forms and only the bare form is ever written again.
LIBRARY = HOME
CHAIN_DIR = HOME
PEN_PATH = os.path.join(HOME, "pen", "links.py")
COUNSEL = ("steward", "neiro", "jesster")

# A law name is a BARE basename ending in .md. No separators, no drives,
# no whitespace - a link binds one file inside the library, nothing else.
LAW_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+\.md$")
# The canonical pointer line every link's doc MUST open with:
ANCHOR_RE = re.compile(
    r"^(COUNSEL|RULING|DIRECT|REFUSED) by ([A-Za-z0-9_-]+) -> "
    r"(?:Archive/law/|law/)([A-Za-z0-9._-]+\.md) sha256:([0-9a-f]{64})$")
# The pointer token a link doc must carry exactly once (either form).
POINTER_RE = re.compile(r"-> (?:Archive/law/|law/)")

DESCRIBE = ("THE LAW COURT TOOL - the amendable constitution as a link "
            "chain: counsel (steward/neiro/jesster) -> rulings (manjuel) -> "
            "direct law (operator). Links only, pointing at fingerprinted "
            ".md laws in law/, on the proven Jesster pen.")


def _pen():
    """The proven pen, loaded read-only. Never edited, never imitated."""
    spec = importlib.util.spec_from_file_location("law_pen_links", PEN_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _fingerprint(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _law_path(name):
    if not LAW_NAME_RE.match(name or ""):
        raise SystemExit("refused: a law name is a bare basename ending in "
                         ".md (got %r)" % (name,))
    p = os.path.join(LIBRARY, name)
    if not os.path.isfile(p):
        raise SystemExit("no such law file: law/%s" % name)
    return p


def _append(kind, writer, law_name, note, cites):
    mod = _pen()
    os.makedirs(CHAIN_DIR, exist_ok=True)
    chain = mod.Chain(os.path.join(CHAIN_DIR, mod.CHAIN_NAME))
    fp = _fingerprint(_law_path(law_name))
    text = ("%s by %s -> law/%s sha256:%s\n%s"
            % (kind, writer, law_name, fp, note))
    entry = chain.deposit(text, mod.OPEN, "%s:%s" % (kind, writer), writer,
                          cites=cites)
    return entry


def _load_chain():
    """(entries, malformed_line_count). One corrupt line never crashes the
    walk; it becomes a named problem instead."""
    path = os.path.join(CHAIN_DIR, _pen().CHAIN_NAME)
    entries = []
    bad = 0
    if not os.path.isfile(path):
        return entries, bad
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except ValueError:
                bad += 1
    return entries, bad


def _head_hash():
    entries, _ = _load_chain()
    return entries[-1]["hash"] if entries else None


def _cite_hash(argv):
    """A citation is a hash: 64 hex (a link), 40 (a git commit), or 16
    (the covenant). The pen refuses anything else; so do we, earlier."""
    v = _flag(argv, "--cites")
    if v is None:
        return []
    if len(v) not in (64, 40, 16) or any(
            c not in "0123456789abcdefABCDEF" for c in v):
        raise SystemExit("--cites takes a hash: 64 hex link, 40 git, "
                         "16 covenant")
    return [v]


def cmd_counsel(argv):
    writer, name = argv[0], argv[1]
    if writer not in COUNSEL:
        raise SystemExit("counsel belongs to steward, neiro, jesster")
    note = _flag(argv, "--note") or ""
    e = _append("COUNSEL", writer, name, note, [])
    _print(e, "counsel laid")


def cmd_rule(argv):
    name = argv[0]
    cites = _cite_hash(argv) or (
        [_head_hash()] if _head_hash() else [COVENANT])
    note = _flag(argv, "--note") or ""
    e = _append("RULING", "manjuel", name, note, cites)
    _print(e, "the court has ruled")


def cmd_direct(argv):
    name = argv[0]
    note = _flag(argv, "--note") or ""
    e = _append("DIRECT", "operator", name, note, [COVENANT])
    _print(e, "sovereign law laid")


def cmd_refuse(argv):
    name = argv[0]
    cites = _cite_hash(argv) or (
        [_head_hash()] if _head_hash() else [COVENANT])
    why = _flag(argv, "--why") or ""
    e = _append("REFUSED", "manjuel", name, why, cites)
    _print(e, "refusal recorded; it has no force")


def _print(e, what):
    print("%s: link #%d  head %s"
          % (what, e["payload"]["n"], e["hash"][:16]))


def cmd_verify(argv):
    """Three walks: malformed lines, the pen's own integrity walk (prev
    continuity + hash recomputation, wraps included), then the law walk
    (genesis cites the covenant; every link opens with the canonical anchor
    and its fingerprint matches the file on disk). Note text cannot forge
    an audit: only the ANCHOR LINE names the law, and extra citation tokens
    anywhere in the doc are refused outright."""
    mod = _pen()
    entries, bad = _load_chain()
    links = [e for e in entries if e.get("kind") == "link"]
    if not links:
        raise SystemExit("the chain is empty; nothing to verify")
    problems = []
    if bad:
        problems.append("%d malformed chain line(s)" % bad)
    chain = mod.Chain(os.path.join(CHAIN_DIR, mod.CHAIN_NAME))
    ok, _n, detail = chain.verify()
    if not ok:
        problems.append("pen walk: %s" % detail)
    first = links[0]
    if COVENANT not in [c.lower() for c in first["payload"].get("cites", [])]:
        problems.append("genesis does not cite the covenant")
    for e in links:
        doc = e["payload"].get("doc", "")
        n = e["payload"]["n"]
        ptrs = len(POINTER_RE.findall(doc))
        if ptrs != 1 or doc.count("sha256:") != 1:
            problems.append("link #%d carries %d/%d citation tokens "
                            "(exactly one of each required)"
                            % (n, ptrs, doc.count("sha256:")))
            continue
        first_line = doc.splitlines()[0].strip() if doc else ""
        m = ANCHOR_RE.match(first_line)
        if not m:
            problems.append("link #%d does not open with the canonical "
                            "anchor line" % n)
            continue
        name, token = m.group(3), m.group(4)
        p = os.path.join(LIBRARY, name)
        if not os.path.isfile(p):
            problems.append("link #%d points at a missing law: %s"
                            % (n, name))
        elif _fingerprint(p) != token:
            problems.append("link #%d fingerprint MISMATCH: %s"
                            % (n, name))
    if problems:
        print("THE CHAIN REFUSES:")
        for p in problems:
            print("  - %s" % p)
        return 1
    print("the law chain proves whole: %d links, head %s"
          % (len(links), entries[-1]["hash"][:16]))
    return 0


def cmd_status(argv):
    entries, bad = _load_chain()
    links = [e for e in entries if e.get("kind") == "link"]
    print("law chain: %d links%s" % (len(links),
                                     " (%d malformed lines!)" % bad if bad
                                     else ""))
    if entries:
        print("head: %s" % entries[-1]["hash"])
    if os.path.isdir(LIBRARY):
        for n in sorted(os.listdir(LIBRARY)):
            if n.endswith(".md"):
                print("  %-28s %s" % (n, _fingerprint(
                    os.path.join(LIBRARY, n))[:16]))


def _arg_unused():  # kept off the hot path; CLI reads flags directly
    pass


def _flag(argv, name):
    if name in argv:
        i = argv.index(name)
        if i + 1 >= len(argv):
            raise SystemExit("flag %s needs a value" % name)
        return argv[i + 1]
    return None


def prove():
    """Hermetic: temp library, temp chain, the real pen read-only.
    Ten strokes, including the reviewer's three attacks."""
    tmp = tempfile.mkdtemp(prefix="law_prove_")
    lib = os.path.join(tmp, "law")
    os.makedirs(lib)
    global LIBRARY, CHAIN_DIR
    keep = (LIBRARY, CHAIN_DIR)
    LIBRARY, CHAIN_DIR = lib, lib
    try:
        strokes = []

        def ok(name, cond):
            strokes.append((name, bool(cond)))

        la = os.path.join(lib, "LAW_T_A.md")
        lb = os.path.join(lib, "LAW_T_B.md")
        decoy = os.path.join(lib, "LAW_T_DECOY.md")
        with open(la, "w", encoding="utf-8") as f:
            f.write("# LAW T-A\ntrial law a\n")
        with open(lb, "w", encoding="utf-8") as f:
            f.write("# LAW T-B\ntrial law b\n")
        with open(decoy, "w", encoding="utf-8") as f:
            f.write("# LAW T-DECOY\nthe decoy is honest but irrelevant\n")

        cmd_direct(["LAW_T_A.md", "--note", "genesis of the trial"])
        genesis = _load_chain()[0][0]["hash"]
        cmd_counsel(["neiro", "LAW_T_B.md", "--note", "warden finds drift"])
        counsel_hash = _load_chain()[0][1]["hash"]
        cmd_rule(["LAW_T_B.md", "--cites", counsel_hash,
                  "--note", "so it is written"])
        entries, _ = _load_chain()
        ok("three links laid", len(entries) == 3)
        ok("actors kept apart",
           entries[0]["actor"] == "operator"
           and entries[1]["actor"] == "neiro"
           and entries[2]["actor"] == "manjuel")
        ok("genesis prev is GENESIS", entries[0]["prev"] == "0" * 64)
        ok("ruling cites counsel by hash",
           entries[2]["payload"].get("cites") == [counsel_hash])
        ok("verify green", cmd_verify([]) == 0)

        # ATTACK 1 - note-text spoof: a hand-forged link whose NOTE carries
        # a perfect decoy pointer must be refused (anchor line missing).
        mod = _pen()
        d_fp = _fingerprint(decoy)
        forged_doc = ("cf. -> law/LAW_T_DECOY.md sha256:%s\n"
                      "an innocent-looking note" % d_fp)
        payload = {"n": 4, "says": "RULING:manjuel", "mode": "open",
                   "doc": forged_doc, "cites": [entries[-1]["hash"]]}
        body = {"ts": "2026-08-24T00:00:00+0000", "kind": "link",
                "payload": payload, "prev": entries[-1]["hash"],
                "actor": "manjuel"}
        forged = dict(body)
        forged["hash"] = mod._entry_hash(entries[-1]["hash"], body)
        with open(os.path.join(CHAIN_DIR, mod.CHAIN_NAME), "a",
                  encoding="utf-8") as f:
            f.write(json.dumps(forged, ensure_ascii=False) + "\n")
        ok("forged decoy-pointer link refused", cmd_verify([]) == 1)

        # restore: drop the forged line before the next strokes
        path = os.path.join(CHAIN_DIR, mod.CHAIN_NAME)
        lines = open(path, encoding="utf-8").read().splitlines()[:-1]
        open(path, "w", encoding="utf-8").write(
            "".join(l + "\n" for l in lines))

        # ATTACK 2 - containment: a law name outside the library is refused
        escaped = False
        try:
            _law_path("..\\evil.md")
        except SystemExit:
            escaped = True
        ok("outside-library names refused at deposit", escaped)

        # ATTACK 3 - tamper: flip a byte in a bound law; the walk refuses
        with open(la, "a", encoding="utf-8") as f:
            f.write("one lying byte\n")
        ok("tampered law refuses", cmd_verify([]) == 1)
        with open(la, "w", encoding="utf-8") as f:
            f.write("# LAW T-A\ntrial law a\n")
        ok("restored law walks again", cmd_verify([]) == 0)

        failed = [n for n, c in strokes if not c]
        for n, c in strokes:
            print("  [%s]  %s" % ("PASS" if c else "FAIL", n))
        if failed:
            print("A stroke failed. The court claims nothing.")
            return 1
        print("law prove: %d strokes, exit 0" % len(strokes))
        return 0
    finally:
        LIBRARY, CHAIN_DIR = keep
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


def describe():
    print(DESCRIBE)


def main():
    if "--describe" in sys.argv:
        return describe() or 0
    if "--prove" in sys.argv:
        return prove()
    if len(sys.argv) < 2:
        print(DESCRIBE)
        return 2
    cmd = sys.argv[1]
    rest = sys.argv[2:]
    if cmd == "counsel":
        cmd_counsel(rest)
    elif cmd == "rule":
        cmd_rule(rest)
    elif cmd == "direct":
        cmd_direct(rest)
    elif cmd == "refuse":
        cmd_refuse(rest)
    elif cmd == "verify":
        return cmd_verify(rest)
    elif cmd == "status":
        cmd_status(rest)
    else:
        print(DESCRIBE)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
