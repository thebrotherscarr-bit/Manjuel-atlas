"""Ollama transport. The only module that knows the model backend exists."""

from __future__ import annotations

import json
import os
import time

import ollama

# How long Ollama holds a model in VRAM after a request. This is a PER-REQUEST
# parameter, so chainkit sets it directly -- unlike OLLAMA_NUM_PARALLEL and
# OLLAMA_MAX_LOADED_MODELS, which the server reads at ITS startup and which no
# client can change from here.
KEEP_ALIVE = os.environ.get("CHAINKIT_KEEP_ALIVE", "30m")

# LAW 7: bounded everything. Skills have had a bound since sitting 68 (300s,
# skills.py) and SEATS HAD NONE: ollama-python's default timeout is None, so
# a seat call waited forever. Sitting 92, 2026-09-07: Jesster on deepseek-r1
# ran 760s in the court and then llama-server answered 500; the court sat
# 12 1/2 minutes for a fool who was never going to speak. The ceiling is the
# operator's number, and a dial, not a constant. 900 was given at 08:00 on
# 2026-09-08; corrected the same morning in his words: "150 for steward,
# 300 for the router, 600 max for the whole system. there should never be
# more than 10 minutes between a response, thats absurd." Then, the same
# afternoon, BY MODEL SIZE: "for the steward-sized models we are running
# the 150-300 then the router-sized gets up to 600 and the max size is at
# 700 for the biggest ones." The seats' own numbers are `Timeout:` in
# agents/*.md (llama3.2 150, phi4-mini 300, qwen3.5:4b 300, the 7-9b
# seats 600, gemma4:12b 700); this is the most any seat may take. The
# TURN is still bounded at 600 (pipeline.TURN_DEADLINE): a 700 seat late
# in a turn is cut to what is left.
try:
    SEAT_TIMEOUT = float(os.environ.get("CHAINKIT_SEAT_TIMEOUT") or 700)
except ValueError:
    SEAT_TIMEOUT = 700.0

# httpx is what ollama-python speaks through; its timeout exceptions are the
# non-streaming half of the bound. Absent (a stubbed transport) the name
# check below still catches them.
try:
    import httpx as _httpx
    _TIMEOUT_ERRORS: tuple = (_httpx.TimeoutException,)
except Exception:          # pragma: no cover -- no httpx, no transport
    _httpx = None
    _TIMEOUT_ERRORS = ()

from .registry import Agent


class RuntimeError_(Exception):
    """Base for runtime problems that should be reported, not crash the REPL."""


class BackendUnreachable(RuntimeError_):
    pass


class ModelMissing(RuntimeError_):
    pass


class SeatTimeout(RuntimeError_):
    """A seat call ran past SEAT_TIMEOUT. The skill timeout's twin.

    Raised as a RuntimeError_ so the pipeline's existing handling applies
    unchanged: on-fail: skip goes on without the seat, on-fail: prompt asks,
    and the record carries the named refusal either way.
    """


def _client_timeout(seconds: float):
    """The transport-level bound: `seconds` to read, 10 to connect.

    A single float would make CONNECT wait the full ceiling too, and
    health() against a black-holed host would hang fifteen minutes before
    saying "cannot reach Ollama". Connection refused is instant either way;
    this is for the host that answers nothing.
    """
    if _httpx is None:
        return seconds
    return _httpx.Timeout(seconds, connect=10.0)


def _seat_refusal(agent: Agent, seconds: float, elapsed: float) -> SeatTimeout:
    return SeatTimeout(
        f"[{agent.name}] seat call ran past the {seconds:.0f}s bound "
        f"({elapsed:.0f}s) and the run has stopped waiting for it "
        f"(LAW 7; sitting 92: Jesster, 760s, then a 500). Raise the bound "
        f"with CHAINKIT_SEAT_TIMEOUT if {agent.model} legitimately needs "
        f"longer, or seat a smaller model (SITTING LAW 3)."
    )


