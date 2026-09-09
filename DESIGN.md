# Manjuel CLI — Architecture Design

Design target: a local, Ollama-backed multi-agent REPL where **markdown is the
source of truth** and Python is only the engine that runs them.

**EVERYTHING IS LOCAL.** No cloud service, no API key, no network call is part
of this build. It runs with the router unplugged. A dependency that needs
someone else's server does not go in, whatever it offers — that property is
the point of the estate and is the hardest one to get back once given up.

> **Status.** §§1–2 are current. Sections 3–12 describe the original design
> and are kept as the record of intent; §13 is what sessions 5–13 built, and
> **§14 is what sittings 14–64 built and is authoritative where they
> disagree** — including §9's model sizing, which §14.2 supersedes.
> §14.10's landing gate and §14.11 carry session 2 (2026-09-03, sittings
> 75–81). **§14.12 carries session 3 (sitting 82) and is the one section a
> new hand should read first** — it names a fault this estate commits
> against its own LAW 5, in four places, and argues why they are one sweep
> and not four bugs. HANDOFF.md is the live operational record and moves
> faster than this file; DAYBOOK.md carries what a session was FOR.
>
> §11's "LANDED" paragraph is CORRECTED in place: the drift check is armed
> only when a run carries a pasted feed. It DID score 41 transcripts on
> 2026-08-29, when the seats were llama3.2 and runs carried a feed; it has
> produced no score since the spine moved (checked 2026-09-04 over 599).
>
> Two lines in §4 are SUPERSEDED and kept as intent: `MAX_TOOL_STEPS` is 5,
> not 4 (it rose with the dedup at sitting 63), and `<content>` IS matched
> greedily on purpose (`_CONTENT_RE` in skills.py, through to the LAST
> closing tag, so a payload that itself contains the tag survives) — the
> preamble here said the opposite until 2026-09-04. `extract_tool_call` reads
> the estate's own tags and a native `tool_calls` is rendered into the same
> shape (see 14.x).

---

## 1. What was wrong with the first build — all fixed

Kept as the record of why the rewrite happened. Every row below is closed;
`manjuel.py` is now a thin entrypoint into `manjuel/`.

| # | Issue | Consequence |
|---|---|---|
| 1 | Bottom of the file is mangled — `except`/`if` collapsed onto single lines, and `if name == "main"` instead of `if __name__ == "__main__"` | **The file does not parse.** Nothing runs. |
| 2 | `agents.md` defines 6 personas; the pipeline hardcodes 4 models and re-inlines the prompts | The manifest is decorative. Editing `agents.md` changes nothing. |
| 3 | Persona prompts are sent as `role: user`, never `role: system` | Weaker steering, and the persona competes with the payload for the model's attention. |
| 4 | **Security Guardian** and **Expert Coder** are defined but never invoked | Two of six agents are dead weight. The safety gate you wrote does not run. |
| 5 | `raw_feed = input()` on multi-line paste | Line 1 becomes the feed; **remaining lines get consumed as the next loop's prompts.** Silent data loss on exactly the "paste a news feed" use case. |
| 6 | Skills manifest is generated from `skills/*.md`, but `execute_markdown_skill` dispatches on a hardcoded if/elif Manjuel | Drop a new `.md` in `skills/` and the router will confidently call a skill that cannot execute. Manifest and executor drift with no warning. |
| 7 | Each stage receives only the previous stage's string | The pipeline is a telephone game. By step 4 the original topic is gone — the delivery agent formats a 0.5b model's rewrite of a 0.5b model's summary. |
| 8 | Inner `except` catches only connection errors | A missing model tag or a malformed response dict kills the whole REPL instead of the run. |
| 9 | Pipeline runs entirely on 0.5b–1.5b models while 4b/7b/9b/14b tags sit unused locally | Every tag resolves, so nothing crashes — but the quality ceiling is set by the smallest model in Manjuel. See §9. |
| 10 | `logs/` exists and holds a prior transcript, but nothing in `manjuel.py` writes to it | Runs are unreproducible. |
| 11 | No streaming | Dead terminal for the duration of every generation. |

Worth keeping: `get_safe_workspace_path` — `os.path.basename` is a sound jail against `../` traversal. Don't lose it in the rewrite.

---

## 2. Module layout

```
manjuel/
  cli.py         # REPL loop, slash commands, rendering
  boot.py        # startup report: GROUND / RACK / RECORD / GATE / VOICE

  registry.py    # agents/*.md + pipelines.md -> Agent, Step
  skills.py      # skills/*.md -> SkillSpec, bound to @skill handlers
  seating.py     # the seat RACK: resting seats, summoned by flag  (§13.1)
  pipeline.py    # executes a running order against a RunContext
  context.py     # RunContext: objective, feed, steps, flags, notes
  intent.py      # deterministic pre-routing: does the objective name a tool?

  runtime.py     # Ollama client: health, chat, embed, warm, resident
  vram.py        # footprint planning, foreign-model detection
  rack.py        # model rack survey -> rack.md
  watch.py       # the ground watches itself (watchdog, optional; no-ops without it)

  vectors.py     # the semantic index; secret-file refusal
  drift.py       # advisory cosine of each stage against the source
  mathkit.py     # dot, cosine, regression — no numpy
  parity.py      # Manjuel vs a bare call to the same model      (§13.3)

  us.py          # the capability manifest, parsed and RECONCILED to code
  lawgate.py     # the law gate: the sealed Manjuel walked, the objective checked, every run stamped (§14.13)
  memory.py      # memory.md, append-only + pending staging
  seatlog.py     # sittings and the toll
  transcript.py  # logs/<timestamp>_<slug>.md; demotes seat headings
  gitstate.py    # read-only git + local init/commit; stale-lock detection

  voice.py       # speech out (OS engine) and in (whisper)      (§13.2)
  spelling.py    # deterministic correction of the delivery     (§13.2)
  ink.py         # per-seat colour, spinner; no-ops when not a tty
  dotenv.py      # .env loading; returns key NAMES, never values
manjuel.py         # thin entrypoint -> manjuel.cli:main
```

**The containment rule, and it has held.** `registry.py` and `skills.py` know
about markdown, nothing else does. `runtime.py` knows about Ollama, nothing
else does. That is why the parser is testable with no model running, the
pipeline is testable with a fake runtime, and the whole stroke suite runs
offline in about a second.

---

## 3. `agents.md` as source of truth

Your current headings already parse cleanly. Extend the schema with optional keys — old sections stay valid.

```markdown
## Security Guardian
- **Model Target:** qwen2.5:1.5b
- **Stage:** guard
- **On Fail:** abort
- **System Prompt:**
You are a strict Operational Security Guardian...
```

Parsed into:

```python
@dataclass(frozen=True)
class Agent:
    name: str
    model: str
    system_prompt: str
    stage: str          # guard | transform | route | gate | deliver
    on_fail: str = "prompt"   # abort | skip | prompt
    when: str | None = None   # optional condition key, see §5
```

**Pipeline order lives in the same file**, so one document describes the whole system:

```markdown
## Pipeline: default
1. Security Guardian
2. Morning Reviewer
3. Router
4. Quality Evaluator
5. Expert Coder      (when: technical)
6. Delivery Agent
```

`/reload` re-parses this at runtime. Prompt iteration becomes: edit markdown → `/reload` → rerun. No restart, no code change.

**Parser contract:** a `## Name` section requires `Model Target` and `System Prompt`. Missing either → startup error naming the section. Unknown `- **Key:**` lines → warn and ignore, so the format can grow without breaking old files.

---

## 4. Skills: markdown declares, Python implements

The drift in issue #6 is the important structural bug. Fix it by making the two halves verify each other at startup.

