"""mathkit — the zero-dependency numeric core.

Scope, stated honestly: this is NOT a NumPy replacement. NumPy is ~750k lines
of C-optimised ufuncs, broadcasting and memory layout, and a pure-Python
rewrite would be slower than what it replaces, not faster. What this module is
instead: the eight or so operations manjuel actually needs — similarity,
dispersion, and ordinary least squares — implemented correctly, with no third
party and no compilation, so the drift check and the statistics run on a box
with nothing installed.

Where numpy IS present it is still used for the index hot path (see
vectors.py), because scoring thousands of 768-dim chunks is exactly the case
pure Python loses. mathkit covers the per-call arithmetic, where the
difference is microseconds and the dependency is the thing worth removing.

Conventions, chosen once and applied everywhere:

- `ddof` is explicit. Population statistics (ddof=0) and sample statistics
  (ddof=1) are different numbers and mixing them silently is a real bug --
  a `std` computed with n and a `var` computed with n-1 do not satisfy
  std**2 == var, and code that assumes they do is wrong.
- Every function that can be handed empty or mismatched input says so by
  raising, rather than returning a plausible zero.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

Number = float
Vector = Sequence[float]


class MathError(ValueError):
    pass


# ---------------------------------------------------------------------
# vectors
# ---------------------------------------------------------------------


def dot(a: Vector, b: Vector) -> float:
    if len(a) != len(b):
        raise MathError(f"dot needs equal lengths; got {len(a)} and {len(b)}")
    if not a:
        raise MathError("dot of empty vectors is undefined")
    return math.fsum(x * y for x, y in zip(a, b))


def norm(a: Vector) -> float:
    if not a:
        raise MathError("norm of an empty vector is undefined")
    return math.sqrt(math.fsum(x * x for x in a))


def normalize(a: Vector) -> list[float]:
    n = norm(a)
    return [x / n for x in a] if n else list(a)


def cosine(a: Vector, b: Vector) -> float:
    """Cosine similarity, clamped to [-1, 1].

    Float error can push a self-comparison to 1.0000000000000002, which then
    reads as an impossible similarity downstream; the clamp is not cosmetic.
    """
    na, nb = norm(a), norm(b)
    if na == 0.0 or nb == 0.0:
        return 0.0
    return max(-1.0, min(1.0, dot(a, b) / (na * nb)))


# ---------------------------------------------------------------------
# dispersion
# ---------------------------------------------------------------------


def mean(xs: Vector) -> float:
    xs = list(xs)
    if not xs:
        raise MathError("mean of an empty sequence is undefined")
    return math.fsum(xs) / len(xs)


def variance(xs: Vector, ddof: int = 0) -> float:
    xs = list(xs)
    n = len(xs)
    if n - ddof <= 0:
        raise MathError(f"variance needs more than {ddof} value(s); got {n}")
    mu = mean(xs)
    return math.fsum((x - mu) ** 2 for x in xs) / (n - ddof)


def stdev(xs: Vector, ddof: int = 0) -> float:
    """stdev(xs, ddof)**2 == variance(xs, ddof), by construction."""
    return math.sqrt(variance(xs, ddof))


def covariance(xs: Vector, ys: Vector, ddof: int = 0) -> float:
    xs, ys = list(xs), list(ys)
    if len(xs) != len(ys):
        raise MathError(f"covariance needs equal lengths; got {len(xs)} and {len(ys)}")
    n = len(xs)
    if n - ddof <= 0:
        raise MathError(f"covariance needs more than {ddof} pair(s); got {n}")
    mx, my = mean(xs), mean(ys)
    return math.fsum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (n - ddof)


def median(xs: Vector) -> float:
    s = sorted(xs)
    n = len(s)
    if not n:
        raise MathError("median of an empty sequence is undefined")
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2.0


def zscore(x: float, xs: Vector, ddof: int = 0) -> float:
    sd = stdev(xs, ddof)
    return 0.0 if sd == 0.0 else (x - mean(xs)) / sd


# ---------------------------------------------------------------------
# ordinary least squares
# ---------------------------------------------------------------------


@dataclass(frozen=True)
class Fit:
    slope: float
    intercept: float
    r2: float
    n: int

    def predict(self, x: float) -> float:
        return self.slope * x + self.intercept

    def __str__(self) -> str:
        return f"y = {self.slope:.4g}x + {self.intercept:.4g}  (R2={self.r2:.4f}, n={self.n})"


def linear_regression(ys: Vector, xs: Vector | None = None) -> Fit:
    """OLS fit. `xs` defaults to 0,1,2,... -- it is NOT assumed to be length 5.

    Both variance and covariance use ddof=0 here; the ratio is identical
    either way, but mixing the two would not be.
    """
    ys = [float(y) for y in ys]
    n = len(ys)
    if n < 2:
        raise MathError(f"a fit needs at least 2 points; got {n}")
    xs = [float(x) for x in xs] if xs is not None else [float(i) for i in range(n)]
    if len(xs) != n:
        raise MathError(f"x has {len(xs)} points, y has {n}")

    vx = variance(xs, 0)
    if vx == 0.0:
        raise MathError("every x is identical; the slope is undefined")

    slope = covariance(xs, ys, 0) / vx
    intercept = mean(ys) - slope * mean(xs)

    # R^2 = 1 - SSres/SStot; when y is constant the fit is exact by definition.
    mu = mean(ys)
    ss_tot = math.fsum((y - mu) ** 2 for y in ys)
    ss_res = math.fsum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys))
    r2 = 1.0 if ss_tot == 0.0 else 1.0 - ss_res / ss_tot

    return Fit(slope=slope, intercept=intercept, r2=r2, n=n)


# ---------------------------------------------------------------------
# small matrix helpers
# ---------------------------------------------------------------------


def shape(m: Sequence[Sequence[float]]) -> tuple[int, int]:
    rows = len(m)
    if rows == 0:
        return (0, 0)
    cols = len(m[0])
    for r in m:
        if len(r) != cols:
            raise MathError("rows are not all the same length")
    return (rows, cols)


def transpose(m: Sequence[Sequence[float]]) -> list[list[float]]:
    r, c = shape(m)
    return [[float(m[i][j]) for i in range(r)] for j in range(c)]


def matmul(a: Sequence[Sequence[float]], b: Sequence[Sequence[float]]) -> list[list[float]]:
    ra, ca = shape(a)
    rb, cb = shape(b)
    if ca != rb:
        raise MathError(f"cannot multiply {ra}x{ca} by {rb}x{cb}")
    bt = transpose(b)
    return [[math.fsum(a[i][k] * bt[j][k] for k in range(ca)) for j in range(cb)]
            for i in range(ra)]


# ---------------------------------------------------------------------
# parsing numbers out of text -- WITHOUT executing it
# ---------------------------------------------------------------------


def parse_numbers(text: str, limit: int = 10_000) -> list[float]:
    """Pull a numeric series out of free text.

    Deliberately a scanner, not an evaluator. The obvious implementation --
    interpolating the text into source and running it -- would let any model
    that can write a number also write a statement. Nothing here executes.
    """
    import re

    if not text or not text.strip():
        raise MathError("no numbers given")

    # Order matters. The grouped form is tried FIRST, so "12,000" reads as one
    # number rather than as 12 and 000 -- while a bare "1,2,3" still reads as
    # three, because those groups are not three digits wide.
    pattern = re.compile(
        r"-?\d{1,3}(?:,\d{3})+(?:\.\d+)?"        # 1,234,567.8
        r"|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?"     # 12  3.4  14.5e3
    )
    found = pattern.findall(text)
    if not found:
        raise MathError("no numbers found in the input")
    if len(found) > limit:
        raise MathError(f"{len(found)} numbers is over the {limit} limit")
    return [float(f.replace(",", "")) for f in found]
