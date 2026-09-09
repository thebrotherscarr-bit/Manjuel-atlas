"""Voice: the chain speaks its delivery, and can be spoken to.

Everything here is OPTIONAL and detected at runtime. The CLI must start and
run normally on a machine with none of it installed -- a missing microphone
library is not a reason to refuse a typed question. Each capability reports
what it needs rather than failing silently.

Speaking out uses whatever the operating system already has: SAPI on Windows
(built in, no install, no VRAM), `say` on macOS, `espeak`/`spd-say` on Linux.
Listening in needs faster-whisper and sounddevice, which are real installs and
so are reported as absent until they are there.

SECURITY: text spoken aloud is usually MODEL OUTPUT, which is testimony and
never trusted (LAW 5). It is handed to the speech engine through a file whose
path travels in an environment variable -- never interpolated into a shell
command, where a seat could close the quoting and append a command of its own.
"""

from __future__ import annotations

import importlib.util
import os
import re
import shutil
import subprocess
import sys
import time
import tempfile
from dataclasses import dataclass
from pathlib import Path

# A delivery can be thousands of words. Reading all of it aloud is not useful
# and cannot be interrupted cleanly, so speech is capped and says it was.
MAX_SPOKEN_CHARS = 1200
SAMPLE_RATE = 16000

# Voice-activity detection: the recorder runs until the SPEAKER stops, not for
# a fixed window. A fixed 8s cut the operator off mid-sentence and padded
# short turns with dead air -- both wrong.
BLOCK_SECONDS = 0.03            # one RMS measurement per 30ms block
CALIBRATE_SECONDS = 0.3         # ambient noise floor, sampled up front
WAIT_FOR_SPEECH_SECONDS = 10    # give up if nothing is said at all
TRAILING_SILENCE_SECONDS = 1.5  # this much quiet after speech ends the turn
MAX_TURN_SECONDS = 120          # hard cap so a left-open mic cannot run forever
MIN_SPEECH_BLOCKS = 5           # <150ms of sound is a click, not a sentence

# Whisper's smallest useful model. Runs on CPU in about a second for a short
# utterance, so it does not compete for a card another client is already on.
#
# NEVER DOWNLOADED. Both whispers fetch from HuggingFace on first use unless
# told not to, and a silent network call in the voice path breaks the one rule
# this estate is built on. The model is found on disk or the chain says so and
# stops -- it does not quietly go and get one.
STT_MODEL = os.environ.get("CHAINKIT_WHISPER_MODEL", "").strip() or "base.en"
STT_DIR_ENV = "CHAINKIT_WHISPER_DIR"

# The estate's proper nouns, and what whisper turns them into. Sitting 25:
# "Steward" arrived as "Stuart" and a seat invented his death; "git" arrived
# as "get"; "toll" as "tall" and "total". Two defences, both deterministic:
# the vocabulary is fed to whisper as a decoding bias, and known confusions
# are corrected by word-boundary replacement after transcription. Only exact
# known mishearings are touched -- this must never "fix" real words.
HEARING: dict[str, str] = {
    "stuart": "steward", "stewart": "steward",
    "manuel": "manjuel", "manwell": "manjuel",
    "jester": "jesster",
    "nero": "neiro", "niro": "neiro",
    "get status": "git status", "get commit": "git commit",
    "get push": "git push", "get pull": "git pull", "get init": "git init",
    "the tall": "the toll", "the total": "the toll",
    "pay the total": "pay the toll", "pay the tall": "pay the toll",
    "chain kit": "chainkit",
    "v ram": "vram", "the ram": "vram",
    "o llama": "ollama", "oh llama": "ollama",
}

VOCAB_BIAS = ("This is the chainkit estate: Steward, Manjuel, Jesster, Neiro, "
              "the Router, the Security Guardian, the Expert Coder. Commands: "
              "git status, git commit, the toll, the rack, vram, ollama, "
              "semantic search, index the ground.")


def correct_hearing(text: str) -> str:
    """Fix KNOWN mishearings of estate terms, word-boundary only."""
    out = text or ""
    for wrong, right in HEARING.items():
        out = re.sub(rf"(?i)(?<![a-z]){re.escape(wrong)}(?![a-z])", right, out)
    return out


# whisper.cpp: a compiled binary and a ggml weights file. Preferred over both
# Python whispers because it is the only one that cannot reach for a network
# even by accident -- no torch, no HuggingFace hub, no cache that fills itself.
CPP_BIN_ENV = "CHAINKIT_WHISPER_CLI"     # path to whisper-cli(.exe)
CPP_MODEL_ENV = "CHAINKIT_WHISPER_GGML"  # path to ggml-*.bin


