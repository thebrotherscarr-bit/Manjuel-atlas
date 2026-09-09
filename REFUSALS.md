# What this estate refuses

Every refusal below is **arithmetic** — Python that runs before, or entirely
without, any model's judgement. None of them is a prompt asking a model to
behave. That distinction is the whole design: a prompt is a request, and a
request can be talked out of.

Each entry names the sitting that earned it. Nothing here was designed in
advance of a failure; every one of them exists because the estate did the
wrong thing once, in the record, and the record is in `logs/`.

Verify any of it yourself:

    python tests/test_manjuel.py     the strokes; every gate proven BOTH ways
    python law/law.py verify          the ledger; refuses a lying byte

---

## 1. Noise never wakes a seat

**Trigger.** The objective does not parse as language: mostly digits, no
word-like tokens, or fewer than half its tokens word-shaped.

**Action.** No seat is woken, no skill runs. The reply asks for a repeat.

**Why.** Sitting 22: keyboard mash raised `technical`, woke the Expert Coder,
and produced four stages of invented work about a request that meant nothing.
Seats improvise on noise, so noise is stopped before any seat sees it.

**Deliberately lenient:** one real word passes, and typos pass, because a typo
is still language.

---

## 2. Pasted material is refused before the Guardian reads it

**Trigger.** Injection markers in a `/paste` feed — instructions to ignore
prior instructions, attempts to re-instruct Manjuel, reaches for `.env` or
credentials, fishing for system prompts.

**Action.** The run is refused outright. **No seat reads the material**, and
the markers are named in the record.

**Why.** Sitting 39: an injection test feed sailed past the *model* Guardian
and moved Manjuel's hands — a skill ran, and 76 characters were spoken
aloud. A model gate rolls dice; this one does not. The Guardian model still
sits behind it for everything softer.

---

## 3. A seat may call only what it is cleared for

**Trigger.** A seat emits a tool call outside its `May Call:` line in
`agents/*.md`. **A seat with no such line may call nothing.**

**Action.** Refused at dispatch. Grant is by omission — an uncleared tool is
never even offered to the model.

