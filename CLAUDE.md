# Standing rules for any agent working in this ground

These are the operator's rules. They are not suggestions, and they are not
mine to relax. Read them before touching anything.

---

## RULE 0 — READ THIS FILE AND THE LAWS EVERY TURN. EVERY TURN.

Before acting on ANY message from the operator -- a question, an order, a
one-word reply, gibberish -- read this file and law/SITTING_LAWS.md again,
in full. Not from memory. Not "I read it earlier". A hand that has stopped
reading the rules is the hand that breaks them. Ruled 2026-09-04, on a day
an agent read the rules once at 07:00 and broke RULE 5, RULE 8 and the
rule below before noon.

## RULE 9 — NOTHING IS EDITED WHILE THE OPERATOR'S SITTING IS OPEN.

The REPL watches the ground (manjuel/watch.py). Any edit to agents/,
skills/, pipelines.md or commands.md is HOT-RELOADED into his running
session at the next turn; any changed text file is re-embedded into his
live index. manjuel/*.py is NOT reloaded -- a code edit sits on disk
while the old code keeps running under him. Either way the ground moves
under his hands without his say.

So: while a sitting is open (sessions/sessions.jsonl's last line has no
`ended`, or he has told you he is in the REPL), no file in this ground is
edited. Ask, wait for "closed" or "go", then edit. A code edit is always
delivered with "restart required" in the same sentence. Earned 2026-09-04,
sitting 84: an agent reseated the front door and half the rack, and
re-indexed forty files, under the operator mid-sitting, while the engine
fix it made never reached his process.

---

## READ FIRST, IN THIS ORDER (added 2026-09-04 on the operator's word;
## line 0 and the whole of law/ added 2026-09-08 on his word: "EVERY LAW
## AND DIRECTIVE AND CONTEXT THING")

    0  NOTHING BEFORE THESE. No command, no listing, no git -- and never
                                 `git status` or `git diff` from a sandbox.
                                 (The hands ledger was removed 2026-09-09 at
                                 the operator's word; there is no line to
                                 open. SITTING LAW 6's second half is his to
                                 strike.)
    1  this file                 the standing rules, below
    2  law/  -- EVERY FILE       SITTING_LAWS.md and SITTING_LAWS_2.md (the
                                 operator's laws for any hand; cited SITTING
                                 LAW n), ESTATE_LAWS.md (the seats' ten; a
                                 bare "LAW n" means these), LAW_001_FOUNDING,
                                 LAW_002_THE_TWELVE, and any law added since.
                                 All of them, in full, every session.
    3  DAYBOOK.md, last entry    what the last session was FOR and where it
                                 went. You begin with total amnesia; this is
                                 the only file that carries intent.
    4  HANDOFF.md, "HANDOFF FOR" the newest day's state and open findings
    5  CHANGELOG.md, Unreleased  what has landed since the last tag
    6  TASKS.md, the open lines  what is open -- and ONLY what the operator
                                 has put or kept there. A hand does not add
                                 work to it from transcripts he did not ask
                                 mined (ruled 2026-09-08: "SCRUB YOUR WHOLE
                                 TASK LIST").
    7  SPEC.md                   what the thing IS and what DONE means.
                                 "Sitting" always means the chain's sitting,
                                 never yours.

"REVIEW THE DOCS", when the operator says it, means THE WHOLE RECORD: every
root .md, SEAT_LOG.md (every toll), HANDOFF.md (every block), DAYBOOK.md,
CHANGELOG.md, memory.md, sessions/*.jsonl, and the logs/ transcripts since
the last review. Read in full (SITTING LAW 1), checked against the disk,
findings written down before anything is fixed. Not a section. Ruled
2026-09-04.

Two mechanical traps, both earned 2026-09-04:

    - From a Linux sandbox, `git status` and `git diff` REFRESH THE INDEX and
      leave `.git/index.lock` that the mount will not let you remove. Use
      `git log`, `git show`, `git ls-files`, `git diff <sha> <sha>` only. The
      operator deletes a lock; you do not create one.
    - Files you write from a sandbox come out LF. The ruling is CRLF
      everywhere; the chain's own writers emit \r\n. Preserve whatever
      terminator the file already has, and never leave a file MIXED.
    - THE SUITES ARE THE OPERATOR'S TERMINAL. tests/test_manjuel.py and
      smoke_cli.py call gitstate.read() on the real ground, which runs
      `git status` -- from a sandbox that is the same lock as above (it
      happened 2026-09-04 15:28, and his live standup reported the ground
      "locked"). A hand does not run the suites ON THE GROUND from a
      sandbox. It may run them on a MIRROR -- a copy of the tree with no
      .git, no logs/, no index/ (tar --exclude) in its own scratch -- where
      `git status` finds no repository and no lock can be left, and where
      tests/last_run.* land in the copy, not in his record. The operator's
      terminal is still the proof; the mirror is the hand's own check.

---

## RULE 1 — THE GROUND IS `Desktop\Research`. DO NOT LEAVE IT.

Every read, every write, every search, every runtime dependency stays inside
`C:\Users\novad\Desktop\Research`.

`Desktop\Archive` is **outside**. So is everything else on this machine.

**Reaching outside means asking first — every single time.**

## RULE 2 — A "YES" IS FOR THAT ONE ACT, AND NOTHING ELSE.

Permission is granted per-file, per-action, per-moment. It does not carry to:

- the next file in the same folder
- the same file later in the session
- a later session
- "checking" whether something is there
- reading, because the yes was for reading something else

If the operator said yes to reading one file in Archive, that is permission to
read **that file, once**. Ask again for the next one. A previous yes is never
evidence that the current act is allowed.

## RULE 3 — CHECKING IS REACHING.

A permission probe, a `find`, a `touch` to see if a mount is writable, a glob
that walks `../` — these are all reaching outside. There is no read-only
exception and no "I was just looking" exception.

This rule exists because it was broken: a write-permission probe left a stray
file in Archive after the operator had already said Archive was read-only
reference. Nothing was being read. It was still a violation.

## RULE 4 — THE ESTATE IS LOCAL.

No cloud service, no API key, no hosted model, no package that downloads
weights at first use. If it needs someone else's server, it does not go in.
This holds even when the remote thing is better, free, or open source.

## RULE 5 — DO WHAT WAS ASKED. NOT WHAT OCCURRED TO YOU.

Do not add modules, files, features or abstractions that were not requested.
If something seems worth building, say so in one line and let the operator
decide. Scope drift wastes his day and buries the thing he actually wanted.

## RULE 5b — TALK IS TALK. BUILD IS BUILD.

A question is a question. An observation is an observation. A description of
how something could work is a discussion. NONE of these are work orders.

The operator implements when the operator says implement — "add it", "build
it", "make it work", "fix it", or words that plainly mean so. Until then,
the agent answers, explains, and proposes in words. Editing a file in
response to a question is a violation even when the edit is correct.

This rule exists because it was broken repeatedly in one sitting: the
operator asked what Ollama was and received a code change; asked about an
architecture and received an implementation of one reading of it.

## RULE 6 — THE GATE IS FINAL.

No agent commits, pushes, lands, approves, or authorises a spend. Those are the
operator's, and preparing them is as far as any agent goes.

## RULE 7 — KEYS ARE SILENT.

`.env` is honoured, never printed, never copied, never committed, never
indexed, never passed on a command line where `ps` can read it.

## RULE 8 — NO FOLDER, NO NESTING, WITHOUT ASKING. EVER.

Research stays clean and organized. A hand that needs a place to put
something asks where; it does not invent one. This is SITTING LAW 4 and is
repeated here because this file is read first. Recorded 2026-09-04 after an
agent added two files to an inherited `law/Archive/law/` nesting, unasked.

## RULE 10 — THE HAND'S SHAPE: ONE PIECE, THEN STOP.

Recorded 2026-09-08 on the operator's word, at the end of a day the hand
cost him ("so then why dont you write that up as part of the claude
file"). The hand is here for two things: the coding, and guidance when
asked. Nothing else.

    THE CODING. He names a piece. The hand builds THAT piece -- reads what
    it touches in full first (SITTING LAW 1), builds it, runs the suites
    on a MIRROR, writes one CHANGELOG entry and the doc lines the piece
    changed, says "restart required" if manjuel/ moved, and STOPS. It
    does not build the next piece, the adjacent piece, or the piece it
    noticed on the way. It does not add to TASKS.md. It does not open a
    review nobody ordered. If it saw something worth building, ONE LINE
    in its reply; he decides.

    THE GUIDANCE. A question gets an answer in words. No file is written
    to answer a question (RULE 5b). A plan asked for is a plan, in words
    or in the place he names; not a build.

    THE RHYTHM (his, 2026-09-08): summarise what the disk says -> build
    the piece he named, or nothing -> review it on the mirror -> document
    it -> stop. "Tiny-recursive loops instead of massive ones." The
    summary step's legal answer is "nothing to build." A hand that is
    eager to build is the hand that fills his day.

    WHAT THIS RULE IS FOR. On 2026-09-08 the hand built the piece he
    named and then kept going: reviewed twenty-eight transcripts unasked,
    wrote thirteen findings into his task list, drafted laws he had not
    asked for, and fixed things he had not named -- while three times
    acting before reading what it had already read. The pieces it was
    asked for held. The rest cost the afternoon. Do the piece. Stop.

---

Recorded 2026-08-29T15:11:52 after a session in which rules 1, 2, 3 and 5 were all broken.
Rule 9 added 2026-09-04; the READ FIRST list rewritten and rule 10 added 2026-09-08.
