# Build Path

The modules, what each one owns, and the order the estate actually grew.
The containment rule has held since the first rewrite and is the reason the
suite runs offline: **`registry.py` and `skills.py` know markdown; `runtime.py`
knows Ollama; nothing else knows either.**

## Layer 0 — words on disk (the sources of truth)

    agents/*.md      seats: model, stage, wake condition, anchor, prompt
    skills/*.md      tools: keyword, description, params (+ optional model)
    pipelines.md     running orders; spine only — racked seats are not listed
    index_roots.txt  what the semantic index may read (Research only)
    parity.md        the measurement cases

## Layer 1 — parsing (markdown becomes objects)

    registry.py   agents/ + pipelines.md → Agent, Step. The only reader of
                  seat markdown. Refuses duplicate seats, unknown seats in
                  pipelines, unreadable anchors — at load, never mid-run.
    skills.py     skills/ → SkillSpec bound to @skill handlers. Manifest and
                  executor verify each other at startup, so a tool cannot be
                  advertised that cannot run. Also home of the handlers
                  themselves (git, rack, ground, index, report skills, and
                  `inspect` -- a file's facts before anything reads it) and
                  of `windowed()`, which turns a file too big for any window
                  into part N of M with its own headings mapped -- a movable
                  window rather than a silent stump.

## Layer 2 — deciding (before any model wakes)

    lawgate.py    THE LAW GATE (2026-09-04, the operator's ruling: every
                  call runs through the law). First on every run: walks
                  law/chain.jsonl with the pen and checks every sealed
                  law's fingerprint; checks the objective against the laws
                  a regex can decide (reach outside the ground, a secret by
                  name, across the wall with remote off, client material by
                  tag); hands every seat a `## The law` block as fact (in
                  the SYSTEM role since 2026-09-07; the court gets the ten
                  verbatim); stamps the record. A tampered law refuses
                  every run.
    intent.py     deterministic pre-routing, all arithmetic, so it cannot
                  hallucinate. In the order it decides: is this language at
                  all (the gibberish gate); does it name a tool (aliases,
                  for how a person actually says it); is it an ORDER to
                  search (decomposes_to_search -- verb class + object
                  class, so close-but-not-exact still dispatches); is it
                  SEVERAL acts (is_big_objective -- sequencing language
                  plus two act-verbs, erring shut); is it a question
                  carrying a term worth looking up (asks_the_ground); is it
                  a write, an action, a filename, a follow-up, a farewell.
                  Also the injection markers and the claim/citation shapes.
    seating.py    the seat rack: who rests, what flag summons them, where
                  they land (first / after X / last). Guarantees the gate
                  stays a gate and one flag cannot seat a loop. `repeat()`
                  sends ONE more pass through a seat that has already sat,
                  bounded by the same (seat, flag) key as summoning.

## Layer 3 — running

    context.py    RunContext: objective, feed, dialogue, flags, artifacts,
                  notes, method, the law, the standing, the named file, the
                  partial reads. Survives to the last stage by construction.
                  Also `now_block()` -- the clock every seat is given. It
                  lives here because both the pipeline and the skill library
                  need it and this module imports nothing of ours.
    pipeline.py   the engine: walks the seating, builds per-seat prompts,
                  reads flags and verdicts (fail-closed), bounds the tool
                  loop, lands the coder's files, prices nothing it cannot see.
    runtime.py    the only Ollama client: chat, embed, warm, resident.
                  Reads dict AND object response shapes; falls back to a
                  thinking model's reasoning when content is empty.

## Layer 4 — measurement (advisory, never authoritative)

    mathkit.py    dot, cosine, regression — no numpy dependency.
    vectors.py    the semantic index (sqlite + embeddings); refuses
                  secret-named files whatever their extension.
    drift.py      each stage scored against the source; a low score is a
                  flag to read, never a verdict.
    parity.py     Manjuel vs one bare call to the same local model;
                  grouped by reference, expected refusals honored.
    vram.py       footprint planning, foreign-model detection, budget.
    rack.py       rack.md -- what is on this machine, written down with the
                  time it was taken. DERIVED from Ollama, regenerated whole,
                  never appended (not a LAW 1 record).
    watch.py      the ground watches itself: an edited seat, skill or doc is
                  noticed and applied at turn boundaries. Needs watchdog;
                  without it every call is a no-op.

    proved        THE ESTATE'S OWN STANDING, read from what the suites
                  stamped -- tallies, staleness, named failures, recent
                  history, and whether the manifest still agrees with the
                  disk. Added 2026-09-03 (sitting 81) because the operator
                  asked "have you run a full test suite on these skills?"
                  and Manjuel answered out of its own head. The strokes (a count
                  the suite prints; none is written here)
                  test the ENGINE from outside; none let the ESTATE say what
                  it had proved. It reports its own limits every time and
                  refuses the claim it cannot make.

## Layer 5 — the record

    transcript.py logs/ per run; recorded text demoted below stage level so
                  output cannot forge the record.
    memory.py     memory.md append-only; seats propose, the operator lands.
    seatlog.py    sittings and the toll; the standing (DAYBOOK's last entry,
                  handed to the door and the court).
    gitstate.py   read-only git + local init/commit; stale locks named with
                  their cure; remotes off unless the operator opens them.

## Layer 6 — the senses and the voice

    voice.py      speech out (OS engine, interruptible, text via file not
                  argv) and in (whisper.cpp from bin/, vocabulary-biased,
                  mishearings corrected, records until you go quiet).
    spelling.py   deterministic corrections on the delivery only; unknown
                  words reported, never rewritten.
    ink.py        per-seat color, spinner; no-ops when not a tty.

## Layer 7 — the door

    cli.py        the REPL: one prompt, shared typed/voice thread, slash
                  commands, boot + preflight.
    boot.py       GROUND / RACK / RECORD / GATE / VOICE report; every
                  section degrades alone. And the brief's facts, read off
                  the record at every open (`/brief` has the door say them).
    dotenv.py     .env honored; returns names, never values.
    manjuel.py      sixteen lines; the entrypoint.

## Layer 8 — the declaration, and the reconciliation

    us/*.us       THE CAPABILITY MANIFEST (the Atlas spec). Each record
                  declares what a thing MAY TOUCH, not what it does:

                      wall          the jail. "agent_workspace/", ".git in
                                    this ground", "none - pure computation"
                      writes        does it put anything on disk
                      remote        does it leave this machine
                      lands         may it write the operator's record
                      can_approve   may it authorise anything (always false)
                      covenant      the hash binding a record to its office
                      reports_to    Manjuel of answerability

    THE MANIFEST IS THE SAFETY CLAIM. Every other harness answers "what
    can this tool do?" with prose. This one answers "what may it reach?"
    with a field, per capability, in a file the operator can read in one
    sitting. That is the deliverable's whole argument.

    IT IS VERIFIED SINCE 2026-09-03. `manjuel/us.py` parses us/*.us and
    reconciles every record to the disk (`python -m manjuel.us`). When
    this paragraph was first written nothing parsed it and it had drifted:
    20 of 35 skills undeclared, 3 of 14 seats without a record, the
    embedder and the tool cap both wrong. Today: every skill file has a
    record and every record a file (37 and 37 as of 2026-09-07); 14 seats,
    14 records; embedder and cap agree. The one
    finding the reconciler still reports is the rack, which it cannot
    ask from a sandbox. It is also indexed (index_roots.txt) so a seat
    can quote it.

    A declaration nobody checks is a promise, and this ground does not
    ship promises. LAW 5 applies to the manifest exactly as it applies to
    a seat: a claim is not a fact until the record proves it.

    THE RECONCILER is therefore the layer, not the manifest:

    us.py         parse us/*.us -> records
    reconcile     compare each record to the implementation it names, and
                  REPORT (never gate -- audit_record.py's rule):
                    every skill on disk has a record
                    every record names a skill that exists
                    `wall` matches the handler's actual jail (gate_paths,
                       safe_path, or "none" for pure computation)
                    `writes` matches WRITING_SKILLS
                    `remote` matches the git remote gate
                    `lands` is false everywhere except the operator's path
                    `can_approve` is false EVERYWHERE, without exception
                    declared model tags are on the rack

    STROKED, because the reconciler is itself a safety claim: it must go
    RED on a record that lies, and green on one that is merely terse.

    WHY THIS AND NOT MCP. MCP describes what a tool DOES so a model can
    call it. `.us` declares what a tool MAY REACH so a person can audit
    it. They answer different questions and the second is the one this
    estate is for. MCP can be surfaced as skills later and would inherit
    the four gates already at execute() -- clearance, LAW 8 paths, the
    timeout, the dedup -- and would then need `.us` records like anything
    else. The manifest is the integration point, not a competitor to it.

## Layer 9 — a stranger's first hour

    Not built. What stands between this ground and someone else running
    it, in the order it blocks them:

    pyproject.toml    LANDED 2026-09-03. One dependency; `manjuel` on
                      PATH; the wheel carries the ENGINE and not the
                      record -- 31 files, no SEAT_LOG, no memory, no
                      logs, no sessions, no .env, no bin/. `law/` is
                      unpackaged: it is a ledger bound to this ground by
                      sha256, and a copy in site-packages would be a
                      second Manjuel nobody walks.
    SPEC.md           LANDED 2026-09-04. What this IS and when it is DONE,
                      line by line: MET with the stroke, or OPEN with whose
                      call it is. The contract; DESIGN is the reasoning.
    BUILDMAP.md       LANDED 2026-09-04. Where to look, generated from the
                      code with ast by tests/buildmap.py: every module,
                      class and function with line ranges; every guard by
                      the sitting that earned it; every stroke and what it
                      touches. `--check` in CI refuses a stale map.
    tests/standup.py  LANDED 2026-09-04. The seats through nine fixed
                      objectives (the court split out 2026-09-09, --court),
                      live, with mechanical expectations and a
                      reviewable report; a sitting opened and tolled. The
                      first live run (sitting 86) found four things in
                      six minutes. `--dry` proves the harness in CI.
    CI                LANDED 2026-09-03. Both suites plus law --prove
                      (and, since 2026-09-04, buildmap --check, standup
                      --dry and the record audit), Windows AND Ubuntu,
                      3.10 and 3.13. Ubuntu is in
                      the matrix BECAUSE this ground is Windows and the
                      record is CRLF: .gitattributes declares the
                      terminators in-repo, and this proves they travel.
                      The offline property is now a PUBLIC CLAIM -- if a
                      change makes the suites need a live model, that is
                      the regression.
    index_roots       ships as a WORKING DEFAULT, tracked on purpose --
                      index_roots.txt says so in its own header. An
                      .example.txt was considered and declined: gitignoring
                      the real file would red the eight strokes that read
                      it.
    the record        SEAT_LOG, memory, DAYBOOK, sessions.jsonl are all
                      tracked -- 3,100 lines of real sittings. KEEP THEM.
                      A harness whose pitch is "every guard is named after
                      the failure that earned it" needs the failures
                      visible or the guards read as theory.
                      SUPERSEDED 2026-09-08, the operator: "dont git
                      track them." SEAT_LOG, memory.md and sessions/
                      *.jsonl stay on disk as the record and leave git;
                      DAYBOOK, HANDOFF, CHANGELOG, TASKS stay tracked.
                      The history up to baa4f32 keeps what it holds
                      (LAW 1). The line above stands as what was true.
    platform          voice.py and registry.py are Windows-bound;
                      bin/ carries whisper/ggml DLLs. Voice degrades on
                      its own (boot reports each section separately), so
                      this blocks nobody -- but it should SAY so.

    DELIBERATELY NOT IN THIS LAYER, and named so nobody adds them
    thinking they are missing:

    chat gateways     eleven-platform bridges are where the market's
                      exposure lives: 40,214 internet-exposed instances
                      of one comparable system, most without auth, a
                      large share RCE-vulnerable. Every one of those
                      findings requires a LISTENING SOCKET. This ground
                      has none, binds nothing, and serves nothing. That
                      is not a gap to close; it is the position.
    always-on daemon  same surface, same answer.
    external APIs     later, deliberately, and behind `.us` records that
                      declare `remote: true` -- the shape git_push
                      already uses.

## The order it actually grew (and why)

1. Rewrite: mangled manjuel.py → manjuel/, containment rule established.
2. Skills verified against handlers; prompt skills added.
3. Transcripts, sessions, memory, git, sittings — the record before polish.
4. Index + drift (the embedder as instrument, not stage).
5. VRAM discipline: foreign models, budgets, warm-on-boot.
6. The simplification: 8 stages → 3-stage spine + seat rack.
7. Deterministic layer: intent routing, gibberish gate, harness-fact skills.
8. Voice: out, in, interruption, hearing correction.
9. Tiering: small resident, coder on call, reasoner one flag up.
10. The gates: refusals in Python rather than requests in prompts --
    injection, LAW 8 paths, per-seat clearance, timeouts, the claim-check,
    the citation-check, the dedup, the seam.
11. Time: the clock on every prompt, a period resolvable to its runs, a
    number resolvable to its sitting, recency as a tiebreak in retrieval.
12. Context by MAP, not reduce: a movable window over a big file, a route
    before a multi-act objective, and one bounded pass back from review.
13. Throughout: every observed failure became a stroke before it was
    called fixed. The suite is the build's memory.

14. The record about the record: an auditor that sweeps the whole corpus
    for the shapes the gates now refuse, run-history with crash detection,
    provenance on every failing stroke, and the session book that carries
    intent across the amnesia between sessions.

## The order it goes next (2026-09-08, proposed; TASKS "THE PATH TO 0.1.8" is the list)

15. Four versions to DONE, one theme each, tagged in order, each ending
    at the same gate: 0.1.5 the bounds (the loops the REPL read found;
    the seat bound; the index guard; the release gate itself);
    0.1.6 the story and the hands (the sitting story; the hands ledger;
    the sitting laws sealed); 0.1.7 the door and the court (the prose
    faults, the citation check, parity on the tiers); 0.1.8 the seal
    (workflows; the gate in CI; the rulings executed; SPEC §4 with no
    OPEN line). The final goal is SPEC's: every line MET or RULED OUT,
    and the operator has run the standup on his own terminal.

## The ladder as it ACTUALLY went, and where it goes next (2026-09-10)

The plan above is kept because it is the record of what was intended. It is
not what happened, and a plan that describes a version nobody shipped is the
same fault as a doc naming a command that does not run.

    0.1.7  shipped WITHOUT the door work it was named for.
    0.1.8  THE GLASS AND THE GATE -- BUILT, NEVER TAGGED, folded into the
           0.1.9 tag (2026-09-10), the way 0.1.6 folded into 0.1.7 the same
           day it was built. A theme the plan never named. atlas as
           the control plane; Records and the `records` tool; the release gate
           read at every boot; the standup split so it runs unattended; the
           estate fully indexed (17 roots -> 39); the runbook that says how to
           start it. SPEC 4.1, 4.2 and 4.3 closed.
    0.1.9  THE DOOR AND THE ROUTE. The operator's own words for what it is
           for: "a chatty front door with enough smarts to know when to route
           externally and actually use the tools/skills that it has access to
           through a larger routed system."
    0.1.10 THE SEAL. Inherits the original 0.1.8 almost unchanged: the gate in
           CI, ESTATE LAW 2 as a gate, SITTING LAW 5 sealed, the terminator
           ruling, the client token, the small-honesty list. Half of it is his
           to rule, which is why it is last.

WHAT MAKES 0.1.9 ONE VERSION. Four of its five pieces are the same fault in
different clothes -- A SEAT SAYING SOMETHING IT DID NOT GET FROM A TOOL:

    1. the corpus split (C+D, his ruling 2026-09-10). semantic_search answers
       from SOURCES; the transcripts are a separate, explicit reach; and a log
       is indexed by its DELIVERY, not its mid-run reasoning. Measured before
       the ruling: 812 of 996 indexed documents (81.5%) and 4,060 of 6,705
       ranked passages (60.6%) are old transcripts, and "what does the
       covenant say" returns eight old runs and never the covenant. The estate
       answers from its own echo, and each answer is written back to logs/ and
       indexed, so an error laundered once becomes the record. `transcript.py`
       already names this risk in a comment ("logs/ is an index root: the next
       rebuild would embed it, and semantic_search would hand it to a seat as
       a tool result") and fixed one instance of it; this generalises that.
    2. the citation check (SPEC 4.3; TASKS s82 finding 4) -- a claim about
       what a tool result SAID with nothing tying it to the result. The
       largest thing left in the spec, and C+D makes it tractable: citations
       are worth checking only once the source is a source.
    3. the door invents numbers (TASKS; SPEC 4.7) -- "300 to 1200 bytes", seen
       again 2026-09-09, intermittent.
    4. the door parrots the record's labels / answers the previous question /
       ships an empty flag scaffold (TASKS). The new door prose already showed
       a mild case: it echoed "I can raise flags" back at the operator.
    5. the tool-loop dedup is per Router sitting, not per run (TASKS) -- the
       Router's half of the same split.

    WHY THE TRANSCRIPTS ARE INDEXED AT ALL, in his words (2026-09-10) and
    recorded because it is the reason the split has two halves rather than
    one deletion: "indexing the logs for drift between responses, and then an
    index for fast searching the codebase and cwd, with a drift check from
    previous responses ... i am very much about building redundant security
    loops within the system to ensure i am not being bypassed or missing
    anything. I don't trust the system, thus i want to see everything and
    make sure its all logged and recorded. the idea is to go back and measure
    from one task to the next kind of as a subprocess so i can go back and
    tune the system where needed."

    So the two corpora have two JOBS, not one job and a nuisance: sources
    answer a question, and the transcripts are the material a drift
    measurement is taken against. That is a better reason to keep logs
    indexed than the one this plan first gave.

    THE GATE IS UNCHANGED: `python tests/release.py --check` must pass before
    any of these is tagged, and the tag is his (RULE 6).


## Reading order for a new hand

`CLAUDE.md` (the operator's rules) → `DAYBOOK.md` (what the last session
was FOR — you begin with total amnesia and that is the only file that
carries intent across the gap) → README → QUICKSTART → this file →
`pipelines.md` → one seat file → `intent.py` (small and load-bearing) →
`pipeline.py` last, with a transcript from `logs/` open beside it.

`REFUSALS.md` when you want to know what the estate will not do,
`TESTING.md` before you touch a stroke, `RUNBOOK.md` when the machine
misbehaves, `HANDOFF.md` for the fix log and the standing rulings.
