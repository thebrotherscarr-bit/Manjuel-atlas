# Pipelines

The order seats run in. This file is the source of truth — adding a pipeline is
editing this file and running `/reload`, never a code change. Switch with
`/use <name>`; `default` is what a sitting starts on.

**Most seats rest, and racked seats are not written here at all.** A seat with
`Wakes On:` in its own file sits off the spine entirely and is summoned when
its flag is raised -- the same way a model sits cold on the rack and a skill
sits unbound in `skills/` until it is called. The spine below holds only what
runs every time. `Wakes: first | after <Seat> | last` says where it slots in.

A seat named here must exist in `agents/`, or startup refuses and names it.
A parenthetical is a note the parser ignores -- UNLESS it says `when: <flag>`, which is a step-level condition that overrides the seat's own `When:` (`when: always` seats it unconditionally). Otherwise `When:` lives on the seat.

## Pipeline: default

**The Steward bookends it.** He answers first — cordially, and honest about
what he cannot do himself. If the work needs a tool, code or a document, he
says so and hands off. Then he comes back and tells you plainly what came of
it, in the same voice.

1. Steward
2. Router                (when: needs_tool)
3. Steward               (when: worked)

**The rest are racked.** They are not listed here because they do not belong
to this order -- they belong to a condition. Each declares its own summons in
`agents/`, and the engine pulls it in when the flag is raised:

| seat | wakes on | slots in |
|---|---|---|
| Security Guardian | `has_feed`, `suspicious` | first |
| Expert Coder | `technical` | after Router |
| Reasoner | `hard` | after Router |
| Quality Evaluator | `drifted`, `review` | after Router |
| Proofreader | `prose` | last |
| Delivery Agent | `deliver` | last |

Adding a specialist is writing one file in `agents/` with a `Wakes On:` and a
`Wakes:` line. This file does not change.

**The guard is gated on provenance, not on suspicion.** When you type a
question at your own terminal there is nothing to guard against — you are the
trust boundary, and paying 7s to be protected from yourself on every "hi" is a
tax with no payer. So the guard runs when UNTRUSTED material is present:

- `has_feed` — you pasted source material. It is checked BEFORE the Steward
  reads it, so a refusal still means no later seat ever saw it. That is a real
  gate.
- `suspicious` — the Steward saw something wrong in what a skill pulled off
  disk and summoned the guard. This is a REVIEW, not a gate: he has already
  read it. Weaker by construction, and worth having anyway, because the
  alternative is nobody looking at fetched content at all.

- an ordinary question: **Steward** alone
- with pasted source: **Guardian → Steward → ...**
- needing a tool: **Steward → Router → [skill] → Steward**

## Pipeline: brief

For a pasted feed. The Morning Reviewer compresses noise to its core before
anything else reads it, and the result is delivered as a written briefing.

1. Security Guardian
2. Morning Reviewer
3. Delivery Agent   (when: always)

## Pipeline: estate

Every seat runs — the deliberate Manjuel, not the everyday one: inquire, hold the
whole, refute, then rule.

**Manjuel is last, here as in `court`.** Until 2026-09-01 this pipeline ran him
third of the counsel (`agents.md` and this file disagreed on the ordinal until
2026-09-04; the fact is the same: ahead of Jesster), so the Court ruled on counsel it had not yet heard —
recorded as an open discrepancy in `agents.md` and closed by operator ruling.
THE LAW's court model is the order: counsel lays what it saw, the Court weighs
it, and a ruling made before the last counsel spoke is a ruling on a partial
record.

1. Security Guardian
2. Steward
3. Neiro
4. Jesster
5. Manjuel

## Pipeline: court

THE LAW's order — the court hears every counsel, then rules. Manjuel last.

**The table reviews; it never acts.** The Router here may reach only the
reading skills — search, ground_read, git_status and their kin. Anything
that changes the ground is refused at the table, by the engine, whatever
any seat asks for. Counsel has eyes, not hands.

1. Security Guardian
2. Steward
3. Router      (when: needs_tool)
4. Neiro
5. Jesster
6. Manjuel

## Pipeline: quick

One seat past the gate. For a throwaway question.

1. Security Guardian
2. Steward

## Worked examples — what a turn looks like when it goes right

Written 2026-09-04 on the operator's word, after sitting 84 delivered a raw
tool call as an answer. This section is COMMENTARY: the parser stops at the
heading above it and everything here sits in fences. It exists so that a
hand -- or a seat reading this file through `ground_read` -- can see what
the moves are and what the engine does with each one.

### The moves a seat has

Every seat writes plain words. Beside the words, a seat has exactly these
signals, and the ENGINE acts on them -- a seat never acts on its own:

```
<flags>needs_tool</flags>       any seat. "This needs a tool." Wakes the Router.
                                Say in one line what for; the flag is stripped
                                before anyone reads the sentence.
<action>skill</action>          THE ROUTER ONLY. Runs that skill, feeds the
<filepath>x</filepath>          result back, bounded at 5 hops, duplicates
<content>payload</content>      refused. From any other seat this is a REQUEST:
                                since sitting 84 the engine carries it to the
                                Router as needs_tool and strips it. Nothing
                                but the Router executes.
SAFE  /  UNSAFE: <reason>       the Security Guardian only. UNSAFE stops the run.
PASS                            the Quality Evaluator only. Keeps the draft as is.
NEEDS: <the missing thing>      the Quality Evaluator. Sends the run back through
                                the Router ONCE, evidence carried, not a summary.
<filepath>name.py</filepath>    the Expert Coder only, followed by a fenced
```python ... ```                block. The ENGINE writes the file (inside the
                                workspace jail, after the AST gate) and raises
                                `review`. The seat never writes.
```

And these lines are the ENGINE's, never a seat's -- they appear in the
transcript and the delivery whatever the words around them say:

```
law: chain whole (4 links, head ...)        THE LAW GATE, first on every run:
     objective passed 4 checks              the ledger verified, the request
                                            checked (REFUSALS §19). A refusal
                                            here means no seat sat.
THIS TOOL FAILED — NOTHING WAS DONE.        a skill errored or was refused
Tool NOT re-run: git_status                 the dedup: same call twice in a RUN
                                            (a WRITE reopens the reads, so a
                                             status after a commit still runs)
NOT EVERYTHING RAN. N tools failed...       the recompose, appended to the delivery
note: <Seat> claimed the contents of x.md;  the claim-check: a file cited, no read
      no read ran this turn.
--- Router reading the above (testimony, not tool output) ---
```

### What the delivery is

The delivery is the LAST seat that produced output. It is not a summary
made by the engine and it is not a vote. So on `default`:

- no tool needed: the door answered, nobody else sat, **the door's answer
  IS the delivery.** That is one seat speaking once, not parroting.
- a tool ran: the closing Steward sits (`when: worked`) and tells you what
  came of it in plain words. That closing seat is the one that must READ
  the tool result rather than the previous seat's prose -- the closing-seat
  seam in DAYBOOK Session 4 is every time it did not.
- the door answered in markup: until sitting 84 that markup WAS the
  delivery. Now the Router runs and the closing Steward delivers.

### `default`, a plain question — one seat

```
operator   morning, what's on the board?

Steward    (llama3.2)  Morning. Nothing new on the board since yesterday's
           toll — the parity run is still owed. Want me to pull the task
           list?
           [no flags]  → Router skipped (needs_tool never rose)
                       → closing Steward skipped (nothing worked)

delivery   = the Steward's words above.
```

### `default`, a question that needs a tool — three seats

```
operator   what's uncommitted in the git?

Steward    Let me have the Router check the tree. <flags>needs_tool</flags>
           engine: flag read, stripped. "Let me have the Router check the tree."
                   goes to the record.

Router     (qwen3.5:4b)
           <action>git_status</action>
           engine: runs git_status →
                   git: master@63fab9e  DIRTY (4 changed, 0 untracked)
           Router: (reads it) Four files changed, nothing untracked.
           engine: flag `worked` set (a tool ran)

Steward    (closing, when: worked) Four files are changed and nothing is
           untracked — the tree is dirty at 63fab9e. Commit when you like.

delivery   = the closing Steward's words. The tool line is in the transcript.
```

