"""Colour and a spinner. Degrades to plain text without complaint.

A run is watched, not just read afterwards, so the terminal is the review
surface. Two things make it legible: a stable colour per seat, so you can tell
at a glance who is speaking, and a spinner while a stage is thinking, so a
long silence reads as work rather than as a hang.

Colour is OFF when it would be wrong: not a terminal (piped, redirected, or
under the test harness), NO_COLOR set, TERM=dumb, or Windows refusing to enable
virtual terminal processing. In all those cases every function here still
returns usable plain text -- nothing downstream needs to know.
"""

from __future__ import annotations

import itertools
import os
import sys
import threading
import time

RESET = "\033[0m"
DIM = "\033[2m"
BOLD = "\033[1m"

# Mid-brightness 256-colour codes: readable on both light and dark terminals,
# and distinct enough from each other to tell apart at a glance.
PALETTE = (81, 114, 215, 141, 209, 79, 176, 180, 111, 150, 218, 117)

_STATE = {"on": None}


def _enable_windows_vt() -> bool:
    if os.name != "nt":
        return True
    try:
        import ctypes
        k = ctypes.windll.kernel32
        h = k.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if not k.GetConsoleMode(h, ctypes.byref(mode)):
            return False
        return bool(k.SetConsoleMode(h, mode.value | 0x0004))
    except Exception:
        return False


def enabled() -> bool:
    if _STATE["on"] is None:
        _STATE["on"] = (
            sys.stdout.isatty()
            and not os.environ.get("NO_COLOR")
            and os.environ.get("TERM") != "dumb"
            and os.environ.get("CHAINKIT_NO_COLOR", "").strip() not in ("1", "true", "yes")
            and _enable_windows_vt()
        )
    return _STATE["on"]


def seat_color(name: str) -> int:
    """A stable colour for a seat name. Same seat, same colour, every run."""
    return PALETTE[sum(ord(c) for c in name.strip().lower()) % len(PALETTE)]


def seat(name: str) -> str:
    if not enabled():
        return name
    return f"\033[38;5;{seat_color(name)}m{BOLD}{name}{RESET}"


def dim(text: str) -> str:
    return f"{DIM}{text}{RESET}" if enabled() else text


def warn(text: str) -> str:
    return f"\033[38;5;208m{text}{RESET}" if enabled() else text


def bad(text: str) -> str:
    return f"\033[38;5;203m{text}{RESET}" if enabled() else text


def good(text: str) -> str:
    return f"\033[38;5;114m{text}{RESET}" if enabled() else text


def body(name: str, text: str) -> str:
    """A seat's streamed output, tinted to match its name."""
    if not enabled():
        return text
    return f"\033[38;5;{seat_color(name)}m{text}{RESET}"


class Spinner:
    """Runs while a stage is thinking; erases itself on the first token.

    A no-op when colour is off, so piped output and the test harness stay
    clean -- a spinner written into a transcript would be noise.
    """

    FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def __init__(self, label: str = "thinking"):
        self.label = label
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._started = 0.0

    def start(self) -> None:
        if not enabled():
            return
        self._started = time.time()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def _spin(self) -> None:
        for frame in itertools.cycle(self.FRAMES):
            if self._stop.is_set():
                return
            secs = time.time() - self._started
            sys.stdout.write(f"\r      {DIM}{frame} {self.label} {secs:4.1f}s{RESET}")
            sys.stdout.flush()
            time.sleep(0.08)

    def stop(self) -> float:
        """Stop, erase the line, and return how long it ran."""
        elapsed = time.time() - self._started if self._started else 0.0
        if self._thread is None:
            return elapsed
        self._stop.set()
        self._thread.join(timeout=0.5)
        sys.stdout.write("\r" + " " * 40 + "\r")
        sys.stdout.flush()
        self._thread = None
        return elapsed

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *exc):
        self.stop()
        return False
