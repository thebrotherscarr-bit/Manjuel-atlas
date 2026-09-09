"""The headless door: the REPL's turn over stdin/stdout as JSON lines.

    python manjuel.py --headless
    python -m manjuel.serve

THE OPERATOR, 2026-09-08 (SPEC_CONTROL_CENTER.md P0-1): "im ok with that,
build it now and get it out of the way." A front end cannot press keys in a
REPL. This is the one extra way in: instructions arrive as JSON lines on
stdin, what happens goes out as JSON lines on stdout, humans get stderr.
NO SOCKET, no daemon, no API -- BUILDPATH's position is kept. The engine is
untouched: run_pipeline, the gates, the record and the toll are exactly the
REPL's, reached through cli.py's own functions, so a transcript written
through this door is the transcript the REPL would have written.

HOW THE REPL'S KEYBOARD AND SCREEN ARE REPLACED, without editing them:

  the screen   sys.stdout is swapped for a channel that turns every write
               into a `text` event. ink.enabled() reads isatty() off it,
               finds False, and switches colour and the spinner off -- the
               same plain text the suites see. Nothing in cli.py or
               pipeline.py stops calling print(); it just lands here.

  the keyboard builtins.input is swapped for a question over the wire: a
               `needs_answer` event with the prompt, then a wait for the
               client's `answer`. Every input() in cli.py (the toll's three
               questions, the memory kind, the confirms) and the one in
               pipeline.py (`retry / skip / abort?` for a seat marked
               On Fail: prompt) reaches the client this way. A `cancel`
               while a question is pending raises KeyboardInterrupt at the
               input() call, which is what Ctrl-C does there; a `close`
               raises EOFError, which is what Ctrl-D does.

  Ctrl-C       a `cancel` while a run is in flight raises KeyboardInterrupt
               in the main thread (_thread.interrupt_main), which the turn
               catches as "Run cancelled" -- the REPL's own path, and the
               transport is closed the way runtime._bounded_stream closes
               it.

THE STRUCTURED EVENTS ride beside the text. Two eyes, neither inside the
engine: the runtime is wrapped so a seat sitting is a `seat` event and its
streamed pieces are `token` events (control markup hidden between `<` and
`>`, the sink's own one-character rule); the skill library's execute() is
wrapped so a call is a `tool` event and its return a `tool_result`. The
run's `report` lines are `report` events. The turn ends in exactly one of
`delivery` / `refused` / `aborted` / `cancelled` / `unreachable` / `error`,
carrying the record's own notes and per-seat facts (elapsed, tools, error,
skipped) -- read off the StepResults, never off a seat's words (LAW 5).

THE WIRE (protocol 1). One JSON object per line, UTF-8.

  in   {"cmd":"objective","text":"...","feed":"...?","method":"...?"}
       {"cmd":"answer","text":"..."}      the reply to a needs_answer
       {"cmd":"listen","seconds":N?}      capture one spoken turn; the
                                          text comes back as `heard` and
                                          is NOT run -- the hand sends it
       {"cmd":"cancel"}                   the run, or the pending question
       {"cmd":"close"}                    close the sitting (the toll is paid
                                          unattended if runs happened, as
                                          on exit)
  out  opened · text · run · report · seat · token · tool · tool_result ·
       needs_answer · heard · delivery · refused · aborted · cancelled ·
       unreachable · error · note · command · closed

EVERY TURN ENDS IN EXACTLY ONE TERMINAL EVENT: delivery for a pipeline
run, command for a `/command` or any other turn that finished without
running one, or refused / aborted / cancelled / unreachable. A client
pumps until one arrives, so a turn that ended silently hung the wire
forever -- which is what every command did until this was added.

An `objective` is anything the REPL would take at its prompt: a plain
turn, a `/command`, `@seat words`, "pay the toll", "remember that". One
turn at a time, in order; an objective sent mid-run waits its turn. The
gate is still final: nothing here lands memory, pays an attended toll or
commits without an `answer` from the client's hand (RULE 6 / LAW 6).

WHAT IT IS NOT. Not a second executor, not a second engine, not
multi-session: one process, one ground, one sitting, one writer -- the
same shape as the REPL it stands beside. Environments (grounds under
agent_workspace/) are THE LINE's to open, one door each (SPEC_CONTROL_CENTER
§4.2). Voice: ONE HALF crosses the wire, and one does not. `listen` (below)
captures a single spoken turn through voice.py -- the same compiled
whisper.cpp, the same vocabulary bias, the same call the REPL's /chat
makes -- because the engine runs on the operator's own machine and the
microphone is right there. What does NOT cross is /chat's interactive
loop: it reads the keyboard to cut off an answer mid-sentence, and a
keypress has no meaning down a pipe. A captured turn is returned, never
run: the hand sends it, or edits it first (RULE 6).
"""