# INSIDE THE GROUND ONLY. An earlier version globbed `../*/` and found the
# operator's Archive build, which made the CLI depend on a folder outside
# Research at runtime. Everything this program needs lives in Research.
_CPP_GLOBS = (
    "bin/whisper-cli*",
    "bin/main.exe",
    "bin/*/whisper-cli*",
)


def _find_cpp_binary(ground: Path) -> str:
    ground = ground.resolve()
    for pattern in _CPP_GLOBS:
        for hit in sorted(ground.glob(pattern)):
            if hit.is_file() and ground in hit.resolve().parents:
                return str(hit.resolve())
    return ""


def _cpp_parts() -> tuple[str, str]:
    """(binary, ggml model) if whisper.cpp is usable here, else ("", "").

    Discovered, not configured. The build and the weights are already on this
    machine; making the operator paste two absolute paths into a dotfile to
    use his own files is the tool failing to do its job.
    """
    ground = Path(__file__).resolve().parent.parent
    exe = (os.environ.get(CPP_BIN_ENV) or "").strip() or _find_cpp_binary(ground)
    if not exe or not Path(exe).is_file():
        return "", ""

    model = (os.environ.get(CPP_MODEL_ENV) or "").strip()
    if model and Path(model).is_file():
        return exe, model
    # Sitting beside the binary, or in a models/ dir near it.
    # The weights live near the binary: beside it, or in the models/ dir of the
    # checkout it was built in. Walk up from bin/ until the repo root shows up.
    root = Path(exe).resolve().parent
    tag = STT_MODEL.replace(".en", "")
    candidates = [root, root / "models"]
    # Prefer the requested size, then base, then whatever is there -- a bigger
    # model is slower per turn but never wrong to fall back to.
    for pat in (f"ggml-{STT_MODEL}.bin", f"ggml-{tag}.en.bin",
                "ggml-base.en.bin", "ggml-*.bin"):
        for d in candidates:
            if not d.is_dir():
                continue
            hit = sorted(d.glob(pat))
            if hit:
                return exe, str(hit[0])
    return "", ""

# Where a locally-downloaded whisper usually lives. Checked in order.
def _cache_dirs() -> list[Path]:
    home = Path.home()
    named = (os.environ.get(STT_DIR_ENV) or "").strip()
    out = [Path(named)] if named else []
    out += [
        home / ".cache" / "whisper",                    # openai-whisper
        home / ".cache" / "huggingface" / "hub",        # faster-whisper
        Path(os.environ.get("HF_HOME", "")) / "hub" if os.environ.get("HF_HOME") else home / ".nonexistent",
        Path(os.environ.get("LOCALAPPDATA", "")) / "whisper" if os.environ.get("LOCALAPPDATA") else home / ".nonexistent",
    ]
    return [d for d in out if d and d.is_dir()]


def local_model() -> tuple[str, str]:
    """(what to load, where it came from) -- or ("", why not).

    A bare tag like `base.en` is only returned once a matching file has been
    SEEN on disk, so loading it cannot turn into a download.
    """
    if Path(STT_MODEL).exists():
        return STT_MODEL, f"explicit path {STT_MODEL}"

    tag = STT_MODEL
    for d in _cache_dirs():
        # openai-whisper keeps <name>.pt
        pt = d / f"{tag}.pt"
        if pt.is_file():
            return str(pt), f"{d}"
        # faster-whisper / HF keep a model directory
        for cand in list(d.glob(f"*faster-whisper-{tag}*")) + list(d.glob(f"*whisper-{tag}*")):
            if cand.is_dir() and any(cand.rglob("model.bin")):
                snap = next((x.parent for x in cand.rglob("model.bin")), cand)
                return str(snap), f"{d}"
    searched = ", ".join(str(d) for d in _cache_dirs()) or "no cache dirs found"
    return "", (f"no local '{tag}' found (looked in: {searched}). "
                f"Set {STT_DIR_ENV} to the folder holding it, or "
                f"CHAINKIT_WHISPER_MODEL to the model path itself.")


class VoiceError(Exception):
    pass


@dataclass(frozen=True)
class Capability:
    ok: bool
    how: str          # what will be used, or what is missing
    install: str = ""  # what to run, when it is missing

    def __str__(self) -> str:
        return self.how if self.ok else f"{self.how}  ({self.install})"


