"""Git state, read-only.

This module NEVER writes to the repository. It does not commit, push, stage,
checkout, or tag. LAW 6 is explicit: "no commit, no push ... within the walls,
the court may rule; across the wall, only he lands." So manjuel reads the
repository's state, stamps it into the record, and hands the operator the exact
command when one is wanted. Running it is his act, not the system's.

Every subprocess call here is a plumbing read (`rev-parse`, `status
--porcelain`, `log -1`), bounded by a timeout, and safe on a directory that is
not a repository at all.
"""

from __future__ import annotations

import re
import subprocess
import time
from dataclasses import dataclass, asdict
from pathlib import Path

TIMEOUT = 5

# EVERY git CALL CLOSES ITS OWN STDIN. Found 2026-09-09 by driving the
# headless door through a commit/push cycle: every git call returned
# "git rev-parse timed out", and git_commit/git_push/git_init refused
# with "this ground is not a git repository" on a ground that plainly
# was one.
#
# subprocess.run() with no `stdin` hands the child the PARENT's stdin.
# In the REPL that is a console and harmless. In `manjuel.py --headless`
# it is the pipe that serve.Inbox has a thread permanently blocked
# reading -- two readers on one pipe, and git never returns. Measured:
# 0.12s with no such thread, 5.02s (the timeout) with one; DEVNULL puts
# it back to 0.02s for reads and writes alike.
#
# No git command here ever reads stdin, so closing it costs nothing and
# is the whole fix. It is not an optimisation: without it the door
# cannot report git state, commit, or push at all.
DEVNULL = subprocess.DEVNULL


@dataclass
class GitState:
    is_repo: bool = False
    head: str = ""
    short: str = ""
    branch: str = ""
    dirty: bool = False
    changed: int = 0
    untracked: int = 0
    subject: str = ""
    error: str = ""

    def stamp(self) -> str:
        """One line for a record header."""
        if self.error:
            return f"git: unavailable ({self.error})"
        if not self.is_repo:
            return "git: not a repository"
        bits = [f"{self.branch or 'DETACHED'}@{self.short}"]
        if self.dirty:
            bits.append(f"DIRTY ({self.changed} changed, {self.untracked} untracked)")
        else:
            bits.append("clean")
        return "git: " + "  ".join(bits)

    def as_dict(self) -> dict:
        return asdict(self)


def _run(args: list[str], cwd: Path) -> tuple[int, str]:
    try:
        p = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            stdin=DEVNULL,          # see DEVNULL, above -- load-bearing
        )
        return p.returncode, (p.stdout or "").strip()
    except FileNotFoundError:
        raise RuntimeError("git is not installed or not on PATH")
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"git {args[0]} timed out")


def read(ground: Path) -> GitState:
    ground = Path(ground)
    try:
        rc, out = _run(["rev-parse", "--is-inside-work-tree"], ground)
    except RuntimeError as exc:
        return GitState(error=str(exc))

    if rc != 0 or out != "true":
        return GitState(is_repo=False)

    st = GitState(is_repo=True)
    try:
        # `git rev-parse HEAD` on a repo with no commits exits 128 but still
        # prints "HEAD" to stdout. Ignoring rc reported a commit named HEAD.
        rc, head = _run(["rev-parse", "HEAD"], ground)
        st.head = head if rc == 0 else ""
        st.short = st.head[:9]
        rc, br = _run(["rev-parse", "--abbrev-ref", "HEAD"], ground)
        st.branch = "" if br == "HEAD" else br

        _, porcelain = _run(["status", "--porcelain"], ground)
        lines = [l for l in porcelain.splitlines() if l.strip()]
        st.untracked = sum(1 for l in lines if l.startswith("??"))
        st.changed = len(lines) - st.untracked
        st.dirty = bool(lines)

        rc, subj = _run(["log", "-1", "--pretty=%s"], ground)
        st.subject = subj if rc == 0 else ""
    except RuntimeError as exc:
        st.error = str(exc)

    # An empty repo has no HEAD yet; that is not an error worth shouting about.
    if not st.head:
        st.short = "(no commits)"
        st.branch = st.branch or "main"
    return st


