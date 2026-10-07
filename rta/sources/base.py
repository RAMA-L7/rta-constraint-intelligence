"""
Ṛta — source adapter layer (advisory context sources).

This package connects the Ṛta MCP server to external and local *context*
sources: a GitHub issue tracker, a local documentation corpus, and an owned
SQLite store.

**Design rule (non-negotiable):** sources are ADVISORY. They supply context;
they never supply authority. A verdict (READY / NOT_READY, blocker counts,
readiness scores) can only come from the frozen deterministic engine via
``rta.api.api_server``. No adapter in this package may compute, infer, or
modify a verdict.

Contract every adapter in this package obeys:

1. ``call(...)`` **never raises**. All failures are returned as a result
   envelope with ``ok=False`` and a stable ``error.code``.
2. Failures **degrade, never crash**: a cached last-known-good value is served
   when available and is marked ``cached=True``.
3. Degradation is **disclosed**: ``degraded`` is ``True`` whenever the answer
   is stale, partial, or served from cache.
4. Results are **deterministic** for the same inputs and the same cached state.
5. **Pure standard library only** — ``urllib``, ``sqlite3``, ``json``,
   ``hashlib``. No new runtime dependencies (matches the engine contract).
6. Secrets are never echoed: tokens are read from the environment, never
   logged, never returned in an envelope, never written to the store.

Result envelope (stable — consumers may rely on these keys)::

    {
      "ok": bool,
      "source": str,                 # "corpus" | "github" | "store"
      "data": any,                   # adapter-specific payload, or null
      "degraded": bool,
      "cached": bool,
      "fetched_at": str | null,      # ISO-8601 UTC, "…Z"
      "error": {"code": str, "message": str, "retry_after": float | null} | null,
      "note": str | null
    }
"""

from __future__ import annotations

import hashlib
import json
import os
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

# ═══════════════════════════════════════════════════════════════════════════
# STABLE ERROR CODES — referenced by the tests, the failure matrix, and the
# MCP tool responses. Never renumber or reuse these strings.
# ═══════════════════════════════════════════════════════════════════════════

CODE_UNAVAILABLE = "UNAVAILABLE"          # source unreachable / not configured
CODE_TIMEOUT = "TIMEOUT"                  # transport timeout
CODE_RATE_LIMITED = "RATE_LIMITED"        # upstream throttled us
CODE_AUTH_MISSING = "AUTH_MISSING"        # no credential supplied for a source
CODE_AUTH_INVALID = "AUTH_INVALID"        # credential rejected by upstream
CODE_NOT_FOUND = "NOT_FOUND"              # resource or root path missing
CODE_BAD_RESPONSE = "BAD_RESPONSE"        # upstream returned unparseable data
CODE_BREAKER_OPEN = "BREAKER_OPEN"        # circuit breaker is cooling down
CODE_FORBIDDEN = "FORBIDDEN"              # access layer denied the call
CODE_DISABLED = "DISABLED"                # source disabled by configuration
CODE_LOCAL_IO = "LOCAL_IO"                # local filesystem/database failure

#: Free-text display order for docs/tests that enumerate the code set.
ERROR_CODES = (
    CODE_UNAVAILABLE,
    CODE_TIMEOUT,
    CODE_RATE_LIMITED,
    CODE_AUTH_MISSING,
    CODE_AUTH_INVALID,
    CODE_NOT_FOUND,
    CODE_BAD_RESPONSE,
    CODE_BREAKER_OPEN,
    CODE_FORBIDDEN,
    CODE_DISABLED,
    CODE_LOCAL_IO,
)


