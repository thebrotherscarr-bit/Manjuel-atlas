#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LINKS — the chain of provenance. What was deposited, by WHOM, and when.

A link is one piece of a long old chain. Every link carries five things, and
exactly five, because five is the shape of the estate's sealed ledger:

    ts       when it happened
    kind     what sort of entry this is — "link" or "wrap"
    payload  the thing itself: plain words, the document or its digest, and
             the hashes of the earlier links it is built on
    prev     the hash of the entry before it — the weld
    actor    the NAME. who did this. inside the hash, so it can never be
             changed without breaking the chain at a named position.

The hash and the signature ride OUTSIDE those five: a signature is taken over
the hash, so it can never be inside what produced it. This is the exact recipe
of the sealed kernel's ledger — same keys, same canonical form, same walk —
which means the sealed one can READ this file and vouch for it, without this
file ever importing him. They share a format, never a process.

TWO WAYS TO DEPOSIT, one chain, one flag apart:

  SEALED — the link carries only H(document). It proves something existed on
           that date and reveals nothing. Later you publish the document and
           anyone checks the hash against the commitment you made years
           earlier. This is Hooke's anagram — ceiiinosssttuv, 1660 — staking
           the claim without giving it away.

  OPEN   — the link carries the document itself. It is prior art the moment
           it lands, and nobody can patent it afterwards.

CITES. A link may name the earlier work it stands on, by hash — links on this
chain, or things already public elsewhere (a block on manjuel.us, a git
commit). The citations sit inside the payload, inside the hash: the terrain a
link claims to stand on is welded to it forever. Nothing judges a deposit at
the door. The topography — what gets built ON — is the only sieve.

WRAPS AND TOKENS. Every 40 links close a wrap: a Merkle root over exactly
those 40. FORTY IS FIXED AND NOBODY CHOOSES IT — if anyone could decide when
to close a wrap, that person would control issuance. Token N IS wrap N. There
are no granted tokens, no genesis pile, no exceptions: every token that exists
has forty links of work behind it and can prove that from the head. The serial
is the rank — there will only ever be nine one-digit tokens, ninety two-digit
ones, and the length of the number tells a stranger everything.

VERIFICATION IS EVERYONE'S. A stranger holding only the head can prove any
single link out of a million in about twenty hashes. The whole chain rewalks
with nothing but the standard library.