from __future__ import annotations

import builtins
import json
import os
import queue
import sys
import threading
import time
import _thread
from pathlib import Path

PROTOCOL = 1

# The wire's vocabulary, spelled once so a stroke can hold the door to it.
COMMANDS = ("objective", "answer", "listen", "cancel", "close")
EVENTS = ("opened", "text", "run", "report", "seat", "token", "tool",
          "tool_result", "needs_answer", "delivery", "refused", "aborted",
          "cancelled", "unreachable", "error", "note", "heard", "command",
          "closed")

# THE EVENTS THAT END A TURN. A client pumps until one of these arrives, so
# a turn that ends without one hangs it for the life of the process -- which
# is exactly what every `/command` did until 2026-09-09. `error` is NOT here:
# the inbox emits it non-terminally for a malformed command and the turn
# carries on.
TERMINAL = ("delivery", "refused", "aborted", "cancelled", "unreachable",
            "command")

# The first characters of a tool result that mean it failed -- the
# pipeline's own test (pipeline.py, the tool loop), repeated here so the
# event says what the record will say.
_FAILED_HEADS = ("Error", "Refused", "Cannot")
_RESULT_HEAD_CHARS = 400


# ---------------------------------------------------------------------
# the wire
# ---------------------------------------------------------------------


class Wire:
    """JSON lines out, one per event, under a lock: the watcher, the
    background warm and a spinner (off, but still) share the process."""

    def __init__(self, out):
        self._out = out
        self._lock = threading.Lock()
        self.sent: int = 0
        # Whether a terminal event has gone out since the turn began. The
        # serve loop clears it at the start of a turn and closes any turn
        # that ended without one. Kept HERE rather than at each early
        # return in turn(): enumerating those fixes the four that exist and
        # misses the fifth someone adds.
        self.ended: bool = False

    def emit(self, event: str, **fields) -> None:
        if event in TERMINAL:
            self.ended = True
        row = {"event": event}
        row.update(fields)
        line = json.dumps(row, ensure_ascii=False, default=str) + "\n"
        with self._lock:
            try:
                self._out.write(line)
                self._out.flush()
            except Exception:
                pass                        # a closed pipe ends the door, below
            self.sent += 1


class TextChannel:
    """Stands where sys.stdout stood. Every write is a `text` event; there
    is no terminal, so isatty() is False and ink stays plain."""

    encoding = "utf-8"
    errors = "replace"

    def __init__(self, wire: Wire):
        self._wire = wire

    def write(self, s) -> int:
        s = str(s or "")
        if s:
            self._wire.emit("text", text=s)
        return len(s)

    def flush(self) -> None:
        return None

    def isatty(self) -> bool:
        return False

    def fileno(self):
        raise OSError("the headless door has no terminal")

    def writelines(self, lines) -> None:
        for l in lines:
            self.write(l)


