# Testing

## The suites run on someone else's machine now

`.github/workflows/prove.yml` runs both suites plus `law.py --prove`,
`buildmap.py --check` and `standup.py --dry` (and the record audit,
report-only) on Windows and Ubuntu, Python 3.10 and 3.13, on every push.

**No rack, no network, no GPU, no model.** Every model call in both suites
is a stub; `ollama` is installed only because `manjuel/runtime.py` imports
it at module load, and nothing in CI reaches 127.0.0.1:11434.

That offline property is now a PUBLIC CLAIM, which changes its status: if a
change makes these suites need a live model, **that is the regression**, not
an inconvenience. The claim is the thing being protected.

`audit_record.py` runs there too with `continue-on-error` -- it reports and
never gates, for the same reason it never gated here: the corpus is ambient
and an assertion over it goes red because someone ran the CLI.

`law.py verify` is deliberately NOT in CI. It walks the committed chain, and
a fork with a re-terminated law file should fail on the operator's terminal
where it means something, not in a job that cannot tell tampering from a
checkout artifact.

Five tiers, and they answer five different questions. Confusing them is how
a suite ends up testing the room instead of the code.

    STROKES   tests/test_manjuel.py   does the CODE do what it must?
              Offline, stubbed, deterministic. Gates every change.

    SMOKE     tests/smoke_cli.py       does the REPL still run end to end?
              Scripted stdin, stub model, throwaway ground.

    AUDIT     tests/audit_record.py    is the RECORD honest?
              Reads the real logs. REPORTS, never gates.

    PARITY    /parity in the REPL      does Manjuel earn its keep?
              Real models. Measures, never rules. See parity.md.

    SITTINGS  running manjuel.py         the E2E tier. Real models, real
              disk, real voice; `logs/` is the assertion record.

---

## Running them

    python tests/test_manjuel.py         everything
    python tests/test_manjuel.py intent  only strokes whose function name
                                          matches "intent"
    python tests/smoke_cli.py
    python tests/audit_record.py

**Read `tests/last_run.md`, not the scrollback.** Both suites write it: each
one's standing, then every failure with its detail and its
`function:line` — and nothing about the ones that passed beyond the count.
A green run's page is four lines saying so.

A selected run never stamps `last_run.json`: a partial tally reported as the
suite's standing would be the exact lie the boot report exists to prevent.

**Where the suites keep their word:**

    tests/last_run.json     where each suite stands, stamped by it
    tests/last_run.md       the red, with addresses
    tests/run_history.jsonl one line per run — finished or CRASHED, appended
    the boot report         what was last proved, when, and STALE if the
                            ground has changed since

A suite marks itself `running` BEFORE its first stroke. A stamp still saying
so means the process never reached the end — a crash used to leave the
previous SUCCESSFUL numbers standing, and they were read aloud as green.

---

## The discipline

**Stroke before "fixed".** Reproduce the failure as a stroke, watch it go
red, then fix it. A fix with no stroke is a hope.

**A superseded ruling REWRITES its stroke; it never deletes the guard.**
When a new rule invalidates an old stroke, that is evidence the rule bites.
Rewrite the stroke, note in it what moved and why, keep what it was
guarding. Several have moved that way: the traversal stroke, the Router's
token cap, the tool-loop cap, the client-world fixtures.

**Guards are stroked BOTH ways.** Firing and not firing. A guard with only a
happy-path test is not a guard — and the not-firing half is what stops it
crying wolf, which is the failure mode that gets a guard switched off.

**Fixtures mirror the real thing.** `env_for()` once omitted `skills_ref`
and a guard tested green while dead. `StubRuntime.chat` once took no
`tools=`, and the smoke suite sat RED at 34/50 for days while the strokes
stayed green. A stroke now compares both fixtures to `OllamaRuntime.chat` by
inspection, and reads `smoke_cli.py` by AST rather than importing it.

**A stroke that reads the AMBIENT environment tests the environment.**
`test_ink` once read the real stdout — green when piped, red at a terminal,
for weeks. On 2026-09-02, six of seven reds were strokes reading ambient
state: a hardcoded model tag, a missing `git`, a keystroke buffered for the
shell. Force the condition, or probe it once and skip loudly:

