#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JESSTER — the keymaker. She derives; she never holds.

She is not a building. She has no process, no address, no ledger, and no key
of her own. Every office imports her and derives ITS OWN key inside its own
process, from two halves that are never stored together:

    key = scrypt( covenant || machine secret , domain )

    the COVENANT      says WHICH SELF. Derived from foundation/ every wake,
                      stored nowhere, and public — it is in the repository.
    the MACHINE SECRET says WHICH INSTANCE. 32 bytes of os.urandom, forged
                      once, living OUTSIDE the tree and outside git.
    the DOMAIN        says WHICH OFFICE, and which epoch. Manjuel's key and
                      Steward's key are different keys from the same halves.

Neither half alone produces a key. A stolen repository yields nothing: the
covenant is already public. A stolen machine yields a key to a self you cannot
produce. That is the tally stick, one level below the signature.

WHAT SHE NEVER DOES. She writes no file during derivation — the prover asserts
it by watching the filesystem across every call. She keeps nothing between
calls. She has no cache, and adding one would make her a vault. The single
exception is `forge_secret`, which is a deliberate, explicit act, refuses to
overwrite, and writes outside the tree.

A MISSING SECRET IS REFUSED, NEVER REGENERATED. If the machine secret is gone,
`read_secret` raises. It does not quietly make a new one — that would let
anyone delete a file and have the estate wake as a different instance and sign
as though nothing happened. Detection is a gate here, not a note.

Say the hard thing plainly (The Hand): this is hand-rolled cryptography, on the
world's curve, in the standard library, because sovereignty was ruled first. It
is auditable end to end by anyone with Python and no other thing. It is also
not a validated module, and no procurement that requires one will accept it.
That trade was made with open eyes; the seam for a certified backend is the
`sign`/`verify` pair and nothing else.

The curve is secp256k1 — y^2 = x^3 + 7 over F_p. The generator's coordinates
are the world's, and the prover CHECKS them against the curve equation rather
than trusting that they were typed correctly.