```python
@skill("read_file", params=["filepath"])
def read_file(ctx: RunContext, filepath: str) -> str:
    ...
```

Startup validation, before the REPL accepts input:

- every `Action Keyword` in `skills/*.md` has a registered `@skill` → else **error**, the router would hallucinate a callable tool
- every `@skill` has a matching `.md` → else **warn**, the model can never discover it
- declared `Parameters Needed` match the handler signature → else **error**

This turns a silent runtime failure into a loud startup failure, which is the whole point.

**Tool loop, not a single shot.** Current code parses one XML block and moves on. Let the router run up to `MAX_TOOL_STEPS` (suggest 4): call skill → append result to context → re-prompt → stop when it emits no `<action>`. Cap it so a small model can't spin.

**Parsing:** keep XML tags — they're friendlier to small models than JSON. But the non-greedy `<content>(.*?)</content>` breaks the moment a payload contains tags. Match greedily to the *last* closing tag, and validate that the extracted action is a known keyword before dispatch.

---

## 5. Context flows forward, not sideways

Replace string-passing with an accumulating context. This is the single highest-value change.

```python
@dataclass
class StepResult:
    agent: str; model: str; output: str
    elapsed: float; tool_calls: list[str]

@dataclass
class RunContext:
    objective: str          # never lost
    feed: str               # never lost
    steps: list[StepResult]
    flags: set[str]         # e.g. {"technical"} — drives `when:`
    artifacts: list[Path]
```

Every agent prompt is built from `objective` + `feed` + *selected* prior steps — not just `steps[-1]`. The Delivery Agent should see the original objective alongside the verified report; right now it cannot.

`flags` is how conditional steps work: the Router sets `technical` when the objective needs code, and **Expert Coder** (`when: technical`) activates. That's your unused sixth agent earning its place without a hardcoded branch.

---

## 6. REPL design

Keeping the interactive loop, but with the sharp edges filed off.

**Multi-line input.** Fixes issue #5:

```
📰 Paste context (end with a line containing only "."; blank to skip):
```

Read lines until the sentinel. Alternatively `--feed path.txt`, or `@filename` at the prompt to slurp a workspace file.

**Slash commands** — available at any prompt:

| Command | Effect |
|---|---|
| `/agents` | list agents, models, and load status |
| `/skills` | list skills and whether each is bound |
| `/pipeline` | show the active step order |
| `/use <name>` | switch pipeline |
| `/reload` | re-parse `agents.md` + `skills/` in place |
| `/last` | reprint the previous run's full transcript |
| `/save <file>` | write last delivery to workspace |
| `/help`, `/exit` | — |

**Streaming.** `client.chat(..., stream=True)`, printed per-token under a live step header. Turns a dead terminal into visible progress.

**Ctrl-C cancels the run, not the process.** Catch `KeyboardInterrupt` inside the step loop, discard the partial run, return to the prompt. Second Ctrl-C at an idle prompt exits.

---

## 7. Failure handling

Three tiers, because they need different responses.

**Startup (fail loud, exit):** Ollama reachable at `127.0.0.1:11434`; every `Model Target` in `agents.md` present in `client.list()` — report *all* missing tags at once with the `ollama pull` line to fix them; every skill bound.

**Per-step (fail soft, stay in the REPL):** wrap each agent call. On exception, honor the agent's `On Fail`:
- `abort` — stop the run, keep the partial transcript (correct for Security Guardian)
- `skip` — pass context through untouched
- `prompt` — ask retry / skip / abort

**Guardian verdict:** parse strictly. `SAFE` → continue. `UNSAFE:` → abort and print the stated reason. **Anything else → treat as unsafe**, because a 1.5b model that fails to follow the format is not a signal you can lean on. Fail closed.

---

## 8. Transcripts

Every run writes `logs/YYYY-MM-DD_HHMMSS_<slug>.md` matching the format already sitting in `logs/`:

- header: timestamp, pipeline name, objective, feed digest
- per step: agent, model, elapsed, full prompt, full output, any tool calls
- footer: final delivery, total wall time

Full prompts included — when a small model behaves strangely the prompt is the evidence, and you can't reconstruct it after the fact.

---

## 9. Model assignment

> **Superseded by §13.4.** Every seat now runs `llama3.2:latest`; only the
> Expert Coder differs (`qwen2.5-coder:1.5b`). The analysis below is kept
> because its reasoning about weak links still holds — the conclusion changed
> when a *thinking* model turned out to be the wrong shape for a front door.

All six tags in `agents.md` exist locally. The problem isn't missing models — it's that a machine holding `qwen3.5:9b`, `qwen2.5:14b`, `qwen3.8:27b` and `gemma4:31b` is running its entire reasoning pipeline on 0.5b–1.5b.

**A chain's output quality is capped by its weakest link, and the weak links are load-bearing here:**

- **Morning Reviewer (0.5b)** runs *first*. Every later stage consumes its compression. A 0.5b model summarizing a noisy feed into two sentences drops and invents detail, and nothing downstream can recover what it discarded.
- **Quality Evaluator (0.5b)** holds *rewrite authority* over the report. A model this size cannot reliably tell a logical gap from correct text it merely failed to parse — it will degrade good output as readily as fix bad output. This is the worst size/authority mismatch in the system.
- **Router (coder:1.5b)** emits the XML that drives the entire skills layer. Every tool call the system makes depends on 1.5b format adherence.

### Hardware reality: Radeon RX 6800 XT, 16 GB

Measured on this machine:

```
NAME                       SIZE      PROCESSOR    CONTEXT
qwen2.5-coder:1.5b-base    4.2 GB    100% GPU     32768
```

**A 986 MB model file is occupying 4.2 GB of VRAM — a ~4× multiplier.** That is not weights. It is KV cache and compute buffers, sized by context length and then multiplied again by the number of parallel sequences Ollama pre-allocates.

This makes **file size useless as a memory budget.** Two consequences:

- `qwen3.8:27b` (17 GB) and `gemma4:31b` (19 GB) **do not fit at all** in 16 GB — before any context allocation. They will spill to CPU and crawl. Treat them as unavailable to this pipeline. Any earlier suggestion of a 27B "escalation tier" was wrong for this hardware.
- Holding three mid-size models resident is not achievable either. The real ceiling is roughly **one 7B plus one small model, with modest context**.

**Two settings recover most of the waste:**

| Setting | Effect |
|---|---|
| `OLLAMA_NUM_PARALLEL=1` | This is a single-user sequential pipeline. The default (often 4) pre-allocates KV cache for 4 concurrent sequences — a silent 4× on every resident model. |
| Per-agent `num_ctx` | 32768 is the dominant cost. A 2-sentence summarizer does not need 32k. Size context per stage. |

### LANDED — aligned to two tags

Measured with `manjuel/vram.py`. Before: `default` paid **6 model loads across
5 tags**. After: 2 tags, 3 loads, ~8.5GB if both stay resident — and `estate`
and `court` collapse to **one model, one load, ~3.6GB**.

The metric that matters is SWITCHES, not model count: a pipeline running
A A B A pays three loads, A A A B pays two. `/models` reports loads against the
floor and names how many are avoidable.

**On running models in parallel:** `OLLAMA_NUM_PARALLEL` does not do that. It
is concurrent request slots *per loaded model*, and each slot allocates its own
KV cache — that is the multiplier behind a 986MB model sitting at 4.2GB. The
var for several models resident is `OLLAMA_MAX_LOADED_MODELS`. And parallelism
cannot help this pipeline regardless: every stage consumes the previous stage's
output, so nothing overlaps. With both tags resident the remaining switch is
free, because neither is evicted.

    OLLAMA_NUM_PARALLEL=1        one request at a time
    OLLAMA_MAX_LOADED_MODELS=3   4b + coder + embedder all stay loaded
    OLLAMA_KEEP_ALIVE=30m        no eviction between runs