- git is probed by REHEARSING THE REAL OPERATION (a `git init` in a temp
  dir), not by asking whether the binary exists — a probe of something
  ADJACENT can pass while the operation still fails.
- when it cannot run, the six git strokes return instead of raising, and
  ONE named red says what could not be proved. Never a crash, never a green
  run that quietly proved less than it claims.

**Anchor phrases live in prompts, so they must be WRAP-SAFE.** A charter is
line-wrapped; `"READ from it, never remembered" in prompt` fails on a phrase
that is plainly there. Compare against `" ".join(prompt.split())`. And a
phrase a stroke greps for in SOURCE must stay on one line — rewrapping one
broke the same stroke twice in ten minutes.

**Make strokes DISCRIMINATING.** The stub embedder scores by bag-of-words
over a fixed VOCAB (`test_manjuel.py`, near the top) — pick fixture words
that are ON that vocab, or the stroke passes for the wrong reason.

**No client data, ever.** Strokes prove the client shield against a
SYNTHETIC world in a temp directory. Two strokes once read a real client
folder on every run — the estate's own shield walked around by its own
suite. A stroke now reads this suite's source and fails if any test reaches
into `worlds/` from the real ground.

---

## The suite tests the estate; two strokes test the suite

- **every `test_*` defined in the file is actually called by `main()`.**
  Registration is by hand, so a new function can silently never run — which
  is exactly how smoke sat red for days.
- **no two strokes share a name**, so a red names one thing. Its first run
  found three collisions.

---

## What a stroke should look like

Name it as the PROPERTY, not the mechanism — the name is what appears in
`last_run.md`, and it should read as a claim about the estate:

    check("a failed tool cannot be reported as a success", ...)
    check("the parent worlds/ is never an index root", ...)

Say what earned it. Every guard in this ground came from a named failure;
the docstring carries the sitting and the fault, so the next hand knows
whether it is safe to change:

    """SITTING 63: "remember the operator rules" staged the SAME rule three
    times in one turn -- the Router answered "need another skill?" by
    repeating itself, and four junk entries piled up in pending."""

State the honest limits in the code, not in a later discovery. The
claim-check's docstring says it catches a claim that NAMES A FILE and that
invention citing nothing passes — written when it was built, so nobody
mistakes its reach.

---

## What is deliberately NOT tested

**Coverage percentages.** The invariant is better: every module owns at
least one stroke that fails if its contract breaks, every guard is proven
both ways, and every fixture mirrors the real interface by inspection.

**More E2E.** Sittings are the E2E tier and they already do real work — most
of the guards in this estate came from reading a transcript, not from a
test that anticipated the fault.

**Voice end to end.** It needs hardware. The SEAMS are strokeable and are
stroked: vocabulary bias reaching all three transcribe paths, hearing
corrections, the interrupt, the spoken cap.

## The suites and the checks -- the five CI runs, and the two that report

    python tests/test_manjuel.py     the strokes -- the ENGINE, offline
    python tests/smoke_cli.py         the REPL end to end, offline
    python law/law.py --prove         the ledger, hermetic, exit 0
    python tests/buildmap.py --check  BUILDMAP.md matches the code (regenerate
                                      with `python tests/buildmap.py`)
    python tests/standup.py --dry     the standup harness itself, on a stub

    LIVE, the operator's terminal only (models, VRAM, a sitting opened):
    python tests/standup.py           the seats through the standup set;
                                      report to logs/standup_<stamp>.md,
                                      toll paid, run_history appended as
                                      suite "standup". Expectations are
                                      mechanical (a tool ran, a gate fired,
                                      no markup in a delivery); the prose is
                                      the reviewer's judgement.

    python -m manjuel.us             the MANIFEST reconciled to the code
    python tests/audit_record.py      the RECORD swept for refused shapes

The last two REPORT and never gate, and the reason is the same for both:
they read things the operator edits by hand and that grow every sitting, so
an assertion over them goes red because he used the CLI. The strokes gate;
those inform. A number from them is a finding, not a failure.

Ask the estate itself with `proved` — it reads the stamp, the run history
and the manifest report, says STALE before it says anything else, and never
reports a crashed run as green.
