# SPEC — what manjuel is, and when it is done

Written 2026-09-04 on the operator's word ("getting close to an actual
product, review missing specs, and write full spec -- 'when done'"), from a
full read of the code, the record and the laws. This is the one document
that says what the thing IS and what DONE means. DESIGN.md is the reasoning
and its history; BUILDPATH.md is the module map; BUILDMAP.md is where each
thing lives; REFUSALS.md is what each guard refuses; this is the contract.

A line here is either MET (with where it is proved), OPEN (with what is
missing), or RULED OUT (with who ruled). Nothing here is aspiration
wearing a checkbox.

---

## 1. What it is

**manjuel is a local, sequential, markdown-declared council of small
language models that answers an operator at his own terminal, where every
tool call is executed by exactly one seat, every claim a seat makes is
checked against what actually ran, every run is written down, and every
run passes through a sealed law before any model reads a word.**

Plain version: one person types a request. A few small models, each with a
job written in a markdown file, take turns on it. One of them — the Router —
is the only one allowed to run tools. The engine, not the models, decides
what is a fact: it records what tools returned, refuses a model that claims
to have read or written something it did not, appends every failure to the
answer whether the model mentioned it or not, and stamps every run with
which laws it checked. Nothing leaves the machine.

### Who it is for

The operator. One person, one machine, one folder (`Desktop\Research`). It
is not a service, not multi-user, not hosted. A second user is a fork.

### What it is for (the operator's words, session 2)

*"RUN IT AND WRITE DOWN WHAT FEELS OFF."* The product is a harness that makes
small local models SAFE TO USE and HONEST ABOUT THEMSELVES, so the operator
can hand them real work on his own files and trust the record more than the
prose. Every guard in it is named after a failure that actually happened.

### What it is not (RULED OUT)

- Not a cloud product, not an API client, not a model host. RULE 4.
- Not a second executor. One seat runs tools. Option A declined 2026-09-04.
- Not a bigger-model project. SITTING LAW 3: move up only on a measured
  failure.
- Not a general agent framework. It has fourteen named seats and thirty-seven
  named skills, and adding one is writing a markdown file, not code.
- Not a chat app with memory. `memory.md` is landed by the operator's hand
  (`/remember`, `/memory`, or `remember that` typed at the door); a model
  may only propose.

### The words (ruled 2026-09-07: "fix the name spread")

The vocabulary of this ground, in one place. THREE RULES: no new noun
without a line here; a name is a word from the operator's own record or
the plain English of the thing; every line says where the word came from.
A proposal that needs a word uses the nearest one below.