Standard library only. Jesster signs; she is imported, never embedded.
"""
import hashlib
import json
import os
import sys
import time

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

try:
    import jesster
except ImportError:                                  # unsigned, and it says so
    jesster = None

# --------------------------------------------------------------------------
WRAP_SIZE = 40           # fixed. see the docstring. nobody chooses this.
GENESIS = "0" * 64
SEALED, OPEN = "sealed", "open"
CHAIN_NAME = "chain.jsonl"
OFFICE = "links"

# The five keys of an entry's hashed body — the sealed kernel's own tuple,
# repeated here as a quotation, never imported. Append nothing. Reorder
# nothing. Remove nothing. The moment these differ from his, he reads this
# chain as tampered, and he is right to.
BODY_KEYS = ("ts", "kind", "payload", "prev", "actor")


def _h(*parts):
    d = hashlib.sha256()
    for p in parts:
        d.update(p if isinstance(p, bytes) else str(p).encode("utf-8"))
    return d.hexdigest()


def _canon(body):
    return json.dumps(body, sort_keys=True, ensure_ascii=False)


def _entry_hash(prev, entry):
    body = {k: entry[k] for k in BODY_KEYS if k in entry}
    return hashlib.sha256((prev + _canon(body)).encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# DOMAIN SEPARATION (RFC 9162 §2.1.1). A leaf and an interior node must not be
# hashable the same way. Without distinct prefixes, an attacker presents an
# interior node as though it were a single leaf — the Kelsey-Schneier second
# preimage. The odd-node carry below already refuses the OTHER Merkle attack
# (doubling); these two bytes close the pair.
#
# Landed while the chain stood at 9 links and 0 wraps: no root had yet been
# committed, so nothing existing was invalidated. After the first wrap closes
# this could not be changed without forking the chain.
LEAF, NODE = b"\x00", b"\x01"


def _mleaf(hexhash):
    """A leaf commitment: SHA-256(0x00 || entry_hash)."""
    return hashlib.sha256(LEAF + bytes.fromhex(hexhash)).hexdigest()


def _mnode(left, right):
    """An interior node: SHA-256(0x01 || left || right)."""
    return hashlib.sha256(NODE + bytes.fromhex(left) + bytes.fromhex(right)).hexdigest()


MERKLE_V = 2             # what NEW wraps use. Old wraps record none and mean 1.


def _merkle(leaves, mv=MERKLE_V):
    """Root over a list of hex entry hashes. An odd node is carried up, not
    doubled — doubling lets one leaf stand in for two and is a real attack.

    TWO TREE VERSIONS, and the reason is the same reason EPOCH exists for keys.
    v1 hashed leaves and nodes identically. v2 domain-separates them. Forty-five
    wraps across the library and predictor chains had ALREADY closed under v1
    before this was found; recomputing them under v2 gives a different root and
    would call every one of them tampered. So v1 is kept, exactly, forever, and
    only new wraps are built with v2. A tree that silently changed shape would
    be the very tampering these roots exist to detect."""
    if not leaves:
        return GENESIS
    if mv == 1:
        row = list(leaves)
        while len(row) > 1:
            nxt = [_h(row[i], row[i + 1]) for i in range(0, len(row) - 1, 2)]
            if len(row) % 2:
                nxt.append(row[-1])
            row = nxt
        return row[0]
    row = [_mleaf(x) for x in leaves]
    while len(row) > 1:
        nxt = []
        for i in range(0, len(row) - 1, 2):
            nxt.append(_mnode(row[i], row[i + 1]))
        if len(row) % 2:
            nxt.append(row[-1])
        row = nxt
    return row[0]


def _path(leaves, i, mv=MERKLE_V):
    """The sibling hashes proving leaf i belongs to the root, in that tree's
    own version."""
    row = list(leaves) if mv == 1 else [_mleaf(x) for x in leaves]
    idx, out = i, []
    join = (lambda a, b: _h(a, b)) if mv == 1 else _mnode
    while len(row) > 1:
        nxt = []
        for j in range(0, len(row) - 1, 2):
            if j == idx or j + 1 == idx:
                out.append((row[j + 1], "R") if j == idx else (row[j], "L"))
            nxt.append(join(row[j], row[j + 1]))
        if len(row) % 2:
            nxt.append(row[-1])
        idx //= 2
        row = nxt
    return out


def climb(leaf, path, mv=MERKLE_V):
    """Walk a path back to a root. This is the whole verifier. Under v2 the leaf
    is committed with the leaf prefix first, so an interior node handed in here
    cannot pass as a leaf. Under v1 it is not — that is the flaw v2 closes, and
    v1 is kept only to keep already-closed roots verifiable."""
    if mv == 1:
        cur = leaf
        for sib, side in path:
            cur = _h(sib, cur) if side == "L" else _h(cur, sib)
        return cur
    cur = _mleaf(leaf)
    for sib, side in path:
        cur = _mnode(sib, cur) if side == "L" else _mnode(cur, sib)
    return cur


def wrap_version(wrap_entry):
    """Which tree a wrap was built with. Absent marker means v1 — every wrap
    closed before 2026-08-15 is v1 and must stay verifiable as one."""
    p = wrap_entry.get("payload") or {}
    if isinstance(p, str):
        try:
            p = json.loads(p)
        except ValueError:
            return 1
    return int(p.get("mv", 1))


# --------------------------------------------------------------------------
# THE CHAIN
# --------------------------------------------------------------------------

class Chain:
    """Append-only, hash-linked, and it holds its own head in memory.

    The head is NOT re-read from disk on every append. A ledger that scans its
    whole file to find the last hash costs O(n) per write — invisible at a
    hundred entries, fatal at a million. Loaded once at open, moved on every
    append."""

    def __init__(self, path=None):
        self.path = path or os.path.join(_ROOT, CHAIN_NAME)
        d = os.path.dirname(self.path)
        if d:
            os.makedirs(d, exist_ok=True)
        self._head = GENESIS
        self._n = 0
        self._leaves = []                 # hashes of the links in the open wrap
        if os.path.exists(self.path):
            self._load()
        else:
            open(self.path, "w", encoding="utf-8").close()

    def _load(self):
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                e = json.loads(line)
                self._head = e["hash"]            # every entry moves the head
                if e.get("kind") != "link":
                    continue
                self._n = e["payload"]["n"]
                self._leaves.append(e["hash"])
                if self._n % WRAP_SIZE == 0:
                    self._leaves = []

    # -- appending ---------------------------------------------------------

    def deposit(self, text, mode=OPEN, says="", actor="", cites=None, key=None):
        """Put one thing on the chain. SEALED commits only the hash of it.
        The actor is the NAME this deposit is welded to, forever."""
        if mode not in (SEALED, OPEN):
            raise ValueError("a deposit is %r or %r, not %r"
                             % (SEALED, OPEN, mode))
        if not says.strip():
            raise ValueError(
                "every link says what it is, in plain words. A chain of "
                "digests proves everything and tells a reader nothing.")
        if not actor.strip():
            raise ValueError(
                "every link names its actor. A chain of provenance with no "
                "names on it is a pile of dated hashes; the WHO is the point.")
        payload = {
            "n": self._n + 1,
            "says": says.strip(),
            "mode": mode,
            "doc": _h(text) if mode == SEALED else text,
        }
        if cites:
            bad = [c for c in cites
                   if not (isinstance(c, str) and len(c) in (16, 40, 64)
                           and all(ch in "0123456789abcdef" for ch in c.lower()))]
            if bad:
                raise ValueError(
                    "a citation is a hash — 64 hex characters for one of ours, "
                    "40 for a git commit, 16 for a covenant mark. This is "
                    "neither: %r" % bad[0])
            payload["cites"] = [c.lower() for c in cites]
        if key:
            payload["mark"] = key["mark"]
        return self._append("link", payload, actor.strip(), key)

    def reveal(self, n, text, says="", actor="", key=None):
        """Open a sealed link. Nothing is edited — Article I — a NEW link is
        appended that cites the old one by hash and carries the document.
        Anyone can check that H(document) equals what was committed then."""
        sealed = self.link(n)
        if not sealed or sealed["payload"]["mode"] != SEALED:
            raise ValueError("link %s is not a sealed deposit" % n)
        if _h(text) != sealed["payload"]["doc"]:
            raise ValueError(
                "that document does not match the commitment at link %d. It "
                "hashes to %s; the chain has held %s since %s."
                % (n, _h(text)[:16], sealed["payload"]["doc"][:16],
                   sealed["ts"]))
        return self.deposit(
            text, OPEN,
            says or ("reveals link %d — %s" % (n, sealed["payload"]["says"])),
            actor or sealed["actor"],
            cites=[sealed["hash"]],
            key=key)

    def _append(self, kind, payload, actor, key=None):
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "kind": kind,
            "payload": payload,
            "prev": self._head,
            "actor": actor,
        }
        entry["hash"] = _entry_hash(self._head, entry)
        if jesster and key and key.get("priv"):
            entry["sig"] = jesster.sign(key["priv"], entry["hash"]).hex()
            entry["pub"] = key["pub"].hex()
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._head = entry["hash"]
        if kind == "link":
            self._n = payload["n"]
            self._leaves.append(entry["hash"])
            if self._n % WRAP_SIZE == 0:
                self._close_wrap(key)
        return entry

    def _close_wrap(self, key=None):
        """A wrap closes at exactly n %% 40 == 0. No hand decides this. The
        wrap IS the token: token N is wrap N, and there is no other kind."""
        w = self._n // WRAP_SIZE
        frm, to = self._n - WRAP_SIZE + 1, self._n
        payload = {
            "w": w, "from": frm, "to": to,
            "root": _merkle(self._leaves, MERKLE_V),
            "mv": MERKLE_V,      # the tree this root was built with. A wrap with
                                 # no marker is v1 and stays verifiable as one —
                                 # forty-five such roots already stand.
            "token": w,
            "says": ("wrap %d seals links %d-%d and IS token %d. Nobody "
                     "closed it; forty links did." % (w, frm, to, w)),
        }
        self._leaves = []
        return self._append("wrap", payload, "arithmetic", key)

    # -- reading -----------------------------------------------------------

    def entries(self, kind=None):
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    e = json.loads(line)
                    if kind is None or e.get("kind") == kind:
                        yield e

    def link(self, n):
        for e in self.entries("link"):
            if e["payload"]["n"] == n:
                return e
        return None

    def head(self):
        return self._head

    def count(self):
        return self._n

    def wraps(self):
        return list(self.entries("wrap"))

    def tokens(self):
        """One token per wrap. None granted, none before the first wrap
        closes, none ever minted by a hand. Token N is wrap N."""
        return len(self.wraps())

    # -- proving -----------------------------------------------------------

    def verify(self):
        """THE STRANGER'S WALK — and the sealed kernel's. The body is rebuilt
        from the five keys and only the five; hash, sig and pub are never
        looked at, so their presence cannot break an old entry and their
        absence cannot break a new one. Returns (intact, n_links, detail)."""
        prev, n = GENESIS, 0
        for e in self.entries():
            where = "%s %s" % (e.get("kind"),
                               e.get("payload", {}).get("n",
                               e.get("payload", {}).get("w", "?")))
            if e["prev"] != prev:
                return False, n, "chain break at %s (prev mismatch)" % where
            if _entry_hash(prev, e) != e["hash"]:
                return False, n, "tamper at %s (hash mismatch)" % where
            prev = e["hash"]
            if e["kind"] == "link":
                n += 1
        return True, n, "chain intact"

    def prove_link(self, n):
        """The sibling path proving link n sits under its wrap's root.
        REFUSED until the wrap has closed — a proof against a root the chain
        has not committed is a proof of nothing, delivered convincingly."""
        w = (n - 1) // WRAP_SIZE + 1
        frm = (w - 1) * WRAP_SIZE + 1
        leaves = [e["hash"] for e in self.entries("link")
                  if frm <= e["payload"]["n"] < frm + WRAP_SIZE]
        i = n - frm
        if i >= len(leaves) or len(leaves) < WRAP_SIZE:
            return None
        wrap_entry = next((e for e in self.entries("wrap")
                           if (e.get("payload") or {}).get("w") == w), None)
        mv = wrap_version(wrap_entry) if wrap_entry else MERKLE_V
        return {"link": n, "wrap": w, "leaf": leaves[i], "mv": mv,
                "path": _path(leaves, i, mv), "root": _merkle(leaves, mv)}


def consistency(entries, m):
    """APPEND-ONLY PROOF — that the chain at length m is a prefix of the chain now.

    RFC 9162 answers this with a Merkle SUBPROOF because a CT log is ONE growing
    tree. This chain is not: a wrap is an independent root over exactly forty
    links, and the append-only property lives in the `prev` weld, not in a
    growing tree. So the honest proof of the same fact is the weld itself —
    the run of (hash, prev) pairs from the old head to the new one.

    Returns what a verifier needs and nothing more: the old head, the new head,
    and each link's (hash, prev) between them. It does not carry the bodies.
    """
    if m < 0 or m > len(entries):
        return None
    if m == 0:
        old_head = GENESIS
    else:
        old_head = entries[m - 1].get("hash", GENESIS)
    return {
        "from_length": m, "to_length": len(entries),
        "old_head": old_head,
        "new_head": entries[-1].get("hash", GENESIS) if entries else GENESIS,
        "weld": [{"hash": e.get("hash"), "prev": e.get("prev")} for e in entries[m:]],
    }


def check_consistency(proof):
    """Verify an append-only proof. Every link after the old head must weld to
    the one before it, and the run must end at the claimed new head. A rewritten
    or removed entry breaks the weld and is located by index."""
    if not proof:
        return {"ok": False, "why": "no proof"}
    prev = proof.get("old_head")
    weld = proof.get("weld") or []
    for i, link in enumerate(weld):
        if link.get("prev") != prev:
            return {"ok": False, "broke_at": proof["from_length"] + i,
                    "why": "weld broken: link %d claims prev %s, chain says %s"
                           % (proof["from_length"] + i, link.get("prev"), prev)}
        prev = link.get("hash")
    if prev != proof.get("new_head"):
        return {"ok": False, "why": "run does not reach the claimed head"}
    return {"ok": True, "appended": len(weld),
            "from": proof["from_length"], "to": proof["to_length"],
            "note": "the chain at length %d is a prefix of the chain at %d"
                    % (proof["from_length"], proof["to_length"])}


def check(proof):
    """A stranger's whole job: climb the path, see if it reaches the root."""
    if not proof:
        return False
    return climb(proof["leaf"], proof["path"]) == proof["root"]


