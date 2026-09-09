# Agents — index

The seats live one per file in **`agents/`**. `manjuel/registry.py` reads that
directory; this file is documentation only and is not parsed while `agents/`
exists. Use `/reload` in the REPL to pick up edits without restarting.

## Roster — read it live, never from here

**There is no seat table in this file, on purpose.** One lived here until
2026-09-02 and every row of it had gone stale: seats that no longer existed,
seats missing, and a model tag (`llama3.2`) that by then carried nothing. It
was not parsed by anything, but it *was* indexed — so the chain could retrieve
a confident, wrong account of itself. A roster is inventory, and inventory
belongs to the thing that holds it:

    the seats        agents/*.md — one file per seat, the source of truth
    what is declared /models, and registry.declared_models()
    what is LOADED   rack_list, or `run the rack` — priced live, in VRAM
    the running order pipelines.md, and /pipelines

The same rule governs `memory.md` and `rack.md`: **facts are read, not
written down.** A number in a document is a claim about the past.

Pipeline order lives in **`pipelines.md`** — adding one is editing that file
and running `/reload`, never a code change. Switch with `/use <name>`; see
`/pipelines`. A pipeline naming a seat that no file in `agents/` declares is
refused at startup, by name.

## File format

One `## Seat Name` section per file. Adding a file adds a seat; no code change.

```
## Agent Name
- **Model Target:** ollama:tag        (required)
- **May Call:** read_file, git_status  (ABSENT = NOTHING. Enforced at dispatch)
- **Wakes On:** flag[, flag]          (optional - what summons this seat)
- **Wakes:** first | last | after X   (optional - where it lands)
- **Stage:** guard|transform|route|gate|deliver   (optional, default: transform)
- **On Fail:** abort|skip|prompt      (optional, default: prompt)
- **When:** flag_name                 (optional - step only runs if flag is set)
- **Max Tokens:** 600                 (optional - cap it, leave room to think)
- **Context:** 8192                   (optional - num_ctx; dominates VRAM use)
- **Timeout:** 150                    (optional - seconds one call may take; else the 600 ceiling)
- **Voice:** David                    (optional - the speech voice; substring-matched on Windows)
- **System Prompt:**                  (required, MUST be the last field)
Everything after the System Prompt marker is prompt text.
```

`May Call` is the clearance: a seat with no such line may call **nothing**.
Grant is by omission from the tool list handed to the model, and refusal is
enforced again at dispatch.

Two seats sharing a name is an error naming both files, not a silent overwrite.

## The estate seats

Ported from `Desktop\Archive` and corrected against the **sealed foundation** —
`01_MYTHOS` / `02_CONSTITUTION` / `03_CREED` / `04_NEURO_CORE` (covenant
`65118a147dd49ed9`) and `05_THE_LAW`, at
`secondbrain\SecondBrain-collab\demo_vault\Manjuel\core\Archive\foundation\`.
Where a `.us` declaration or an LLD conflicted with the foundation, the
foundation stands.

**The court model** (THE LAW, "GOVERNANCE"): `steward` / `neiro` / `jesster` are
**THE COUNSEL** — they lay what they saw and what they recommend; their word is
testimony under signature, heard and never silently discarded. `manjuel` is
**THE COURT** — he reads the counsel, weighs it against the sealed foundation and
the record, and rules. The operator is **THE SOVEREIGN**; nothing binds him.

Laws every seat carries:

- Testimony is never fact (LAW 5; Constitution Art. II). Model output is tagged, never executed as instruction, never promoted by confidence.
- Evidence outranks assumption. Every seat distinguishes "I know" from "I infer" on demand.
- The Neuro-Core separation (sealed doc IV): **Pattern cannot create facts. Logic cannot create meaning.**
- The gate is final (LAW 6). No seat commits, pushes, lands, approves, or exiles.
- Fold, never delete (LAW 1). Corrections append; they never overwrite.

> **CLOSED 2026-09-01 — the order of the chain.** THE LAW has the court read
> the counsel and then rule, which puts Manjuel *last*. `estate` had been
> running him third, ruling without having heard Jesster. It now runs him
> last, as `court` always did; both pipelines carry the foundation order.