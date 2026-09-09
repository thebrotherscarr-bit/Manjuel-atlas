# S6 — THE FIELD-OPS SKILLS: the caretaker script

Author of record: the Steward's session of 2026-07-31, under the operator's
directive to build the enterprise gateway/orchestrator. Five skills, built
additively, each carrying the Forge's contract (`# skill:` header, `run(arg)`,
`describe()`, `prove()`). Author's discipline: standard library only; every
record hash-chained and append-only under `shelf/ops/`; tamper is caught and
PINPOINTED, never erased; the skills write nothing outside their own books
except what their gates (board mirror, incident handoff, forge path) require.

All five walked the town's stations: test -> verify -> use -> confirm ->
field report (1/1 worked, chained + witnessed). Registry (neiro/forge):
proposed by steward, VERIFIED by the smith's hand in sealed children, exit 0
observed. ASCENDED 2026-07-31 by the operator's own hand — town board
witnessed, registry state=ascended, chain straight.

------------------------------------------------------------------------------
## dispatch — the work queue
AUTHOR: built for field ops: one queue the steward carries, jobs that walk
open -> claimed -> done, every move on the chain. Mirrors the commons board's
open tasks without owning them.
USE:   use dispatch enqueue <title> [| <world>]   — put work in
       use dispatch pull                          — mirror the commons' open tasks
       use dispatch claim <id> [who]              — take a job
       use dispatch done <id> [note: ...]         — finish a job
       use dispatch status                        — queue + counts + moves
       use dispatch verify                        — the chain is straight?
CARE:  lives at shelf/ops/dispatch.jsonl. State is DERIVED from the last move
       per id — never stored, so a bent line is caught by verify, not silently
       trusted. Ids rise forever; nothing is ever deleted.
MAINTENANCE: add a move type = append a kind + fold it in `status`. Keep the
       contract: prove() must pass in a child before the skill travels.
TIME:  94 ms on a live forge.invoke carry (queued + returned).
USES:  intake of repair jobs, board-mirror work orders, handover of tasks
       between shifts.

## incident — the crisis track
AUTHOR: the P1/P2/P3 record: open -> assign -> escalate -> close. Escalations
mirror to the commons board so the town sees the smoke; the record stays here.
USE:   use incident open <P1|P2|P3> <title> [| <world>] — declare
       use incident assign <id> <owner>                — name the hand
       use incident escalate <id> <why>                — raise; boards the alert
       use incident close <id> [resolved: ...]         — resolve, with the note
       use incident status                             — open/escalated/closed by severity
       use incident verify                             — the chain is straight?
CARE:  lives at shelf/ops/incidents.jsonl. The OPEN record seeds state; every
       later move overrides by position in the chain. Escalate mirrors once,
       chained, to the commons — the alert is a witness, not the record.
MAINTENANCE: severity levels and mirror targets live in the move records;
       the board door is neiro/board.Commons — swap the mirror only there.
TIME:  75 ms live.
USES:  outage calls, client escalations, breach handoffs from the SLA clock.

## sla — the service clock
AUTHOR: the ticking obligation: a promise with a due moment and a severity.
Due accepts absolute moments or `+N<d|h|m>` from now; `tick` walks the clock
and hands every breach to the incident track as a P2 (the clock does not
carry the crisis — it rings the bell).
USE:   use sla add <name> <due|+Nh|+Nd|+Nm> <P1|P2> — promise on the clock
       use sla met <name>                            — kept on time
       use sla due                                   — what the clock is watching
       use sla tick                                  — ring the bell; breaches open
       use sla verify                                — the chain is straight?
CARE:  lives at shelf/ops/sla.jsonl. Parsing is from the RIGHT so names may
       carry spaces; an unparseable due is refused, not guessed. Breach
       handoffs are one-way: the clock rings, the incident track owns it.
MAINTENANCE: the breach severity (P2) and the handoff door live in
       `_open_incident`; change the contract there, re-prove.
TIME:  112 ms live.
USES:  client SLAs, maintenance windows, recall deadlines, shift duty clocks.

## pulse — the field-ops digest
AUTHOR: one page for the whole operation: queue, incidents, the clock, the
board's open tasks, the rack, the ledger — folded, read-only, verified.
`pulse world <name>` scopes the page to one world.
USE:   use pulse                — the whole operation on one page
       use pulse world <name>   — one world only
       use pulse verify         — every chain it reads is straight?
CARE:  reads only — writes nothing, so it can be trusted anywhere, any time.
       The `rack: dark` line is honest: no voice answering means the page
       says so instead of pretending.
MAINTENANCE: add a fold by appending a section in `run` — the section must
       state its own source and stay read-only.
TIME:  171 ms live.
USES:  the morning page, the shift handover page, the client sitrep.

## gateway — the messenger
AUTHOR: the operator's central ask: one door that carries ANY traffic between
the core and the upper tiers, and witnesses every carry on a chained bus
record. Five doors: journal (the ledger line), board (Commons post), skill
(forge.invoke — a skill called by name), rack (a voice asked), ops (a note
on the bus itself).
USE:   use gateway gateway <journal|board|skill|rack|ops> <message> — carry
       use gateway log                     — the last ten carries, with replies
       use gateway verify                  — the bus record is straight?
CARE:  lives at shelf/ops/gateway.jsonl (the bus) + gateway_journal.jsonl
       (the ledger's echoes). A carry is appended ONCE, after delivery, with
       the reply; a failed delivery is a carried failure, never a gap. If the
       rack is dark the bus says so — the messenger does not invent voices.
MAINTENANCE: a new door = a `_*_door` function + one branch in the carry
       switch; the door answers text, the bus carries it. Keep the door
       hermetically provable (base-aware) and re-prove.
TIME:  81 ms live (journal carry).
USES:  cross-tier messaging, ledger echoes, board announcements, skill
       orchestration from a single mouth, rack queries in one line.
------------------------------------------------------------------------------
## The whole suite at a glance
VERIFY:  python skills/<name>.py prove   (PASS, five of five)
GATE:    python tools/smith.py --check skills/<name>.py   (gates 1-2 held)
FORGE:   registry straight; verified by a different hand, in a child
RECORDS: shelf/ops/{dispatch,incidents,sla,gateway}.jsonl — append-only,
         hash-chained; never edit a line, never delete. Fold or write new.
