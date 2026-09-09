"""Model plan: what a pipeline actually costs in loads and VRAM.

The metric that matters here is SWITCHES, not model count. The pipeline is
sequential by construction -- every stage consumes the one before it -- so
nothing overlaps and concurrency buys nothing. What costs wall-time is Ollama
evicting one model to make room for the next, then loading the first again.

A pipeline running A A B A pays three loads. The same seats ordered A A A B pay
two. Same models, less thrashing.

Sizing note: a model's VRAM footprint is NOT its file size. Measured on this
ground, a 986 MB model at num_ctx 32768 was resident at 4.2 GB -- the rest is
KV cache and compute buffers, sized by context and multiplied again by
OLLAMA_NUM_PARALLEL. The estimate below adds a KV term rather than pretending
weights are the whole story, and is still an estimate.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Rough KV+overhead bytes per context token, per model, at fp16 with GQA.
# Deliberately generous: under-estimating VRAM is the failure that thrashes.
KV_BYTES_PER_TOKEN = 90_000 / 8192      # ~11 KB/token, calibrated to the 4.2GB observation
GRAPH_OVERHEAD = 220_000_000            # compute buffers, roughly constant

# When Ollama cannot tell us a model's weight, assume it is LARGE. Guessing
# small makes every plan look like it fits and turns the eviction guard into a
# rubber stamp -- under-estimating VRAM is the failure that thrashes.
UNKNOWN_WEIGHT = 5_000_000_000

# The card is shared. Another client (opencode, a second REPL, anything) can be
# holding a model chainkit knows nothing about, and warming ours can evict
# theirs -- costing THEM a reload. Anything resident that this pipeline does not
# name is FOREIGN, and its bytes are spoken for.
import os

def budget_bytes() -> int:
    """Usable VRAM. Override with CHAINKIT_VRAM_GB when the guess is wrong."""
    try:
        return int(float(os.environ.get("CHAINKIT_VRAM_GB", "15")) * 1e9)
    except ValueError:
        return 15_000_000_000


def foreign(resident: list, mine: list[str]) -> list[tuple[str, int]]:
    """Resident models this pipeline does not use -- somebody else's."""
    owned = {m.split(":")[0] if ":" not in m else m for m in mine}
    return [(t, b) for t, b in resident if t not in owned]


@dataclass
class ModelPlan:
    pipeline: str
    order: list[tuple[str, str]]                 # (seat, model) in run order
    sizes: dict[str, int] = field(default_factory=dict)   # model -> weight bytes
    contexts: dict[str, int] = field(default_factory=dict)  # model -> max ctx used

    @property
    def sized(self) -> bool:
        """True when every model in the plan has a real weight from Ollama."""
        return bool(self.sizes) and all(self.sizes.get(m) for m in self.distinct)

    @property
    def distinct(self) -> list[str]:
        seen: list[str] = []
        for _, m in self.order:
            if m not in seen:
                seen.append(m)
        return seen

    @property
    def switches(self) -> int:
        """Loads incurred: the first model, plus every change of model."""
        if not self.order:
            return 0
        n = 1
        for i in range(1, len(self.order)):
            if self.order[i][1] != self.order[i - 1][1]:
                n += 1
        return n

    @property
    def ideal_switches(self) -> int:
        """Loads if the same seats were grouped by model -- the floor."""
        return len(self.distinct)

    def estimate(self, model: str, parallel: int = 1) -> int:
        w = self.sizes.get(model) or UNKNOWN_WEIGHT
        ctx = self.contexts.get(model, 8192)
        return int(w + ctx * KV_BYTES_PER_TOKEN * parallel + GRAPH_OVERHEAD)

    def resident_bytes(self, parallel: int = 1) -> int:
        """If every distinct model stayed loaded at once."""
        return sum(self.estimate(m, parallel) for m in self.distinct)

    def peak_pair_bytes(self, parallel: int = 1) -> int:
        """The most two consecutive models cost together -- the real floor for
        swapping without eviction mid-chain."""
        if len(self.order) < 2:
            return self.resident_bytes(parallel)
        worst = 0
        for i in range(1, len(self.order)):
            a, b = self.order[i - 1][1], self.order[i][1]
            if a != b:
                worst = max(worst, self.estimate(a, parallel) + self.estimate(b, parallel))
        return worst or self.estimate(self.order[0][1], parallel)


def gb(n: int) -> str:
    return f"{n / 1e9:.1f}GB"


def build_plan(name: str, steps: list, registry, skills=None,
               sizes: dict[str, int] | None = None) -> ModelPlan:
    order: list[tuple[str, str]] = []
    contexts: dict[str, int] = {}
    for step in steps:
        seat = str(step)          # a Step renders as its seat name
        a = registry.get(seat)
        order.append((a.name, a.model))
        contexts[a.model] = max(contexts.get(a.model, 0), a.context or 8192)
    return ModelPlan(pipeline=name, order=order, sizes=sizes or {}, contexts=contexts)


def installed_sizes(runtime) -> dict[str, int]:
    """Weight bytes per tag, from Ollama. Empty dict if it cannot be reached."""
    from .runtime import _field
    try:
        data = runtime._client.list()
    except Exception:
        return {}
    out: dict[str, int] = {}
    for m in _field(data, "models") or []:
        tag = _field(m, "model") or _field(m, "name")
        size = _field(m, "size")
        if tag and size:
            out[tag if ":" in tag else f"{tag}:latest"] = int(size)
    return out


def render(plan: ModelPlan, parallel: int = 1, budget: int | None = None,
           resident: list | None = None) -> str:
    lines = [f"  pipeline '{plan.pipeline}'"]
    prev = None
    for seat, model in plan.order:
        mark = " " if model == prev else "*"
        lines.append(f"    {mark} {seat:<20} {model}")
        prev = model
    lines.append("")
    lines.append(f"    distinct models : {len(plan.distinct)}")
    lines.append(f"    model loads     : {plan.switches}"
                 + (f"   (floor is {plan.ideal_switches} — "
                    f"{plan.switches - plan.ideal_switches} avoidable reload"
                    f"{'s' if plan.switches - plan.ideal_switches != 1 else ''})"
                    if plan.switches > plan.ideal_switches else "   (at the floor)"))

    if True:
        res = plan.resident_bytes(parallel)
        if not plan.sized:
            lines.append(f"    (weights unknown -- assuming {gb(UNKNOWN_WEIGHT)} each, "
                         f"deliberately high)")
        pair = plan.peak_pair_bytes(parallel)
        lines.append(f"    all resident    : ~{gb(res)}")
        lines.append(f"    worst adjacent  : ~{gb(pair)}  (two models loaded at a swap)")

        others = foreign(resident or [], plan.distinct)
        if others:
            ob = sum(b for _, b in others)
            lines.append(f"    NOT ours        : ~{gb(ob)}  "
                         f"({', '.join(t for t, _ in others)})")
            if budget:
                free = budget - ob
                lines.append(f"    left for us     : ~{gb(free)} of {gb(budget)}")
                if res > free:
                    lines.append("    ** warming ours would evict theirs. Share a tag, "
                                 "or accept the reload on both sides. **")
        elif budget:
            verdict = ("fits with everything resident" if res <= budget else
                       "will swap, but a swap fits" if pair <= budget else
                       "WILL THRASH — even one swap overflows")
            lines.append(f"    against {gb(budget)}   : {verdict}")
    lines.append("    * = a model load")
    return "\n".join(lines)