### The original argument: one model, many personas

Swapping models between stages is the load-time problem, and it is self-inflicted. **The multi-agent value in this system comes from the prompts and the pipeline structure, not from the weights.** Six personas pointing at the same tag still give six genuinely different behaviors — they just load once.

| Agent | Model | Suggested `num_ctx` |
|---|---|---|
| Security Guardian | `qwen3.5:4b` | 4096 |
| Morning Reviewer | `qwen3.5:4b` | 8192 |
| Router | `qwen3.5:4b` | 8192 |
| Deep Researcher | `qwen3.5:4b` | 8192 |
| Quality Evaluator | `qwen3.5:4b` | 8192 |
| Delivery Agent | `qwen3.5:4b` | 8192 |
| Expert Coder | `qwen2.5-coder:7b` | 8192 |

**One model serves six of seven stages** — loaded once, never swapped, `keep_alive` holding it. The coder is the only genuine second model, and it loads only when the `technical` flag fires, which is exactly what conditional steps are for.

Add `nomic-embed-text` (274 MB, negligible even at 4×) and the steady state is roughly **6–7 GB resident with zero swaps**. That leaves real headroom on a 16 GB card and removes the churn entirely.

Start here and measure. If `qwen3.5:4b` proves too weak at the Evaluator specifically, promoting *that one stage* to `qwen3.5:9b` costs one extra load — a deliberate trade for one stage, not a six-model carousel.

> **Caveat:** I know the `qwen2.5` family well. `qwen3.5`, `qwen3.8` and `gemma4` are tags I can't speak to from benchmarks — the reasoning above is from parameter count and task-shape fit, not measured capability. Worth a head-to-head on one real objective before committing, especially for the Evaluator.

Because §3 puts model choice in `agents.md`, testing any of this is a markdown edit plus `/reload` — no code change. That's much of the argument for building step 2 early.

---

## 10. Build order

**Status as of sitting 1** was: steps 1–4 and 7 landed, 5 partial, 6 not.
The table below is the CURRENT status (all seven landed; see the line after
it). Everything below the line was added after this doc was written.

