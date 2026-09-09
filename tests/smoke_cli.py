"""Smoke test for the REPL itself.

    python tests/smoke_cli.py

The suite in test_chainkit.py proves the engine but never touches cli.py,
because the REPL is input()-driven. This drives main() end to end with a
scripted stdin and a stub model, so the loop, every slash command, the
confirmations and the shutdown path all actually execute.

It runs against a THROWAWAY COPY of the ground -- agents/, skills/ and
pipelines.md are copied to a temp dir and the module constants repointed at it
-- so a smoke run never writes to the real logs/, memory.md, SEAT_LOG.md or
sessions/.
"""

from __future__ import annotations

import io
import math
import shutil
import sys
import tempfile
import traceback
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from chainkit import cli                                    # noqa: E402
from chainkit.registry import Agent                         # noqa: E402

from chainkit.registry import AgentRegistry  # noqa: E402

SEAT = AgentRegistry.load(ROOT / "agents").get("Steward").model
# Every tag the ground declares -- a new seat must not fail preflight here.
from chainkit.skills import SkillLibrary  # noqa: E402
ALL_MODELS = ({a.model for a in AgentRegistry.load(ROOT / "agents").all()}
              | SkillLibrary.load(ROOT / "skills").models()
              | {"nomic-embed-text:latest"})

CHECKS: list[tuple[str, bool, str]] = []


def check(name, ok, detail=""):
    CHECKS.append((name, bool(ok), detail))


VOCAB = "vram ctx model budget dominated weights bread recipe".split()


class StubRuntime:
    """Stands in for Ollama. Answers every seat, embeds by bag-of-words."""

    def __init__(self, host="http://127.0.0.1:11434", keep_alive=""):
        self.host = host
        self.calls: list[str] = []
        self.embeds = 0
        self.foreign_models: list[tuple[str, int]] = []
        # Mirrors OllamaRuntime.supports_tools, which pipeline.py consults
        # before every seat call. Default False = the XML path, the same
        # fail-closed answer the real one gives for an unreadable model.
        self.tools_capable = False
        self.tools_seen: list = []

    def health(self):
        return None

    def warm(self, model, num_ctx=None):
        self.calls.append(f"warm:{model}@{num_ctx or 2048}")
        return 0.4

    def resident(self):
        # pretend another client is holding a model on the same card
        return list(self.foreign_models)

    def installed_models(self, refresh=False):
        # must cover every tag agents/ and skills/ declare, or preflight
        # refuses startup -- which is the missing-model guard doing its job.
        return set(ALL_MODELS)

    def missing(self, required):
        return sorted(t for t in required if t not in self.installed_models())

    def supports_tools(self, model) -> bool:
        return self.tools_capable

    def chat(self, agent: Agent, prompt: str, stream_to=None, tools=None,
             think_to=None, think=None):
        # `think=` arrived 2026-09-07 with the ruling loop (the fourth move).
        # `tools=` arrived in pipeline.py at 14e2711 and this signature was
        # not moved with it, so every REPL turn raised TypeError and the smoke
        # suite had been RED since -- 34/50, the last 9 checks never reached.
        # A fixture that does not mirror the real runtime is the trap named in
        # HANDOFF's test discipline; this is the second time in this file.
        # `think_to=` arrived at sitting 79 and is the third overall. The
        # strokes now compare this signature to OllamaRuntime.chat's rather
        # than rely on the next hand noticing.
        self.tools_seen.append((agent.name, [t["function"]["name"] for t in (tools or [])]))
        self.calls.append(agent.name)
        if agent.stage == "guard":
            out = "SAFE"
        elif agent.key == "router":
            out = ("The vram budget on this card is set by context length rather than "
                   "by model weights; a small model at a large num_ctx is resident far "
                   "above its file size.")
        else:
            # Long enough to be scored -- drift skips anything under MIN_CHARS,
            # and a stub that never clears it would silently prove nothing.
            out = (f"{agent.name}: the vram budget is dominated by ctx and not by model "
                   f"weights. Context length drives the KV cache, which is the bulk of "
                   f"what sits resident on the card during a run.")
        if stream_to:
            stream_to(out)
        return out

    def embed(self, model, text):
        self.embeds += 1
        t = text.lower()
        v = [float(t.count(w)) for w in VOCAB] + [0.05]
        k = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / k for x in v]