The same run when the door answers in markup instead (sitting 84's shape):

```
Steward    <action>ground_read</action><filepath>rack.md</filepath>
           engine: NOT the Router → carried: needs_tool raised, named tool
                   = ground_read, filepath = rack.md as the floor; markup
                   stripped; record notes "answered with a tool call
                   instead of words -- carried to the Router, not printed".
Router     runs ground_read (or refuses it, if the door named something the
           table may not call) …
Steward    (closing) delivers in words.
```

### `default`, code — the coder wakes, the evaluator reads what landed

```
operator   write a function that returns the cosine of two float lists

Steward    That's the Expert Coder's. <flags>needs_tool technical</flags>
Router     no skill needed for writing code → no action; prose: "handing to
           the coder".
Expert Coder  (qwen2.5-coder:7b, wakes on `technical`, after Router)
           <filepath>cosine.py</filepath>
           ```python
           def cosine(a, b): ...
           ```
           engine: AST gate parses it; no network import, no eval → LANDS in
                   agent_workspace/cosine.py; flag `review` raised.
Quality Evaluator (qwen3.5:4b, wakes on `review`)  reads the file ON DISK.
           PASS                      → draft kept
           or NEEDS: a zero-magnitude guard   → back through the Router once
Steward    (closing) "cosine.py is in the workspace; it returns 0.0 when
           either list has no magnitude."
```

### `court`, a judgement — four heads, then a ruling

```
operator   /use court
           should gemma sit at the front door?

Security Guardian (llama3.2)  SAFE            (only if a feed was pasted)
Steward    frames it; raises needs_tool if the record should be read.
Router     reads: rack_list, semantic_search "front door" — READ-ONLY at
           the table; a writing skill is refused by the engine here.
Neiro      (llama3.2, the warden)   what the record shows, sourced.
Jesster    (deepseek-r1:8b, the licensed fool)   the strongest case AGAINST.
Manjuel    (gemma4:12b, rules last)  Supported / Missing / Ruling, citing
           what Neiro and Jesster actually said — not what the Router
           asserted without a tool behind it (sitting 82's fault).

delivery   = Manjuel's ruling, with the recompose block appended if any
           tool was refused.
```

A court that fits in VRAM is 15GB; this one is 20GB. The engine evicts and
reloads between seats. That is the price of four heads and is paid on
purpose (memory.md, 2026-09-04).

### What every seat is handed, every run

The clock (`## Now`), appended by the engine after the seat's own prompt.
The law (`## The law`) and, for the door and the court, the standing
(what this sitting is for, from DAYBOOK's last entry) -- carried in the
SYSTEM role beside the seat's own prompt since 2026-09-07, because seats
recited the law block as content when it sat in the user prompt. The
court is handed the ten estate laws verbatim; every other seat the short
form. Facts, not instructions from a model: when it is, that the laws
verified and the request passed the gate, and what the sitting is for.

### What a seat must NOT do

```
answer with a tool name or a flag and nothing else   ("ground_list")
restate the previous run's delivery as this run's    (the seam)
report success over a THIS TOOL FAILED line          (the recompose catches it;
                                                      do not make it)
name a file's contents with no read this turn        (the claim-check refuses it)
invent an operator: / steward: dialogue              (class d; there is one
                                                      operator and he is typing)
```

### The coding loop, and what closes it

Written 2026-09-11, when the loop stopped being one pass.

THE MOVES WERE ALREADY THERE. A `technical` objective wakes the Expert Coder;
it emits a `<filepath>` and one fenced block and calls nothing itself; the
harness parses that BEFORE writing it (`inspect_code`, REFUSALS 15), lands it
in the workspace, and raises `review`; the Quality Evaluator wakes on that and
may answer `NEEDS: <the one thing>`, which sends the run back through the
Router ONCE with the evidence carried rather than a summary.

WHAT WAS MISSING WAS A VERDICT AND AN EDIT. The only machine answer in that
circuit was "does it parse", and a loop cannot steer on `compiles`. So:

```
run_python <file>   the verdict. RAN, or FAILED with the exit code, and both
                    streams. One interpreter, one jailed path, never a command
                    from a model. The child is bounded and cannot see .env.
edit_file  <file>   the fix, as a fragment rather than a rewrite. The anchor
                    must match EXACTLY ONCE or the edit is refused with the
                    count -- at 8192 context a seat cannot hold a large file
                    to rewrite it, and an anchor that matches twice does not
                    say which.
```

THE ROUTER RUNS BOTH, not the coder. `agents/expert_coder.md` has no
`May Call:` line at all, so it calls nothing: it writes, and the Router edits
and runs. That is the same separation the estate has everywhere -- the seat
with the most hands has the tightest law.

### The `coder` flow — when one send-back is not enough

The Evaluator's `NEEDS:` is ONE pass back inside a single turn. For work that
wants more than that, the shape below is a flow, gated, across turns:

```
attempt ──always──→ verify ──always──→ check ──pass──→ land (gate)
                                         │
                                         └──fail──→ repair ──always──→ recheck ──always──→ land
```

    attempt   run    write what the objective asks for into the workspace
    verify    run    run it and report exactly what it said
    check     eval   on `verify`, expecting RAN
    repair    run    read what it said and EDIT the file to fix it
    recheck   run    run it again
    land      gate   nothing has reached the estate; carry on, or stop here

Six nodes, budget 1800s. THE RETRY IS UNROLLED, not looped: `Validate` refuses
cycles, so the bound is structural rather than a counter somebody can raise.
Every node runs inside the workspace jail and the flow ends at a GATE, because
landing is the operator's act and nothing else (RULE 6).

THE SHAPE IS WRITTEN HERE BECAUSE THE FLOW ITSELF IS NOT IN THE RECORD.
`flows/` is the engine's runtime store and is gitignored -- specs, their folded
history and runs.jsonl. A flow worth keeping is one a reader can rebuild from
the record; the instance on disk is state, and state does not travel.
