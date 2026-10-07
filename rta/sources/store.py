"""
Ṛta — owned data store adapter (structured store the operator controls).

Holds three things:

1. **runs / findings** — what the deterministic engine was asked and what it
   answered (verdict, debt, per-rule findings). The engine remains the
   authority; this table is a *record of authority*, never a substitute for it.
   Nothing here may be read back as a verdict.
2. **source_evidence** — provenance rows linking a run to the external or local
   reference that supplied context (an issue URL, a doc path) with the
   reference's content hash and fetch time, so "why did the assistant mention
   this?" is answerable months later.
3. **tool_audit** — an append-only log of MCP tool calls: tool, role, argument
   *digest*, outcome, duration, degradation flag. Deliberately stores a SHA-256
   digest of the arguments instead of the arguments themselves: auditability
   without quietly becoming a second copy of customer constraint files.

Storage is SQLite from the standard library with WAL journalling and a busy
timeout. The default location is ``~/.rta/store/rta_store.db`` — outside any
repository, so a run never drops an untracked database into a clean checkout.
Override with ``RTA_STORE_DB``.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Optional

from rta.sources.base import (
    CODE_DISABLED,
    CODE_LOCAL_IO,
    fail,
    now_iso,
    ok,
    sha256_hex,
)

SOURCE_NAME = "store"

SCHEMA_VERSION = 1

DDL_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS schema_version (
        version     INTEGER NOT NULL,
        applied_at  TEXT    NOT NULL,
        note        TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS runs (
        run_id            TEXT PRIMARY KEY,
        created_at        TEXT NOT NULL,
        tool              TEXT NOT NULL,
        role              TEXT NOT NULL,
        sdc_sha256        TEXT NOT NULL,
        sdc_bytes         INTEGER NOT NULL,
        verdict           TEXT,
        debt_count        INTEGER,
        blocker_count     INTEGER,
        warning_count     INTEGER,
        rule_count        INTEGER,
        context_available INTEGER,
        degraded          INTEGER NOT NULL DEFAULT 0,
        sources_used      TEXT,
        engine_version    TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS findings (
        finding_id   TEXT NOT NULL,
        run_id       TEXT NOT NULL,
        rule_id      TEXT,
        severity     TEXT,
        message      TEXT,
        line         INTEGER,
        PRIMARY KEY (finding_id, run_id),
        FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS source_evidence (
        evidence_id  INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id       TEXT NOT NULL,
        source       TEXT NOT NULL,
        ref          TEXT NOT NULL,
        content_hash TEXT,
        fetched_at   TEXT,
        freshness    TEXT,
        note         TEXT,
        FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tool_audit (
        audit_id     INTEGER PRIMARY KEY AUTOINCREMENT,
        ts           TEXT NOT NULL,
        tool         TEXT NOT NULL,
        role         TEXT NOT NULL,
        args_digest  TEXT NOT NULL,
        args_keys    TEXT,
        outcome      TEXT NOT NULL,
        duration_ms  REAL,
        degraded     INTEGER NOT NULL DEFAULT 0,
        sources_used TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_findings_run ON findings(run_id)",
    "CREATE INDEX IF NOT EXISTS idx_evidence_run ON source_evidence(run_id)",
    "CREATE INDEX IF NOT EXISTS idx_runs_created ON runs(created_at)",
    "CREATE INDEX IF NOT EXISTS idx_audit_ts ON tool_audit(ts)",
)

RUN_COLUMNS = ("run_id", "created_at", "tool", "role", "sdc_sha256",
               "sdc_bytes", "verdict", "debt_count", "blocker_count",
               "warning_count", "rule_count", "context_available", "degraded",
               "sources_used", "engine_version")


def default_db_path() -> Path:
    """Store location — outside the repository by default."""
    override = os.environ.get("RTA_STORE_DB", "").strip()
    if override:
        return Path(override)
    return Path.home() / ".rta" / "store" / "rta_store.db"


def disabled() -> bool:
    """``RTA_STORE_DISABLE=1`` turns the store off entirely."""
    return os.environ.get("RTA_STORE_DISABLE", "").strip() in ("1", "true", "yes")


def connect(path: Optional[Path] = None) -> sqlite3.Connection:
    """Open (and create) the store. Raises ``sqlite3.Error`` / ``OSError``."""
    target = Path(path) if path is not None else default_db_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target), timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=2000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def migrate(conn: sqlite3.Connection) -> int:
    """Apply DDL statements. Idempotent — safe to call on every startup."""
    for statement in DDL_STATEMENTS:
        conn.execute(statement)
    row = conn.execute("SELECT MAX(version) AS v FROM schema_version").fetchone()
    current = int(row["v"]) if row and row["v"] is not None else 0
    if current < SCHEMA_VERSION:
        conn.execute(
            "INSERT INTO schema_version(version, applied_at, note) VALUES (?,?,?)",
            (SCHEMA_VERSION, now_iso(), "initial multi-source schema"))
        conn.commit()
    return SCHEMA_VERSION


def engine_facts(analysis: Optional[dict]) -> dict:
    """Extract the fields the store records from an engine ``analyze()`` payload.

    The engine's payload shape is the authority — this helper only *reads* it.

    Observed payload keys (verified against ``rta.api.api_server.analyze``):

    * ``issues[]``  → ``{sev, code, msg, line, line2, identity, context}``
    * ``readiness`` → ``{overall, mode, engine_failed, dimensions{...}}``
    * ``info[]``    → ``{code, msg, line}`` advisories (not blockers)
    * ``ok`` / ``engine_error`` / ``mode_note`` / ``context``

    Nothing here invents or recomputes a verdict: ``verdict`` is copied from
    ``readiness.overall`` verbatim.
    """
    payload = analysis if isinstance(analysis, dict) else {}
    issues = payload.get("issues") if isinstance(payload.get("issues"), list) else []
    info = payload.get("info") if isinstance(payload.get("info"), list) else []
    readiness = payload.get("readiness") if isinstance(payload.get("readiness"), dict) else {}

    def _sev(item) -> str:
        return str((item or {}).get("sev", "")).lower()

    blocks = [i for i in issues if _sev(i) in ("error", "blocker")]
    warns = [i for i in issues if _sev(i) == "warning"]
    codes = {str(i.get("code")) for i in issues if isinstance(i, dict) and i.get("code")}
    dimensions = readiness.get("dimensions") if isinstance(readiness.get("dimensions"), dict) else {}
    design_ctx = dimensions.get("DESIGN_CONTEXT") if isinstance(dimensions.get("DESIGN_CONTEXT"), dict) else {}
    context_available = bool(payload.get("context")) or (
        str(readiness.get("mode", "")) != "SDC_ONLY"
        and str(design_ctx.get("status", "")) not in ("INSUFFICIENT_CONTEXT", ""))

    return {
        "verdict": readiness.get("overall"),
        "mode": readiness.get("mode"),
        "engine_failed": bool(readiness.get("engine_failed")),
        "ok": bool(payload.get("ok")),
        "engine_error": payload.get("engine_error"),
        "mode_note": payload.get("mode_note"),
        "blocker_count": len(blocks),
        "warning_count": len(warns),
        "issue_count": len(issues),
        "info_count": len(info),
        "rule_count": len(codes),
        "rule_ids": sorted(codes),
        "context_available": context_available,
        "limited_design_verification": bool(readiness.get("limited_design_verification")),
    }


def args_digest(args: Optional[dict]) -> tuple:
    """Return ``(sha256_hex, comma_separated_keys)`` for an MCP argument dict.

    The digest is what the audit log stores — the argument values themselves are
    never persisted, so constraint text and any embedded paths stay out of the
    audit trail.
    """
    payload = args if isinstance(args, dict) else {}
    try:
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                               default=str)
    except (TypeError, ValueError):
        canonical = repr(sorted(payload.keys()))
    keys = ",".join(sorted(str(k) for k in payload.keys()))[:400]
    return sha256_hex(canonical), keys


class StoreAdapter:
    """Read/write adapter over the SQLite store. Never raises on public calls."""

    name = SOURCE_NAME

    def __init__(self, path: Optional[Path] = None, enabled: Optional[bool] = None,
                 default_policy_ok: bool = True) -> None:
        self.path = Path(path) if path is not None else default_db_path()
        self.enabled = (not disabled()) if enabled is None else bool(enabled)
        self._ready = False
        self._last_error: Optional[str] = None
        self._default_policy_ok = default_policy_ok

    # ── plumbing ───────────────────────────────────────────────────────────

    def _ensure(self, conn: sqlite3.Connection) -> None:
        if not self._ready:
            migrate(conn)
            self._ready = True

    def _open(self):
        conn = connect(self.path)
        self._ensure(conn)
        return conn

    def health(self) -> dict:
        info = {
            "source": self.name,
            "kind": "sqlite",
            "enabled": self.enabled,
            "path": str(self.path),
            "schema_version": SCHEMA_VERSION,
            "requires_network": False,
            "requires_credential": False,
            "last_error": self._last_error,
        }
        if not self.enabled:
            info["note"] = "store disabled via RTA_STORE_DISABLE"
            return info
        try:
            with self._open() as conn:
                for table in ("runs", "findings", "source_evidence", "tool_audit"):
                    info[f"{table}_rows"] = int(
                        conn.execute(f"SELECT COUNT(*) AS n FROM {table}")
                        .fetchone()["n"])
                info["bytes"] = self.path.stat().st_size if self.path.exists() else 0
        except (sqlite3.Error, OSError) as err:
            info["last_error"] = f"{type(err).__name__}: {err}"
        return info

    # ── writes ─────────────────────────────────────────────────────────────

    def record_run(self, *, run_id: str, sdc_text: str, analysis: dict,
                   tool: str, role: str, degraded: bool = False,
                   sources_used: Optional[list] = None,
                   engine_version: str = "") -> dict:
        """Persist one engine run plus its findings. Verdict values are copied
        verbatim from the engine payload — the store never recomputes them."""
        if not self.enabled:
            return fail(SOURCE_NAME, CODE_DISABLED,
                        "store disabled via RTA_STORE_DISABLE")
        sdc = sdc_text or ""
        analysis = analysis if isinstance(analysis, dict) else {}
        facts = engine_facts(analysis)
        issues = analysis.get("issues") if isinstance(analysis.get("issues"), list) \
            else []
        try:
            with self._open() as conn:
                conn.execute(
                    f"INSERT OR REPLACE INTO runs ({','.join(RUN_COLUMNS)}) "
                    f"VALUES ({','.join('?' * len(RUN_COLUMNS))})",
                    (run_id, now_iso(), tool, role, sha256_hex(sdc), len(sdc),
                     facts["verdict"], facts["issue_count"],
                     facts["blocker_count"], facts["warning_count"],
                     facts["rule_count"],
                     1 if facts["context_available"] else 0,
                     1 if degraded else 0,
                     json.dumps(sources_used or []), engine_version))
                for index, issue in enumerate(issues):
                    if not isinstance(issue, dict):
                        continue
                    code = str(issue.get("code") or f"UNKNOWN-{index}")
                    line = issue.get("line")
                    finding_id = str(issue.get("identity") or f"{code}:{line}")
                    conn.execute(
                        "INSERT OR REPLACE INTO findings"
                        " (finding_id, run_id, rule_id, severity, message, line)"
                        " VALUES (?,?,?,?,?,?)",
                        (finding_id, run_id, code,
                         issue.get("sev"),
                         str(issue.get("msg") or "")[:1000],
                         line))
                conn.commit()
        except (sqlite3.Error, OSError) as err:
            self._last_error = f"{type(err).__name__}: {err}"
            return fail(SOURCE_NAME, CODE_LOCAL_IO,
                        f"could not write run: {self._last_error}")
        return ok(SOURCE_NAME, {"run_id": run_id, "findings": len(issues)})

    def record_evidence(self, *, run_id: str, source: str, ref: str,
                        content_hash: str = "", fetched_at: str = "",
                        freshness: str = "", note: str = "") -> dict:
        """Attach a provenance row: which reference supplied context to a run."""
        if not self.enabled:
            return fail(SOURCE_NAME, CODE_DISABLED,
                        "store disabled via RTA_STORE_DISABLE")
        try:
            with self._open() as conn:
                conn.execute(
                    "INSERT INTO source_evidence"
                    " (run_id, source, ref, content_hash, fetched_at, freshness, note)"
                    " VALUES (?,?,?,?,?,?,?)",
                    (run_id, source, ref, content_hash, fetched_at, freshness,
                     note[:400]))
                conn.commit()
        except (sqlite3.Error, OSError) as err:
            self._last_error = f"{type(err).__name__}: {err}"
            return fail(SOURCE_NAME, CODE_LOCAL_IO,
                        f"could not write evidence: {self._last_error}")
        return ok(SOURCE_NAME, {"run_id": run_id, "source": source, "ref": ref})

    def audit(self, *, tool: str, role: str, args: Optional[dict],
              outcome: str, duration_ms: float = 0.0, degraded: bool = False,
              sources_used: Optional[list] = None) -> None:
        """Append one audit row. Best-effort by design — never raises, never
        blocks a tool call, and never stores argument values."""
        if not self.enabled:
            return
        digest, keys = args_digest(args)
        try:
            with self._open() as conn:
                conn.execute(
                    "INSERT INTO tool_audit"
                    " (ts, tool, role, args_digest, args_keys, outcome,"
                    "  duration_ms, degraded, sources_used)"
                    " VALUES (?,?,?,?,?,?,?,?,?)",
                    (now_iso(), tool, role, digest, keys, outcome,
                     float(duration_ms), 1 if degraded else 0,
                     json.dumps(sources_used or [])))
                conn.commit()
        except (sqlite3.Error, OSError) as err:
            self._last_error = f"{type(err).__name__}: {err}"
            return

    # ── reads ──────────────────────────────────────────────────────────────

    def query_runs(self, limit: int = 10, verdict: str = "",
                   rule_id: str = "", run_id: str = "") -> dict:
        """Look up previous runs. Read-only; returns engine-recorded values."""
        if not self.enabled:
            return fail(SOURCE_NAME, CODE_DISABLED,
                        "store disabled via RTA_STORE_DISABLE")
        cap = max(1, min(int(limit or 10), 100))
        sql = ["SELECT * FROM runs"]
        where, params = [], []
        if verdict:
            where.append("verdict = ?")
            params.append(verdict)
        if run_id:
            where.append("run_id = ?")
            params.append(run_id)
        if rule_id:
            where.append("run_id IN (SELECT run_id FROM findings WHERE rule_id = ?)")
            params.append(rule_id)
        if where:
            sql.append("WHERE " + " AND ".join(where))
        sql.append("ORDER BY created_at DESC LIMIT ?")
        params.append(cap)
        try:
            with self._open() as conn:
                rows = [dict(r) for r in conn.execute(" ".join(sql), params)]
                for row in rows:
                    row["sources_used"] = json.loads(row.get("sources_used") or "[]")
                evidence = []
                if rows:
                    marks = ",".join("?" * len(rows))
                    evidence = [dict(r) for r in conn.execute(
                        f"SELECT * FROM source_evidence WHERE run_id IN ({marks})",
                        [r["run_id"] for r in rows])]
        except (sqlite3.Error, OSError, ValueError) as err:
            self._last_error = f"{type(err).__name__}: {err}"
            return fail(SOURCE_NAME, CODE_LOCAL_IO,
                        f"could not read runs: {self._last_error}")
        return ok(SOURCE_NAME, {"runs": rows, "returned": len(rows),
                                "evidence": evidence, "path": str(self.path)})

    def query_audit(self, limit: int = 20, tool: str = "") -> dict:
        """Read the audit trail (digests only — no argument values)."""
        if not self.enabled:
            return fail(SOURCE_NAME, CODE_DISABLED,
                        "store disabled via RTA_STORE_DISABLE")
        cap = max(1, min(int(limit or 20), 200))
        try:
            with self._open() as conn:
                if tool:
                    rows = [dict(r) for r in conn.execute(
                        "SELECT * FROM tool_audit WHERE tool = ? "
                        "ORDER BY audit_id DESC LIMIT ?", (tool, cap))]
                else:
                    rows = [dict(r) for r in conn.execute(
                        "SELECT * FROM tool_audit ORDER BY audit_id DESC LIMIT ?",
                        (cap,))]
        except (sqlite3.Error, OSError) as err:
            self._last_error = f"{type(err).__name__}: {err}"
            return fail(SOURCE_NAME, CODE_LOCAL_IO,
                        f"could not read audit log: {self._last_error}")
        return ok(SOURCE_NAME, {"entries": rows, "returned": len(rows)})


def new_run_id(prefix: str = "run") -> str:
    """Deterministic-shaped, collision-resistant run identifier."""
    return f"{prefix}-{int(time.time() * 1000)}-{os.getpid()}"