def suggest_commit(ground: Path, message: str) -> str:
    """The command the OPERATOR may choose to run. Never executed here."""
    safe = message.replace('"', "'").strip() or "manjuel: sitting"
    return f'git -C "{Path(ground)}" add -A && git -C "{Path(ground)}" commit -m "{safe}"'


# =====================================================================
# Write operations
# =====================================================================
#
# LOCAL writes (init, add, commit) are allowed: they are additive, confined to
# this ground, and recoverable -- git keeps what it is given. That is local
# versioning, and it is what the operator asked for.
#
# REMOTE writes (push) and remote reads (pull) cross the wall to somewhere the
# operator does not control, and a push cannot be taken back once someone has
# fetched it. Those are OFF unless MANJUEL_GIT_REMOTE=1 is set in the
# environment, so a model cannot reach a remote by deciding to.
# =====================================================================

import os

REMOTE_ENV = "MANJUEL_GIT_REMOTE"


def remote_allowed() -> bool:
    return os.environ.get(REMOTE_ENV, "").strip() in ("1", "true", "yes", "on")


class GitRefused(Exception):
    pass


def _write(args: list[str], ground: Path) -> tuple[int, str, str]:
    try:
        p = subprocess.run(
            ["git", *args], cwd=str(ground), capture_output=True, text=True,
            timeout=60, stdin=DEVNULL,      # see DEVNULL, above -- load-bearing
        )
        return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()
    except FileNotFoundError:
        raise GitRefused("git is not installed or not on PATH")
    except subprocess.TimeoutExpired:
        raise GitRefused(f"git {args[0]} timed out")


def init(ground: Path) -> str:
    ground = Path(ground)
    if read(ground).is_repo:
        return "Already a repository."
    rc, out, err = _write(["init"], ground)
    if rc != 0:
        raise GitRefused(err or "git init failed")
    return out or "Initialised an empty repository."


# A lock older than this with no git process behind it is stale rather than
# contended. Git itself never cleans these up; an interrupted `add` or `init`
# leaves one behind and every later write dies on it.
STALE_LOCK_SECONDS = 120


_PORCELAIN_RE = re.compile(r"^\S{1,2}\s+(?P<path>.+)$")


def areas(ground: Path, limit: int = 4) -> list[str]:
    """Top-level paths git says changed, for a subject built on fact.

    A commit whose subject is a placeholder tells a reader nothing. This is
    not a guess at intent -- it is what actually moved, straight from git.
    """
    rc, porcelain = _run(["status", "--porcelain"], ground)
    if rc != 0:
        return []
    # Parse by SHAPE, not by column. `_run` strips its output, so only the
    # first porcelain line loses its leading status space -- a fixed line[3:]
    # silently ate one character of exactly one filename ("EAT_LOG.md").
    seen: list[str] = []
    for line in porcelain.splitlines():
        m = _PORCELAIN_RE.match(line.strip())
        if not m:
            continue
        path = m.group("path").strip().strip('"')
        if " -> " in path:                     # a rename: take the destination
            path = path.split(" -> ", 1)[1]
        if not path:
            continue
        top = path.split("/", 1)[0] + ("/" if "/" in path else "")
        if top not in seen:
            seen.append(top)
    return seen[:limit]