SCRIPT = """/help
/agents
/skills
/pipelines
/models
/pipeline
/use estate
/use nonsense
/nosuchcommand
/paste
The budget is dominated by ctx and not by model weights at all.
A second line of source material.
.
Explain the VRAM budget for this card
And what did I just ask you about?
/new
/last
/remember
a ruling worth keeping past this sitting
.
VRAM ruling
ruling
y
/memory
/git
/sittings
/reload
/toll
the smoke test ran
the repl had no coverage before
wire the toll into CI
y
/status
/exit
"""


def run_repl(script: str, ground: Path, runtime: StubRuntime) -> tuple[int, str]:
    cli.ROOT = ground
    cli.AGENTS_DIR = ground / "agents"
    cli.AGENTS_FILE = ground / "agents.md"
    cli.PIPELINES_FILE = ground / "pipelines.md"
    cli.SKILLS_DIR = ground / "skills"
    cli.WORKSPACE_DIR = ground / "agent_workspace"
    cli.LOGS_DIR = ground / "logs"
    cli.OllamaRuntime = lambda *a, **k: runtime

    old_stdin = sys.stdin
    sys.stdin = io.StringIO(script)
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            code = cli.main()
    except SystemExit as exc:
        code = exc.code or 0
    except Exception:
        buf.write("\n!! UNCAUGHT !!\n" + traceback.format_exc())
        code = 99
    finally:
        sys.stdin = old_stdin
    return code, buf.getvalue()


