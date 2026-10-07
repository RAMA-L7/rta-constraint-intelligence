"""
Ṛta — GitHub issue-tracker adapter (structured, action-capable source).

Answers "has this already been reported?" before an engineer re-debugs a
constraint problem from scratch. It is the one source here that exercises real
third-party behaviour: real authentication, real pagination, real rate limits,
and real inconsistent responses.

Credential handling: the token is read from ``GITHUB_TOKEN`` (or the legacy
``GH_TOKEN``) at call time, sent only as an ``Authorization`` header, and
**never** logged, cached, or included in a result envelope. Anonymous access
works too — GitHub allows a small unauthenticated quota, which the adapter
reports through ``note`` and ``health()`` so a low-quota run is never mistaken
for a broken integration.

Failure classification (mirrors the failure matrix in
``docs/features/README-18-mcp-multi-source.md``):

| Upstream | Code returned | Trips breaker? | Retryable |
|---|---|---|---|
| timeout / connection error | ``TIMEOUT`` / ``UNAVAILABLE`` | yes | yes (once) |
| 401, 403 without quota exhausted | ``AUTH_INVALID`` | no | no |
| 403/429 with ``x-ratelimit-remaining: 0`` | ``RATE_LIMITED`` | no | after reset |
| 404 | ``NOT_FOUND`` | no | no |
| 422 | ``BAD_RESPONSE`` | no | no |
| 5xx | ``UNAVAILABLE`` | yes | yes (once) |

Authentication and quota failures deliberately do **not** trip the breaker: a
missing token is a configuration fact, not an upstream outage, and opening the
breaker would hide the real cause behind a ``BREAKER_OPEN`` code.
"""

from __future__ import annotations

import os
import time
from typing import Optional

from rta.sources.base import (
    CODE_AUTH_INVALID,
    CODE_BAD_RESPONSE,
    CODE_BREAKER_OPEN,
    CODE_NOT_FOUND,
    CODE_RATE_LIMITED,
    CODE_UNAVAILABLE,
    CircuitBreaker,
    DiskCache,
    SourcePolicy,
    TransportError,
    UrllibTransport,
    cached_ok,
    fail,
    iso_from_epoch,
    ok,
    parse_retry_after,
    redact,
    with_retries,
)

SOURCE_NAME = "github"

API_BASE = "https://api.github.com"

#: Default target — the issue tracker of the Ṛta repository itself.
DEFAULT_REPO = "RAMA-L7/rta-constraint-intelligence"

#: Failure codes that indicate upstream ill-health (as opposed to misconfig).
BREAKER_CODES = (CODE_UNAVAILABLE, CODE_BAD_RESPONSE)

TOKEN_ENV_VARS = ("GITHUB_TOKEN", "GH_TOKEN", "RTA_GITHUB_TOKEN")


def resolve_token() -> tuple:
    """Return ``(token, env_var_name)``. Never returns a token in a message."""
    for name in TOKEN_ENV_VARS:
        value = os.environ.get(name, "").strip()
        if value:
            return value, name
    return "", ""