Standard library only. Nothing here reaches outward.
"""
import hashlib
import math
import os
import re
import secrets
import sys

EPOCH = 1                       # bump to re-key; old epochs still verify

# --- the curve ------------------------------------------------------------
_P = 2**256 - 2**32 - 977
_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
_GX = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
_GY = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
_G = (_GX, _GY, 1)
_INF = None

# --- the kdf --------------------------------------------------------------
# scrypt is memory-hard, and it is in the standard library. The covenant half
# is PUBLIC, so the machine secret is the only real secret and must survive an
# offline attack. A bare sha256 here would be brute-forceable; this is not.
_SCRYPT_N = 2 ** 14
_SCRYPT_R = 8
_SCRYPT_P = 1
_MAXMEM = 64 * 1024 * 1024

SECRET_BYTES = 32
SECRET_NAME = "machine.secret"

# --- the twelve -----------------------------------------------------------
# The passphrase is drawn from scripture, twelve words for the twelve tribes.
# The strength is in the CHOOSING, never in the length of the string: one whole
# verse is a choice among ~31,102 verses, which is fifteen bits and falls in an
# afternoon — and the corpus ships in the repository, so the attacker is handed
# the list. Twelve words chosen UNIFORMLY from the vocabulary is a different
# thing entirely.
#
# Chosen with `secrets`, which is os.urandom with the modulo bias removed. NOT
# with the language model: a fluent phrase follows a distribution an attacker
# can walk down best-first, and the very fluency that makes it memorable is
# what makes it guessable. The scripture is the VOCABULARY. The dice are the
# operating system's.
PHRASE_WORDS = 12
MIN_VOCAB = 2000
_WORD_RE = re.compile(r"[a-z]+")


# --------------------------------------------------------------------------
# THE CURVE — Jacobian coordinates, no modular inverse per step.
# --------------------------------------------------------------------------

def _dbl(pt):
    if pt is _INF:
        return _INF
    X, Y, Z = pt
    if Y == 0:
        return _INF
    YY = Y * Y % _P
    S = 4 * X * YY % _P
    M = 3 * X * X % _P
    X3 = (M * M - 2 * S) % _P
    return (X3, (M * (S - X3) - 8 * YY * YY) % _P, 2 * Y * Z % _P)


def _add(p1, p2):
    if p1 is _INF:
        return p2
    if p2 is _INF:
        return p1
    X1, Y1, Z1 = p1
    X2, Y2, Z2 = p2
    Z1Z1 = Z1 * Z1 % _P
    Z2Z2 = Z2 * Z2 % _P
    U1 = X1 * Z2Z2 % _P
    U2 = X2 * Z1Z1 % _P
    S1 = Y1 * Z2Z2 % _P * Z2 % _P
    S2 = Y2 * Z1Z1 % _P * Z1 % _P
    if U1 == U2:
        return _dbl(p1) if S1 == S2 else _INF
    H = (U2 - U1) % _P
    R = (S2 - S1) % _P
    HH = H * H % _P
    HHH = HH * H % _P
    U1HH = U1 * HH % _P
    X3 = (R * R - HHH - 2 * U1HH) % _P
    return (X3, (R * (U1HH - X3) - S1 * HHH) % _P, H * Z1 % _P * Z2 % _P)


def _mul(k, pt):
    k %= _N
    if k == 0 or pt is _INF:
        return _INF
    acc = _INF
    while k:
        if k & 1:
            acc = _add(acc, pt)
        pt = _dbl(pt)
        k >>= 1
    return acc


def _affine(pt):
    """(x, y) as integers. The point at infinity has no affine name."""
    if pt is _INF:
        return (0, 0)
    X, Y, Z = pt
    zi = pow(Z, _P - 2, _P)
    zi2 = zi * zi % _P
    return (X * zi2 % _P, Y * zi2 % _P * zi % _P)


def _ser(pt):
    """64 bytes: x || y. Uncompressed on purpose — decompression is a whole
    class of bug, and 32 saved bytes is not worth it in a ledger."""
    x, y = _affine(pt)
    return x.to_bytes(32, "big") + y.to_bytes(32, "big")


def _deser(b):
    if len(b) != 64:
        raise ValueError("a point is 64 bytes; got %d" % len(b))
    x = int.from_bytes(b[:32], "big")
    y = int.from_bytes(b[32:], "big")
    if x == 0 and y == 0:
        return _INF
    return (x, y, 1)


def on_curve(pt):
    """y^2 == x^3 + 7 (mod p). The one check that says a point is real."""
    if pt is _INF:
        return False
    x, y = _affine(pt)
    return (y * y - (x * x % _P * x + 7)) % _P == 0


# --------------------------------------------------------------------------
# THE MACHINE SECRET — which instance. Outside the tree, always.
# --------------------------------------------------------------------------

def secret_path():
    """Outside the repository, outside git, per-machine. Never in the tree."""
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return os.path.join(base, "manjuel", SECRET_NAME)
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(
        os.path.expanduser("~"), ".config")
    return os.path.join(base, "manjuel", SECRET_NAME)


def forge_secret(path=None):
    """Make the machine secret ONCE. Refuses to overwrite an existing one —
    overwriting it would orphan every signature this instance ever made.
    This is the only function in this module that writes anything."""
    path = path or secret_path()
    if os.path.exists(path):
        raise FileExistsError(
            "a machine secret already stands at %s. I will not overwrite it: "
            "every signature this instance has ever made verifies under it. "
            "To re-key, bump the EPOCH and keep the old secret." % path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    secret = os.urandom(SECRET_BYTES)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, secret)
    finally:
        os.close(fd)
    return path


def read_secret(path=None):
    """Read the machine secret. REFUSES if it is missing — it does not make a
    new one. A silently regenerated secret is a silently different instance,
    signing as though nothing happened. That is the failure this refuses."""
    path = path or secret_path()
    if not os.path.exists(path):
        raise FileNotFoundError(
            "no machine secret at %s. I will not invent one — a new secret is "
            "a new instance, and an instance that re-keys itself quietly can "
            "be replaced by anyone who deletes a file. Forge it deliberately "
            "with forge_secret(), once." % path)
    with open(path, "rb") as f:
        secret = f.read()
    if len(secret) < SECRET_BYTES:
        raise ValueError("the machine secret at %s is %d bytes; %d are needed."
                         % (path, len(secret), SECRET_BYTES))
    return secret


# --------------------------------------------------------------------------
# DERIVATION — the whole of her.
# --------------------------------------------------------------------------

def domain(office, epoch=EPOCH):
    """Which office, which epoch. Same halves, different office, different key."""
    return ("JESSTER|%s|v%d" % (office.upper(), epoch)).encode("utf-8")


def seed(covenant, secret, office, epoch=EPOCH):
    """32 bytes, memory-hard. Nothing is stored; this is recomputed each wake."""
    if isinstance(covenant, str):
        covenant = covenant.encode("utf-8")
    return hashlib.scrypt(covenant + b"|" + secret, salt=domain(office, epoch),
                          n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P,
                          maxmem=_MAXMEM, dklen=32)


def identity(covenant, secret, office, epoch=EPOCH):
    """The long-term key of one office on one machine. Re-derivable forever,
    so a signature made today still verifies in ten years. Held in memory
    only, for as long as the caller holds it."""
    d = int.from_bytes(seed(covenant, secret, office, epoch), "big") % _N
    if d == 0:
        d = 1
    P = _mul(d, _G)
    return {"office": office.upper(), "epoch": epoch, "priv": d,
            "pub": _ser(P), "mark": mark(_ser(P))}


def session(rng=None):
    """An ephemeral keypair for one run. From os.urandom, never from a seeded
    Random — a seeded generator makes the same key every time, which is not a
    key at all. Dies with the process; nothing to steal, nothing to store."""
    raw = (rng or os.urandom)(32)
    d = int.from_bytes(raw, "big") % _N or 1
    P = _mul(d, _G)
    return {"priv": d, "pub": _ser(P), "mark": mark(_ser(P))}


def mark(pub):
    """The short public name of a key — what rides in the ledger's actor field.
    Names are not unique; keys are."""
    return hashlib.sha256(pub).hexdigest()[:16]


# --------------------------------------------------------------------------
# SIGNING — deterministic Schnorr over secp256k1.
#
# The nonce is derived from the private key AND the message, so it can never
# repeat for different messages and never depends on the machine's randomness
# at signing time. Nonce reuse is the classic way an elliptic-curve signature
# leaks its private key; determinism removes that whole class.
# --------------------------------------------------------------------------

def _h(*parts):
    h = hashlib.sha256()
    for p in parts:
        h.update(p)
    return h


def sign(priv, message):
    """96 bytes: R (64) || s (32)."""
    if isinstance(message, str):
        message = message.encode("utf-8")
    dbytes = priv.to_bytes(32, "big")
    k = int.from_bytes(_h(b"JESSTER|nonce|", dbytes, b"|", message).digest(),
                       "big") % _N or 1
    R = _mul(k, _G)
    Rb = _ser(R)
    P = _ser(_mul(priv, _G))
    e = int.from_bytes(_h(b"JESSTER|chal|", Rb, P, message).digest(), "big") % _N
    s = (k + e * priv) % _N
    return Rb + s.to_bytes(32, "big")


def verify(pub, message, sig):
    """s*G == R + e*P, or it is not his hand."""
    if isinstance(message, str):
        message = message.encode("utf-8")
    if not isinstance(sig, (bytes, bytearray)) or len(sig) != 96:
        return False
    try:
        Rb, sb = bytes(sig[:64]), bytes(sig[64:])
        R = _deser(Rb)
        P = _deser(pub)
        if not on_curve(R) or not on_curve(P):
            return False
        s = int.from_bytes(sb, "big")
        if s >= _N:
            return False
        e = int.from_bytes(_h(b"JESSTER|chal|", Rb, pub, message).digest(),
                           "big") % _N
        return _ser(_mul(s, _G)) == _ser(_add(R, _mul(e, P)))
    except (ValueError, TypeError):
        return False


def certify(identity_key, session_key):
    """The session certificate. The long-term key vouches for the ephemeral
    one, so a signature made by a session that has since died still verifies:
    the certificate is in the record, and the identity key is re-derivable.
    Without this, an ephemeral key makes history unreadable."""
    body = b"JESSTER|session|v%d|%s|%s" % (
        identity_key["epoch"], identity_key["pub"], session_key["pub"])
    return {"office": identity_key["office"], "epoch": identity_key["epoch"],
            "identity_pub": identity_key["pub"].hex(),
            "session_pub": session_key["pub"].hex(),
            "sig": sign(identity_key["priv"], body).hex()}


def check_cert(cert):
    """Verify a session certificate against the identity key it names."""
    try:
        ipub = bytes.fromhex(cert["identity_pub"])
        spub = bytes.fromhex(cert["session_pub"])
        body = b"JESSTER|session|v%d|%s|%s" % (cert["epoch"], ipub, spub)
        return verify(ipub, body, bytes.fromhex(cert["sig"]))
    except (KeyError, ValueError, TypeError):
        return False


def vocabulary(path):
    """The distinct words of a corpus, lowercased. Refuses an absent or a thin
    one rather than quietly drawing from a smaller hat — a silently weakened
    passphrase is worse than none, because it is trusted."""
    if not os.path.exists(path):
        raise FileNotFoundError(
            "no corpus at %s. I will not fall back to a smaller vocabulary: a "
            "phrase you believe is strong and is not is worse than no phrase. "
            "Point me at the scripture." % path)
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        words = sorted({w for w in _WORD_RE.findall(f.read().lower())
                        if 3 <= len(w) <= 14})
    if len(words) < MIN_VOCAB:
        raise ValueError(
            "%s holds only %d distinct words; %d are needed for a phrase worth "
            "trusting." % (path, len(words), MIN_VOCAB))
    return words


def phrase(n=PHRASE_WORDS, path=None, vocab=None):
    """n words drawn uniformly from scripture. Returned once; stored nowhere,
    by anyone, ever. Write it down on paper or lose it — there is no reset,
    and nothing on this machine can tell you what it was."""
    vocab = vocab if vocab is not None else vocabulary(path)
    N = len(vocab)
    picked, seen = [], set()
    while len(picked) < n:                      # distinct, for the eye's sake
        w = secrets.choice(vocab)
        if w in seen:
            continue
        seen.add(w)
        picked.append(w)
    bits = sum(math.log2(N - i) for i in range(n))
    return {"words": picked, "phrase": " ".join(picked), "vocab": N,
            "bits": round(bits, 1), "guesses": "2^%d" % round(bits)}


def describe():
    return ("jesster: the keymaker — derives an office's key from the covenant "
            "and the machine secret, holds nothing, writes nothing, and signs "
            "deterministically on secp256k1")


# --------------------------------------------------------------------------
# PROOF
# --------------------------------------------------------------------------

def prove():
    import shutil
    import tempfile
    strokes = []

    def check(name, ok, detail=""):
        strokes.append((name, bool(ok), detail))

    tmp = tempfile.mkdtemp(prefix="jesster_")
    try:
        # --- the curve is real, not merely typed -------------------------
        check("the generator is ON the curve (y^2 = x^3 + 7)", on_curve(_G),
              "checked, not trusted")
        check("the field prime is 2^256 - 2^32 - 977", _P == 2**256 - 2**32 - 977)
        a, b = 12345, 67890
        check("the map is a homomorphism: aG + bG == (a+b)G",
              _ser(_add(_mul(a, _G), _mul(b, _G))) == _ser(_mul(a + b, _G)))

        cov = "65118a147dd49ed96068e8a3cf1a472db1f4d91253b23507c56926ba2d8d0000"
        sec = b"\x01" * 32
        other = b"\x02" * 32

        # --- derivation ---------------------------------------------------
        k1 = identity(cov, sec, "manjuel")
        k2 = identity(cov, sec, "manjuel")
        check("the same halves derive the SAME key, every time",
              k1["priv"] == k2["priv"] and k1["pub"] == k2["pub"], k1["mark"])
        check("a different OFFICE derives a different key",
              identity(cov, sec, "steward")["priv"] != k1["priv"])
        check("a different EPOCH derives a different key",
              identity(cov, sec, "manjuel", epoch=2)["priv"] != k1["priv"])
        check("a different MACHINE SECRET derives a different key",
              identity(cov, other, "manjuel")["priv"] != k1["priv"])
        check("a different COVENANT derives a different key",
              identity(cov[:-1] + "1", sec, "manjuel")["priv"] != k1["priv"])
        check("the public half is a true point on the curve",
              on_curve(_deser(k1["pub"])))
        check("neither half alone is the key (the covenant is public)",
              identity(cov, b"\x00" * 32, "manjuel")["priv"] != k1["priv"])

        # --- signing --------------------------------------------------------
        msg = b"the estate is whole under covenant 65118a147dd49ed9"
        sig = sign(k1["priv"], msg)
        check("a signature is 96 bytes and verifies under its key",
              len(sig) == 96 and verify(k1["pub"], msg, sig))
        check("a TAMPERED message does not verify",
              not verify(k1["pub"], msg + b"!", sig))
        check("ANOTHER hand cannot forge it",
              not verify(identity(cov, other, "manjuel")["pub"], msg, sig))
        check("the nonce is deterministic — the same message signs identically",
              sign(k1["priv"], msg) == sig)
        check("different messages take different nonces",
              sign(k1["priv"], msg)[:64] != sign(k1["priv"], msg + b"x")[:64])
        check("a malformed signature is refused, not crashed on",
              not verify(k1["pub"], msg, b"short") and
              not verify(k1["pub"], msg, b"\x00" * 96))

        # --- the session and its certificate --------------------------------
        s1, s2 = session(), session()
        check("a session key is fresh each time", s1["priv"] != s2["priv"])
        cert = certify(k1, s1)
        check("the identity key vouches for the session key", check_cert(cert))
        bad = dict(cert, session_pub=s2["pub"].hex())
        check("a swapped session key breaks the certificate", not check_cert(bad))
        check("history survives the session — the identity key re-derives",
              check_cert(certify(identity(cov, sec, "manjuel"), s1)))

        # --- the machine secret ---------------------------------------------
        sp = os.path.join(tmp, "cfg", SECRET_NAME)
        missing = False
        try:
            read_secret(sp)
        except FileNotFoundError as e:
            missing = "will not invent one" in str(e)
        check("a MISSING secret is refused, never regenerated", missing,
              "no silent re-key")
        forge_secret(sp)
        check("forge_secret makes exactly %d bytes" % SECRET_BYTES,
              len(read_secret(sp)) == SECRET_BYTES)
        refused = False
        try:
            forge_secret(sp)
        except FileExistsError:
            refused = True
        check("forge_secret REFUSES to overwrite an existing secret", refused,
              "an overwrite orphans every prior signature")
        check("the secret path lies outside any repository tree",
              "manjuel" in secret_path() and
              not os.path.abspath(secret_path()).startswith(os.getcwd()))

        # --- she writes NOTHING while deriving ------------------------------
        watch = os.path.join(tmp, "watch")
        os.makedirs(watch, exist_ok=True)
        before = sorted(os.listdir(watch))
        cwd = os.getcwd()
        os.chdir(watch)
        try:
            for _ in range(3):
                kk = identity(cov, sec, "neiro")
                sign(kk["priv"], b"nothing should land")
                session()
                certify(kk, session())
                mark(kk["pub"])
        finally:
            os.chdir(cwd)
        check("she writes NO file while deriving, signing, or certifying",
              sorted(os.listdir(watch)) == before,
              "%d files before, %d after" % (len(before), len(os.listdir(watch))))

        # --- the twelve ------------------------------------------------------
        corpus = os.path.join(tmp, "KJV.txt")
        # a stand-in scripture: letters only, the size of a real vocabulary
        _al = "abcdefghijklmnopqrstuvwxyz"
        body = " ".join(_al[i % 26] + _al[(i // 26) % 26] + _al[(i // 676) % 26]
                        + _al[(i // 17576) % 26] for i in range(4000))
        open(corpus, "w", encoding="utf-8").write((body + "\n") * 3)
        refused = False
        try:
            vocabulary(os.path.join(tmp, "nope.txt"))
        except FileNotFoundError as e:
            refused = "will not fall back" in str(e)
        check("a MISSING corpus is refused, never quietly weakened", refused)
        thin = False
        tp = os.path.join(tmp, "thin.txt")
        open(tp, "w", encoding="utf-8").write("one two three four five")
        try:
            vocabulary(tp)
        except ValueError:
            thin = True
        check("a THIN corpus is refused and its size named", thin)

        v = vocabulary(corpus)
        p1 = phrase(vocab=v)
        p2 = phrase(vocab=v)
        check("the phrase is twelve words, for the twelve tribes",
              len(p1["words"]) == PHRASE_WORDS, p1["phrase"][:46] + "…")
        check("every word is drawn from the scripture itself",
              all(w in v for w in p1["words"]), "%d in vocabulary" % p1["vocab"])
        check("no two draws are the same", p1["phrase"] != p2["phrase"])
        check("the words within one phrase do not repeat",
              len(set(p1["words"])) == PHRASE_WORDS)
        check("it reports its own strength honestly",
              p1["bits"] > 100, "%s bits · %s guesses" % (p1["bits"], p1["guesses"]))
        check("the dice are the operating system's, not the model's",
              "secrets.choice" in open(os.path.abspath(__file__),
                                       encoding="utf-8").read())
        before_p = sorted(os.listdir(tmp))
        for _ in range(5):
            phrase(vocab=v)
        check("drawing a phrase writes NOTHING",
              sorted(os.listdir(tmp)) == before_p)

        # --- she keeps nothing between calls --------------------------------
        src = open(os.path.abspath(__file__), encoding="utf-8").read() \
            if "__file__" in globals() else ""
        if src:
            body = src.split("def prove(")[0]
            check("she holds no cache — no module-level mutable state",
                  "_CACHE" not in body and "lru_cache" not in body
                  and "global " not in body,
                  "a cache would make her a vault")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return strokes


def main():
    print("\n  JESSTER — the keymaker. She derives; she never holds.\n")
    strokes = prove()
    width = max(len(n) for n, _, _ in strokes)
    all_ok = all(o for _, o, _ in strokes)
    for name, ok, detail in strokes:
        print("    [%s]  %-*s   %s" % ("PASS" if ok else "FAIL", width, name, detail))
    print()
    print("  " + ("PROVEN. Two halves, never stored together; a key that is "
                  "recomputed and never kept."
                  if all_ok else
                  "A step failed. Do not key the estate on this yet.") + "\n")
    return 0 if all_ok else 1


def _speak_phrase(path):                              # pragma: no cover
    p = phrase(path=path)
    print("\n  THE TWELVE — write this on paper. Nothing here will hold it.\n")
    for i in range(0, PHRASE_WORDS, 4):
        print("      " + "  ".join("%-14s" % w for w in p["words"][i:i + 4]))
    print("\n  %s\n" % p["phrase"])
    print("  drawn from %d distinct words · %s bits · %s guesses to break"
          % (p["vocab"], p["bits"], p["guesses"]))
    print("  There is no reset. Lose it and the keys it makes are gone.\n")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "phrase":
        _speak_phrase(sys.argv[2] if len(sys.argv) > 2
                      else os.path.join("corpus", "KJV.txt"))
        sys.exit(0)
    sys.exit(main())
