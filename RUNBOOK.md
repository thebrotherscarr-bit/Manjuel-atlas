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

## Starting the system

Two processes and a browser. Neither starts by itself, and nothing opens a
sitting behind you.

**You need Go for this half.** The engine wants only Python and Ollama; these
two servers are Go, built from source. QUICKSTART's "You need" is the ENGINE's
list and does not name a Go toolchain, because nothing in the REPL wants one.
If `go version` answers, you are ready.

**And atlas is its own repository.** Since 2026-09-10 the core and atlas are
two repos sharing one ground (`atlas/` is gitignored by the core). Cloning the
core does NOT bring the dashboard: without atlas there is nothing here to
build, which is what a second machine finds first.

**So clone it, INTO the ground, at exactly `atlas`.** Every build path below
and the core's own `.gitignore` assume that name and that place.

    cd <YOUR-GROUND>
    git clone https://github.com/thebrotherscarr-bit/Atlas.git atlas

The core itself is `https://github.com/thebrotherscarr-bit/Manjuel.git`. Both
are public. Until 2026-09-11 this page told you atlas was a separate repo and
then gave no URL for it — a stop sign with nothing past it, which is the first
thing a second machine hits.

**Offline?** Make the bundle at transfer time, never ship a stale one:

    git bundle create atlas.bundle main          # run inside atlas/
    git clone atlas.bundle atlas                 # on the other machine

Use `main`, not `--all`. `--all` carries every local branch, and a local
branch can hold material that was deliberately kept off the remote.

**Build the Rust spine first.** `verify_chain` shells a Rust binary, and the
Go halves cannot prove themselves without it — `atlas/tests/prove.py` reports
every leg that needs it ABSENT, naming `cargo build -p atlas` as the command
that would answer. ABSENT is never a pass: those legs proved nothing.

Until 2026-09-11 this page said those legs went RED, and one of them really
did: `check_trade_parity` refused with a COMMAND rather than a missing path,
which prove.py's absence check did not recognise, so a fresh clone's first
battery reported a break on a tree where nothing was wrong. Both are fixed.

    cd atlas
    cargo build -p atlas        # -> atlas\target\debug\atlas.exe

Nothing needs to be told where it is: the door walks out from its own
location to find `target\{debug,release}\atlas.exe`. `--atlas-bin` and
`ATLAS_BIN` still override, and both win over the walk.

**Build them once.** Both binaries are `*.exe`, which `.gitignore` already
covers, so they live beside their own source and never reach a commit.

    cd atlas\line
    go build -o atlas-mcp.exe .\cmd\atlas-mcp
    cd ..\webapp
    go build -o atlas-webapp.exe .

Rebuild after any Go change. The webapp EMBEDS its own HTML, CSS and
JavaScript (`go:embed`), so a change to a page is not live until you rebuild
and restart it -- editing the file on disk does nothing to a running server.

**Start the door.** `atlas-mcp` is the MCP door: it serves the 78 tools and it
is the only thing that spawns a Manjuel engine. It holds `127.0.0.1:8090`.

    cd atlas\line
    .\atlas-mcp.exe --http 127.0.0.1:8090 --tenant research=<PATH-TO-YOUR-GROUND> --default-project research --manjuel "python <PATH-TO-YOUR-GROUND>/manjuel.py" *> mcp.log

`<PATH-TO-YOUR-GROUND>` is the folder holding `manjuel.py` -- an ABSOLUTE
path, forward slashes, no trailing slash. This line carried the author's own
`C:/Users/novad/Desktop/Research` twice until 2026-09-10: it worked on exactly
one machine and pointed at nothing on any other.

`--tenant name=path` declares a world; repeat it for more. `--default-project`
is the one the dashboard uses when you do not name another. `--manjuel` is the
command the door runs to raise an engine -- `--headless` and `--ground` are
appended by the door itself, so do not add them.

**Start the glass.** `atlas-webapp` serves the dashboard on `:8091` and talks
to the door at `127.0.0.1:8090`.

    cd atlas\webapp
    .\atlas-webapp.exe *> web.log

    ATLAS_WEB_PORT=<n>   serve on another port
    OLLAMA_HOST=<url>    if the rack is not on the default loopback

**Open it.** `http://127.0.0.1:8091`

**Stop them.** They are servers; they run until stopped. Nothing is lost --
the engine already exits with every sitting, and both processes keep no state
of their own.

    Get-Process atlas-mcp,atlas-webapp | Stop-Process

## Running it from the dashboard

