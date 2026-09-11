# Manjuel

A local multi-agent CLI. One REPL, a rack of seats that rest until called,
markdown as the source of truth, and a git-versioned ground. Everything runs
on this machine: no cloud service, no API key, no download at runtime. Unplug
the router and it still works — that property is the point.

    python manjuel.py

## Install

    pip install .          # one dependency: ollama

Puts `manjuel` on PATH. `python manjuel.py` from a clone works too.
Full prerequisites -- Ollama and the model pulls, seven since the rack
was tiered -- are in QUICKSTART.md.

Windows-first: voice (SAPI out, whisper.cpp in) is Windows-bound and
DEGRADES ALONE -- boot reports GROUND / RACK / RECORD / GATE / VOICE
separately, so a machine without it boots, says so, and runs everything
else. The suites never need it.

The suites are offline and stubbed: no rack, no network, no GPU, no
model. `python tests/test_manjuel.py && python tests/smoke_cli.py`
runs anywhere, and CI runs them (with the law's prover, the build map's
check and the standup's dry run) on Windows and Ubuntu on every push.
`python tests/standup.py` is the live one: the seats through nine fixed
objectives on your rack in about ninety seconds, a report to read. The
court -- six seats, the big models, minutes -- is `--court`, on its own.

## The dashboard

There is a control plane: `atlas`. Two processes -- an MCP door serving 72
tools on `:8090`, and a web app on `:8091` -- and the browser is where the
whole loop lives: boot an engine, type an objective, watch the seats run,
commit and push through the council, close the sitting. Nothing opens a
sitting behind you, and every act goes through the law gate rather than
around it. **RUNBOOK.md, "Starting the system", is how to build and start
both** -- every command in it was run before it was written.

## What a turn looks like

Type, or speak (`/chat`). Before any model sees it, arithmetic decides: is
this language at all, does it name a tool ("git status", "who is manjuel"),
is it an *order* to search the ground, a question carrying a term worth
looking up, several acts in one sentence, or just talk. What matches is
dispatched; everything else falls through to conversation. Then the spine
runs:

    Steward  →  Router (when a tool is needed)  →  Steward

Two to four stages for an ordinary exchange. Specialists rest on the rack and
are summoned by flag: paste untrusted material and the Security Guardian
gates it *first*; ask for code and the Expert Coder wakes, its file landed on
disk by the harness and reviewed; raise something genuinely hard and the
Reasoner (a 9b) takes the knot. A review that finds the work *unfinished*
rather than wrong can send it back through the tools once, carrying the
evidence. The conversation carries across turns, typed and voice sharing one
thread.

Each seat is told the date and hour, so "written 2h ago" means something. A
file too big for any window arrives as part 1 of N with its own headings
mapped, and the seat can ask for the part it needs — because chaining cannot
widen a window, only cover more ground with each one.

## The rules the build enforces

- **Testimony is never fact.** Seat output cannot forge the record, the
  closer may only report work it can point to, search results declare their
  age and tense.
- **Facts are read, not generated.** Where am I, what can you do, what is on
  the card — answered by the harness from ground truth, never by a model.
- **Keys are silent.** `.env` is never printed, indexed, or passed on a
  command line. Secret-shaped files are refused by name.
- **The gate is final.** Manjuel prepares commits, memory entries and
  spends; the operator lands them.
- **The ground is this folder.** Nothing reaches outside `Research`, and a
  test fails if anything tries.
- **A claim needs something behind it.** A seat that presents a file's
  contents with no read, or cites a search result the search never
  returned, is refused at the gate and the fault is named in the record.
- **Client data is sealed.** A `vault/` path, a `.client.` name or a
  `[[CLIENT]]` token — any one of the three, and the file is refused by
  the index, the watcher, every reader and every listing.

## The ground

    agents/        one seat per file: model, clearances, wake condition, prompt
    skills/        one tool per file: keyword, description, params
    pipelines.md   the running orders
    manjuel/      the engine (28 modules — see BUILDPATH.md)
    tests/         the strokes and the smoke suite — offline, seconds; both
                   print their own count, which is why none is written here.
                   They also write `tests/last_run.md`: the failures, with
                   their detail, and nothing about the ones that passed
    logs/          every run transcribed; prompts kept apart
    memory.md      rulings that outlive a session (operator-landed)
    SEAT_LOG.md    the sittings and their tolls
    law/           THE LAW as a hash-chained ledger (`python law/law.py verify`)
    SPEC.md        what this IS and when it is DONE, line by line; the words
    TASKS.md       what the record owes, by the sitting that found it
    BUILDMAP.md    where to look -- generated from the code (tests/buildmap.py)
    worlds/        the estate's worlds; client data never indexed, never read

Extending it is writing markdown: a new seat is one file in `agents/`, a new
tool one file in `skills/`, a new pipeline a block in `pipelines.md`. The
engine changes for none of these.

## At the prompt

`/help` prints the palette. The commands, so none is only in the code
(the REPL read of 2026-09-08 found eleven that no doc named):

    talking     /chat  /say  /new  /resume  /paste  /table <q>  @<seat> <words>
    the record  /last  /remember  /memory  /git  /toll  /sittings  /brief
    the ground  /status  /index  /find <q>  /parity   (`inspect <name>` is a skill, typed as words)
    the rack    /models  /model <tag>|reset  /warm  /rack
    plumbing    /agents  /skills  /pipeline  /pipelines  /use <name>  /reload  /listen  /exit

`/model <tag>` runs every seat on one model for the sitting -- a
measurement, not a configuration; `rack.md` keeps the declared models.
`/table` seats the counsel on a question and Manjuel rules; `@<seat>`
opens one seat alone, its own voice, the shared thread. Typing "remember
that" at the door lands a memory; "pay the toll" pays it.

`python manjuel.py --headless` opens the same sitting over stdin/stdout as
JSON lines (`manjuel/serve.py`): one `objective` per line in -- anything
the prompt takes -- and the turn out as events (seat, token, tool,
needs_answer, delivery). Every question the REPL would ask at the keyboard
comes back as `needs_answer` and waits for an `answer`; nothing is
decided for you. No socket: a front end runs the process and speaks on
its pipes. The control center (SPEC_CONTROL_CENTER.md) is built on it.

`python manjuel.py --ground worlds\NAME` (with or without `--headless`) sits
the engine inside a world: that folder's own `agents/`, `skills/`,
`pipelines.md`, `law/`, `sessions/` and `logs/`. A sitting opened there is
that world's, and this ground's record gains nothing. A path that is not a
directory is refused, never created.

The thirty-nine skills are `skills/*.md`; `/skills` lists them and
`skill_report` (ask "what can you do") reads them off the disk. The ones
no earlier doc named: `deep_research`, `ground_report`, `skill_report`,
`skill_search`, `list_directory`, `write_file`, `linear_regression`,
`subtask` (a scoped sub-run: depth 1, three per turn, the Router alone).

## Documents

- `QUICKSTART.md` — running in five minutes
- `DAYBOOK.md`    — the session book: what each working session was FOR,
  where it drifted, and the rulings it produced. The check sequence lives
  at the top of it.
- `REFUSALS.md`   — every gate: what it refuses, and the failure that earned it
- `TESTING.md`    — the tiers, how to run them, and the discipline
- `parity.md`     — what Manjuel is measured against, and how to read a score
- `RUNBOOK.md`    — when the machine misbehaves: rack down, locks, VRAM, voice
- `BUILDPATH.md`  — every module, what it owns, and the order it was built
- `DESIGN.md`     — the architecture record, including what was tried and superseded
- `HANDOFF.md`    — the live operational record: patterns, fix log, rulings
- `CLAUDE.md`     — standing rules for any agent working in this ground
- `LICENSE`       — MIT

Built session by session, with every observed failure pinned by a test
before it was called fixed.
