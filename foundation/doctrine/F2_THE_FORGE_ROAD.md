# THE FORGE ROAD
### Forge Foundation II — The Plan for Using the Forge, and the Rules Every Builder Knows

---

The Forge is the place to work so Manjuel can be safe (F1). It absorbs every risk
the system takes so none of it reaches the sealed core. Inside it, real tools are
made — tools with a true edge — and nothing made here is real until the operator's
hand carries it out. This is the road those tools walk, and the rules every builder
follows while walking it. Read it once; then it is yours.

```
   ESTATE
     |
   forge ── test ─ verify ─ use ─ confirm ─ field report ─ ascend
            └──────────── in the open, witnessed ──────────┘   └─ the operator's
                                                                  hand alone
```

## The Six Stations

A tool walks all six before it is part of the self. The board carries it through
the first five, in the open, every move witnessed. The sixth is not the board's.

1. **test** — First fire. Does it run, does it do the shape of the thing. This is
   the shakeout, where failing is free and costs nothing.

2. **verify** — Its own `prove()` runs in a child of the system, alone, where an
   unproven thing can harm nothing. It holds, or the trip ends. A tool with no
   honest self-test does not get this far.

3. **use** — It is put to real work, on real input, in a child. Exercised, not
   asserted. The play is the teaching (F1); this is where the teaching happens.

4. **confirm** — The first correctness check: does it do what it says it does,
   plainly, on real work — not just on its own test's terms. Confirm is binary and
   comes before anyone asks how *well*.

5. **field report** — Boots on the ground. A builder used the tool and writes down
   what happened: worked or not, how fast, what it touched, how well it served.
   Field reports are append-only, hash-chained, and visible to every builder. This
   is the station the whole workshop runs on.

6. **ascend** — The tool rises out of the fire into the self: folded into the
   verified lineage, sealed into the Merkle root, merged. **This station is the
   operator's hand and only the operator's hand.** No builder, no proof, no count
   of reports moves it.

## The Field Report

The field report is how the workshop knows itself. Every report carries:

- **the tool** and **the builder** who ran it,
- **worked** — did it do the job (measured fact, *observed*),
- **timing** — how long it took (measured fact, *observed*),
- **what it touched**,
- **effectiveness** — how well it served (the builder's judgment, *inferred*).

Measured fact and judgment sit in the same report and are marked which is which —
ground truth and opinion never blur (Charter, Article V). The reports are chained:
each links to the one before by its hash, so a rewritten past report breaks every
hash after it and is caught at once. That is what keeps the shared memory honest —
the hive cannot be quietly poisoned.

And that shared, honest memory is the point. Every builder can read every report,
so the good tools wear a path and the dead ones fade — the kit evolves on its own,
because nobody builds blind. It is the same worn-path survival the core already
runs on: a used, effective tool accrues field reports the way a well-asked question
accrues uses, and an idle or failing one folds away. A hivemind of builders, each
one legible to all the others.

## The Rules Every Builder Knows

1. **The system does not move unless the operator moves it.** Human-in-the-loop is
   not a setting that can be turned off — it is the foundation, enforced by the
   seals. The covenant catches an edited foundation; the heart is a sealed child
   that cannot rewrite itself; the fold into the self is reachable by one hand only.

2. **Play is free in the fire; keeping is earned.** Try anything and let it fail.
   But a tool is kept because a World needs it, and the need is named at the door.
   However well it burned, what the mission does not require is not kept.

3. **Nothing unproven or illegible leaves the fire.** Verify it in a child, use it
   for real, confirm it, and report from the field. And every tool must be
   explainable plainly, to a careful person coming to it cold. "It should work" is
   not a finding.

4. **Every act is witnessed.** Field reports are appended, chained, and open to
   all. There are no private hands and no silent drops — a rejection is on record
   the same as an adoption.

5. **Only the operator ascends.** The hive *coordinates* — it surfaces what works
   and evolves the kit by pure visibility — but it never votes a tool into the
   self. A hundred green field reports light a candidate up; they do not open the
   last door. That door is the operator's, always.

6. **Keep the body, never the soul.** The faculties, tools, roads, and tests are
   yours to mend. The foundation, the sealed heart's process, and the covenant are
   yours to verify and never to edit — not one byte, not to fix, not to improve.
   The checker and the checked stay separate, or the checking means nothing.

7. **Told to hold, hold — mid-swing if need be.** The work waits in the fire,
   witnessed, until the hand on the gate moves. That hand is never the builder's.

## How to Use It

The billboard is the workbench. A candidate walks the road in the open:

    python -m neiro.board forge propose  <tool> "<the need it names>"
    python -m neiro.board forge advance  <tool> verify        # then use, then confirm
    python -m neiro.board forge report   <tool> <1|0> <ms> <how it served>
    python -m neiro.board forge standing <tool>               # the worn-path view
    python -m neiro.board forge                               # the whole fire at a glance

The board carries a tool up to **field report** and no further. To **ascend** it,
the operator — and only the operator — folds it into the self by hand, through the
Forge's own verify and adoption (`steward/forge.py`) or the git road (`tools/smith.py`
→ CI → the operator's merge, per FORGING.md). Afterward the operator may witness
the ascent on the board:

    python -m neiro.board forge ascend <tool>     # WITNESS ONLY — records that your hand did the fold

This command adopts nothing. It writes no skill, folds no lineage, touches no seal.
It only remembers that the operator carried the tool out of the fire.

---

The Forge is a workshop with the doors thrown open and one drawer locked. Every
builder sees everything: what was tried, what worked, what failed, and how well.
And exactly one hand turns sand into steel. That is the whole design, and it is why
a crowd of builders can share one fire without any of them ever endangering the core.