class Inbox:
    """The client's lines, read on a thread so a `cancel` can reach a run
    that is busy in a model call. Malformed lines are answered with an
    `error` event and dropped -- never guessed at."""

    IDLE, RUNNING, ASKING = "idle", "running", "asking"

    def __init__(self, source, wire: Wire):
        self._source = source
        self._wire = wire
        self._q: "queue.Queue[dict | None]" = queue.Queue()
        self._state = self.IDLE
        self._lock = threading.Lock()
        self.closed = False
        self._thread = threading.Thread(target=self._pump, daemon=True,
                                        name="headless-inbox")

    def start(self) -> None:
        self._thread.start()

    def set_state(self, state: str) -> None:
        with self._lock:
            self._state = state

    def _pump(self) -> None:
        try:
            for raw in self._source:
                line = (raw or "").strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except ValueError:
                    self._wire.emit("error", text=f"not JSON: {line[:120]!r}")
                    continue
                if not isinstance(row, dict) or not isinstance(row.get("cmd"), str):
                    self._wire.emit("error", text=f"not a command: {line[:120]!r}")
                    continue
                cmd = row["cmd"].strip().lower()
                if cmd not in COMMANDS:
                    self._wire.emit("error",
                                    text=f"unknown cmd {cmd!r}; the wire takes "
                                         f"{', '.join(COMMANDS)}")
                    continue
                row["cmd"] = cmd
                with self._lock:
                    state = self._state
                if cmd == "cancel" and state == self.RUNNING:
                    # Ctrl-C, delivered to the thread that is in the model
                    # call. The turn's own except: KeyboardInterrupt does
                    # the rest, and the transport is closed on the way out.
                    _thread.interrupt_main()
                    continue
                self._q.put(row)
        except Exception as exc:                # the pipe died under us
            self._wire.emit("error", text=f"inbox: {type(exc).__name__}: {exc}")
        finally:
            self.closed = True
            self._q.put(None)                  # EOF: the client hung up

    def take(self, timeout: float | None = None) -> dict | None:
        """The next command, or None at EOF."""
        try:
            return self._q.get(timeout=timeout)
        except queue.Empty:
            return {"cmd": "_timeout"}

    def put_back(self, row: dict) -> None:
        self._q.put(row)


# ---------------------------------------------------------------------
# the eyes: seat / token and tool / tool_result, without touching the engine
# ---------------------------------------------------------------------


class _Runtime:
    """The runtime as it is, plus a `seat` event when a seat sits and
    `token` events as it speaks. Delegates everything else, so the Stub the
    suites use and the real OllamaRuntime both fit behind it."""

    def __init__(self, inner, wire: Wire):
        self._inner = inner
        self._wire = wire

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def chat(self, agent, user_prompt, stream_to=None, tools=None,
             think_to=None, think=None):
        self._wire.emit("seat", seat=agent.name, model=agent.model,
                        timeout=getattr(agent, "timeout", None),
                        streaming=stream_to is not None)
        sink = self._token_sink(agent.name) if stream_to is not None else None
        return self._inner.chat(agent, user_prompt, stream_to=sink, tools=tools,
                                think_to=think_to, think=think)

    def _token_sink(self, seat: str):
        # SITTING 70's rule, kept: control markup is the seat's channel to
        # the ENGINE and never reaches a person live. A tag can be split
        # across pieces, so this is the sink's one-character state machine:
        # from `<` to `>` nothing is shown.
        inside = [False]

        def sink(piece):
            shown = []
            for ch in str(piece or ""):
                if inside[0]:
                    if ch == ">":
                        inside[0] = False
                    continue
                if ch == "<":
                    inside[0] = True
                    continue
                shown.append(ch)
            text = "".join(shown)
            if text:
                self._wire.emit("token", seat=seat, text=text)
        return sink


def _watch_skills(skills, wire: Wire) -> None:
    """Wrap execute() on THIS library instance for THIS wire. /reload
    builds a new library, so the turn re-checks before every run."""
    if skills is None or getattr(skills, "_headless_wire", None) is wire:
        return
    # Wrap the library's OWN execute, never a previous wrap: one library
    # can outlive a wire (the suites drive several doors over one).
    inner = getattr(skills, "_headless_inner", None) or skills.execute

    def execute(action, args, env):
        wire.emit("tool", action=action,
                  args={k: str(v)[:200] for k, v in (args or {}).items()})
        result = inner(action, args, env)
        text = str(result or "")
        wire.emit("tool_result", action=action,
                  failed=text.lstrip().startswith(_FAILED_HEADS),
                  chars=len(text), head=text[:_RESULT_HEAD_CHARS])
        return result

    skills.execute = execute
    skills._headless_inner = inner
    skills._headless_wire = wire