| # | Step | State |
|---|---|---|
| 1 | Unbreak it | **landed** — `manjuel/` package, `manjuel.py` entrypoint |
| 2 | `registry.py` from `agents.md` | **landed** — now `agents/`, one seat per file; prompts are `role: system` |
| 3 | `RunContext` | **landed** — objective and feed reach the final stage |
| 4 | `skills.py` decorator + binding validation | **landed** — md↔handler drift is a startup refusal |
| 5 | REPL polish | **landed** — multi-line input, slash commands, `/reload`, and streaming now on (`stream=True` from the CLI) |
| 6 | Pipelines in markdown + `when:` | **landed** — order lives in `pipelines.md`; Guardian leads every pipeline with a fail-closed verdict (defect #4 closed); `<flags>` raised by any seat drive `When:` steps, so Expert Coder now runs when code is wanted |
| 7 | Transcripts | **landed** — record + prompts, split |

**Added beyond the original plan:** the semantic index (§11's retrieval idea,
built out), `memory.md` with an operator gate, the estate seats, `.us`
declarations for atlas enrolment, and versioned sittings with `SEAT_LOG.md`.

**All seven steps are landed.** The design's closing claim now holds: the
markdown is the source of truth and Python is only the engine. `agents/` says
who the seats are, `pipelines.md` says what order they run in, `skills/*.md`
says what tools exist — none of the three needs a code change to extend.

Also landed from §4: the router runs a **bounded tool loop** (`MAX_TOOL_STEPS
= 5`; was 4 until sitting 63) rather than a single shot, feeding each result back before deciding
again, capped so a small model cannot spin.

---

## 10b. Sittings, the toll, and version

A **sitting** is one REPL launch: numbered monotonically, recorded in
`sessions/sessions.jsonl` (append-only), and stamped with the git state at open
and close. A session id is therefore a version, not just a timestamp.

Every sitting pays its toll into `SEAT_LOG.md` (LAW 10) — appended below,
never rewritten above. The toll separates what is **observed** (runs, stages,
models, timings, git) from what is **judgment** (what proved, what is thin,
what is owed). Judgment comes from the operator via `/toll`. A sitting that
closes unattended writes the observed half and states plainly that thin and
owed were never stated, rather than inventing them.

**Git is a skill, split by reversibility.** `git_status` reads. `git_init` and
`git_commit` write locally — additive, confined to this ground, recoverable, so
a seat may do it; commits carry the sitting id. `git_pull` and `git_push` reach
a remote and are refused unless `MANJUEL_GIT_REMOTE=1` is set: a push leaves
the machine and cannot be recalled once fetched, which under LAW 6 is the
operator's act. The capability exists and is off by default.

---

## 11. Embedders, and what "multi-level review" should actually mean

Two corrections up front, because they change the shape of the answer.

### Embedders cannot be pipeline stages

`nomic-embed-text`, `nomic-embed-text-v2-moe`, `bge-m3:567m`, `qwen3-embedding:0.6b` and `qwen3-embedding:4b` are **embedding models**. They emit a fixed-length vector, not text. There is no prompt that makes one "review" a draft — it has no generative head. They cannot occupy a stage slot in Manjuel.

### You cannot Manjuel embedders together

This is the part worth being blunt about: **each model's vector space is unrelated to every other model's.** Cosine similarity between a `nomic` vector and a `bge-m3` vector is not a weak signal, it is noise — the dimensions mean different things, and the numbers are not comparable even when the dimensionality happens to match. Feeding one embedder's output into another is not a meaningful operation.

Pick **one** embedder and use it consistently for any given index or comparison. Re-embedding an existing index with a different model means rebuilding it from scratch.

What you *can* legitimately do is **ensemble the scores**: embed a pair with two models independently, compute similarity twice, average the two *similarity numbers*. That's valid because you're averaging comparable scalars, not incompatible vectors. Worth it only if you've measured that one embedder alone is unreliable.

**Suggested pick:** `nomic-embed-text` (274 MB) — small enough to keep resident permanently at negligible cost. Move to `qwen3-embedding:4b` only if retrieval quality measurably disappoints.

**LANDED.** The drift check is live in `manjuel/drift.py`: the source is
embedded once per run, every transform/gate/deliver stage is scored against it
by cosine, and below 0.55 the stage is reported DRIFTED and raises the
`drifted` flag. Advisory — nothing is rewritten on a low score.

> **CORRECTED 2026-09-03, sitting 82 — the paragraph above overstates what
> runs.** It says "once per run" and means it, and the disk does not agree:
> `pipeline.py:907` primes the checker **only when the objective carries a
> pasted feed.** With no feed the source vector is never built, `score()`
> returns `None` at every stage, and the run reports
> *"drift: not scored this run (no usable source)"*.
>
> **In 502 transcripts on disk the drift check has produced ZERO scores.**
> 463 say no usable source, 37 say the output was too short. Not one number.
>
> That gating is DELIBERATE and it is right — the sitting-27 ruling. With no
> feed the checker scored a reply against the words "good job stew", called
> it drifted, and woke the Quality Evaluator to review a compliment. An
> objective alone is a request, not a source.
>
> What is wrong is that neither this section nor the run note says so. The
> note *"no usable source"* reads as a measurement that was attempted and
> came back empty; the truth is it was **never armed**. The operator reasoned
> aloud about automating the toll on the strength of this metric — building
> on a number that has never once existed.
>
> Also dead beside it: `drift.py`'s `_short_source`, `DRIFT_WARN_SHORT`, and
> the comment promising that "a bare-objective comparison is judged against a
> lower bar" describe a path that cannot be reached, because a bare objective
> never primes at all.
>
> Open in TASKS as **THE DRIFT METRIC HAS NEVER PRODUCED A NUMBER**. Kept
> here rather than rewritten above, per LAW 1.

The arithmetic runs on `manjuel/mathkit.py`, a zero-dependency numeric core (cosine,
dispersion with explicit `ddof`, covariance, OLS, small matrix helpers),
checked against Python's `statistics` module. numpy stays optional and is still
used for the index hot path, where pure Python genuinely loses.

### Not a translation layer — an instrument

Close, but the distinction matters. A translation layer sits *between* two stages and content flows *through* it, coming out transformed. An embedder can't do that: the vector is a lossy fingerprint, and there is no path back to text. Nothing can flow through it.

It also isn't needed as a translator, because **text is already the universal interface between models.** Any model's output is directly consumable by any other. There is no impedance mismatch to bridge.

What the embedder does is sit *beside* the pipeline and measure it. Content flows stage to stage as plain text, exactly as now; the embedder is pointed at that text to answer questions like "did this drift from the source?" or "which skill is this objective closest to?" It's a measuring instrument and a card catalog — not a conveyor belt, and not a link in Manjuel.

### Where embedders genuinely belong here

They fix the three weakest points in §9 — as *measurement*, which is exactly what a review system needs and what small generative models are worst at:

| Use | What it does | Which weak link it fixes |
|---|---|---|
| **Drift scoring** | Embed the source feed and the Morning Reviewer's summary; low cosine = the summary invented or dropped material | The 0.5b first stage, whose errors poison everything downstream |
| **Semantic skill routing** | Embed the objective, embed each skill description, rank by similarity | The 1.5b Router's shaky XML tool selection — use as a cross-check, and flag when router and embeddings disagree |
| **Redundancy detection** | Sentence embeddings, flag near-duplicate pairs | The "fluff sentences" the Quality Evaluator is asked to find — deterministic, no model judgment needed |
| **Run retrieval** | Index `logs/` and `agent_workspace/`; retrieve relevant prior runs for a new objective | Nothing yet — this is new capability |

**Run retrieval is the real answer to "make them work cohesively."** It's what turns a set of models that restart cold every run into a system that accumulates. The embedder isn't in Manjuel; it's the memory Manjuel reads from.

Note that drift scoring and redundancy detection produce **numbers**, not prose. That makes them qualitatively better than a small model's opinion: a cosine score can't hallucinate, and you can set a threshold and act on it.

### Serial chains compound error; panels average it

The instinct to add more review stages is right, but the current shape works against it. In a serial Manjuel each stage rewrites the last, so **every stage's error is inherited and amplified** — and a small model's rewrite can destroy correct text as easily as fix broken text. Adding stages to a serial Manjuel makes this worse, not better.

A review *panel* inverts that: several reviewers see the **same** input independently and never see each other's output, so errors are uncorrelated and tend to cancel rather than accumulate.

**Proposed three-tier review**, which is what "load up the VRAM" should buy:

- **Tier 1 — free, always on.** Embedding checks: drift score, redundancy score. Milliseconds, deterministic, no generation. Produces numbers.
- **Tier 2 — panel, parallel.** 2–3 mid-size models (`qwen3.5:4b`, `cogito:8b`, `qwen2.5:14b`) each critique the *same* draft against the *original objective*. They emit **critiques, not rewrites**. Different families is deliberate — correlated architectures make correlated mistakes.
- **Tier 3 — escalation, conditional.** Only when tier 1 crosses a threshold or tier 2 flags something substantive does a stronger model do the actual repair, with the critiques as input.

**Revised for 16 GB:** tier 3 cannot be a 27B/31B model — those do not fit (see §9). The realistic escalation target is `qwen3.5:9b`, and it is a *load-on-demand* step, not a resident one. Because it fires rarely, paying its load cost occasionally is acceptable in a way that swapping models every run is not.

Tier 2 also changes shape on this hardware: running three mid-size models as a true parallel panel would need all three resident. Instead run the panel **sequentially against the same input** — same weights, three different reviewer personas, one load. The property that matters is that reviewers never see each other's output, and that survives sequential execution intact. Only model *diversity* is lost, which is a lesser benefit than independence.

This also keeps the §5 advisory principle intact — critiques accumulate in `RunContext`, and exactly one stage has authority to rewrite. A bad critique gets ignored; a bad rewrite is silently destructive.

### Checking the memory budget

```
nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv
ollama ps          # what is resident right now, and its VRAM footprint
```

`ollama ps` is the more useful one — it shows actual footprint under load, which exceeds file size once context is allocated. Set `keep_alive` explicitly (already wired in `runtime.py`); the default will evict and reload models between stages and dominate your wall time.

---

## 12. Open questions

- ~~**Model tags.**~~ Resolved — all six exist locally. See §9 for the sizing problem that turned up instead.
- **Evaluator authority.** Even at 9b, consider making the Evaluator *advisory* (emit a critique the Delivery Agent reads alongside the report) rather than *authoritative* (rewrite in place). Advisory is strictly safer: a bad critique gets ignored, a bad rewrite is silently destructive.
- **Memory budget.** The §9 recommendation assumes ~15 GB can stay resident. Unknown on this machine — the two-tag variant (~8 GB) is the fallback.
- **`fabrice-verify` / `manjuel-verify`.** Both 397 MB, identical to `qwen2.5:0.5b` — custom Modelfiles on that base. If either is a tuned verification gate, it may belong in the Evaluator slot ahead of a general-purpose model, since a narrow tuned classifier can beat a larger generalist at a fixed-format judgment task.

---

## 13. What sessions 5–13 actually built

Sections 3–12 are the original design. This section is what the build became,
and where the two disagree, this one is right.

### 13.1 The seat rack — `seating.py`

The pipeline listed eight steps and skipped six of them on an ordinary run.
Every transcript was mostly `_skipped_`, and adding a specialist meant editing
`pipelines.md` even though the pipeline had nothing to say about when it should
fire. Models rest on a rack and load on call; skills rest in a folder and bind
on call. Seats were the only one of the three that had to be written into the
running order in advance.

Now the spine holds only what runs every time:

```
## Pipeline: default
1. Steward
2. Router     (when: needs_tool)
3. Steward    (when: worked)
```

and a specialist declares its own summons, in its own file:

```
**Wakes On:** technical
**Wakes:** after Router
```

Adding a seat is one `.md`. `pipelines.md` does not change.

**Why placement is declared rather than inferred.** `has_feed` is set before
any seat runs. If a summoned seat simply appended after whoever raised the
flag, the Security Guardian would be *reviewing* material the Steward had
already read, not *gating* it. `Wakes: first` is what keeps a gate a gate.
Anchors are `first`, `last`, or `after <Seat>`; absent means `last`, so a seat
nobody thought about lands after the work rather than in front of the gate.

**Two triggers, one seat.** The Guardian is a gate on `has_feed` and a review
on `suspicious` — same seat, two moments. So `Wakes On:` takes a list, and
summoning is tracked per `(seat, flag)`: a seat may sit twice for two roles,
never twice on one flag. That is the loop bound.

**Ordering.** Two seats anchored `after Router` inserted backwards, which would
have had the Quality Evaluator judging output the Expert Coder had not written
yet. Insertion skips past seats already summoned behind the same anchor.

Bad anchors are refused at load time with the seat named — not discovered
mid-run.

### 13.2 Voice and spelling — `voice.py`, `spelling.py`

Both optional, both degrade: the CLI starts with none of it installed.

**Speaking** uses whatever the OS already has — SAPI on Windows (built in,
zero VRAM), `say` on macOS, `espeak` on Linux. **Listening** takes either
`faster-whisper` or `openai-whisper`, probed with `find_spec` rather than
imported, because importing whisper drags in torch and costs seconds at
startup. What is heard is confirmed before it runs: a misheard command is
still a command.

> **Spoken text is model output, which is testimony (LAW 5).** It reaches the
> speech engine through a *file*, with the path in an environment variable —
> never interpolated into a shell command, where a seat could close the quoting
> and append a command of its own.

**Spelling is deterministic and conservative.** It only changes words that are
never correct English. Code fences, inline code, `snake_case`, model tags,
paths, URLs and acronyms are untouchable. Unknown words are *reported, never
rewritten* — an unrecognised word is far more often a name than a mistake. It
corrects the **delivery** only; the transcript keeps what each seat actually
said, because the record is not edited.

Grammar is a seat, not a function: `agents/proofreader.md` wakes on `prose`.

### 13.3 Parity — `parity.py`

**Does the machinery earn its keep?** By default the reference is the *same
model the seats run*, called once, bare. So the comparison is the whole Manjuel
— Steward, Router, tools, rack, drift, closing Steward — against just asking
the model. Several calls versus one.

Scoring reuses the embedder already on the rack: same cosine the drift check
performs. Nothing new, nothing billed, nothing leaves the box.

> **The direction of the reading depends on the reference, so the report groups
> by it and never averages across.** Against the seats' own model, HIGH means
> Manjuel changed nothing and was overhead. Against a *larger* local model,
> HIGH means the seats kept up. Same number, opposite conclusions.

And the standing caution, unchanged from drift: a cosine is topical agreement,
**not correctness**. Two answers can agree and both be wrong. A low score means
go and read that pair. An embedding cannot know a fact.

### 13.4 Models — one tag carries the estate

| seat | model | why |
|---|---|---|
| all eleven seats (of 14; the Router, Reasoner and Coder are named below) | `llama3.2:latest` | 2.0 GB, native tool calling, **not a thinking model** |
| Expert Coder | `qwen2.5-coder:1.5b` | 986 MB, wakes only on `technical` |
| embedder | `nomic-embed-text` | index, drift, parity |

`qwen3.5:2b` was dropped despite being the obvious choice. It is a *reasoning*
model: it spent an entire 56-second run inside its `thinking` field and handed
back `content: ""`, and Manjuel delivered a blank screen. `llama3.2` is
smaller (2.0 GB vs 2.7 GB), has native tool calling, and has no thinking field
to lose the answer in.

`runtime._extract` now falls back to `thinking` when content is empty, and an
empty seat reply is recorded as a fault rather than swallowed — the bug is
fixed as well as avoided.

### 13.5 Routing is deterministic before it is generative — `intent.py`

Three consecutive `git commit` runs never reached the Router. It wakes on
`needs_tool`, and that flag was left entirely to a 2b model's willingness to
emit an exact XML string. It refused, then excused, then returned nothing at
all — three failures of one single point.

A request that literally says "git commit" does not need a language model's
permission to reach the git skill. `intent.py` scans the objective against the
skill keywords before any model loads. It only ever **opens the door**: the
Router still chooses, and may still answer in prose instead.

### 13.6 What the record may not be told

Three separate holes, one principle — **testimony is never fact, and must not
be able to shape the record either.**

- A seat emitted `### Deployment Instructions`, at exactly the heading level
  the transcript uses for stages. A seat could have written
  `### 4. Security Guardian` + `SAFE` and fabricated a gate it never passed.
  Recorded text is now demoted below stage level, clamped at `#####`.
- A commit landed 98 files under the subject `git_commit` — the Router echoed
  the skill's own keyword. A degenerate subject is discarded for the objective;
  a lone snake_case token is a tool name *by shape*, checked without depending
  on the skill library being wired in.
- `.env` was skipped by the indexer only because it has no file extension,
  while `.yaml`, `.ini` and `.cfg` *are* indexed. Secrets are now refused by
  **name**, before the suffix check. An embedding cannot be un-published.

### 13.7 The index reads Research, and only Research

`index_roots.txt` now includes `manjuel/` and `tests/`, so Manjuel can read
*how it works* and not merely *how it is configured* — the strokes are the
most precise statement of intended behaviour in the ground.

Archive is reference the operator reads. It is not ground Manjuel indexes,
and a stroke fails if any root ever escapes Research.

### 13.8 Open questions, session 13

- **Does Manjuel beat a bare call?** Unmeasured until `/parity` is run. If it
  does not on ordinary questions, the spine is too long and should shrink
  further.
- **`llama3.2` as Router across 27 skills.** It has echoed the skill keyword
  into `<content>` and emitted malformed `<git_commit>` XML. Guards catch both,
  but a routing model that needs guarding may be the wrong size.
- **The manifest scales with the library.** 27 skills is ~1,327 tokens sent
  twice per tool call. `ROUTING_DESC_CHARS` has already dropped 240 → 170 → 112 (as of 2026-09-04).
  Past ~40 skills the Router needs a shortlist, not the whole library.
- **`logs/` is untracked but indexed.** Right for git, but the semantic index
  will keep growing with run transcripts. It may need an age horizon.

---

## 14. What sittings 14–64 built

§13 was written at session 13 and was authoritative then. This section is
what the build became over the fifty sittings after it, and where the two
disagree, **this one is right.** HANDOFF.md is the live operational record
and moves faster than this file; DESIGN is the record of *intent*, and §14
exists so intent and build do not silently part company.

The three commitments in the preamble have not moved: everything local,
markdown as the source of truth, Python as the engine only. Nothing below
was bought at their expense.

### 14.1 §13.8's open questions, answered

- **Does Manjuel beat a bare call?** Measured. `/parity` puts Manjuel at
  ~0.93 against a bare call to the same model on ordinary questions, 0.82–0.88
  against larger references — "the seats kept up". The spine did not need to
  shrink; the answer was better gates, not fewer stages.
- **`llama3.2` as Router.** Superseded twice. The Router is `qwen3.5:4b`, a
  thinking model with tool capability, and llama3.2 is now named by nothing in
  the ground. The guarding question was real and is answered in 14.5.
- **The manifest scales with the library.** MEASURED, and the shortlist was
  NOT built. Over 476 logs / 119 tool-running turns, `intent.names_a_tool`
  resolves 79% of tool dispatch deterministically, and the 21% residual is
  dominated by turns where the right answer was *no tool at all*. An embedder
  would hand noise a plausible tool. Re-measure before building it.
- ~~**`logs/` age horizon.**~~ BUILT 2026-09-02: transcripts leave retrieval
  at 45 days (`MANJUEL_LOG_HORIZON_DAYS`, 0 disables). Standing documents
  never age out — the doctrine is old by nature. Nothing is deleted, and
  `sitting`/`when` read logs/ directly, outside the index entirely.

### 14.2 The rack is many tags again, and why that is not a reversal

§9 and §13.4 argued the estate down to one tag, then two. It declared
five for a while: `phi4-mini` (the spine and most seats), `qwen3.5:4b`
(Router), `qwen2.5-coder:7b` (Smith, lazy), `qwen3.5:9b` (Reasoner,
background), and `nomic-embed-text-v2-moe` (index, drift, parity).
SUPERSEDED 2026-09-04 (the tiering; §14.11): seven tags seat fourteen
seats -- the door and most of the spine on `llama3.2`, the Router on
`qwen3.5:4b`, `phi4-mini` for the Proofreader and Delivery Agent, the
Reasoner and Deep Researcher on `qwen3.5:9b`, Jesster on `deepseek-r1:8b`,
Manjuel on `gemma4:12b`, the coder on `qwen2.5-coder:7b` -- plus the
embedder. `agents/*.md` is the truth; rack.md is read off Ollama.

A sixth, a compile of the operator's own, sat behind an `@`-addressed
seat. He cleaned the rack on 2026-09-02 and it came off; the seat went with
it, because a seat naming a model the ground does not hold blocks boot at
preflight — preflight working, not a fault to route around. Losing the
weights is a rack decision and reversible by a rebuild; the seat's own
file was the operator's to keep or discard, and he discarded it.

The embedder is worth naming apart: it is referenced by NEITHER `agents/`
nor `skills/`, so preflight cannot check it, and a wrong `EMBED_MODEL` boots
clean and fails later at index, drift and parity. Changing it invalidates
the index — each embedder's vector space is its own (§11), so the old
vectors are not merely stale, they are meaningless against the new ones.
`index ground` rebuilds, which is why the index is disposable by design.

The RULE that produced "one tag" is unchanged and still governs — *always
start small; move up only on measured failure, never in anticipation of it*
(memory.md, OPERATOR). Each of the five is the result of that rule running its
course on a specific seat, not an abandonment of it. **The inventory belongs
to the rack, which prices itself live; it does not belong in a document or in
memory, where it goes stale the moment a seat moves.** `rack_list` is the
answer to "what is loaded", always.

Warm order is an operator ruling and is NOT to be retuned without him: spine
in the foreground at boot, Reasoner on a background thread, coder lazy. One
context size per model -- the largest any of its seats declares: 8192 for
most, Manjuel's gemma4:12b at 16384 since 2026-09-07 (at 8192 the ruling
never got a token). The card is 16GB and effectively full.

