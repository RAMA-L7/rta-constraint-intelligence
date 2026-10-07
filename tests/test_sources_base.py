"""
Contract tests for the source adapter base layer (``rta/sources/base.py``).

These pin the envelope shape, the circuit breaker, the disk cache and the
credential-redaction helper. If any of these change, the MCP response contract
documented in ``docs/features/README-18-mcp-multi-source.md`` changes with it.
"""

from __future__ import annotations

import json

from rta.sources.base import (
    ERROR_CODES,
    CODE_UNAVAILABLE,
    CircuitBreaker,
    DiskCache,
    SourcePolicy,
    TransportError,
    cached_ok,
    fail,
    iso_from_epoch,
    ok,
    parse_retry_after,
    redact,
    sha256_hex,
)

ENVELOPE_KEYS = {"ok", "source", "data", "degraded", "cached", "fetched_at",
                 "error", "note"}


class TestEnvelope:
    def test_ok_envelope_shape(self):
        result = ok("corpus", {"a": 1})
        assert set(result) == ENVELOPE_KEYS
        assert result["ok"] is True
        assert result["degraded"] is False
        assert result["cached"] is False
        assert result["error"] is None
        assert result["fetched_at"].endswith("Z")

    def test_fail_envelope_defaults_to_degraded(self):
        result = fail("github", CODE_UNAVAILABLE, "boom")
        assert result["ok"] is False
        assert result["degraded"] is True
        assert result["fetched_at"] is None
        assert result["error"]["code"] == CODE_UNAVAILABLE
        assert result["error"]["message"] == "boom"
        assert result["error"]["retry_after"] is None

    def test_cached_ok_is_degraded_and_flagged(self):
        result = cached_ok("github", {"issues": []}, "2026-10-01T00:00:00Z",
                           "serving last-known-good")
        assert result["ok"] is True
        assert result["cached"] is True
        assert result["degraded"] is True
        assert result["fetched_at"] == "2026-10-01T00:00:00Z"
        assert "last-known-good" in result["note"]

    def test_envelope_is_json_serialisable(self):
        payload = fail("store", "LOCAL_IO", "db locked", retry_after=1.5)
        assert json.loads(json.dumps(payload))["error"]["retry_after"] == 1.5

    def test_error_codes_are_unique_strings(self):
        assert len(set(ERROR_CODES)) == len(ERROR_CODES)
        assert all(isinstance(code, str) and code for code in ERROR_CODES)


class TestCircuitBreaker:
    def test_closed_until_threshold(self):
        breaker = CircuitBreaker(threshold=3, cooldown_s=60.0, clock=lambda: 0.0)
        assert breaker.allow() is True
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.allow() is True           # two failures < threshold
        breaker.record_failure()
        assert breaker.is_open is True
        assert breaker.allow() is False
        assert breaker.retry_after() == 60.0

    def test_success_resets_failure_count(self):
        breaker = CircuitBreaker(threshold=2, cooldown_s=60.0, clock=lambda: 0.0)
        breaker.record_failure()
        breaker.record_success()
        breaker.record_failure()
        assert breaker.allow() is True

    def test_half_open_after_cooldown(self):
        now = {"t": 100.0}
        breaker = CircuitBreaker(threshold=1, cooldown_s=30.0,
                                 clock=lambda: now["t"])
        breaker.record_failure()
        assert breaker.allow() is False
        now["t"] = 129.9
        assert breaker.allow() is False
        now["t"] = 130.0
        assert breaker.allow() is True           # probe allowed again

    def test_snapshot_shape(self):
        breaker = CircuitBreaker(threshold=2, cooldown_s=5.0, clock=lambda: 0.0)
        breaker.record_failure()
        snap = breaker.snapshot()
        assert snap["state"] == "closed"
        assert snap["consecutive_failures"] == 1
        assert snap["threshold"] == 2


class TestDiskCache:
    def test_set_get_roundtrip(self, tmp_path):
        cache = DiskCache(tmp_path)
        cache.set("k", {"value": 1})
        assert cache.get("k", ttl_s=60)["value"] == {"value": 1}

    def test_ttl_expiry_and_get_any(self, tmp_path):
        cache = DiskCache(tmp_path)
        cache.set("k", {"value": 1})
        assert cache.get("k", ttl_s=-1) is None      # nothing survives -1s TTL
        assert cache.get_any("k") is not None        # stale read still works

    def test_missing_key_is_none(self, tmp_path):
        assert DiskCache(tmp_path).get("absent", ttl_s=60) is None

    def test_corrupt_entry_is_ignored(self, tmp_path):
        cache = DiskCache(tmp_path)
        cache.set("k", 1)
        for path in tmp_path.glob("*.json"):
            path.write_text("{not json", encoding="utf-8")
        assert cache.get("k", ttl_s=60) is None

    def test_stats_counts_entries(self, tmp_path):
        cache = DiskCache(tmp_path)
        cache.set("a", 1)
        assert cache.stats()["entries"] == 1


class TestPolicy:
    def test_from_env_overrides_and_falls_back(self, monkeypatch):
        monkeypatch.setenv("RTA_SOURCE_TIMEOUT_S", "12.5")
        monkeypatch.setenv("RTA_SOURCE_RETRIES", "0")
        policy = SourcePolicy.from_env()
        assert policy.timeout_s == 12.5
        assert policy.retries == 0

    def test_garbage_env_falls_back_to_defaults(self, monkeypatch):
        monkeypatch.setenv("RTA_SOURCE_TIMEOUT_S", "not-a-number")
        monkeypatch.setenv("RTA_SOURCE_RETRIES", "-4")
        policy = SourcePolicy.from_env()
        assert policy.timeout_s == SourcePolicy.timeout_s
        assert policy.retries == SourcePolicy.retries


class TestHelpers:
    def test_parse_retry_after(self):
        assert parse_retry_after("120") == 120.0
        assert parse_retry_after("") is None
        assert parse_retry_after("Wed, 21 Oct 2015 07:28:00 GMT") is None
        assert parse_retry_after("-3") is None

    def test_iso_from_epoch(self):
        assert iso_from_epoch(0) == "1970-01-01T00:00:00Z"
        assert iso_from_epoch(None) is None
        assert iso_from_epoch("nope") is None

    def test_sha256_is_stable(self):
        assert sha256_hex("abc") == sha256_hex("abc")
        assert sha256_hex("abc") != sha256_hex("abd")

    def test_redact_removes_secrets_and_headers(self):
        secret = "ghp_abcdefghijklmnopqrst"
        text = f"failed with Authorization: Bearer {secret} token={secret}"
        cleaned = redact(text, [secret])
        assert secret not in cleaned
        assert "<redacted>" in cleaned

    def test_transport_error_carries_code(self):
        err = TransportError(CODE_UNAVAILABLE, "nope", retry_after=2.0)
        assert err.code == CODE_UNAVAILABLE
        assert err.retry_after == 2.0
