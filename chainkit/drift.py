"""Drift: does a stage's output still say what the source said?

This is §11's tier-1 check. It is not a model judging a model -- it is a
measurement. Embed the source material, embed what a stage produced, take the
cosine. A low score means the stage wandered from, dropped, or invented
material relative to what it was given.

Why it matters here specifically: the Morning Reviewer is a 0.5b model running
FIRST, compressing a noisy feed to two sentences. Everything downstream
inherits whatever it discarded or made up, and no later seat can recover it.
A cosine score cannot hallucinate, and it costs one embedding per stage.

It is ADVISORY. A low score is recorded and reported, never used to rewrite or
silently discard a stage -- the same principle that keeps Manjuel and Jesster
from rewriting the work they rule on. What it can do is raise a flag, so a
`When:` step could react to it.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import mathkit

# Below this cosine, a stage is reported as having drifted. Chosen to be
# quiet in normal use: unrelated text on nomic-embed-text sits near 0.2-0.4,
# a faithful summary of its source typically 0.7+.
# A short objective carries less signal than a full feed, so a bare-objective
# comparison is judged against a lower bar -- see `threshold_for`.
DRIFT_WARN = 0.55
DRIFT_WARN_SHORT = 0.35

# Two floors, not one. An OUTPUT needs real length before a cosine means
# anything. A SOURCE does not: "review the git init" is only 19 characters and
# is still exactly the thing the answer should be about. Sessions 3 and 4 both
# skipped the check entirely because one floor was applied to both, so the
# 274MB embedder never ran at all.
MIN_OUTPUT_CHARS = 80
MIN_SOURCE_CHARS = 12


@dataclass
class DriftScore:
    score: float
    ok: bool
    reason: str = ""

    def stamp(self) -> str:
        if self.reason:
            return f"drift: not scored ({self.reason})"
        verdict = "ok" if self.ok else "DRIFTED"
        return f"drift: {self.score:.3f} {verdict}"


class DriftChecker:
    """Embeds the source once per run, then scores each stage against it."""

    def __init__(self, runtime, model: str, threshold: float = DRIFT_WARN):
        self.runtime = runtime
        self.model = model
        self.threshold = threshold
        self._source: list[float] | None = None
        self._failed = False
        self._noted = False   # a skip is reported once, not once per stage
        self._short_source = False

    def prime(self, source_text: str) -> bool:
        """Embed the source material. False if it cannot be scored at all."""
        if self._failed:
            return False
        text = (source_text or "").strip()
        if len(text) < MIN_SOURCE_CHARS:
            self._failed = True
            return False
        self._short_source = len(text) < 200
        try:
            self._source = self.runtime.embed(self.model, text)
            return True
        except Exception:
            # An embedder that is missing or down must not take the run with
            # it -- the check is a courtesy, not a dependency.
            self._failed = True
            return False

    def note_once(self, reason: str) -> str | None:
        """Return `reason` the first time only, so a skipped check is stated
        without repeating itself at every stage."""
        if self._noted:
            return None
        self._noted = True
        return reason

    def score(self, output: str) -> DriftScore | None:
        if self._failed or self._source is None:
            return None
        text = (output or "").strip()
        if len(text) < MIN_OUTPUT_CHARS:
            return DriftScore(0.0, True, reason="output too short to score")
        try:
            vec = self.runtime.embed(self.model, text)
        except Exception as exc:
            return DriftScore(0.0, True, reason=f"embedder unavailable: {exc}")

        sim = mathkit.cosine(self._source, vec)
        # Against a bare objective the expected similarity is genuinely lower;
        # holding it to the full-feed bar would cry drift on every short run.
        bar = DRIFT_WARN_SHORT if self._short_source else self.threshold
        return DriftScore(sim, sim >= bar)
