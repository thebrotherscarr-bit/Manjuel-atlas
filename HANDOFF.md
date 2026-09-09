# HANDOFF

Next agent: read CLAUDE.md (operator's rules), then DAYBOOK.md (what the
last session was for and where it drifted — you begin with total amnesia
and that file is the only thing that carries intent across the gap), then
this. BUILDPATH.md has
the module map. The strokes and the smoke suite pin everything below; run
both after any edit (each prints its own tally — no count is written into a
doc, because the suites grow with the system):

    python tests/test_chainkit.py && python tests/smoke_cli.py

RUN THE SMOKE SUITE, not just the strokes. It was RED at 34/50 from 14e2711
to 2026-09-02 because its StubRuntime had not been moved with pipeline.py,
and nothing noticed: the strokes were green the whole time.

**START AT `## HANDOFF FOR 2026-09-09`** (search for it — the day blocks
stack newest first above `## Open`). CHANGELOG.md carries the versions;
DAYBOOK.md Session 5 carries the day's intent. Everything between here and
there is standing reference that has not moved.

## Numbers (as of 2026-09-04, sitting 86 — see SEAT_LOG for the outside hands)

    THE RACK IS TIERED SINCE 2026-09-04 (operator's ruling after sitting
    82: "table works mostly the same reasoning from the same models").
    Seven models seat fourteen seats; the court is four different heads.
    Eleven-seats-on-phi4-mini is CLOSED. rack.md is DERIVED -- run
    `rack_sync` after any seat change; it was last taken 2026-09-04 22:18.


    chainkit/     26 modules (+__init__; lawgate.py is the 26th), ~12,400 lines
                  strokes + smoke offline · standup LIVE (tests/standup.py) ·
                  BUILDMAP.md generated from the code; SPEC.md is the contract
    agents/       14 seats       skills/    37 tools (32 handlers + 5 prompt skills; `inspect` is the 37th, 2026-09-07)
    pipelines     5 · foundation/ 25 docs indexed · worlds/ (see the file)
    law/          THE LAW as a hash-chained ledger. `python law/law.py verify`
    models        llama3.2 (Steward -- the front door; Neiro, Guardian,
                  Morning Reviewer, Quartermaster) · phi4-mini (Proofreader,
                  Delivery Agent) · qwen3.5:4b (Router, Quality Evaluator) ·
                  qwen3.5:9b (Reasoner, Deep Researcher) · deepseek-r1:8b
                  (Jesster) · gemma4:12b (Manjuel -- rules last; a thinking
                  model NEVER sits at the door in front of the Router) ·
                  qwen2.5-coder:7b (Expert Coder)
                  references only: gemma4:e4b, qwen2.5-coder:14b, qwen3-vl:8b
                  nomic-embed-text-v2-moe (index/drift/parity -- named by
                  NEITHER agents/ nor skills/, so PREFLIGHT CANNOT CATCH a
                  wrong tag here; it is EMBED_MODEL in skills.py, and
                  changing it invalidates the index) · llama3.2 and
                  deepseek-r1, qwen3-vl, qwen2.5-coder:14b: on the rack,
                  NAMED BY NOTHING
    voices David/Zira/Mark · warm order: spine fg, reasoner bg thread,
    coder lazy — operator ruling, DO NOT retune
    CLIENT SHIELD: vault/ path, .client. name, [[CLIENT]] token — any one
    tag HARD-refuses index/watcher/reads/listings. Does NOT cover git.
    worlds/ IS in .gitignore and NO LONGER TRACKED -- `git rm -r --cached
    worlds/` landed; `git ls-files worlds/` is 0.
    INDEX SCOPE, SUPERSEDED 2026-09-03: NO WORLD IS AN INDEX ROOT AT ALL.
    A world is ORIGIN ONLY. The earlier ruling (one at a time, by name, on
    his call) bounded WHICH worlds could be swept in; it did not stop a
    named world from ANSWERING, and worlds/manjuel put 91 of 783 docs in
    the corpus and delivered "Steward is Manjuel, the instance of
    llama3.2" — three errors from one retrieval. Not a shield breach: 0
    vault, 0 .client., 0 secrets, re-proved. A DOCTRINE collision, and
    structural — that world describes a different system in this one's
    exact vocabulary. Stroked as a property, naming no world.
    index_roots.txt is the first line, the vault/ shield is the second.