class GithubIssuesAdapter:
    """Read-only view of a GitHub repository's issues."""

    name = SOURCE_NAME

    def __init__(self, repo: str = DEFAULT_REPO,
                 token: Optional[str] = None,
                 transport=None,
                 policy: Optional[SourcePolicy] = None,
                 cache: Optional[DiskCache] = None,
                 breaker: Optional[CircuitBreaker] = None,
                 now=time.time) -> None:
        self.repo = str(repo or DEFAULT_REPO)
        self._token_override = token
        self.transport = transport if transport is not None else UrllibTransport()
        self.policy = policy or SourcePolicy.from_env()
        self.cache = cache if cache is not None else DiskCache()
        self.breaker = breaker if breaker is not None else CircuitBreaker(
            self.policy.breaker_threshold, self.policy.breaker_cooldown_s)
        self._now = now

    # ── credentials ────────────────────────────────────────────────────────

    def token(self) -> tuple:
        if self._token_override:
            return str(self._token_override), "constructor"
        return resolve_token()

    # ── health (never touches the network) ─────────────────────────────────

    def health(self) -> dict:
        token, source_name = self.token()
        return {
            "source": self.name,
            "kind": "github-issues",
            "repo": self.repo,
            "requires_network": True,
            "requires_credential": False,
            "auth_mode": "token" if token else "anonymous",
            "auth_env_var": source_name or None,
            "timeout_s": self.policy.timeout_s,
            "breaker": self.breaker.snapshot(),
            "cache": self.cache.stats(),
            "last_error": getattr(self, "_last_error", None),
        }

    # ── request plumbing ───────────────────────────────────────────────────

    def _url(self, state: str, labels: str, query: str, limit: int) -> str:
        per_page = max(1, min(int(limit or 10), self.policy.max_items))
        if query:
            from urllib.parse import quote_plus
            terms = f"repo:{self.repo} {query}".strip()
            if state:
                terms += f" state:{state}"
            if labels:
                for label in labels.split(","):
                    if label.strip():
                        terms += f' label:"{label.strip()}"'
            return (f"{API_BASE}/search/issues?q={quote_plus(terms)}"
                    f"&per_page={per_page}&sort=updated&order=desc")
        params = [f"per_page={per_page}", "sort=updated", "direction=desc",
                  "state=" + (state or "open")]
        if labels:
            params.append("labels=" + labels)
        return f"{API_BASE}/repos/{self.repo}/issues?" + "&".join(params)

    def _call_api(self, url: str, token: str) -> tuple:
        """One HTTP attempt. Returns ``(status, headers, payload_or_none)``."""
        headers = {"Accept": "application/vnd.github+json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        response = self.transport.get(url, headers=headers,
                                      timeout=self.policy.timeout_s)
        # 5xx is raised as a retryable transport failure so the shared retry
        # policy handles it in one place. Never retried: a malformed body.
        if response.status >= 500:
            raise TransportError(CODE_UNAVAILABLE,
                                 f"GitHub returned HTTP {response.status}")
        payload = None
        if response.status < 400:
            try:
                payload = response.json()
            except ValueError:
                raise TransportError(
                    CODE_BAD_RESPONSE,
                    "upstream returned a non-JSON body",
                    retryable=False)
        return response.status, response.headers, payload

    def _classify(self, status: int, headers: dict) -> tuple:
        """Map a non-2xx status to ``(code, message, retry_after)``."""
        remaining = str(headers.get("x-ratelimit-remaining", "")
                        if hasattr(headers, "get") else "")
        reset = str(headers.get("x-ratelimit-reset", "")
                    if hasattr(headers, "get") else "")
        retry_after = parse_retry_after(str(headers.get("retry-after", "")
                                            if hasattr(headers, "get") else ""))
        if status in (403, 429):
            if remaining.strip() == "0" or status == 429:
                if retry_after is None and reset.strip():
                    try:
                        retry_after = max(0.0, float(reset) - self._now())
                    except (TypeError, ValueError):
                        retry_after = None
                return (CODE_RATE_LIMITED,
                        "GitHub rate limit exhausted for this credential/IP",
                        retry_after)
            return (CODE_AUTH_INVALID,
                    "GitHub rejected the credential (403 without quota exhaustion)",
                    None)
        if status == 401:
            return (CODE_AUTH_INVALID, "GitHub rejected the credential (401)", None)
        if status == 404:
            return (CODE_NOT_FOUND,
                    f"repository not found or not visible: {self.repo}", None)
        if status == 422:
            return (CODE_BAD_RESPONSE,
                    "GitHub rejected the query (422) — check the search terms",
                    None)
        if status >= 500:
            return (CODE_UNAVAILABLE, f"GitHub returned HTTP {status}", None)
        return (CODE_UNAVAILABLE, f"unexpected GitHub status {status}", None)

    # ── normalisation ──────────────────────────────────────────────────────

    @staticmethod
    def _items(payload) -> list:
        if isinstance(payload, dict):
            items = payload.get("items")
            return items if isinstance(items, list) else []
        if isinstance(payload, list):
            return payload
        return []

    @staticmethod
    def _normalise(item: dict) -> dict:
        labels = []
        for label in item.get("labels") or []:
            if isinstance(label, dict) and label.get("name"):
                labels.append(str(label["name"]))
            elif isinstance(label, str):
                labels.append(label)
        return {
            "number": item.get("number"),
            "title": str(item.get("title") or "")[:200],
            "state": item.get("state"),
            "labels": labels,
            "url": item.get("html_url"),
            "updated_at": item.get("updated_at"),
            "comments": item.get("comments"),
            "is_pull_request": bool(item.get("pull_request")),
        }

    # ── search ─────────────────────────────────────────────────────────────

    def search(self, query: str = "", state: str = "open", labels: str = "",
               limit: int = 10, include_pull_requests: bool = False) -> dict:
        """Search issues. Never raises — see the module failure table."""
        token, token_source = self.token()
        cache_key = (f"github:{self.repo}:{state}:{labels}:{query}:"
                     f"{int(limit or 10)}:{bool(include_pull_requests)}")

        if not self.breaker.allow():
            stale = self.cache.get_any(cache_key)
            if stale is not None:
                return cached_ok(
                    SOURCE_NAME, stale["value"],
                    iso_from_epoch(stale["stored_at"]),
                    "circuit breaker open — serving last-known-good result")
            return fail(SOURCE_NAME, CODE_BREAKER_OPEN,
                        "circuit breaker open after repeated upstream failures",
                        retry_after=self.breaker.retry_after(),
                        note="health() reports the breaker state; no network call made")

        url = self._url(state, labels, query, limit)
        try:
            status, headers, payload = with_retries(
                lambda: self._call_api(url, token), self.policy)
        except TransportError as err:
            code = err.code
            if code in BREAKER_CODES:
                self.breaker.record_failure()
            self._last_error = code
            stale = self.cache.get_any(cache_key)
            if stale is not None:
                return cached_ok(
                    SOURCE_NAME, stale["value"],
                    iso_from_epoch(stale["stored_at"]),
                    f"{code} — serving last-known-good result "
                    f"({err.message})")
            return fail(SOURCE_NAME, code, err.message,
                        retry_after=err.retry_after,
                        note=f"repo={self.repo} auth={token_source or 'anonymous'}")

        if status >= 400:
            code, message, retry_after = self._classify(status, headers)
            if code in BREAKER_CODES:
                self.breaker.record_failure()
            self._last_error = code
            stale = self.cache.get_any(cache_key)
            if stale is not None:
                return cached_ok(SOURCE_NAME, stale["value"],
                                 iso_from_epoch(stale["stored_at"]),
                                 f"{code} — serving last-known-good result")
            return fail(SOURCE_NAME, code, message, retry_after=retry_after,
                        note=f"repo={self.repo} auth={token_source or 'anonymous'}")

        self.breaker.record_success()
        raw_items = self._items(payload)
        items = [self._normalise(i) for i in raw_items if isinstance(i, dict)]
        if not include_pull_requests:
            items = [i for i in items if not i["is_pull_request"]]
        items = items[:max(1, min(int(limit or 10), self.policy.max_items))]

        data = {
            "repo": self.repo,
            "query": query,
            "state": state,
            "labels": labels,
            "issues": items,
            "returned": len(items),
            "auth_mode": "token" if token else "anonymous",
        }
        self.cache.set(cache_key, data)
        note = None
        if not token:
            note = ("anonymous GitHub access — the unauthenticated quota is "
                    "small and shared; set GITHUB_TOKEN for reliable results")
        return ok(SOURCE_NAME, data, note=note)

    # ── references (used by the composite tool) ────────────────────────────

    def references(self, terms: Optional[list] = None, limit: int = 3) -> dict:
        """Search using engine-derived terms; returns the raw envelope."""
        query = " ".join(terms or [])
        return self.search(query=query, state="open", limit=limit)


def redact_transport_message(message: str, token: str = "") -> str:
    """Public helper so callers can sanitise before display."""
    return redact(message, [token] if token else [])
