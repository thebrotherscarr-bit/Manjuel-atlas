# SYSTEM_DESIGN — the software side of the NAS

*Drafted 2026-09-08 at the operator's word: "the money is there, the
business is viable, i just need the digital platform backend to keep
everything organized and simple, without paying out hand-over-foot for a
series of different services … an 'agentic' system that works and is able
to contextually understand what i am saying without paying for a monthly
subscription or sending everything to the cloud … this PC can do everything
we need inference-wise … the whole 'under 1k' in hardware being built to
have your own personal digital assistant on your own home network with your
files and your functionality … basically the software side of the NAS, you
just add whatever hardware to it."*

*Grounded in the disk AS OF THE DRAFTING, 2026-09-08: `Desktop\Research`
(Manjuel, 0.1.6 unsealed, the headless door landed that day),
`Desktop\Archive\atlas` (the spine, THE LINE, the faces — an artifact,
pulled in as needed), `worlds\TBC` (the business), and
`SPEC_CONTROL_CENTER.md` (the glass). Nothing here is a work order until he
names the piece. Placeholders stand where names were.*

*Two of those have MOVED since and the line above is left as the record of
what was true when it was written: Manjuel is 0.1.11, and atlas is a
repository of its own inside the ground at `atlas/` — not an artifact
pulled from the attic. Section 6 is still the build order.*

**HOW TO READ A PATH IN THIS DOCUMENT.** Added 2026-09-12, after a doc-truth
pass over this file reported eight “dead” references that were nothing of
the kind. Three different things look identical here, and nothing said which
was which:

    `manjuel/intent.py`      IN THIS GROUND. It exists, and if it does not,
                             that is a defect worth reporting.
    `ROUTES.md` *(planned)*  A THING THIS DESIGN ASKS FOR. It does not exist
                             yet and its absence is the POINT — §6 is the
                             build order, and these are what it orders.
    the business's own files  IN ANOTHER WORLD, described as INPUTS. They are
                             not in this repository and never will be; a
                             checker looking for them here is asking the wrong
                             question of the wrong disk.

The pass that found them checked every path-shaped token against
`Desktop\Research` and called the second and third kinds dead. It was right
about the disk and wrong about the question — which is the same fault, in a
tool, that this document exists to avoid in a design. Planned artifacts carry
*(planned)* from here on; anything belonging to another world is named as that
world's rather than left looking like a missing file.

---

## 0. The one sentence