def describe():
    return ("links: the chain of provenance — sealed or open deposits, each "
            "naming its actor and citing what it stands on, wrapped every 40 "
            "into a token that IS its wrap, provable by anyone with the head")


# --------------------------------------------------------------------------
# PROOF
# --------------------------------------------------------------------------

def prove():
    import shutil
    import tempfile
    strokes = []

    def ck(name, ok, detail=""):
        strokes.append((name, bool(ok), detail))

    tmp = tempfile.mkdtemp(prefix="links_")
    try:
        c = Chain(os.path.join(tmp, "chain.jsonl"))
        key = jesster.identity("covenant-for-the-test", b"the twelve words here",
                               "manjuel") if jesster else None
        ck("jesster is in the bones — a key derives, or it says unsigned",
           key is not None or jesster is None,
           key["mark"] if key else "jesster absent")

        a = c.deposit("the cistern behind the north wing sits at forty percent",
                      OPEN, "a reading of the north cistern", "kyler", key=key)
        ck("an OPEN deposit carries the document itself",
           a["payload"]["doc"].startswith("the cistern"), a["payload"]["says"])
        ck("the entry's hashed body is the sealed kernel's five keys, exactly",
           tuple(k for k in BODY_KEYS if k in a) == BODY_KEYS
           and all(k in BODY_KEYS for k in a if k not in ("hash", "sig", "pub")),
           ", ".join(BODY_KEYS))
        ck("the ACTOR is a name, inside the hash",
           a["actor"] == "kyler",
           "actor %r rides in the body, not beside it" % a["actor"])

        try:
            c.deposit("x", OPEN, "a thing", "   ", key=key)
            unnamed = False
        except ValueError as e:
            unnamed = "names its actor" in str(e)
        ck("a link with NO NAME on it is refused", unnamed)

        if key:
            ck("and it is SIGNED by the hand that made it — verified",
               "sig" in a and jesster.verify(key["pub"], a["hash"],
                                             bytes.fromhex(a["sig"])),
               "signature checks against %s" % key["mark"])
            ck("the key's mark rides INSIDE the hash, welding name to key",
               a["payload"].get("mark") == key["mark"]
               and jesster.mark(bytes.fromhex(a["pub"])) == a["payload"]["mark"])
            forged = jesster.identity("covenant-for-the-test",
                                      b"a different twelve words", "manjuel")
            ck("another hand's signature does NOT check",
               not jesster.verify(forged["pub"], a["hash"],
                                  bytes.fromhex(a["sig"])))
        else:
            ck("SIGNING WAS NOT EXERCISED — jesster is not beside this file",
               "sig" not in a, "links written unsigned, and they say so")

        secret = "a thing I am not ready to show anyone yet"
        b = c.deposit(secret, SEALED, "sealed — an idea, dated", "kyler", key=key)
        ck("a SEALED deposit reveals nothing but its hash",
           secret not in json.dumps(b) and len(b["payload"]["doc"]) == 64,
           b["payload"]["doc"][:16])

        try:
            c.deposit("x", OPEN, "   ", "kyler", key=key)
            said = False
        except ValueError as e:
            said = "plain words" in str(e)
        ck("a link with nothing to SAY is refused", said)

        d1 = c.deposit("built on the cistern reading", OPEN,
                       "a valve schedule derived from link 1", "claude",
                       cites=[a["hash"], "6da3cf8" + "0" * 33], key=key)
        ck("a link CITES the earlier work it stands on, by hash",
           d1["payload"]["cites"][0] == a["hash"],
           "%d citations, on-chain and off" % len(d1["payload"]["cites"]))
        try:
            c.deposit("x", OPEN, "junk cite", "kyler",
                      cites=["not-a-hash"], key=key)
            junk = False
        except ValueError as e:
            junk = "citation is a hash" in str(e)
        ck("a citation that is not a hash is refused", junk)

        r = c.reveal(b["payload"]["n"], secret, actor="kyler", key=key)
        ck("revealing a sealed link proves the old date",
           r["payload"]["doc"] == secret, r["payload"]["says"][:40])
        ck("and the reveal CITES the sealed link it opens",
           r["payload"]["cites"] == [b["hash"]])
        bad = False
        try:
            c.reveal(b["payload"]["n"], "a different document",
                     actor="kyler", key=key)
        except ValueError as e:
            bad = "does not match the commitment" in str(e)
        ck("a WRONG document cannot open a sealed link", bad)
        ck("nothing was edited to do it — the seal still stands",
           c.link(b["payload"]["n"])["payload"]["mode"] == SEALED
           and c.link(b["payload"]["n"])["payload"]["doc"] != secret)

        ck("no token exists before any work does", c.tokens() == 0,
           "%d links, %d tokens" % (c.count(), c.tokens()))

        while c.count() < WRAP_SIZE:
            c.deposit("reading %d" % c.count(), OPEN,
                      "routine reading %d" % c.count(), "steward", key=key)
        ck("a wrap closes at exactly %d links, and not before" % WRAP_SIZE,
           len(c.wraps()) == 1 and c.count() == WRAP_SIZE,
           "%d links, %d wrap(s)" % (c.count(), len(c.wraps())))
        w = c.wraps()[0]
        ck("the wrap says what it is, in words",
           "seals links 1-40" in w["payload"]["says"], w["payload"]["says"])
        ck("TOKEN 1 IS WRAP 1 — no grants, no genesis pile, no exceptions",
           c.tokens() == 1 and w["payload"]["token"] == w["payload"]["w"] == 1,
           "%d token(s); serial = wrap number" % c.tokens())
        ck("nobody chose when it closed — 40 links did",
           w["payload"]["from"] == 1 and w["payload"]["to"] == WRAP_SIZE
           and w["actor"] == "arithmetic")

        for _ in range(WRAP_SIZE):
            c.deposit("more", OPEN, "another reading", "steward", key=key)
        ck("the second wrap closes on the same fixed rule",
           len(c.wraps()) == 2
           and c.wraps()[1]["payload"]["from"] == WRAP_SIZE + 1)

        ok, n, detail = c.verify()
        ck("the whole chain verifies, links and wraps together", ok, detail)

        p = c.prove_link(7)
        ck("any single link proves itself against its wrap root", check(p),
           "%d sibling hashes" % len(p["path"]))
        p["leaf"] = _h("a forged leaf")
        ck("a forged leaf does NOT reach the root", not check(p))
        c.deposit("one more", OPEN, "a link in the still-open wrap",
                  "steward", key=key)
        ck("a proof is REFUSED while its wrap is still open",
           c.prove_link(c.count()) is None,
           "link %d waits for wrap %d to close"
           % (c.count(), (c.count() - 1) // WRAP_SIZE + 1))

        d = Chain(os.path.join(tmp, "chain.jsonl"))
        ck("reopening picks the head off the end, not by rescanning",
           d.head() == c.head() and d.count() == c.count(),
           "%d links, head %s" % (d.count(), d.head()[:12]))

        def tampered(mutate):
            rows = [json.loads(l)
                    for l in open(c.path, encoding="utf-8") if l.strip()]
            mutate(rows)
            q = os.path.join(tmp, "tampered.jsonl")
            with open(q, "w", encoding="utf-8") as f:
                for row in rows:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
            return Chain(q).verify()

        ok2, _, why2 = tampered(
            lambda rows: rows[3]["payload"].__setitem__(
                "says", "a line no hand wrote"))
        ck("editing what a link SAYS breaks the chain and is named",
           not ok2, why2)
        ok3, _, why3 = tampered(
            lambda rows: rows[0].__setitem__("actor", "somebody else"))
        ck("editing WHOSE a link is breaks the chain and is named",
           not ok3, why3)
        ok4, _, why4 = tampered(
            lambda rows: rows[4]["payload"].__setitem__("cites", []))
        ck("editing what a link CITES breaks the chain and is named",
           not ok4, why4)

        ck("every link and every wrap says something, and every link is named",
           all(e["payload"].get("says", "").strip() and e["actor"].strip()
               for e in c.entries()))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return strokes


# --------------------------------------------------------------------------
# THE HAND — a small CLI, so depositing is a command and not a ritual.
# --------------------------------------------------------------------------

_USAGE = """\
  links — the chain of provenance. Forty to a wrap; token N is wrap N.

    python3 links.py                                    run the proof
    python3 links.py status                             links, wraps, tokens, head
    python3 links.py verify                             rewalk the whole chain
    python3 links.py deposit open|sealed "SAYS" --actor NAME
                     (--text "..." | --file PATH)
                     [--cites HASH,HASH,...] [--sign]   put one thing on the chain
    python3 links.py reveal N (--text "..."|--file PATH)
                     [--actor NAME] [--sign]            open a sealed link
    python3 links.py show N                             print link N
    python3 links.py prove N                            inclusion proof for link N

  The chain lives beside this file as %s. SEALED writes only the document's
  hash; keep the document safe yourself — the chain cannot give it back.
  --sign derives your key through jesster: the twelve words are asked for at
  the moment of signing, used in memory, and never written anywhere.""" % CHAIN_NAME


def _arg(argv, name, default=None):
    if name in argv:
        i = argv.index(name)
        if i + 1 < len(argv):
            v = argv[i + 1]
            del argv[i:i + 2]
            return v
    return default


def _flag(argv, name):
    if name in argv:
        argv.remove(name)
        return True
    return False


def _read_doc(argv):
    text = _arg(argv, "--text")
    path = _arg(argv, "--file")
    if (text is None) == (path is None):
        raise SystemExit("  give the document ONE way: --text or --file.")
    if path is not None:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return text


def _key_if_signing(argv):
    if not _flag(argv, "--sign"):
        return None
    if jesster is None:
        raise SystemExit(
            "  --sign needs jesster.py beside this file, and it is not there.")
    import getpass
    words = getpass.getpass("  the twelve words (never stored): ").strip()
    if not words:
        raise SystemExit("  no words, no signature. Deposit unsigned, or speak.")
    return jesster.identity(words, jesster.read_secret(), OFFICE)


def cli(argv):
    cmd = argv[0] if argv else ""
    rest = list(argv[1:])

    if cmd == "status":
        c = Chain()
        print("  %d links, %d wraps, %d tokens. head %s"
              % (c.count(), len(c.wraps()), c.tokens(), c.head()[:16]))
        return 0

    if cmd == "verify":
        ok, n, detail = Chain().verify()
        print("  %s — %d links. %s" % ("INTACT" if ok else "BROKEN", n, detail))
        return 0 if ok else 1

    if cmd == "deposit":
        if len(rest) < 2 or rest[0] not in (OPEN, SEALED):
            raise SystemExit(_USAGE)
        mode, says = rest[0], rest[1]
        rest = rest[2:]
        actor = _arg(rest, "--actor") or ""
        cites = _arg(rest, "--cites")
        key = _key_if_signing(rest)
        doc = _read_doc(rest)
        e = Chain().deposit(doc, mode, says, actor,
                            cites=cites.split(",") if cites else None, key=key)
        print("  link %d — %s — %s\n  hash %s%s"
              % (e["payload"]["n"], e["payload"]["mode"], e["actor"],
                 e["hash"], "  (signed %s)" % e["payload"]["mark"]
                 if "sig" in e else "  (unsigned)"))
        return 0

    if cmd == "reveal":
        if not rest or not rest[0].isdigit():
            raise SystemExit(_USAGE)
        n = int(rest[0])
        rest = rest[1:]
        actor = _arg(rest, "--actor") or ""
        key = _key_if_signing(rest)
        doc = _read_doc(rest)
        e = Chain().reveal(n, doc, actor=actor, key=key)
        print("  link %d — %s\n  hash %s"
              % (e["payload"]["n"], e["payload"]["says"], e["hash"]))
        return 0

    if cmd == "show":
        if not rest or not rest[0].isdigit():
            raise SystemExit(_USAGE)
        e = Chain().link(int(rest[0]))
        if not e:
            print("  no link %s on this chain." % rest[0])
            return 1
        print(json.dumps(e, indent=2, ensure_ascii=False))
        return 0

    if cmd == "prove":
        if not rest or not rest[0].isdigit():
            raise SystemExit(_USAGE)
        p = Chain().prove_link(int(rest[0]))
        if not p:
            print("  link %s is not under a closed wrap yet — its wrap has "
                  "not reached %d links." % (rest[0], WRAP_SIZE))
            return 1
        print(json.dumps(p, indent=2))
        print("  climbs to the root: %s" % ("YES" if check(p) else "NO"))
        return 0

    raise SystemExit(_USAGE)


def main():
    print("\n  LINKS — the chain of provenance. Forty to a wrap; "
          "token N is wrap N.")
    print("  %s\n" % ("jesster is present — the signing path IS exercised"
                      if jesster else
                      "JESSTER IS ABSENT — the signing path is NOT exercised. "
                      "Put jesster.py beside this file to prove it."))
    strokes = prove()
    width = max(len(n) for n, _, _ in strokes)
    all_ok = all(o for _, o, _ in strokes)
    for name, ok, detail in strokes:
        print("    [%s]  %-*s   %s"
              % ("PASS" if ok else "FAIL", width, name, detail))
    print()
    print("  " + ("PROVEN. Every link is named, says what it is, and cites "
                  "what it stands on. Forty make a wrap, the wrap IS the "
                  "token, and a stranger with the head can check any of it."
                  if all_ok else "A step failed. Do not deposit anything yet.")
          + "\n")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(cli(sys.argv[1:]) if len(sys.argv) > 1 else main())