# ═══════════════════════════════════════════════════════════════════════════
# POLICY
# ═══════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class SourcePolicy:
    """Per-source reliability policy.

    Defaults are deliberately conservative: short timeout, a single retry,
    a breaker that opens after three consecutive failures, and a five-minute
    cache TTL. Every field is overridable from the environment so an operator
    can tune a noisy upstream without a code change.
    """

    timeout_s: float = 5.0
    retries: int = 1
    breaker_threshold: int = 3
    breaker_cooldown_s: float = 60.0
    cache_ttl_s: float = 300.0
    max_items: int = 25

    @classmethod
    def from_env(cls) -> "SourcePolicy":
        def _f(name: str, default: float) -> float:
            raw = os.environ.get(name, "")
            try:
                value = float(raw)
            except (TypeError, ValueError):
                return default
            return value if value > 0 else default

        def _i(name: str, default: int) -> int:
            raw = os.environ.get(name, "")
            try:
                value = int(raw)
            except (TypeError, ValueError):
                return default
            return value if value >= 0 else default

        return cls(
            timeout_s=_f("RTA_SOURCE_TIMEOUT_S", cls.timeout_s),
            retries=_i("RTA_SOURCE_RETRIES", cls.retries),
            breaker_threshold=_i("RTA_SOURCE_BREAKER_THRESHOLD",
                                 cls.breaker_threshold),
            breaker_cooldown_s=_f("RTA_SOURCE_BREAKER_COOLDOWN_S",
                                  cls.breaker_cooldown_s),
            cache_ttl_s=_f("RTA_SOURCE_CACHE_TTL_S", cls.cache_ttl_s),
            max_items=_i("RTA_SOURCE_MAX_ITEMS", cls.max_items),
        )


# ═══════════════════════════════════════════════════════════════════════════
# RESULT ENVELOPE
# ═══════════════════════════════════════════════════════════════════════════