The pages, in the order the panel lists them:

    Dashboard   the launchpad. THE ENGINE card is first because nothing below
                it runs until one is open. Then the box you type in, the
                brief (silent when there is nothing to say), and THE
                REPOSITORY with its Commit and Push buttons. It repaints
                itself every 15s and says so when what it shows is stale.
    Chat        the same conversation, kept. The composer is disabled with
                the reason written under it when no engine is open.
    Agents      the fourteen seats as they declare themselves in agents/.
    Evals       the last run whole -- every seat, tool, result, timing --
                and evals scored by hand.
    Records     the estate's own memory: the suite and standup proof cards,
                the sittings, and 141 documents in seven kinds (doctrine,
                record, spec, agents, commands, skills, logs), each opening
                whole with a sha256 receipt.
    Settings    the dials.

**The loop, four clicks.**

    1. Boot            opens an engine AND a sitting. Nothing opens one for
                       you; a sitting nobody meant to start is what every
                       refusal in this system guards against.
    2. type and Run    the turn runs on the Dashboard, the answer lands under
                       the box, and the whole trace goes to Evals.
    3. Commit / Push   type the message in THE REPOSITORY's field first. Both
                       go THROUGH THE COUNCIL, not around it: the law gate
                       stamps the act, the Router runs `git_commit`, and the
                       commit body carries the sitting id. A button that
                       shelled out to git would be a second write-path past
                       everything the estate checks.
    4. Close sitting   pays the toll, writes `ended`, and reaps the engine.
                       DO THIS. A sitting left open is what makes the next
                       Boot refuse.

**Or the whole turn in one act.** `git_cycle` is step 3's commit and push as a
single skill, with the proofs read first and the push verified after. Type it
on the Dashboard the way you would any objective, and give it the message --
that is the one part it cannot read off the ground:

    git_cycle: "what this commit is"

It does five things and reports what each one said:

    THE PROOFS            the six file-readable checks the boot report asks,
                          of which ONLY TWO GATE A COMMIT: strokes and smoke,
                          green AND fresh. A red or STALE one there REFUSES THE
                          SHIP by name and nothing is committed. The other four
                          -- standup, SPEC vs CHANGELOG, DAYBOOK, HANDOFF --
                          are read and PRINTED but do not stop a commit: a
                          commit does not cut a tag, close a session or end a
                          day, and it must never need a live rack. They are the
                          TAG's to answer; `python tests/release.py --check`
                          still wants all nine.
                          It does not RUN the suites -- spawning python inside
                          the engine is measured unsafe here -- it reads the
                          verdict they already left, which is why a proof older
                          than the code is refused.
    THE GROUND            what is about to be committed. Clean tree, no commit.
    THE COMMIT            the hash, or a refusal.
    THE PUSH              git's own output.
    THE PROOF IT LANDED   the local head and the remote head, side by side.
                          A push exiting 0 is not proof the remote moved; on
                          2026-09-10 one reported success while origin sat a
                          commit behind. These two lines are what closed that.

It refuses rather than guesses: no message, a red proof, nothing to commit, the
wall shut, not a repository -- each names itself and stops. Nothing half-runs.

**Before you start, and before you tag.** Two read-only reports answer the two
questions that used to mean opening six files in order. Neither writes
anything, and neither is a skill — they are run directly:

    python -m manjuel.doctrine            where the estate stands
    python -m manjuel.doctrine --check    the doctrine check

`doc_pass` — the STATE of the record: which DAYBOOK entry is newest and whether
it was closed, whether there is a HANDOFF for today, how many CHANGELOG entries
stand under Unreleased, how many TASKS lines are still on the table, the
repository (head, dirty, local against remote, version), and whether the proofs
are green. It reads TASKS.md and NEVER writes it — a hand does not add work to
your list.

`doctrine_check` — whether the docs still describe what the system performs
(LAW 6): the law chain and any law drafted but unsealed; whether the skill
library agrees with the handlers behind it; whether every file holding the
version says the same number; any suite tally left standing in a living doc;
any backticked path that resolves to nothing. Every finding names its file and
line.

**WHY THEY ARE NOT SKILLS.** They were, for about an hour on 2026-09-10, and
the cost landed on the ROUTER'S SHORTLIST. Both describe the record, and this
estate's commonest question is about the record — so they outranked the right
answer on every doc question, and `semantic_search` stopped being offered at
all. A standup case green all morning went to no tool at 09:59: the Router
burned its whole thinking budget weighing them. Arithmetic that calls no model
and makes no judgement has no business in a roster the Router reads on every
turn. The operator named it: "you have too many knobs."

Both are arithmetic. Dated ledgers (HANDOFF, SEAT_LOG, DAYBOOK, CHANGELOG,
TASKS, REFUSALS, memory, BUILDMAP) are skipped on purpose — a number in a
ledger is a true record of its day, not a claim about now.

