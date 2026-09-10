# Runbook

The machine misbehaving, not a seat misbehaving. For a seat that said
something wrong, read `logs/` — HANDOFF.md's *Debugging a sitting* is that
procedure, and it starts with **check the disk before the transcript**: a
seat's account of what it did is testimony (LAW 5); the file is the fact.

Run everything below from `Desktop\Research`.

**The morning, in one command.** `python tests\standup.py` runs the seats
through nine fixed objectives on the live rack, opens and tolls a sitting,
and writes `logs\standup_<stamp>.md`. About ninety seconds, and it runs
unattended. Read REVIEW THESE FIRST, then the deliveries; write what feels
off in TASKS.md.

    --court    the court alone: six seats, deepseek-r1 and gemma4, minutes.
               Out of the morning set on his ruling 2026-09-09 -- it was 73%
               of the run, and the only case that could not finish without a
               terminal (a failed seat there asks `retry / skip / abort?`).
    --all      both sets.
    --only <name>   the cases whose name contains it, the court included --
                    naming one is asking for it.
    --dry      the harness on a stub, no models.

Only a run of the WHOLE morning set is written to the record as suite
"standup"; anything less is "court" or "partial", so a one-case run cannot
satisfy the release gate. Where to look for anything it names: BUILDMAP.md.

---

## Manjuel will not start

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

    python tests/test_manjuel.py

---

## Git will not commit

**`Unable to create '.git/index.lock': File exists`**

An interrupted `add` or `init` left a lock behind. Git never cleans these up.
Manjuel names it with its age and the exact removal command rather than
inventing a cure (that fix is from sitting 6). A lock older than two minutes
with no git process behind it is stale, not contended:

    del .git\index.lock

**Never run git writes from a sandboxed agent's shell.** A mount can create
files it cannot unlink, so a failed commit leaves exactly this lock behind and
blocks yours. Commits are the operator's act anyway (RULE 6).

**`remote operations are off`** on pull or push — that is not a fault. Remote
git is gated behind `MANJUEL_GIT_REMOTE=1`; a push cannot be recalled once
fetched, so it is yours to make, not a seat's.

**`git rev-parse timed out` from the headless door, on a ground that is
plainly a repository.** Fixed 2026-09-09; if it ever returns, this is why.
`subprocess.run()` with no `stdin` hands the child the PARENT's stdin. In the
REPL that is a console and harmless. Under `manjuel.py --headless` it is the
pipe `serve.Inbox` has a thread permanently blocked reading, and git never
returns — every call dies on its timeout, and `git_commit`/`git_push` then
refuse with "this ground is not a git repository" about a repository. Every
git call in `gitstate.py` now passes `stdin=DEVNULL`; two strokes hold it
there. Measured: 0.12s with no such thread, 5.02s with one, 0.02s with the
fix.

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

       python tests/test_manjuel.py && python tests/smoke_cli.py

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
gemma4:12b 700) or the ceiling `MANJUEL_SEAT_TIMEOUT` (700); ONE TURN may take at most
`MANJUEL_TURN_DEADLINE` (600) -- a seat whose turn comes after that is
not seated and is NAMED in the delivery, and a seat seated just before it
is cut to what is left. Both are dials, neither is a fault: the seat that
hung is the fault, and its name is in the record. Raise the dial only for
a run that legitimately needs it (a parity sweep is many runs, each with
its own deadline; it needs nothing raised).

---

## The dials, in one place

Every `MANJUEL_*` the code reads, with its default. Set in `.env` (the
boot report says which took effect) or the shell. Nothing else is a dial.

    MANJUEL_SEAT_TIMEOUT    700    the most one seat call may take (runtime.py)
    MANJUEL_TURN_DEADLINE   600    the most one turn may take (pipeline.py)
    MANJUEL_SKILL_TIMEOUT   300    the most one skill call is waited for (skills.py)
    MANJUEL_GIT_REMOTE      off    1 allows pull/push/rack_pull (gitstate.py)
    MANJUEL_RACK_PULL       off    1 allows `ollama pull` from a seat (skills.py)
    MANJUEL_KEEP_ALIVE      30m    how long Ollama holds a model after a call (runtime.py)
    MANJUEL_NO_WARM         off    1 skips warming the spine at boot (cli.py)
    MANJUEL_VRAM_GB         card   the budget the VRAM plan reasons against (vram.py)
    MANJUEL_LOG_HORIZON_DAYS 45    transcripts older than this leave retrieval; 0 = never (vectors.py)
    MANJUEL_NO_COLOR        off    1 turns the ink off (ink.py)
    MANJUEL_WHISPER_MODEL / _DIR / _CLI / _GGML   where speech-in looks (voice.py)

`MANJUEL_OLLAMA_HOST` is named in dotenv.py's docstring and READ NOWHERE
-- the runtime binds 127.0.0.1:11434 (runtime.py). Setting it does
nothing; TASKS (the review of 2026-09-08) carries it.

---

## The hands ledger is gone (2026-09-09)

refusal over an open hand were removed at the operator's word: "we didnt
have it 3 days ago". It cost a ritual at both ends of every stretch of work
and bought a line nobody read.

The file itself STAYS on disk, unwritten -- LAW 1, nothing in the record is
deleted. `law/SITTING_LAWS_2.md` still carries SITTING LAW 6, whose second
half tells a hand to open a line that no longer exists; striking it is the
operator's act, not a hand's.

---

## Before a tag: the release gate

    python tests\release.py --check 0.1.8

One command, run ON YOUR TERMINAL before every tag, that refuses by name:
the suites green and stamped after the newest edit; buildmap clean; the
standup run LIVE and green after the newest edit; the law proves; the
manifest agrees with the disk; every SPEC section-4 line whose status
changed since the last tag has an Unreleased CHANGELOG line naming it;
DAYBOOK's last entry closed; a HANDOFF block for today; It reads; it never writes. A REFUSED line is the
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