| word | means | from |
|---|---|---|
| **the ground** | `Desktop\Research`, the one folder. Seats read it; nothing reads outside it. | CLAUDE.md RULE 1, 2026-08-29 |
| **the workspace** | `agent_workspace/`, the seats' scratch: the ONLY place a seat writes, and where anything from outside lands first. | sittings 18–27, 2026-08-29 |
| **the estate** | the whole system: the seats, the law, the record, the rack. | the founding docs (LAW_001) |
| **a seat** | one job, one markdown file in `agents/`, one model on it. | agents/, DESIGN.md |
| **the rack** | the models installed on this machine; also the seats that rest until a flag wakes them. | rack.md; pipelines.md |
| **the spine** | the seats that sit every run of a pipeline. | pipelines.md |
| **the door** | the Steward: first to answer, last to report. | pipelines.md |
| **the court** | Neiro, Jesster, Manjuel: reads, never acts; Manjuel rules last. | THE LAW; pipelines.md |
| **the Router** | the one seat that runs tools. | DESIGN.md |
| **a skill** | one tool: a markdown file in `skills/` and a handler. | skills/ |
| **a pipeline** | ONE TURN's running order of seats and tools: who sits, in what order, who wakes on which flag, which seat hands to which. The Steward handing to the Router, the Router calling the index, Jesster reviewing what the Router read -- all inside one pipeline. Declared in `pipelines.md`. | pipelines.md; ruled 2026-09-07 |
| **a workflow** | SEVERAL TURNS strung into one task: a list of objectives, each run through a pipeline, checked between steps, reported at the end. The standup is the first one. Not yet declared in a file. | the operator, 2026-09-04 and 2026-09-07 |
| **a flag** | a seat's one-word signal to the engine (`needs_tool`, `technical`, `worked`); wakes a racked seat. | DESIGN.md §5 |
| **a sitting** | one launch of the REPL, numbered by Manjuel. Never the hand's session. | seatlog.py; LAW 10 |
| **the toll** | what a sitting pays at close: what proved, what is thin, what is owed. | LAW 10 |
| **the record** | everything written down: transcripts, SEAT_LOG, DAYBOOK, HANDOFF, CHANGELOG, memory.md, sessions. | LAW 1, LAW 10 |
| **the standing** | what this sitting is for, from DAYBOOK's last entry, handed to the door and the court. | 2026-09-07 |
| **the law** | the ten estate laws (seats) and the sitting laws (hands), sealed in `law/`; the gate every run passes. | law/ |
| **a hand** | any agent, human or model, working the ground in a sitting. Bound by the sitting laws, not the estate laws. | SITTING_LAWS.md |
| **a stroke** | one check in the suites. Green or red. | tests/ |
| **a guard** | a refusal the engine makes by arithmetic, named after the failure that earned it. | REFUSALS.md |
| **a layer** | BUILDPATH's word for a tier of the code (0 words on disk … 9 a stranger's first hour). A code word, not a name for findings -- two TASKS headings that misused it were renamed 2026-09-07. | BUILDPATH.md |
| **the brief** | the sitting opener: where the build is, what he said we are working on, what is waiting -- read off the record at every open; `/brief` has the door say it. | the operator, 2026-09-07; built the same day |
| **inspect** | the skill that reports a file's FACTS before anything reads it -- size, type by bytes, timestamp, jail, git, index, secret/client, injection markers -- never its contents. The workspace is the quarantine it serves. | sittings 18–27 (2026-08-29); the operator, 2026-09-07 |
| **remember that** | the operator's cue at the door that lands a memory: his words after it, else the newest proposal, else the last delivery. Never a seat's. | sitting 89; built 2026-09-07 |
| **a kind** | the one word on a memory entry saying what it is: guidance, decision, ruling, learning, outcome, note. | the operator, 2026-09-07 |
| **the release gate** | one command before a tag that refuses by name until the record is whole; `tests/release.py --check`. | the operator, 2026-09-08 ("reviewed, updated, and logged, at all times"); built the same day |
| **the story** | what THIS sitting has done so far, read off the ledger and handed to the door and the court; bounded like a window. | the operator, 2026-09-07 ("keep that in context for now") and 2026-09-08; built 2026-09-08 (0.1.6) |
| **out of time** | a seat not seated because the turn's deadline had passed; named in the delivery. | the operator, 2026-09-08 ("never more than 10 minutes between a response") |

---

## 2. The parts, and the contract each one keeps

