"""
Ṛta — local documentation corpus adapter (unstructured knowledge source).

Answers "where is this documented / which rule says this?" from the files that
ship with the repository: feature docs, product docs, samples, the engineer
test kit, and the changelog.

Why a local corpus instead of a hosted wiki: it needs **no credential**, works
**offline**, and is **deterministic** — which keeps the tool's clean-room and
CI guarantees intact. A hosted knowledge base (Notion, Confluence) can be
added later behind the same adapter contract (see ``base.py``); it is not
required for the multi-source story.

Scoring is deliberately simple and readable, not clever: exact term hits in a
line, weighted by a filename match bonus, then a deterministic sort. There is
no embedding model and no network call — so the same query always returns the
same ranking on the same tree.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Iterator, Optional

from rta.sources.base import (
    CODE_LOCAL_IO,
    CODE_NOT_FOUND,
    DiskCache,
    SourcePolicy,
    fail,
    ok,
    sha256_hex,
)

SOURCE_NAME = "corpus"

#: Directories indexed by default, relative to the repository root.
DEFAULT_DIR_ROOTS = (
    "docs",
    "rta/docs",
    "samples",
    "engineer_test_kit",
)

#: Individual files indexed by default, relative to the repository root.
DEFAULT_FILE_ROOTS = (
    "README.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
)

#: File extensions considered textual knowledge.
DEFAULT_EXTS = (
    ".md", ".txt", ".rst",
    ".yaml", ".yml", ".json",
    ".sdc", ".tcl",
    ".py", ".js", ".ts", ".html",
)

MAX_FILE_BYTES = 1_000_000        # 1 MB — larger files are indexed by name only
MAX_FILES = 4_000                 # hard cap so a stray tree cannot stall a call
SNIPPET_CHARS = 240
TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def repo_root() -> Path:
    """Repository root inferred from this file's location."""
    return Path(__file__).resolve().parents[2]


def _env_list(name: str) -> list:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return []
    return [part for part in re.split(r"[;:]", raw) if part.strip()]


def _tokenize(query: str) -> list:
    """Lowercase alphanumeric terms of two or more characters."""
    seen = []
    for token in TOKEN_RE.findall(query.lower()):
        if len(token) >= 2 and token not in seen:
            seen.append(token)
    return seen


class _Entry:
    """One indexed file: relative path, content hash, and its lines."""

    __slots__ = ("rel", "abs_path", "sha", "lines", "truncated")

    def __init__(self, rel: str, abs_path: Path, sha: str, lines: list,
                 truncated: bool) -> None:
        self.rel = rel
        self.abs_path = abs_path
        self.sha = sha
        self.lines = lines
        self.truncated = truncated


