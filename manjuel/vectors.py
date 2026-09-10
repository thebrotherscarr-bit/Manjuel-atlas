"""Semantic index: chunked, incremental, passage-level retrieval.

Design notes that matter:

- CHUNKS, not documents. A whole-file vector is one average of everything the
  file says, which is why the first version needed a 4000-char cap and still
  retrieved poorly. Chunking removes the cap and returns the passage rather
  than just the filename.
- INCREMENTAL. Files are keyed by sha256; unchanged files are skipped. Without
  this, pointing at a large ground means re-embedding everything every run.
- READ-ONLY over source ground. Roots are read and never written. The index
  lives in manjuel's own ground (LAW 2: originals are read-only; packets
  prepare, the operator lands).
- BOUNDED (LAW 7). Caps on file size, file count, and chunks per file, so a
  stray root cannot run away.
- Vectors are stored L2-normalized, so cosine similarity is a plain dot
  product at query time.
- The embedder is stamped in `meta`. Vectors from two models are not
  comparable, so a model change invalidates the index and is refused rather
  than silently mixed.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import struct
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import memory as _memory
from . import transcript as _transcript

SCHEMA_VERSION = "2"

# Bounds
MAX_FILE_BYTES = 256_000
MAX_FILES = 4000
MAX_CHUNKS_PER_FILE = 200
CHUNK_CHARS = 1200
CHUNK_OVERLAP = 200

TEXT_SUFFIXES = {".md", ".txt", ".us", ".py", ".json", ".jsonl", ".csv", ".rst", ".toml", ".yaml", ".yml", ".ini", ".cfg"}
# Keys are silent (LAW 9). `.env` happens to be skipped because it has no
# suffix, but `.yaml`, `.ini` and `.cfg` ARE indexed -- so a secrets file with
# one of those names would be embedded, and an embedding cannot be unpublished.
# Refused by NAME, explicitly, rather than left to a coincidence of extensions.
SECRET_NAMES = {".env", "env", "secrets", "secret", "credentials", "creds",
                "id_rsa", "id_ed25519", ".netrc", ".npmrc", ".pypirc",
                "keyfile", "apikey", "api_key", "token", "tokens"}


LOG_HORIZON_DAYS = 45


def _too_old_to_index(path) -> bool:
    """A transcript past the horizon is history, not a retrieval candidate.

    Set MANJUEL_LOG_HORIZON_DAYS=0 to index every transcript ever written.
    Nothing is deleted either way -- `sitting` and `when` read logs/ direct,
    by number and by date, and neither goes through the index.
    """
    import os as _os
    import time as _t
    from pathlib import Path as _P
    p = _P(path)
    parts = {x.lower() for x in p.parts}
    if "logs" not in parts:
        return False                      # standing documents never age out
    try:
        days = float(_os.environ.get("MANJUEL_LOG_HORIZON_DAYS",
                                     LOG_HORIZON_DAYS))
    except ValueError:
        days = LOG_HORIZON_DAYS
    if days <= 0:
        return False
    try:
        return (_t.time() - p.stat().st_mtime) > days * 86400
    except OSError:
        return False


def is_secret(path) -> bool:
    """Whether this file must never be embedded, whatever its extension."""
    from pathlib import Path as _P
    p = _P(path)
    name = p.name.lower()
    if name in SECRET_NAMES or name.startswith(".env"):
        return True
    stem = p.stem.lower()
    return stem in SECRET_NAMES or stem.endswith("_secrets") or stem.endswith("_key")


# CLIENT DATA — the operator's ruling, sitting 45: highest priority, never
# indexed, never used, never cross-referenced. Three tags, ANY one protects:
# a `vault` directory anywhere in the path; `.client.` anywhere in the name;
# a [[CLIENT]] token in the first bytes of the file. Refusal is HARD at
# every surface -- index, watcher, reads, listings, search -- so protected
# content can never reach a model, a transcript, the dialogue, or a recall.
CLIENT_TOKEN = "[[CLIENT]]"


def is_protected(path, peek: bool = True) -> bool:
    """Client-bearing by tag. Location, name, or content token."""
    from pathlib import Path as _P
    p = _P(path)
    if any(part.lower() == "vault" for part in p.parts):
        return True
    if ".client." in p.name.lower():
        return True
    if peek and p.is_file():
        try:
            with p.open("rb") as fh:
                head = fh.read(2048)
            if CLIENT_TOKEN.encode() in head:
                return True
        except OSError:
            pass
    return False


SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "blobs",
             "target", "dist", "build", ".mypy_cache", ".pytest_cache",
             # full prompts repeat the objective and feed once per stage;
             # indexing them floods retrieval with near-duplicate passages.
             "_prompts"}

try:                        # optional: exact same results, ~100x faster
    import numpy as _np
except Exception:
    _np = None


class IndexError_(Exception):
    pass


# THE LINE BETWEEN THE TWO CORPORA, in one place so nothing can draw it twice.
# logs/ is the transcripts; everything else is a source. index_roots.txt
# already draws this boundary in prose -- "what the chain IS", "what it is
# CONFIGURED as", "what it has DONE" -- and logs/ sits alone under the third.
def is_transcript(path) -> bool:
    """Is this indexed path a past run rather than a source?"""
    p = str(path).replace("\\", "/")
    return "/logs/" in p or p.startswith("logs/")


# ---------------------------------------------------------------------
# chunking
# ---------------------------------------------------------------------


def chunk_text(text: str, size: int = CHUNK_CHARS, overlap: int = CHUNK_OVERLAP):
    """Split on blank lines, packing paragraphs up to `size` with overlap.

    Paragraph-aware so a chunk rarely cuts mid-sentence; the overlap keeps a
    passage that straddles a boundary retrievable from either side.
    """
    text = text.replace("\r\n", "\n")
    paras = [p for p in text.split("\n\n")]
    chunks: list[tuple[int, str]] = []
    buf, start = "", 0
    cursor = 0

    for p in paras:
        piece = p if not buf else buf + "\n\n" + p
        if len(piece) <= size or not buf:
            if not buf:
                start = cursor
            buf = piece
        else:
            chunks.append((start, buf))
            tail = buf[-overlap:] if overlap else ""
            start = cursor - len(tail)
            buf = (tail + "\n\n" + p) if tail else p
        cursor += len(p) + 2
        if len(chunks) >= MAX_CHUNKS_PER_FILE:
            break

    if buf.strip() and len(chunks) < MAX_CHUNKS_PER_FILE:
        chunks.append((start, buf))

    # A single paragraph longer than `size` is hard-split rather than dropped.
    out: list[tuple[int, str]] = []
    for st, c in chunks:
        if len(c) <= size * 2:
            out.append((st, c))
            continue
        for i in range(0, len(c), size):
            out.append((st + i, c[i:i + size]))
            if len(out) >= MAX_CHUNKS_PER_FILE:
                break
    return [(s, c.strip()) for s, c in out if c.strip()][:MAX_CHUNKS_PER_FILE]


def _norm(vec: list[float]) -> list[float]:
    n = sum(x * x for x in vec) ** 0.5
    return [x / n for x in vec] if n else vec


def _pack(vec: list[float]) -> bytes:
    return struct.pack(f"<{len(vec)}f", *vec)


def _unpack(blob: bytes) -> tuple[float, ...]:
    return struct.unpack(f"<{len(blob) // 4}f", blob)


# ---------------------------------------------------------------------
# the index
# ---------------------------------------------------------------------


@dataclass
class IndexStats:
    scanned: int = 0
    embedded: int = 0
    skipped_unchanged: int = 0
    skipped_big: int = 0
    chunks: int = 0
    errors: list[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class VectorIndex:
    def __init__(self, db_path: Path, embed_model: str):
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.embed_model = embed_model
        self.db = sqlite3.connect(str(self.path))
        self.db.execute("PRAGMA journal_mode=WAL")
        self._schema()
        self._check_schema()
        self._check_model()

    def _schema(self) -> None:
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
            CREATE TABLE IF NOT EXISTS docs (
                id INTEGER PRIMARY KEY,
                path TEXT UNIQUE NOT NULL,
                root TEXT NOT NULL,
                sha TEXT NOT NULL,
                chars INTEGER NOT NULL,
                indexed_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY,
                doc_id INTEGER NOT NULL REFERENCES docs(id) ON DELETE CASCADE,
                ord INTEGER NOT NULL,
                start INTEGER NOT NULL,
                text TEXT NOT NULL,
                vec BLOB NOT NULL,
                label TEXT DEFAULT '',
                stamp TEXT DEFAULT '',
                session TEXT DEFAULT ''
            );
            CREATE INDEX IF NOT EXISTS chunks_doc ON chunks(doc_id);
            """
        )
        self.db.commit()

    def _check_schema(self) -> None:
        row = self.db.execute("SELECT value FROM meta WHERE key='schema'").fetchone()
        if row is None:
            self.db.execute("INSERT INTO meta(key,value) VALUES('schema',?)", (SCHEMA_VERSION,))
            self.db.commit()
        elif row[0] != SCHEMA_VERSION:
            # The index is derived state, never a record -- it is rebuilt from
            # the ground rather than migrated.
            self.db.executescript(
                "DROP TABLE IF EXISTS chunks; DROP TABLE IF EXISTS docs; DELETE FROM meta;"
            )
            self.db.commit()
            self._schema()
            self.db.execute("INSERT INTO meta(key,value) VALUES('schema',?)", (SCHEMA_VERSION,))
            self.db.commit()

    def _check_model(self) -> None:
        cur = self.db.execute("SELECT value FROM meta WHERE key='embed_model'")
        row = cur.fetchone()
        if row is None:
            self.db.execute(
                "INSERT INTO meta(key,value) VALUES('embed_model',?)", (self.embed_model,)
            )
            self.db.commit()
        elif row[0] != self.embed_model:
            raise IndexError_(
                f"index at {self.path.name} was built with '{row[0]}' but the "
                f"configured embedder is '{self.embed_model}'. Vectors from "
                f"different models are not comparable. Rebuild with "
                f"index_ground <rebuild> or restore the old tag."
            )

    # ---- building ---------------------------------------------------

    def _iter_files(self, roots: list[Path]):
        # THE LOG HORIZON. logs/ grows by a file per run forever, and an
        # index that keeps every transcript ever written slowly buries the
        # ground's own documents under old chatter -- a two-month-old run
        # about a bug that no longer exists competing with the doctrine.
        # Only TRANSCRIPTS age out: everything else in the ground is a
        # standing document and stays indexed however old it is. The
        # transcripts themselves are never deleted; they simply stop being
        # retrieval candidates, and `sitting` and `when` still read them
        # directly, by number and by date.
        seen = 0
        for root in roots:
            if not root.exists():
                continue
            if root.is_file():
                if (root.suffix.lower() in TEXT_SUFFIXES
                        and not is_secret(root) and not is_protected(root)):
                    seen += 1
                    yield root.parent, root
                continue
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
                for fn in sorted(filenames):
                    p = Path(dirpath) / fn
                    if is_secret(p) or is_protected(p):
                        continue
                    if p.suffix.lower() not in TEXT_SUFFIXES:
                        continue
                    if _too_old_to_index(p):
                        continue
                    seen += 1
                    if seen > MAX_FILES:
                        return
                    yield root, p

    def build(self, roots: list[Path], embed_fn, report=lambda s: None) -> IndexStats:
        st = IndexStats()
        for root, p in self._iter_files(roots):
            st.scanned += 1
            try:
                size = p.stat().st_size
                if size > MAX_FILE_BYTES:
                    st.skipped_big += 1
                    continue
                raw = p.read_bytes()
            except Exception as exc:
                st.errors.append(f"{p.name}: {exc}")
                continue

            sha = hashlib.sha256(raw).hexdigest()
            key = str(p.resolve())

            cur = self.db.execute("SELECT id, sha FROM docs WHERE path=?", (key,))
            row = cur.fetchone()
            if row and row[1] == sha:
                st.skipped_unchanged += 1
                continue

            try:
                text = raw.decode("utf-8", errors="replace")
            except Exception as exc:
                st.errors.append(f"{p.name}: {exc}")
                continue
            if not text.strip():
                continue

            # A RUN TRANSCRIPT IS INDEXED BY ITS DELIVERY (his ruling
            # 2026-09-10). transcript.index_text returns "" for anything that
            # is not a run -- a standup report, a parity run -- and those fall
            # through to whole-file chunking below, because both are already
            # summaries and dropping them would be a silent loss.
            trimmed = ""
            if p.suffix.lower() == ".md":
                try:
                    trimmed = _transcript.index_text(text)
                except Exception:
                    trimmed = ""

            if trimmed:
                pieces = [(st, tx, "delivery", "", "")
                          for st, tx in chunk_text(trimmed)]
            elif p.name == _memory.MEMORY_FILE:
                # One chunk per remembered entry, carrying its stamp and the
                # session that produced it, instead of one growing blob.
                pieces = [(st, tx, lb, sp, ss)
                          for st, tx, lb, sp, ss in _memory.split_entries(text)]
            else:
                pieces = [(st, tx, "", "", "") for st, tx in chunk_text(text)]
            if not pieces:
                continue

            vecs = []
            try:
                for piece in pieces:
                    vecs.append(_norm(embed_fn(piece[1])))
            except Exception as exc:
                st.errors.append(f"{p.name}: embed failed ({exc})")
                continue

            if row:
                self.db.execute("DELETE FROM chunks WHERE doc_id=?", (row[0],))
                self.db.execute(
                    "UPDATE docs SET sha=?,chars=?,indexed_at=?,root=? WHERE id=?",
                    (sha, len(text), _now(), str(root), row[0]),
                )
                doc_id = row[0]
            else:
                cur = self.db.execute(
                    "INSERT INTO docs(path,root,sha,chars,indexed_at) VALUES(?,?,?,?,?)",
                    (key, str(root), sha, len(text), _now()),
                )
                doc_id = cur.lastrowid

            self.db.executemany(
                "INSERT INTO chunks(doc_id,ord,start,text,vec,label,stamp,session)"
                " VALUES(?,?,?,?,?,?,?,?)",
                [
                    (doc_id, i, pieces[i][0], pieces[i][1], _pack(vecs[i]),
                     pieces[i][2], pieces[i][3], pieces[i][4])
                    for i in range(len(pieces))
                ],
            )
            self.db.commit()
            st.embedded += 1
            st.chunks += len(pieces)
            report(f"    + {p.name} ({len(pieces)} chunks)")

        self.prune(report, roots=roots)
        return st

    # A refresh may evict this share of the corpus and no more. Above it the
    # prune REFUSES and reports, because a number that large is far more
    # likely to be a typo in index_roots.txt than a deliberate narrowing --
    # and the operator finding out via a thin search result days later is
    # the failure mode this bound exists to prevent.
    ORPHAN_CEILING = 0.25

    def prune(self, report=lambda s: None, roots: list[Path] | None = None) -> int:
        """Drop docs the index should no longer be holding.

        TWO QUESTIONS, and until 2026-09-03 it could only ask the first:

            1. is the file gone?              (the filesystem knows)
            2. is its root still declared?    (index_roots.txt knows)

        The second was the hole. Sitting 78: `worlds/manjuel` was removed
        from index_roots.txt and 91 of 801 documents from that world STAYED
        IN THE CORPUS and kept answering, because every one of their files
        still existed on disk. The door was shut and the room was still
        full. Only a full rebuild cleared it, and nothing said so.

        MATCH ON THE PATH, NOT THE STORED `root` STRING. A root can be
        renamed, narrowed (`worlds/manjuel` -> `worlds/manjuel/codex`) or
        re-cased; the stored label then compares equal for documents that
        are genuinely out of scope, and unequal for ones that are not. The
        path is the fact.

        GATED, and this is the operator's ruling of 2026-09-03 (option c of
        three). Root-awareness makes a REFRESH destructive in a way it has
        never been: a typo in index_roots.txt would silently evict that
        root's documents on the very next run. So an eviction larger than
        ORPHAN_CEILING of the corpus is REFUSED and reported instead --
        the shape of a guard that will not perform a suspiciously large
        action on the say-so of a config file. `rebuild` still clears
        everything; that path DROPs the tables and is explicit.

        `roots=None` keeps the old behaviour exactly -- missing files only.
        A caller that cannot say what is in scope must not be taken to mean
        that nothing is.
        """
        rows = list(self.db.execute("SELECT id, path FROM docs"))
        total = len(rows)

        missing = [(i, p) for i, p in rows if not Path(p).exists()]

        orphans: list[tuple] = []
        if roots:
            live = []
            for r in roots:
                try:
                    live.append(Path(r).resolve())
                except OSError:
                    continue
            known = {i for i, _ in missing}
            for i, p in rows:
                if i in known:
                    continue
                try:
                    rp = Path(p).resolve()
                except OSError:
                    continue
                if not any(rp == root or root in rp.parents for root in live):
                    orphans.append((i, p))

        if orphans and total and (len(orphans) / total) > self.ORPHAN_CEILING:
            report(f"    ! {len(orphans)} of {total} docs are under a root no "
                   f"longer declared -- more than "
                   f"{int(self.ORPHAN_CEILING * 100)}% of the corpus.")
            report("      REFUSED as too large for a refresh. Check "
                   "index_roots.txt; run `index_ground rebuild` if it is right.")
            orphans = []

        for i, pth in missing:
            self.db.execute("DELETE FROM chunks WHERE doc_id=?", (i,))
            self.db.execute("DELETE FROM docs WHERE id=?", (i,))
            report(f"    - {Path(pth).name} (missing)")
        for i, pth in orphans:
            self.db.execute("DELETE FROM chunks WHERE doc_id=?", (i,))
            self.db.execute("DELETE FROM docs WHERE id=?", (i,))
            report(f"    - {Path(pth).name} (root no longer declared)")

        if missing or orphans:
            self.db.commit()
        return len(missing) + len(orphans)

    # ---- searching --------------------------------------------------

    def search(self, qvec: list[float], limit: int = 5, per_doc: int = 2,
               scope: str = "all"):
        """Rank the index. `scope` picks the corpus (his ruling 2026-09-10):

            sources      everything that is not a transcript -- the code, the
                         doctrine, the seats, the record's own documents
            transcripts  logs/ only: what was SAID on a past run
            all          both, the old behaviour, kept for callers that mean it

        WHY THIS EXISTS. Measured 2026-09-10: 812 of 996 indexed documents and
        4,060 of 6,705 ranked passages were old runs, and "what does the
        covenant say" returned eight transcripts and never the covenant. Each
        answer is written back to logs/ and indexed, so the estate was
        answering from its own echo and laundering an error into the record.
        A weight was refused in favour of a split -- a cosine penalty is a
        number nobody can defend and would still return transcripts for a
        question about doctrine, just fewer of them.
        """
        q = _norm(qvec)
        rows = self.db.execute(
            "SELECT c.id, c.doc_id, c.ord, c.start, c.text, c.vec, d.path, "
            "c.label, c.stamp, c.session "
            "FROM chunks c JOIN docs d ON d.id = c.doc_id"
        ).fetchall()

        if scope in ("sources", "transcripts"):
            want_log = scope == "transcripts"
            rows = [r for r in rows if is_transcript(r[6]) == want_log]

        usable = [r for r in rows if len(r[5]) // 4 == len(q)]
        if not usable:
            return []

        if _np is not None:
            mat = _np.frombuffer(b"".join(r[5] for r in usable), dtype="<f4")
            mat = mat.reshape(len(usable), len(q))
            sims = mat @ _np.asarray(q, dtype="<f4")
            scored = [
                (float(sims[i]), usable[i][6], usable[i][2], usable[i][3],
                 usable[i][4], usable[i][7], usable[i][8], usable[i][9])
                for i in range(len(usable))
            ]
        else:
            scored = [
                (sum(a * b for a, b in zip(q, _unpack(r[5]))), r[6], r[2], r[3],
                 r[4], r[7], r[8], r[9])
                for r in usable
            ]

        scored.sort(key=lambda t: t[0], reverse=True)

        out, per = [], {}
        for score, path, ordn, start, text, label, stamp, session in scored:
            if per.get(path, 0) >= per_doc:
                continue
            per[path] = per.get(path, 0) + 1
            out.append({"score": score, "path": path, "ord": ordn, "start": start,
                        "text": text, "label": label, "stamp": stamp,
                        "session": session})
            if len(out) >= limit:
                break
        return out

    def stats(self) -> dict:
        d = self.db.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
        c = self.db.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        roots = [r[0] for r in self.db.execute("SELECT DISTINCT root FROM docs")]
        return {"docs": d, "chunks": c, "roots": roots, "model": self.embed_model}

    def close(self) -> None:
        self.db.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_roots(config: Path, default: list[Path], base: Path | None = None) -> list[Path]:
    """Roots come from a plain text file, one path per line. Keeps the ground
    list editable without touching code, same as agents/ and skills/.

    Relative entries resolve against `base` (manjuel's own ground), NOT the
    process working directory -- otherwise the same config would index
    different files depending on where the REPL was launched from.
    """
    if not config.exists():
        return list(default)
    base = base or config.parent
    roots = []
    for line in config.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        p = Path(os.path.expandvars(os.path.expanduser(line)))
        roots.append(p if p.is_absolute() else (base / p))
    return roots or list(default)
