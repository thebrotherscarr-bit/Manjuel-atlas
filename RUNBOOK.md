# Runbook

The machine misbehaving, not a seat misbehaving. For a seat that said
something wrong, read `logs/` — HANDOFF.md's *Debugging a sitting* is that
procedure, and it starts with **check the disk before the transcript**: a
seat's account of what it did is testimony (LAW 5); the file is the fact.

Run everything below from `Desktop\Research`.

**The morning, in one command.** `python tests\standup.py` runs the seats
through ten fixed objectives on the live rack, opens and tolls a sitting,
and writes `logs\standup_<stamp>.md`. Read REVIEW THESE FIRST, then the
deliveries; write what feels off in TASKS.md. `--only <name>` runs one
case; `--dry` runs the harness on a stub with no models. Where to look
for anything it names: BUILDMAP.md.

---

## The chain will not start

**`RACK UNREACHABLE — the ground is open, the models are not.`**

Ollama is not running. The ground opened anyway on purpose: the record, the
palette, git state and the ground's own skills do not need models.

    ollama serve

It reconnects on the next turn — no restart needed. Ollama is *the* server
here (operator ruling, sitting 33); there is no fallback by design.

**`Missing model tags referenced by agents/ or skills/`**

A seat or skill declares a tag that is not installed. The boot report names
each one with its own pull command. Either pull it, or point that seat at a
tag you have — `agents/*.md`, one line, then `/reload`.

**Something else, at import.** Run the strokes: they need no model and no
network, and a parse error or a bad seat file shows up there in a second.

    python tests/test_chainkit.py

---

## Git will not commit

**`Unable to create '.git/index.lock': File exists`**

An interrupted `add` or `init` left a lock behind. Git never cleans these up.
The chain names it with its age and the exact removal command rather than
inventing a cure (that fix is from sitting 6). A lock older than two minutes
with no git process behind it is stale, not contended:

    del .git\index.lock

**Never run git writes from a sandboxed agent's shell.** A mount can create
files it cannot unlink, so a failed commit leaves exactly this lock behind and
blocks yours. Commits are the operator's act anyway (RULE 6).

**`remote operations are off`** on pull or push — that is not a fault. Remote
git is gated behind `CHAINKIT_GIT_REMOTE=1`; a push cannot be recalled once
fetched, so it is yours to make, not a seat's.

---

## The card is full / everything is slow

    run the rack          in the REPL — prices VRAM live, model by model