**Why.** Before it existed, any seat could call anything. Counsel is *eyes,
never hands* (the operator's ruling, sitting 39), and that has to be enforced
rather than requested.

---

## 4. One write-path per Manjuel (LAW 8)

**Trigger.** A skill handler resolves a caller-supplied path. Every handler
that does so must declare it (`**Path Args:**`), and the gate checks the
declared argument at the single chokepoint in `SkillLibrary.execute()`.

**Action.** A path resolving outside its jail is refused, and the record says
`LAW 8 gate refused <skill>`.

**Why.** Five of twenty-six handlers were jailing their own paths privately,
and nothing could distinguish "this skill takes no path" from "this skill
forgot to jail one". A stroke reads `skills.py`'s own source and goes red if a
handler resolves a path without declaring it — because argument *names* lie:
`remember`'s `<filepath>` is a title, `rack_load`'s is a model tag.

---

## 5. Client data is sealed

**Trigger.** Any **one** of three tags on a file:

    a `vault/` path part          ·  a `.client.` in the name
    a `[[CLIENT]]` token in the first 2KB

**Action.** Refused by the indexer, the ground watcher, every reader
(`ground_read`, `read_file`) and every listing. A directory listing shows
`vault/ (N protected items — contents never listed)` — the count, never the
names.

**Why.** The operator's ruling, sitting 45: client data is of the highest
priority, never indexed, never used, never cross-referenced.

**Proven live, not merely asserted.** Sitting 61 ran a real semantic search
for a client's name against 3,601 chunks: five passages came back, **none from
the sealed world**, no vault path, no filename, no fragment. `index_roots.txt`
is the first line of that defence (the world is named in no root); the shield
is the second.

---

## 6. Keys are silent (LAW 9)

**Trigger.** A file named as a secret — `.env` and anything starting with it,
`secrets`, `credentials`, `id_rsa`, `apikey`, `token`, `*_secrets`, `*_key`,
and their kin — **by name, whatever the extension.**

**Action.** Never embedded, never indexed, never printed, never passed on a
command line where `ps` could read it.

**Why.** `.env` was being skipped by luck (no file extension), while `.yaml`,
`.ini` and `.cfg` *are* indexed — so a secrets file with one of those names
would have been embedded, and **an embedding cannot be unpublished.**

---

## 7. A claim about a file needs a read behind it

**Trigger.** A seat's output presents a named file's contents, and no reading
skill ran this turn.

**Action.** The claim is refused rather than delivered, and the fault is named
in the record.

**Why.** Sitting 56: "Can you read me the poem?" — one stage, no tools — and
the seat composed a new poem under the heading "Here is the content of
`poem_about_jesster.md`". The file existed and said something else. The
operator caught it, which is exactly the part that must not be the mechanism.

**Honest limits, stated in the code, not discovered later:** it catches a
claim that *names a file*; invention citing nothing passes. It proves a claim
**unsupported**, never false — which is enough, because LAW 5 says testimony
is not fact, and an unsupported claim of fact is what must not reach the
operator.

---

## 7b. A claim to have WRITTEN a file needs a writer behind it

**Trigger.** A seat says a file was saved, written, created or committed,
and no writing skill ran this turn.

**Action.** The claim is refused rather than delivered, and named in the
record.

**Why.** Sitting 70's closer: *"Yesterday, I compiled a poem about autumn,
saved it as 'poem.txt' in the Research folder, and successfully read it
back to you."* No yesterday, no file, no earlier reading — the one true
clause was that `speak` had run. The claim-check could not see it (that
wants a *contents* claim), nor the citation-check (that wants a search
result). Same arithmetic, new place: the turn's tool calls say whether any
writer ran.

**Same honest limits as §7:** it wants a NAMED file, so invention citing
nothing still passes, and it proves a claim **unsupported**, never false.

## 8. A cited search result must be a search result

**Trigger.** A seat's prose cites a path with a score, and this turn's search
returned no such result.

**Action.** The prose is withheld; the tool's own results stand alone.

**Why.** Sitting 61: the Router lifted a filename out of one result's *snippet*
and reported it as the top hit, carrying a *different* result's cosine — then
built a whole relationship between two unrelated things on that misread, and
the closer delivered it. Unlike uncited invention, this has ground truth: the
tool output is the exhaustive list of what exists this turn. Arithmetic.

---

## 9. The same call does not run twice

**Trigger.** A seat emits an identical `(skill, arguments)` twice in one turn.

**Action.** Not re-run. Told once that it already ran; if it repeats after
being told, the loop breaks — it is spinning.

**Why.** Sitting 63: one "remember the operator rules" request staged the same
rule three times, because the follow-up asked whether another skill was needed
and the Router answered by repeating itself. The step cap had been doing a
rule's job. This covers every skill — a doubled write or a doubled commit dies
here too.

---

## 10. Testimony is separated from fact at the line where they meet

**Trigger.** A seat writes prose after a tool result.

**Action.** The record splits them with a named boundary:
`--- <Seat> reading the above (testimony, not tool output) ---`.

**Why.** Sitting 63: a `memory.md` read came back with the file's headings
demoted to h5, and the Router's own summary above it demoted to h5 as well. In
the record the two were indistinguishable — a paraphrase read as file content.
Facts first, opinion after, and the record says which is which.

---

## 11b. A failure cannot be left out of the answer

**Trigger.** Any tool failed or was refused during a run.

**Action.** The delivery carries the list — what failed and why — appended
from what was recorded *as it happened*, whatever the closing seat wrote.

**Why.** Twice in two sittings a seat's prose contradicted its own record
without inventing anything: the Quartermaster read `15.0GB of ~15.0GB, ~0.0
headroom` and called the card "comfortable and functioning optimally"; the
closer delivered "no new issues or concerns" over a run holding a
326-second timeout under a THIS TOOL FAILED banner. **Omission, not
invention** — which is why the claim-check (nothing cited) and the
citation-check (no result quoted) both let it through.

The recompose is arithmetic and **not another seat**: a model summarising a
record and dropping the failures is the disease, so a second model
summarising would be more of it. It makes no judgement about the seat's
words and does not read them for all-clear language. The facts travel with
the answer every time, and a seat that reported them honestly is simply
corroborated.

## 11. A failed tool cannot be reported as a success

**Trigger.** A skill returns an error, refusal, or "cannot".

**Action.** The result is wrapped: `THIS TOOL FAILED — NOTHING WAS DONE. Do
not report success, contents, or findings from it.`

**Why.** Sitting 40: an errored read was narrated as "successfully opened" and
the file's contents were invented on top of the failure.

---

## 12. Manjuel never lands anything (LAW 6 / RULE 6)

**Trigger.** Any act that commits the operator: a git commit or push, a memory
entry, a spend.

**Action.** Prepared, staged, and handed over. **Never landed.** Memory
proposals are stamped `GENERATED` in `memory/pending.jsonl` and reach
`memory.md` only when the operator lands them with `/memory`. Remote git
(pull/push) is refused unless `MANJUEL_GIT_REMOTE=1` — a push cannot be
recalled once fetched, so it is the operator's act, not a seat's. Model
downloads (`rack_pull`) are off behind their own switch: they cross the
network and can move gigabytes onto the machine.

---

## 13. The ground is `Desktop\Research`, and nothing reaches outside it

**Trigger.** Any read, write, index root, or runtime dependency resolving
outside the ground.

**Action.** Refused. A stroke fails if any index root escapes Research, and
the workspace jail collapses traversal attempts.

**Why.** The operator's standing rule, written after this was broken: checking
counts as reaching, and a yes covers one act, once — never the next file,
never the next session. Full text in `CLAUDE.md`.

---

## 14. Everything is bounded

    tool loop        5 hops, and an identical call is not one of them
    review -> repeat ONE pass back through the tools when a review finds
                     the work unfinished; the second request is refused and
                     the gap is named to the operator instead
    skill execution  SKILL_TIMEOUT bounds the WAIT (not the work — stated
                     plainly in the code rather than hidden)
    speech           capped, and says so when it truncates
    seat output      Max Tokens per seat, declared in agents/*.md
    VRAM             a budget with headroom, foreign models never evicted

LAW 7: bounded everything. An unbounded thing on a single machine is an
outage waiting for a bad afternoon.

---

## 15. Code the coder emits is PARSED before it is written

**Trigger.** The Expert Coder declares a file. Before it lands, `ast.parse`
runs on it and the tree is walked.

**Action.** Refused, by proof and not by prompt, when the code: does not
parse (the syntax error and its line are named); imports `requests`,
`urllib`, `socket` or `http`; imports `importlib`; or calls `eval`, `exec`,
`__import__`, or anything with `shell=True`.

**Why.** RULE 4 says the estate is local. Until 2026-09-03 that was a
REQUEST — a line in CLAUDE.md obeyed by whichever model sat on the coder's
seat. `ast` makes it arithmetic. And a file that did not parse used to land
anyway, after which the Quality Evaluator reviewed it as prose, because it
reads what is on disk and cannot tell the difference.

**IT FAILS OPEN, DELIBERATELY.** A non-Python emission is NOT refused — it
lands with `landed UNINSPECTED -- not checked: x.md is not Python` in the
record. A gate that silently passes what it cannot read spends your trust
on a check that did not happen.

**Three honest limits, in the docstring rather than discovered later:**
`shell=True` is flagged on ANY call, not only subprocess's (over-refusing on
a write gate is recoverable; under-refusing is not). A module reached by
getattr, a `__builtins__` lookup, or an import spelled through a variable is
still uncaught — NARROWED, NOT SEALED. And it proves what the SOURCE says,
never what the code does when run; nothing here executes the file.

---

## 16. A large eviction from the index is refused

**Trigger.** A refresh finds documents under a root that `index_roots.txt`
no longer declares, and they are more than 25% of the corpus.

**Action.** Nothing is evicted. The count, the share, and the remedy are
reported: check `index_roots.txt`; run `index_ground rebuild` if it is right.

**Why.** Sitting 78: `worlds/manjuel` was removed from the roots and 91 of
801 documents from that world stayed in the index and kept answering,
because `prune()` asked only whether the FILE was gone and every file still
existed. Teaching it to ask about scope made a refresh destructive in a way
it had never been — a typo in a config file would silently empty a root on
the next run. So the guard performs the small correction and refuses the
large one. A bound is not a rule; this is the rule, and the bound is on the
mistake.

---

## 17. The manifest is checked against the code

**Trigger.** `python -m manjuel.us`.

**Action.** Every `us/*.us` record is compared to the thing it names:
declared-vs-present both ways for skills and seats, `wall` present, `writes`
against WRITING_SKILLS, `remote` against the gated set, `model` against the
seat, `source` exists, `may_call` against May Call, `permission.edit`
against write clearance, and `can_approve` FALSE EVERYWHERE. It REPORTS and
exits 0 — the manifest describes a ground the operator edits by hand, so an
assertion over it would go red because he added a skill.

**Why.** The manifest declared what every skill may reach and NOTHING
CHECKED IT. Twenty of thirty-five skills had no record at all; ten of eleven
seat records named a model the seat had not run in weeks; and the Router
declared `read: agent_workspace only` while cleared for `May Call: all`,
which includes every ground reader. A declaration nobody checks is a
promise, and LAW 5 applies to the manifest exactly as it applies to a seat.

**A check that cannot run says so.** With no rack reachable, the model-tag
comparison reports "not checked" rather than passing. A reconciler finding
nothing looks identical to a clean ground, and telling those apart is the
whole value.

## 18. A door's tool call is carried, never printed — and only the Router holds tools

**Sitting 84, 2026-09-04.** The first run on llama3.2 at the front door.
"review the changelog" raised no flag, the Router was skipped, and the
Steward delivered `<action>ground_read</action><filepath>rack.md</filepath>`
as its whole answer. The Steward has a May Call list; llama3.2 supports
native tools; the engine had handed it schemas; it called one, as a
tool-trained model does; the runtime rendered the call as the estate's
action block; and only the route stage executes action blocks. The ask
went nowhere and the markup went to the operator. phi4-mini had hidden the
hole for three days by mostly obeying "never answer with tool names".

**Two things, by the operator's ruling (option B: one executor):**

- A seat that is not the Router is **not handed tool schemas**, whatever
  its model supports and whatever its May Call says. Tools go to the seat
  that runs them.
- A non-Router seat that answers in markup anyway is **asking for a tool**:
  `needs_tool` rises, the skill it named becomes the Router's named tool,
  the arguments it gave are the floor under the Router's call, and the
  markup is stripped. The Router applies its own clearance — a door naming
  a skill the table may not call gets a refusal from the seat that holds
  the gate, not a silent run. A markup ask for something that is not a
  skill is dropped and named in the record.

`strip_control` now strips an action block from anything a person reads,
but ONLY when an `<action>` is present: the Expert Coder's bare
`<filepath>` declaration, which `land_code` reads after the strip, is
untouched. Stroked both ways and the schema half directly:
`test_a_door_that_calls_a_tool_hands_it_to_the_router`.

**What this is not.** It does not make the door a second executor (option
A, declined). One seat acts; the rest ask.

## 19. THE LAW GATE — every run passes through the law before any seat sits

**The operator's ruling, 2026-09-04:** "EVERY single call, no matter what,
runs THROUGH the law." The same rule he wrote for the hands that morning
(CLAUDE.md RULE 0), applied to the seats. Built the same day: `manjuel/lawgate.py`,
called first thing in `run_pipeline`, after the gibberish gate and before
intent decides anything.

**What it does, in order, on every run:**

1. **Walks the chain.** `law/chain.jsonl` is verified with the pen -- the
   same three walks `law.py verify` makes -- and every sealed law's
   fingerprint is checked against the file on disk. A law that does not
   verify refuses **every** run: "no seat sits on a law that cannot be
   trusted (LAW 4: a red blocks the road)." A ground with no ledger at all
   (a bare clone, a test workspace) is not a broken Manjuel; the gate says so
   in the record and runs on the rules alone.
2. **Checks the objective** against what a regex can decide: a reach
   outside the ground (`..`, a drive letter, `~`, `/home` -- RULE 1 / LAW
   8; the ground's own path is not a reach), a reach for a secret by name
   with a verb that would surface it (LAW 9), a reach across the wall while
   remote operations are off (`git push`, `ollama pull`, `pip install`,
   `curl` -- LAW 6 / RULE 4), and client material named by tag
   (`vault/`, `.client.` -- SITTING LAW 2). A hit refuses the run with the
   law named. No seat read it.
3. **Hands every seat the law as fact** -- a `## The law` block, the
   Manjuel verified, at which head, and which checks this request passed.
   Appended to the user prompt until 2026-09-07; in the SYSTEM role since
   (§20), where a small model does not recite it as content. A seat cannot
   claim it was not told; a reader of the transcript can see it was.
4. **Stamps the record**: `law: chain whole (4 links, head ...); objective
   passed 4 checks`, or the refusal, one note per run, machine-emitted.

**What it is not.** It decides what a regex can decide and nothing softer;
the Guardian, the claim-check, the citation-check and the recompose stand
behind it. It proves the laws are unchanged since sealing; it cannot prove
a seat obeyed them. It reads the objective; pasted material has its own
gate (§2). Stroked: `test_the_law_gate` -- a tampered law refuses every
run and no seat sits; each of the four checks fires on its shape and not
on a plain question; the operator's own path and a local commit pass;
every seat that sat saw the block; the record carries the stamp; a
ledger-less ground passes on the rules and says so.

---

## 20. THE CLAUDE.md SYSTEM, and THE RULING LOOP — what a seat is handed beside its prompt, and how long it may think

**The operator, 2026-09-07:** "make sure we are looking at how the
claude.md works and implementing that system into Manjuel", and, on
Manjuel: "expanding his context and letting him give some room for
thinking, but limit his turns ... kind of like the router is limited."

**The law in the SYSTEM role** (`pipeline.carried_blocks`, `_seat_for_call`).
§19's `## The law` block used to be appended to the USER prompt. Sittings
86 and 87 showed four seats reciting it back as content -- a small model
copies what sits beside the material. CLAUDE.md reaches the hand as
system text, never inside the operator's message; the seats get the same
shape now: the block rides beside the seat's own system prompt
(`dataclasses.replace` for this call; the registry's declaration is never
written). A BAKED seat has no system role and keeps the old shape. The
record keeps what rode in the system role (StepResult.prompt), so the
prompts companion still shows the seat was told.

**The ten, verbatim, for the court** (`lawgate.laws_text`, `Verdict.block(full=)`).
The hand reads 3KB of law every turn (RULE 0); a seat that RULES on the
record was reading sixty words about it. The court seats -- the ones the
advisory builder serves -- are handed the ten estate laws as sealed, read
from `law/ESTATE_LAWS.md` and never re-typed in code, labelled "not
material, not counsel, never quoted as either". The door, the Router and
the Guardian keep the short form; cost matters there.

**The standing** (`seatlog.standing_block`, `RunContext.standing`). CLAUDE.md
READ FIRST: "you begin with total amnesia; DAYBOOK's last entry is the
only file that carries intent." Every seat began with amnesia too, and
sitting 87's toll said so. The last DAYBOOK entry's **Standing**, **The
plan** and **Next session** lines, bounded to 1,800 characters, labelled
as record, built ONCE at sitting open and handed to the Steward and the
court on every run. Not the Router (budget; it routes). Read, never
generated: no DAYBOOK, no block.

**The partial-read stamp** (`pipeline.note_partial_read`, `unread_parts`,
`recompose`) -- SITTING LAW 1 for the seats. `windowed()` already said
"THIS IS NOT THE WHOLE FILE" in capitals; nothing carried it past the
seat. Now every read that returns a numbered window, a section, one
definition or the map is recorded as it happens, and the delivery ends
with READ IN PART, NOT WHOLE and the files named -- unless every numbered
part of the file was read this run, in which case it was read whole and
is not listed. Sitting 87 run 7: an answer from 12,000 of DESIGN.md's
63,000 characters, unmarked. Arithmetic over the tool's own first line.

**The ruling loop** (`pipeline._press_for_ruling`, `MAX_RULING_TURNS = 3`,
`runtime.chat(think=)`). Manjuel on gemma4:12b thought for 13–15k
characters twice and ruled on nothing; the court's delivery was the
salvage line. A seat that comes back with the salvage line is now asked
again -- the same prompt, its own deliberation appended as ITS OWN WORDS
(never as material), "RULE NOW", and Ollama's thinking switch OFF for the
retry -- up to three sittings in all. Then what it has stands and the
record says the turns were spent. The Router is never pressed: its loop is
the tool loop (§9). A runtime that cannot switch thinking off still gets
the bounded retry. Manjuel's window is 16384 (agents/manjuel.md).

**What it is not.** Moving the law to the system role is the first layer
against the recital; a guard that REFUSES a delivery reciting it is not
built, on purpose, until the next sittings are measured. The standing does
not refresh mid-sitting (RULE 9's shape: nothing moves under his hands).
The loop bounds turns, not seconds: three turns of a two-minute seat is
six minutes, and the cap is the operator's to raise or lower. Stroked:
`test_the_claude_md_system_and_the_ruling_loop` (48), `test_the_law_gate`
(prompt clean, soul told).

---

## 21. THE BOUNDS OF 2026-09-08 — a seat, a turn, one index build, and the tag

The operator, the same morning: "150 for steward 300 for the router 600
max for the whole system. there should never be more than 10 minutes
between a response, thats absurd." Every refusal here is arithmetic on a
clock or a lock; no model is asked.

- **A seat call past its bound is cut** (`runtime.SeatTimeout`). The
  bound is the seat's own `Timeout:` (agents/*.md, by model size: 150 /
  300 / 600 / 700, his words of the afternoon) or the ceiling
  `SEAT_TIMEOUT` = 700 (`MANJUEL_SEAT_TIMEOUT`). Two halves: httpx's read
  timeout for a call that answers nothing (connect held at 10s), and a
  wall clock on the stream that CLOSES it for a call that never stops --
  Ollama stops generating. One named refusal; `on-fail: skip` goes on
  without the seat. Earned: sitting 92, Jesster 760s then a 500.
- **A seat whose turn comes after the turn's deadline is not seated**
  (`pipeline.TURN_DEADLINE` = 600, `MANJUEL_TURN_DEADLINE`). Named in
  the record and in the delivery under OUT OF TIME (the recompose's third
  block, beside NOT EVERYTHING RAN and READ IN PART); a seat seated just
  before the line is cut to the seconds left (`_within_deadline`); a
  sub-run inherits its parent's clock; a run where nobody sat still
  delivers the block, from the Gate. Earned: sitting 95, `time align the
  logs`, 1858s with no seat past its bound.
- **A second index build while one runs is refused by name**
  (`skills._INDEX_BUSY`, held for the life of the build, refusal or not;
  `index_ground` and `embed_text` share it). **A rebuild that cannot
  discard the old file is refused**, not pretended (`_open_index`).
  Earned: sitting 94, two builds on one vectors.db, `UNIQUE constraint
  failed: docs.path`, and a seat log that said "finished".
- **The tag is refused by name** (`tests/release.py --check`): suites
  green and after the newest edit, buildmap, the standup live, the law,
  the manifest, SPEC-vs-CHANGELOG, DAYBOOK closed, HANDOFF today, the
  hands ledger closed. Reads only. RUNBOOK "Before a tag".
- Smaller, the same day (the REPL read): Manjuel's own writes
  (`sessions/`, SEAT_LOG.md, memory.md, rack.md, the suites' stamps) no
  longer queue a re-embed every turn (`watch._SELF_WRITTEN`); a palette
  command whose Runs: is a command is refused before it re-enters the
  loop; `/chat` ends after three failed listens; a paid sitting is not
  closed twice; an exception nothing caught still closes the sitting;
  `git_pull`/`git_push` are writers for the write-claim check; one git
  read at open.

- **Seats that failed reach the delivery** (the recompose's fourth block,
  SEATS THAT FAILED, from StepResult.error) -- sitting 96's court said
  OUT OF TIME for Manjuel and nothing of Jesster's 577s.
- **A refused feed is withheld from the transcript** (`transcript.write`):
  the delivery is the refusal; the source is described, never copied.
  Earned: the injection case's payload in logs/, an index root.
- **An unknown skill name is answered by the Gate** with the nearest real
  names; no seat sits (`_unknown_skill_word`). Earned: sitting 95,
  `index_workspace rebuild`, the door answering the previous question.
- **`<keyword> <words>` is decided** for a reading or prompt skill --
  the words are the argument; a Takes: match decides too; a writer is
  never decided from words (`decided_call`, `named_by = "the words"`).
- **A prompt skill with only the order as payload is refused** before
  the model is called (`_run_prompt_skill`): "time align the logs" is a
  request for material, not material.
- **The brief's numbers are checked** against the facts the door was
  handed (`cli._unsourced`); the invented ones are named beneath.
- **The standup judges seats** (`tests/standup.py`): failed stages, OUT
  OF TIME, the seats a case names, the judge's last word, and THE NUMBER
  CHECK -- a number in the delivery from no tool result is a miss.
- **The ruling loop is twelve** (`MAX_RULING_TURNS`, his number); the
  turn's clock is what keeps twelve honest.

Stroked: `test_the_seat_bound`, `test_the_turn_deadline`,
`test_the_loops_of_2026_09_08`, `test_the_release_gate`,
`test_the_p0_of_the_review`.

---

## 22. THE STORY AND THE HANDS (0.1.6, 2026-09-08) — what a seat is told about THIS sitting, and what a hand writes down about itself

- **The door and the court are handed THE SITTING STORY** -- every run of
  this sitting so far, read off the ledger line the engine wrote as each
  run ended (objective, seconds, tools, guards, seats that failed or ran
  out of time, the first line delivered), newest last, bounded at 1800
  characters; the oldest fold into a counted line that points at logs/
  and the index. Not the Router. Earned: sitting 93, "what happened? why
  did you suck so bad?" -> a search over the whole record -> "the
  operator doesn't have access to see previous outputs in this session."
- **A question about this sitting keeps the door** (`intent.asks_the_
  sitting`): a reader dispatch guessed from the words is withdrawn; a
  tool the operator named is still his order; with no story yet (the
  first run) nothing changes.
  the fingerprints of the rules as read, HEAD, the DAYBOOK entry and
  HANDOFF block read, the newest sitting seen; closed with HEAD, the
  files edited, the strokes, restart required or not. The brief prints
  the last hand; an OPEN hand is flagged; the release gate refuses a tag
  over an unclosed hand. Earned: 2026-09-08, a hand that ran `git
  status` before reading CLAUDE.md and left the lock the file warns of,
  and a record that held what the hand believed, never what it read.
- **A kind is one word** (`cli._ask_kind`); **`rack rebuild` has a door**
  (rack_sync's Says:); **a short question about the seat itself is
  conversation** (`asks_the_ground`: four words or fewer, addressed to
  "you"); **the Router is told it cannot write memory** (agents/router.md).

Stroked: `test_the_story_and_the_hands`.

---

## What this does NOT protect against

Stated plainly, because a security page that only lists wins is marketing.

- **Invention that cites nothing.** A seat can still state something false in
  ordinary prose with no file named and no result cited. Sitting 60 produced a
  confident paragraph about a real client's work, sourced from nowhere. The
  answer to that class is *dispatch* — a question about the ground now reaches
  a reader, so the void that invention fills is smaller — but the class is not
  closed and may not be closeable by arithmetic alone.
- **A model's judgement, where judgement is the job.** The Guardian, the
  Evaluator and the Router make calls a gate cannot make for them.
- **A PARTIAL read spoken as a whole one.** `windowed()` hands a big file
  over as "part 1 of 7 — THIS IS NOT THE WHOLE FILE" in capitals, with a map
  of the headings it did not show. The claim-check then asks only whether A
  READ RAN this turn — part 1 ran, so it passes, and a seat that saw 9% can
  speak about 100%. Named 2026-09-03 after an agent did exactly this to
  `parity.py` and was wrong twice in one turn. BUILT 2026-09-07 as the
  partial-read stamp (§20): the delivery now SAYS the read was partial.
  What is still not caught is the harder half -- a claim about what a read
  SAID with nothing tying it to the read (TASKS, Layer 7).
- **The operator.** Nothing here binds him, and it is not trying to. He is the
  one who lands, and the estate's honesty exists so that what he lands is
  informed.
