"""
Ṛta — advisory context sources.

Three adapters sit behind one contract (see ``base.py``):

* ``corpus``  — local documentation corpus (no network, no credential)
* ``github``  — GitHub issue tracker (network, optional credential)
* ``store``   — owned SQLite store: runs, findings, provenance, audit trail

They are **advisory only**. Verdicts (READY / NOT_READY, blocker counts,
readiness scores) come exclusively from the frozen deterministic engine in
``rta/api/api_server.py``. Sources supply context, provenance and history —
never authority.

Adapters are constructed lazily and re-used per process so the breaker and
cache state stay coherent across calls within one MCP session.
"""

from __future__ import annotations

import os
from typing import Optional

from rta.sources.base import (  # noqa: F401 - re-exported for callers
    CircuitBreaker,
    DiskCache,
    SourcePolicy,
    TransportError,
    UrllibTransport,
    ERROR_CODES,
)
from rta.sources.corpus import CorpusAdapter
from rta.sources.github_issues import DEFAULT_REPO, GithubIssuesAdapter
from rta.sources.store import StoreAdapter, new_run_id  # noqa: F401

__all__ = [
    "SOURCE_NAMES",
    "SOURCE_ROLES",
    "CorpusAdapter",
    "GithubIssuesAdapter",
    "StoreAdapter",
    "build_sources",
    "get_sources",
    "health_all",
    "reset_sources",
    "new_run_id",
]

#: Adapter keys, in report order.
SOURCE_NAMES = ("corpus", "github", "store")

#: Human-readable description of what each source contributes.
SOURCE_ROLES = {
    "corpus": "documentation and sample knowledge (local, deterministic)",
    "github": "upstream issue tracker (reported bugs, open work)",
    "store": "recorded runs, findings and provenance you control",
}

_SOURCES: Optional[dict] = None


def _github_repo() -> str:
    return os.environ.get("RTA_GITHUB_REPO", "").strip() or DEFAULT_REPO


def build_sources(policy: Optional[SourcePolicy] = None,
                  cache: Optional[DiskCache] = None) -> dict:
    """Construct the adapter set. No network access happens here."""
    policy = policy or SourcePolicy.from_env()
    cache = cache if cache is not None else DiskCache()
    return {
        "corpus": CorpusAdapter(policy=policy, cache=cache),
        "github": GithubIssuesAdapter(repo=_github_repo(), policy=policy,
                                      cache=cache),
        "store": StoreAdapter(),
        "policy": policy,
        "cache": cache,
    }


def get_sources(refresh: bool = False) -> dict:
    """Process-wide adapter registry (keeps breaker/cache state coherent)."""
    global _SOURCES
    if _SOURCES is None or refresh:
        _SOURCES = build_sources()
    return _SOURCES


def reset_sources() -> None:
    """Drop the registry — used by tests to isolate breaker/cache state."""
    global _SOURCES
    _SOURCES = None


def health_all() -> dict:
    """Aggregate health for every adapter. Never performs a network call."""
    sources = get_sources()
    report = {}
    for name in SOURCE_NAMES:
        adapter = sources.get(name)
        try:
            report[name] = adapter.health()
        except Exception as err:                     # noqa: BLE001 - diagnostics
            report[name] = {
                "source": name,
                "status": "error",
                "last_error": f"{type(err).__name__}: {err}",
            }
    cache_stats = sources["cache"].stats()
    return {
        "sources": report,
        "roles": dict(SOURCE_ROLES),
        "cache": cache_stats,
        "policy": {
            "timeout_s": sources["policy"].timeout_s,
            "retries": sources["policy"].retries,
            "breaker_threshold": sources["policy"].breaker_threshold,
            "breaker_cooldown_s": sources["policy"].breaker_cooldown_s,
            "cache_ttl_s": sources["policy"].cache_ttl_s,
            "max_items": sources["policy"].max_items,
        },
        "network_used": False,
        "authority_note": (
            "Sources are advisory. Verdicts come only from the deterministic "
            "Ṛta engine."
        ),
    }