def now_iso() -> str:
    """Current UTC time as an ISO-8601 string ending in ``Z``."""
    return (datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"))


def envelope(
    source: str,
    *,
    ok: bool,
    data: Any = None,
    degraded: bool = False,
    cached: bool = False,
    code: Optional[str] = None,
    message: Optional[str] = None,
    retry_after: Optional[float] = None,
    note: Optional[str] = None,
    fetched_at: Optional[str] = None,
) -> dict:
    """Build the stable result envelope both success and failure paths use."""
    error = None
    if code:
        error = {"code": code,
                 "message": "" if message is None else str(message),
                 "retry_after": retry_after}
    return {
        "ok": bool(ok),
        "source": source,
        "data": data,
        "degraded": bool(degraded),
        "cached": bool(cached),
        "fetched_at": fetched_at if (ok or cached) else None,
        "error": error,
        "note": note,
    }


def ok(source: str, data: Any, **kw) -> dict:
    """Success envelope. ``fetched_at`` defaults to now."""
    kw.setdefault("fetched_at", now_iso())
    return envelope(source, ok=True, data=data, **kw)


def fail(source: str, code: str, message: str, **kw) -> dict:
    """Failure envelope. ``degraded`` defaults to ``True``."""
    kw.setdefault("degraded", True)
    return envelope(source, ok=False, code=code, message=message, **kw)


def cached_ok(source: str, data: Any, fetched_at: Optional[str],
              note: str) -> dict:
    """Serve last-known-good data, disclosing that it is cached and stale."""
    return envelope(source, ok=True, data=data, degraded=True, cached=True,
                    fetched_at=fetched_at, note=note)


# ═══════════════════════════════════════════════════════════════════════════
# CIRCUIT BREAKER
# ═══════════════════════════════════════════════════════════════════════════

class CircuitBreaker:
    """In-process breaker: stop hammering an upstream that keeps failing.

    Deliberately not persisted. Process restart resets it, which keeps
    behaviour easy to reason about and keeps the tool free of hidden state.
    """

    def __init__(self, threshold: int = 3, cooldown_s: float = 60.0,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.threshold = max(1, int(threshold))
        self.cooldown_s = max(0.0, float(cooldown_s))
        self._clock = clock
        self._failures = 0
        self._opened_at: Optional[float] = None

    def allow(self) -> bool:
        """True when a request may be attempted."""
        if self._opened_at is None:
            return True
        if (self._clock() - self._opened_at) >= self.cooldown_s:
            # Half-open: allow a single probe and let the result decide.
            self._opened_at = None
            self._failures = 0
            return True
        return False

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self.threshold and self._opened_at is None:
            self._opened_at = self._clock()

    @property
    def is_open(self) -> bool:
        return self._opened_at is not None

    def retry_after(self) -> float:
        """Seconds until the breaker will allow a probe again."""
        if self._opened_at is None:
            return 0.0
        remaining = self.cooldown_s - (self._clock() - self._opened_at)
        return round(max(0.0, remaining), 3)

    def snapshot(self) -> dict:
        return {
            "state": "open" if self.is_open else "closed",
            "consecutive_failures": self._failures,
            "threshold": self.threshold,
            "retry_after_s": self.retry_after(),
        }


# ═══════════════════════════════════════════════════════════════════════════
# DISK CACHE (last-known-good)
# ═══════════════════════════════════════════════════════════════════════════

def default_cache_dir() -> Path:
    """Cache location.

    Kept OUTSIDE the repository by default so a run never leaves untracked
    files in a clean checkout. Override with ``RTA_SOURCE_CACHE_DIR``.
    """
    override = os.environ.get("RTA_SOURCE_CACHE_DIR", "").strip()
    if override:
        return Path(override)
    return Path.home() / ".rta" / "source-cache"


class DiskCache:
    """Tiny JSON file cache keyed by a hash. Best-effort — never raises."""

    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = Path(root) if root is not None else default_cache_dir()

    def _path(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]
        return self.root / f"{digest}.json"

    def get(self, key: str, ttl_s: float) -> Optional[dict]:
        """Return ``{"stored_at": float, "value": Any}`` or ``None``."""
        try:
            raw = json.loads(self._path(key).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if not isinstance(raw, dict) or "value" not in raw:
            return None
        stored_at = raw.get("stored_at")
        if not isinstance(stored_at, (int, float)):
            return None
        # TTL semantics: < 0 always expired, 0 never expires, > 0 expires after
        # that many seconds. ``get_any`` uses 0 to read stale entries.
        if ttl_s < 0:
            return None
        if ttl_s > 0 and (time.time() - float(stored_at)) > ttl_s:
            return None
        return {"stored_at": float(stored_at), "value": raw["value"]}

    def get_any(self, key: str) -> Optional[dict]:
        """Return the entry ignoring TTL (used for stale fallback)."""
        return self.get(key, ttl_s=0.0)

    def set(self, key: str, value: Any) -> None:
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            payload = {"stored_at": time.time(), "value": value}
            tmp = self._path(key).with_suffix(".tmp")
            tmp.write_text(json.dumps(payload, ensure_ascii=False, default=str),
                           encoding="utf-8")
            tmp.replace(self._path(key))
        except OSError:
            return

    def stats(self) -> dict:
        try:
            files = list(self.root.glob("*.json"))
            total = sum(f.stat().st_size for f in files)
        except OSError:
            return {"dir": str(self.root), "entries": 0, "bytes": 0}
        return {"dir": str(self.root), "entries": len(files), "bytes": total}


def iso_from_epoch(epoch: Optional[float]) -> Optional[str]:
    """Convert an epoch timestamp to the envelope's ISO-8601 UTC form."""
    if not isinstance(epoch, (int, float)):
        return None
    return (datetime.fromtimestamp(float(epoch), tz=timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"))


# ═══════════════════════════════════════════════════════════════════════════
# HTTP TRANSPORT
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class HttpResponse:
    """Transport-level response: any HTTP status, raw bytes."""

    status: int
    headers: dict
    body: bytes = b""

    def json(self) -> Any:
        """Parse the body as JSON. Raises ``ValueError`` on malformed input."""
        if not self.body:
            raise ValueError("empty response body")
        return json.loads(self.body.decode("utf-8", errors="replace"))

    def header(self, name: str, default: str = "") -> str:
        lowered = name.lower()
        for key, value in self.headers.items():
            if str(key).lower() == lowered:
                return str(value)
        return default


class TransportError(Exception):
    """Connection-level failure (never an HTTP status).

    ``retryable`` distinguishes "the upstream is having a bad moment" (timeout,
    connection error, 5xx) from "the answer will be identical if we ask again"
    (a malformed body). Only retryable failures are re-attempted.
    """

    def __init__(self, code: str, message: str,
                 retry_after: Optional[float] = None,
                 retryable: bool = True) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retry_after = retry_after
        self.retryable = retryable


class UrllibTransport:
    """``urllib``-based GET transport. Pure standard library.

    HTTP error statuses are returned as ``HttpResponse`` (not raised) so the
    adapter — not the transport — owns the status→code mapping. Only genuine
    connection failures raise ``TransportError``.
    """

    user_agent = "rta-mcp/1.0 (+https://github.com/RAMA-L7/rta-constraint-intelligence)"

    def __init__(self, user_agent: Optional[str] = None) -> None:
        if user_agent:
            self.user_agent = user_agent

    def get(self, url: str, headers: Optional[dict] = None,
            timeout: float = 5.0) -> HttpResponse:
        request = urllib.request.Request(url, method="GET")
        request.add_header("User-Agent", self.user_agent)
        request.add_header("Accept", "application/vnd.github+json, application/json")
        for key, value in (headers or {}).items():
            request.add_header(str(key), str(value))
        try:
            with urllib.request.urlopen(request, timeout=timeout) as resp:
                return HttpResponse(
                    status=int(getattr(resp, "status", 200) or 200),
                    headers=dict(resp.headers.items()),
                    body=resp.read(),
                )
        except urllib.error.HTTPError as err:            # 4xx / 5xx
            try:
                body = err.read()
            except Exception:                            # noqa: BLE001
                body = b""
            return HttpResponse(status=int(err.code or 0),
                                headers=dict((err.headers or {}).items()),
                                body=body)
        except socket.timeout as err:
            raise TransportError(CODE_TIMEOUT, f"timeout after {timeout}s: {err}")
        except urllib.error.URLError as err:
            reason = getattr(err, "reason", err)
            if isinstance(reason, socket.timeout):
                raise TransportError(CODE_TIMEOUT,
                                     f"timeout after {timeout}s: {reason}")
            raise TransportError(CODE_UNAVAILABLE,
                                 f"connection failed: {reason}")
        except OSError as err:
            raise TransportError(CODE_UNAVAILABLE,
                                 f"connection failed: {err}")


def with_retries(fn: Callable[[], Any], policy: SourcePolicy) -> Any:
    """Call ``fn`` once, retrying at most ``policy.retries`` times.

    Retries only failures that can differ on a second attempt: timeouts,
    connection errors and 5xx. A malformed body or an HTTP status the caller
    already classified (403 rate limit, 401 auth) is never retried — retrying
    those burns quota to receive the same answer.
    """
    attempts = max(0, int(policy.retries)) + 1
    last: Optional[TransportError] = None
    for attempt in range(attempts):
        try:
            return fn()
        except TransportError as err:
            last = err
            if not getattr(err, "retryable", True):
                break
            if attempt + 1 >= attempts:
                break
            time.sleep(min(0.5, 0.1 * (attempt + 1)))
    raise last if last is not None else TransportError(CODE_UNAVAILABLE,
                                                       "no attempt made")


def parse_retry_after(value: str) -> Optional[float]:
    """Parse a ``Retry-After`` header (seconds form). ``None`` if unusable."""
    if not value:
        return None
    try:
        seconds = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return seconds if seconds >= 0 else None


def sha256_hex(text: str) -> str:
    """Stable content hash used for cache keys and provenance rows."""
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def redact(text: str, secrets: Optional[list] = None) -> str:
    """Defensively strip anything that looks like a credential from a string.

    Adapters must never place a token in an envelope; this is the last line of
    defence for messages that echo a transport error verbatim.
    """
    out = str(text)
    for secret in (secrets or []):
        if secret and len(str(secret)) >= 8:
            out = out.replace(str(secret), "<redacted>")
    for marker in ("Authorization:", "authorization:", "token=", "api_key="):
        if marker in out:
            head, _, tail = out.partition(marker)
            out = head + marker + "<redacted>" + (" " if tail else "")
    return out