# ---------------------------------------------------------------------
# the door
# ---------------------------------------------------------------------


class Door:
    """One sitting, over one wire. `sess` is cli.Session or anything that
    stands where it stands (the suites hand in a stand-in)."""

    def __init__(self, sess, wire: Wire, inbox: Inbox, ground: Path | None = None,
                 closer=None):
        from . import cli as _cli
        self.sess = sess
        self.wire = wire
        self.inbox = inbox
        self.ground = Path(ground) if ground else _cli.ROOT
        # What closes the sitting: cli._close (the toll, the ledger line,
        # "bye"). The suites hand in a stand-in so no stroke pays a toll
        # into the record it runs beside.
        self.closer = closer if closer is not None else _cli._close
        self.asked = 0
        self._deferred: list[dict] = []
        if not isinstance(getattr(sess, "runtime", None), _Runtime):
            sess.runtime = _Runtime(sess.runtime, wire)

    # ---- the keyboard --------------------------------------------------

    def ask(self, prompt: str = "") -> str:
        """Stands where input() stood. One question, one answer, over the
        wire; a cancel here is Ctrl-C and a close is Ctrl-D, which is what
        every input() site in cli.py and pipeline.py already handles."""
        self.asked += 1
        self.inbox.set_state(Inbox.ASKING)
        self.wire.emit("needs_answer", id=self.asked, prompt=str(prompt or ""))
        try:
            while True:
                row = self.inbox.take()
                if row is None:
                    raise EOFError("the client hung up")
                cmd = row.get("cmd")
                if cmd == "answer":
                    return str(row.get("text") or "")
                if cmd == "cancel":
                    raise KeyboardInterrupt
                if cmd == "close":
                    self._deferred.append(row)
                    raise EOFError("closed while a question was pending")
                if cmd == "objective":
                    # Not an answer. Kept for after the question, in order.
                    self._deferred.append(row)
                    self.wire.emit("note",
                                   text="a question is pending (needs_answer); "
                                        "the objective waits until it is answered")
                    continue
        finally:
            self.inbox.set_state(Inbox.RUNNING)

    def _listen(self, row: dict) -> None:
        """One spoken turn, captured and transcribed, and NOT run.

        voice.listen() is the REPL's own call: it calibrates against the
        room, ends the turn when the operator goes quiet, transcribes on
        the compiled whisper.cpp and applies correct_hearing() so the
        estate's proper nouns survive. Nothing is reimplemented here; if
        the REPL can hear, so can the glass, and neither can drift.

        The text comes back as `heard` and stops there. A microphone that
        fired objectives at the council on its own would be a gate nobody
        holds, and a misheard word would run before he had read it.

        Every failure is voice.py's own sentence on an `error` event,
        which is NOT terminal on this wire: a bad capture ends the
        capture, never the sitting.
        """
        from . import voice
        seconds = voice.MAX_TURN_SECONDS
        try:
            asked = int(row.get("seconds") or 0)
            if asked > 0:
                seconds = min(asked, voice.MAX_TURN_SECONDS)
        except (TypeError, ValueError):
            pass
        try:
            said = voice.listen(
                seconds,
                report=lambda m: self.wire.emit("note", text=str(m).strip()))
        except voice.VoiceError as exc:
            self.wire.emit("error", text=str(exc))
            return
        except Exception as exc:                      # a dead device, a bad driver
            self.wire.emit("error", text=f"the microphone failed: {exc}")
            return
        self.wire.emit("heard", text=said)

    def _next(self) -> dict | None:
        if self._deferred:
            return self._deferred.pop(0)
        return self.inbox.take()

    # ---- the loop ------------------------------------------------------

    def serve(self) -> int:
        """cli._loop's shape: take a turn, run it, until close or EOF."""
        from . import cli as _cli
        real_input = builtins.input
        builtins.input = self.ask
        try:
            while True:
                self.inbox.set_state(Inbox.IDLE)
                row = self._next()
                if row is None:
                    self._close("the client hung up")
                    return 0
                cmd = row.get("cmd")
                if cmd == "close":
                    self._close("closed by the client")
                    return 0
                if cmd == "listen":
                    self._listen(row)
                    continue
                if cmd == "cancel":
                    self.wire.emit("note", text="nothing is running; nothing to cancel")
                    continue
                if cmd == "answer":
                    self.wire.emit("note", text="no question is pending; the answer was dropped")
                    continue
                if cmd != "objective":
                    continue
                objective = str(row.get("text") or "").strip()
                feed = str(row.get("feed") or "")
                method = str(row.get("method") or "")
                if feed.strip():
                    self.sess.pending_feed = feed.strip()      # /paste's shape
                if method.strip():
                    self.sess.pending_method = method.strip()  # a command's method
                self.inbox.set_state(Inbox.RUNNING)
                self.wire.ended = False
                try:
                    if not self.turn(objective):
                        return 0
                    # A turn that ran no pipeline -- a /command, @seat, the
                    # toll, a remember cue, an empty line -- printed its
                    # words and returned. Nothing told the client it was
                    # over, and a client pumps until something does.
                    if not self.wire.ended:
                        self.wire.emit("command", text=objective)
                except KeyboardInterrupt:
                    # A cancel that landed after the model call returned --
                    # in the tail of the turn, or at a command. The turn is
                    # over either way; the sitting is not.
                    print("\n\nRun cancelled.\n")
                    self.wire.emit("cancelled", notes=[], seats=[])
        finally:
            builtins.input = real_input

    def _close(self, why: str) -> None:
        st = self.sess.sitting
        try:
            self.closer(self.sess)
        except Exception as exc:
            self.wire.emit("error", text=f"close: {type(exc).__name__}: {exc}")
        self.wire.emit("closed", why=why, sitting=getattr(st, "n", None),
                       runs=len(getattr(st, "runs", []) or []),
                       toll_paid=bool(getattr(st, "toll_paid", False)))

    # ---- one turn ------------------------------------------------------

    def turn(self, objective: str) -> bool:
        """One typed turn, cli._loop's body line for line (the REPL read of
        2026-09-08 is the reference; a divergence here is a bug here).
        Returns False when the turn closed the sitting."""
        from . import cli as _cli
        from . import transcript, spelling, voice
        from . import seatlog as _log
        from .context import RunContext
        from .drift import DriftChecker
        from .intent import wants_out
        from .pipeline import Aborted, Refused, run_pipeline
        from .runtime import BackendUnreachable, RuntimeError_
        from .skills import EMBED_MODEL

        sess = self.sess
        print(_cli.BAR)
        if not objective:
            return True
        print(f"Objective: {objective}")
        if objective.lower() in ("exit", "quit") or wants_out(objective):
            print(f"\n  Alright — closing the sitting. (the record keeps)\n")
            self._close("the objective asked out")
            return False

        _cli._apply_ground_changes(sess)
        _watch_skills(sess.skills, self.wire)

        if _cli._topic_turn(sess, objective):
            return True

        low = objective.lower().strip()
        if "pay the toll" in low or low.rstrip(".!?") == "the toll":
            _cli._cmd_toll(sess, attended=True)
            return True
        cued, words = _cli.remember_cue(objective)
        if cued:
            _cli._cmd_remember_that(sess, words)
            return True

        if objective.startswith("@"):
            if _cli._address_seat(sess, objective):
                return True
        try:
            if _cli.handle_command(objective, sess):
                _watch_skills(sess.skills, self.wire)      # /reload rebuilt it
                return True
        except SystemExit:
            self._close("/exit")
            return False

        if not sess.rack_ok and not sess.rack_check():
            print("\n  The rack is still unreachable — `ollama serve`, then "
                  "just ask again.\n")
            self.wire.emit("unreachable", text="the rack is unreachable; no run")
            return True

        ctx = RunContext(objective=objective, feed=sess.pending_feed,
                         dialogue=_cli._dialogue_for(sess, objective),
                         method=sess.pending_method,
                         review_only=sess.pipeline_name in ("court", "estate"),
                         standing=getattr(sess, "standing", ""),
                         story=_log.story_block(sess.sitting))
        sess.pending_feed = ""
        sess.pending_method = ""
        sess.last_run_ref = f"logs/{transcript.name_for(ctx)}"
        print("\nRunning pipeline...")
        self.wire.emit("run", objective=objective, pipeline=sess.pipeline_name,
                       transcript=sess.last_run_ref, feed_chars=len(ctx.feed),
                       review_only=ctx.review_only)

        def report(line):
            print(line)
            self.wire.emit("report", text=str(line))

        try:
            run_pipeline(
                ctx,
                sess.registry,
                sess.runtime,
                sess.skills,
                sess.env,
                steps=sess.pipeline,
                report=report,
                stream=True,
                drift=DriftChecker(sess.runtime, EMBED_MODEL),
            )
        except Refused as exc:
            print(f"\n  REFUSED: {exc}")
            print("  The run did not proceed. Nothing downstream saw this input.\n")
            self.wire.emit("refused", text=str(exc), notes=list(ctx.notes))
            return True
        except Aborted as exc:
            print(f"\nRun aborted: {exc}\n")
            self.wire.emit("aborted", text=str(exc), notes=list(ctx.notes))
            return True
        except KeyboardInterrupt:
            print("\n\nRun cancelled.\n")
            self.wire.emit("cancelled", notes=list(ctx.notes),
                           seats=[s.agent for s in ctx.steps])
            return True
        except BackendUnreachable as exc:
            print(f"\n{exc}\n")
            self.wire.emit("unreachable", text=str(exc))
            return True
        except RuntimeError_ as exc:
            print(f"\nRuntime error: {exc}\n")
            self.wire.emit("error", text=str(exc), notes=list(ctx.notes))
            return True

        sess.last = ctx
        _final = ctx.last_output().strip()
        if _final:
            sess.dialogue.append(("operator", ctx.objective, time.time()))
            sess.dialogue.append(("steward", _final, time.time()))
            _cli.save_thread(self.ground, sess.session, sess.dialogue)

        name = sess.pipeline_name
        logged = ""
        try:
            record, _ = transcript.write(ctx, self.ground / "logs", pipeline=name)
            logged = f"logs/{record.name}"
            where = f"  logged: {logged}"
            sess.sitting.runs.append(vars(_log.note_for(ctx, name, logged)))
        except Exception as exc:
            where = f"  (transcript not written: {exc})"

        print(f"\n--- delivery · {ctx.elapsed:.1f}s ---\n")
        body = ctx.last_output().strip()
        if body:
            result = spelling.check(body)
            if result.changed:
                body = result.text
                ctx.notes.append(result.note())
        if not body:
            print("  (no seat produced an answer this run)")
            for n in ctx.notes:
                print(f"  - {n}")
        else:
            print(body)
        print()
        print(where)
        print()

        self.wire.emit(
            "delivery", text=body, elapsed=round(ctx.elapsed, 1), transcript=logged,
            pipeline=name, flags=sorted(ctx.flags), notes=list(ctx.notes),
            failures=[list(f) for f in ctx.failures],
            out_of_time=list(ctx.out_of_time),
            steps=[{"seat": s.agent, "model": s.model, "elapsed": round(s.elapsed, 1),
                    "tools": list(s.tool_calls or []), "error": s.error or "",
                    "skipped": bool(s.skipped), "chars": len(s.output or ""),
                    "drift": s.drift, "drifted": bool(s.drifted)}
                   for s in ctx.steps])

        if sess.speaking and body:
            try:
                voice.speak(body, blocking=False, voice=_cli._voice_for(sess, ctx))
            except voice.VoiceError as exc:
                print(f"  (not spoken: {exc})")
                print()
        return True