The card is 16GB and the resident set normally sits near the ceiling. Waking a
cold seat (the coder, or a world's agent) costs an eviction and the reload
that follows. That is the budget working, not a fault — but it explains a
sudden 7-second pause on the first code question of a sitting.

**Warm order is an operator ruling and is not to be retuned casually:** the
spine warms in the foreground at boot, the Reasoner on a background thread,
the coder stays lazy. One context size per model -- the largest any of its
seats declares (8192 for most; Manjuel's gemma4:12b runs at 16384 since
2026-09-07, because at 8192 the ruling never got a token).

To free VRAM deliberately:

    rack_unload <tag>     refuses a model this ground does not declare —
                          evicting someone else's model charges THEM the
                          reload, and that is not a cost a seat may spend

If a boot feels much slower than usual, check nothing else is holding the
card: `rack_list` marks models this ground never declared.

---

## The index is empty, stale, or missing something

    index ground          in the REPL — sweeps and reindexes

The boot report prints `index  N docs / M passages`. Empty means it has never
been built here; stale counts mean files changed since.

**A file you expect to be searchable is not.** In order of likelihood: it is
outside `index_roots.txt`; it is a suffix the indexer skips; it is refused as
a secret **by name** (see REFUSALS §6); or it is sealed client data (three
tags, REFUSALS §5). The last two are refusals working correctly and are not to
be "fixed".

**`index/.fuse_hidden*` files.** Corpses left by a mount when a file was
deleted while open. Harmless, hidden from Explorer, safe to remove — the index
is rebuildable by design:

    del /A index\.fuse_hidden*

**`Refused: an index build is still running behind an earlier call`.** A
build refused at the 300s skill bound keeps working (Python cannot kill
the thread); a second `index ground` while it runs would write the same
`vectors.db` -- sitting 94's `UNIQUE constraint failed: docs.path`. Wait,
or restart the REPL to end the first. **`rebuild refused: vectors.db is
held open`** is the same fact from the other side: nothing was discarded,
nothing was written.

**Removing a root from `index_roots.txt` (the prune note).** On the next
`index ground`, docs whose root is no longer declared are EVICTED from the
index. If that would evict more than 25% of the corpus (`ORPHAN_CEILING` in
vectors.py) the prune REFUSES and says so; run `index ground rebuild` to start
clean instead. Nothing on disk is touched either way — only the index.

---

## Voice does nothing

Everything voice degrades rather than crashes, so silence is the symptom.

- **No transcription:** whisper.cpp lives in `bin/`. Nothing is downloaded at
  runtime, ever (RULE 4) — if the build is missing, put it back; do not let
  anything fetch it.
- **No sound out:** SAPI voices are per-seat (`Voice:` in `agents/*.md`,
  matched as a substring). A name that matches nothing falls back silently.
- **It talks over you / will not stop:** any keypress cuts speech off. Long
  deliveries are capped and say so.

---

## A stroke is red

**Don't scroll the output.** Both suites write `tests/last_run.md`: each
suite's standing, then every failure with its detail, and nothing about the
ones that passed. That file is the whole conversation — open it, or hand it
over as-is.

Then read the failing line — it names what broke, in its own words. Then:

1. **Is it a real regression, or a superseded ruling?** A stroke that a new
   rule invalidates is evidence the rule bites. House discipline: **rewrite
   the stroke, note why, keep the guard** — never relax it. Several have moved
   that way (the traversal stroke, the Router's token cap, the tool-loop cap,
   the client-world fixtures).
2. **Fix at the cheapest layer that holds:** alias/gate in `intent.py` >
   skill output wording > prompt > model size. Model size is last and is the
   operator's call.
3. **Run both suites.** The smoke suite sat RED for days once while the
   strokes stayed green, because a fixture had not moved with the code:

       python tests/test_chainkit.py && python tests/smoke_cli.py

---

## Auditing the record itself

    python tests/audit_record.py       reads logs/, SEAT_LOG, sessions, memory

Not a test suite and it never gates anything — the corpus grows every
sitting, so a red over it would mean *you ran the CLI*, not that code broke.
It reports: malformed transcripts, dangling references, orphan prompt files,
unstamped memory, anything sealed that is not protected, and — the useful
part — every run in the record whose shape a gate now refuses (a delivery
claiming all-clear over a failed tool, a file's contents claimed with no
read, a citation the search never returned). Findings land in
`tests/last_audit.md` with their paths.

Run it after a stretch of sittings, or when you want to know whether a
guard you just built would have caught anything historically.

## A seat, or a turn, ran out of time

    [Jesster] seat call ran past the 600s bound (611s) and the run has
    stopped waiting for it ...
    OUT OF TIME. 2 seats did not sit this run because the turn's 600s
    deadline had passed: ...

Two bounds, both the operator's (2026-09-08): ONE CALL to a seat may take
at most its own `Timeout:` (agents/*.md, by the model's size -- his
words: steward-sized 150-300, router-sized up to 600, the biggest 700:
llama3.2 150, phi4-mini 300, qwen3.5:4b 300, the 7-9b seats 600,
gemma4:12b 700) or the ceiling `CHAINKIT_SEAT_TIMEOUT` (700); ONE TURN may take at most
`CHAINKIT_TURN_DEADLINE` (600) -- a seat whose turn comes after that is
not seated and is NAMED in the delivery, and a seat seated just before it
is cut to what is left. Both are dials, neither is a fault: the seat that
hung is the fault, and its name is in the record. Raise the dial only for
a run that legitimately needs it (a parity sweep is many runs, each with
its own deadline; it needs nothing raised).

---

## The dials, in one place

Every `CHAINKIT_*` the code reads, with its default. Set in `.env` (the
boot report says which took effect) or the shell. Nothing else is a dial.

    CHAINKIT_SEAT_TIMEOUT    700    the most one seat call may take (runtime.py)
    CHAINKIT_TURN_DEADLINE   600    the most one turn may take (pipeline.py)
    CHAINKIT_SKILL_TIMEOUT   300    the most one skill call is waited for (skills.py)
    CHAINKIT_GIT_REMOTE      off    1 allows pull/push/rack_pull (gitstate.py)
    CHAINKIT_RACK_PULL       off    1 allows `ollama pull` from a seat (skills.py)
    CHAINKIT_KEEP_ALIVE      30m    how long Ollama holds a model after a call (runtime.py)
    CHAINKIT_NO_WARM         off    1 skips warming the spine at boot (cli.py)
    CHAINKIT_VRAM_GB         card   the budget the VRAM plan reasons against (vram.py)
    CHAINKIT_LOG_HORIZON_DAYS 45    transcripts older than this leave retrieval; 0 = never (vectors.py)
    CHAINKIT_NO_COLOR        off    1 turns the ink off (ink.py)
    CHAINKIT_WHISPER_MODEL / _DIR / _CLI / _GGML   where speech-in looks (voice.py)

`CHAINKIT_OLLAMA_HOST` is named in dotenv.py's docstring and READ NOWHERE
-- the runtime binds 127.0.0.1:11434 (runtime.py). Setting it does
nothing; TASKS (the review of 2026-09-08) carries it.

---

## A hand's session: open it, close it

    python -m chainkit.seatlog hand-open  --hand claude --note "what for"
    python -m chainkit.seatlog hand-close --edited a.py,b.md --strokes 1825/1825 --restart
    python -m chainkit.seatlog hand-close                  # no --edited: see below
    python -m chainkit.seatlog hands

The first act of any hand in this ground, before a command: read CLAUDE.md
and the sitting laws, then `hand-open` -- it writes their fingerprints AS
READ, HEAD, the DAYBOOK entry and HANDOFF block it found, and the newest
sitting, to `sessions/hands.jsonl`. The last act: `hand-close`, with what
was edited and what the mirror proved. The brief shows the last hand beside
the last sitting; `!! OPEN since` means a hand never closed and its work
is unrecorded. The release gate refuses a tag over an open hand.

**A close with no `--edited` no longer records nothing** (0.1.6+, 2026-09-09).
It reads the ground's mtimes since the open — no git, so no `.git/index.lock`
is ever left — and stamps `edited_by: observed`. A named `--edited` stamps
`named` and always wins. mtimes cannot see WHO changed a file, so a file you
edited while a hand was open lands in the hand's line: that is a deliberate
over-report you can discount, chosen over a silent empty list. Derived trees
(`logs/`, `sessions/`, `index/`, `worlds/`, `bin/`, the suites' own stamps)
are never attributed to a hand.

**"what happened?" at the door.** The door holds THE SITTING STORY -- every
run of this sitting so far, off the ledger -- and answers from it, naming
the run; no search is dispatched. Older runs past the window are folded
into a count; `/find` or `semantic_search` reaches their transcripts.

---

## The record: what gets written down, and by whom

*Ruled 2026-09-09: "atlas needs to first and foremost document and record
everything. do not make changes without reviewing all the docs and make sure
every step taken is recorded in the logs ... keep everything on record and
usable by the next agent/operator."*

The next hand begins with **total amnesia**. Everything below exists so that
what was decided, what was built, and what was believed at the time can be
rebuilt from files alone. Testimony is never fact (LAW 5); the disk is.

### The loop, every time

```
  1  READ   CLAUDE.md, every file in law/, DAYBOOK last entry,
            HANDOFF newest block, CHANGELOG Unreleased, TASKS open, SPEC
  2  OPEN   hand-open  -- no command comes before it (SITTING LAW 6)
  3  SUM    say what the disk says. "Nothing to build" is a legal answer
            |
            +-- he named no piece --> answer in words, write no file (RULE 5b)
            |
  4  ASK    is a sitting open? then ask, and wait (RULE 9)
  5  BUILD  the piece he named. Mirror-prove it. Keep the terminators
  6  WRITE  one CHANGELOG entry: what, why, who asked. Plus the doc lines
            the piece changed. "restart required" in the same sentence
            if chainkit/ moved
  7  CLOSE  hand-close --edited ... --strokes ... [--restart].  STOP
```

### Who owns which line

| the line | who writes it | who owns it |
|---|---|---|
| `sessions/hands.jsonl` | the hand, at open and close | the operator |
| `sessions/sessions.jsonl` | the engine, per sitting and run | the engine |
| `SEAT_LOG.md` — observed half | the engine | the engine |
| `SEAT_LOG.md` — proved / thin / owed | **the operator, never generated** | the operator |
| `logs/` + `logs/_prompts/` | the engine, per run | the engine |
| `CHANGELOG.md` | the hand, one entry per edit | the operator |
| `DAYBOOK.md` | the hand at his word — the only file carrying INTENT | the operator |
| `HANDOFF.md` | the hand — the day's state and open findings | the operator |
| `TASKS.md` | **the operator only.** A hand does not mine work into it | the operator |
| an ADR (`SPEC_CONTROL_CENTER.md`) | the hand, whenever a choice is made or reversed | the operator |
| a tag | **the operator**, after the release gate passes | the operator |

### A decision is not a chat message

A choice made in conversation and not written down did not happen. It goes
into the governing document as an ADR — status, date, decider, the options,
and *why* — and **the rejected option's text is kept and folded, never
deleted** (LAW 1). `SPEC_CONTROL_CENTER.md` §11 (ADR-001) is the pattern: the
withdrawn stone's wording is still there at P1-6, struck, because it was the
plan of record for a day and the record should show what was believed.

### What is still missing, named so nobody assumes otherwise

- **atlas has no enforcement.** It keeps `SEAT_LOG.md` and
  `STATE_OF_BUILD.md` by charter, but has no release gate, no record audit
  and no hands ledger — and its record has already failed: `THE_ROAD.md`'s
  B1 row reads "16/19 tools real" while its code carries 62, and the N1–N6
  stones are on no road at all. The check worth porting first is
  **road-versus-code**: it would have caught that drift the day it happened.
- **No cross-ground reconciliation.** Two SEAT_LOGs, two CHANGELOGs, two
  HANDOFFs, nothing joining them — which is how `ATLAS_PRODUCT_PLAN.md` came
  to be written against a stale reading of atlas's own code. Once atlas
  lands in Research (ADR-001, and his ruling that the product lands here),
  one index covers both records and this stops being a manual step.

### Exceptions

| situation | what to do |
|---|---|
| A sitting is open and he says "go" | Write — and **record in the CHANGELOG that a hand wrote against an open line**, and why |
| Reading would cross into `Archive` or a world | Ask, for that act, every time (RULES 1–3). Name the yes in the entry |
| A doc line contradicts the disk | The disk wins. Fix the line in the same pass. Never edit the disk to match a doc |
| The record itself is wrong | Append a correction. Never rewrite (LAW 1). The SEAT_LOG gaps and `(re-tolled)` stand as record |
| Nothing was decided or built | Say so and close. An empty entry beats an invented one — the toll's own principle |
| A hand is interrupted | Its line stays open; the release gate refuses a tag over it; close it by `--id` |

### Whether it is working

| measure | target | where to look |
|---|---|---|
| hand sessions closed | 100% | `hands.jsonl` — no line without `closed` |
| closes that say what they did | 100% | `hands.jsonl` — `edited_by` on every close |
| edits carrying a CHANGELOG entry | 100% | the release gate already refuses otherwise |
| road rows matching code | 100% | chain passes today; **atlas fails** |
| faults found by reading transcripts afterwards | 0 | `SPEC.md` §7.2 |

---
## Before a tag: the release gate

    python tests\release.py --check v0.1.5

One command, run ON YOUR TERMINAL before every tag, that refuses by name:
the suites green and stamped after the newest edit; buildmap clean; the
standup run LIVE and green after the newest edit; the law proves; the
manifest agrees with the disk; every SPEC section-4 line whose status
changed since the last tag has an Unreleased CHANGELOG line naming it;
DAYBOOK's last entry closed; a HANDOFF block for today; the hands ledger
closed (from 0.1.6). It reads; it never writes. A REFUSED line is the
thing to do next, not a thing to argue with. PASSED means the tag may be
cut -- by you (RULE 6).

---

## The boot report says STALE

    proved   NNN/NNN strokes, NN/NN smoke   3h ago   ** STALE: the ground
                                                        changed since **

The suites last ran *before* the current code. The number is honest about the
past and says nothing about now. Re-run them. This is the report doing its
job, not an error.

`not run here yet` means no run has ever stamped `tests/last_run.json` on this
machine — the same instruction applies.

---

## A world will not answer

Worlds are addressed directly (`@name`) and are private by design: a direct
address is a closed-door visit, recorded in the transcript, never fed into the
conversation other seats read. If a world's seat has no `Wakes On:` line, it
will *never* be summoned by a flag — that is deliberate, not a fault.

Client data inside a world is sealed and stays sealed (REFUSALS §5). An empty
search result over sealed material is the correct answer, not a bug.