# ---------------------------------------------------------------------
# speaking out
# ---------------------------------------------------------------------


def _speech_backend() -> tuple[str, str]:
    if sys.platform == "win32":
        exe = shutil.which("powershell") or shutil.which("pwsh")
        return ("sapi", exe) if exe else ("", "")
    if sys.platform == "darwin":
        exe = shutil.which("say")
        return ("say", exe) if exe else ("", "")
    for name in ("spd-say", "espeak-ng", "espeak"):
        exe = shutil.which(name)
        if exe:
            return (name, exe)
    return ("", "")


def can_speak() -> Capability:
    kind, exe = _speech_backend()
    if kind == "sapi":
        return Capability(True, "Windows SAPI (built in, no VRAM)")
    if kind:
        return Capability(True, f"{kind}")
    if sys.platform.startswith("linux"):
        return Capability(False, "no speech engine", "apt install espeak-ng")
    return Capability(False, "no speech engine found", "")


_FENCE = re.compile(r"```.*?```", re.DOTALL)
_INLINE = re.compile(r"`([^`]*)`")
_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_MARKUP = re.compile(r"^[ \t]*[#>*\-]+[ \t]*", re.MULTILINE)
# Only asterisk emphasis. Stripping `_` mangled every identifier it met --
# `git_commit` came out "gitcommit" -- and underscore emphasis is vanishingly
# rare in seat output next to how common snake_case is.
_EMPH = re.compile(r"\*{1,3}")
# Read an identifier the way a person says it, deliberately rather than as a
# side effect: "git commit", not "git underscore commit".
_SNAKE = re.compile(r"\b([a-z][a-z0-9]*(?:_[a-z0-9]+)+)\b")