# ---------------------------------------------------------------------
# main: cli.main's boot, then the door
# ---------------------------------------------------------------------


def open_wire(out=None, source=None) -> tuple[Wire, Inbox]:
    """The real stdout and stdin as the wire. stdout is swapped for the
    text channel HERE, before anything can ask ink whether it is a
    terminal."""
    real = out if out is not None else sys.stdout
    try:
        real.reconfigure(encoding="utf-8", errors="replace")   # type: ignore[attr-defined]
    except Exception:
        pass
    src = source if source is not None else sys.stdin
    try:
        src.reconfigure(encoding="utf-8", errors="replace")    # type: ignore[attr-defined]
    except Exception:
        pass
    wire = Wire(real)
    sys.stdout = TextChannel(wire)
    inbox = Inbox(src, wire)
    return wire, inbox


def main(argv: list[str] | None = None) -> int:
    from . import cli as _cli
    from . import boot, dotenv, gitstate, ink
    from . import seatlog as _log
    from . import watch as _watch
    from .skills import EMBED_MODEL

    wire, inbox = open_wire()
    inbox.start()

    # THE GROUND, first (cli.main's shape): `--ground <path>` sits the door
    # inside a world; a bad path is refused on the wire, never created.
    try:
        ground = _cli.ground_from_argv(sys.argv[1:] if argv is None else argv)
    except ValueError as exc:
        wire.emit("error", text=f"{_cli.GROUND_FLAG} refused: {exc}")
        wire.emit("closed", why="ground refused", sitting=None, runs=0,
                  toll_paid=False)
        return 1
    if ground is not None:
        _cli.set_ground(ground)
    ROOT = _cli.ROOT

    # cli.main, line for line, with the prints landing on the wire as text.
    print("\nChain -- local multi-agent pipeline (headless door)")
    if ground is not None:
        print(f"  ground: {ROOT}")
    for line in dotenv.report(*dotenv.load(ROOT / ".env")):
        print(line)

    sess = _cli.Session()
    door = Door(sess, wire, inbox, ground=ROOT)
    if not sess.load():
        wire.emit("error", text="the declarations did not load; see the text above")
        wire.emit("closed", why="declarations did not load", sitting=None,
                  runs=0, toll_paid=False)
        return 1
    if not sess.rack_check():
        print("\n  RACK UNREACHABLE — the ground is open, the models are not.")
        print("  Start `ollama serve` whenever; the chain reconnects on the "
              "next turn.\n")
    elif not sess.preflight():
        wire.emit("error", text="preflight failed; see the text above")
        wire.emit("closed", why="preflight failed", sitting=None, runs=0,
                  toll_paid=False)
        return 1

    _log.record(ROOT, sess.sitting)
    g0 = gitstate.read(ROOT)
    print(f"  sitting {sess.sitting.n} · session {sess.session} · {g0.stamp()}")
    print()

    if os.environ.get("MANJUEL_NO_WARM", "").strip() not in ("1", "true", "yes"):
        if sess.rack_ok:
            _cli._cmd_warm(sess, quiet=True)
            sess._bg_warm = _cli._warm_reasoner_later(sess)
        sess.watcher = _watch.GroundWatch(ROOT)
        if sess.watcher.start():
            print(ink.dim("  watching the ground — edits reload and reindex "
                          "themselves between turns"))
        else:
            sess.watcher = None

    for line in boot.report(sess, ROOT, EMBED_MODEL, git=g0):
        print(line)
    print()
    try:
        for line in boot.brief_facts(sess, ROOT, git=g0):
            print(line)
        print("  /brief has the door say it\n")
    except Exception as exc:
        print(ink.dim(f"  (the brief could not be read: {exc})\n"))
    origin, prior = _cli.load_thread(ROOT)
    if prior:
        print(f"  a thread from {origin} is on file "
              f"({len(prior) // 2} turns) — /resume picks it up")

    wire.emit("opened", protocol=PROTOCOL, sitting=sess.sitting.n,
              session=sess.session, git=g0.stamp(), rack_ok=bool(sess.rack_ok),
              pipeline=sess.pipeline_name, pipelines=sess.pipeline_names(),
              seats=[a.name for a in sess.registry.all()],
              commands=list(COMMANDS), events=list(EVENTS))

    try:
        return door.serve()
    except Exception as exc:
        # cli.main's shape: close the sitting so the ledger does not hold
        # it open, THEN show the fault whole.
        print(f"\n  !! unhandled: {type(exc).__name__}: {exc}")
        print("  closing the sitting so the ledger does not hold it open.")
        wire.emit("error", text=f"unhandled: {type(exc).__name__}: {exc}")
        try:
            door._close("unhandled fault")
        finally:
            raise


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
