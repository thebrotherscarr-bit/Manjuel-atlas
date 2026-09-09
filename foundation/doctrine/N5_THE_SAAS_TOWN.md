# N5 — THE SAAS TOWN: property management + tradeskill coordination

The town, filled: every occupant and every skill needed to run a fully
functional software company for property management and tradeskill
coordination — standing on everything the estate already is. Nothing is
rebuilt; every new piece is additive, carries the Forge's contract, proves
itself in a child, and waits for the operator's hand before it is part of
the self.

Working branch moving forward: smith/deep4 (the operator's new main).

## 1. THE PRODUCT

A deployable platform with five cores:

  PROPERTY CORE   properties, units, tenants, leases, rent rolls,
                  inspections and compliance
  TRADE CORE      tradespeople (credentials, areas, rates, ratings),
                  work orders, dispatch, duty rosters, time cards, invoices
  OPS CORE        service clocks, incidents, the queue, the digest, the bus
  FINANCE CORE    the till (money ledger), billing, quoting
  SECURITY CORE   the vault, the audit trail, identity/access, the ark,
                  the airgap discipline

## 2. THE OCCUPANTS (org chart of the town)

  The Steward ......... CEO — the agent loop, routes, tools (steward/)
  The Clerk ........... county clerk — facts, provenance, the hyper-core
                        (garth + the bound paths)
  The Vault ........... security — vault, security, heartguard, warden
  The Ledger .......... money — till (the cash book), mint (bounty pay)
  The Messenger ....... gateway — traffic between the tiers, on a chained bus
  The Watch ........... watch, radar, clock — sentinels and horizons
  The Board ........... commons board + the forge (artifact pipeline, the
                        smith, the registry)
  The Library ......... librarian, almanac, seek, inspect, ark
  The Rack ............ the voices (scale/rack), the door (rackrelay)
  The Glass ........... aurora — the display at 127.0.0.1:7788
  The Field ........... dispatch, workorder, incident, sla, pulse
  --- occupants this plan adds ---
  The Property Keeper . property — the property book (new, batch 1)
  The Trade Master .... trades — the tradesperson book (new, batch 1)
  The Billing Clerk ... invoice — the billing book (new, batch 1)
  The Roster Master ... roster — the duty rosters (new, batch 1)
  The Timekeeper ...... timesheet — the field time cards (new, batch 1)
  The Auditor ......... audit — the security trail (new, batch 1)
  The Contracts Clerk . contract — agreements and leases (new, batch 2)
  The Compliance Officer compliance — inspections and certs (new, batch 2)
  The Gatekeeper ...... access — identity and permissions (new, batch 2)
  The Estimator ....... quote — estimates and job costing (new, batch 2)
  The Client Warden ... client — accounts and sitreps (new, batch 3)

## 3. THE SKILL ROSTER (the full set — 24 skills)

  Existing (13): num, seek, inspect, ark, almanac, workorder, till,
                 rolodex, dispatch, incident, sla, pulse, gateway
  New (11):      property, trades, invoice, roster, timesheet, audit,
                 contract, compliance, access, quote, client

  Every new skill: # skill: header, run(arg), describe(), prove(); hash-
  chained append-only records under shelf/ops/; temp-dir hermetic proves;
  tamper caught and pinpointed, never erased. Every skill verified in a
  child by a different hand before it travels; ascended by the operator.

## 4. THE 30-DAY PLAN

  DAY 1 (this session)
    - smith/deep4 becomes the working main; the town plan is set (this doc)
    - batch 1 built and proven: property, trades, invoice, roster,
      timesheet, audit — smith gates 1-2 held, forge registry verified by
      the smith's hand in sealed children, field reports filed
    - operator ascends batch 1 (his hand), commits ride the branch

  DAYS 1-7  PHASE 1 — FOUNDATION (the platform stands)
    - batch 1 skills walked to field report; live steward run through the
      rack door (relay --warm, NEIRO_RACK, run.py) driving all 11 skills
    - gateway rack warm-keep: a carry never finds the rack dark
    - aurora sitrep: pulse world rendered on the glass (read-only surface)
    - packaging: boot.bat/boot.sh + NEIRO_LAUNCHER verified on a clean box
    GATE: prove_all EXIT 0; every skill prove PASS in a child; covenant unmoved

  DAYS 8-14  PHASE 2 — TRADE (the flows close)
    - batch 2 built and proven: contract, compliance, access, quote
    - the money flow: workorder -> dispatch -> timesheet -> invoice -> till
    - the clock flow: sla (recurring) -> roster -> dispatch
    - the security flow: access gates the doors; audit witnesses every act
    GATE: all 20 skills prove PASS; the five flows live-tested end to end

  DAYS 15-21  PHASE 3 — SECURE AND TEST (the walls harden)
    - audit hardening: every skill's mutating act witnessed on the trail
    - ark drills: full restore from the ark into a bare tree
    - security review: vault + security + access + seal_airgap, findings
      recorded, none patched in the sealed organs — additive fixes only
    - full suite on the CI matrix (3.9/3.11/3.12) on smith/deep4
    - staging server: a clean estate box running the whole town with
      real-shaped data; the glass live
    GATE: prove_all EXIT 0 on all three Pythons; restore drill passes

  DAYS 22-28  PHASE 4 — CLIENT AND PACKAGE (the company faces out)
    - client built and proven (accounts, portfolio, sitrep templates)
    - caretaker scripts (S6-style) for every new skill; operator docs
    - client onboarding: worlds per client, pulse world sitreps, aurora
      dashboards, report folds (what happened, when, by whose hand)
    - release notes, pricing/billing shape through the till, the boot
      ceremony, backup schedule (ark daily), incident runbook
    GATE: every skill has a caretaker; a full client world live in staging

  DAYS 29-30  PHASE 5 — GO (the deploy)
    - final gates: prove_all EXIT 0; all 24 skills prove PASS in children;
      registry straight; covenant hash unmoved
    - dry run: the launch script on staging, glass up, rack warm, backup
      taken and verified
    - the operator's sign-off; production server brought up; handoff written
    GATE: the operator's hand on the deploy — the same hand that ascends

  The rule through all of it: nothing becomes part of the self unless it
  proved itself first and the operator's own hand merged it. The record
  shows everything.