## THE LAW is in the ground now

    foundation/foundation/05_THE_LAW.md   the canon, beside the sealed four
    law/ESTATE_LAWS.md                    the ten, sealed 2026-09-04 (link 3)
    law/SITTING_LAWS.md                   the operator's four, sealed (link 4)
    law/law.py --prove                    9 strokes, hermetic, exit 0
    law/law.py verify                     walks the chain, refuses a lying byte
                                          4 links, head def001d70eb410d2
    law/*.md                              the library    law/chain.jsonl the chain (flat since 2026-09-04)
    worlds/manjuel/                       origin archive, read-only by position

TWO FAMILIES OF LAW, ruled 2026-09-04. THE ESTATE LAWS are the ten, for
the seats (law/ESTATE_LAWS.md); a bare `LAW n` anywhere means ESTATE
LAW n. THE SITTING LAWS are the operator's, for the hands (law/SITTING_LAWS.md):
1 read in full or say nothing, 2 client material only when pointed at,
3 always start small, 4 Research stays clean -- no folder, no nesting,
without asking, ever. Cited as SITTING LAW n, never bare.

Ten estate laws are cited across the engine. The ones with mechanism today
(LAW 3 and LAW 4 have none; LAW 2 has a comment, not a gate):

    LAW 1  fold, never delete        memory.md, SEAT_LOG.md, transcripts append
    LAW 2  originals read-only       imports are copies; NOT enforced -- the
                                     `ground` jail contains worlds/
    LAW 5  testimony is never fact   model output tagged, never executed
    LAW 6  the gate is final         gitstate refuses commit/push; /memory stages
    LAW 7  bounded everything        skill timeout, Router cap, the ruling
                                     loop's cap, vram caps. NOT a per-seat
                                     call timeout: sitting 92, Jesster ran
                                     760s before llama-server errored
    LAW 8  ONE WRITE-PATH PER CHAIN  gate_paths() at SkillLibrary.execute()
    LAW 9  keys are silent           .env refused by name, never printed
    LAW 10 honest logs               every sitting pays its toll

## Write targets (all inside Research; stroke-enforced)

    tests/last_audit.md       THE RECORD AUDITED, not the code tested.
                              `python tests/audit_record.py` reads logs/,
                              SEAT_LOG, sessions and memory and REPORTS --
                              malformed transcripts, dangling references,
                              anything sealed left unprotected, and every
                              run whose shape a gate NOW refuses (s56, s61,
                              s68 swept retroactively). It never gates: the
                              corpus grows every sitting, so a red over it
                              would mean the operator ran the CLI.
    sessions/parity_history.jsonl  one appended line per /parity: the mean,
                              the per-reference means, and THE SEAT MAP that
                              produced them. A mean without a history is a
                              number.
    tests/run_history.jsonl   one appended line per suite run: finished or
                              CRASHED, the tally, the names that failed. The
                              stamp says where we stand; this says how we
                              got here, and it is the only one that can be
                              diffed against itself (LAW 1).
    tests/last_run.md         THE RED, ON THEIR OWN. Both suites' standing,
                              then every failure with its detail -- and
                              nothing about the ones that passed beyond the
                              count. Written by the suites; read it instead
                              of scrolling ~1,000 lines of output.
    tests/last_run.json       what the suites last proved, stamped by them;
                              the boot report reads it back and says STALE
                              when the ground changed since. NO COUNT GOES
                              IN A DOC (his ruling): the suites grow.
    logs/<stamp>_<slug>.md    per run          logs/_prompts/   prompts, apart
    sessions/sessions.jsonl   per sitting (a line per open/toll/close, so more
                              lines than sittings; the last one for an n wins)
    sessions/thread.jsonl     THE CURRENT SITTING ONLY, last 80 turns. Opened
                              "w" and rewritten each save — not a history. It
                              is 2 lines after a one-turn sitting and that is
                              correct. History is logs/.
    memory.md + memory/pending.jsonl           SEAT_LOG.md      tolls
    index/vectors.db          rebuildable      agent_workspace/ only seat-writable
    law/chain.jsonl           append-only via law.py ONLY
    rack.md · .git (local; remotes gated by CHAINKIT_GIT_REMOTE=1)

## Execution path, one turn

    input → gibberish gate → intent.names_a_tool (alias table)
          → a named READING skill on a WRITE-shaped objective is set aside
            (REVIEW_ONLY_SKILLS); the Router decides instead
          → casual check (whitelist, edit-distance 1; <40 chars, no feed)
          → spine: Steward → Router(needs_tool) → Steward(worked)
          → seating.summon() between steps: racked seats per anchor
          → EVERY seat call carries tools= for what it MAY CALL, if the
            model has the capability; native tool_calls are rendered into
            the estate's <action> block, so the loop never changed
          → tool loop, MAX_TOOL_STEPS=5, each hop gated at execute():
              caller clearance → LAW 8 path gate → SKILL_TIMEOUT → handler
          → the chosen skill's MARKDOWN BODY is injected (router prompt when
            named; follow-up hop for the skill just called)
          → flags are read, then STRIPPED from the text (strip_control)
          → delivery: spelling.check() · quote_structure() demotes ≥ h5

## Flags → seats (declared in agents/*.md, not pipelines.md)

    has_feed*  → Security Guardian (first)   *set by harness, pre-run
    suspicious → Security Guardian (again)   needs_tool → Router (spine)
    technical  → Expert Coder (after Router) hard → Reasoner (after Router)
    drifted/review → Evaluator               prose → Proofreader (last)
    deliver    → Delivery Agent (last)       worked* → closing Steward

A raised needs_tool ALWAYS reaches the Router. The sitting-48 set-aside was
dropped by operator ruling 2026-09-01 — see the fix log.

## Fix log (failure → mechanism; sitting # in the stroke's docstring)

    s5   Steward said "run it yourself"     → prompt names the chain's reach
    s5   thinking model returned ""          → _extract falls back to .thinking
    s6   commit subject = "git_commit"       → _commit_subject rejects tool-shaped
    s6   stale index.lock, invented cure     → lock_state(): path+age+del command
    s22  mash woke coder                     → gibberish gate
    s23  "cool"→"classify_sentiment"         → casual branch, roster removed
    s24  Router ignored named tool           → named_tool = DIRECTIVE
    s24  "[Router]" copied into delivery     → work record indented as quote
    s25  whisper: Stuart/Manuel/get/tall     → VOCAB_BIAS + HEARING table
    s26  search w/o query → invented person  → query falls back to objective
    s27  "whats up"→invented intruder        → NOTHING-IS-HAPPENING clause
    s28  covenant query hit intent.py        → rank: foundation+.06 us/agents+.03
    s29  "where is memory"→"All is quiet"    → question ≠ small-talk
    s30  "write a file"→small-talk           → whitelist casual (inverted)
    s31  "heloo stewy" woke coder            → edit-distance + _CODEISH gate
    s33  warm at max-declared ctx            → ONE ctx per model; warm order
    s39  injection feed moved the hands      → hard gate before any model
    s40  errored read narrated as success    → THIS TOOL FAILED banner
    s42  "exit bro" ran tools                → leave-words lexicon
    s44-48 the Modelfile detour              → REVERTED whole; NO bake dev-loops
    s47  per-chunk strip ate stream spaces   → chunks RAW, cleaned on the join
    s48  greeting reached the Router         → needs_tool set-aside gate
    s63  "remember X" staged the SAME rule   → THE DEDUP: an identical
         3x in one turn; the cap bounded        (skill, args) is refused, not
         it at 4, doing a rule's job            re-run; told once, then the
                                                loop breaks. Cap 4 -> 5: the
                                                hop buys DIFFERENT work now.
    s63  everything was stamped and the      → THE CLOCK: every seat is told
         stamps did nothing -- no seat          the date and hour, from the
         knew the DATE, so "written 2h          RUN's start so the whole
         ago" had no anchor and s26             chain agrees on "now".
         narrated an old log as news.         → the `when` skill: a PERIOD
         Nothing read stamps as a range.        resolves to its runs, by
         Retrieval showed age, ranked by         arithmetic over the log
         meaning alone.                          stamps. No model, no index.
                                              → RECENCY_WEIGHT 0.04 in the
                                                search rank, decaying over a
                                                month. Breaks TIES, never
                                                outvotes meaning; foundation
                                                exempt (old by nature).
                                                Atom = timestamp, molecule =
                                                sitting; both are kept.
    s64  CONTEXT DOES NOT CHAIN BY SUMMARY. The operator asked whether the
         chain could "expand" context seat to seat. It cannot widen a
         window; it can widen the MATERIAL COVERED, and only by map (each
         act its own full window over different material), never by reduce
         (summaries forward, which compound error -- DESIGN 11). Three
         landed, in that light:
      1  a big read was `text[:12000]`      → windowed(): part N of M with
         -- SEAT_LOG.md arrived as its         the file's own headings
         first 9% and the seat did not         mapped, a movable window, and
         feel the rest                         sections reachable BY NAME.
                                               Grammar: one tag = whole
                                               file, two = file + part.
      2  decompose_task existed and was     → a plainly multi-act objective
         never dispatched                      is routed to it first, then
                                               worked act by act. The gate
                                               errs SHUT (is_big_objective).
      3  the Evaluator could say WRONG but  → `NEEDS: <thing>` sends the work
         never UNFINISHED, so a critique       back through the Router ONCE,
         naming missing work died there        evidence carried, bounded by
                                               the same (seat, flag) key that
                                               stops a flag looping.
    s66  a bare noun claimed every sentence  → a **Says:** phrase must be two
         holding it: `index` in "new index      words or the keyword itself.
         new day" started a 326s reindex       A word is not an intent --
         that hit the timeout                  s23, s31, the `when` adverbs,
                                               and now my own. A stroke reads
                                               EVERY skill's Says so nobody
                                               can reload that gun.
    s66  an error named a cure that did      → index_ground reads `rebuild`
         not exist: "Rebuild with               from the args OR the objective
         index_ground <rebuild>" while          (the objective is the payload)
         the handler read no args at all       and actually discards the db.
    s72  a commit landed as "Committing 13   → _commit_subject refuses a
         changed files locally - master@       subject that describes THE ACT
         ff7dbe05b (chain: HANDOFF.md,         (true of every commit ever
         SEAT_LOG.md, chainkit/, sessions/)"   made), and refuses the PREVIOUS
         Two faults in one line: it says       subject whole or embedded --
         what git DOES, not what changed;      git_status prints `last commit:`
         and the parenthetical is the LAST     and the Router copied it
         commit's subject, copied forward      forward. Sitting 61's lifted
         from git_status. Sitting 6's guard    citation in a new place: tool
         caught a bare tool name; a fluent     output reused as this turn's
         sentence sailed past it.              fact. Falls back to areas().
    s71  THE ROUTER HAD NO WORLD. Operator:  → its charter now carries the
         "the router isnt taking in proper     estate: what the ground is,
         context, it's reasning with no        that facts are READ from it,
         heuristics, no meaning, or            evidence-or-silence, that NO
         overarching ideas, or vision."        TOOL is a real answer, name
         Its whole charter was three           things don't describe them,
         sentences about XML formatting        one call one purpose, the
         while the Steward carried a           operator lands -- and, plainly,
         3,400-char soul. The seat that        that it CANNOT see the
         makes every tool decision had no      conversation, with what to say
         idea what it was part of.             when an objective points at
                                               something it cannot see.
    s71  an anaphoric follow-up was sent    → asks_the_ground() refuses a
         to the reader: "what does that        short question built around
         even mean?" -> semantic_search,       that/it/this. It points at the
         and the Router answered "there is     CONVERSATION, and the Steward
         no prior exchange and nothing to      is the seat that holds it.
         refer to as 'that'". Correct, and     A LONG question that merely
         it should never have been asked.      contains one still dispatches.
    s70  SPEAK LEFT NO WORDS IN THE RECORD  → speak() returns what it said.
         -- "Spoke 311 characters aloud"      The operator: "pretty
         and nothing else. The one output     concerning in and of itself."
         that reaches the operator THROUGH    It is. A spoken run could not
         THE AIR left a receipt.              be reviewed at all (LAW 10).
    s70  a closer invented a yesterday:     → THE WRITE-CLAIM CHECK, the
         "Yesterday I compiled a poem...      claim-check's sibling: a seat
         saved it as 'poem.txt'... read it     says a file was written, the
         back to you". No yesterday, no       turn's tool calls say whether
         file, no reading. claim-check        a writer ran. WRITING_SKILLS
         wants a CONTENTS claim; citation-    is maintained beside
         check wants a result. Neither saw.   REVIEW_ONLY_SKILLS.
    s70  prose passed as a path, 3rd time   → gate_paths() refuses a value
         ("list available files in            of 3+ bare words with no
         ground"). Refused downstream with    separator and no extension,
         "is not a folder" -- true and        AT DISPATCH, and names what a
         useless.                             path looks like.
    s70  <action> tags streamed to the       → the streaming sink is a
         terminal live, between two tool      one-character state machine:
         lines. strip_control keeps them      nothing between < and > is
         out of the RECORD; nothing kept      printed. Tags split across
         them off the SCREEN.                 chunks, so no regex would do.
    s69  asking ABOUT a tool RAN the tool   → intent.asks_about_a_tool():
         -- "what does deep research do?"     an ABOUT-frame question about
         matched the spaced keyword and       a named skill is answered from
         dispatched                           its own markdown by
                                              `skill_search`, never obeyed.
                                              Orders keep dispatching; a
                                              question mark does not make an
                                              order a question.
    s69  `worked` was raised by a Router     → `route` dropped from that
         that called NOTHING, so the          test. A ROUTER THAT ROUTED
         closer announced work: "Deep         NOTHING DID NOTHING. Transform
         research conducted an intensive      seats keep the rule (producing
         analytical evaluation", past         the content IS their work);
         tense, over an empty run             the coder lands files and
                                              raises `review` instead.
    s69  THE SHORTLIST, on a budget          → SkillLibrary.shortlist(): the
         argument, not an accuracy one.       ~6 closest skills at ~300
         Accuracy was MEASURED unnecessary    chars each, scored by word
         (79% deterministic). But the         overlap over their own words --
         Router's prompt hit its ceiling      arithmetic, no embedder. EVERY
         twice in a day, and every            other skill still travels BY
         description was cut to 112 chars     NAME, so nothing is hidden and
         -- the whole library paying for      the Router may still call
         total irrelevance.                   anything. Advisory, like drift
                                              and parity: measures, never
                                              rules. Falls back to the whole
                                              manifest on a wordless
                                              objective or a small library.
    s68  SCOPED SUB-RUNS, the map half.     → `subtask`: one objective, its
         A turn's single window was being      own RunContext, its own full
         asked to hold everything, and the     window; only the RESULT comes
         alternative -- summarising            back, marked as another seat's
         forward -- compounds error.           words. BOUNDED: depth 1, three
         The seed already existed: an          per turn, refused by
         @-addressed seat whose exchange       arithmetic. ITS FAILURES ARE
         never entered shared dialogue.        THE PARENT'S -- lifted up so
                                               the recompose carries them,
                                               or a sub-run would be a way
                                               to launder a failure out of
                                               the answer. env.sub_run is
                                               INJECTED by the pipeline;
                                               skills.py never imports it.
    s68  RECOMPOSE. Twice the delivery       → recompose(): if anything failed
         contradicted its own record            this run, the delivery carries
         WITHOUT INVENTING ANYTHING:            the list, machine-emitted from
         s66 "the card is comfortable and       what was recorded AS IT
         functioning optimally" over 0.0GB      HAPPENED. Not a seat -- a
         headroom; s68 "no new issues or        model summarising and dropping
         concerns" over a 326s timeout          failures IS the disease. No
         under a FAILED banner.                 reading of prose, no all-clear
         OMISSION, not invention: the           detection: the facts travel
         claim-check needs a citation and       every time, and an honest
         the citation-check needs a result.     closer is merely corroborated.
    s64  prompt skills never saw the clock   → now_block moved to context.py
         (they run OUTSIDE build_prompt:        (imports nothing of ours) and
         body as system, payload as user),      prepended to a prompt skill's
         so time_align promised to find         payload. ONE clock in the
         what is OVERDUE while forbidden        ground, both paths. Its md now
         to know today's date                   uses the given date, never one
                                                from memory.
    s64  bare adverbs dispatched `when`     → every alias carries a VERB:
         ("yesterday was rough..." would        "ran/did/happened yesterday".
         have listed transcripts)                A word is not an intent --
                                                s23 and s31's fault again.
    s63  "review sitting 63" found nothing   → the `sitting` skill: a NUMBER
         -- runs are filed by timestamp,        resolves to its runs and
         sittings are numbered, nothing         their transcript paths, read
         mapped one to the other. The           from the one SEAT_LOG block
         Router guessed logs/sitting_63.md      that owns it (the file is
         and passed sentences as filepaths.     136KB; reading it whole is
         Every guess refused correctly --       not a sane call). An unpaid
         guarding a guess is not answering.     toll is SAID, never invented.
    s63  a seat's paraphrase read as file    → THE SEAM: tool results and the
         content (both demoted to h5)           seat's reading of them are
                                                split by a named line. LAW 5
                                                at the join.
    ---- 2026-09-01, sittings 51-55 --------------------------------------
    s48's gate ate CORRECT flags             → SET-ASIDE DROPPED (operator).
         ("try speaking…", "condition of        Its evidence was names_a_tool,
          the dir" — no Router, no tool)        the same lookup that routes: a
                                                gate cannot be tuned out of
                                                citing its own miss.
    "write a note about the rack"            → a READING skill is never
         dispatched to rack_list                dispatched on a write-shaped
                                                objective (REVIEW_ONLY_SKILLS)
    Router returned "" (11s, 5s)             → s5c's fallback existed only on
         thinking model, 400-tok cap            the NON-streaming path; s47 had
                                                dropped the thinking chunks it
                                                needed. Kept, never shown. Cap
                                                400→900, stroke now two-sided.
    seat markup delivered verbatim           → strip_control(): flags are read
         (`<flags>needs_tool</flags>`)          then removed; a markup-only
                                                reply is a NAMED FAULT
    5 of 26 handlers jailed their paths      → LAW 8: gate_paths() at execute(),
         nothing told "no path" from "forgot"   on the DECLARED arg (**Path
                                                Args:**), + a stroke reading
                                                skills.py's own source
    bespoke XML asked of a tools-trained     → native tool_calls rendered INTO
         model (DESIGN.md §4 chose it for       the <action> block; XML kept as
          coder:1.5b and named the risk)         the fallback; supports_tools()
          the risk)                             fails closed
    any seat could call anything             → **May Call:** per seat. Absent =
                                                NOTHING. Grant by omission from
                                                tools=, enforce at dispatch.
    Router told WHAT, never HOW              → the chosen skill's body injected
         (130-char truncated manifest)          (~100 tok), not all 31 (~4,000)
    execute() had no timeout at all          → SKILL_TIMEOUT, daemon thread.
         (voice 180s, gitstate 60s)             Bounds the WAIT, not the work —
                                                stated in the code, not hidden.
    estate ran Manjuel 4th, before Jesster   → Manjuel last, as in `court`
    ---- 2026-09-02, an outside hand — NOT sitting 59 ---------------------
         (this work took no sitting and no session line; "s59" in the
          stroke comments below means this entry, not the REPL's 59)
    a /model override was written into       → rack.survey() reads
         rack.md AS the declaration. s57         registry.declared_models(),
         showed all 15 seats on gemma4:12b       never all(); an active
         and filed the Router, the Reasoner      override is REPORTED in the
         and others under "weight you may not    file instead. The registry
         have meant to keep."                    keeps what agents/*.md
                                                 declares apart from what the
                                                 seats are running.
    smoke's StubRuntime.chat took no         → signature mirrored, plus a
         tools=, so every REPL turn raised       supports_tools(). 34/50 -> 59/59.
         TypeError. RED since 14e2711 and        HANDOFF claimed 59/59 for a
         the strokes stayed green throughout.    suite that had not passed.
    a bare `y` meant for the confirm landed  → _toll_answer() re-asks on a
         in "What proved?", which becomes        yes/no; blank still skips, and
         the SEAT_LOG heading (28, 41, 42,       the prompt says "text, not y/n".
         44 and 58 are titled y or n)
    two tolls for one sitting came out       → render_toll marks the second
         byte-identical in the head (s57)        "(re-tolled)" and says the
                                                 earlier entry stands (LAW 1).
    ---- 2026-09-02, an outside hand, group B ----------------------------
    rack_report returned ONLY the seat's     → the observed inventory now
         prose under a `Tool executed:`          travels WITH the reading and
         label. s59: the Quartermaster           the join names which half is
         renamed qwen3.5:4b/:9b to               which. Facts first, so a
         qwen2.5-coder:4b/:9b, dropped ten       truncated read still gets
         models incl. its own, put               them. LAW 5 at the boundary.
         phi4:latest in VRAM when it was
         not, invented a VRAM total — and
         the Router reasoned on all of it.
    s56: a seat presented a file's           → THE CLAIM-CHECK.
         contents with no read this turn         intent.claims_file_contents()
                                                 + a gate after strip_control:
                                                 claim + no reader this turn =
                                                 named fault, claim refused.
                                                 Narrow BY DESIGN — it wants a
                                                 CLAIM, not a mention.

    ===== SESSION 2, 2026-09-03, sittings 75-81. ONE FAULT, TEN COSTUMES: =====
    ===== a guard that checked one thing when it needed one thing more.   =====

    s79: "good morning, sunshine, how      → THE GREETING FAMILY. The lead
         are ya?" went to semantic_search      set held morning/evening/
         and cost 155 SECONDS. The lead        afternoon and the test read
         set could never be reached            words[0] -- and `good X`, the
         because the family leads with         commonest form in English,
         `good`.                               leads with `good`. Reads the
                                               first TWO words now.
    s81: "thank you for the clarification, → _after_courtesy(). The MIRROR
         where do i find a list of the         of the greeting bug: a polite
         tools" dispatched NOTHING, and        preamble moves the question
         the Steward answered a question       off words[0], and someone who
         from two turns earlier while          opens with "thanks" rarely
         inventing a file's contents.          closes with "?". ONE clause,
                                               from the front only.
    s77: the Router called list_directory  → THE SIGNATURE IS THE DECLARED
         TWICE in one turn and both ran        CALL. SkillSpec.declared_args
         -- the dedup keyed on what the        reads a skill's own
         MODEL EMITTED, so an argument         **Parameters Needed:** line.
         the skill DOES NOT HAVE made two      An undeclared argument cannot
         identical calls look different.       vary a signature. It caught
                                               test_tool_loop's own fixture
                                               making that same mistake.
    s77: `ground_list` got the whole       → the refusal names WHICH mistake:
         objective as a folder name and        "a folder NAME was expected,
         the honest refusal was READ AS        not a sentence ... this says
         a verdict -- the Router concluded     nothing about whether that
         /skills might not exist, with 3       folder exists -- it was never
         hops left and the fix written down.   looked up."
    s81: the Steward tried TWICE to hand   → A MALFORMED FLAG IS STILL MEANT.
         off and both died on a MISSING        _FLAGS_RE required </flags>, so
         SLASH: `needs_tool` was emitted,      an unclosed tag was invisible
         never rose, the Router never woke     to read_flags AND unstripped by
         -- and the raw markup went to the     strip_control. One character
         operator, undoing sitting 42.         undid two rulings. Three shapes
                                               now, BOUNDED to 80 chars and no
                                               newline so a stray tag in prose
                                               eats one run, never the answer.
    s78: `worlds/manjuel` came out of      → PRUNE ASKS TWO QUESTIONS: is the
         index_roots.txt and 91 of 801         file gone, AND is its root still
         docs from that world STAYED and       declared. Matches on the PATH,
         kept answering -- prune asked         never the stored `root` label.
         only "is the file gone?" and          GATED at 25% of the corpus
         every file still existed.             (operator's ruling, option c):
                                               a bigger eviction is REFUSED and
                                               reported, because a typo in a
                                               config file must not silently
                                               empty the index.
    s80: two commits carried INVENTED      → THE SUBJECT IS THE OPERATOR'S OR
         subjects -- "add git repository       GIT'S, NEVER THE MODEL'S. The
         initialization and basic ignore       three older guards ask if a
         rules" over a one-file                string is DEGENERATE; none can
         sessions/thread.jsonl diff, and       ask if it is TRUE. And the
         the Router's COMPLAINT about the      arithmetic version does not
         request committed as history.         work: matching subject words to
                                               changed paths refuses "fix the
                                               greeting dispatch" as fast as
                                               it refuses a fabrication. So
                                               <content> is no longer a
                                               candidate (LAW 5), and the
                                               fallback is fact read from git.
    s80: git_commit's "1 changed, 0        → SAY WHICH DIRECTION THE COUNT
         untracked" means WHAT WENT IN and     POINTS. git_status carries its
         the Router read it forward: "the      own disambiguation line; this
         repository shows one file changed     had none, so the ambiguity was
         since this commit was made."          the TOOL's, not the seat's.
    s81: `index_ground rebuild` WORKED     → THE MODE, IN THE FIRST LINE, as
         -- 733 docs, the world evicted --     a word and not an inference.
         and BOTH seats told the operator      The "Rebuilt from scratch"
         it had not. The banner was            banner was appended to `lines`,
         appended to `lines`, which is the     which idx.build() takes as its
         report callback and never read        report callback and nothing
         again. COLLECTED AND DISCARDED.       reads after. Result now reads
                                               REBUILT or Refreshed, and says
                                               why `unchanged` is 0.
    s81: parity printed the reading        → render() READS THE SEAT MAP.
         BACKWARDS on both models that         The test was `model ==
         mattered: llama3.2 (named by          DEFAULT_REFERENCE_MODEL`, a
         nothing) labelled "same model as      constant still naming llama3.2
         the seats", phi4-mini (eleven         from when it was the spine.
         seats) labelled "the seats fell       stamp() already took the real
         short" -- the opposite of what        map; render() inferred. It reads
         this module's own docstring says      now, counts how many seats run
         that number means.                    that model, and says UNKNOWN
                                               rather than guess when given
                                               none.
    ---- and the two that are not fixes, but the same shape one level up ----
    s78: us/*.us DECLARED what every       → chainkit/us.py: PARSE and
         skill may reach and NOTHING            RECONCILE. Nine comparisons,
         CHECKED IT. 20 of 35 skills had        report-only. Proved against the
         no record at all; 10 of 11 seat        OLD manifest -- 41 findings
         records named a model the seat         there, 1 here. `speak` reaches
         had not run in weeks; the ROUTER       the OS temp dir and spawns
         declared `read: agent_workspace        PowerShell and nothing had
         only` while cleared for `all`.         declared it; `subtask` opens a
                                                NESTED RUN, bounded by depth
                                                and not by path. `permission`
                                                is now DERIVED from May Call
                                                plus each skill's wall, never
                                                asserted beside it.
    s81: an agent grepped parity.py and    → SITTING LAW 1, the operator's word:
         asserted about it; told the            NEVER ASSUME ANYTHING ABOUT A
         operator the parity had never          FILE NOT READ IN FULL. Both
         run while parity_history.jsonl         claims were disprovable from
         held it; left the world-eviction       disk. The engine cannot gate an
         task open after he had done it.        agent working from outside --
                                                what it can do is keep the
                                                receipt, which is how he caught
                                                it. `COVERAGE, NOT EXISTENCE`
                                                is the in-chain half and is on
                                                the TASKS list, not built.

## Config surface (markdown only — touching chainkit/ for these is wrong)

    agents/x.md      Model Target/May Call/Wakes On/Wakes/Stage/Context/Max Tokens
    skills/x.md      Action Keyword/Description/Params/Path Args (+Model Target)
                     **Says:** phrases this skill answers to -- read by
                       names_a_tool beside the table in intent.py. A phrase
                       that is one skill's business belongs HERE, in the file
                       a person edits; the table keeps only what belongs to
                       no single skill (here-words, cross-skill vocabulary).
                     **Takes:** words | more words -> content|filepath
                       The payload survives recognition. Before this, matching
                       a keyword threw the rest of the sentence away, so
                       `index_ground rebuild` could not obey `rebuild` however
                       the handler was written. Fills only what the seat left
                       empty -- a floor, never an override.
    pipelines.md     spine per pipeline; racked seats NOT listed
    commands.md      /palette additions. **Runs:** = objective shortcut, with
                     $ARGS filled from what you type after the command (or
                     appended when the token is absent). **Method:** on its
                     own line = everything after it rides with the run and is
                     shown to EVERY seat, labelled as the operator's
                     instruction. Same marker convention as **System Prompt:**
    parity.md        cases; **Model:** per-case reference; **Expect:** refusal
    index_roots.txt  index scope (Research-relative only)
    .env             CHAINKIT_VRAM_GB, CHAINKIT_KEEP_ALIVE, CHAINKIT_GIT_REMOTE,
                     CHAINKIT_SKILL_TIMEOUT, CHAINKIT_WHISPER_*,
                     CHAINKIT_LOG_HORIZON_DAYS (45; 0 = index every
                     transcript forever)

## Pattern: adding a seat (no engine change)

    ## Auditor
    - **Model Target:** phi4-mini:latest
    - **May Call:** read_file, list_directory, git_status   ← absent = NONE
    - **Wakes On:** audit            ← flag(s), comma-separated
    - **Wakes:** after Router        ← first | last | after <Seat>
    - **Stage:** transform           ← guard|transform|route|gate|deliver
    - **On Fail:** skip              ← abort|skip|prompt
    - **Max Tokens:** 600            ← cap it, but leave room to think AND emit
    - **Context:** 8192              ← num_ctx drives VRAM: 986MB@32k = 4.2GB
    - **System Prompt:**
    You are the AUDITOR...

    /reload. registry.py refuses bad anchors AT LOAD with the seat named.
    Fields are `- **Key:**`. Duplicate seat name = refused, both files named.

## Pattern: adding a skill

    Prompt skill (no python): add **Model Target:** — the md body IS the
    system prompt. Handler skill: md declares, python binds:

    @skill("audit_ground")                      # in chainkit/skills.py
    def _audit(env: SkillExecutionEnv, args: dict) -> str:
        thing = (args.get("content") or env.objective or "").strip()
        path = env.safe_path(name)              # workspace jail (writes)
        path = _inside_ground(env, rel)         # ground jail (reads)
        return "..."                            # strings only, errors as prose

    IF IT RESOLVES A CALLER'S PATH, DECLARE IT:
        - **Path Args:** filepath -> workspace
    A stroke reads skills.py's own source and goes RED if a handler calls
    safe_path/_inside_ground without a declaration. Argument NAMES lie:
    `remember`'s <filepath> is a title, `rack_load`'s is a model tag.

## Prompt rules for small seats (every one learned from a failure)

    1. NO quotable example utterances. State constraints; never give lines.
    2. Format-to-mimic must be unmimickable — work records are INDENTED.
       phi4-mini copied the `steward:`/`operator:` dialogue format and
       invented eight turns of conversation. Same family as s24.
    3. Label material vs furniture explicitly.
    4. Scope negative rules to 3 named things max.
    5. One rule, one statement. Contradictions must resolve into precedence.
    6. Anchor phrases the strokes grep live in prompts — search tests before
       rewording. Wrap-safe: `phrase in " ".join(prompt.split())`.
    7. The models' native word is TOOL (Ollama's API field, their training).
       `skills/` is the folder a PERSON edits; prompts say tool.

## Test discipline (the suite IS the memory)

    - stroke BEFORE "fixed". Reproduce → fix → green.
    - superseded ruling: REWRITE the old stroke, note why, KEEP THE GUARD.
      Three moved this sitting: the collapse-to-basename traversal stroke,
      the Router's one-sided token cap, the llama3.2 foreign-model fixture.
    - a stroke that reads the AMBIENT environment tests the environment.
      test_ink() read the real stdout: green piped, red at a terminal, for
      weeks. It now FORCES the condition.
    - fixtures must mirror the real thing. env_for() once omitted skills_ref
      and a guard tested green while dead; Stub had no supports_tools() and
      would have hidden the whole native-tools path.
    - make strokes DISCRIMINATING: the stub embedder scores by bag-of-words
      over VOCAB (grep `VOCAB =` in test_chainkit.py) — pick fixture words ON that vocab.

## Debugging a sitting

    1. logs/<stamp>_<slug>.md — flags, notes, per-stage output. "rack: X (on
       flag)" = who was summoned why. "set aside" = a flag was discarded.
       "LAW 8 gate refused X" = a path was stopped at the chokepoint.
    2. logs/_prompts/ same stamp — EXACTLY what each seat saw.
    3. sessions/thread.jsonl — what the dialogue carried (fiction compounds).
       ONLY for the sitting that just ran; it is overwritten, not appended.
       For any earlier sitting the dialogue is in logs/ and nowhere else.
    4. Fix at the CHEAPEST layer that holds: alias/gate (intent.py) > skill
       output wording > prompt > model size. Model-size is last and needs the
       operator (memory.md: evidence first, always start small).
    5. CHECK THE DISK BEFORE THE TRANSCRIPT. A seat's account of what it did
       is testimony (LAW 5). `WHAT RAN (observed)` and the file itself are
       the facts.

## HANDOFF FOR 2026-09-09 — read this before anything below it

**THE FRONTEND IS UP AND THE GLASS REACHES THE COUNCIL. atlas-mcp on
:8090, atlas-webapp on :8091. /chat sends an OBJECTIVE into the world's
own Manjuel process over PROTOCOL 1, so the law gate stamps it, the one
Router runs the tools, the dedup refuses a repeat and the recompose puts
every failure in the delivery. Chat is the conversation; Evals is the run,
whole -- every seat, every tool, every result, the per-seat table, the
transcript. Both read one `Run` object, so they cannot disagree about what
ran. Proven live: delivered at 53.4s, 248 events kept, Router shown
skipped in the seat table.**

**THE VIBE CODING LOOP LANDED THE SAME DAY.** `run` is a flow node kind: it
drives a whole Manjuel turn, where `ask` reaches a bare model. A `run` node
will NOT start an engine -- that would open a sitting he never opened.
Gate titles render, so `{{out_work}}` puts what the council produced into
the question he walks back to, and `flow_status` prints it whole with the
exact `flow_resume` line under it. Proven: PAUSED at the gate in 4.1s, read
back intact AFTER the door was rebuilt and restarted, `continue` ->
COMPLETE at 7.8s. SPEC_CONTROL_CENTER 4.9.

**MANJUEL WAS NOT TOUCHED for any of the above.** Every change is in
`atlas/`. The one edit outside it is the version string.

**0.1.6: THE STRINGS AND THE CHECKPOINT ARE CUT; THE TAG IS NOT.**
`manjuel/__init__.py` and `pyproject.toml` now read 0.1.6 (they carried
0.1.4 while 0.1.5 and 0.1.6 were built -- LAUNCH_PLAN's step 5), and
CHANGELOG's Unreleased folded down into `## 0.1.6` per its own convention.
**RESTART REQUIRED**: a running REPL read the version at import.

**WHAT THE GATE STILL REFUSES, and it is right to.** `python
tests/release.py --check 0.1.6` -> standup. Strokes (1858/1858), smoke
(60/60), buildmap, law (9 strokes), manifest, spec and daybook are green
and fresh. The standup's newest LIVE line is 9/10 from 2026-09-08 12:44,
failing the case **"a folder"**: "what is in the skills dir" did not reach
`ground_list`. That is a live ROUTING miss in the core, it predates today,
and it has blocked 0.1.5 and 0.1.6 both. It is the last thing between this
ground and a tag. Fixing it means touching the Router's routing -- the
operator's call, not a hand's.

**KNOWN AND UNTOUCHED, neither of them code.** `atlas/tests/fixtures/
rack_open_ground/` came over from the H0 pull EMPTY, so `internal/rack`
fails four strokes; `cmd/atlas-door`'s prove stroke needs the Rust spine
built (`cargo build -p atlas`) or `ATLAS_BIN` set.

**THE REPO.** `origin/main` and local `master` are squared, zero
divergence, zero attribution, and zero vault files. The local history that
carried `worlds/tbc/vault` in seven old commits is kept as
`pre-strip-master` and is NOT what is published; the published line is the
clean one. Do not force-push `pre-strip-master`.

## HANDOFF FOR 2026-09-08 — read this before anything below it

**Newest first (12:45–): 0.1.6 IS BUILT but for his seal. THE STORY:
the ledger line carries tools/guards/failed seats/delivery; the door and
the court are handed "The sitting so far"; "what happened?" is the
door's. THE HANDS LEDGER: sessions/hands.jsonl; `python -m
chainkit.seatlog hand-open|hand-close|hands`; the brief shows the last
hand; the gate refuses over an open one. The two laws are DRAFTED in
DAYBOOK Session 6 for his names and his seal. MEASURED before it:
sitting 98's live standup on 0.1.5 -- the court seated all six and
ruled in 300s; 9/10, the miss the number check catching "35" for 37.
1825 strokes. RESTART REQUIRED. Neither 0.1.5 nor 0.1.6 tagged: the
gate wants a live 10/10 and a closed hand. Below this line is earlier.**

**Earlier (late afternoon): 0.1.5 IS WHOLE ON DISK, RESTART
REQUIRED, NOT TAGGED. The P0 of the review is built (CHANGELOG "0.1.5
TIED UP"); his numbers are on every seat by model size (150/300/600/
700; ceiling 700; the turn 600; twelve ruling turns). What the tag
waits on: restart -> the standup live (the court must seat all six with
Manjuel last inside 600 -- Jesster 600 is the seat to watch; if he eats
the turn, his number is the operator's to lower) -> `python
tests\release.py --check v0.1.5` on his terminal -> the tag. Then 0.1.6.
Archive/atlas holds the webapp end (his word); outside the ground;
untouched. Below this line is earlier today.**

**Earlier (afternoon): 0.1.5 RAN LIVE in sitting 96 -- the standup
10/10, Jesster cut at 577s, Manjuel OUT OF TIME -- and the whole record
was then reviewed on his word. The tag now waits on the P0 list in TASKS
"From the review of 2026-09-08": his court numbers (Neiro/Jesster/
Manjuel inside 600 with the Router), the standup judging seats and
failed stages, a failed seat in the delivery, the refused feed out of
the transcript and the index, the unknown skill name. SPEC 7 is the
deliverable. Nineteen doc lines fixed against the disk; RUNBOOK carries
every dial. Below this line is the morning.**

**Earlier: 0.1.5 IS BUILT (afternoon, on "go for it"), RESTART
REQUIRED, NOT TAGGED. On disk, uncommitted: the release gate
(`tests/release.py --check`, new file, reads only); the turn deadline
(600, OUT OF TIME in the delivery); one index build at a time and a
rebuild that refuses a held file; the watcher deaf to the chain's own
writes; one git read at open; `/toll` then exit = one closing line;
an escape still closes; `/chat` ends on a dead mic; a palette command
cannot run a command; git_pull/push are writers. 1751 strokes, smoke
60, buildmap. CHANGELOG (the 0.1.5 entry), REFUSALS §21, RUNBOOK ("A
seat, or a turn, ran out of time"; "Before a tag"), SPEC 4.6 + the
words, TASKS (eleven items ticked). His numbers landed earlier: ceiling
600, Steward 150, Router 300; the ledger out of git (his `git rm
--cached` done). What the tag waits on: restart; one sitting that
measures a seat cut at its bound and a turn cut at 600 (a court is the
natural case); the standup live; then `python tests\release.py --check
v0.1.5` on his terminal, green; then his tag. Before that: the seat
bound and the turn deadline have NEVER RUN LIVE. `master@baa4f32` is
still HEAD; sitting 95 was his last (13 runs; `time align the logs`
1858s, unread by any hand).**

**Where the ground stood at open.** `master@66f5e1376` after the operator's
commit in sitting 94 (07:31–07:52, his; the brief's first live run, a
commit, two index_ground rebuilds). His toll: proved "the brief ran, kind
of"; thin "timeout, as stated previously"; owed "reviewing if the memory
landed". The first `index_ground rebuild` ran 320s against the 300s skill
bound and was refused; the second, 8 minutes later, FAILED in 39s --
`Indexing failed: UNIQUE constraint failed: docs.path`
(logs/2026-09-08_074949_*.md line 28) -- while the first was still
running behind its refusal (`_run_bounded` cannot kill a thread), both
writing one vectors.db, and `rebuild`'s unlink swallowed on the held
file (skills.py:2121-2125). The Router then spent four more tools
guessing at the cause. THE INDEX IS NOT KNOWN CLEAN: whether the first
thread finished, and what the db holds, is unmeasured -- the next
`index_ground rebuild` from a fresh REPL (no thread behind it) says.
memory.md's tail
carries the landed entry (2026-09-08T14:51, provenance OPERATOR) -- the
memory LANDED, and what it holds is worth his eye: the `kind:` line is
his whole typed phrase ("outcome failed due to timeout, as stated"), not
a kind; the entry names the 44s run's transcript while describing the
320s failure; the body says the same sentence four ways; and its failed
tool is `read_file` on `ground/index_roots.txt` -- the jail's name on a
WORKSPACE path (unjail strips it for the ground reader; the workspace
reader still takes it).

**Built 2026-09-08 (RESTART REQUIRED): THE SEAT BOUND.** His number: 900s.
`runtime.SEAT_TIMEOUT` (900; `CHAINKIT_SEAT_TIMEOUT` moves it) and
`SeatTimeout`, a RuntimeError_. Two halves: httpx's read timeout on the
transport (a seat that answers nothing; connect held at 10s) and a wall
clock on the stream that CLOSES it at the bound (a seat that never stops
answering -- Ollama stops generating). One named refusal, the skill
bound's twin, and on-fail: skip goes on without the seat as it did in 92.
A seat may declare `- **Timeout:** N` in agents/*.md beneath the ceiling
(registry; parsed like Context); one transport per distinct bound, made
once. No agents/*.md changed -- the per-seat numbers (his shape: Router
300-600, Steward 180-300, the court 600-900) are his to write, and they
hot-reload without a restart. 1697 strokes, smoke 60, buildmap
regenerated. NOT MEASURED LIVE: the first court after the restart is
the measurement -- does a seat that hangs get cut with the refusal in
the record, and does a healthy court run unchanged.

**Open, in the order they matter.** (1) THE SITTING STORY, his "story
loop" -- after the index comes back clean, his word. His shape, 2026-09-08:
a per-session context window, calling out to the local index (which
already re-indexes at every open and names what is dirty). (2) The
per-seat numbers. (3) The door's keyword bait ("can you hear me"). (4)
The Router's "I wrote memory.md" line. (5) `rack rebuild` alias. (6)
Workflows, after the brief runs clean twice -- it has run once, "kind of".

---

## HANDOFF FOR 2026-09-07 — read this before anything below it

**Where the ground stands.** `master@0917c6d4a`, clean at open (Monday
08:xx). The last work was sitting 87, Thursday night 2026-09-04 22:14–23:16
(17 runs, the operator's) -- the record says Thursday, not Saturday. Version
0.1.4. Nothing has run since.

**Sitting 87, read in full 2026-09-07.** Seven findings in TASKS, "From sitting 87".
The two that matter most: a FOLLOW-UP loses the thread because the door is
skipped and the Router cannot see the dialogue ("needs more context" --
the toll); and THE HAND'S OWN SCAFFOLD GUARD discards a seat's real answer
when it quotes a recalled turn, and loses the raw text. Manjuel on gemma
did not rule for the second sitting running. Jesster on deepseek argued a
real counter-position for the first time.

**The `build/` folder.** Not new: created 2026-09-03 10:37 by
`pip install .` (setuptools' build dir) in sitting 80's window, when
pyproject landed. Gitignored (.gitignore line 41), untracked, and STALE --
it holds a 0.1.0 copy of chainkit with no us.py and no lawgate.py.
Harmless; regenerated by any `pip install .`; safe to delete, the
operator's call. `chainkit.egg-info/` is the same story.

**Built 2026-09-07, all RESTART REQUIRED, none measured live yet.**
Fix 1-3 from sitting 87 (the follow-up keeps the door; the scaffold guard
narrowed and keeps its evidence; a flag mentioned is not raised). Then, on
the operator's ruling on gemma and "implement the CLAUDE.md system into
the chain": Manjuel at Context 16384 with THE RULING LOOP (three turns,
thinking off on the retry; the Router is never looped); the law block in
the SYSTEM role, the ten verbatim for the court; THE STANDING from
DAYBOOK's last entry to the door and the court; THE PARTIAL-READ STAMP
in the delivery. REFUSALS §20, CHANGELOG 2026-09-07 (two entries), 1589
strokes on the mirror. The first court after the restart is the
measurement: does Manjuel rule on turn 1, 2, 3, or not at all, and does
any seat recite the law from its system role.

**Sitting 88 measured it (09:06).** Manjuel ruled on turn 1 at 16384
(237s, 27.7k chars thinking); the law was not recited; the stamp fired.
The Router's paths were the whole fault list, and one guard ate evidence.
Built the same morning (RESTART REQUIRED): `unjail`; the named file
checked and handed (`RunContext.named_file`); `find_by_name` in the
"not a file" error; `_refuse_testimony` keeps results under a refused
claim. 1612 strokes on the mirror.

**Built the same afternoon (RESTART REQUIRED):** `inspect`, "remember
that" + kinds, the brief (`/brief`, and its facts at every open), the
words in SPEC. Not yet run live. The first sitting after the restart
measures the brief: does the door say the day without inventing, and does
"remember that" land what he meant.

**Sittings 89–93 (09:42–12:10), and what they measured.** 89 (his):
"rack rebuild" twice -- no alias, the door invented (git_status, "a
workflow file in the sitting 87 record"); "thank you. good job remember
that!" -- the door answered the PREVIOUS question, the closer recited its
own instruction back ("a description or an opinion ... past tense"). 90
and 91: the standup 9/10, the same case -- `what is in the skills dir` --
which the engine dispatched right and qwen3.5:4b overrode; THE DECIDED
CALL was built for it. 92: 10/10; Jesster died at 760s on a llama-server
500 (no per-seat timeout); Manjuel ruled without him in 185s. 93 (his):
"can you hear me" went to the reader and the Router called `speak` with
nothing (84s); "what happened, why did you suck so bad" got 100s of
semantic_search and a delivery calling him "the operator" -- no seat is
handed THIS sitting's runs, which is the sitting story, not built. His
toll: proved "the standup is 10/10"; thin "speaking now"; owed "the vibe
code loop".

**Where the ground stands at close.** `master@f1da1a4c3`, one file dirty
after his commit plus this pass. Built today, all landed by him except
the last pass: fix 1-3; the ruling loop and Manjuel at 16384; the law in
the system role and the ten for the court; the standing; the partial-read
stamp; the paths (`unjail`, the named file, `find_by_name`); a refused
claim keeps its evidence; "what is in the X dir" is a listing; THE
DECIDED CALL; `inspect`; "remember that" + kinds; the brief (`/brief`);
the words in SPEC. 1685 strokes, smoke 60, standup dry 10, buildmap
clean, the manifest 51 records.

**Open, in the order they matter.** (1) A PER-SEAT CALL TIMEOUT -- LAW 7
has one for skills and none for a seat; the number is the operator's.
(2) THE SITTING STORY -- what this sitting has done, handed to the door
and the closing seat, so "what happened?" is answerable; the learning
loop's first piece. (3) The door's keyword bait, FIFTH sighting ("can
you hear me" -> the reader -> `speak`): a short question about the seat
itself is conversation. (4) The Router's "I wrote memory.md" habit (three
courts running) -- a line in its prompt. (5) "rack rebuild" -> rack_sync
alias. (6) TASKS "From sitting 86": rack_report's reading; the door
copying the record's labels; the guard for a recited law block (not until
measured -- none recited in 40 runs since the system-role move). (7)
Workflows, after the brief runs clean twice -- it has not run live yet.

---

## HANDOFF FOR 2026-09-04 — read this before anything below it

**Where the ground stands.** `master@63fab9e`, tagged v0.1.4, clean at the
time of writing except what CHANGELOG / Unreleased lists. Strokes
1471/1471, smoke 59/59 (sandbox, stand-in ollama — the operator's terminal
is the proof). Law chain 4 links. Index 753 docs / 3,172 chunks (rebuilt
again in sitting 84, 08:52). rack.md re-taken 08:51 in sitting 84 -- BUT
with the intermediate seating (Steward gemma, Manjuel qwen9b); the final
seating landed after it, so `rack_sync` is owed again.

**What landed today, in order.**

    07:xx   DAYBOOK Session 4 opened. The whole record read in full by seven
            hands: 599 transcripts, SEAT_LOG, sessions, memory, law,
            foundation, agents, skills, us. Findings in DAYBOOK s4 (two
            Found blocks). CHANGELOG.md written from sitting 1. → cefdec0,
            tag v0.1.3.
    07:42   SITTING 83 (the operator): a question about the changelog and
            the laws (closing seat fabricated; two tool refusals held),
            index rebuilt, commit. → 7ed80f0.
    08:01   THE DOC SWEEP: ~40 stale lines across 14 files corrected; see
            CHANGELOG v0.1.4 / Fixed. → 175b545.
    08:21   THE LAW: law/ flattened (was law/Archive/law + law/state/law,
            inherited from the old core\ layout); ESTATE_LAWS.md and
            SITTING_LAWS.md written and SEALED by the operator; CLAUDE.md
            READ FIRST block + RULE 8; version 0.1.3 → 0.1.4. → 63fab9e.

**Rulings today (the operator's).**

    - Two families of law. ESTATE LAWS (the ten, for the seats): a bare
      `LAW n` means ESTATE LAW n. SITTING LAWS (for the hands): cited
      SITTING LAW n. Four: read in full or say nothing; client material only
      when pointed at; always start small; NO FOLDER, NO NESTING, UNASKED.
    - law/ is flat.
    - The version is what the tag says.

**Open, in the order they matter.**

    0  BUILT 09:2x, the operator's option B -- THE DOOR'S HANDOFF.
       Sitting 84, 09:04, "review the changelog": the Steward on llama3.2
       delivered a raw <action> block. Cause: the engine handed the door
       tool schemas (May Call + tools-capable model) and only the Router
       executes. Now: schemas go to the executor only; a non-Router seat
       that emits <action> has its ask CARRIED (needs_tool, named tool,
       args) and the markup stripped. REFUSALS §18; 13 strokes both ways;
       pipelines.md "Worked examples" written. Sitting 84 still OPEN and
       untolled. UNMEASURED LIVE: the first door run after this lands.
    1  THE TWO-TERMINATOR INCIDENT. 144 of 159 tracked text files are LF,
       14 CRLF, memory.md MIXED. The CRLF ruling is not the disk. Decision
       (renormalize to CRLF, or rule LF) is the operator's; then a stroke
       that walks the tree. CHANGELOG / Known has the full note.
    1b BUILT 10:xx, the operator's "go": THE LAW GATE (chainkit/lawgate.py,
       REFUSALS §19). Every run: chain walked, objective checked, every
       seat handed `## The law`, record stamped. 21 strokes. RESTART
       REQUIRED. Unmeasured live: the first sitting after it loads.
    1c SITTING 85 DEBUG, built: unattended close now records its ledger
       line; `git commit -m X` takes X; the scaffold parrot is refused.
       NOT built, the operator's call: rack_report's model reading misled
       him three times in one sitting (see CHANGELOG).
    1e SITTING 86 = THE FIRST LIVE STANDUP (15:33-15:39, 8/10 met). Real
       findings, in TASKS: the door recited the `## The law` block as "the
       covenant" (9 laws from a block naming 4 -- no read ran); the door's
       greeting invented a sentiment-classification objective (keyword bait
       again); "what is in the skills dir" was dispatched to the reader,
       and the Router chose skill_report over ground_list; "what does the
       covenant say?" -- the Router fed SENTENCES to ground_list/ground_read
       (both refused, recompose caught them) and never called the search
       it was told to; Manjuel on gemma4:12b spent 283s and delivered
       "(deliberation only, no conclusion reached)" -- the salvage line,
       not a ruling; the rack delivery dropped one model of eleven.
       The lock in run 2 was THIS HAND's suite run from a sandbox.
    1d BUILT 10:xx: SPEC.md (the contract; DONE line by line), BUILDMAP.md
       (generated where-to-look; `tests/buildmap.py --check` for CI),
       tests/standup.py (the seats through ten fixed objectives, live,
       with a reviewable report; dry-proven 10/10). NOT YET: BUILDMAP in
       index_roots and CI; the standup run live. Both the operator's.
    2  THE CLOSING SEAT STILL INVENTS WHEN NO TOOL RAN (s83 run 1, and
       finding 4 from s82). The one real build open: COVERAGE, NOT
       EXISTENCE. Do not start without the operator's word.
    3  Findings 1-3 from s82: message-only, one afternoon. Unchanged.
    4  git_commit's subject is the raw objective (7ed80f0 carries an
       unclosed quote). The skill exposes no message argument to the
       Router.
    5  The Router costs 9-35s on a git status the parser already decided.
       Proposed: run the tool and deliver its output when intent has the
       tool AND its arguments. Not the two-tier refactor. Not built.
    6  The scrub: the client token is still in 12 log filenames,
       sessions.jsonl, the index and the git pack. Names, not contents.
    7  The rack question (11 of 14 seats one model). rack.md needs
       `rack_sync` (says 3 loaded; s82 saw 4).
    8  DAYBOOK Session 4 is still open: "At close" and "Next session"
       unfilled until the operator closes the day.

**A note to whoever reads this next.** Today's faults were the hands', not
the seats': an agent chose a folder and a name without asking, twice, and
that is now SITTING LAW 4. Read CLAUDE.md's READ FIRST block. Ask where.

---

## HANDOFF FOR 2026-09-03 — read this before anything below it

**Where the ground stands at close.** `master@0e9988853`, three files dirty
(`SEAT_LOG.md`, `sessions/sessions.jsonl`, `sessions/thread.jsonl` — the
sitting wrote itself). Strokes 1470/1470, smoke 59/59, law chain whole at 2
links, manifest 50 records / 1 finding (the rack, unaskable from a sandbox
with no ollama module). Version moved 0.1.0 -> 0.1.1; tagged v0.1.1 on 0bd8666 (not on the
"0.1.1 woo hoo!" commit c04c4ef, which came later). v0.1.3 was tagged
2026-09-04 on cefdec0. See CHANGELOG.md.

**What landed today, in order.**

    morning    the AST landing gate finished; the manifest reconciler
               (chainkit/us.py) written and wired; prune made root-aware
               and gated; the world evicted from the index (733 docs, 0
               world docs); the whole doc set swept to 0.1.1; CONTRIBUTING,
               CI, pyproject.
    midday     the deliberation sink reached the TOOLS path -- the Router
               is the only seat that both thinks and holds tools, and was
               the one stage that could never be watched.
    afternoon  ALL 7,965 LINES of tests/test_chainkit.py read line by line
               at the operator's word. SEVEN STROKES COULD NOT FAIL. Five
               were a disjunction whose second clause was trivially true;
               three of the seven were written that same morning by the
               agent reporting them. Fixed. `proved` was added to
               REVIEW_ONLY_SKILLS -- the only behaviour change, and the
               only one of the seven that was hiding a FALSE FACT rather
               than an untested one.
    evening    SITTING 82. The operator ran the estate and wrote the toll.
               Five findings. NONE FIXED -- this was a review, and RULE 5b
               is RULE 5b. All five are open in TASKS.

**What sitting 82 proved works** — say this first, because the findings
below are all reporting faults and the machinery under them held:

    - deliberation captured on the tools path, five for five, prose not a
      column: 1291 / 2102 / 6133 / 6147 / 10271 chars. First live evidence.
    - the dedup: `git_status` named twice in one turn, ran once, said so.
    - the stale-lock guard: a 125-minute-old `.git/index.lock`, named with
      the exact `del` line and a seat refusing to touch anything in `.git`.
    - the commit subject came from `git areas()`, not from the model.
    - `proved` appeared in the table's cleared list -- this morning's fix,
      running.
    - the recompose appended the refused tool to BOTH court deliveries.
      Three seats never mentioned it. The machine did.

**The five findings. Four are one fault.** Full detail in TASKS; the
argument for treating them as one sweep is DESIGN §14.12.

    1  A REFUSAL NAMED A REASON IT NEVER CHECKED.
       skills.py:2266 refused `rack_report` with "'rack_report' changes
       things". It changes nothing. THE GATE IS RIGHT; THE SENTENCE IS
       INVENTED. Thirteen skills sit outside both lists and the message is
       false for at least five of them.

    2  THE DRIFT METRIC HAS PRODUCED NO NUMBER SINCE THE SPINE MOVED.
       (First written "never"; 41 transcripts of 2026-08-29 DO carry
       scores -- corrected 2026-09-04.) 502 transcripts since, 463
       "no usable source", 37 "too short", zero scores. Not broken --
       pipeline.py:907 arms it only on a pasted feed, which is the
       sitting-27 ruling and correct. The NOTE is what misleads: it reads
       as a failed measurement, not an unarmed one. DESIGN §11's "LANDED"
       paragraph said "once per run" and has been corrected in place.

    3  THE CARD REPORT CANNOT SAY "OVER". `max(0, budget - used)` printed
       "~0.0GB headroom" on a card 0.5GB overcommitted. Separately: the
       per-row size is DISK size, the total is VRAM footprint; the column
       sums to 13.5 and the total says 15.5, unlabelled.

    4  A CLAIM ABOUT A TOOL RESULT, CARRYING NO CITATION, IS UNCHECKED.
       The Router told the court "parity tests showed phi4 consistently
       scoring well on prose tasks". The word prose is in no parity
       artifact; phi4 appears in one run, n=1, at 0.53 -- the WORST of the
       seven references there (first written "four"; corrected 2026-09-04). Three minutes earlier the same Router had
       answered the same question correctly. `bogus_citations` could not
       bite: the claim quoted no path and no score, and that check is
       narrow BY DESIGN and says so in its own docstring.

    5  AND NOTHING DOWNSTREAM CONTRADICTED IT. Neiro, Jesster and Manjuel
       all sat after that claim; all three pivoted to VRAM and the false
       sentence fell out of the delivery by being IGNORED. That is not a
       safety property.

**THE FAULT, NAMED ONCE.** 1, 2, 3 and this morning's `us.py` bug are the
same thing: *a guard acts correctly, then explains itself with the most
likely reason instead of the established one.* `us.py` said "no rack was
reachable" without asking. It was fixed at 11am. `skills.py` told the same
class of lie at 3pm. **The fix was applied to a SITE. The fault is a
SHAPE.** That is the whole argument for one sweep over four bug-fixes, and
it is written up as DESIGN §14.12.

**The operator's toll, and it is a rack question, not a code one:**

    "table works mostly the same reasoning from the same models"
    "actual parity runs needs to be from different models with different
     perspectives"

Eleven of fourteen seats are phi4-mini. Neiro, Jesster and Manjuel are
three phi4-mini instances in three hats, and in both court runs they agreed
with each other and with the Router. Jesster is the LICENSED FOOL, seated
to give the strongest counter-argument; in run 2 it opened "The strongest
counter-argument the material supports is" and restated Neiro nearly word
for word. **Do not fix this in code.** It is the operator's rack.

**What is owed.**

    OPERATOR   `git add -A && git commit`, and a tag if 0.1.1 is real.
               The rack question above. Whether `rack_report` should sit
               at the table at all (recorded in TASKS as a QUESTION, not
               a task -- it is a reader, but it wakes the Quartermaster,
               and `rack_list` already serves).
    NEXT HAND  Findings 1, 2 and 3 are one afternoon between them and all
               three are MESSAGE-ONLY -- no behaviour moves, and each
               wants a stroke that reads the message for both cases.
               Finding 4 is a real build and is the second half of
               COVERAGE, NOT EXISTENCE. Do not start any of it without
               the operator's word.

**A note to whoever reads this next.** Every finding above came out of the
operator running the thing and writing down what felt off — which is
exactly what session 2's DAYBOOK said to do next, and it outperformed a
day of building. Three words in a toll found a fabricated commit history
last session. This session, two court runs found four reporting lies and a
metric that has never once fired. Run it. Write down what feels off.

---

## Open

### THE BUILD IS DONE. 2026-09-02.

    Everything the plan called for is built, stroked, and running on the
    operator's own machine. What is below this line is the REASONING behind
    what was built -- kept because it still governs, not because it is
    outstanding. Read it before changing a gate; do not read it as a queue.

    The last four items closed today:

      the log horizon        transcripts leave RETRIEVAL at 45 days
                             (CHAINKIT_LOG_HORIZON_DAYS=0 disables). Nothing
                             is deleted; `sitting` and `when` read logs/
                             direct, by number and by date.
      11 unused skills       MOOT, not cut. They cost nothing now: the
                             shortlist describes ~6 candidates and passes
                             the rest by name only. A skill nobody calls is
                             not a defect; a prompt paying for it was.
      gibberish at dispatch  closed. Noise is driven through run_pipeline
                             in the strokes and executes nothing.
      the Router's world     it has one now (agents/router.md), which was
                             the cause behind half the routing faults.

    WHAT REMAINS IS NOT BUILDING. It is running the thing, and two chores
    the operator holds because they are his by rule:

      - the commit, and the toll                     (RULE 6, LAW 6)
      - SEAT_LOG.md's client references — scrubbed 2026-09-02 to
        [redacted] on his word; the shape of the record is intact

    THE AST GATE ON land_code IS BUILT. 2026-09-03, session 2.
    `pipeline.inspect_code()`, called by `land_code` before the write.
    RULE 4 is no longer a request made of whichever model holds the
    coder's seat; it is arithmetic:

        does not parse          refused, with the syntax error and line
        requests urllib         refused, "RULE 4: the estate is local"
          socket http           (NETWORK_MODULES -- exactly the four
                                DESIGN 14.10 names, and a stroke says so,
                                so widening it stays deliberate)
        eval exec __import__    refused, "executes a string as code"
        shell=True              refused, "hands the string to a shell"
        NOT PYTHON              LANDS, noted "UNINSPECTED" -- the gate
                                fails OPEN and says so, because one that
                                silently passes what it cannot read spends
                                your trust on a check that did not happen

    Stroked both ways in test_the_landing_gate_parses_before_it_writes:
    every refusal has a sibling that must still land. `socketserver` and
    `httpx_is_not_http` land, where a substring grep would refuse both --
    that difference IS the argument for the instrument. So do a relative
    import, shell=False, `{'eval': 1}` as data, and a method named eval.

    THREE HONEST LIMITS, in the docstring rather than discovered later:
    `shell=True` is flagged on ANY call (over-refusing on a WRITE gate is
    recoverable, under-refusing is not); `importlib` is an uncaught hole,
    named as one; it proves what the SOURCE says, never what the code does
    when run -- nothing here executes the file, and nothing should.

    DESIGN 14.10's two lesser uses -- structural strokes, semantic slicing
    -- follow from the same instrument and are NOT built. They are not a
    queue; read them before reaching for a regex over source.

    A NOTE TO THE NEXT HAND, AND TO MYSELF. On 2026-09-02 twenty-seven
    changes landed in one day and not one of them added a capability --
    every one was a reaction to something the last sitting coughed up. A
    conversational front door will produce faults forever, so "fix what the
    last run showed" is an infinite queue wearing the costume of a plan.
    If you are here to improve dispatch heuristics, stop and ask what the
    estate is FOR. STOP ADDING THINGS is two hundred lines below this and
    it was written for the same reason, five sittings earlier.

    ### BUILT 2026-09-02. Kept below as the reasoning, which still governs.
    ### intent.claims_file_contents() + the gate in pipeline.py after
    ### strip_control. Stroked four ways firing, three ways NOT firing;
    ### disable the gate and exactly the four firing strokes go red.
    ### The honest limits below were written into the docstring, not
    ### discovered later. THE CLAIM-CHECK  (agreed 2026-09-01, built)

    A seat that CLAIMS a file's contents when no read ran that turn is
    asserting something the engine can already disprove. Make it arithmetic,
    not a matter of the model's character.

    WHY. Five fabrications in one day, and the shape only became clear at
    the end of it:

      s56  "Can you read me the poem?"   1 stage, NO flags, NO tool ran
           → composed a new poem and wrote "Here is the content of
             `poem_about_jesster.md`:" above it. The file existed and said
             something else entirely. The operator caught it.
      s58  "read me popsicles.md"        4 tools ran, 2 of them failed
           → "The requested file popsicles.md was not found." Correct,
             and the first time any seat has said it could not.

    SAME MODEL BOTH TIMES (phi4-mini). The variable was not size, it was
    whether tools actually ran: in s58 intent matched the filename and
    dispatched to ground_read, so real results came back; in s56 nothing
    matched, no flag rose, and a seat answering a file question out of its
    own head produced a file. A 12B answering out of its own head invents
    just as confidently and takes a minute doing it (s57: gemma4 spent 36s
    deliberating and reached no conclusion).

    So the fix is the guard, not the rack. It is also why the
    "bigger closing seat" line below is no longer the obvious remedy.

    WHAT IT DETECTS. Both conditions, this turn only:
      1. the seat's output claims to be showing a file's contents, AND
      2. no reading skill ran this turn

    WHERE THE DATA ALREADY IS.
      `tool_calls`             pipeline.py, per turn, already collected
      REVIEW_ONLY_SKILLS       skills.py, the maintained list of readers
      intent.names_a_file()    finds a filename in text — point it at the
                               SEAT'S OWN OUTPUT, not the objective

    THE RESPONSE. Same shape as THIS TOOL FAILED and the LAW 8 note: a
    fault named in the record, and the claim refused rather than delivered.
      note: <Seat> claimed the contents of `x.md`; no read ran this turn.

    HONEST LIMITS, to write into the docstring rather than discover later:
      - catches a claim that NAMES A FILE. Invention with no file cited
        still passes. Narrow and certainly right beats broad and crying wolf.
      - a seat legitimately quoting a file read in an EARLIER turn would
        trip it. Scope to this turn's claims, or consult the thread.
      - it proves a claim is UNSUPPORTED, never that it is false. That is
        enough: LAW 5 says testimony is not fact, and an unsupported claim
        of fact is exactly what must not reach the operator.

    STROKE IT BOTH WAYS. The refusal fires on a claim with no read; it does
    NOT fire when a read ran, nor on ordinary prose that happens to mention
    a filename. A guard with only a happy-path test is not a guard.

    ---

    THE CLOSING SEAT — STILL THE OPERATOR'S, AND THE CASE IS WEAKER AGAIN.
      Five strikes stand. But s58 showed the same model reporting a failure
      honestly once tools engaged, s59's closing Steward summarised honestly,
      and the claim-check now refuses the exact fabrication shape at the
      gate. Model size looks less and less like the variable. Re-measure
      against the guard before spending VRAM on it.
      NOT THE SAME THING as the toll: the operator noted 2026-09-02 that
      paying the toll is HIS typing, by hand, every time — which is why it
      goes unpaid most sittings. That is a separate item and not a seat.
    phi4-mini at the front door: hallucinated an eight-turn
      `steward:`/`operator:` dialogue (s56) and refused a benign read.
      Also said "not found" correctly (s58). Measured, not settled.
    RESOLVED 2026-09-01: agent_workspace/ was 94% of the index corpus.
      The operator cleared the cloned repos and reindexed. RE-PROVED
      2026-09-03 over 783 docs (the figure was 598 / 3,140 when first
      written; the corpus grows with the logs, so no count here is
      current for long -- read it from the index). The client shield
      came back clean both times with the estate's own is_protected()/
      is_secret() over every stored path: 0 vault docs, 0 .client.
      names, 0 secrets, 0 protected.
    RULED 2026-09-02: `worlds/` IS in .gitignore now. The operator's own
      archive, local only, left aside. 383 files under worlds/ (268 under a
      vault/) entered at e1c0ae6 and 0bfd8c4; `git rm -r --cached worlds/`
      LANDED the same day (d0d6426) and `git ls-files worlds/` is 0 -- the
      block near the top of this file is current, this one was stale until
      2026-09-04. The two old commits still hold them. Still not an exposure: no [remote] in
      .git/config, no refs/remotes, pushes gated behind CHAINKIT_GIT_REMOTE,
      no cloud sync. The existing commits are a separate question and LAW 1
      cuts against rewriting them.
    RULED 2026-09-02, SUPERSEDED 2026-09-03 (see INDEX SCOPE at the top:
      NO WORLD IS AN INDEX ROOT AT ALL). As first ruled: THE WORLDS ARE
      INDEXED BY NAME, ONE AT A TIME, on his call. The parent `worlds` is never listed, since it would inherit
      every world by the back door. The strokes state this as a PROPERTY
      and name no world: the bare parent is never a root, and no root may
      reach into anything holding a vault/. index_roots.txt is the first
      line; the vault/ shield in vectors.py is the second. Which worlds
      exist, and which are sealed, is the operator's business and is not
      written down here.
    ANSWERED 2026-09-02, THE VRAM CEILING: 16GB. Radeon RX 6800 XT, single
      card, NO second GPU. 32GB DDR4-3200, Ryzen 7 5800X, ASRock B450M Pro4.
      CHAINKIT_VRAM_GB=15 is therefore correct as headroom, not a guess.
      This CLOSES CogAgent permanently rather than pending — see SEAT_LOG,
      2026-09-02 — and it bounds whatever ends up behind `screen_act`:
      whatever it is must fit beside the resident set, not replace it.
    FIXED 2026-09-02: CRLF writer. All nine write_text sites carry
      newline="\n"; a source-reading stroke refuses a bare tenth.
    RULED 2026-09-02: an @-addressed seat of the operator's was RETIRED when
      its compile came off the rack. A seat naming a model the ground does
      not hold BLOCKS BOOT at preflight — preflight working, not a fault to
      route around. Its file is gone by his hand. Do not reseat anything
      unasked, and do not write his private seats into this file again.
    ### NEXT, ON SITTING 60'S EVIDENCE: SUBSTANTIVE-QUESTION ROUTING.
    Designed 2026-09-01, never landed, and now the live gap. Five questions
    about the estate's OWN contents — "what is the ledger?", "who is
    warden?", "what is the ledger work?" — raised no
    needs_tool and SKIPPED THE ROUTER. Nothing was retrieved, so nothing
    leaked; the client shield was never actually reached and is still
    unproven against a query that gets as far as semantic_search. What
    filled the gap instead was invention: one of those turns produced a
    confident paragraph about a real client's work, sourced from nowhere.
    THE CLAIM-CHECK CANNOT CATCH THAT — it needs a named file, and this
    cited nothing. A question about the ground must reach a reader.
    SITTING 61 PROVED THE SHIELD. `semantic_search warden` actually ran
      against 3,601 chunks and returned nothing from the sealed world. The gap
      named above (never reached) is closed. What sitting 61 opened:
    ### THE CITATION-CHECK — proposed, not built. The Router cited
      `logs/..._what_is_jesster.md` at cosine 0.5058 as a search hit. It was
      NOT a result; it was a filename INSIDE result #4's text, and 0.5058 was
      result #4's score. From that it invented "'warden' relates to jesster"
      and the closer delivered it. Unlike uncited invention this HAS ground
      truth: the tool output is the exhaustive list of paths and cosines
      this turn. A cited path+score either appears in it or does not.
      Arithmetic. The claim-check's shape with the evidence already in hand.
    "search the ground" matches NO alias for semantic_search. Run 1 of s61
      dispatched only because the literal keyword was typed; runs 4 and 5
      did not dispatch at all — run 5 said "use tools!" and got the word
      `ground_list` as prose. One line in intent.py ALIASES. Not added.
    `claim_check` is a GATE, not a skill; the operator invoked it as one
      twice. Nothing to call. Say so in commands.md or the Steward prompt.
    the front door still mimics formats: "who is warden?" emitted an
      `Operator:` / `Answer:` exchange, inventing a turn. Prompt rule 2,
      s56's family, not held. phi4-mini.
    the card is FULL: 15.3GB of ~15.0 in use, 0.0 headroom, 4 resident.
      the Expert Coder is cold and now costs an eviction to wake.
    the Router's prose drifts off its own tool output even when the tool is
      right: "6 declared" over a list of five, unused weight called
      "headroom". rack_report's fix does not reach the consuming seat.
    SUPERSEDED — THE SHORTLIST WAS BUILT 2026-09-02, on a different
      argument. The measurement below stands and was about ACCURACY; what
      changed is the budget, which is the reason it was finally built. Kept
      so nobody re-argues it from the accuracy side.
    MEASURED 2026-09-02, THE ROUTER SHORTLIST IS NOT NEEDED YET. Over 476
      logs / 119 tool-running turns: intent.names_a_tool already resolves
      79% deterministically, and the 21% residual is dominated by turns
      where the right answer was NO TOOL ('!@', 'workslsdmfg;m', 'chaty').
      An embedder would hand noise a plausible tool. Re-measure before
      building; the harness was deliberately not kept.
    RULED 2026-09-02, THE TERM-SHIELD IS NOT BUILT: the file-level client
      shield is enough. A client's name does echo in indexed transcripts,
      but the operator read the echoes and they are only the estate saying
      "nothing there" -- refusals, not contents. A chunk-level client-terms
      filter was proposed and DECLINED. Do not build it unasked; revisit
      only if an indexed transcript ever carries client CONTENT, which the
      claim-check and citation-check now make a named fault rather than a
      silent one.
    CLOSED 2026-09-02: the log horizon (45 days, transcripts only, nothing
      deleted); the 11 never-run skills (moot — the shortlist means they
      cost nothing in a prompt); the gibberish gate at dispatch (noise is
      driven through run_pipeline in the strokes and executes nothing).
    STOP ADDING THINGS. Sittings 44-48 were lost to unrequested iteration.
      RULE 5b exists because of it. Fix what the operator names; propose in
      one line; land on his word only.

## Rules that gate YOU (violations happened; see CLAUDE.md)

    ask before ANY reach outside Research — checking counts as reaching
    one yes = one act, once             — never carries forward
    no folder, no nesting, unasked      — SITTING LAW 4; ask where, always
    from a sandbox, read-only git only  — status/diff leave a lock you
                                          cannot remove (2026-09-04)
    keep the file's terminator          — CRLF ruling; never leave MIXED
    no cloud, no downloads at runtime   — whisper/models resolve local-only
    chain prepares; operator lands      — commits, memory, spends
    broke something → say so plainly, then fix it
    and say what you did NOT do, as plainly as what you did
