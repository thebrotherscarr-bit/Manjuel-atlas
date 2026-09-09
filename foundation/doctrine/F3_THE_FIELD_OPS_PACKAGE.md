# F3 — THE FIELD-OPS PACKAGE: confirmation to the operator

Delivered 2026-07-31 by the Steward's session, under the directive to build
the enterprise gateway/orchestrator. This is the confirmation: what was
built, how it was tested, by which path it travels, and where it goes next.

UPDATE — ASCENDED 2026-07-31 07:47 by the operator's word: all five skills
ascended on the town board ([ascend], witnessed) and in the artifact registry
(state=ascended, ascended_by=operator, chain straight, 25 lines). The exit is
walked: proposed by steward, verified by the smith's hand, ascended by the
operator, used by agent C (all five answer, code=0).

## 1. THE SKILLS (the deliverables)

  skills/dispatch.py   the work queue
  skills/incident.py   the crisis track
  skills/sla.py        the service clock
  skills/pulse.py      the field-ops digest
  skills/gateway.py    the messenger (core <-> upper tiers)
  doctrine/S6_THE_FIELD_OPS_SKILLS.md   the caretaker script (author, use,
                                        care, maintenance, time, uses)

All additive. Sealed organs untouched (foundation/, manjuel.py, steward/,
proven neiro/ organs, proofs/ — the two new neiro/forge registry entries are
records in shelf/, not patches). Provers for the registry at
shelf/forge/provers/<name>.prove.py.

## 2. TEST RESULTS (all witnessed this session)

### The skills' own proofs — five of five PASS
  python skills/<name>.py prove   -> PASS for dispatch, incident, sla,
                                      pulse, gateway
  (proves run hermetically in temp grounds, tamper included: each proof
   bends a line of its chain and demands the TAMPER verdict)

### The smith's gate — gates 1-2 held for all five
  python tools/smith.py --check skills/<name>.py
  gate 1 CHECK-IN held (header, run, describe, prove present)
  gate 2 VERIFY held (proof ran clean in a child)

### The workbench (steward/workbench.py) — rehearsal in children
  try_run  on each skill's run(arg):  ok=True, real answers
  check    on each skill's prove():   HELD, five of five
  (throwaway child per run; nothing adopted)

### The forge path (neiro/forge.py) — the registry, the parallel queue
  propose  : 5 artifacts, by=steward, prover + deliverable + quest,
             parents=[]  (a name is proposed once — the registry refused
             the re-proposes)
  verify   : 5/5 VERIFIED by a DIFFERENT hand (smith), run in real sealed
             child processes, workers=2, prover exit 0 [observed]
  findings : the first queue run FAILED (workers died on a driver bug in
             the parent script — the prover paths then failed on a bad
             root depth) — every failure is ON THE RECORD (failures=2
             each), never erased; the fixed run re-verified clean. This is
             the auto-prover rule working: nothing entered as ascended
             without a PASSING prover run by a different hand.
  registry : shelf/forge/artifacts.jsonl — 20 lines, chain STRAIGHT
             (propose x5, fail x10, verify x5)
  states   : all five: proposed -> verified, verified_by=smith
  ascend   : NOT taken — operator's hand alone, and the record shows whose
             it must be. No path from autonomous work to ascend exists.

### Live field timings (forge.invoke, the agent's own use route)
  dispatch 94ms   incident 75ms   sla 112ms   pulse 171ms   gateway 81ms
  1/1 worked each, chained + witnessed (field-report chain intact, 5 reports)

### The whole package
  python proofs/prove_all.py -> EXIT 0; covenant unmoved
  (65118a147dd49ed96068e8a3cf1a472db1f4d91253b23507c56926ba2d8d)

## 3. THE BUILD PATH (where these skills are, and what opens next)

  Town stations (neiro/board forge):  test -> verify -> use -> confirm ->
  field report — WALKED, all five, 1/1 worked.
  Registry (neiro/forge): proposed -> VERIFIED — RECORDED.
  Remaining, in order:
    1. THE OPERATOR ASCENDS (your hand): the ascend ceremony is operator-
       only, both on the town board (`python -m neiro.board forge ascend
       skills/<name>.py`) and in the registry (`neiro.forge.ascend(name,
       by="operator")`) — the registry additionally proves the parent gate
       (none here — this suite is the first generation).
    2. THE GIT CEREMONY (your hand): smith/<name> -> forge -> main, one
       branch per skill, one commit with the proof verdict; CI (prove.yml)
       is gate 4 on the push.
    3. THE RACK DOOR LIVE RUN (next session's work): relay --warm on
       127.0.0.1:11435, NEIRO_RACK=127.0.0.1:11435, python run.py — drive
       use dispatch/incident/sla/pulse/gateway with real traffic, field
       reports filed from the rack's own answers.

## 4. THE PLAN FOR THE TOOLS' EVOLUTION

  Near (this suite, hardening):
    - gateway rack door: a warm-keep loop so a carry never finds the rack
      dark (today: `rack: dark` is answered honestly, but the door can do
      better with a hot voice).
    - dispatch: world-scoped status (a per-world queue view, mirroring
      pulse's world scoping).
    - sla: recurring promises (cron-shaped due: a name that re-arms after
      met) — the clock then serves duty rosters, not just one-shot SLAs.
    - incident: severity-aware status rollup (P1 count first) and an
      optional incident -> dispatch handoff for the remediation job.
  Mid (the enterprise tier):
    - the client sitrep: pulse rendered through Aurora on the glass
      (aurora/server.py imports nothing; the digest is read-only and safe
      to surface).
    - the duty roster: sla recurring + dispatch worlds compose into shift
      handover pages.
    - reporting: the chains are the audit — a fold script per client/world
      that answers "what happened, when, by whose hand" without editing.
  Far (the estate's own discipline applies):
    - any new capability arrives as a new skill with run/describe/prove,
      walks the same stations, and is verified in a child by a different
      hand before it is ever ascended.
    - every evolution lands additive: never rewrite a chain line, never
      patch a sealed organ — new files, new folds, new provers.

  The rule that binds all of it: nothing becomes part of the self unless it
  proved itself first and the operator's own hand merged it. The record
  shows everything.
