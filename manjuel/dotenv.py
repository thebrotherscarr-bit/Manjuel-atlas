"""A `.env` beside the work, honored and never printed.

LAW 9: "Keys are silent. A `.env` beside the work is honored, never printed,
copied, or committed." So this reads the file, sets what is missing, and
reports only KEY NAMES -- never a value, not even in an error.

What a .env here CAN change
---------------------------
Anything manjuel itself reads, because manjuel reads it at ITS startup:

    MANJUEL_KEEP_ALIVE=30m      how long Ollama holds a model (per-request)
    MANJUEL_NO_WARM=1           skip warming models on launch
    MANJUEL_GIT_REMOTE=1        allow git pull/push
    MANJUEL_OLLAMA_HOST=...     where Ollama lives

What it CANNOT change
---------------------
`OLLAMA_NUM_PARALLEL` and `OLLAMA_MAX_LOADED_MODELS` are read by the `ollama
serve` PROCESS when IT starts. Setting them here puts them in manjuel's
environment, which the already-running server never reads. Writing them in a
.env and believing they took effect is worse than not setting them, so if they
appear here manjuel says plainly that they were ignored and where they belong.

An existing environment variable always wins: the shell you launched from is a
more deliberate act than a file you wrote once.
"""

from __future__ import annotations

import os
from pathlib import Path

# Set by the ollama server at its own startup. We can read these to compare
# intent against reality, but setting them from here does nothing.
SERVER_ONLY = {
    "OLLAMA_NUM_PARALLEL",
    "OLLAMA_MAX_LOADED_MODELS",
    "OLLAMA_KEEP_ALIVE",
    "OLLAMA_HOST",
    "OLLAMA_MODELS",
    "OLLAMA_FLASH_ATTENTION",
}


def _unquote(v: str) -> str:
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    return v


def load(path: Path) -> tuple[list[str], list[str], list[str]]:
    """Read `path` into the environment.

    Returns (applied, already_set, server_only) as lists of KEY NAMES only.
    No value is returned, logged, or raised.
    """
    applied: list[str] = []
    already: list[str] = []
    server: list[str] = []

    path = Path(path)
    if not path.exists():
        return applied, already, server

    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return applied, already, server

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.lower().startswith("export "):
            line = line[7:].lstrip()

        key, _, value = line.partition("=")
        key = key.strip()
        if not key:
            continue

        if key in SERVER_ONLY:
            # Honest about the limit rather than silently doing nothing.
            server.append(key)
            continue
        if key in os.environ:
            already.append(key)
            continue

        os.environ[key] = _unquote(value)
        applied.append(key)

    return applied, already, server


def report(applied: list[str], already: list[str], server: list[str]) -> list[str]:
    """Lines to print. Key names only -- never a value (LAW 9)."""
    out: list[str] = []
    if applied:
        out.append(f"  .env: set {', '.join(sorted(applied))}")
    if already:
        out.append(f"  .env: {', '.join(sorted(already))} already in the "
                   f"environment, left alone")
    if server:
        out.append(f"  .env: {', '.join(sorted(server))} IGNORED — the ollama "
                   f"server reads those at its own startup,")
        out.append( "        so setting them here does nothing. Set them where "
                    "Ollama launches, then restart it.")
    return out
