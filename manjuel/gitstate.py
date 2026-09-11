"""Git, from the core's own hand.

THIS DOCSTRING WAS WRONG FOR MONTHS. It opened "Git state, read-only. This
module NEVER writes to the repository. It does not commit, push, stage,
checkout, or tag" -- while the bottom half of this same file has committed 29
times and pushed 24, by the record's own count. The Write operations section
below was added under it and the header was never revisited. A file that
denies what its own second half does is worse than an undocumented one,
because it is believed.

WHAT IS ACTUALLY TRUE, and the line LAW 6 actually draws:

    LOCAL writes are the core's        init, add, commit, branch, switch.
                                       Additive, confined to this ground,
                                       and recoverable -- git keeps what it
                                       is given.

    REMOTE acts are walled             push, pull. They cross to somewhere
                                       the operator does not control and a
                                       push cannot be recalled once fetched.
                                       OFF unless MANJUEL_GIT_REMOTE=1.

    THE GATE IS STILL HIS              nothing here fires on its own. Every
                                       call below is reached because he
                                       asked for it, in the REPL or in words.

THE CORE READS ITS OWN GROUND. Added 2026-09-10 at the operator's word: the
REPL should not have to ask atlas what is going on in its own repository.
diff, branches, switch and remotes land here so `/git` can answer without a
door, an engine or a browser standing.

Every subprocess call in this module closes its own stdin and is bounded by a
timeout, and every one is safe on a directory that is not a repository.
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


# =====================================================================
# What the core could not see about itself
# =====================================================================
#
# Until 2026-09-10 this module could say WHETHER the ground was dirty and
# nothing about WHAT changed, could name the branch it was on and offer no
# way to leave it, and could push to a remote it could not name. The door
# (atlas) grew all three the same day, which left the core asking a browser
# about its own repository. The operator: "it would make a lot more sense to
# smarten up the REPL and add in the git functionality then just relying on
# atlas to understand WTF is going on".
#
# These are the core's own. The door keeps its copy; that redundancy is
# deliberate -- the court, the acting seats and the door each reach git by
# their own path, and a layer that cannot see for itself is a layer that
# cannot check anyone else.


def _jailed(ground: Path, rel: str) -> str:
    """Refuse a path that leaves this ground. Resolve first, judge after.

    RULE 1 is about where a path LANDS, not how it is spelled, so the stated
    form is never trusted -- `a/../../b` is judged where it ends up.
    """
    if not rel:
        return ""
    if rel.startswith(("/", "\\")) or ":" in rel:
        return f"Refused: an absolute path is outside this ground ({rel})."
    home = Path(ground).resolve()
    try:
        full = (home / rel).resolve()
    except OSError:
        return f"Refused: that path could not be resolved ({rel})."
    if full != home and home not in full.parents:
        return f"Refused: that path resolves outside this ground ({rel})."
    return ""


DIFF_CAP = 60_000


def diff(ground: Path, path: str = "", cap: int = DIFF_CAP) -> str:
    """What actually changed -- one file, or the whole tree.

    UNTRACKED IS NOT A DIFF. `git diff` says nothing about a file git has
    never seen, so a reader that only ran diff would show an empty page for
    the one kind of file most likely to be lost. Those come back as their own
    first bytes, and it says so.

    BOUNDED, WITH THE BOUND NAMED. A truncated diff that does not admit it was
    truncated is a lie about the size of a change.
    """
    ground = Path(ground)
    if not read(ground).is_repo:
        return "This ground is not a git repository."

    rel = (path or "").strip()
    refusal = _jailed(ground, rel)
    if refusal:
        return refusal

    def clip(text: str, what: str) -> str:
        if len(text) <= cap:
            return text
        return (text[:cap] +
                f"\n\n... ({what} is {len(text)} bytes; this is the first {cap})")

    if not rel:
        _, staged = _run(["diff", "--cached"], ground)
        _, unstaged = _run(["diff"], ground)
        both = (staged + "\n" + unstaged).strip()
        return clip(both, "the whole diff") if both else \
            "Nothing has changed since the last commit."

    for args, what in ((["diff", "--", rel], "the change"),
                       (["diff", "--cached", "--", rel], "the staged change")):
        rc, out = _run(args, ground)
        if rc == 0 and out.strip():
            return clip(out, what)

    full = ground / rel
    if not full.exists():
        return f"No such file in this ground: {rel}"
    try:
        body = full.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"That file has no recorded change and could not be read: {exc}"
    return (f"{rel} is new -- git has never seen it, so there is nothing to "
            f"compare it against. Its contents:\n\n" + clip(body, "the file"))


def branches(ground: Path) -> list[dict]:
    """Every line of work, newest first, with where you stand marked.

    `sent` answers what a branch list is usually asked for: is this only on my
    machine? An upstream means the remote has seen it.
    """
    ground = Path(ground)
    st = read(ground)
    if not st.is_repo:
        return []
    here = st.branch
    rc, raw = _run(
        ["for-each-ref", "--sort=-committerdate",
         "--format=%(refname:short)\t%(upstream:short)\t%(committerdate:relative)"
         "\t%(contents:subject)", "refs/heads"],
        ground)
    if rc != 0:
        return []
    out: list[dict] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = (line.split("\t") + ["", "", ""])[:4]
        name, upstream, when, subject = parts
        out.append({
            "name": name,
            "current": name == here,
            "main": name in ("main", "master"),
            "upstream": upstream,
            "sent": bool(upstream),
            "when": when,
            "subject": subject,
        })
    return out


_BRANCH_BAD = (" ", "..", "~", "^", ":", "?", "*", "[", "\\", "@{")


def _bad_branch_name(name: str) -> str:
    if not name:
        return "Refused: name the line of work."
    if name.startswith("-"):
        return ("Refused: a branch name may not begin with '-' -- git reads it "
                "as a flag.")
    for bad in _BRANCH_BAD:
        if bad in name:
            return (f"Refused: {name!r} is not a lawful branch name "
                    f"({bad!r} is not allowed).")
    if name.endswith("/") or name.endswith(".lock"):
        return f"Refused: {name!r} is not a lawful branch name."
    return ""


def switch(ground: Path, name: str, create: bool = False) -> str:
    """Move to a line of work, or open one and move there.

    A DIRTY TREE DOES NOT FOLLOW YOU QUIETLY. Uncommitted work carried onto
    another branch confuses both, so this refuses and says what to do about
    it. Opening a NEW line carries the work on purpose, which is the usual
    reason to open one, so that case is allowed.
    """
    ground = Path(ground)
    if not read(ground).is_repo:
        raise GitRefused("this ground is not a git repository")
    refusal = _bad_branch_name(name)
    if refusal:
        raise GitRefused(refusal)

    blocked = lock_state(ground)
    if blocked:
        raise GitRefused(blocked)

    if not create and read(ground).dirty:
        raise GitRefused(
            "there is uncommitted work here. Commit it first, or it follows "
            "you onto the other line and confuses both.")

    args = ["switch", "-c", name] if create else ["switch", name]
    rc, out, err = _write(args, ground)
    if rc != 0:
        raise GitRefused(err or out or f"could not switch to {name}")
    if create:
        return (f"Opened {name} and moved onto it. It exists only here until "
                f"it is pushed.")
    return f"Now on {name}."


def close_branch(ground: Path, name: str) -> str:
    """Finish with a line of work.

    UNMERGED WORK IS NOT DISCARDED ON A GUESS. Plain -d refuses a branch git
    cannot see folded in; that refusal is reported, never escalated to -D.
    Throwing away the only copy of something is the operator's act.
    """
    ground = Path(ground)
    st = read(ground)
    if not st.is_repo:
        raise GitRefused("this ground is not a git repository")
    refusal = _bad_branch_name(name)
    if refusal:
        raise GitRefused(refusal)
    if name == st.branch:
        raise GitRefused("you are standing on that line. Move to another first.")

    rc, out, err = _write(["branch", "-d", name], ground)
    if rc != 0:
        both = (err or "") + (out or "")
        if "not fully merged" in both:
            raise GitRefused(
                f"{name} holds work that is on no other line. Closing it would "
                f"lose that work. Merge it first, or discard it yourself with "
                f"`git branch -D {name}` if that is what you mean.")
        raise GitRefused(both.strip() or f"could not close {name}")
    return f"Closed {name}. Its work is already on another line."


def remotes(ground: Path) -> list[dict]:
    """Where this ground sends, by name and host.

    READ-ONLY, DELIBERATELY. Adding, renaming or removing a remote points the
    repository at a different server; that is a decision, not a verb a seat
    gets.
    """
    ground = Path(ground)
    if not read(ground).is_repo:
        return []
    rc, raw = _run(["remote", "-v"], ground)
    if rc != 0:
        return []
    seen: dict[str, str] = {}
    order: list[str] = []
    for line in raw.splitlines():
        bits = line.split()
        if len(bits) < 2:
            continue
        if bits[0] not in seen:
            order.append(bits[0])
        seen[bits[0]] = bits[1]
    return [{"name": n, "url": seen[n], "host": _host_of(seen[n])} for n in order]


def _host_of(url: str) -> str:
    """The server a remote points at, for both spellings git accepts.

    LAW 9 reaches here: a remote URL can carry a token in its userinfo, so the
    userinfo is cut before anything is returned. Only the host comes out --
    never the credential half.
    """
    u = url
    if "://" in u:
        u = u.split("://", 1)[1]
    if "@" in u:
        u = u.rsplit("@", 1)[1]
    for cut in ("/", ":"):
        if cut in u:
            u = u.split(cut, 1)[0]
    return u
