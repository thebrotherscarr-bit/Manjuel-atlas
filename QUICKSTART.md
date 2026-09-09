# Quickstart

## You need

- **Ollama** running locally (`ollama serve`; usually already a service).
- Eight pulls: seven seat models and the embedder (the rack is TIERED since 2026-09-04; a seat naming
  a tag that is not installed blocks boot at preflight, on purpose):

      ollama pull llama3.2                 # the Steward (front door), Neiro, Guardian, Morning Reviewer, Quartermaster
      ollama pull qwen3.5:4b               # the Router (thinking, tools), Quality Evaluator
      ollama pull phi4-mini                # Proofreader, Delivery Agent
      ollama pull qwen3.5:9b               # Reasoner, Deep Researcher
      ollama pull deepseek-r1:8b           # Jesster (the licensed fool)
      ollama pull gemma4:12b               # Manjuel -- the court's ruling seat (thinks long; never at the door)
      ollama pull qwen2.5-coder:7b         # the Expert Coder
      ollama pull nomic-embed-text-v2-moe  # index, drift, parity

  Parity references, optional: `gemma4:e4b`, `qwen2.5-coder:14b`, `qwen3-vl:8b`. What each seat declares is in `agents/*.md` — that is the
  truth, not this list.

  Boot refuses to start if a seat or skill names a tag you do not have, and
  says which. **The embedder is the exception**: nothing in `agents/` or
  `skills/` names it, so a wrong `EMBED_MODEL` boots clean and fails later
  at `index ground`. Changing it invalidates the index — rebuild with
  `index ground`, since each embedder's vectors mean nothing to another's.
- **Python 3.10+**. One dependency, and it is the only one:

      pip install .            # from a clone -- brings `ollama` with it

  That puts a `manjuel` command on PATH. `python manjuel.py` from the clone
  still works and is what the record's examples use.
- For voice only: `pip install sounddevice numpy`. Transcription uses the
  whisper.cpp build in `bin/` — already there, nothing to download.

## Run

    cd Desktop\Research
    python manjuel.py
    python manjuel.py --headless     # the same sitting as JSON lines on stdin/stdout
    python manjuel.py --ground worlds\NAME   # either, sitting inside a world (its own record)

Boot prints the report: GROUND, RACK (with real sizes and what is warm),
RECORD, GATE, VOICE. If a needed model is missing it says which and stops.

## First five minutes

    what can you do            → the skill table, read from the harness
    what is in this repo       → the ground, live from disk
    git status                 → routed deterministically, no model guessing
    what ran yesterday         → the record for a period, from the stamps
    review sitting 47          → a sitting number resolved to its runs
    /chat                      → talk; it answers aloud; any key cuts it off
    /help                      → everything else, grouped

A period and a sitting are different questions: `when` reads a stretch of
clock, `sitting` reads a unit of work you declared by opening the REPL.

Paste material with `/paste` (the Guardian gates it before any seat reads
it). Land a ruling with `/remember`, or just say `remember that` -- the last
proposal or the last answer is shown back, you give it a kind, one y. Drop
outside files in `agent_workspace/` and say `inspect <name>` before anything
reads them. `/brief` says where the build is and what you said we are on.
Pay the sitting's toll with `/toll`.

## The two tests

    python tests/test_manjuel.py    # the strokes; no model needed
    python tests/smoke_cli.py        # drives the REPL end to end

Each prints its own tally when it finishes. That tally is the only honest
one — the suites grow with the system, so no count is written into a doc.

Both offline, both finish in seconds. Run them after any edit to agents/,
skills/ or manjuel/. Red blocks; the failing stroke names what broke.

## Extending

- **New seat:** one file in `agents/` — model, `Wakes On:` flag, `Wakes:`
  anchor, prompt. `/reload`.
- **New tool:** one file in `skills/` — keyword, description, params. A
  `Model Target:` line makes it a prompt skill needing no Python; otherwise
  bind a handler in `manjuel/skills.py`. Startup refuses a manifest that
  advertises what cannot execute. A skill can also declare how it is
  reached and what it takes, so neither has to be carved into the engine:

      - **Says:** index, reindex, run the index
      - **Takes:** rebuild | from scratch -> content
- **New pipeline:** a block in `pipelines.md`. `/use <name>`.
- **New command:** a block in `commands.md` — `**Runs:**` is the objective
  (with `$ARGS` where what you type after the command belongs), and an
  optional `**Method:**` line makes everything after it a procedure that
  rides with the run and is shown to every seat. `/reload`.

## When the machine misbehaves

`RUNBOOK.md` — the rack unreachable, a stuck git lock, a full card, a stale
index, voice gone quiet, a red stroke. `REFUSALS.md` explains anything the
estate refused on purpose, and why.

## When a seat misbehaves

Every run is transcribed in `logs/` with per-stage timings, prompts kept
apart in `logs/_prompts/`. Read the transcript before blaming a seat — the
record outranks any model's account of itself, including Manjuel's own.