def main() -> int:
    try:
        from test_chainkit import begin_run
        begin_run(ROOT, "smoke")     # so a crash cannot leave a green stamp
    except Exception:
        pass
    ground = Path(tempfile.mkdtemp(prefix="chainkit_smoke_"))
    for item in ("agents", "skills"):
        shutil.copytree(ROOT / item, ground / item)
    shutil.copy(ROOT / "pipelines.md", ground / "pipelines.md")
    shutil.copy(ROOT / "index_roots.txt", ground / "index_roots.txt")

    rt = StubRuntime()
    code, out = run_repl(SCRIPT, ground, rt)

    check("the REPL exits cleanly", code == 0, f"exit={code}")
    check("nothing raised out of the loop", "UNCAUGHT" not in out,
          out[out.find("UNCAUGHT"):][:400] if "UNCAUGHT" in out else "")

    # startup
    check("startup names the sitting and session", "sitting 1" in out and "session S" in out)
    # the boot report replaced the one-line model summary
    for section in ("GROUND", "RACK", "RECORD", "GATE"):
        check(f"the boot report has a {section} section", section in out)
    check("boot names the seats, skills and pipelines",
          "seats ·" in out and "skills ·" in out and "pipelines" in out)
    check("boot names the active pipeline and what rests",
          "'default': Steward" in out and "resting" in out)
    check("boot says whether each needed model is resident or cold",
          ("RESIDENT" in out or "cold" in out) and "every run" in out)
    check("boot reports the record", "index" in out and "memory" in out and "logs" in out)

    # commands
    for cmd, needle in [("/help", "/remember"), ("/agents", "Security Guardian"),
                        ("/skills", "semantic_search"), ("/pipelines", "estate"),
                        ("/models", "model loads"), ("/pipeline", "1."),
                        ("/git", "git:"), ("/sittings", "sitting 1"),
                        ("/last", "budget")]:
        check(f"{cmd} produces output", needle in out, f"missing {needle!r}")

    check("/status reprints the report on demand", out.count("RACK") >= 2)
    check("/use switches pipeline", "pipeline: Security Guardian -> Steward" in out)
    check("an unknown pipeline is named, not fatal", "unknown pipeline 'nonsense'" in out)
    check("an unknown command becomes a palette search, not an error",
          "nothing in the palette matches 'nosuchcommand'" in out)

    # a real run
    check("the guard passed and the chain ran", "verdict: SAFE" in out)
    check("every stage of the pipeline reported", out.count("[1/") >= 1 and "[5/5]" in out)
    check("the delivery was printed", "--- delivery ·" in out)
    check("streaming reached the terminal", "dominated by ctx" in out)
    check("the run was logged", "logged: logs/" in out)

    # artefacts on disk
    logs = list((ground / "logs").glob("*.md"))
    prompts = list((ground / "logs" / "_prompts").glob("*.md"))
    check("a transcript was written per turn", len(logs) == 2,
          str([p.name for p in logs]))
    check("prompts were written apart", len(prompts) == 2)
    follow = [p for p in prompts if "what_did_i_just" in p.name.lower()
              or "and_what" in p.name.lower()]
    check("the second typed turn carries the conversation",
          bool(follow) and "Conversation so far" in
          follow[0].read_text(encoding="utf-8")
          and "Explain the VRAM budget" in follow[0].read_text(encoding="utf-8"),
          str([p.name for p in prompts]))
    if logs:
        first = sorted(logs, key=lambda x: "what_did" in x.name.lower()
                       or "and_what" in x.name.lower())[0]
        body = first.read_text(encoding="utf-8")
        check("the transcript records the objective", "Explain the VRAM budget" in body)
        check("the transcript records every stage", body.count("###") >= 5)
        check("the transcript records drift scores", "drift" in body)
        # the script does /use estate before the run, so 'estate' is correct --
        # what must never appear is the old fall-through value 'custom'.
        check("the transcript names the real pipeline, not 'custom'",
              "**pipeline:** estate" in body and "custom" not in body,
              [l for l in body.splitlines() if "pipeline:" in l][:1])

    check("memory.md was written by the operator's confirmation",
          (ground / "memory.md").exists())
    check("the landed entry carries the kind the operator typed (2026-09-07)",
          (ground / "memory.md").exists()
          and "- kind: ruling" in (ground / "memory.md").read_text(encoding="utf-8"))
    if (ground / "memory.md").exists():
        mem = (ground / "memory.md").read_text(encoding="utf-8")
        check("the entry is stamped OPERATOR", "provenance: OPERATOR" in mem)
        check("the entry carries its session", "session: S" in mem)
        check("the entry kept its title", "VRAM ruling" in mem)

    check("the toll was paid into SEAT_LOG.md", (ground / "SEAT_LOG.md").exists())
    if (ground / "SEAT_LOG.md").exists():
        log = (ground / "SEAT_LOG.md").read_text(encoding="utf-8")
        check("the toll records what ran", "WHAT RAN" in log)
        check("the toll records the operator's judgment",
              "the smoke test ran" in log and "wire the toll into CI" in log)

    check("the sitting was recorded", (ground / "sessions" / "sessions.jsonl").exists())
    check("the model was actually called", len(rt.calls) >= 5, str(rt.calls))
    check("models are warmed at launch, AT RUN CONTEXT, not inside the first question",
          any(c.startswith("warm:") for c in rt.calls), str(rt.calls[:3]))
    check("boot warms the SPINE model only, in the foreground",
          not any(c.startswith("warm:qwen2.5-coder") for c in rt.calls),
          str([c for c in rt.calls if c.startswith("warm:")]))
    import time as _t
    _t.sleep(0.2)   # let the daemon thread land its call
    check("the Reasoner's model warms in the background after entry",
          any(c.startswith("warm:qwen3.5:9b") for c in rt.calls),
          str([c for c in rt.calls if c.startswith("warm:")]))

    # a second client holding the card must stop chainkit warming over it
    g3 = Path(tempfile.mkdtemp())
    shutil.copytree(ROOT / "agents", g3 / "agents")
    shutil.copytree(ROOT / "skills", g3 / "skills")
    shutil.copy(ROOT / "pipelines.md", g3 / "pipelines.md")
    busy = StubRuntime()
    busy.foreign_models = [("phi4:latest", 13_000_000_000)]
    _, out_busy = run_repl("/exit\n", g3, busy)
    check("chainkit will not warm over another client's model",
          "not warming" in out_busy and "another" in out_busy,
          [l for l in out_busy.splitlines() if "warm" in l][:2])
    check("the drift check embedded the source and the stages", rt.embeds >= 2,
          f"{rt.embeds} embeds")

    # --- failure paths ---
    class Dead(StubRuntime):
        def health(self):
            from chainkit.runtime import BackendUnreachable
            raise BackendUnreachable(
                "Cannot reach Ollama at http://127.0.0.1:11434.\n"
                "  Start it with:  ollama serve\n  Underlying error: refused")

    g2 = Path(tempfile.mkdtemp())
    shutil.copytree(ROOT / "agents", g2 / "agents")
    shutil.copytree(ROOT / "skills", g2 / "skills")
    shutil.copy(ROOT / "pipelines.md", g2 / "pipelines.md")
    # Superseded, operator ruling sitting 33: a dead rack no longer exits --
    # the ground opens, the record works, and the chain reconnects when
    # Ollama appears. Models down is not estate down.
    code2, out2 = run_repl("/help\n/git\n/agents\nwho is manjuel\n/exit\n",
                           g2, Dead())
    check("a dead rack opens the ground anyway, exit 0",
          code2 == 0 and "RACK UNREACHABLE" in out2, f"exit={code2}")
    check("the palette works without models", "/remember" in out2)
    check("git state reads without models", "git:" in out2)
    check("/agents lists without models", "Security Guardian" in out2)
    check("a turn gets the plain reconnect line, not a crash",
          "still unreachable" in out2)

    # and the REAL runtime says the same thing, not just the stub
    from chainkit.runtime import BackendUnreachable, OllamaRuntime
    real_msg = ""
    try:
        OllamaRuntime(host="http://127.0.0.1:59599").health()
    except BackendUnreachable as exc:
        real_msg = str(exc)
    check("the real runtime's unreachable message names the fix",
          "ollama serve" in real_msg, real_msg[:70])

    class NoModel(StubRuntime):
        def installed_models(self, refresh=False):
            return {"nomic-embed-text:latest"}

    code3, out3 = run_repl("/exit\n", g2, NoModel())
    check("a missing model tag is named with its pull command",
          code3 == 1 and f"ollama pull {SEAT}" in out3, f"exit={code3}")
    check("a coder tag change is caught by preflight, not at first use",
          "qwen2.5-coder" in "".join(
              (ROOT / "agents" / "expert_coder.md").read_text(encoding="utf-8")))

    g3 = Path(tempfile.mkdtemp())
    shutil.copytree(ROOT / "agents", g3 / "agents")
    shutil.copytree(ROOT / "skills", g3 / "skills")
    (g3 / "pipelines.md").write_text("## Pipeline: broken\n1. Ghost Seat\n", encoding="utf-8")
    code4, out4 = run_repl("/exit\n", g3, StubRuntime())
    check("a pipeline naming a ghost seat refuses startup by name",
          code4 == 1 and "Ghost Seat" in out4, f"exit={code4}")

    width = max(len(n) for n, _, _ in CHECKS)
    passed = sum(1 for _, ok, _ in CHECKS if ok)
    print()
    print("  chainkit — CLI smoke")
    print()
    for name, ok, detail in CHECKS:
        print(f"    [{'PASS' if ok else 'FAIL'}]  {name:<{width}}  {detail if not ok else ''}")
    print()
    print(f"  {passed}/{len(CHECKS)} checks." +
          ("  THE REPL RUNS." if passed == len(CHECKS) else "  RED."))
    print()
    shutil.rmtree(ground, ignore_errors=True)
    # Stamp the tally beside the strokes' own, for the boot report. The
    # helper lives with the stroke suite; importing it is cheaper than a
    # second copy that could drift (the fixture-drift lesson).
    try:
        from test_chainkit import REPORT_FILE, record_run
        record_run(ROOT, "smoke", CHECKS)
        if passed != len(CHECKS):
            print(f"  the red, on their own: {REPORT_FILE}\n")
    except Exception:
        pass
    return 0 if passed == len(CHECKS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
