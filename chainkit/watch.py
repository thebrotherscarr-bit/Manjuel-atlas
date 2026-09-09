"""The ground watches itself.

Sitting 41: the operator installed watchdog. Before this, an edit to a seat,
a skill, or a document sat invisible until a manual /reload or /index -- the
chain's knowledge of its own ground went stale the moment the operator
touched a file. Now the ground reports its own changes, and the CLI applies
them at TURN BOUNDARIES: never mid-answer, always audibly.

watchdog is OPTIONAL. Absent, everything here degrades to no-ops and the
CLI behaves exactly as before -- a missing convenience is never a refusal.

Two kinds of change matter, and they are handled differently:

  DECLARATIONS  agents/*.md, skills/*.md, pipelines.md, commands.md,
                providers of behavior -> queue a reload.
  MATERIAL      indexable files under the ground -> queue an incremental
                re-embed, so semantic_search stops lying about fresh edits.

Secrets are refused by name here too -- a .env touched is a .env IGNORED.
"""

from __future__ import annotations

import importlib.util
import threading
from pathlib import Path

from .vectors import TEXT_SUFFIXES, is_protected, is_secret

_DECLARATION_DIRS = {"agents", "skills"}
_DECLARATION_FILES = {"pipelines.md", "commands.md", "agents.md"}
_IGNORE_PARTS = {".git", "__pycache__", "index", "_prompts", "bin",
                 ".venv", "node_modules",
                 # THE CHAIN'S OWN WRITES (the REPL read, 2026-09-08). The
                 # ledger and the thread are written at every open, turn,
                 # toll and close; with `sessions` watched, every turn
                 # queued thread.jsonl and the NEXT turn re-embedded the
                 # whole rolling conversation ("reindexed on change:
                 # thread.jsonl", every turn). logs/ was already excused
                 # for the same reason; sessions/ is the same hand.
                 "sessions"}
# Files the chain writes into the ground's root and tests/, for the same
# reason: touched by the record, not by the operator's hand.
_SELF_WRITTEN = {"SEAT_LOG.md", "memory.md", "rack.md",
                 "last_run.json", "last_run.md", "run_history.jsonl",
                 "parity_history.jsonl", "last_audit.md"}


def available() -> bool:
    try:
        return importlib.util.find_spec("watchdog") is not None
    except (ImportError, ValueError):
        return False


class GroundWatch:
    """Collects change events; the CLI drains them between turns.

    The handler logic is plain methods so the suite can drive it without a
    real observer thread; the observer is only wired when watchdog exists.
    """

    def __init__(self, ground: Path):
        self.ground = Path(ground).resolve()
        self._lock = threading.Lock()
        self._reload_needed = False
        self._changed: set[Path] = set()
        self._observer = None

    # ---- classification (pure; unit-tested directly) -----------------

    def note(self, path) -> None:
        """One changed path, classified. Called by the observer thread."""
        try:
            p = Path(path).resolve()
        except OSError:
            return
        if self.ground not in p.parents:
            return                        # outside the ground: not ours
        rel = p.relative_to(self.ground)
        if any(part in _IGNORE_PARTS for part in rel.parts):
            return
        if rel.name in _SELF_WRITTEN:
            return                        # the record's own hand
        if is_secret(p.name) or is_protected(p):
            return          # secrets and client data: touched is ignored
        with self._lock:
            if (rel.parts and rel.parts[0] in _DECLARATION_DIRS
                    and p.suffix == ".md") or rel.name in _DECLARATION_FILES:
                self._reload_needed = True
            if p.suffix.lower() in TEXT_SUFFIXES and rel.parts[0] != "logs":
                # logs are indexed too, but they change every turn by our own
                # hand -- indexing them stays with /index, not the watcher.
                self._changed.add(p)

    # ---- draining (called by the CLI at turn boundaries) -------------

    def drain(self) -> tuple[bool, list[Path]]:
        """(reload_needed, changed_files) -- and the slate is wiped."""
        with self._lock:
            reload_needed = self._reload_needed
            changed = sorted(self._changed)
            self._reload_needed = False
            self._changed.clear()
        return reload_needed, changed

    # ---- the real observer (only when watchdog exists) ----------------

    def start(self) -> bool:
        if not available():
            return False
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer

        watch = self

        class H(FileSystemEventHandler):
            def on_modified(self, event):
                if not event.is_directory:
                    watch.note(event.src_path)

            def on_created(self, event):
                if not event.is_directory:
                    watch.note(event.src_path)

            def on_moved(self, event):
                if not event.is_directory:
                    watch.note(event.dest_path)

        self._observer = Observer(timeout=2)
        self._observer.schedule(H(), str(self.ground), recursive=True)
        self._observer.daemon = True
        self._observer.start()
        return True

    def stop(self) -> None:
        if self._observer is not None:
            try:
                self._observer.stop()
            except Exception:
                pass
            self._observer = None