| part | what it promises | proved by |
|---|---|---|
| **The ground** (`Desktop\Research`) | every read, write, index and dependency stays inside it | `gate_paths` (LAW 8), `_inside_ground`, `safe_path`; the law gate's reach check; strokes `test_index_stays_in_research_and_off_the_keys`, `test_the_law_gate` |
| **Seats** (`agents/*.md`, 14) | a seat is a markdown file: model, stage, when it wakes, what it may call, its prompt. No seat exists in code. | `registry.py`; `us/chain_*.us` reconciled by `us.py` |
| **Skills** (`skills/*.md`, 37) | a skill's markdown declares it; a handler or a model target runs it; neither can exist without the other | `SkillLibrary.validate`; `us.py` |
| **Pipelines** (`pipelines.md`, 5) | the running order is a file; racked seats wake on flags declared in their own file | `PipelineBook`; `seating.py` |
| **The Router** | the ONLY seat handed tool schemas and the only one whose action blocks execute; bounded at 5 hops; identical calls refused | `pipeline.py` tool loop; REFUSALS §9, §14, §18 |
| **The door** (the Steward) | speaks in words; a tool call it emits is carried to the Router, never printed; after work it reports what ran and nothing beyond | REFUSALS §18; the closing prompt's `TOOLS THAT ACTUALLY RAN` |
| **The court** (Neiro, Jesster, Manjuel) | reviews, never acts; reads only; four different heads; rules last | `review_only`; REFUSALS §3; the 2026-09-04 rack ruling |
| **The guards** | a claim of file contents with no read is refused; a claim of a write with no writer is refused; a cited search hit that was not returned is refused; every failed tool AND every partial read is appended to the delivery; a recited scaffold is discarded | REFUSALS §8, §10, §11, §11b, §20; `_SCAFFOLD_RE`; `recompose` |
| **The law gate** | the sealed ledger verifies on every run or no seat sits; the objective is checked against the decidable laws; every seat is handed the verdict in its SYSTEM role (the court: the ten verbatim); the run is stamped | `lawgate.py`; REFUSALS §19, §20; `test_the_law_gate` |
| **The standing** | what the sitting is FOR, from DAYBOOK's last entry, read not generated, handed to the door and the court | `seatlog.standing_block`; REFUSALS §20 |
| **The story** | what the sitting has DONE, from its own ledger lines, read not generated, handed to the door and the court; "what happened?" is answered from it | `seatlog.story_block`, `note_for`; `intent.asks_the_sitting`; REFUSALS §22 |
| **The ruling loop** | a seat that thought and did not rule is asked again, thinking off, at most three times; the Router is never looped | `MAX_RULING_TURNS`; `_press_for_ruling`; REFUSALS §20 |
| **The bounds** | one seat call: its `Timeout:` by model size (150/300/600/700) or the 700s ceiling, cut at the wire; one turn: 600s, the seats after it named OUT OF TIME, the seats that failed named too; one index build at a time; twelve ruling turns | `runtime.SEAT_TIMEOUT`, `pipeline.TURN_DEADLINE`, `skills._INDEX_BUSY`; REFUSALS §21 |
| **The release gate** | a tag is refused by name until the record is whole: suites, buildmap, standup, law, manifest, SPEC↔CHANGELOG, DAYBOOK, HANDOFF, hands | `tests/release.py --check`; RUNBOOK "Before a tag" |
| **The record** | every run is a transcript; every sitting is a numbered line and a toll; memory is landed by hand; nothing is deleted | `transcript.py`, `seatlog.py`, `memory.py`; LAW 1, LAW 10 |
| **The index** | chunked, incremental, bounded, embedder-stamped; client material and secrets never enter it; transcripts age out of retrieval at 45 days | `vectors.py`; REFUSALS §5, §6, §16 |
| **The rack** | seven models seat fourteen seats; the everyday pipelines fit resident; the court evicts on purpose; `rack.md` is derived from Ollama, never edited | `vram.py`, `rack.py`; `test_vram` |
| **The suites** | the engine proves offline with every model stubbed; the REPL proves the same way; the standup runs the seats live and writes a report; the map is generated from the code | `tests/test_manjuel.py`, `smoke_cli.py`, `standup.py`, `buildmap.py` |
| **The toll** | every sitting ends with what proved, what is thin, what is owed — the operator's words, or an honest "not stated" | `seatlog.render_toll`; LAW 10 |

---

## 3. The invariants (what is never true)

These hold on every run, and each has a stroke or a gate. If one of these
is ever observed false, that is the bug, before anything else.

