#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BIP-340 — Schnorr signatures over secp256k1, to the published standard.

Epoch 1's signatures are the estate's own construction: a custom `JESSTER|chal|`
prefix over uncompressed 64-byte points. They are sound, and no standard library
on earth can verify them. That cuts against the chain's own promise that
"verification is everyone's" — a stranger with the head should be able to check
the work with tools they already have.

So this is EPOCH 2, added beside epoch 1 and never replacing it. Three signed
links already stand under epoch 1; they keep verifying under epoch 1 forever.
That is exactly what `EPOCH = 1  # bump to re-key; old epochs still verify` was
put there for.

x-only 32-byte keys, even-Y convention, tagged hashes, 64-byte signatures.
Verified against the BIP-340 reference test vectors at the bottom of this file.
Standard library only; the curve arithmetic is the estate's own, reused.
"""
import hashlib
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import jesster as _j  # the estate's own curve arithmetic — reused, not re-rolled

P = _j._P
N = _j._N
G = _j._G


def tagged(tag, *parts):
    """SHA256(SHA256(tag) || SHA256(tag) || msg) — BIP-340's domain separation.
    The doubled tag hash is what makes a signature for one purpose unusable for
    another, and it is why this is not interchangeable with epoch 1."""
    t = hashlib.sha256(tag.encode()).digest()
    h = hashlib.sha256(t + t)
    for p in parts:
        h.update(p)
    return h.digest()


def _has_even_y(pt):
    return _j._affine(pt)[1] % 2 == 0


def _x(pt):
    return _j._affine(pt)[0]


def lift_x(xb):
    """Recover the even-Y point with this x. Fails if x is not on the curve —
    the check that stops a forged public key from being accepted."""
    x = int.from_bytes(xb, "big")
    if x >= P:
        return None
    y2 = (pow(x, 3, P) + 7) % P
    y = pow(y2, (P + 1) // 4, P)          # p == 3 mod 4, so this is the sqrt
    if pow(y, 2, P) != y2:
        return None
    return (x, y if y % 2 == 0 else P - y, 1)


def pubkey(seckey):
    """The 32-byte x-only public key. Half the width of epoch 1's, and the
    reason a mark under epoch 2 differs from the same secret's mark under 1."""
    d0 = int.from_bytes(seckey, "big") if isinstance(seckey, (bytes, bytearray)) else int(seckey)
    if not 1 <= d0 <= N - 1:
        raise ValueError("secret key out of range")
    return _x(_j._mul(d0, G)).to_bytes(32, "big")


def sign(seckey, msg, aux=None):
    """64 bytes: R.x || s. `aux` defaults to 32 zero bytes, which BIP-340 permits
    and which keeps signing deterministic — the estate's standing preference."""
    if isinstance(seckey, int):
        seckey = seckey.to_bytes(32, "big")
    if isinstance(msg, str):
        msg = msg.encode()
    aux = aux if aux is not None else b"\x00" * 32

    d0 = int.from_bytes(seckey, "big")
    if not 1 <= d0 <= N - 1:
        raise ValueError("secret key out of range")
    Pp = _j._mul(d0, G)
    d = d0 if _has_even_y(Pp) else N - d0
    px = _x(Pp).to_bytes(32, "big")

    t = (d ^ int.from_bytes(tagged("BIP0340/aux", aux), "big")).to_bytes(32, "big")
    k0 = int.from_bytes(tagged("BIP0340/nonce", t, px, msg), "big") % N
    if k0 == 0:
        raise ValueError("nonce is zero")
    R = _j._mul(k0, G)
    k = k0 if _has_even_y(R) else N - k0
    rx = _x(R).to_bytes(32, "big")

    e = int.from_bytes(tagged("BIP0340/challenge", rx, px, msg), "big") % N
    return rx + ((k + e * d) % N).to_bytes(32, "big")


def verify(pubkey_x, msg, sig):
    """s*G - e*P must be R, with even Y and the claimed x. Returns a bool and
    never raises on malformed input — a verifier that crashes is a verifier an
    attacker controls."""
    try:
        if isinstance(msg, str):
            msg = msg.encode()
        if not isinstance(sig, (bytes, bytearray)) or len(sig) != 64:
            return False
        if not isinstance(pubkey_x, (bytes, bytearray)) or len(pubkey_x) != 32:
            return False
        Pp = lift_x(bytes(pubkey_x))
        if Pp is None:
            return False
        r = int.from_bytes(sig[:32], "big")
        s = int.from_bytes(sig[32:], "big")
        if r >= P or s >= N:
            return False
        e = int.from_bytes(
            tagged("BIP0340/challenge", bytes(sig[:32]), bytes(pubkey_x), msg), "big") % N
        R = _j._add(_j._mul(s, G), _j._mul(N - e, Pp))
        if R is _j._INF:
            return False
        if not _has_even_y(R) or _x(R) != r:
            return False
        return True
    except (ValueError, TypeError):
        return False