**One box on the home network holds the record — the household's files and
the business's — and a council of small local models works that record
under sealed law, through one door, with a glass to run it from and a
receipt on everything; a domain (a business, a project, a person's affairs)
is a world on the box, and the first world is the property-care business.**

That is the appliance. The NAS gives it disks; the gaming PC gives it a
GPU; the software is what this estate already is, finished and joined.

---

## 1. Requirements

### 1.1 Functional — what it does

| # | Requirement | Where it comes from |
|---|---|---|
| F1 | **Hold the record.** Every document, photo, note, invoice, estimate, contract and log a household or business produces, on the box, in plain files, append-only, hashed on arrival. | Manjuel LAW 1 (fold, never delete); atlas `state = fold(record)`; TBC `Filed\{property}\{date}\` already does this by hand |
| F2 | **Understand what the operator says, in context.** A typed or spoken line routes to the right world and pipeline by rules first, arithmetic second, a model last — and the seat that answers holds that world's standing, story and index. | Manjuel `intent.py`, `ROUTES.md` *(planned)* (spec §4.4), the story block, `semantic_search` |
| F3 | **Do the business's work as skills.** Intake → contract → scheduled visit → checklist + photos → report → estimate (50 % deposit) → invoice → payment → record → next visit. Each step a skill or a pipeline, each output a draft for his hand. | TBC `agents.md` §5, `TBC - ESTIMATE FORMAT.md`, `tbc_estimate` CLI |
| F4 | **Never lie.** No claim reaches the operator, the delivery, the memory or the index without the engine having checked it against what ran; every failure travels with the answer. | Manjuel SPEC §3 invariants, `REFUSALS.md` §7–11, the recompose |
| F5 | **The gate is final.** Money, legal commitments, sends, posts, landings: the system prepares, the operator's hand confirms. `can_approve:false` everywhere. | Manjuel RULE 6 / LAW 6; atlas law 5; TBC `SEAT.md` "MONEY AND LEGAL COMMITMENTS ARE THE OPERATOR'S" |
| F6 | **Many worlds, one discipline.** A domain is a folder with its own declarations, law copy, record, index and workspace; the origin never indexes a world; a world is written only by its own engine. | his ruling 2026-09-08; `SPEC_CONTROL_CENTER.md` §4.2 |
| F7 | **Run it without a terminal.** A glass on the LAN: environments, run, traces, waterfall, seats, rack, record, alerts, law — and the business's own screens (clients, visits, photos, estimates, invoices, contracts). | `SPEC_CONTROL_CENTER.md`; TBC `tbc_hub_v2.html`'s eight panels |
| F8 | **Publish on his hand only.** Marketing content drafted from released material; the release verb is the only path client material crosses; posting is a human act. | the campaign design (this afternoon); SITTING LAW 2 |
| F9 | **Take material in from a phone.** Photos and voice notes land on the box over the LAN and become record entries with receipts, without an app store. | TBC's photo dump problem ("still working through the final photo-dump solution"); `tbc_system_core.py`'s watch-folder idea |
| F10 | **Leave with your data.** Everything is files a stranger can read; export is byte-identical; a world moves by copying its folder. | atlas `db export`; Manjuel's one-dependency law |

### 1.2 Non-functional

| Dimension | Number | Source / reasoning |
|---|---|---|
| Users | **1 operator** now; his seats (14 + 40 declarations); outside users a later phase behind a gate | Manjuel SPEC §1 "a second user is a fork" |
| Worlds | < 10 (TBC, marketing, books, clients, manjuel, sewder, …) | his list of functions |
| Clients (TBC) | 1 today; design for 50 | four tiers, monthly cadence |
| Runs per day | < 50 typed turns; a handful of pipelines | sittings 86–98 measured |
| Turn latency | ≤ **600 s** ceiling, court ~300 s, a door answer 2–30 s | `TURN_DEADLINE`, sitting 98 (300.4 s court) |
| Inference budget | **15 GB VRAM** on a 16 GB card; per-seat timeouts 150/300/600/700 by size | `vram.py`, `agents/*.md` `Timeout:` |
| Storage | photos dominate: ~**250 MB per job-month** today (47 photos ≈ 90 MB at 6-20; `picture\` 234 MB); text is negligible; index ~25 MB | `worlds\TBC` on disk |
| Availability | one box; restart is seconds; the ground opens with the rack down | Manjuel boot, "RACK UNREACHABLE — the ground is open" |
| Durability | append-only files + hash chain + a copy of the folder; no database is the truth | atlas `SPEC_SQLITE` rule 1–4 |
| Cost | **$0 / month.** Hardware ≤ $1k one-off (any gaming PC with a 12–16 GB GPU + disks) | his word |
| Network | **home LAN only**; loopback for the engine; no WAN, no cloud, no key | Manjuel RULE 4; atlas loopback doctrine |
| Dependencies | Manjuel: `ollama` only; atlas: none; nothing that downloads weights at first use | both charters |
| Honesty | every claim checked; every failure delivered; every number read, never written | Manjuel SPEC §3 |

### 1.3 Constraints

- **Two codebases, one operator, one afternoon at a time.** RULE 10: one piece, mirror-proved, one CHANGELOG entry, stop. The design is sized in pieces, not sprints.
- **Manjuel finishes its own path** (0.1.7 door/court → 0.1.8 seal). The appliance builds beside it and absorbs it stone by stone (`SPEC_CONTROL_CENTER.md` §10).
- **atlas is an artifact now**; pieces are pulled into Research at places he names (SITTING LAW 4).
- **Windows 11 host, RX 6800 XT 16 GB, Ollama at 127.0.0.1:11434, OLLAMA_NUM_PARALLEL=1** — sequential inference by construction (Manjuel DESIGN §9).
- **CRLF is the ruling** for what the estate writes; fixtures keep what they have.
- **Client material is sealed** (SITTING LAW 2). The design must make the wrong thing impossible, not merely forbidden.

---

## 2. High-level design

### 2.1 The shape

```
                         THE HOME NETWORK (LAN only; no WAN; no cloud)
   phone / laptop / TV ──────────────────────────────────────────────────┐
        │  https://<box>.local  (one operator credential)                │
        ▼                                                                │
┌─────────────────────────────────────────────────────────────────────┐  │
│  THE GLASS      browser SPA · vanilla JS · WebCrypto verify        │  │
│  estate pages: environments · run · traces · waterfall · seats ·    │  │
│                rack · record · alerts · law                         │  │
│  world pages:   TBC — clients · visits · photos · estimates ·       │  │
│                 invoices · contracts · calendar · logbook           │  │
├─────────────────────────────────────────────────────────────────────┤  │
│  THE LINE       atlas-mcp (Go) · JSON-RPC 2.0 + SSE · one door      │  │
│  tenant = world · env_* run_* route_* · every hash via `atlas` exec │  │
│  ROUTES.md → intent → Router seat            (deterministic first)  │  │
├──────────────┬──────────────────────┬───────────────────────────────┤  │
│  THE RACK    │  THE ENGINE(S)       │  THE DROP                     │  │
│  Ollama on   │  one `manjuel.py       │  SMB share per world:         │◄─┘
│  loopback ·  │  --headless --ground │  worlds\<w>\Input\            │  photos,
│  VRAM plan · │  worlds\<w>` per     │  watcher → hash on arrival →  │  voice notes,
│  seat-call   │  open world, over    │  entry drafted → his hand     │  scans
│  queue ·     │  stdio; no socket    │                               │
│  tiers       │                      │                               │
├──────────────┴──────────────────────┴───────────────────────────────┤
│  THE SPINE      atlas (Rust) · sha256 · canon · Manjuel verdicts ·    │
│                 merkle · covenant · SQLite mirror (derived) ·       │
│                 export byte-identical                               │
├─────────────────────────────────────────────────────────────────────┤
│  THE RECORD     plain files on the NAS disks                        │
│  Research\ (origin: laws, seats, skills, tools, its own record)     │
│  worlds\TBC\  worlds\marketing\  worlds\books\  …  (each: agents/   │
│    skills/ pipelines.md commands.md ROUTES.md law/ sessions/ logs/  │
│    SEAT_LOG.md memory.md index/ agent_workspace/ Input/ Filed/)     │
└─────────────────────────────────────────────────────────────────────┘
```

Three rules hold the picture together, and all three already exist:

1. **Rule of one computer** (atlas `SPEC_SEAM`): every hash, verdict and
   seal is computed by the Rust `atlas` binary; Go and Python exec it with
   an argument array and read one JSON object. The engine is reached the
   same way — THE LINE execs `manjuel.py --headless` and speaks JSON lines on
   its pipes (`manjuel/serve.py`, landed today). No engine socket.
2. **The record is the truth; everything else is derived** (atlas
   `SPEC_SQLITE`): the SQLite mirror, the index, the glass's every screen —
   all `fold(record)`, all rebuildable from the files.
3. **One executor, one writer** (Manjuel SPEC §3, §4.2 of the spec): exactly
   one seat runs tools; exactly one engine writes a world.

### 2.2 Data flow — one business day, end to end

```
 06:30  phone → SMB drop: 17 photos + a voice note            (THE DROP)
        watcher: hash each on arrival (`atlas` via THE LINE) → Input/ ledger line
        transcribe locally (whisper.cpp in bin/) → draft entry "visit 8_10_26:
        filters, salt, entry bulb, threshold…"  → needs_answer → his hand lands it
 07:00  glass › TBC › Visit: checklist rows from the draft, photos attached,
        🟢🟡🔴 per row, temp/humidity; "invoice this visit" →
        `tbc_estimate`-style skill writes TBC-1007 as HTML from the record,
        counter is the only issuer, history line + hash → DRAFT
 07:10  he reads the draft in the glass, confirms → PDF via print, Zelle memo
        text ready to paste; nothing is sent by the box
 07:15  "remember that the west-wall conduit is still open" → memory.pending →
        his hand lands it → next visit's standing carries it
 18:00  glass › marketing: `release` two photos + the visit summary →
        worlds\marketing\ (the only door across) → `campaign` pipeline drafts
        three posts + a calendar; Guardian refuses the one that names a street
 18:10  he posts by hand. The transcript, the release lines, the hashes are the record.
```

Every arrow above is a `needs_answer` or a delivery; none is an auto-act.

### 2.3 API contracts (the door's verbs)

THE LINE already carries 25 tools; the appliance adds three families,
every call naming its world (`project`), unknown worlds refused by name:

| family | verbs | notes |
|---|---|---|
| **environments** | `env_list` · `env_fork <template> <name>` · `env_open` · `env_close` · `env_retire` · `env_reload` | fork copies declarations + `law/` verbatim, never record; retire = rename, never delete |
| **runs** | `run_start {world, objective, pipeline?, feed?, method?}` → run id + transcript path · `run_answer` · `run_cancel` · `run_events` (SSE) | maps 1:1 onto `serve.py`'s wire: objective / answer / cancel / close in; opened · run · seat · token · tool · needs_answer · delivery · refused · … out |
| **routing** | `route_table` · `route_dry_run <text>` → `{world, pipeline, rule}` | `ROUTES.md` per world + a global one at the origin |
| **rack** | `rack_list` (exists) · `rack_plan` · `rack_override` · `rack_warm` · `rack_unload` · `rack_sync` | pull stays behind `MANJUEL_RACK_PULL` + confirm |
| **drop** | `drop_list <world>` · `drop_ingest <world> <file>` (hash + ledger line + draft) | the watcher calls it; the glass shows it |
| **world skills (TBC)** | `tbc_estimate`'s verbs as they are: `generate` · `validate` · `next-number` · `list` · `batch` — argv, `--json` stdin/stdout, exit 0/1/2/3/4 | already the seam's shape; wraps as skills without change |

Forbidden verbs stay absent from every route table by construction:
approve · ascend · merge · commit · push · delete · reject · promote ·
**send** · **post** (the two the business adds).

### 2.4 Storage — what lives where

| store | holds | truth? |
|---|---|---|
| **files under `worlds\<w>\`** | declarations, `Filed\{property}\{date}\` records, photos, transcripts, ledgers | **yes** — canonical, append-only |
| `law/chain.jsonl` per world | the sealed laws (4 links + 5–6 when sealed) | yes; verified before any seat sits |
| `index/vectors.db` per world | embeddings of that world only (`NO WORLD IS A ROOT` for the origin) | derived; rebuilt on demand |
| SQLite mirror (atlas `store`) | sittings, runs, receipts, TBC entities folded from the record | derived; `journal_sync` pointer; refuse on FLIP/TAMPER |
| browser `localStorage` | nothing that matters (a remembered tab, an unsent draft) | never |
| `sessions/*.jsonl`, `SEAT_LOG.md`, `memory.md` | the record's own spine | yes |

`tbc_hub_v2.html`'s store (`localStorage['tbc_hub_v2']`, 26-field clients,
photos as dataURLs, contracts as PNG signatures) is the one thing this
design **retires**: it is a second truth in a browser tab. Its shapes are
kept (§3.1); its home moves to the record.

---

## 3. Deep dive

### 3.1 The TBC data model — from what is on disk to what the record needs

What exists: `clients.json` (id, name, address, tier, grandfathered_rate,
contact, notes), `schemas/estimate.json` (client_id, est_num `^(AUTO|TBC-\d{4})$`,
valid_days, service_summary, notes, line_items[{desc, bullets, amt}]),
`.tbc_estimate/counter.json` + `history.jsonl`, the hub's 26-field client,
photo `{id, clientId, tag, dataUrl, filename, ts}`, contract
`{clientId, tier, ownerSig, tbcSig, signedTs}`, invoice
`{invNum, clientId, total, status, date, due, lines[]}`, the checklist's
`PHASE1`/`PHASE2` rows with ✅/🚩/N/A, the log/packet/report/CSV exports.

What the record needs — one folder per client world-side, one JSON line per
event, files beside them, every line hashed:

```
worlds\TBC\
  clients\<client-id>\            one folder per property
    client.json                   the 26 fields (access codes: see §3.5)
    contracts\<tier>_<date>.html  + .sig.png ×2 + release line
    visits\<YYYY-MM-DD>\          checklist.json · notes.md · photos\*.jpg
                                  · report.html · invoice-TBC-####.html
    estimates\TBC-####.html       + the input .json that made it
    ledger.jsonl                  append-only: {ts, kind, ref, hash, actor}
  counter.json                    THE ONLY ISSUER of TBC-#### (see below)
  history.jsonl                   every generation, as today
```

**Kinds** on `ledger.jsonl`: `intake`, `contract_signed`, `visit`,
`checklist`, `photo`, `estimate`, `invoice`, `payment`, `release`,
`note`, `reminder`. `state = fold(ledger)`: the client's open items, the
next visit due, the balance, the last five wear-trend rows — all derived,
never stored.

**The ID scheme, fixed.** Today invoices (1001–1004, by hand) and estimates
(1005, 1006, by the tool) share `TBC-####` with no collision guard, the
counter is bypassed whenever `est_num` is given, and `TBC-1006` is logged
twice with two totals. Design: the counter is the only issuer; `est_num:
AUTO` is the only accepted input; a hand-numbered document is *imported*
with a ledger line saying so; invoices and estimates keep one sequence
(his clients already know it) but every number is unique by construction
and a stroke proves it.

### 3.2 The engine per world

`manjuel.py --headless --ground worlds\TBC` — the piece that unlocks everything
(`cli.ROOT` is the one hard-coded layer; every function below it already
takes a ground). One process per open world, one run at a time per world,
THE LINE enforcing one writer. A world's `agents/` carries only the seats it
needs: TBC's door (a Steward on llama3.2), the Router, the Guardian, a
**Clerk** seat for the estimate/invoice skills (phi4-mini, reading numbers
off the record), and — only in `worlds\marketing` — the copywriter that
`modelfile` describes, started on the smallest model that can write a
caption, moved up on a measured failure (SITTING LAW 3), never at the door.

### 3.3 Contextual understanding — how "what I'm saying" becomes the right run

Four layers, each cheaper than the next, each recorded:

1. `ROUTES.md` at the origin: *"invoice"*, *"estimate"*, *"walkthrough"*,
   *"filters"* → `worlds\TBC`; *"post"*, *"caption"*, *"campaign"* →
   `worlds\marketing`; *"how much did I make"* → `worlds\books`. Longest
   match wins, the fired rule goes in the transcript header.
2. `intent.py` inside the world: names a tool, a file, a folder, a
   follow-up; decides the call when the argument is proven on disk.
3. The door's context: the **standing** (what today is for), the **story**
   (this sitting so far), the **thread** (the conversation), and the
   world's **index** (`semantic_search` over its own record only). "What's
   still open at the west wall" is answered from the ledger fold, not from
   a model's memory.
4. The Router seat, the one executor, five hops, dedup, claim-check.

A classifier seat is consulted only when 1–2 name nothing, and its verdict
is testimony (`routed_by: model`), never a route it invented.

### 3.4 The drop — photos and voice from the phone

An SMB share on the box, one folder per world: `\\box\drop\TBC\`. The
phone's Files app writes there; no app, no account. The watcher (Manjuel
`watch.py`, already classifying arrivals) hands each file to `drop_ingest`:
hash via `atlas` → ledger line `{kind: photo, file, sha256, ts}` → EXIF GPS
stripped **on arrival** (the scrub proved 150 of 266 photos carried the
house's coordinates) → a draft `visit` entry from the folder date and, for a
voice note, a whisper.cpp transcript → `needs_answer` in the glass. Nothing
is filed until his hand says which client and which visit. This retires the
`Filed\{property}\{date}` hand-filing and the `LAST_TOUCH` sidecars (one
stamp per batch today, not per file — a receipt that isn't one).

### 3.5 Secrets and codes

The intake form collects gate, lockbox, smart-lock and alarm codes and
Wi-Fi passwords. Today every hub build stores them in `localStorage` in
clear, writes them into `.txt` packets and CSV rows, and "encrypts" the
backup as base64 with the PIN in front. Design: those five fields live in
the world's `.env`-class file (`clients\<id>\access.env`), honoured by the
one skill that needs them at visit time, **never** printed, indexed,
exported or shown to a seat (RULE 7 / LAW 9 already do this for `.env`;
`vectors.is_secret` already shields the name). The packet prints "on file"
where a code was.

### 3.6 Rendering — estimates, invoices, contracts, packets

HTML from templates by string-replace (`tbc_estimate/generator.py`, as
built), print-to-PDF from the glass (what he does today, zero
dependencies). `weasyprint` is **not** taken on: Manjuel's one-dependency law
and atlas's zero. If a server-side PDF is ever needed, it is one hand-rolled
writer over the seam, not a pip install.

### 3.7 Sending — email, text, posting

The box drafts; the box does not send. `mailto:` with the body filled (the
hub's `emailReport()` shape), copy-to-clipboard for texts, the post text
and image ready in the glass. Sending is a human act on a human's device —
RULE 4 (nothing that needs someone else's server) and the gate (nothing
outbound without his hand) agree here, and a hallucinated invoice can never
leave the LAN.

### 3.8 Error handling and retry — the engine's, unchanged

Seat timeout by size → `SEATS THAT FAILED` in the delivery; turn deadline →
`OUT OF TIME`; tool failure → `THIS TOOL FAILED`, never narrated as success;
partial read → `READ IN PART`; law that doesn't verify → no seat sits; rack
down → the ground opens, runs refuse, the glass says so; index busy → the
run queues. Retry is a human decision (`retry / skip / abort?` reaches the
glass as `needs_answer`), except `On Fail: skip` seats, which the record
names.

### 3.9 Caching

None that is truth. Warm models (`/warm`, spine only), the embedder
resident, `supports_tools` cached per model tag, the standing built once at
sitting open (RULE 9's shape). Everything else is read off the record each
turn — the estate's rule that a number in a document is a claim about the
past.

---

## 4. Scale and reliability

### 4.1 Load

Single operator, sequential inference. A busy day is 30 turns × ~20 s at
the door + 3 pipelines × ~300 s + one index refresh — under an hour of GPU
time. The card is the only contended resource; THE RACK's seat-call queue
serializes worlds at seat granularity and shows the queue in the glass.
There is no horizontal scaling and no need for it: **a second operator is a
second box** (Manjuel SPEC §1), and a world moves by copying a folder.

### 4.2 Failure and recovery

| failure | behaviour | recovery |
|---|---|---|
| Ollama down | ground opens; runs refuse by name; record, palette, git state all live | `ollama serve`; next turn reconnects |
| a seat past its bound | cut, named in the delivery | his call: retry, reseat smaller, raise the bound |
| VRAM over budget | `vram.render` refuses the pipeline before it runs | override recorded, or smaller tier |
| a world's `law/chain.jsonl` fails to verify | **no seat sits** | he re-seals or restores from the origin's copy |
| FLIP / TAMPER on any Manjuel | reads only; the glass alerts; no writes | the operator rules |
| box dies | the record is files on NAS disks; SQLite/index are derived | copy the folder to a new box; `atlas db import`; rebuild the index |
| power loss mid-write | JSONL append + `os.replace` counters; Manjuel replays past `last_applied_n` | nothing to do; the record never holds a state the journal doesn't justify |

Backup is `robocopy /MIR` of `Research\` and `worlds\` to a second disk or
a second box; Manjuel verdict on the copy is the proof it is whole.

### 4.3 Monitoring and alerts

From the spec, all read off the record: seat over timeout, turn ≥ 80 % of
budget, gate refusal, claim-check hit, index refused, VRAM over budget,
FLIP/TAMPER, a sitting left open — shown live, kept as
`kind: alert` lines. For the business: a visit due and not scheduled, an
invoice past due, an estimate past its 30 days, a High open item older than
a visit cycle (the west-wall conduit and the AC wiring are both High and
both older than two visits today).

---

## 5. Trade-offs, made explicit

| decision | chosen | over | why | cost |
|---|---|---|---|---|
| Truth | plain files + hash chain | a database | portable, readable by a stranger, provable, survives the vendor | joins are folds; a mirror must be maintained |
| Engine transport | stdio JSON lines (`serve.py`) | a socket / HTTP in the engine | keeps Manjuel's "no listening socket" and atlas's "one computer"; one process per world = one writer | THE LINE must supervise processes |
| Inference | small local models, tiered, sequential | one big model or a cloud API | $0/month, private, fits 16 GB, measured not assumed | a court takes five minutes; some tasks need the 12b tier |
| Network posture | LAN only, one operator credential | loopback only / WAN with auth | a NAS is a network appliance; the phone must reach it | the P2 gate (auth, TLS) becomes P0-adjacent — one secret, self-signed cert |
| Sending | never from the box | SMTP / social APIs | RULE 4 and the gate; no hallucinated invoice leaves | one more tap per message; posting is manual |
| PDF | print-to-PDF | weasyprint | zero deps; what he does today | no unattended PDF generation |
| Codes | `.env`-class file, never shown | fields in the client record | LAW 9 already covers it; the packets stop leaking | the visit skill must read it at the seam |
| Second user | a fork (a second box or a second world) | multi-tenant auth now | Manjuel SPEC §1; nothing to get wrong yet | remote/family access waits for a ruling |
| Dependencies | Manjuel `ollama` only; atlas none; hand-roll or refuse | pip/npm/crates | the two charters; no supply-Manjuel surprise on a home box | more code owned; slower on the margins |
| The hub prototype | keep its shapes, retire its store | keep `tbc_hub_v2.html` as is | a browser tab is not a record; localStorage is not durable | the eight panels are rebuilt over THE LINE |

---

## 6. Build order — pieces, each his to name

The five backend pieces already on the table (`--ground` · the marketing
world · `release` · the marketing seats and pipeline · the door drives a
world) stand. The business adds these, in dependency order:

| # | piece | done when |
|---|---|---|
| T1 | **`worlds\TBC` becomes a world**: `agents/` (door, Router, Guardian, Clerk), `skills/` (the `tbc_estimate` verbs wrapped as skills; `intake`, `visit`, `invoice`, `packet`), `pipelines.md`, `ROUTES.md`, `law/` copied and sealed, `index_roots.txt` = itself | the world opens its own sitting; the origin's roots resolve nothing under it; strokes green on a mirror |
| T2 | **the counter is the only issuer**; `AUTO` only; hand-numbered documents imported with a ledger line; uniqueness stroked | `history.jsonl` can never carry one number twice |
| T3 | **the client ledger**: `clients\<id>\ledger.jsonl` + the fold (`open items`, `next due`, `balance`); the four visits and two estimates on disk imported as the first lines, hashed | `state = fold(ledger)` reproduces `seat_log.md`'s NEXT section from the lines alone |
| T4 | **the drop**: SMB share, `drop_ingest`, EXIF-strip on arrival, whisper transcript to draft, `needs_answer` to file | a photo from the phone is a hashed ledger line with no GPS in under a minute, filed only by his hand |
| T5 | **access codes to `.env`-class**; the packet prints "on file"; a stroke proves no export, index or transcript carries a code | — |
| T6 | **the glass's TBC pages** over THE LINE: clients · visits · photos · estimates · invoices · contracts · calendar · logbook — the eight panels of `tbc_hub_v2.html`, reading the record, writing through `run_*` and `needs_answer` only | a visit start-to-invoice with no terminal and no localStorage |
| T7 | **the LAN gate**: bind to the LAN interface, one operator secret, self-signed TLS, the phone reaches the glass | — his ruling first |
| T8 | **the rulings executed** (Appendix A): tier identity, scope, materials rule, retainer, grandfather, non-compete version — as edits to the templates, by his hand or at his word | one canonical document per kind; the drift folded, not erased |

Each piece: read what it touches whole, build on a mirror, one CHANGELOG
entry, "restart required" when `manjuel/` moves, stop.

---

## 7. What to revisit as it grows

- **Remote access** (the box from outside the house): a WireGuard-class
  tunnel is the only shape that keeps "no cloud"; his ruling, not a default.
- **A second person** (a partner, a technician with the Field role from
  `agents.md` §2): a world of their own or a second box; the gate model
  (`can_approve:false`) already fits a technician who writes visits and
  never invoices.
- **The engine port to Go** (spec H6): only when the golden-master
  transcripts say parity; the Python engine is not the bottleneck today.
- **A PDF writer** and **an outbound mailer**: both only if a ruling
  reverses "the box does not send."
- **More GPUs**: the rack scheduler is already the seam; `OLLAMA_NUM_PARALLEL`
  stays 1 per card.
- **A second business** on the same box: a fork of `worlds\TBC`'s
  declarations, none of its record — the environment model exists for this.

---

## Appendix A — what the TBC world holds, and what needs his ruling

Read in full today (two read-only surveys; nothing written). The folder
is the business's whole history: four billed visits ($75 + $75 + $350 + $75
= **$575** invoiced; an $874 proposal whose labour half became TBC-1003;
estimate TBC-1005 at **$1,185** / deposit $592.50 outstanding), the intake
and checklist as filled, 266 photos, three generations of contracts, four
tiers ($75–150/visit · $150–350 · $350–700 · $700–1,200 per month), a
working estimate CLI whose shape is already the seam's (argv, `--json`
stdin/stdout, exit 0/1/2/3/4), a single-file hub prototype with a real
relational store in the wrong place, and an "Agentic OS" plan (`agents.md`
§9) that describes THE LINE almost verbatim.

**Rulings the templates need, one line each** (the drift is folded in
`worlds\TBC`; nothing is erased):

1. Tier 2 is either *Monthly, one visit, $150–350* or *Bi-Weekly, two
   visits, $150–300* — two files say each.
2. Tier 3 either includes routine on-site replacements (filters, salt,
   bulbs, batteries) or "no hands-on repairs" — two near-identically named
   files say opposite things.
3. Materials: owner-supplied / cost + 10 % / $50 per-item pre-auth / the
   A.R.S. § 32-1121 $1,000 aggregate handyperson cap — four rules, the last
   in one file only and the most consequential.
4. The emergency retainer: $50/month in two documents, $0.00 on every
   real invoice; four different names.
5. The grandfathered $75/month on a $350–700 tier is in `clients.json` and
   nowhere a client would sign.
6. Termination notice: 30 days everywhere except the hub (14/21/30 + a
   3-month minimum); venue Yavapai-or-Coconino vs Yavapai only.
7. "No property management" in every contract vs "Licensed Co-Host /
   Property Manager" and a "Co-Hosting Management Fee" in the older packets.
8. The non-compete exists in two versions that name opposite parties as
   employer and side business; only one can be true.
9. Numbering: one sequence for invoices and estimates, no collision guard
   (piece T2).
10. Three agent personas for one business (a copywriter modelfile on
    14b, a "steward" on 4b, a retired `tbc-agent`) and two watch-folder
    daemons watching different folders. One door per world (piece T1).

**The scrub, second pass** (the survey found what a byte-scrub of the
named tokens could not): two non-compete documents carrying a third party's
company and personal names; two "installer" HTML files carrying the
business name inside base64 payloads; one hub file with a live property
UUID and a hard-coded PIN; a P.O. box in two packets; a person's initials in
two checklists; the Windows user path in four files. Awaiting his word, the
world being read-only by position.