def _has_tool_calls(part) -> bool:
    """Does this streamed chunk carry a native tool call?

    Kept beside calls_to_action_xml because they must agree about where a
    call lives: the chunk this returns True for is handed to that function
    WHOLE, never merged with another.
    """
    msg = part.get("message") if isinstance(part, dict) else getattr(part, "message", None)
    if msg is None:
        return False
    calls = msg.get("tool_calls") if isinstance(msg, dict) else getattr(msg, "tool_calls", None)
    return bool(calls)


def calls_to_action_xml(resp) -> str:
    """A native `message.tool_calls` rendered as the estate's action block.

    Ollama returns tool calls as structured objects. Rather than teach the
    tool loop a second shape, they are rendered into the ONE format it
    already parses -- so extract_tool_call, the guards around it, and every
    stroke on them stay exactly as they are, and a model without the `tools`
    capability keeps working unchanged.

    DESIGN.md chose bespoke XML because the Router was coder:1.5b and JSON
    was thought harder for it. The Router is qwen3.5:4b now and `ollama show`
    lists `tools`: it was trained to emit calls natively, and was being asked
    for a format that appears nowhere in its training while the whole skills
    layer depended on its compliance.
    """
    msg = resp.get("message") if isinstance(resp, dict) else getattr(resp, "message", None)
    if msg is None:
        return ""
    calls = msg.get("tool_calls") if isinstance(msg, dict) else getattr(msg, "tool_calls", None)
    if not calls:
        return ""
    call = calls[0]                      # one hop at a time; the loop iterates
    fn = call.get("function") if isinstance(call, dict) else getattr(call, "function", None)
    if fn is None:
        return ""
    name = (fn.get("name") if isinstance(fn, dict) else getattr(fn, "name", "")) or ""
    args = (fn.get("arguments") if isinstance(fn, dict) else getattr(fn, "arguments", None)) or {}
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except Exception:
            args = {"content": args}
    if not isinstance(args, dict) or not str(name).strip():
        return ""
    xml = f"<action>{str(name).strip()}</action>"
    for key in ("filepath", "content"):
        val = args.get(key)
        if val not in (None, ""):
            xml += f"<{key}>{val}</{key}>"
    return xml


def thinking_of(resp) -> str:
    """A response's `thinking`/`reasoning` field, or "".

    Split out because the STREAMING path must keep the deliberation without
    showing it: sitting 47 stopped displaying thinking chunks and, in doing
    so, stopped keeping them at all.
    """
    msg = resp.get("message") if isinstance(resp, dict) else getattr(resp, "message", None)
    if msg is None:
        return ""
    def field(name):
        return msg.get(name) if isinstance(msg, dict) else getattr(msg, name, None)
    return str(field("thinking") or field("reasoning") or "")


# The salvage line's opening words. A CONSTANT, not a string the pipeline
# re-types: the ruling loop (pipeline.py, 2026-09-07) decides "this seat
# thought and did not rule" by this prefix, and a prefix spelled twice is a
# guard that dies on a rewording.
SALVAGE_MARK = "(deliberation only, no conclusion reached)"


def _salvage(thought: str) -> str:
    """Mark a budget that died mid-think. Never dump a full monologue.

    Session 5c: a reasoning model can spend its whole num_predict inside
    `thinking` and hand back content="", and the run delivered 56 seconds of
    silence. Thought is worse than an answer; it is far better than nothing,
    and it tells the operator WHY there is no answer.
    """
    thought = str(thought or "").strip()
    if not thought:
        return ""
    tail = " ".join(thought.split()[-120:])
    return f"{SALVAGE_MARK} {tail}"


_THINK_RE = __import__("re").compile(r"<think>.*?</think>\s*",
                                     __import__("re").DOTALL)