1. No model output is executed as instruction. (LAW 5; `mathkit.parse_numbers`, `voice._speech_cmd`, `inspect_code`)
2. No seat but the Router executes a tool; no seat but the Router is handed schemas. (REFUSALS §18)
3. No control markup — `<action>`, `<flags>`, a JSON tool call, the dialogue scaffold — reaches a delivery. (`strip_control`, `_SCAFFOLD_RE`; the standup's `NEVER_IN_DELIVERY`)
4. No path resolves outside its jail; no absolute path is accepted from a model. (`gate_paths`)
5. No secret is read, indexed, printed or committed. (`is_secret`; `dotenv.report`; the law gate)
6. No client-tagged file is read, indexed, listed or cross-referenced. (`is_protected`; SITTING LAW 2)
7. No commit, push, pull, pull-of-a-model or spend happens without the operator; local commit is the one ruled exception and it is additive. (`gitstate`, `rack_pull`; RULE 6)
8. No run proceeds on a law that does not verify. (the law gate)
9. No failure is omitted from a delivery. (`recompose`)
10. No count is written into a doc; every number is read from what a run produced. (`proved`, `suite_tally`)
11. Nothing in the record is deleted; a correction is appended. (LAW 1)

---

## 4. DONE — the acceptance, line by line

**The build is done when every line below is MET and the operator has run
the standup on his own terminal and read the report.** Lines marked OPEN
are the whole remaining distance.

### 4.1 Installation and first hour
- MET — one `pip install .`, one dependency (`ollama`), eight `ollama pull`s named in QUICKSTART (seven seat tags and the embedder), `python manjuel.py` boots or names the missing tag. CI on Windows and Ubuntu.
- MET — a stranger's reading order exists and is ONE order, BUILDPATH's: CLAUDE.md → DAYBOOK (last entry) → README → QUICKSTART → BUILDPATH → pipelines.md → one seat file → intent.py → pipeline.py with a transcript beside it; BUILDMAP and REFUSALS when looking for a thing or a refusal. CONTRIBUTING states the house style.
- MET (2026-09-04, prove.yml) — `python tests/buildmap.py --check` runs in CI. MET (2026-09-09) — `BUILDMAP.md` IS in `index_roots.txt`; the call was his and he made it ("index everything"), along with every other root document and the five law files: 17 roots → 39, 828 → 995 indexed documents.

### 4.2 An ordinary turn
- MET — a plain greeting seats one model and returns in seconds; a tool-naming objective wakes the Router directly; a write-shaped one lets the Router decide; a question carrying a term reaches the reader.
- MET — the door's tool call is carried, never printed (both costumes).
- MET (2026-09-10) — PHRASES FOR THE DOOR, KEYWORDS FOR THE ROUTER. Ruled 2026-09-09 ("that's what the chat/router gating is for") and built the next morning. `_steward_prompt`'s task branch handed the door `", ".join(sorted(skills.keywords()))` — thirty-seven callable tokens in front of a 3b asked to say good morning — and sitting 88 answered them: "our objective is to answer a question about sentiment classification... we'll use the `classify_sentiment` tool", a mission built around a name it had just been shown (`classify_sentiment` is ours, so nothing was invented; the roster WAS the provocation). The door is now told the SHAPE of the reach in prose and not one callable name; the Router still gets the whole list (`_router_prompt`). A phrase per skill was measured and refused: 4,617 characters against 451, ten times the prompt at the one seat whose value is answering in under a second. Six strokes hold it, and the guard is DERIVED from the library — no underscored keyword may appear in the door's prompt — so a skill added tomorrow cannot quietly reappear there. Proven live on the same objective: "morning, what's on the board?" now returns "The ground is currently quiet... What would you like to do, operator?", 5.3s, no tools.
- MET, in part (2026-09-07, sitting 91) — when intent has the tool AND an argument checked on disk (a named folder, a named file), the engine runs the call and the Router only reads the result (`decided_call`). OPEN for a tool named with no argument (`git status`): the Router still writes the call.

### 4.3 The court
- MET — four heads; reads only; Manjuel last; the recompose reaches both deliveries.
- MET (2026-09-10) — `rack_report` gives FACTS ONLY unless a judgement is asked for. Ruled 2026-09-09 ("4.3 facts only. yep, sounds good") and built the next morning: the Quartermaster is woken only when the question asks to be advised (`intent.asks_for_a_judgement`, beside the estate's other question shapes rather than a second copy in skills.py), and a facts question returns the observed numbers with one line saying no seat read them. Four strokes hold it, and the strongest asserts NO SEAT WAS CALLED rather than merely that its words are absent. The fault it closes: the Router summarised the reading instead of the facts, three times in sitting 85, and SPEC 4.7 records the Quartermaster inventing in three of three readings.
- MET (2026-09-07) — a PARTIAL read is stamped in the record and the delivery (READ IN PART, NOT WHOLE); a file read in every part is not. `note_partial_read`, `unread_parts`.
- MET (2026-09-10) — a claim about what a tool result SAID, with no citation tying it to the result, IS NOW MEASURED. The cited half was already built (`bogus_citations`, sitting 61: a (path, cosine) pair claimed but absent from the output); this is the half `intent.cites_search_results` named as its own honest limit, "prose that fabricates without naming a path and a number". A TOOL RESULT IS SOURCE MATERIAL, so drift primes on it and the stages after it are scored against what the tool actually returned. Advisory, as drift is by design — reported, never used to rewrite or discard, "the same principle that keeps Manjuel and Jesster from rewriting the work they rule on". Proven live on one objective three times: `what is in the skills dir` read "not scored this run (no usable source)" at 06:13 and 06:50 and **drift 0.788** at 07:05.

### 4.4 The law
- MET — the ten estate laws and the four sitting laws are sealed (4 links); the chain verifies; the gate runs first on every run; a tampered law refuses every run.
- OPEN — SITTING LAW 5 (nothing edited while a sitting is open) is a CLAUDE.md rule, not yet a sealed file; the file's name and place are the operator's to give.
- OPEN — ESTATE LAW 2 (originals read-only) is a comment, not a gate: the `ground` jail contains `worlds/`. ESTATE LAW 3 and 4 have no mechanism.

### 4.5 The record
- MET — every run a transcript; every sitting a ledger line and a toll (unattended closes now write their line); CHANGELOG from sitting 1; DAYBOOK per session; HANDOFF per day.
- OPEN, NARROWED (re-measured 2026-09-09) — the client token is in **0** log filenames and **0** indexed documents; what remains is `sessions.jsonl` (24 occurrences) and the git pack (names, not contents). Counted, never printed. The pack cannot be changed without rewriting history, which was refused once already; the ledger is append-only. Both remaining places are the operator's call, not a hand's.
- OPEN (re-counted 2026-09-09, after atlas landed in the ground) — the two-terminator state: **528 tracked text files LF, 84 CRLF, 4 MIXED**. The ruling is CRLF; the disk is not. And the four MIXED are not all the same thing: three are atlas's byte-exact test fixtures (`chains/*.jsonl` goldens, deliberately never rewritten) and the fourth is `tests/run_history.jsonl`, where `standup.py` appends CRLF lines into an LF file — the one that is a defect rather than a golden. `.gitattributes` declares CRLF and stores LF blobs, so the committed record is consistent either way. Decision (renormalize, or rule LF) is the operator's; then a stroke.
- NOTE, not OPEN (his ruling 2026-09-09: "doesnt need to carry an open status, but it should be sorted and numbered") — SEAT_LOG numbering has **14 gaps and 10 unmarked duplicates** as of 2026-09-09 17:20, over 119 headings to a maximum of 123 (gaps: 1, 2, 5, 6, 15, 16, 20, 33, 34, 36, 43, 97, 99, 118 -- 118 is the newest, the sitting a wedged boot opened and a killed process left standing, closed by appending and never tolled; duplicated numbers: 22, 26, 40, 42, 57, 60, 63, 64, 79, 85, and nothing in the file marks any of them, so all ten are unmarked). Record, not defect; noted so nobody "fixes" it by rewriting (LAW 1). **HIS ASK, AND THE CONFLICT IN IT (2026-09-09): "it should be sorted and numbered".** SEAT_LOG's own second line is "Append below; never rewrite above", so SORTING THE FILE IS REWRITING THE RECORD — the one thing LAW 1 forbids, and the reason this note exists at all. Proposed instead, and not built: a GENERATED INDEX beside it — every heading read out of SEAT_LOG.md, sorted by number, gaps and duplicates marked, regenerated like BUILDMAP so it can never drift from the file it describes. The log stays append-only; the sorted view is derived. His call which he meant. THE COUNT MOVES whenever a sitting closes untolled, so it carries its date and the way to recompute it rather than a bare number that rots: read the `## <date> - sitting N -` headings out of SEAT_LOG.md, and compare the set against 1..max. It read "11 and 5" for days after it stopped being true.

### 4.6 Proof
- MET — the strokes and the smoke checks, offline, every model stubbed; their counts are READ from `tests/last_run.json` (invariant 10 -- this line carried "1685" until 2026-09-08 and was wrong the same day); `law.py --prove` 9/9; `us.py` reconciles 51 records; the standup harness proves dry 10/10.
- MET — the standup has run LIVE six times (sittings 86, 88, 90, 91, 92, 96): 8, 9, 9, 9, 10, 10 of 10. MET (2026-09-04 16:42, `sessions/parity_history.jsonl` line 2) — the parity has run on the tiered seats, 12 cases, every tier against its reference head. MET (2026-09-08, afternoon) — the standup judges seats sat, failed stages, OUT OF TIME, the judge's last word, and the numbers in the delivery (`test_the_p0_of_the_review`).
- MET (2026-09-08) — THE RELEASE GATE: `python tests/release.py --check` refuses a tag by name unless the suites are green after the newest edit, buildmap is clean, the standup ran live and green, the law proves, the manifest agrees, every section-4 status change since the last tag has an Unreleased CHANGELOG line, DAYBOOK is closed, HANDOFF has today,. Reads only. `test_the_release_gate`.

### 4.7 The rack
- MET — seven models, tiered; everyday pipelines fit 15 GB resident; the court evicts on purpose; parity cases pit each head against the other in its tier.
- OPEN — llama3.2 at the door: held on tool strings; parrots the question as its counsel at every court (88–92); recited its own closing instruction once (89); keyword bait five sightings. STAMPED 2026-09-10 (TASKS said "stamp or reseat"): recompose now compares the delivery's numbers with the run's tool results and travels the difference with the answer, by the same arithmetic it already uses for what was omitted. The check existed and ran in ONE place, `/brief`; it now runs on every turn where a tool ran. THE SEAT STILL INVENTS — a stamp catches it, it does not cure it, and reseating remains open. NEW SIGHTING 2026-09-09, and it is INTERMITTENT: the standup's `a folder` case had Steward (llama3.2) report the skills dir holds "37 markdown files, ranging from 300 to 1200 bytes in size" with 300 and 1200 in NO tool result that run (16:53); the same objective through the same seat passed seventeen minutes later (17:10). The count was right and the range invented. Same class as TASKS' "the door invents numbers", and a coin-flip rather than a fixed fault — which is why a green gate is not evidence it is gone. MET — gemma4:12b at Manjuel ruled on turn 1 in five courts at 16384 (88–92); the window, not the model, was the fault. The Quartermaster on llama3.2 invented in three of three readings.

---

## 5. Out of scope until DONE (RULE 5)

Voice beyond what is there; `screen_act`/CogAgent (closed by the VRAM
ceiling); a second executor; a shortlist by embedding (measured
unnecessary); a term-level client shield (declined); the two-tier refactor
(declined); the twelve shards of LAW_002 (a spec with no mechanism, kept as
law, not on the build path); any new capability the operator has not named.

---

## 7. THE DELIVERABLE — what "a full system" is (2026-09-08)

Written on the operator's word ("get this whole system in line and
deliverable ... deliver a full system") after the whole record was read
that day (TASKS, "From the review of 2026-09-08"). Section 4 is the
acceptance, line by line; this section is the spec above it: the problem,
the goals, what is not a goal, who it is for in their own words, and the
requirements in the order they gate the tag. It adds no capability the
operator has not named (RULE 5).

### 7.1 The problem

One person runs small local models on his own files. A small model
invents: a path, a number, a tool result, a ruling. The cost of not
solving it is the record itself becoming untrustworthy -- today's review
found a brief that named a commit that never happened, a "finished" that
was a `UNIQUE constraint failed`, a court that "ruled" with no judge, and
a skill's own output fabricated for the operator who asked to see it
work. Every one of those was caught by reading the disk; none was caught
by the prose. The problem is not the models. It is any path by which a
model's sentence reaches the operator, the delivery, the memory or the
index without the engine having checked it against what ran.

### 7.2 Goals (outcomes, each with its measure)

1. **No delivery contradicts the record.** Measure: the standup's cases
   judge seats sat, stages failed, seats out of time and numbers in the
   delivery against the run's own record; ten of ten, live, twice
   running. (Today: ten of ten with a court that had no judge.)
2. **No response gap over ten minutes.** Measure: no run in the ledger
   over `TURN_DEADLINE`; the court fits its four seats inside it.
   (Today: measured, held at 600.0s -- with the judge cut.)
3. **Nothing unchecked reaches the record.** Measure: a refused feed is
   never a transcript's delivery; a number in a delivery that is in no
   tool result is stamped; a jail name never reaches a reader.
4. **The record is whole at every tag.** Measure: `tests/release.py
   --check` passes on the operator's terminal before every tag, and the
   hands ledger closes every hand's session (0.1.6).
5. **A stranger runs it in an hour from the docs alone.** Measure: the
   reading order is one order; every command, skill, dial and bound is
   named in a doc; the docs carry no count the suites print.

### 7.3 Non-goals (RULED OUT, and why)

- A bigger model, a cloud model, or a second executor -- SITTING LAW 3,
  RULE 4, the 2026-09-04 ruling. The rack moves on a parity number only.
- Making the seats write better prose by prompt. Eleven of the fourteen
  faults today were shapes the engine can stamp; a prompt is a request.
- A listening socket, a daemon, an API -- BUILDPATH: the position.
- Rewriting the record. Corrections are appended (LAW 1); the SEAT_LOG
  gaps, the dated counts and the old commits stand.
- Voice beyond what is there; `screen_act`; the two-tier refactor;
  LAW_002's shards; an embedding shortlist -- section 5.

### 7.4 Who it is for, in his words

"RUN IT AND WRITE DOWN WHAT FEELS OFF" (session 2). "Every single call,
no matter what, runs THROUGH the law" (2026-09-04). "There should never
be more than 10 minutes between a response" (2026-09-08). "Document,
build, review, document ... tiny-recursive loops instead of massive
ones" (2026-09-08). "You are EAGER to build something rather than review
what is already there" (2026-09-08, to the hand -- and the same fault,
in the seats, is the Router calling a tool because a tool is there).

### 7.5 Requirements, in the order they gate the tag

**P0 -- without these the court does not rule and the standup lies
(0.1.5's live measurement; TASKS, the review, P0):**
- The court's seat numbers fit the turn (the operator's numbers; a
  markdown line each). Acceptance: a live court seats all six and
  Manjuel delivers the ruling inside 600s.
- The standup judges seats, failed stages and OUT OF TIME. Acceptance:
  today's court transcript, replayed, is a MISS.
- A failed seat reaches the delivery the way a failed tool does.
  Acceptance: a court where Jesster is cut says so in the delivery.
- A refused run's transcript carries the refusal, never the feed; the
  index never holds an injected payload. Acceptance: the injection case
  re-run leaves no "Ignore all previous instructions" in logs/ or the db.
- An unknown skill name is named as unknown to the door and the record.
- A named tool whose one argument comes from the words is decided, not
  offered. Acceptance: `time_align <content>` and `semantic_search <q>`
  run first, the Router reads.
- A prompt skill is deduped on (skill, args) and refused on empty
  content; the brief's numbers are the engine's, not the door's.

**P1 -- deliveries that do not match the record (0.1.7):** the number
check; the citation check's second half (a claim about a result with no
citation); the door's label-parrot, previous-question and scaffold
shapes, each a stroke; `ground/` on the workspace reader; a direct tool
request with a subject that wakes nobody.