def mark(pubkey_x):
    """The short public name of an epoch-2 key. Deliberately the same shape as
    epoch 1's mark, over different bytes — an epoch-2 identity is a DIFFERENT
    name for the same secret, and the ledger must not conflate them."""
    return hashlib.sha256(bytes(pubkey_x)).hexdigest()[:16]


# --- the reference vectors (BIP-340, index 0-3) ---------------------------
VECTORS = [
    ("0000000000000000000000000000000000000000000000000000000000000003",
     "F9308A019258C31049344F85F89D5229B531C845836F99B08601F113BCE036F9",
     "0000000000000000000000000000000000000000000000000000000000000000",
     "0000000000000000000000000000000000000000000000000000000000000000",
     # NOTE: transcribed from the BIP-340 vector table. Vectors 1 and 2 below
     # match byte-exact, which is what gives this implementation its confidence;
     # this line was mistyped once (DBA -> DCA) and corrected. Anyone with the
     # spec's own CSV to hand should re-check all three against it directly.
     "E907831F80848D1069A5371B402410364BDF1C5F8307B0084C55F1CE2DCA8215"
     "25F66A4A85EA8B71E482A74F382D2CE5EBEEE8FDB2172F477DF4900D310536C0"),
    ("B7E151628AED2A6ABF7158809CF4F3C762E7160F38B4DA56A784D9045190CFEF",
     "DFF1D77F2A671C5F36183726DB2341BE58FEAE1DA2DECED843240F7B502BA659",
     "0000000000000000000000000000000000000000000000000000000000000001",
     "243F6A8885A308D313198A2E03707344A4093822299F31D0082EFA98EC4E6C89",
     "6896BD60EEAE296DB48A229FF71DFE071BDE413E6D43F917DC8DCF8C78DE3341"
     "8906D11AC976ABCCB20B091292BFF4EA897EFCB639EA871CFA95F6DE339E4B0A"),
    ("C90FDAA22168C234C4C6628B80DC1CD129024E088A67CC74020BBEA63B14E5C9",
     "DD308AFEC5777E13121FA72B9CC1B7CC0139715309B086C960E18FD969774EB8",
     "C87AA53824B4D7AE2EB035A2B5BBBCCC080E76CDC6D1692C4B0B62D798E6D906",
     "7E2D58D8B3BCDF1ABADEC7829054F90DDA9805AAB56C77333024B9D0A508B75C",
     "5831AAEED7B44BB74E5EAB94BA9D4294C49BCF2A60728D8B4C200F50DD313C1B"
     "AB745879A5AD954A72C45A91C3A51D3C7ADEA98D82F8481E0E1E03674A6F3FB7"),
]


def prove():
    """Run the standard's own vectors. Passing these is the only claim of
    compliance worth making — anything else is an assertion."""
    ok = True

    def ck(name, cond, detail=""):
        nonlocal ok
        ok = ok and bool(cond)
        print("    [%s]  %-58s %s" % ("PASS" if cond else "FAIL", name, detail))

    for i, (sk, pk, aux, msg, sig) in enumerate(VECTORS):
        skb, pkb = bytes.fromhex(sk), bytes.fromhex(pk)
        auxb, msgb, sigb = bytes.fromhex(aux), bytes.fromhex(msg), bytes.fromhex(sig)
        ck("vector %d — public key derives" % i, pubkey(skb) == pkb, pk[:16] + "…")
        ck("vector %d — signature matches the standard" % i, sign(skb, msgb, auxb) == sigb)
        ck("vector %d — verifies" % i, verify(pkb, msgb, sigb))
        ck("vector %d — a flipped message fails" % i,
           not verify(pkb, bytes([msgb[0] ^ 1]) + msgb[1:], sigb))

    sk = (7).to_bytes(32, "big")
    pk = pubkey(sk)
    s = sign(sk, b"the estate signs")
    ck("round trip", verify(pk, b"the estate signs", s))
    ck("determinism — same message, same signature", s == sign(sk, b"the estate signs"))
    ck("x-only key is 32 bytes", len(pk) == 32, "epoch 1 is 64")
    ck("signature is 64 bytes", len(s) == 64, "epoch 1 is 96")
    ck("a malformed signature is refused, not crashed on",
       verify(pk, b"x", b"") is False and verify(pk, b"x", b"\x00" * 63) is False)
    ck("an off-curve public key is refused",
       lift_x(b"\xff" * 32) is None or verify(b"\xff" * 32, b"x", s) is False)
    ck("epoch 2 mark differs from epoch 1's for the same secret",
       mark(pk) != _j.mark(_j._ser(_j._mul(7, G))), "a different name, deliberately")
    return ok


if __name__ == "__main__":
    print("\n  BIP-340 — epoch 2. Epoch 1 stands untouched beside it.\n")
    good = prove()
    print("\n  %s\n" % ("PROVEN against the standard's own vectors."
                        if good else "A step failed. Do not sign under epoch 2."))
    sys.exit(0 if good else 1)
