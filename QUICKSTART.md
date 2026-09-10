# Quickstart

This is the first hour with the REPL. If what you want is the DASHBOARD --
building and starting the two atlas servers, the four-click loop, the skills
and the tools -- that is RUNBOOK.md, "Starting the system".

## You need

- **Ollama** running locally (`ollama serve`; usually already a service).
- **Models for the seats you will use — YOURS TO CHOOSE, not a shopping list.**
  Nothing here requires a particular model. Every seat names its own tag in
  `agents/*.md`, and you may point them wherever you like: seven different
  models, or ONE small model in all seven slots. Boot refuses only when a seat
  names a tag you do not have, and it says which.

  So the floor is **one pull per DISTINCT tag named in `agents/*.md`, plus an
  embedder** — three or four gigabytes if you point the seats at one small
  model, thirty-three if you copy the set below verbatim.

  **THE SHAPE IS WHAT MATTERS; THE TAGS ARE JUST HIS.** What the roster is
  really asking for is a size per JOB, and you fill the slots:

      the door        SMALL and fast. It greets, and it closes the turn. It is
                      spoken to on every single run, so latency here is the
                      whole feel of the thing.
      the router      A STEP UP, and it must think. This is the seat that reads
                      the shortlist and decides which tool runs; a model too
                      small stalls mid-deliberation and calls nothing.
      a coder         Whatever you actually code in. Slotted, not required --
                      drop the seat and the requirement goes with it.
      an overwatch    The long thinker that rules, refutes or reviews. It never
                      sits at the door, so it may be slow.
      the embedder    Small, and the ONE tag you cannot improvise: change it
                      and every vector already built means nothing.

  Add seats, remove them, point three of them at the same tag. The set below is
  the AUTHOR'S, tuned on his own machine over weeks, and it is an illustration
  of that shape rather than a bill of materials:

      ollama pull llama3.2                 # the Steward (front door), Neiro, Guardian, Morning Reviewer, Quartermaster
      ollama pull qwen3.5:4b               # the Router (thinking, tools), Quality Evaluator
      ollama pull phi4-mini                # Proofreader, Delivery Agent
      ollama pull qwen3.5:9b               # Reasoner, Deep Researcher
      ollama pull deepseek-r1:8b           # Jesster (the licensed fool)
      ollama pull gemma4:12b               # Manjuel -- the court's ruling seat (thinks long; never at the door)
      ollama pull qwen2.5-coder:7b         # the Expert Coder
      ollama pull nomic-embed-text-v2-moe  # index, drift, parity

  Parity references, optional: `gemma4:e4b`, `qwen2.5-coder:14b`, `qwen3-vl:8b`.
  **What each seat declares in `agents/*.md` is the truth; this list is not.**
  Change a seat's `Model Target:` and the requirement changes with it.

  **`OLLAMA_MODELS`** decides where the weights land. Unset, Ollama uses its
  default under your user profile. The author points it at another disk; if you
  do too, set it before pulling or the files go somewhere you did not mean.

  Boot refuses to start if a seat or skill names a tag you do not have, and
  says which. **The embedder is the exception**: nothing in `agents/` or
  `skills/` names it, so a wrong `EMBED_MODEL` boots clean and fails later
  at `index ground`. Changing it invalidates the index — rebuild with
  `index ground`, since each embedder's vectors mean nothing to another's.
- **Python 3.10+**. One dependency, and it is the only one:

      pip install .            # from a clone -- brings `ollama` with it

  That puts a `manjuel` command on PATH. `python manjuel.py` from the clone
  still works and is what the record's examples use.
- For voice only: `pip install sounddevice numpy`. Transcription looks for a
  compiled **whisper.cpp** binary with a `ggml-*.bin` beside it, and falls back
  to **faster-whisper** from a local HuggingFace cache.

  **NEITHER IS IN A CLONE.** `bin/` is gitignored — 144 MB of binaries and
  weights is not source and does not go in the record — and the HuggingFace
  cache lives in your user profile, not here. This file used to say the build
  was "already there, nothing to download", which was true only on the machine
  that built it. On a fresh clone, speaking works (Windows SAPI) and LISTENING
  does not until you supply one of the two. The boot report's VOICE line names
  which one it found, or says so plainly.

## What a fresh clone does NOT have, and why the first boot looks alarming

Everything below is deliberate. The record is untracked (his ruling
2026-09-08) and the binaries are not source, so a clone carries the CODE and
the DOCTRINE and nothing that was earned on someone else's machine.

    bin/              the whisper build. Listening is off until you supply one.
    index/            empty. `index ground` builds it; nothing works by meaning
                      until it does.
    logs/             no transcripts. Yours start at your first turn.
    sessions/         no sittings. Your first boot is sitting 1.
    agent_workspace/  made on demand.
    .env              copy `.env.example`. Remote git stays OFF without it.

**Your first boot will show a RED GATE, and that is correct.** It reads
something like `gate 3/6 -- REFUSED: strokes, smoke, standup`. Nothing is
broken: the gate refuses to call a thing proven that YOU have not proven. Run
them and it goes quiet:

    python tests/test_manjuel.py     the strokes
    python tests/smoke_cli.py        the REPL
    python tests/standup.py          the live set (needs the rack)

**The first brief you see is the AUTHOR'S, not yours.** DAYBOOK, HANDOFF and
TASKS are tracked — they are the intent of the work, and losing them would
leave a stranger with code and no reason for any of it. So your first sitting
opens with his last session, his open tasks, and a version note that predates
your clone. Read it as history. It becomes yours as you write into it.

**A suite tally may ship with the clone too.** `tests/last_run.json` is
tracked, so the boot report can quote numbers earned on the author's machine
and then mark them STALE against your files. Treat any tally you did not run
as hearsay — the estate's own rule is that a proof older than the code is not
a proof.

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
