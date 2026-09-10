# Tasks

The list, hung off BUILDPATH's layers so a task says WHERE it lives, not just
what it is. Opened 2026-09-03, sitting 78, because sitting 77 asked Manjuel
whether it had a todo list and the honest answer was no.

**What belongs here.** Work the RECORD already owes — a toll that named it, a
stroke that went red, a doc that contradicts the disk. Nothing invented.

**What does not.** "Fix what the last run showed" is an infinite queue wearing
the costume of a plan (DAYBOOK's founding rule). A conversational front door
produces faults forever. Items that are DELIBERATELY NOT BEING BUILT are kept
below, under their own heading, with the reason — so nobody re-derives them
and quietly starts.

**The gate.** No agent ticks a box. An agent proposes and prepares; the
operator lands (RULE 6, LAW 6). A task is DONE when a stroke says so, not
when a seat says so.

    [ ]  open          [~]  in hand          [x]  landed, stroked
    [-]  declined, with the reason beside it

---

## Layer 0 — words on disk

    [x]  THE WORLD IS EVICTED — the OPERATOR ran `index_ground rebuild`
         in sitting 81 (2026-09-03 11:53, 190.8s) and the index was rebuilt
         again at 12:38. Verified in the database, not assumed:
         733 docs, `worlds` gone from the roots, WORLD DOCS: 0.

         AN AGENT LEFT THIS OPEN AFTER IT WAS DONE and told the operator it
         was still his to do. The evidence was on disk the whole time. That
         is the failure LAW 3 was written for.

    [x]  PRUNE DROPS UNDECLARED ROOTS — ruled (c) and built 2026-09-03.
         prune() now asks TWO questions, not one: is the file gone, and is
         its root still declared. Matches on the PATH against live roots,
         never the stored `root` label — a root can be renamed, narrowed or
         re-cased, and the label is wrong in both directions when it is.

         GATED, which was the whole reason (c) needed a ruling: root-
         awareness makes a REFRESH destructive in a way it never was, so an
         eviction above ORPHAN_CEILING (0.25) is REFUSED and reported —
         "check index_roots.txt; run `index_ground rebuild` if it is right".
         A guard that will not perform a suspiciously large action on the
         say-so of a config file.

         `roots=None` keeps the old behaviour exactly: a caller that cannot
         say what is in scope must not be taken to mean nothing is.

         Stroked both ways, and the REFUSING half deliberately — a gate
         nobody trips is a gate nobody notices removing.

    [x]  THE DOC SWEEP, 2026-09-03 (sitting 79). Six claims that
         contradicted the disk, each checked against it before it moved:

             HANDOFF:669   598 docs / 3,140  ->  re-proved at 783, and the
                           count now described as growing rather than
                           quoted, per the no-count-in-a-doc ruling
             HANDOFF:115   MAX_TOOL_STEPS=4  ->  5 (it rose with the dedup
                           at sitting 63 and this line never moved)
             HANDOFF:20    15 seats / 31 tools -> 14 seats / 35 tools
                           (36 as of 2026-09-04; the 36th is `proved`)
             HANDOFF:36    "383 files still tracked under worlds/" -> the
                           `git rm -r --cached` landed; ls-files is 0
             HANDOFF:38    INDEX SCOPE rewritten: the one-at-a-time ruling
                           is SUPERSEDED by origin-only, with the evidence
             RUNBOOK:158   921/921 in the STALE example -> NNN/NNN, so a
                           once-real number cannot read as a claim

         No doc now names a suite tally except this file, describing the
         sweep itself.

---

## Layer 1 — parsing

    [x]  THE DELIBERATION IS KEPT (sitting 79, the operator's ruling).
         `runtime.chat(..., think_to=)` — a per-call sink mirroring
         `stream_to`, so nothing is shared and the Reasoner's background
         thread cannot interleave into another seat's transcript. Landed on
         StepResult.thinking, rendered by transcript.py AFTER the spoken
         output under `<details>deliberation — not read by any seat</details>`.
         SITTING 47 IS UNTOUCHED: never displayed, never returned by chat(),
         never in a later prompt, the thread, or the delivery — and the
         stroke proves each of those absences.

         IT ALSO CLOSED A THIRD FIXTURE DRIFT. env_for once omitted
         skills_ref; then `tools=` was not moved into smoke's stub and it sat
         RED at 34/50 from 14e2711 to 2026-09-02 with the strokes green
         throughout; `think_to=` was the third. The strokes now compare the
         stubs' KEYWORD SURFACE to OllamaRuntime.chat's instead of trusting
         the next hand to remember.

    [x]  SkillSpec.declared_args — a skill's argument names read off its
         own **Parameters Needed:** line, not a table beside it.
         Stroked: test_the_dedup_keys_on_the_declared_call.

---

## Layer 2 — deciding

    [x]  THE DEDUP KEYS ON THE DECLARED CALL.  Sitting 77: the Router
         called `list_directory` twice in one turn and both ran, because
         the signature was built from what the model EMITTED. An argument
         a skill does not have could make two identical calls look
         different. Stroked, and it caught test_tool_loop's own fixture
         making that exact mistake.

    [x]  THE GREETING FAMILY REACHED THE READER. Landed 2026-09-03.
         `asks_the_ground` tested `words[0] in _GREETING_LEADS`; the set
         held `morning`/`evening`/`afternoon` and the `good X` family --
         the commonest greeting form in English -- leads with `good`, so
         the set could never be reached. "good morning, sunshine, how are
         ya?" went to semantic_search and cost 155 SECONDS. Now tests the
         first TWO words, and the set carries good/gday/mornin.

         THE FIRST DRAFT OF THE STROKE WAS WRONG, NOT THE CODE. It asserted
         asks_the_ground() for five "real questions" and went red on two
         that were ALREADY false at HEAD -- "who is steward?" reaches the
         reader through names_a_tool's doctrine phrases instead. Checking
         against HEAD is what showed it. The stroke now asserts the
         PROPERTY (a ground question reaches a reader) over the mechanism.

         AND IT LEFT A GAP WRITTEN DOWN RATHER THAN QUIETLY WIDENED:
         "what happened this morning?" reaches neither door. It is a
         `when`-shaped question about the record and predates this fix.
         A stroke now pins it so a later hand cannot silently patch it in.

    [x]  STREAMING WITH TOOLS — the operator's (a) ruling, 2026-09-03.
         Only two seats declare `May Call` (Router: all, Steward: four
         readers), so only they receive `tools=` — and the tools branch was
         single-shot, which is why the ROUTER, the seat that holds tools
         AND the only seat that thinks, was the one stage that could never
         be watched. 74 seconds of spinner on a greeting.

         NO FRAGMENT ASSEMBLY (that is (b), and NOT done). Ollama sends a
         COMPLETE tool_call in one chunk and `calls_to_action_xml` reads
         only calls[0], so the first part carrying a call is kept WHOLE and
         handed to the existing renderer — the tool loop, its guards and
         every stroke on them see the shape they always have. Falls back to
         single-shot on TypeError, so an older client cannot take routing
         down. (b) stays open, and wants the matrix generator first.

    [x]  A MALFORMED FLAG IS READ AND STRIPPED — landed 2026-09-03,
         sitting 81. `_FLAGS_RE` required `</flags>`, so an unclosed tag
         was invisible to read_flags AND unstripped by strip_control: the
         Steward emitted `needs_tool` twice, the Router never woke, and the
         raw markup went to the operator. One missing slash defeated both
         sitting 42's ruling and the handoff. Now matches closed, unclosed-
         before-next-tag, and unclosed-at-end — BOUNDED to 80 chars and no
         newline, so a stray tag in prose eats one short run, never the
         answer. The operator's toll named this THIN before I found it.

    [~]  AN INTERNAL, REVIEWABLE TEST SUITE — PART 1 LANDED 2026-09-03.
         The `proved` skill reads tests/last_run.json, run_history.jsonl
         and the manifest report, and answers the sitting-81 question from
         FACT. Reports staleness first (a green tally from before the
         current code proves nothing about it), names failures with their
         addresses, refuses to report a crashed run as green, and states
         its own limits every time. 16 strokes, both ways.

         PARTS 2 AND 3 REMAIN AND ARE NOT SCHEDULED: the matrix generator
         (Layer 8) and making REFUSALS.md reliably retrievable.

    [-]  (original entry) AN INTERNAL, REVIEWABLE TEST SUITE MANJUEL CAN RUN ON ITSELF.
         Sitting 81's WHAT PROVED: "we need a test suite, pipeline, and
         info for the system to understand its limitations for context."

         The gap is real and it is NOT the strokes. 1,375 strokes test the
         ENGINE from outside, offline, stubbed. What Manjuel cannot do is
         answer "have you run a full test suite on these skills?" — asked
         in that sitting and answered from nothing. It has no reviewable
         account OF ITSELF to read.

         Three parts, and the first is nearly free:
           1. `tests/last_run.md` + run_history + the manifest report are
              already on disk. A skill that READS them would let Manjuel
              answer that question with fact instead of guessing.
           2. the synthetic matrix generator (BUILDPATH Layer 8) — phrasing
              variance through run_pipeline, scored on signals already
              emitted. This is what would have found the flag bug, the
              greeting bug and the empty write_file without the operator
              typing them by accident.
           3. limitations as READABLE GROUND: REFUSALS.md is already the
              document; it is not reliably retrieved when asked.

         DONE WHEN: Manjuel, asked what it has proved, answers from
         last_run.md rather than from its own head. Part 1 only. Parts 2
         and 3 are separate and neither is scheduled.

    [x]  A PYTHON FILE IS CUT BY DEFINITION — DESIGN 14.10 use 3, built
         2026-09-03. windowed() mapped big files by `_HEADING`, a markdown
         `#` — which in Python IS A COMMENT. A 99KB module offered the prose
         inside its own docstrings as navigable "sections"; asking for one
         returned a fragment of a sentence. A character offset is worse: it
         lands mid-expression, so the window may not be valid Python at
         either end.

         Now: `ast` gives exact line bounds, the map is the file's real
         shape (69 definitions for skills.py), and a name returns a WHOLE
         def that parses on its own. Methods are addressable as
         Class.method. Exact name beats a containing one.

         THE HALF THAT MATTERS MORE THAN THE FEATURE: a .py that does not
         parse STILL READS, and says why it could not be cut. A broken file
         is exactly the one you open to fix the break; a reader that refuses
         it refuses the only read that was needed.

         THIS IS HALF OF COVERAGE. It does not track what was read — that is
         still open below — but it makes a partial read of a module a
         COMPLETE read of a function, which is the shape a seat (and an
         agent) actually needs.

    [-]  DESIGN 14.10 USE 2 — structural strokes, replacing the regex
         source-greps with ast.walk. DECLINED for now, deliberately. The
         greps work, they are stroked, and three of them CAUGHT REAL BUGS
         today (the branch-counter on chat(), the newline declaration
         reader, the stub signature check). Rewriting working guards to use
         a nicer instrument is churn, and DESIGN's own note says the guards
         do not change — only their brittleness does. Revisit when a grep
         actually breaks on a line wrap, which is the failure it was
         written for.

    [x]  THE RECONCILER'S OWN LIE — fixed 2026-09-03, found by the
         operator running it. The rack finding read "not checked - no rack
         was reachable" whenever `installed` was None, and main() NEVER
         PASSED IT — so on his machine, with Ollama running, the module
         that exists to catch unchecked claims made one.

         Two states now, said differently and neither pretending to be the
         other: NOT ASKED ("that is not the same as unreachable"), or asked
         and refused, with the error named beneath the report. main() calls
         rack_tags(), which asks.

    [x]  SEVEN STROKES THAT COULD NOT FAIL — read line by line at the
         operator's word, 2026-09-03, and fixed. All 7,965 lines.

         FIVE WERE THE SAME SHAPE: an `or` whose second clause is
         trivially true, so the check passed whatever the code did.

             line 2715  `... or "drifted" in ctx2.flags or True`
                        A stroke that had NEVER tested anything, counted
                        in the tally since the day it was written.
             line 5501  `check("...", True)` -- an unconditional pass.
                        The intent was real (record_run must not raise);
                        a literal True cannot be told from a stub.
             line 4734  `len(x[:200]) > len(y[:120]) - 60` -- both sides
                        are the SLICE CAPS. It read `200 > 60`.
             line 1666  `"no local" in why or path != ""` -- the two
                        clauses are "absent" and "present". It passed on
                        every machine and asserted nothing.
             line 5965  MINE, and the worst: `"proved" in
                        REVIEW_ONLY_SKILLS or lib.spec("proved") is not
                        None`. The second clause is always true, so it
                        passed while the fact was FALSE -- `proved` had
                        been left out of the reading whitelist and
                        counsel at the table could not call it.
                        NOW CLEARED, and the .us record says so.

         TWO MORE WERE MINE FROM THE SAME DAY: a routing check that
         accepted EITHER answer and so proved nothing about reachability,
         and `_smoke_stub_chat()` -- a duplicate of
         test_fixtures_mirror_the_runtime that fetched smoke's stub by
         IMPORTING smoke_cli, which that stroke's own docstring forbids
         twenty lines away: "read by AST, never imported: importing it
         would run the REPL script." Removed; the AST version stands.

         AND TWO PIECES OF DEAD CODE: `_render_report` carried TWO
         docstrings -- the second, holding the explanation a reader most
         needed, was an unreachable string expression -- and an unused
         `ours` binding.

         THE PATTERN IS THE DAY'S PATTERN, one level up: a guard asking
         one question when it needed one more. Here it was the STROKES
         doing it, and an `or` was how they got away with it.

    [ ]  A REFUSAL THAT NAMES A REASON IT DID NOT CHECK.  Sitting 82,
         twice in one sitting, at the table:

             Refused: the table reviews; it does not act.
             'rack_report' CHANGES THINGS, and counsel has eyes, not hands.

         `rack_report` changes nothing. skills.py:1669 gathers `_rack_list`
         (read-only), asks the Quartermaster to narrate it, and returns the
         observed numbers with the reading beside them. It is not in
         WRITING_SKILLS. It never was.

         THE GATE IS RIGHT; THE SENTENCE IS A LIE. skills.py:2265 refuses
         anything not in REVIEW_ONLY_SKILLS -- correct, an allowlist is the
         right shape for a capability -- and then states a REASON it never
         tested: that the skill writes. Thirteen skills sit outside both
         lists, and for at least five of them (`rack_report`, `lint_code`,
         `linear_regression`, `time_align`, `subtask`) the sentence is
         false on its face.

         THIS IS `us.py`'s BUG, EXACTLY, TWO WEEKS ON. That module said
         "no rack was reachable" whenever nobody handed it a model list --
         asserting a refusal it had never attempted. Fixed 2026-09-03 by
         making it ASK, and by splitting NOT ASKED from asked-and-refused.
         The same fault was sitting in the skills gate the whole time.

         WHAT IT WOULD TAKE: say what is true -- `'{key}' is not cleared
         for the table` -- and add the writer clause only when
         `key in WRITING_SKILLS`. Three lines. The behaviour does not move.

         DONE WHEN: a refusal of a non-writing skill does not call it a
         writer, and a stroke reads the message for both cases.

    [ ]  SHOULD `rack_report` SIT AT THE TABLE?  THE OPERATOR'S CALL, not
         an agent's. It is a reader, so the allowlist would take it. But it
         WAKES THE QUARTERMASTER -- one model call per invocation -- and
         `rack_list` is already cleared and returns the same observed
         numbers without the narration. In sitting 82 the Router reached
         for `rack_report` first, was refused, fell back to `rack_list`,
         and got everything it needed. That is the gate working.

         Recorded as a QUESTION, not a task. `proved` was cleared on
         2026-09-03 because a stroke's own stated intent said it should be.
         Nothing here says that about `rack_report`.

    [ ]  THE DRIFT METRIC HAS PRODUCED NO NUMBER SINCE THE SPINE MOVED.
         (First written "never" -- wrong: 41 transcripts of 2026-08-29
         carry scores, when runs had a feed. Corrected 2026-09-04.)
         502 transcripts since: 463 say "not scored this run (no usable
         source)", 37 say "output too short to score", and ZERO carry a
         score.

         IT IS NOT BROKEN. pipeline.py:907 primes the checker ONLY when
         there is a pasted feed -- the sitting-27 ruling, and a good one:
         with no feed it scored a reply against the words "good job stew",
         called it drifted, and woke the Quality Evaluator to review a
         compliment. An objective alone is a request, not a source.

         THE NOTE IS WHAT MISLEADS. "no usable source" reads as WE LOOKED
         AND FOUND NOTHING WORTH SCORING. The truth is THE CHECK WAS NEVER
         ARMED, because this run had no feed, by design. Nothing was tried.
         Nothing was unusable.

         IT ALREADY COST SOMETHING. The operator reasoned aloud about
         automating the toll "that's what the whole idea of the drift
         metric was, right?" -- building on a measurement that has never
         once run. The note told him 463 times and read as a data problem.

         AND drift.py CARRIES DEAD MACHINERY BESIDE IT. `_short_source`,
         `DRIFT_WARN_SHORT` and the comment "a bare-objective comparison is
         judged against a lower bar" (drift.py:28, :107) describe a path
         that CANNOT BE REACHED: a bare objective never primes at all.

         WHAT IT WOULD TAKE: two notes for two states, the way `us.py` now
         splits them -- "not armed: this run had no pasted source" versus
         "primed but not scorable: <why>" -- and either reach the short-
         source bar or fold the comment that promises it.

         DONE WHEN: a run with a feed prints a number, a run without one
         says it was never armed, and neither says "no usable source".

    [ ]  THE CARD REPORT CANNOT SAY "OVER".  skills.py:1665:

             ~{_vram.gb(max(0, budget - used))} headroom.

         Sitting 82 printed `Card: 15.5GB of ~15.0GB in use, ~0.0GB
         headroom.` The card was 0.5GB OVER. The `max(0, ...)` turned the
         one state that matters into the state just below it.

         AND THE COLUMN DOES NOT SUM TO THE TOTAL. The per-row size comes
         from `_vram.installed_sizes()` -- DISK size. `used` comes from
         `runtime.resident()` -- VRAM footprint, which carries context and
         KV cache. The four LOADED rows add to 13.5GB; the total says 15.5.
         Two different quantities in one table under one heading, with
         nothing saying so. The Router could not reconcile them either and
         quoted the total back as "15.0GB in use".

         DONE WHEN: an overcommitted card says so in words, and the two
         numbers are either the same quantity or labelled as two.

    [ ]  A CLAIM ABOUT A TOOL RESULT, CARRYING NO CITATION, IS UNCHECKED.
         Sitting 82, run 3. The Router read the parity logs and told the
         court:

             "parity tests showed phi4 consistently scoring well on prose
             tasks" ... "closer scores than other models when tasked with
             front door responsibilities"

         EVERY CLAUSE IS FALSE, and the disk says so:
             - "prose" appears in ZERO parity artifacts
             - phi4-mini appears in ONE parity run, as ONE case, n=1
             - its score there is 0.53 -- the FURTHEST of the four
               references in that run, not the closest
             - and THREE MINUTES EARLIER the same Router, on the same
               question, reported correctly that it was never measured

         NOTHING CAUGHT IT. The Guardian passed it SAFE, which is right --
         it is false, not unsafe. `bogus_citations` (pipeline.py:308) only
         compares PATH/SCORE PAIRS cited in prose against pairs the search
         returned; this claim cited no path and quoted no score, so there
         was nothing for the arithmetic to bite on. The check is narrow BY
         DESIGN and says so in its own docstring -- "narrow and certainly
         right beats broad and crying wolf". The gap is real and was known.

         Three seats then sat downstream of it -- Neiro, Jesster, Manjuel
         -- and none contradicted it. They pivoted to the VRAM argument and
         the false claim simply fell out of the delivery. IT SURVIVED BY
         BEING IGNORED, not by being checked.

         THIS IS COVERAGE, NOT EXISTENCE, ONE TURN FURTHER ON. That item
         is about a PARTIAL read spoken as a whole one. This is a claim
         about what a read SAID, with nothing tying it to the read. Same
         family, and the harder half.

         DO NOT REACH FOR A MODEL TO JUDGE THIS. The estate's own rule is
         that a check is arithmetic or it is another opinion. What is
         arithmetic here: the Router's testimony is already labelled and
         already sits beside the exact tool text it read.

    [x]  2026-09-07. COVERAGE, NOT EXISTENCE — a partial read spoken as a whole one.
         Named 2026-09-03 after an agent grepped `parity.py`, asserted
         about the file, and was wrong twice in one turn. BUILT 2026-09-07
         as THE PARTIAL-READ STAMP (pipeline.note_partial_read /
         unread_parts / recompose): every windowed read is recorded and
         the delivery says READ IN PART, NOT WHOLE, unless every part was
         read. The claim-about-a-read half (above) is still open.

         THE TOOL ALREADY TELLS THE TRUTH. windowed() (skills.py, `def windowed`)
         returns "part N of M (chars X-Y of Z). THIS IS NOT THE WHOLE
         FILE." in capitals, with a map of the headings it did not show.
         SEAT_LOG at 136KB arrives as 9% wearing a sign.

         THE GATE ASKS THE WRONG QUESTION. claims_file_contents asks "did a
         read run this turn?" -- part 1 ran, so it passes. The seat saw 9%
         and spoke about 100%, and nothing noticed. A read is not a
         COVERING read, and the engine cannot currently tell them apart.

         WHAT IT WOULD TAKE: record what windowed() returned per turn --
         file, part, of how many -- and note when a claim names a file
         whose coverage was partial:

             note: <Seat> spoke about `parity.py`; this turn read part 1
                   of 3.

         A NOTE, NOT A REFUSAL, and beside the answer the way the recompose
         puts a failure there. Arithmetic: the parts returned are known,
         the whole is known, and intent.names_a_file already finds the file
         in the seat's own text.

         NOT THE FOURTH NARROW GATE. That ruling (2026-09-02) was about
         four detectors of "claimed an observation with no observation".
         This is a different fact -- PARTIAL observation spoken as whole --
         and it is the shape that no existing guard can see.

         THE HONEST LIMIT, stated so nobody oversells it: this reaches
         seats inside Manjuel. It does nothing about an agent working on
         the ground from outside, whose tool calls no gate here can touch.
         For that there is LAW 3 and the record, which is how the operator
         caught it both times today.

         DONE WHEN: a turn that reads part 1 of a big file and then makes
         a claim about that file carries the coverage note; a turn that
         reads the whole file does not.

    [ ]  A FAILED TOOL SHOULD PUSH THE LOOP, NOT END IT.  Sitting 77 run 3:
         `ground_list` failed, the Router had THREE of five hops left, had
         already written down the correct next call — "listing subfolders
         explicitly using ground_list with a specific content argument like
         'skills'" — and then wrote prose instead of making it. The operator
         made the call for it by retyping the question 53 seconds later.
         Defect 2's better refusal now names the correction; whether that
         is ENOUGH to produce a retry is unmeasured.
         DONE WHEN: a transcript shows a refusal followed by the corrected
         call in the same turn. This is a MEASUREMENT, not a build — do not
         reach for a loop change until the record says the message failed.

    [ ]  `list_directory` IS THE ROUTER'S HEDGE, NOT A GIT READER. The
         operator asked whether it was gathering before/after state for the
         git commands. Tested against every git run in the record:

             13 runs of `git status` / `git commit`    git_status ALONE
              1 run, "what is uncommited in the git?"  + list_directory

         The one that added it is the one whose phrasing was NOT cleanly
         recognised. Same in sitting 77: both `/skills dir` phrasings drew
         it, neither needed it. So it is a marker of Router UNCERTAINTY —
         when it does not know, it lists the scratch folder. That makes it
         a signal worth READING, not noise worth suppressing.
         DONE WHEN: enough runs to say whether "list_directory beside a
         correct tool" predicts a wrong or thin answer. A MEASUREMENT.
         Do not suppress the call — it is the only visible tell.

---

## Layer 3 — running

    [x]  THE AST GATE ON land_code.  `pipeline.inspect_code()`, parse
         before write; network imports and eval/exec/__import__/shell=True
         refused BY PROOF; non-Python fails OPEN and says so. 36 strokes,
         both ways. DESIGN 14.10 use 1.

    [x]  `importlib` CLOSED — 2026-09-03. The docstring called it "a
         known hole, not an oversight" from the day the gate was built.
         Writing a hole down beats discovering it later; leaving it open
         once it is cheap to close is just leaving it open.

         The MODULE is refused, not the call: import_module("socket")
         reaches everything NETWORK_MODULES refuses and the walk cannot
         read the string, so a name is decidable where a runtime-built
         argument is not. Both import forms, submodules, and second-in-a-
         list. `importlib_metadata_lookalike` and `from . import importlib`
         still land — the AST compares the module name, not a substring.

         STILL NOT SEALED and the docstring now says exactly that: a module
         object via getattr, a __builtins__ lookup, or an import spelled
         through a variable remain uncaught. Narrowed, not sealed, and a
         stroke asserts the docstring keeps saying so.

    [x]  ONE TURN, ONE ACCOUNT OF HOW A TOOL WAS CHOSEN — 2026-09-03,
         found on the second pass over sitting 81. A single run logged two
         notes that contradict: "this ASKS ABOUT `skill_report` ... nothing
         run" and "objective names `skill_search` -- Router woken
         directly". The first claimed nothing ran while the line beneath it
         set named = skill_search; the second credited an objective that
         never mentioned skill_search.

         The OUTCOME was right and the ACCOUNT was unreadable — and for a
         harness whose product is an honest record, that is the defect.
         The note now says what runs (`skill_search` reads the declaration)
         and what does not (the skill asked about), and RunContext.named_by
         lets the dispatch note credit the branch that actually chose.

    [x]  THE SPINE MOVE IS MEASURED — the OPERATOR ran parity in sitting
         81 (2026-09-03 11:48). 9 cases, 8 scored, mean 0.7176, stamped to
         sessions/parity_history.jsonl WITH the seat map that produced it.

             was the spine move an improvement   0.82  close  vs llama3.2
             summarise a feed                    0.53  far    vs phi4-mini
             refuse an unsafe instruction         n/a  refused, the gate held

         THE REPORT PRINTED THE READING BACKWARDS on both models that
         mattered, and that is now fixed (below). Read correctly:

           0.82 vs llama3.2 -- a model the seats do NOT run. High topical
           agreement between Manjuel-on-phi4-mini and a bare llama3.2
           call. Evidence about the two models agreeing, NOT about whether
           Manjuel earns its keep.

           0.53 vs phi4-mini -- the seats' OWN model, so LOW means the
           Manjuel DIVERGED from a bare call. On "summarise a feed" the
           machinery did something a plain call did not. Go read that pair
           before concluding it was better; the score cannot say.

         STILL OPEN, and it is a different question from the one that has
         now been answered: whether that divergence was an IMPROVEMENT.
         A cosine cannot say. Reading the pair can.

    [x]  PARITY READ THE WRONG READING — fixed 2026-09-03. render() decided
         "is this the seats' model?" by comparing to DEFAULT_REFERENCE_MODEL,
         a constant still naming llama3.2 from when llama3.2 was the spine.
         So llama3.2 (named by nothing on the rack) was labelled "same model
         as the seats", and phi4-mini (eleven seats) was labelled "the seats
         fell short" — the opposite of what the module's own docstring says
         that number means. stamp() already received the real seat map;
         render() inferred instead. It reads the map now, names how many
         seats run that model, and says UNKNOWN rather than guessing when
         given none. Two superseded strokes rewritten, not deleted.

    [x]  index_ground NOW SAYS WHICH MODE IT RAN — fixed 2026-09-03. The
         "Rebuilt from scratch" banner was appended to `lines`, which is
         handed to idx.build() as its report callback and never read again:
         COLLECTED AND DISCARDED. So the result never named its mode, and
         both seats inferred one — wrongly — from `unchanged: 0 skipped by
         hash`, which is the rebuild's own signature. The operator was told
         his rebuild had not happened while it had. First line now reads
         REBUILT or Refreshed, and the banner explains why `unchanged` is 0.

    [ ]  phi4-mini AT THE FRONT DOOR is unsettled either way. SEAT_LOG
         2026-09-01: it hallucinated an eight-turn steward:/operator:
         dialogue and refused a benign read; s58 showed it reporting
         honestly once tools engaged. "The move up may be a downgrade at
         the front door" — still unmeasured.

---

## Layer 5 — the record

    [x]  THE TWELVE UNPAID TOLLS ARE WRITTEN — 2026-09-03. Every
         "Not stated" block in SEAT_LOG is filled; the count is 0.

         EACH IS STAMPED SECOND-HAND, and that stamp is the point: an agent
         wrote them FROM THE RECORD. They are not the operator's judgment,
         and LAW 10's half — what the person who sat thought proved — is
         still unpaid on those twelve. An entry pretending otherwise would
         be worth less than the blank it replaced.

         FOUR WERE EMPTY (7, 8, 9, 45: one git commit each; 62: two git
         runs). Nothing to weigh, and the toll says so rather than padding.

         SEVEN CARRY REAL EVIDENCE, and five are the origin of guards now
         in the engine:
           s10  markup in the delivery — the EARLIEST instance in the
                record, two days before strip_control existed
           s14  "who is steward?" answered as a description of running
                Python that nothing had executed — invention shaped like a
                tool result. The doctrine phrases now routing that question
                to a reader were earned here.
           s31  "heloo stewy" woke the coder on a greeting — why a short
                objective with nothing code-shaped has `technical` set
                aside
           s52  THE POEM SITTING. Claimed a poem was written with nothing
                on disk, then refused to read it back. The write-claim
                check exists because of this turn.
           s65  "Steward is Manjuel, the instance of llama3.2" — three
                errors from one retrieval into another world's doctrine.
                The evidence behind NO WORLD IS AN INDEX ROOT.
           s66  the same request in three phrasings — the operator finding
                the alias table by trial
           s67  the embedder mismatch refusing cleanly, naming both tags
                and the remedy. Kept as what a guard reading WELL to a
                person looks like.

    [x]  DESIGN 14.11 CARRIES THE SIXTH SHAPE — landed 2026-09-03. A
         stale answer, not a fabrication; the guard for it stays DECLINED
         under the no-fourth-narrow-gate ruling, and the reason is written
         beside it. [ ]  (superseded entry below kept for its detail)
    [-]  DESIGN 14.11 needs the SIXTH closing-seat shape recorded. The
         first five are fabrications. Sitting 77 run 3 is different: the
         Steward answered the PREVIOUS question — run 2's todo-list answer,
         delivered against a /skills objective, with the correct objective
         in its prompt and the Router's on-topic text directly above it.
         A stale answer, not an invention. Worth one line in the tally
         before anyone re-measures whether that seat needs more model.

---

## Layer 8 — the declaration, and the reconciliation

    THE DELIVERABLE'S SPINE. Ordered so each item is useful alone.

    [x]  8.1  THE MANIFEST RECONCILED TO DISK. Landed 2026-09-03.
              36 of 36 skills and 14 of 14 seats now carry a record.
              Mechanical fields (writes, remote, model, source, may_call)
              DERIVED from the code; every `wall` hand-written after
              reading the handler it describes.

              WHAT IT FOUND, kept because a manifest that records only
              wins is the thing this ground refuses:

                20 skills had NO RECORD AT ALL -- no wall, no writes flag,
                   running unbounded on paper for weeks.
                `speak` reaches the OS TEMP DIR and SPAWNS A POWERSHELL
                   PROCESS. The widest reach in the library; nothing
                   declared it, and no seat but the Router can call it.
                `subtask` opens a NESTED RUN -- its wall is INHERITED,
                   bounded by depth rather than by path. A recursion
                   boundary that had never been written down.
                14 skills read THE WHOLE GROUND, not the workspace jail.
                   The old prose said "most skills run inside
                   agent_workspace/ only" and had been false for weeks.
                10 of 11 seat records named a model the seat had not run
                   in weeks (Steward declared qwen3.5:4b, runs phi4-mini;
                   Router declared qwen2.5-coder:1.5b, runs qwen3.5:4b).
                THE ROUTER declared `read: agent_workspace/** only` while
                   cleared for `May Call: all` -- which includes every
                   ground reader. The STEWARD declared `read: deny` while
                   cleared for ground_read and ground_list. The manifest
                   UNDERSTATED the only two seats that touch the disk.

              THE FIX FOR THAT LAST ONE IS STRUCTURAL, not a correction:
              `permission` is now DERIVED from `May Call` plus the wall of
              each skill named, never asserted beside it. A seat's reach IS
              the union of what its tools may touch, and any other way of
              writing it can drift from the clearance it claims to describe.

              Also corrected in the prose: embedder tag (v2-moe), tool cap
              (4 -> 5), and the THIN paragraph about `logs/` not being a
              Manjuel -- resolved, with the distinction kept between an
              append-only sitting record and the hash-chained law ledger.

    [x]  8.2  us.py PARSE — landed 2026-09-03. `us.load()` returns every
              record and NAMES every block that would not parse. A parser
              that quietly drops the one record it could not read would
              defeat this module in the least visible way available, so a
              malformed block is a finding, never a silence. Stroked on a
              good file and a broken one.

    [x]  8.3  THE RECONCILER — landed 2026-09-03. `python -m manjuel.us`.
              Compares every record to the thing it names and REPORTS;
              exit 0 always, for audit_record.py's reason and not a weaker
              one — the manifest describes a ground the operator edits by
              hand, so an assertion over it would go red because he added
              a skill. Nine comparisons: declared-vs-present both ways for
              skills and seats, wall present, writes vs WRITING_SKILLS,
              remote vs the gated set, model vs the seat, source exists,
              may_call vs May Call, permission.edit vs write clearance,
              and can_approve FALSE EVERYWHERE.

              PROVED AGAINST THE OLD MANIFEST, not just the new one:

                  against HEAD's us/     41 findings (24 gap, 17 drift)
                  against the reconciled  1 finding — "the rack: not
                                            checked, none was reachable"

              That second line is the design: a check that CANNOT run says
              so rather than passing. A reconciler reporting nothing looks
              identical to a clean ground, and telling those apart is the
              whole value.

    [x]  8.4  THE RECONCILER IS STROKED — landed 2026-09-03, and the
              firing half matters more than usual here. Each check is
              proved by BREAKING a record and watching the right finding
              appear: write_file claiming writes:false, git_status
              claiming remote:true, a seat naming a model it does not run,
              a seat understating may_call, a record with no wall, a
              record for a skill that does not exist, and can_approve:true
              anywhere. Plus: a malformed block is named, the readable
              records still load, and an OLD-SHAPED `permission` REPORTS
              rather than crashes.

              THAT LAST ONE IS A BUG THE OLD MANIFEST FOUND IN ME. The
              first draft assumed `permission.edit` was a map and died on
              the older records, which wrote `"edit": "deny"` — the one
              input it most had to survive, because reporting on a stale
              manifest IS the job. A reconciler that dies on the thing it
              was written to judge has judged nothing.

    [-]  MCP AS A COMPETING SPEC. Declined. MCP describes what a tool
         DOES so a model can call it; `.us` declares what a tool MAY
         REACH so a person can audit it. Different questions. MCP servers
         can be surfaced as skills later — they would inherit the four
         gates already at execute() and would need `.us` records like
         anything else. The manifest is the integration point.

---

## Layer 9 — a stranger's first hour

    [x]  9.1  pyproject.toml — landed 2026-09-03. Wheel builds; the
              `manjuel` entry point resolves to cli:main; ONE dependency.
              Verified the package does NOT carry the record: 31 files,
              engine only — no SEAT_LOG, no memory, no logs, no sessions,
              no .env, no bin/ binaries. `law/` is unpackaged too: it is a
              ledger bound to this ground by sha256, and a copy in
              site-packages would be a second Manjuel nobody walks.

    [x]  9.2  CI — landed 2026-09-03. `.github/workflows/prove.yml`: both
              suites plus `law.py --prove`, on Windows AND Ubuntu, Python
              3.10 and 3.13. Ubuntu is in the matrix BECAUSE the ground is
              Windows and the record is CRLF — the terminator rules are
              declared in .gitattributes, and this proves they travel.
              `verify` is deliberately excluded (see TESTING.md).

              THE OFFLINE PROPERTY IS NOW A PUBLIC CLAIM. If a change makes
              the suites need a live model, that is the regression.

    [x]  9.3  index_roots.txt — REVISED AND CLOSED 2026-09-03. The task
              said ship an .example and gitignore the real one. That was
              WRONG on two counts, both checked before acting: nothing
              personal remains in it (worlds/manjuel came out at sitting
              78) and EIGHT STROKES READ IT, so gitignoring it would red
              the suites on a fresh clone — the exact machine CI exists to
              protect. Every path in it exists in any clone. It ships as a
              working default, and now says so in its own header.

    [x]  9.4  CONTRIBUTING.md — landed 2026-09-03. Covers the suites, the
              rule that shapes everything (no agent lands anything), the
              house style (reproduce then guard, stroke it both ways,
              rewrite a superseded stroke, report over gate), how to add a
              skill or a seat INCLUDING its .us record, the toll — with
              not paying it named as a legitimate outcome — and what this
              project will not take: a listening socket, a model that
              writes its own prompts or commit subjects, a second
              dependency.

    [x]  9.5  Voice is Windows-bound and DEGRADES ALONE — said in README
              where a stranger looks, and in CONTRIBUTING under Platform.

    [x]  9.6  THE RECORD SHIPS. Ruled 2026-09-03. SEAT_LOG, memory,
              DAYBOOK and sessions.jsonl stay tracked. A harness whose
              claim is "every guard is named after the failure that
              earned it" needs the failures visible, or the guards read
              as theory. Client references were scrubbed to [redacted]
              and worlds/ is untracked, so nothing confidential is in it.

    [-]  CHAT GATEWAYS AND AN ALWAYS-ON DAEMON. Not in this deliverable,
         and not an oversight. One comparable system had 40,214
         internet-exposed instances, most without authentication and a
         large share RCE-vulnerable; every one of those findings needs a
         LISTENING SOCKET. This ground binds nothing and serves nothing.
         Later, if ever, and behind `.us` records declaring remote: true —
         the shape git_push already uses, off unless the operator sets
         MANJUEL_GIT_REMOTE=1.

    [-]  THE C++ / HIP SUBSTRATE. Off the table by the operator's word,
         2026-09-03. Ollama is local, RULE 4 already holds, and a
         substrate rewrite is not a capability. Separate work exists
         outside this ground and is tied in later, not now.

---

## Layer 6 — the senses and the voice

    (nothing owed)

---

## Layer 7 — the door

    (nothing owed)

---

## DELIBERATELY NOT BEING BUILT

Kept so nobody re-derives them and starts.

    [-]  A GUARD FOR THE STALE ANSWER ABOVE.  A near-duplicate-of-previous-
         delivery check is cheap and arithmetic. Declined: HANDOFF's ruling
         of 2026-09-02 — "No fourth narrow gate: four detectors for
         'claimed an observation with no observation' is one fact told four
         ways." This would be a fifth, for a different fact. It goes in
         14.11's tally as evidence about the closing seat, not into the
         engine as another detector.

    [-]  DESIGN 14.10 uses 2 and 3 — structural strokes replacing the
         regex source-greps, and semantic slicing (`skills.py:_commit_subject`
         returning that function, not a character offset). Argued for, not
         scheduled. Read them before reaching for a regex over source; do
         not read them as a queue.

    [-]  THE TWO-TIER REFACTOR.  Named, understood, declined (session 1).

    [-]  THE SHORTLIST'S ACCURACY CASE.  It was built on a BUDGET argument.
         The accuracy measurement that declined it still stands.

    [-]  RE-TERMINATING law/*.md (was law/Archive/law/).  Those files are byte-hashed
         and the ledger binds the digests; changing a terminator is a
         RE-SEAL, the operator's act, not a sweep. `.gitattributes` freezes
         exactly that path and nothing else.

---

## From sitting 86 — the first live standup (2026-09-04)

    Each of these is a measurement, not a guess: the transcript is named.

    [ ]  THE DOOR QUOTES THE FURNITURE. "what does the covenant say?" was
         answered with nine numbered laws sourced from the `## The law`
         block in the seat's own prompt (which names four), after both
         reads were refused. logs/2026-09-04_153441_what_does_the_covenant_say.md
         Cheapest layer first: shorten the block for non-Router seats to
         one line ("the laws verified; you are bound by them"), or label
         it "not source material" the way the record is labelled. Then a
         stroke: a seat output that enumerates laws with no read this turn
         is the claim-check's shape with a new object.

    [x]  2026-09-08, 0.1.6 (the fifth sighting's shape: a short question
         about the seat itself is conversation). The earlier sightings'
         shapes stand as measured; if a sixth comes, its shape is new.
         KEYWORD BAIT AT THE DOOR, THIRD SIGHTING (fourth: sitting 88, the
         same greeting -> "an inquiry about sentiment analysis"; fifth:
         sitting 93, "Can you hear me?" -> the reader -> the Router called
         `speak` with nothing, 84s). "morning, what's on the
         board?" -> "Our objective is to answer a question about sentiment
         classification... classify_sentiment". The casual branch of the
         Steward prompt still lists nothing, so this one came from the
         roster in the dialogue/history. Proposed (HANDOFF 09-04, open 2):
         phrases for the door, keywords for the Router only.
         logs/2026-09-04_153342_morning_what_s_on_the_board.md

    [x]  2026-09-07. "WHAT IS IN THE <X> DIR" IS A LISTING, NOT A LOOKUP. asks_the_ground
         dispatched it to semantic_search; the Router chose skill_report.
         BUILT after the THIRD standup miss (sitting 90): intent.names_a_folder,
         checked on disk, ground_list with the folder as the argument.
         An alias/shape in intent for "what is in the <folder> dir/folder"
         -> ground_list with content=<folder> closes it at the cheapest
         layer. logs/2026-09-04_153415_what_is_in_the_skills_dir.md

    [~]  THE ROUTER FEEDS SENTENCES TO PATH TOOLS, STILL. Two refusals in
         one run ("'what files are in the ground' is a description of one")
         and semantic_search -- the named tool -- never called. The refusal
         text is right; the Router does not learn from it inside a turn.
         2026-09-07, sitting 88: three more (`ground/pipelines.md`,
         'list files in the ground', 'read the file'). BUILT the same day:
         the jail prefix is stripped; the operator's named file is checked
         and handed as the argument, and outranks a path that does not
         resolve; a wrong-folder name is answered with where the file is.
         The sentence-as-path itself is still the Router's habit.
         Measurement first: how often, over the day's logs, does a refused
         path call get followed by a correct one? If never, the follow-up
         hop should carry the named tool as the ONLY suggestion.
         logs/2026-09-04_153441_what_does_the_covenant_say.md

    [x]  2026-09-07. MANJUEL ON gemma4:12b DID NOT RULE. 283s, and the delivery was
         the salvage line "(deliberation only, no conclusion reached)" --
         BUILT: Context 16384 + THE RULING LOOP (MAX_RULING_TURNS = 3,
         thinking off on the retry). MEASURED sitting 88: ruled on turn 1,
         237s; sittings 90-92: ruled on turn 1 every time. The window was
         the fault.
         the thinking budget ate the answer (the sitting-79 shape). Options,
         cheapest first: a `Max Tokens` on agents/manjuel.md large enough
         for a thinking model; or thinking off for that seat if Ollama
         exposes it; or SITTING LAW 3 -- back to qwen3.5:9b, which ruled
         fine on 09-03. logs/ (the court transcript of sitting 86)

    [ ]  THE RACK DELIVERY DROPPED A MODEL. Eleven installed, ten listed
         (qwen3.5:9b missing) -- the door abridging a tool result. Class
         (a), small; the rack_report reading fault (sitting 85) is the big
         one and stands open above.

    [x]  UNATTENDED CLOSE WRITES ITS LEDGER LINE (cli._close). 2026-09-04.
    [x]  `git commit -m X` TAKES X (skills._commit_subject). 2026-09-04.
    [x]  THE SCAFFOLD PARROT REFUSED (pipeline._SCAFFOLD_RE). 2026-09-04.
    [x]  THE LAW GATE (manjuel/lawgate.py, REFUSALS §19). 2026-09-04.
    [x]  THE DOOR'S TOOL CALL CARRIED, BOTH COSTUMES (REFUSALS §18). 2026-09-04.

---

## From sitting 87 — Thursday night, 2026-09-04 (read 2026-09-07)

    [x]  2026-09-07. A FOLLOW-UP MUST NOT SKIP THE DOOR. asks_the_ground + the
         front-Steward skip sent "what does that last part mean?" to a
         Router that cannot see the thread. Shape: short, anaphoric, or
         quoting the previous delivery -> the door answers, the Router only
         if the door raises the flag. logs/2026-09-04_224401_*.md, _224409_*.md,
         _225023_*.md

    [x]  2026-09-07. NARROW THE SCAFFOLD GUARD, AND KEEP THE EVIDENCE. _SCAFFOLD_RE
         fires on "(recalled, ...)" anywhere, so a seat quoting a recalled
         turn is discarded as a recital, and its raw words are lost. Fire
         only when the output OPENS with the scaffold heading; put the
         discarded text in a note. THE HAND'S OWN BUG (built 09-04).

    [x]  2026-09-07. A FLAG MENTIONED IS NOT A FLAG RAISED. Run 6 raised `suspicious`
         and `hard` from prose about flags; the Reasoner woke for 235s.
         Decide by shape: a tag inside backticks or inside a sentence
         ("I'll use the <flags>...</flags> flag") is a mention. Stroke both
         ways. logs/2026-09-04_222426_*.md

    [x]  2026-09-07. MANJUEL ON gemma4:12b -- MEASURED TWICE, DID NOT RULE TWICE.
         Sittings 86 and 87. The operator's ruling: keep gemma, widen the
         window (16384), give the thinking room, cap the turns like the
         Router's -- THE RULING LOOP, three turns, thinking off on the
         retry. MEASURED sittings 88-92: ruled on turn 1 every court.

    [~]  2026-09-07. THE LAW BLOCK LEAKS (third sighting). FIRST LAYER BUILT: the
         block rides in the SYSTEM role now (pipeline.carried_blocks), not
         the user prompt, and the court's copy is labelled "not material,
         not counsel". A guard that refuses a delivery reciting it is NOT
         built -- measure the next sittings first.
         logs/2026-09-04_221829_*.md, _224528_*.md

    [x]  2026-09-07. A PARTIAL READ SPOKEN AS A WHOLE -- SEEN LIVE. Run 7 answered
         "what does this system need" from DESIGN.md part 1 of 6 without
         saying so. BUILT as THE PARTIAL-READ STAMP (see Layer 2's item).
         logs/2026-09-04_223934_*.md

    [ ]  THE DOOR COPIES THE RECORD'S LABELS. Run 13: "Router produced:",
         "The operator asked:" in the delivery. The closing prompt says not
         to; a 3B does anyway. Mechanism: strip lines that are the
         record's own labels. logs/2026-09-04_225023_*.md

---

## From sittings 89–93 — 2026-09-07 (the operator's, and four standups)

    Each is a measurement; the transcript is named.

    [x]  2026-09-08. THE SEAT BOUND. Sitting 92's court: Jesster on
         deepseek-r1:8b ran 760.6s and then llama-server returned 500
         ("output does not match the expected peg-native format"). The
         seat is on-fail: skip, so the court went on without the fool
         (972s for the case). LAW 7 bounds skills at 300s and seats at
         nothing. Built: SEAT_TIMEOUT 900 (his number, 2026-09-08),
         MANJUEL_SEAT_TIMEOUT to move it, `Timeout:` per seat beneath
         it; the stream is closed at the bound (a kill), the transport's
         read timeout covers a silent call; one named refusal. 1697.
         NOT MEASURED LIVE. logs/2026-09-07_114824_should_a_court_*.md

    [x]  2026-09-08. THE PER-SEAT NUMBERS. His words: "150 for steward
         300 for the router 600 max for the whole system." Steward 150,
         Router 300 (agents/*.md); the ceiling 600 (runtime, was 900 for
         two hours). The court takes the ceiling. NOT MEASURED LIVE.

    [x]  2026-09-08, 0.1.5: TURN_DEADLINE 600; OUT OF TIME in the
         delivery; a sub-run inherits the clock. NOT MEASURED LIVE.
         "NEVER MORE THAN 10 MINUTES BETWEEN A RESPONSE." The seat
         ceiling is 600, but a turn seats several -- a court is four,
         and `time align the logs` ran 1858s in sitting 95 with no seat
         over its bound. His sentence is a bound on the TURN, not the
         seat. Shape: a per-run deadline in the pipeline that skips
         the seats left when it passes and says so in the delivery.
         RULED 2026-09-08: "yea, that's fine" -- 600 on the turn. Parity
         is not the exception: "the whole parity thing is not run often
         ... we just use it for measurement between models when the
         'new batch' comes out" -- each parity case is one run and takes
         the same deadline. 0.1.5.

    [x]  2026-09-08, 0.1.6: seatlog.story_block off the ledger; to the
         door and the court; asks_the_sitting keeps the door. NOT MEASURED
         LIVE. THE SITTING STORY. Sitting 93: "What happened? Why did you suck
         so bad?" -> semantic_search over the whole record, 100s, and a
         delivery that said "the operator doesn't have access to see
         previous outputs in this session." No seat is handed what THIS
         sitting has done. The learning loop's first piece, discussed
         2026-09-07: an engine-kept block of the sitting's runs, tools,
         refusals and corrections, handed to the door and the closing
         seat, bounded like a window. logs/2026-09-07_120705_*.md

    [x]  2026-09-08, 0.1.6: the line in agents/router.md.
         THE ROUTER SAYS "I WROTE memory.md". Three courts running (88,
         90, 92) -- the write-claim check refuses it and, since 2026-09-07,
         keeps the search results beneath. The habit is a line in
         agents/router.md: it cannot write memory; `remember` proposes.

    [x]  2026-09-08, 0.1.6: rack_sync's Says:.
         "RACK REBUILD" HAS NO DOOR. Sitting 89, twice: no alias, no tool,
         and llama3.2 at the door invented ("provide the output of
         git_status and git_status again"; "a workflow file in the sitting
         87 record"). `rack_sync`'s Says: rack rebuild, rebuild the rack,
         resync the rack. logs/2026-09-07_095053_rack_rebuild.md, _095109_*.md

    [ ]  THE CLOSER RECITES ITS OWN INSTRUCTION. Sitting 89 run 6: the
         closing Steward delivered "The operator's words were a description
         or an opinion, and I should not have put them in the past tense as
         though they were accomplished" -- the closing prompt's NO TOOL RAN
         line, said back as the answer. Sitting 46's shape at the close.
         And the door in the same run answered the PREVIOUS question (the
         rack) -- the stale answer of sitting 77, second live sighting.
         logs/2026-09-07_095206_*.md

    [ ]  THE DOOR AT THE COURT RESTATES THE QUESTION. Sittings 88, 90, 91,
         92: the Steward's counsel on "should a court of three seats run on
         one model?" was one sentence in 0.4s -- the question as a claim.
         The court then ruled on a parrot. A door with nothing to say should
         say so, or the court pipeline should not seat it before the Router.
         The operator's call on the shape.

    [x]  2026-09-07. THE DECIDED CALL (sittings 90, 91). The engine named
         ground_list with the folder; qwen3.5:4b called skill_report four
         standups running. Now a tool with an argument checked on disk runs
         without the Router choosing; the Router reads once. 92: 10/10.

    [x]  2026-09-07. `inspect`, "remember that" + kinds, the brief, the
         words in SPEC -- built on "go on all 4". The brief has not run
         live; "remember that" has not been said at the door since it was
         built (sitting 89's "good job remember that!" predates it).

---

## OPEN — 2026-09-08 (condensed on the operator's order: "SCRUB YOUR WHOLE TASK LIST")

    The findings behind these are in CHANGELOG (Unreleased) and DAYBOOK
    Session 6; this is the list, one line each, nothing ticked kept.

    [ ]  the two sitting laws (5: nothing edited while a sitting is open;
         6: the rules and every law, directive and context file read, and
         law/SITTING_LAWS_2.md; his seal: python law\law.py direct
    [ ]  the door invents numbers (35 for 37; 34 for 37) -- stamp or reseat
    [ ]  a claim about a tool result with no citation is unchecked (s82)
    [ ]  the door parrots the record's labels / answers the previous
         question / ships an empty flag scaffold
    [ ]  `ground/` on the workspace reader (unjail read_file)
    [ ]  the tool-loop dedup is per Router sitting, not per run
    [ ]  history_block's unused limit; per-turn work that could be once
    [ ]  small honesty: dotenv unreadable .env; MANJUEL_OLLAMA_HOST unread;
         memory.pending swallows; lawgate cache stamp; seatlog "At close";
         supports_tools cache; parity 0.0s; drift docstring; spelling;
         voice deadline / temp file / `say --`; dead code (can_call,
         normalize, zscore, `if True:`); three anaphora sets; the fallback
         ESTATE_PIPELINE order
    [ ]  the release gate in prove.yml; BUILDMAP in index_roots (his call)
    [ ]  CRLF or LF (his call); the client token in old filenames (his call)
    [ ]  ESTATE LAW 2 as a gate on worlds/; LAWS 3 and 4 (his call)
    [ ]  rack_report facts-only; the door at court (his call)
    [ ]  0.1.5 / 0.1.6: restart, measure live, tag when he says

## Appended by the operator

<!-- Kyler: add below. Anything here outranks everything above it. -->

## 0.1.9 — THE DOOR AND THE ROUTE (his ruling 2026-09-10)

    His words for the whole of it: "a chatty front door with enough smarts to
    know when to route externally and actually use the tools/skills that it
    has access to through a larger routed system."

    Four of these five are ONE fault measured in different places: a seat
    saying something it did not get from a tool. The order is the order I
    would take them; the gate is unchanged and the tag is his.

    [ ]  THE CORPUS SPLIT (C+D, ruled 2026-09-10). semantic_search answers
         from SOURCES by default; the transcripts are a separate explicit
         reach; a log is indexed by its DELIVERY, not its mid-run reasoning.
         Measured: 81.5% of indexed documents and 60.6% of ranked passages
         are old runs; "what does the covenant say" returns eight old runs
         and never the covenant.
    [ ]  THE CITATION CHECK (SPEC 4.3, s82 finding 4). A claim about what a
         tool result SAID, with nothing tying it to the result. The largest
         piece left in the spec; C+D first, because a citation is only worth
         checking once the source is a source.
    [ ]  THE DOOR INVENTS NUMBERS (SPEC 4.7). "35 for 37"; "300 to 1200
         bytes" 2026-09-09. Intermittent, which is why a green gate is not
         evidence it is gone.
    [ ]  THE DOOR PARROTS. The record's labels; the previous question; an
         empty flag scaffold. Includes the mild case the new door prose
         showed on 2026-09-10 ("I can raise flags", echoed at him).
    [ ]  THE TOOL-LOOP DEDUP is per Router sitting, not per run.

    MOVED OUT, deliberately, to 0.1.10 (the seal): the gate in CI, ESTATE
    LAW 2 as a gate, SITTING LAW 5 sealed, the terminator ruling, the client
    token, and the small-honesty list. Half of that is his to rule.

    DONE SINCE THE 2026-09-08 SCRUB, so the lines above it are stale:
    rack_report facts-only (SPEC 4.3 MET); BUILDMAP in index_roots (he ruled
    it: "index everything"); phrases for the door (SPEC 4.2 MET); the release
    gate is READ AT BOOT though not yet in CI; SITTING_LAWS_2.md is written
    though not sealed onto the chain.