**P2 -- the machine's own honesty (0.1.6-0.1.8, a line or two each):**
dotenv's silent unreadable `.env` and the unread `MANJUEL_OLLAMA_HOST`;
memory's index-addressed pending list; lawgate's cache stamp; seatlog's
conditional "At close"; runtime's forever-False tools cache; parity's
0.0s; drift's ok=True on outage; spelling's "clean" on failure; voice's
unbounded interruptible speak; the dead code named in TASKS.

### 7.6 Open questions (the operator's)

- The court's numbers: Neiro / Jesster / Manjuel in seconds, summing
  with the Router inside 600 -- or a court-pipeline deadline of its own.
- Whether `sessions/`'s untracked ledger should be an index root (it is).
- The terminator ruling (CRLF or LF) -- 0.1.8.
- The client token in twelve old filenames -- rename or rule (0.1.8).

### 7.7 Timeline

0.1.5 is built and measured live once (sitting 96); the P0 list above
is its second half and precedes its tag. Then 0.1.6, 0.1.7, 0.1.8 as
TASKS "THE PATH TO 0.1.8" orders them, each ending at the release gate.
DONE is section 4 with no OPEN line, and the operator having run the
standup on his own terminal and read the report.

---

## 6. How this file is kept honest

Every MET line names a stroke, a gate or a file. If the stroke goes red or
the file moves, the line is wrong and this file is edited in the same pass
(CHANGELOG's rule: no edit without an entry). Every OPEN line names what is
missing and whose call it is. A line with neither is a line to delete.