def _field(obj, name):
    """dict key or attribute, whichever this ollama-python version uses."""
    if isinstance(obj, dict):
        return obj.get(name)
    got = getattr(obj, name, None)
    if got is None and hasattr(obj, "get"):
        try:
            got = obj.get(name)
        except Exception:
            got = None
    return got


def _normalize(tag: str) -> str:
    tag = tag.strip()
    return tag if ":" in tag else f"{tag}:latest"


class OllamaRuntime:
    def __init__(self, host: str = "http://127.0.0.1:11434", keep_alive: str = KEEP_ALIVE):
        self.host = host
        self.keep_alive = keep_alive
        self._client = ollama.Client(host=host, timeout=_client_timeout(SEAT_TIMEOUT))
        self._installed: set[str] | None = None
        self._tool_capable: dict[str, bool] = {}
        # One transport per distinct seat bound (see _client_for). The
        # default above carries the ceiling; a seat that declares a tighter
        # `Timeout:` gets its own, made once.
        self._bounded: dict[float, object] = {}

    def _client_for(self, bound: float):
        """The transport whose READ timeout is `bound`.

        The non-streaming half of the seat bound lives in httpx, and httpx
        takes its timeout at construction, not per request -- so a seat
        with its own ceiling needs its own client. A replaced `_client`
        (the suite's fakes) is honoured as-is: a fake has no transport to
        bound, and the wall clock in the stream loop still applies.
        """
        if bound == SEAT_TIMEOUT or not isinstance(self._client, ollama.Client):
            return self._client
        if bound not in self._bounded:
            self._bounded[bound] = ollama.Client(host=self.host,
                                                 timeout=_client_timeout(bound))
        return self._bounded[bound]

    # ---- health / validation ---------------------------------------

    def health(self) -> None:
        """Raise BackendUnreachable if Ollama is not answering."""
        try:
            self._client.list()
        except Exception as exc:
            raise BackendUnreachable(
                f"Cannot reach Ollama at {self.host}.\n"
                f"  Start it with:  ollama serve\n"
                f"  Underlying error: {exc}"
            ) from exc

    def installed_models(self, refresh: bool = False) -> set[str]:
        if self._installed is None or refresh:
            try:
                data = self._client.list()
            except Exception as exc:
                raise BackendUnreachable(f"Could not list models: {exc}") from exc

            names: set[str] = set()
            for m in _field(data, "models") or []:
                # ollama-python has moved this key around between versions.
                tag = _field(m, "model") or _field(m, "name")
                if tag:
                    names.add(_normalize(tag))
            self._installed = names
        return self._installed

    def missing(self, required: set[str]) -> list[str]:
        """Return required tags that are not installed. Empty list == all good."""
        installed = self.installed_models()
        return sorted(_normalize(t) for t in required if _normalize(t) not in installed)

    # ---- warming -----------------------------------------------------

    def warm(self, model: str, num_ctx: int | None = None) -> float:
        """Load a model into VRAM now, at the context it will actually RUN at.

        Ollama treats a different num_ctx as a different runner: warming at
        ctx 256 and then chatting at 8192 loads the model TWICE, and the
        second load lands mid-question -- the exact cost warming exists to
        prepay. Pass the largest context any seat declares for this model.
        """
        started = time.time()
        try:
            self._client.chat(
                model=_normalize(model),
                messages=[{"role": "user", "content": "hi"}],
                keep_alive=self.keep_alive,
                options={"num_predict": 1, "num_ctx": int(num_ctx or 2048)},
            )
        except Exception as exc:
            raise RuntimeError_(f"could not warm {model}: {exc}") from exc
        return time.time() - started

    def unload(self, model: str) -> None:
        """Evict a model from VRAM now. keep_alive=0 tells Ollama to drop it
        as soon as this (empty) request returns."""
        try:
            self._client.chat(
                model=_normalize(model),
                messages=[],
                keep_alive=0,
            )
        except Exception as exc:
            raise RuntimeError_(f"could not unload {model}: {exc}") from exc

    def pull(self, model: str, on_progress=None) -> str:
        """Download a model. Reaches the network and can move gigabytes."""
        try:
            last = ""
            for part in self._client.pull(_normalize(model), stream=True):
                status = (part.get("status") if isinstance(part, dict)
                          else getattr(part, "status", "")) or ""
                if status and status != last:
                    last = status
                    if on_progress:
                        on_progress(status)
            return last or "done"
        except Exception as exc:
            raise RuntimeError_(f"could not pull {model}: {exc}") from exc

    def resident(self) -> list[tuple[str, int]]:
        """What Ollama currently holds in memory: (tag, bytes). Best effort.

        ollama-python answers with response OBJECTS in newer versions, dicts
        in older ones. An `isinstance(data, dict)` guard here silently turned
        the object case into [] -- so every model printed "cold" at boot even
        while it was resident, and the report was WRONG rather than degraded.
        `_field` reads either shape.
        """
        try:
            data = self._client.ps()
        except Exception:
            return []
        out = []
        for m in _field(data, "models") or []:
            tag = _field(m, "model") or _field(m, "name")
            if tag:
                out.append((tag, int(_field(m, "size") or 0)))
        return out

    # ---- generation -------------------------------------------------

    def supports_tools(self, model: str) -> bool:
        """Whether Ollama reports the `tools` capability for this model.

        Cached, and FAIL CLOSED: anything unreadable answers False, which
        keeps the seat on the XML path that works today. A wrong `True` would
        send tools= to a model that cannot take them and break the turn.
        """
        model = _normalize(model)
        if model in self._tool_capable:
            return self._tool_capable[model]
        ok = False
        try:
            info = self._client.show(model)
            caps = _field(info, "capabilities") or []
            ok = any(str(c).strip().lower() == "tools" for c in caps)
        except Exception:
            ok = False
        self._tool_capable[model] = ok
        return ok

    def _chat(self, think, client=None, **kw):
        """One call to the client, with the `think` switch when it is set.

        `client` is the bounded transport for this seat (_client_for);
        None is the default one.

        THE RULING LOOP (2026-09-07, the operator: "give him some room for
        thinking, but limit his turns"). A seat that deliberated and did not
        rule is asked again with its own deliberation in front of it -- and
        on THAT turn thinking is switched off, so the model must write the
        ruling rather than think a second time. Ollama takes `think=` per
        request on models that support it. FALLS BACK: a client too old to
        know the keyword, or a model that refuses it, gets the plain call --
        the loop still bounds the turns; it just cannot switch the thinking
        off. None means "do not pass it", which is every ordinary call."""
        client = client or self._client
        if think is None:
            return client.chat(**kw)
        try:
            return client.chat(think=think, **kw)
        except TypeError:
            return client.chat(**kw)
        except ollama.ResponseError as exc:
            if "think" in str(exc).lower():
                return client.chat(**kw)
            raise

    @staticmethod
    def _bounded_stream(parts, agent: Agent, bound: float, started: float):
        """Yield streamed parts until the seat's bound; then close and refuse.

        The streaming half of the seat bound. httpx's read timeout only
        catches a stream that has gone SILENT; a seat that keeps producing
        tokens for fifteen minutes never trips it. So the wall clock is
        checked on every part, and on breach the generator is CLOSED --
        which closes the HTTP stream, which is how Ollama learns to stop
        generating. That is a real stop, not the skill bound's "stopped
        waiting": the transport is the kill.
        """
        try:
            for part in parts:
                if time.time() - started > bound:
                    raise _seat_refusal(agent, bound, time.time() - started)
                yield part
        finally:
            close = getattr(parts, "close", None)
            if close:
                try:
                    close()
                except Exception:
                    pass

    def chat(self, agent: Agent, user_prompt: str, stream_to=None,
             tools: list | None = None, think_to=None,
             think: bool | None = None) -> str:
        """Run one agent turn.

        `think_to`, if given, is called with each thinking fragment as it
        arrives -- the same shape as `stream_to`, and deliberately NOT the
        same sink. Operator's ruling 2026-09-03, sitting 79: the Router's
        deliberation goes to THE RECORD so its chain of thought can be read
        after the fact.

        `think`, if given, is passed to Ollama as the per-request thinking
        switch (see _chat). The ruling loop sets it False on a retry; nothing
        else sets it.

        SITTING 47'S RULING IS UNCHANGED AND THIS DOES NOT TOUCH IT: thinking
        is never displayed, never returned, never fed to a later seat, never
        put in the thread or the delivery. `chat` still returns the SPOKEN
        text only. A sink is passed per call rather than stashed on `self`
        because the Reasoner runs on a background thread -- shared state here
        would interleave two seats' deliberation into one transcript.

        The persona goes in as role=system (it used to be crammed into the
        user turn, where it competed with the payload for attention).
        """
        # A BAKED seat (empty system_prompt) speaks from its compiled soul;
        # a system message here -- even an empty one -- would overwrite it.
        messages = ([{"role": "system", "content": agent.system_prompt}]
                    if agent.system_prompt else []) + [
            {"role": "user", "content": user_prompt},
        ]

        # num_ctx dominates VRAM footprint -- a 986MB model at 32k ctx was
        # measured resident at 4.2GB. Size context per stage, not globally.
        options: dict = {}
        if agent.context:
            options["num_ctx"] = agent.context
        if getattr(agent, "max_tokens", None):
            # A guard that answers in one word must not be free to write an
            # essay: session 4 spent 33s on a seat whose whole reply was "SAFE".
            options["num_predict"] = agent.max_tokens
        options = options or None

        # THE SEAT BOUND (LAW 7, 2026-09-08). The seat's own `Timeout:` if it
        # declares one, else the ceiling. Two halves: the transport's read
        # timeout (a call that answers nothing) and the wall clock on the
        # stream (a call that never stops answering). Either ends in the
        # same named refusal, and the pipeline's on-fail handling does the
        # rest -- the court goes on without the seat, and says so.
        # The pipeline hands a seat seated late in the turn a `timeout`
        # already cut to the seconds left (pipeline._within_deadline), so
        # this one line is the whole of the turn deadline's reach here.
        bound = float(getattr(agent, "timeout", None) or SEAT_TIMEOUT)
        client = self._client_for(bound)
        started = time.time()

        try:
            # A native tool call is structured and cannot stream usefully, so
            # a seat holding tools takes the single-shot path. Sitting 47's
            # live display is for prose; a call is not prose.
            if tools and stream_to is not None:
                # STREAMING WITH TOOLS (operator's ruling 2026-09-03, the
                # (a) option). The old comment here said "a native tool
                # call is structured and cannot stream usefully" -- true of
                # the CALL, and not true of the prose and the deliberation
                # the Router produces around it. The Router is the seat
                # that holds tools AND the seat that thinks, so it was the
                # one stage the operator could never watch: 74 seconds of
                # spinner on a greeting.
                #
                # NO FRAGMENT ASSEMBLY. Ollama sends a COMPLETE tool_call
                # object in one chunk (unlike the OpenAI delta shape), and
                # calls_to_action_xml only ever reads calls[0]. So the
                # first part carrying tool_calls is kept WHOLE and handed
                # to the existing renderer -- the tool loop, its guards and
                # every stroke on them see exactly the shape they always
                # have. Reconstructing calls from fragments is the (b)
                # option and is NOT done here; a mangled call would break
                # dispatch for every seat.
                #
                # FALLS BACK. If this Ollama cannot stream with tools, the
                # single-shot path below still runs. A capability that is
                # not there must not take routing down with it.
                try:
                    chunks: list[str] = []
                    call_part = None
                    for part in self._bounded_stream(self._chat(
                        think,
                        client,
                        model=agent.model,
                        messages=messages,
                        keep_alive=self.keep_alive,
                        options=options,
                        tools=tools,
                        stream=True,
                    ), agent, bound, started):
                        if call_part is None and _has_tool_calls(part):
                            call_part = part
                        piece = self._extract(part, strict=False)
                        if piece:
                            chunks.append(piece)
                            stream_to(piece)
                        t = thinking_of(part)
                        if t and think_to is not None:
                            think_to(t)
                    if call_part is not None:
                        called = calls_to_action_xml(call_part)
                        if called:
                            return called
                    return _THINK_RE.sub("", "".join(chunks)).strip()
                except TypeError:
                    pass          # this client cannot stream with tools
                except ollama.ResponseError:
                    raise         # a real model error is not a fallback case

            if tools:
                resp = self._chat(
                    think,
                    client,
                    model=agent.model,
                    messages=messages,
                    keep_alive=self.keep_alive,
                    options=options,
                    tools=tools,
                )
                # SITTING 79, MY OWN BUG, CAUGHT BY THE OPERATOR. think_to
                # was added to the streaming and non-streaming paths and NOT
                # to this one -- and this is the path the ROUTER takes, the
                # only seat that thinks and the one whose deliberation was
                # the whole point. The capture ran and recorded nothing,
                # which is worse than not building it: a `<details>` block
                # that never appears reads as "the seat did not think".
                if think_to is not None:
                    t = thinking_of(resp)
                    if t:
                        think_to(t)
                called = calls_to_action_xml(resp)
                if called:
                    if stream_to:
                        stream_to(called)
                    return called
                return self._extract(resp)

            if stream_to is None:
                resp = self._chat(
                    think,
                    client,
                    model=agent.model,
                    messages=messages,
                    keep_alive=self.keep_alive,
                    options=options,
                )
                # The non-streaming path has the deliberation in one field
                # rather than in fragments. Same sink, so a caller does not
                # have to know which path it got.
                if think_to is not None:
                    t = thinking_of(resp)
                    if t:
                        think_to(t)
                return self._extract(resp)

            chunks: list[str] = []
            thoughts: list[str] = []
            for part in self._bounded_stream(self._chat(
                think,
                client,
                model=agent.model,
                messages=messages,
                keep_alive=self.keep_alive,
                options=options,
                stream=True,
            ), agent, bound, started):
                piece = self._extract(part, strict=False)
                if piece:
                    chunks.append(piece)
                    stream_to(piece)
                # KEPT, never shown. Sitting 47 stopped displaying thinking
                # chunks, correctly -- but dropping them also threw away the
                # only copy, which deleted session 5c's fallback on the ONLY
                # path the REPL uses. 2026-09-01: the Router spent 11s and 5s
                # thinking inside a 400-token cap, returned content="", and
                # the run recorded an empty reply while the closer went on to
                # narrate a poem that was never written. The suite never saw
                # it because the suite does not stream.
                t = thinking_of(part)
                if t:
                    thoughts.append(t)
                    # To the RECORD, not to the room (sitting 79).
                    if think_to is not None:
                        think_to(t)
            # the stream shown live may include thinking; the RETURNED text
            # (what the record and later seats consume) is cleaned whole
            spoken = _THINK_RE.sub("", "".join(chunks)).strip()
            if not spoken:
                # Same rule as the non-streaming path: thought is worse than an
                # answer and infinitely better than silence.
                spoken = _salvage("".join(thoughts))
            return spoken

        except SeatTimeout:
            raise
        except ollama.ResponseError as exc:
            text = str(exc)
            if "not found" in text.lower():
                raise ModelMissing(
                    f"Model '{agent.model}' (agent: {agent.name}) is not installed.\n"
                    f"  Fix with:  ollama pull {agent.model}"
                ) from exc
            raise RuntimeError_(f"[{agent.name}] backend error: {text}") from exc
        except Exception as exc:
            # The transport's half of the bound: httpx's ReadTimeout (a seat
            # that answered nothing for `bound` seconds), named by class or,
            # under a transport that is not httpx, by name.
            if (isinstance(exc, _TIMEOUT_ERRORS)
                    or "timeout" in type(exc).__name__.lower()):
                raise _seat_refusal(agent, bound, time.time() - started) from exc
            raise RuntimeError_(f"[{agent.name}] {type(exc).__name__}: {exc}") from exc

    # ---- embeddings --------------------------------------------------

    def embed(self, model: str, text: str) -> list[float]:
        """One embedding vector. Embedders have no generative head, so this
        does not go through chat() and takes a raw model tag, not an Agent."""
        model = _normalize(model)
        try:
            # ollama-python renamed embeddings() -> embed() and changed the
            # response shape; support both rather than pinning a version.
            if hasattr(self._client, "embed"):
                resp = self._client.embed(model=model, input=text)
                data = resp.get("embeddings") if isinstance(resp, dict) else getattr(resp, "embeddings", None)
                if data:
                    return list(data[0])
            resp = self._client.embeddings(model=model, prompt=text)
            vec = resp.get("embedding") if isinstance(resp, dict) else getattr(resp, "embedding", None)
            if not vec:
                raise RuntimeError_(f"embedding response had no vector: {resp!r}")
            return list(vec)
        except ollama.ResponseError as exc:
            if "not found" in str(exc).lower():
                raise ModelMissing(
                    f"Embedding model '{model}' is not installed.\n"
                    f"  Fix with:  ollama pull {model}"
                ) from exc
            raise RuntimeError_(f"embedding error: {exc}") from exc
        except RuntimeError_:
            raise
        except Exception as exc:
            raise RuntimeError_(f"embedding {type(exc).__name__}: {exc}") from exc

    @staticmethod
    def _extract(resp, strict: bool = True) -> str:
        """Pull message content out of a response across ollama-python versions.

        `strict=False` is a STREAMING CHUNK and returns content only. Use
        `thinking_of()` alongside it to keep the deliberation, which the
        stream must not display but must not lose either -- see chat().
        """
        msg = None
        if isinstance(resp, dict):
            msg = resp.get("message")
        else:
            msg = getattr(resp, "message", None)

        if msg is None:
            if strict:
                raise RuntimeError_(f"Malformed response from Ollama: {resp!r}")
            return ""

        def field(name):
            return msg.get(name) if isinstance(msg, dict) else getattr(msg, name, None)

        content = field("content")
        if not strict:
            # STREAMING CHUNK: pass content through RAW, nothing else --
            # no strip (sitting 47a: ate the joining spaces), no fallback
            # marking (47b: stamped every thinking fragment), no think-strip.
            # A thinking model's streamed deliberation has empty content per
            # chunk, so returning content-only also keeps thinking OFF the
            # live display entirely. All cleverness happens ONCE, on the
            # joined whole, in chat().
            return str(content or "")
        if content and strict:
            # A thinking model must never publish its deliberation: strip any
            # <think> blocks that landed in content. FULL responses only --
            # sitting 47: applying this (with its strip) to STREAMING CHUNKS
            # deleted the joining spaces and every streamed reply came out
            # as wordsoup. Chunks pass through untouched; the joined stream
            # is cleaned once, below in chat().
            content = _THINK_RE.sub("", str(content)).strip()
        # A reasoning model can spend its entire num_predict budget in the
        # `thinking` field and hand back content="". Session 5c delivered 56
        # seconds of silence that way. Thought is worse than an answer, but it
        # is infinitely better than nothing, so fall back to it.
        if strict and not (content or "").strip():
            salvaged = _salvage(field("thinking") or field("reasoning") or "")
            if salvaged:
                return salvaged
        if content is None:
            if strict:
                raise RuntimeError_(f"Response had no content: {resp!r}")
            return ""
        return content