def speakable(text: str) -> str:
    """Strip what should not be read aloud: fences, markup, urls.

    A delivery read verbatim says "hash hash hash" and recites code character
    by character. Code blocks are announced, not performed.
    """
    t = _FENCE.sub(" (code block omitted) ", text or "")
    t = _LINK.sub(r"\1", t)
    t = _INLINE.sub(r"\1", t)
    t = _MARKUP.sub("", t)
    t = _EMPH.sub("", t)
    t = _SNAKE.sub(lambda m: m.group(1).replace("_", " "), t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{2,}", "\n", t).strip()
    if len(t) > MAX_SPOKEN_CHARS:
        cut = t[:MAX_SPOKEN_CHARS]
        cut = cut[: cut.rfind(" ")] if " " in cut else cut
        t = cut + " ... the rest is on screen."
    return t


def _speech_cmd(body: str, voice: str | None = None):
    """(cmd, env, tmp_path) for reading `body` aloud on this OS.

    The voice, like the text, travels in the ENVIRONMENT -- never argv. A
    substring is matched against installed voices; no match falls back to
    the default silently, because a missing voice is a preference unmet,
    not an error."""
    kind, exe = _speech_backend()
    if not kind:
        raise VoiceError(str(can_speak()))

    if kind == "sapi":
        # The text goes through a FILE, and the path through the environment.
        # Model output must never be interpolated into a command line.
        fd, path = tempfile.mkstemp(suffix=".txt", text=True)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(body)
        script = (
            "Add-Type -AssemblyName System.Speech; "
            "$t = [IO.File]::ReadAllText($env:CHAINKIT_SPEAK_FILE, "
            "[Text.Encoding]::UTF8); "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$v = $env:CHAINKIT_SPEAK_VOICE; "
            "if ($v) { try { "
            "$m = $s.GetInstalledVoices() | Where-Object "
            "{ $_.VoiceInfo.Name -like ('*' + $v + '*') } | "
            "Select-Object -First 1; "
            "if ($m) { $s.SelectVoice($m.VoiceInfo.Name) } } catch {} } "
            "$s.Speak($t)"
        )
        env = dict(os.environ, CHAINKIT_SPEAK_FILE=path,
                   CHAINKIT_SPEAK_VOICE=(voice or ""))
        cmd = [exe, "-NoProfile", "-NonInteractive", "-Command", script]
    else:
        path = ""
        env = dict(os.environ)
        if kind == "say":
            cmd = [exe] + (["-v", voice] if voice else []) + [body]
        else:
            cmd = [exe] + (["-v", voice] if voice else []) + ["--", body]

    return cmd, env, path


def speak(text: str, blocking: bool = True, voice: str | None = None) -> str:
    """Read text aloud. Returns what was spoken, or raises VoiceError."""
    body = speakable(text)
    if not body:
        return ""
    cmd, env, path = _speech_cmd(body, voice)
    try:
        if blocking:
            subprocess.run(cmd, env=env, capture_output=True, timeout=180)
        else:
            subprocess.Popen(cmd, env=env,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as exc:
        raise VoiceError(f"speech failed: {exc}") from exc
    finally:
        if path and blocking:
            try:
                os.unlink(path)
            except OSError:
                pass
    return body


def _key_pressed() -> bool:
    """A key is waiting on stdin, without blocking. Windows first-class."""
    try:
        import msvcrt
        if msvcrt.kbhit():
            msvcrt.getch()
            return True
        return False
    except ImportError:
        pass
    try:
        import select
        r, _, _ = select.select([sys.stdin], [], [], 0)
        if r:
            # An empty read is EOF, not a keypress -- a closed stdin must not
            # cut every answer off at the first word.
            return bool(sys.stdin.readline())
        return False
    except Exception:
        return False


def speak_interruptible(text: str, report=print,
                        voice: str | None = None) -> bool:
    """Read text aloud, but the OPERATOR can cut it off with a keypress.

    The machine must never hold the floor: a long answer read in full when the
    operator has already heard enough turns a conversation into a lecture.
    Returns True if it finished, False if it was cut off. Ctrl+C also cuts the
    speech -- and only the speech; ending the whole chat stays the caller's
    decision.
    """
    body = speakable(text)
    if not body:
        return True
    cmd, env, path = _speech_cmd(body, voice)
    proc = None
    try:
        proc = subprocess.Popen(cmd, env=env,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
        while proc.poll() is None:
            if _key_pressed():
                proc.kill()
                report("  (cut off)")
                return False
            time.sleep(0.05)
        return True
    except KeyboardInterrupt:
        if proc is not None:
            proc.kill()
        report("  (cut off)")
        return False
    except Exception as exc:
        raise VoiceError(f"speech failed: {exc}") from exc
    finally:
        if proc is not None and proc.poll() is None:
            proc.kill()
        if path:
            try:
                os.unlink(path)
            except OSError:
                pass


# ---------------------------------------------------------------------
# listening in
# ---------------------------------------------------------------------


def _has(module: str) -> bool:
    """Probe WITHOUT importing: whisper pulls in torch and costs seconds."""
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


def _stt_parts() -> tuple[str, str]:
    """Which transcriber is present, and what is missing if none is.

    whisper.cpp first: a compiled binary with a ggml file on disk is the only
    option with no path to the network at all. Then faster-whisper, then the
    original -- both real paths, both pinned to local files.
    """
    if not _has("sounddevice"):
        return "", "sounddevice"
    if all(_cpp_parts()):
        return "whisper_cpp", ""
    if _has("faster_whisper"):
        return "faster_whisper", ""
    if _has("whisper"):
        return "whisper", ""
    return "", "whisper.cpp, faster-whisper or whisper"


def can_listen() -> Capability:
    kind, missing = _stt_parts()
    if not kind:
        return Capability(False, f"{missing} not installed",
                          f"pip install "
                          f"{'sounddevice' if missing == 'sounddevice' else missing}")
    if kind == "whisper_cpp":
        _exe, model = _cpp_parts()
        return Capability(True, f"whisper.cpp {Path(model).name} (compiled, offline)")
    where, why = local_model()
    if not where:
        return Capability(False, "whisper installed but no LOCAL model", why)
    engine = "faster-whisper" if kind == "faster_whisper" else "openai-whisper"
    return Capability(True, f"{engine} {STT_MODEL} (CPU, local: {why})")


_MODEL_CACHE: dict = {}


def _model(kind: str):
    if kind not in _MODEL_CACHE:
        where, why = local_model()
        if not where:
            raise VoiceError(why)
        if kind == "faster_whisper":
            from faster_whisper import WhisperModel
            # CPU/int8 deliberately: the card belongs to whatever else runs.
            # local_files_only closes the download path for good -- without it
            # a cache miss silently becomes a network fetch.
            _MODEL_CACHE[kind] = WhisperModel(where, device="cpu",
                                              compute_type="int8",
                                              local_files_only=True)
        else:
            import whisper
            _MODEL_CACHE[kind] = whisper.load_model(where)
    return _MODEL_CACHE[kind]


def _transcribe_cpp(audio) -> str:
    """Write a 16k mono WAV and hand it to whisper-cli.

    The binary takes a file, not a stream, so the clip goes through a temp WAV
    -- written with the stdlib `wave` module, no extra dependency.
    """
    import wave

    exe, model = _cpp_parts()
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        pcm = [max(-1.0, min(1.0, float(x))) for x in audio]
        with wave.open(path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SAMPLE_RATE)
            w.writeframes(b"".join(
                int(v * 32767).to_bytes(2, "little", signed=True) for v in pcm))
        cmd = [exe, "-m", model, "-f", path, "-l", "en",
               "--no-timestamps", "--no-prints",
               "--prompt", VOCAB_BIAS]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if proc.returncode != 0:
            raise VoiceError(f"whisper.cpp failed: "
                             f"{' '.join((proc.stderr or '').split())[:200]}")
        # Strip any bracketed noise annotations the model emits.
        said = re.sub(r"\[[^\]]*\]", " ", proc.stdout or "")
        return " ".join(said.split()).strip()
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def _transcribe(kind: str, audio) -> str:
    if kind == "whisper_cpp":
        return _transcribe_cpp(audio)
    model = _model(kind)
    if kind == "faster_whisper":
        segments, _info = model.transcribe(audio, language="en",
                                           vad_filter=True,
                                           initial_prompt=VOCAB_BIAS)
        return " ".join(seg.text.strip() for seg in segments).strip()
    return (model.transcribe(audio, language="en", fp16=False,
                             initial_prompt=VOCAB_BIAS)
            .get("text", "").strip())


def _rms(block) -> float:
    import numpy as np
    return float(np.sqrt(np.mean(np.square(block)))) if len(block) else 0.0


def listen(max_seconds: int = MAX_TURN_SECONDS, report=print) -> str:
    """Record until the speaker goes quiet, then transcribe.

    The turn ends when the OPERATOR stops talking: after speech is heard, a
    stretch of trailing silence closes the recording. The only fixed numbers
    are safety rails -- a wait cap when nothing is said, and a hard ceiling so
    a left-open microphone cannot record forever.

    The speech threshold is calibrated against the room: ambient noise is
    sampled for a moment first, and "speaking" means clearly above that. A
    quiet room and a noisy one therefore behave the same.
    """
    kind, _missing = _stt_parts()
    if not kind:
        raise VoiceError(str(can_listen()))

    import numpy as np
    import sounddevice as sd

    block = int(SAMPLE_RATE * BLOCK_SECONDS)
    calibrate = max(1, int(CALIBRATE_SECONDS / BLOCK_SECONDS))
    trailing = max(1, int(TRAILING_SILENCE_SECONDS / BLOCK_SECONDS))
    wait_cap = int(WAIT_FOR_SPEECH_SECONDS / BLOCK_SECONDS)
    hard_cap = int(max(5, max_seconds) / BLOCK_SECONDS)

    chunks: list = []
    noise: list[float] = []
    speaking = False
    quiet_run = 0
    speech_blocks = 0

    report("  listening — speak; the turn ends when you go quiet")
    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                            dtype="float32", blocksize=block) as stream:
            for i in range(hard_cap):
                data, _overflow = stream.read(block)
                flat = np.squeeze(data)
                level = _rms(flat)

                if i < calibrate:
                    noise.append(level)
                    continue
                floor = sorted(noise)[len(noise) // 2] if noise else 0.0
                threshold = max(floor * 3.0, 0.01)

                if not speaking:
                    if level >= threshold:
                        speaking = True
                        chunks.append(flat)
                        speech_blocks += 1
                    elif i - calibrate > wait_cap:
                        raise VoiceError(
                            "heard nothing — is the right input device selected?")
                    continue

                chunks.append(flat)
                if level >= threshold:
                    quiet_run = 0
                    speech_blocks += 1
                else:
                    quiet_run += 1
                    if quiet_run >= trailing:
                        break
    except VoiceError:
        raise
    except Exception as exc:
        raise VoiceError(f"microphone unavailable: {exc}") from exc

    if speech_blocks < MIN_SPEECH_BLOCKS:
        raise VoiceError("heard only a click — say it again?")

    audio = np.concatenate(chunks) if chunks else np.zeros(1, dtype="float32")
    seconds = len(audio) / SAMPLE_RATE
    report(f"  {seconds:.1f}s heard — transcribing…")
    try:
        said = _transcribe(kind, audio)
    except Exception as exc:
        raise VoiceError(f"transcription failed: {exc}") from exc
    return correct_hearing(said)