class CorpusAdapter:
    """Searchable view over the repository's documentation and sample tree."""

    name = SOURCE_NAME

    def __init__(self, roots: Optional[list] = None,
                 policy: Optional[SourcePolicy] = None,
                 cache: Optional[DiskCache] = None,
                 base_dir: Optional[Path] = None) -> None:
        self.policy = policy or SourcePolicy.from_env()
        self.cache = cache if cache is not None else DiskCache()
        self.base_dir = Path(base_dir) if base_dir is not None else repo_root()
        self.exts = tuple(_env_list("RTA_CORPUS_EXTS")) or DEFAULT_EXTS
        self._roots = list(roots) if roots else self._default_roots()
        self._entries: Optional[list] = None
        self._index_error: Optional[str] = None
        self._signature: str = ""

    # ── roots ──────────────────────────────────────────────────────────────

    def _default_roots(self) -> list:
        env_roots = _env_list("RTA_CORPUS_ROOTS")
        if env_roots:
            return [Path(p) for p in env_roots]
        roots = [self.base_dir / name for name in DEFAULT_DIR_ROOTS]
        roots += [self.base_dir / name for name in DEFAULT_FILE_ROOTS]
        return roots

    def existing_roots(self) -> list:
        return [p for p in self._roots if p.exists()]

    def missing_roots(self) -> list:
        return [str(p) for p in self._roots if not p.exists()]

    # ── indexing ───────────────────────────────────────────────────────────

    def _iter_files(self) -> Iterator[Path]:
        for root in self.existing_roots():
            if root.is_file():
                yield root
                continue
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames[:] = sorted(d for d in dirnames
                                     if not d.startswith((".", "__")))
                for filename in sorted(filenames):
                    if filename.lower().endswith(self.exts):
                        yield Path(dirpath) / filename

    def _load_entry(self, path: Path) -> Optional[_Entry]:
        try:
            raw = path.read_bytes()
        except OSError:
            return None
        if b"\x00" in raw[:8192]:                    # binary — skip content
            return None
        truncated = len(raw) > MAX_FILE_BYTES
        if truncated:
            raw = raw[:MAX_FILE_BYTES]
        text = raw.decode("utf-8", errors="replace")
        try:
            rel = str(path.relative_to(self.base_dir))
        except ValueError:
            rel = str(path)
        lines = text.splitlines()
        return _Entry(rel.replace("\\", "/"), path, sha256_hex(text)[:16],
                      lines, truncated)

    def _build_index(self) -> list:
        entries: list = []
        signature_parts: list = []
        try:
            for path in self._iter_files():
                if len(entries) >= MAX_FILES:
                    break
                entry = self._load_entry(path)
                if entry is None:
                    continue
                entries.append(entry)
                signature_parts.append(f"{entry.rel}:{entry.sha}")
        except OSError as err:                        # pragma: no cover - rare
            self._index_error = f"{type(err).__name__}: {err}"
        entries.sort(key=lambda e: e.rel)
        self._signature = sha256_hex("\n".join(signature_parts))[:16]
        return entries

    def entries(self) -> list:
        """Indexed entries, built once per process."""
        if self._entries is None:
            self._entries = self._build_index()
        return self._entries

    def rebuild(self) -> None:
        """Drop the in-process index (call after editing docs)."""
        self._entries = None
        self._index_error = None

    # ── health ─────────────────────────────────────────────────────────────

    def health(self) -> dict:
        entries = self.entries()
        total_lines = sum(len(e.lines) for e in entries)
        return {
            "source": self.name,
            "kind": "local-corpus",
            "requires_network": False,
            "requires_credential": False,
            "base_dir": str(self.base_dir),
            "roots": len(self.existing_roots()),
            "missing_roots": self.missing_roots(),
            "files_indexed": len(entries),
            "lines_indexed": total_lines,
            "index_signature": self._signature,
            "extensions": list(self.exts),
            "last_error": self._index_error,
        }

    # ── search ─────────────────────────────────────────────────────────────

    def search(self, query: str, limit: int = 8,
               path_filter: str = "") -> dict:
        """Return the top matching documentation lines for ``query``.

        Never raises. An empty or unmatched query returns ``ok`` with an empty
        result list and an explanatory ``note`` rather than an error — "no
        docs matched" is a legitimate answer, not a failure.
        """
        tokens = _tokenize(str(query or ""))
        if not tokens:
            return ok(SOURCE_NAME, {"query": str(query or ""), "matches": [],
                                    "index_signature": self._signature},
                      note="query contained no searchable terms (>= 2 chars)")

        cap = max(1, min(int(limit or 8), self.policy.max_items))
        needle = str(path_filter or "").lower()

        matches: list = []
        for entry in self.entries():
            if needle and needle not in entry.rel.lower():
                continue
            name_bonus = sum(3 for t in tokens if t in entry.rel.lower())
            for lineno, line in enumerate(entry.lines, start=1):
                lowered = line.lower()
                hits = sum(1 for t in tokens if t in lowered)
                if not hits:
                    continue
                score = hits * 2 + name_bonus
                if line.lstrip().startswith("#"):
                    score += 1                          # headings are strong hits
                matches.append({
                    "path": entry.rel,
                    "line": lineno,
                    "score": score,
                    "snippet": line.strip()[:SNIPPET_CHARS],
                    "content_hash": entry.sha,
                    "lines_in_file": len(entry.lines),
                })

        matches.sort(key=lambda m: (-m["score"], m["path"], m["line"]))
        top = matches[:cap]

        if self._entries == [] and self.missing_roots():
            return fail(SOURCE_NAME, CODE_NOT_FOUND,
                        "no corpus roots exist on this machine",
                        data={"query": str(query or ""), "matches": [],
                              "missing_roots": self.missing_roots()})
        if self._index_error:
            return fail(SOURCE_NAME, CODE_LOCAL_IO,
                        f"index completed with errors: {self._index_error}",
                        data={"query": str(query or ""), "matches": top},
                        note="partial index — some roots could not be read")

        return ok(SOURCE_NAME, {
            "query": str(query or ""),
            "terms": tokens,
            "matches": top,
            "total_matches": len(matches),
            "files_indexed": len(self.entries()),
            "index_signature": self._signature,
        }, note=("no documentation matched — try a rule id (e.g. SDC-068) or a "
                 "feature name (e.g. clock-groups)") if not top else None)