Push is disabled unless the wall is open (`MANJUEL_GIT_REMOTE` in `.env`) and
there is something to push; hover it and it says which.

## Running it from the terminal instead

    python manjuel.py            the REPL -- the same engine, no glass
    python manjuel.py --version  what version this is
    python manjuel.py --help     the argument contract

The REPL opens its own sitting and prints the boot report: GROUND (seats,
skills, pipelines), RACK (what Ollama holds and what is warm), RECORD (index,
memory, transcripts, what the suites last proved), GATE (git, whether remote
operations are permitted, and the release gate's verdict) and VOICE. Every
block degrades on its own -- if the rack is unreachable that block says so and
the rest still prints.

**One engine per world.** The dashboard and the REPL both open a sitting on
`research`, so they refuse each other by design. Close one before opening the
other.

## The skills and the tools

Two different things, and it is worth keeping them apart.

**Skills** are what a SEAT can do -- 40 of them, declared as markdown in
`skills\`, hot-reloaded into a running session at the next turn. A seat asks
for one by keyword and the engine runs it; the law gate can refuse it, and a
refusal names the law. Read them on Records -> skills, or `commands.md` for
what can be asked for in words.

**Tools** are what ATLAS serves over MCP -- 78 of them, listed at
`http://127.0.0.1:8090/tools` and reachable from the glass through
`POST /api/tools/call`. They are read-only unless their declaration says
`Writes: true`. The ones the dashboard itself leans on:

    git       branch, head, dirty counts, upstream, whether remote is walled
    proofs    the suites, the standups, the parity runs and the sittings
    seats     the seat declarations, read from agents/ and pipelines.md
    records   the estate's documents by kind, one served whole with a receipt
    muster    the declared worlds
    rack_list what the rack holds

Thirty-two of the seventy-eight have no page yet -- the record and law readers,
the rack commands, the mesh, keys and tenants. They answer over MCP today; they
have no button.

## The dials

`.env` in this folder, gitignored and never printed. `.env.example` names every
one with what it does. The ones that change how a run behaves:
`MANJUEL_GIT_REMOTE` (the push wall), `MANJUEL_RACK_PULL` (may models be
downloaded), `MANJUEL_VRAM_GB`, `MANJUEL_KEEP_ALIVE`, `MANJUEL_SEAT_TIMEOUT`,
`MANJUEL_SKILL_TIMEOUT`. The older `CHAINKIT_` spellings still answer.

## When starting goes wrong

    "research has an open sitting (N, opened ...)"
        A sitting is open, or one was left open by a killed process. Close it
        from the dashboard's Close sitting; if no engine is running, the last
        line of `sessions\sessions.jsonl` has no `ended` and it is closed by
        APPENDING a closing line, never by editing the one already written.

    the dashboard shows something that is not true
        It repaints every 15s and confesses when it is over a minute stale.
        If a page still looks old after a rebuild, that was the missing-ETag
        fault -- fixed 2026-09-09; every static file now revalidates.

    "mcp unreachable"
        The door is not running, or not on 8090. Check `atlas\line\mcp.log`.

    the rack is unreachable
        `ollama serve`. The boot report's RACK block says so and the rest of
        the report still prints.

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
    MANJUEL_MCP_<NAME>      --     a LOCAL MCP server, callable as <NAME> by the
                                   `mcp_call` skill. Loopback only; anything else
                                   is refused by name and nothing is sent (skills.py)

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

    python tests\release.py --check 0.1.10

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

**If you saw this after EVERY green run, that was a bug, and it is fixed.**
Until 2026-09-10 the check took the newest `.py`/`.md` under `manjuel`,
`agents`, `skills` and `tests` with no exclusions — and `tests/last_run.md` is
a `.md` under `tests/` that the suite itself writes as it finishes. So the
ground always looked "changed since" the moment a run ended, and the line fired
every time. Measured: boot's newest edit was `tests/last_run.md` at 0.0s after
the run, while the release gate read the same tree as 86 seconds *older*.

The suites' own stamps (`last_run.md`, `last_run.json`, `run_history.jsonl`,
`last_audit.md`) are now excluded, which is the rule `tests/release.py` already
used. A stroke proves both copies agree, so they cannot separate again. **A
STALE line now means what it says.**

---

## A world will not answer

Worlds are addressed directly (`@name`) and are private by design: a direct
address is a closed-door visit, recorded in the transcript, never fed into the
conversation other seats read. If a world's seat has no `Wakes On:` line, it
will *never* be summoned by a flag — that is deliberate, not a fault.

Client data inside a world is sealed and stays sealed (REFUSALS §5). An empty
search result over sealed material is the correct answer, not a bug.