def lock_state(ground: Path) -> str:
    """Describe a blocking index.lock, or "" if the ground is writable.

    Session 6 lost four runs to a 0-byte lock left by an interrupted git init.
    The raw stderr went up to a 3b model, which invented `git pull` as the
    cure -- a fabricated remedy for a problem whose real fix is one rm. Naming
    it precisely leaves no room to invent.
    """
    lock = Path(ground) / ".git" / "index.lock"
    try:
        age = time.time() - lock.stat().st_mtime
    except FileNotFoundError:
        return ""
    except OSError:
        return ""

    win = "\\".join(str(lock).split("/"))
    verdict = "stale" if age > STALE_LOCK_SECONDS else "recent"
    extra = ("" if verdict == "stale" else
             " If another git process is genuinely running, wait for it instead.")
    return (
        f"git is locked: {lock} exists ({age/60:.0f} min old, {verdict}).\n"
        f"No commit, add or checkout can run until it is gone.\n"
        f"This is NOT fixed by pull, push, fetch or a fresh init -- those are "
        f"blocked by the same lock. The operator removes it by hand:\n"
        f"  del {win}\n"
        f"A seat will not delete anything inside .git.{extra}"
    )


def commit(ground: Path, message: str, add_all: bool = True) -> str:
    ground = Path(ground)
    st = read(ground)
    if not st.is_repo:
        raise GitRefused("this ground is not a git repository (git_init first)")
    if not st.dirty:
        return "Nothing to commit; the ground is clean."

    blocked = lock_state(ground)
    if blocked:
        raise GitRefused(blocked)

    # Normalise the SUBJECT only. Flattening the whole message collapsed the
    # trailers onto the subject line -- session 6's record reads
    # "git_commit sitting: S2026..." as a single run-on line.
    raw = (message or "").strip()
    if not raw:
        raise GitRefused("a commit needs a message")
    head, _, body = raw.partition("\n")
    subject = " ".join(head.split()).strip()
    if not subject:
        raise GitRefused("a commit needs a message")
    msg = subject if not body.strip() else f"{subject}\n{body.rstrip()}"

    if add_all:
        rc, _, err = _write(["add", "-A"], ground)
        if rc != 0:
            raise GitRefused(err or "git add failed")

    rc, out, err = _write(["commit", "-m", msg], ground)
    if rc != 0:
        raise GitRefused(err or out or "git commit failed")

    after = read(ground)
    return f"Committed {after.short} on {after.branch or 'DETACHED'}: {msg}"


def pull(ground: Path) -> str:
    if not remote_allowed():
        raise GitRefused(
            f"remote operations are off. A pull rewrites this ground from "
            f"somewhere the operator does not control, so it is not something "
            f"a seat may start. Set {REMOTE_ENV}=1 to allow it."
        )
    ground = Path(ground)
    if not read(ground).is_repo:
        raise GitRefused("this ground is not a git repository")
    rc, out, err = _write(["pull", "--ff-only"], ground)
    if rc != 0:
        raise GitRefused(err or out or "git pull failed")
    return out or "Up to date."


def head_and_remote(ground: Path) -> tuple[str, str, str]:
    """(local head, remote head, why the remote could not be read).

    A push exiting 0 is not proof the remote moved. On 2026-09-10 a turn
    named `git_push`, ran `git_status` instead, and reported success while
    `origin/main` sat a commit behind -- so what a push SAYS is checked
    against what the remote HAS. Reads only; never fetches, because a fetch
    inside a report is a network act nobody asked for.
    """
    ground = Path(ground)
    rc, local = _run(["rev-parse", "HEAD"], ground)
    if rc != 0:
        return "", "", "no local head"
    rc, remote = _run(["rev-parse", "@{u}"], ground)
    if rc != 0:
        return local[:9], "", "no upstream is tracked"
    return local[:9], remote[:9], ""


def push(ground: Path) -> str:
    if not remote_allowed():
        raise GitRefused(
            f"remote operations are off. A push leaves this machine and cannot "
            f"be recalled once fetched, so it is the operator's act. Set "
            f"{REMOTE_ENV}=1 to allow it."
        )
    ground = Path(ground)
    if not read(ground).is_repo:
        raise GitRefused("this ground is not a git repository")
    rc, out, err = _write(["push"], ground)
    if rc != 0:
        raise GitRefused(err or out or "git push failed")
    return out or err or "Pushed."
