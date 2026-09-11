# Contributing

## Run the suites first

    pip install ".[test]"   # the [test] extra is not optional for the
                           # strokes: one of them imports numpy outright.
    python tests/test_manjuel.py && python tests/smoke_cli.py
    python law/law.py verify
    python tests/buildmap.py            regenerate BUILDMAP.md after a code change
    python tests/standup.py             the seats, live -- read the report

Both suites are **offline and stubbed**: no rack, no network, no GPU, no
model. If a change makes them need a live model, that is the regression —
the offline property is a promise this project makes publicly, and CI runs
both on Windows and Ubuntu, Python 3.10 and 3.13, on every push.

`law.py verify` walks the hash-chained ledger. It is not in CI on purpose:
a fork with a re-terminated law file should fail on a real terminal, where
it means something, and not in a job that cannot tell tampering from a
checkout artifact.

## The rule that shapes everything else

**No agent lands anything.** Not a commit, not a memory entry, not a push,
not a config change. Agents prepare; a person lands. That is RULE 6 in
`CLAUDE.md` and LAW 6 in the ledger, and it is not a setting.

If a change would let Manjuel commit, approve, or write outside its
declared wall, it is not a feature with a flag — it is a different project.

## Every guard is named after the failure that earned it

Read `REFUSALS.md`. Twenty-one numbered refusals (plus 7b and 11b), each with the sitting number of the
run that produced it. That is the house style, and it is the contribution
standard:

- **Reproduce, then guard.** A stroke goes red BEFORE the fix, not after.
- **Stroke it both ways.** Every guard needs a case that fires and a case
  that must NOT. A guard proved only on what it refuses might refuse
  everything. Most bugs found in this repo were found that way.
- **Rewrite a superseded stroke, never delete it.** Note why it moved and
  keep the guard. See `test_the_chain_writes_declared_newlines` — the
  ruling reversed and the guard survived.
- **Report over gate, for anything that reads the corpus.** `logs/` grows
  every sitting, so an assertion over it goes red because someone used the
  CLI. `audit_record.py` and `manjuel/us.py` both report and exit 0.

## Adding a skill

1. `skills/<name>.md` — Action Keyword, Description, Parameters Needed.
2. A handler in `manjuel/skills.py`, registered with `@skill("<name>")`.
3. **A record in `us/manjuel.us`** declaring what it may reach: `wall`,
   `writes`, `remote`. Write `wall` by reading your own handler; do not
   infer it. `python -m manjuel.us` will tell you if you skipped this.
4. A stroke that executes it.

Startup refuses, by name, a skill file with no handler and a pipeline
naming a seat no file declares. It will tell you which.

## Adding a seat

`agents/<name>.md` declares model, stage, on-fail, when, context, timeout, voice, prompt —
and `May Call` if it holds tools. A seat with no `May Call` holds none: it
reads nothing, writes nothing, reaches nothing. That is most of the roster
and it is deliberate.

Then `us/chain_<name>.us`. `permission` is **derived** from `May Call` plus
each named skill's wall — never written beside it. Writing it separately is
how the Router came to declare `read: agent_workspace only` while cleared
for `all`.

## The toll

At the end of a sitting the REPL offers a toll into `SEAT_LOG.md`. The
observed half — runs, stages, timings, git state — is machine-written. The
judgment half (`WHAT PROVED / IS THIN / IS OWED`) is yours and is never
generated.

**Not paying it is a legitimate outcome.** A sitting that closes without a
toll gets an honest entry saying the judgment was never stated, rather than
an invented one. Nothing is blocked by an unpaid toll. Pay it when you have
something to say; the record is worth more when it is not padded.

## Platform

Windows-first. `manjuel/voice.py` (SAPI out, whisper.cpp in) and parts of
`registry.py` are Windows-bound, and `bin/` carries Windows binaries.

**Voice degrades alone.** `boot.py` reports GROUND / RACK / RECORD / GATE /
VOICE separately, so a machine with no voice boots, says so, and runs
everything else. The suites do not need it. Nothing else is platform-bound.

## What this project will not take

- A listening socket, a chat-platform bridge, or an always-on daemon. The
  comparable systems' exposure findings all require one; this binds nothing
  and serves nothing, and that is the position rather than a gap.
- A model that writes its own seat prompts, commit subjects, or memory
  entries. Models propose into a pending file; a person lands.
- A dependency. There is one. Adding a second needs an argument.