### 14.3 The gates: what the engine refuses, arithmetically

The largest architectural change since §13 is that the estate stopped
*asking models to behave* and started *refusing them in Python*. Every gate
below is deterministic, fires before or independently of any model's
judgement, and names itself in the record when it fires.

    gibberish gate      noise never reaches a seat (s22)
    injection gate      hostile feed refused BEFORE the Guardian model (s39)
    LAW 8 path gate     one write-path per Manjuel, checked at execute() on the
                        DECLARED **Path Args:** -- 5 of 26 handlers had been
                        jailing their own paths, and nothing could tell "no
                        path" from "forgot to jail it"
    May Call            per-seat clearance in agents/*.md. ABSENT = NOTHING.
                        Grant by omission from tools=, enforced at dispatch
    SKILL_TIMEOUT       execute() had no timeout at all; bounds the WAIT
    THE CLAIM-CHECK     a seat presenting a file's contents when no reading
                        skill ran this turn is refused (s56)
    THE CITATION-CHECK  a cited path+cosine that is not in this turn's search
                        results is refused; the tool output is the exhaustive
                        list, so this is arithmetic (s61)
    THE DEDUP           an identical (skill, args) is refused, not re-run;
                        told once, then the loop breaks (s63)
    THE SEAM            tool results and the seat's reading of them are split
                        by a named line, so a paraphrase can never read as
                        file content (s63)

The through-line, and the reason they are worth listing together: **fabrication
is not a model problem to be prompted away, it is a boundary to be checked.**
Sitting 58 proved it — the same model that invented a file's contents when no
tool ran reported "not found" correctly the moment a real read happened. The
variable was dispatch, not size. That finding is why the answer to bad output
here is a gate, and why "use a bigger model" keeps losing the argument.

### 14.4 Deterministic dispatch, extended

§13.5 established arithmetic before generation. It has since grown:

- **the alias table** — how a person actually says it ("this place", "the
  repo", "this archive" all mean the ground)
- **write-shapes and action-shapes** — a write is a decision; the Router
  decides the tool, nothing is presumed
- **a reading skill is never dispatched on a write-shaped objective**
  (`REVIEW_ONLY_SKILLS`) — "write a note about the rack" once dispatched
  `rack_list`
- **`asks_the_ground`** — a question carrying a term worth looking up reaches
  a READER. Sitting 60 is why: five substantive questions about the estate's
  own contents raised no flag, ran no tool, and one produced a confident
  invented paragraph about a real client. Invention fills the void that
  non-dispatch leaves.
- **the decomposer** — verb class + object class + remainder, so matching is
  by STRUCTURE, not by pre-carved phrases. "search the ground find the
  warden estate!" dispatched nothing twice before it existed.
- **the balance, an operator ruling**: what matches, executes; everything
  else falls through to conversation. A complaint, a review and an aimless
  verb are talk, and dispatch on noise is worse than dispatch on nothing.

A superseded gate is worth recording: sitting 48 added a `needs_tool`
set-aside that discarded flags on short objectives. It ate CORRECT flags and
was dropped by operator ruling on 2026-09-01 — its evidence was the same
lookup that routes, so it could only ever confirm its own misses.

### 14.5 THE LAW, and the client shield

Two subsystems exist that §13 never imagined.

**THE LAW** (`law/`, `foundation/foundation/05_THE_LAW.md`) is the estate's
constitution as a hash-chained ledger — `law/law.py verify` walks the chain
and refuses a lying byte. Ten laws are cited across the engine; the ones with
mechanism today are fold-never-delete (1), originals read-only (2), testimony
is never fact (5), the gate is final (6), bounded everything (7), one
write-path (8), keys are silent (9), honest logs (10).

**The client shield** (`vectors.py`, `watch.py`, the readers) enforces the
operator's ruling that client data is never indexed, never cross-referenced,
never listed. Three tags, any one of which seals a file: a `vault/` path
part, a `.client.` name, or a `[[CLIENT]]` token in the first 2KB. It is
proven live — sitting 61 ran a real search for a client name against 3,601
chunks and returned nothing from the sealed world. `index_roots.txt` is the
first line of that defence and the shield is the second; a sealed world is
named in neither and is indexed by nothing.

A term-level shield (filtering a client's NAME from every chunk estate-wide)
was proposed and DECLINED on evidence: the only echoes of the name in the
record are the estate's own refusals, not contents.

### 14.6 The record grew a spine

`SEAT_LOG.md` holds the toll of every sitting, appended and never rewritten,
including a `(re-tolled)` marker when a second toll supersedes a first — the
earlier entry stands (LAW 1). `logs/` keeps the transcript and, apart from
it, the exact prompt every seat saw. `sessions/thread.jsonl` is the CURRENT
sitting only and is overwritten by design; history lives in `logs/`.
`tests/last_run.json` is stamped by the suites themselves and read back by
the boot report, which says what was proved, when, and **STALE** if the
ground changed since — because no count belongs in a document when the
suites grow with the system.

### 14.7 Where the value actually accumulated

Worth stating plainly, because it is the architectural finding of these fifty
sittings: **almost nothing that improved this system was model work.** The
fixes were dispatch structure, refusal arithmetic, boundary marking and
record-keeping. The models became increasingly interchangeable tenants of a
harness that does the guaranteeing.

That is the thesis proving out — the estate is an exterior layer any local
model can be loaded into, not a wrapper around one clever model — and it has
a practical consequence: the seats can shrink, or swap to whatever comes
next, and the guarantees survive.

### 14.8 Time, and why the estate could not reason about it

Everything was stamped -- transcripts, memory, the ledger, every search hit
carrying "written 2h ago" -- and the stamps did almost nothing, because
three pieces were missing.

**No seat knew the date.** Not one prompt carried it. A model handed an age
with no present moment falls back on its training-data sense of now, which
is how sitting 26 narrated a two-hour-old transcript as news; the fix then
was a warning sentence in the search results, a patch over a missing clock.
`now_block()` is now appended to every seat's prompt, stamped from the RUN's
start so a later stage cannot believe it is further into the future than the
first. It lives in `context.py` because the skill library needs it too --
prompt skills run outside the pipeline, and `time_align` had been written
promising to find what is OVERDUE while forbidden to know today's date.

**Nothing read the stamps as a range.** `when` answers a period from the
transcript filenames -- arithmetic over the folder, no model, no index. It
pairs with `sitting`, and the pairing is the point: **the timestamp is the
atom, the sitting is the molecule.** A period is a stretch of clock; a
sitting is a unit of work the operator declared by opening the REPL, and no
amount of timestamp arithmetic can infer where he decided one began.

**Retrieval displayed age and ranked without it.** `RECENCY_WEIGHT` is 0.04,
decaying to nothing over a month: enough to break a tie between comparably
relevant passages, never enough to outvote meaning. Recency AS relevance is
the mistake `context.py`'s dialogue selector was built to escape, so this is
a thumb on the scale rather than a second opinion. The doctrine is exempt --
the founding documents are old by nature, and decaying them would bury the
ground's own law under whatever ran this morning.

### 14.9 Context does not Manjuel by summary

The operator asked whether Manjuel could "expand" context from model to
model. It cannot widen a window. It can widen the MATERIAL COVERED, and
only one of the two ways of trying works:

    REDUCE   stage 2 reads stage 1's summary. Feels like more context and
             is less: every hop is lossy and errors compound. This is
             section 1's issue 7 and section 11's warning, and it is the
             thing this estate was rebuilt to stop doing.
    MAP      stage 2 reads DIFFERENT material at full fidelity. Total
             covered = one window x number of passes, with no compression
             loss inside a pass. The only honest expansion.

Three things landed in that light, and each is map-shaped:

**A big file is a movable window, not a stump.** The wall was never the 8192
context -- it was `text[:12000]`, so `SEAT_LOG.md` arrived as its first 9%
and the seat did not feel the rest. `windowed()` returns part N of M with
the file's own headings mapped, and a seat can ask for the next part or for
a section BY NAME. The tool grammar stayed at three tags: one tag means the
whole file, two mean file plus part, and no fourth tag was invented for the
parser to drop.

**A multi-act objective gets a route first.** `decompose_task` existed as a
skill and was never dispatched. Now sequencing language plus two act-verbs
sends the objective to it, and the Router works the acts one at a time --
each with its own full window. The gate errs SHUT: a decomposition that
fires on one act spends a model call restating the request, and every
unnecessary stage is another chance to drift.

**A review can send work back, once.** The Evaluator could say a draft was
WRONG (and hand back a correction) but never that it was UNFINISHED, so a
critique naming missing work had nowhere to go. `NEEDS: <thing>` sends one
more pass through the Router with the critique and the real prior results in
front of it -- evidence carried forward, never a summary -- bounded by the
same (seat, flag) arithmetic that stops a flag looping. When the pass is
spent, the gap is NAMED to the operator rather than quietly filled.

### 14.10 The AST as an instrument — uses 1 and 3 BUILT 2026-09-03, use 2 not

    THE LANDING GATE IS BUILT: `pipeline.inspect_code()`, called by
    `land_code` before the write, stroked both ways in
    test_the_landing_gate_parses_before_it_writes. What follows is the
    reasoning that produced it, kept because it still governs — and
    because uses 2 and 3 below are still only argued for.


The estate reads code as TEXT everywhere it looks at itself: the strokes
that check every `write_text` carries `newline=`, that every handler
resolving a path declares it, that every test function is registered. All
three are structural questions answered with substring matching, which is
why an anchor phrase wrapping across a line break broke the same stroke
twice on 2026-09-02. Python's `ast` answers them exactly and does not care
where the lines end. One stroke already does this: it parses `smoke_cli.py`
to compare a fixture's signature WITHOUT importing it.

Three uses, in the order they earn their keep:

**1. The landing gate.** `land_code` writes whatever the Expert Coder
emitted. A file that does not parse lands anyway and the Quality Evaluator
then reviews it as prose. `ast.parse()` is a model-free refusal — and once
the tree is walked, **RULE 4 stops being a request and becomes a proof**: a
landed file that imports `requests`, `urllib`, `socket` or `http`, or calls
`eval`, `exec`, `__import__`, or `subprocess` with `shell=True`, is refused
because the structure says so, not because a prompt asked nicely. That is
this estate's whole thesis — arithmetic over character — applied to the
code it writes about itself.

**2. Structural strokes.** Replace the regex source-greps with `ast.walk`.
The guards do not change; only their brittleness does.

**3. Semantic slicing. BUILT 2026-09-03.** `windowed()` cuts a big file by character range —
part 3 of 7. For a `.py` file the right slice is a FUNCTION. Asking for
`manjuel/skills.py:_commit_subject` and getting exactly that definition is
a better window than a character offset that lands mid-expression.

**Not on the list: complexity metrics.** Nobody has asked what the
cyclomatic complexity of `pipeline.py` is, and a number nobody acts on is
drift with a decimal point.

**The honest limit:** this is Python-only. Fine for a ground that writes
nothing else — but the moment the coder emits something that is not
Python, the gate must fail OPEN and say so rather than pretending to have
checked.

**As built, 2026-09-03.** It fails open exactly as argued above: a
non-`.py` name lands with `coder file <n> landed UNINSPECTED -- not
checked: <n> is not Python` in the record. Two limits were found in the
building and are in the docstring, not here, so they travel with the
code: `shell=True` is flagged on ANY call rather than resolving the
callee through imports and aliases — over-refusing on a write gate is
recoverable and under-refusing is not — and `importlib` is an uncaught
route to a module, named as a hole rather than left to be discovered.

### 14.11 Open, sitting 64 (and what session 2 closed, 2026-09-03)

**CLOSED SINCE THIS SECTION WAS WRITTEN.** The AST landing gate (14.10 use
1) is built, `importlib` with it. The manifest is reconciled and checked.
The estate can report its own standing (`proved`). The Router can be watched
while it thinks. Ten guards that each asked one question too few now ask
one more -- see HANDOFF's fix log, session 2.

**STILL OPEN, and it is the shape this section should carry forward:** a
PARTIAL read spoken as a whole one. `windowed()` says "part 1 of 7 -- THIS
IS NOT THE WHOLE FILE"; the claim-check asks only whether A read ran. Not
the fourth narrow gate -- a different fact, coverage rather than existence.



- **The Router is the single chokepoint.** Every tool decision routes through
  one 4b thinking seat, and its two worst failures (published deliberation,
  the lifted citation) both came from it. Gated on both sides now, but it is
  the one place a single model's quality still sets a ceiling.
- **The closing seat, and a SIXTH shape that is not a fabrication.**
  Sitting 77 run 3: the Steward delivered the PREVIOUS turn's answer -- run
  2's todo-list reply against a /skills objective -- with the correct
  objective in its prompt and the Router's on-topic text directly above it.
  A STALE answer, not an invention. The guards held (the recompose named
  the failed tool); nothing catches an answer that is true about the wrong
  question. A near-duplicate-of-previous-delivery check is cheap and
  arithmetic and is DECLINED under the no-fourth-narrow-gate ruling: this
  belongs in the tally as evidence about the seat, not in the engine as a
  fifth detector.
- **The closing seat.** Five fabrication strikes stand, but the case has
  weakened twice: s58 showed honest reporting once tools engaged, and the
  claim-check now refuses the shape at the gate. Re-measure against the guards
  before spending VRAM.
- **The toll is hand-typed**, so it mostly goes unpaid. A friction item, and
  deliberately not a seat.
- **`logs/` age horizon — BUILT 2026-09-02** (`LOG_HORIZON_DAYS = 45` in vectors.py; transcripts leave retrieval, nothing is deleted).
- **The 11 never-run skills** are now stroked at execute level, but eleven
  skills no sitting has ever called is still a question about the library,
  not about the tests. `remember` firing for the first time in sitting 63 is
  what surfaced the dedup bug.
- **The decomposition threshold is untuned.** Two act-verbs plus sequencing
  language. If it fires on things that felt like one request, the dial is
  `is_big_objective(..., verbs=3)` -- and the evidence for turning it is
  transcripts, not taste.
- **The Router prompt sits at its ceiling.** ~1800 tokens, and the clock
  block put it one token over before being trimmed. The next thing added to
  every prompt will need `ROUTING_DESC_CHARS` to come down, or the manifest
  to be shortlisted -- which was MEASURED unnecessary and should be
  re-measured before it is built.
- **Prompt skills and seats are two classes of model call.** Both now get
  the clock, but only seats get the method, the dialogue and the manifest.
  Nothing is wrong with that; it is simply not written down anywhere but
  here.

---

### 14.12 THE UNCHECKED WHY — the estate's own recurring fault

*Named 2026-09-03, sitting 82, after four of five findings in one review
turned out to be the same thing wearing four costumes.*

This estate's whole claim is **LAW 5: testimony is never fact.** Every
guard in it exists to stop a seat asserting something the record has not
proved. Sitting 82 found the engine doing it *to itself*, in four places,
none of them a model:

| where | it said | the fact |
|---|---|---|
| `skills.py:2266` | `'rack_report' changes things` | it writes nothing, and is in no writing list |
| `pipeline.py:1425` | `drift: not scored (no usable source)` | the check was never armed; nothing was looked at |
| `skills.py:1665` | `~0.0GB headroom` | the card was 0.5GB **over** |
| `us.py` *(fixed same day)* | `no rack was reachable` | nobody had asked the rack |

**The shape, stated once.** A guard refuses, a check skips, or a report
clamps — correctly — and then explains itself with the *most likely*
reason rather than the *established* one. The action is right every time.
The sentence beside it is invented. And an invented sentence in a REPORT
is worse than one in a seat's prose, because a report is what everything
downstream — the next seat, the next agent, the operator — is entitled to
treat as fact.

**Why it recurs.** The reason is written at the moment the guard is
authored, when the author knows *why they are adding it*. The reason is
then emitted at runtime in every case the guard fires, including the cases
the author never had in mind. `rack_report` was refused by a rule written
about writers. Drift skipped by a rule written about empty feeds. Neither
message was ever wrong when it was written.

**The rule this argues for**, and it is cheap:

> A message may state the CONDITION THAT WAS TESTED. It may not state a
> cause the code did not evaluate on this path.
>
> `'rack_report' is not cleared for the table` — true, tested, sufficient.
> `'rack_report' changes things` — a second claim, never checked.

**And it argues against a habit.** `us.py`'s version of this was fixed on
the morning of 2026-09-03; `skills.py`'s version refused a skill with the
same lie that afternoon. The fix was applied to a **site**. The fault is a
**shape**. That is the whole argument for sweeping the four together
rather than closing them one at a time as bugs.

**Not a stroke, yet.** A grep for reason-giving strings is the obvious
next thought and it is the wrong one — it would flag every honest message
in the engine. What is arithmetic here: a refusal that names a *set*
(`WRITING_SKILLS`, `REVIEW_ONLY_SKILLS`) can be stroked by asking whether
the named key is actually in the set it is accused of. That is three of
the four. The fourth (drift) is a two-state note, not a set.

### 14.13 THE LAW GATE — every run through the law (built 2026-09-04)

*The operator's ruling, the same morning he wrote RULE 0 for the hands:
"every single call, no matter what, runs through the law." Built as a
GATE, not a prompt line, because the estate already knew what a prompt
line is worth (sitting 46: instructions in a prompt are parrot food) and
what a gate is worth (§14.5, the shield; §14.10, the AST).*

`manjuel/lawgate.py`, first in `run_pipeline`. Four acts: Manjuel is
walked with the pen and every sealed law's fingerprint checked (a tampered
law refuses every run -- LAW 4's rule for a red suite, applied to the law
itself); the objective is checked against the laws a regex can decide
(reach, secret, wall, client tag); every seat is handed a `## The law`
block as fact, beside the clock; the record is stamped. REFUSALS §19.

What the first live run showed (sitting 86, the standup): both law
refusals fired at 0.0s with no seat sat; every other run carried the stamp.
AND: the door on llama3.2 answered "what does the covenant say?" by
reciting laws off the `## The law` block in its own prompt as if it had
read them -- the block is a fact handed to a seat, and a seat that quotes
the furniture is the sitting-46 fault in a new room. The block names four
laws by number; the seat produced nine. The claim-check cannot see it (no
file named). Open in TASKS: the block should say LESS to the door, or the
door should be told the block is not source material.

### 14.14 THE CLAUDE.md SYSTEM, for the seats (built 2026-09-07)

*The operator, the Monday after: "make sure we are looking at how the
claude.md works and implementing that system into Manjuel." CLAUDE.md
works on the hand by five mechanisms; four of them had no counterpart for
the seats, and the record of sittings 86–87 showed each absence.*

**Rules as system text, not as the operator's message (RULE 0).** The
`## The law` block rode in the USER prompt and four seats recited it as
content. CLAUDE.md reaches the hand as system text. So: `carried_blocks`
puts the law beside the seat's own system prompt (`dataclasses.replace`
for the call; the registry is never written); a BAKED seat keeps the user-
prompt shape. The court -- the seats that rule -- is handed the ten estate
laws verbatim (`lawgate.laws_text`, read from the sealed file); the door
and the Router the short form. Forty runs since: no recital.

**Intent across the amnesia (READ FIRST).** DAYBOOK's last entry is "the
only file that carries intent" for the hand; the seats had nothing. THE
STANDING (`seatlog.standing_block`): that entry's intent lines, bounded,
built once at sitting open, handed to the door and the court. Not the
Router. The brief (`boot.brief_facts`, `/brief`) is the same idea at the
sitting's start, read off the record and said by the door.

**A grep is not a read (SITTING LAW 1).** THE PARTIAL-READ STAMP: every
windowed read is recorded as it happens; the delivery ends READ IN PART,
NOT WHOLE unless every part was read.

**Room to think, bounded (LAW 7).** Manjuel on gemma4:12b at Context 8192
thought 13–15k characters and never ruled; at 16384 it ruled on turn 1 in
five courts. THE RULING LOOP stands behind it: a seat that returns the
salvage line is asked again with its own deliberation, thinking off, at
most three times; the Router is never looped.

**And the one the operator found by losing four standups to it.** The
engine had named the tool and checked the argument on disk, and a 4B
Router overrode it every time. THE DECIDED CALL: when the tool and its
argument are both decided by arithmetic, the engine writes the call and
the Router only reads the result. §14.12's fault from the other side --
not a seat asserting a why it never checked, but a seat overriding a why
the engine had.

**What this section does not claim.** The sitting story -- what THIS
sitting has done, handed back to the seats -- is not built; sitting 93
measured its absence. Guidance lands memory ("remember that" at the
door, a kind on every entry); no seat writes it. The learning loop is
that, and it is the next thing, after the brief runs clean twice.
