"""
GitHub issue adapter tests — the failure-classification table in
``rta/sources/github_issues.py`` is the specification these tests pin.

No network is used: a scripted ``FakeTransport`` drives each upstream status,
header set and connection failure.
"""

from __future__ import annotations

import json

import pytest

from rta.sources.base import (
    CODE_AUTH_INVALID,
    CODE_BAD_RESPONSE,
    CODE_BREAKER_OPEN,
    CODE_NOT_FOUND,
    CODE_RATE_LIMITED,
    CODE_TIMEOUT,
    CODE_UNAVAILABLE,
    CircuitBreaker,
    DiskCache,
    SourcePolicy,
)
from rta.sources.github_issues import GithubIssuesAdapter

from tests.source_fakes import (
    FAKE_TOKEN,
    FakeTransport,
    forbidden_response,
    issue,
    json_response,
    rate_limited_response,
    timeout_error,
)


@pytest.fixture
def policy():
    """Deterministic policy: 1 retry, short cooldown, breaker at 2 failures."""
    return SourcePolicy(timeout_s=1.0, retries=1, breaker_threshold=2,
                        breaker_cooldown_s=30.0, cache_ttl_s=300.0,
                        max_items=25)


def make_adapter(transport, policy, tmp_path, token=None, clock=None):
    """Adapter with an injectable clock so retry-after maths is deterministic."""
    now = clock or (lambda: 0.0)
    return GithubIssuesAdapter(
        repo="example/repo",
        token=token,
        transport=transport,
        policy=policy,
        cache=DiskCache(tmp_path),
        breaker=CircuitBreaker(policy.breaker_threshold,
                               policy.breaker_cooldown_s,
                               clock=now),
        now=now,
    )


class TestSuccessPath:
    def test_normalises_items_and_caps_limit(self, tmp_path, policy):
        transport = FakeTransport(json_response(
            [issue(1, "First"), issue(2, "Second"), issue(3, "Third")]))
        result = make_adapter(transport, policy, tmp_path).search(limit=2)
        assert result["ok"] is True
        assert result["data"]["returned"] == 2
        assert [i["number"] for i in result["data"]["issues"]] == [1, 2]
        assert result["data"]["issues"][0]["labels"] == ["bug"]

    def test_excludes_pull_requests_by_default(self, tmp_path, policy):
        transport = FakeTransport(json_response([
            issue(1, "A bug"),
            issue(2, "A PR", pull_request={"url": "x"}),
        ]))
        result = make_adapter(transport, policy, tmp_path).search()
        assert [i["number"] for i in result["data"]["issues"]] == [1]

    def test_include_pull_requests_flag(self, tmp_path, policy):
        transport = FakeTransport(json_response([
            issue(1, "A bug"), issue(2, "A PR", pull_request={"url": "x"})]))
        result = make_adapter(transport, policy, tmp_path).search(
            include_pull_requests=True)
        assert [i["number"] for i in result["data"]["issues"]] == [1, 2]

    def test_anonymous_access_is_disclosed(self, tmp_path, policy):
        transport = FakeTransport(json_response([issue(1, "x")]))
        result = make_adapter(transport, policy, tmp_path).search()
        assert result["data"]["auth_mode"] == "anonymous"
        assert "GITHUB_TOKEN" in (result["note"] or "")

    def test_search_endpoint_used_when_query_present(self, tmp_path, policy):
        transport = FakeTransport(json_response({"items": [issue(7, "hit")]}))
        result = make_adapter(transport, policy, tmp_path).search(query="SDC-005")
        assert "/search/issues?" in transport.calls[0]["url"]
        assert "SDC-005" in transport.calls[0]["url"]
        assert result["data"]["returned"] == 1

    def test_repo_endpoint_used_without_query(self, tmp_path, policy):
        transport = FakeTransport(json_response([issue(7, "hit")]))
        make_adapter(transport, policy, tmp_path).search(state="open")
        assert "/repos/example/repo/issues?" in transport.calls[0]["url"]


class TestFailureClassification:
    def test_rate_limit_maps_to_retry_after_from_reset(self, tmp_path, policy):
        now = {"t": 1_000.0}
        transport = FakeTransport(rate_limited_response(reset_epoch=1_085))
        result = make_adapter(transport, policy, tmp_path,
                              clock=lambda: now["t"]).search()
        assert result["ok"] is False
        assert result["error"]["code"] == CODE_RATE_LIMITED
        assert result["error"]["retry_after"] == 85.0
        assert result["degraded"] is True

    def test_403_without_quota_exhaustion_is_auth_invalid(self, tmp_path, policy):
        transport = FakeTransport(forbidden_response())
        result = make_adapter(transport, policy, tmp_path).search()
        assert result["error"]["code"] == CODE_AUTH_INVALID

    def test_401_is_auth_invalid(self, tmp_path, policy):
        transport = FakeTransport(json_response({"message": "Bad credentials"},
                                                status=401))
        result = make_adapter(transport, policy, tmp_path).search()
        assert result["error"]["code"] == CODE_AUTH_INVALID

    def test_404_is_not_found(self, tmp_path, policy):
        transport = FakeTransport(json_response({"message": "Not Found"},
                                                status=404))
        result = make_adapter(transport, policy, tmp_path).search()
        assert result["error"]["code"] == CODE_NOT_FOUND
        assert "example/repo" in result["error"]["message"]

    def test_422_is_bad_response(self, tmp_path, policy):
        transport = FakeTransport(json_response({"message": "Validation Failed"},
                                                status=422))
        result = make_adapter(transport, policy, tmp_path).search(query="??")
        assert result["error"]["code"] == CODE_BAD_RESPONSE

    def test_500_is_unavailable_and_retried_once(self, tmp_path, policy):
        transport = FakeTransport(json_response({"message": "boom"}, status=500),
                                  json_response({"message": "boom"}, status=503))
        result = make_adapter(transport, policy, tmp_path).search()
        assert result["error"]["code"] == CODE_UNAVAILABLE
        assert len(transport.calls) == 2          # retries=1 → two attempts

    def test_timeout_maps_to_timeout_code(self, tmp_path, policy):
        transport = FakeTransport(timeout_error(), timeout_error())
        result = make_adapter(transport, policy, tmp_path).search()
        assert result["error"]["code"] == CODE_TIMEOUT

    def test_non_json_body_is_bad_response(self, tmp_path, policy):
        from rta.sources.base import HttpResponse
        transport = FakeTransport(HttpResponse(status=200, headers={},
                                               body=b"<html>not json</html>"))
        result = make_adapter(transport, policy, tmp_path).search()
        assert result["error"]["code"] == CODE_BAD_RESPONSE

    def test_adapter_never_raises_on_garbage_transport(self, tmp_path, policy):
        class Exploding:
            def get(self, *a, **kw):
                raise RuntimeError("unexpected")
        # A non-TransportError still surfaces as a failed envelope via the
        # caller's guard, but the adapter itself must not swallow a programming
        # error into a fake success.
        adapter = make_adapter(Exploding(), policy, tmp_path)
        with pytest.raises(RuntimeError):
            adapter.search()


class TestCircuitBreakerIntegration:
    def test_breaker_opens_after_threshold_and_skips_network(self, tmp_path, policy):
        transport = FakeTransport(json_response({}, status=500),
                                  json_response({}, status=500),
                                  json_response({}, status=500))
        adapter = make_adapter(transport, policy, tmp_path,
                               clock=lambda: 0.0)
        adapter.search()                       # failure 1 (2 attempts)
        adapter.search()                       # failure 2 → breaker opens
        assert adapter.breaker.is_open is True
        calls_before = len(transport.calls)
        result = adapter.search()
        assert result["error"]["code"] == CODE_BREAKER_OPEN
        assert len(transport.calls) == calls_before     # no further network
        assert result["error"]["retry_after"] == 30.0

    def test_auth_failure_does_not_trip_breaker(self, tmp_path, policy):
        transport = FakeTransport(forbidden_response(), forbidden_response(),
                                  forbidden_response())
        adapter = make_adapter(transport, policy, tmp_path)
        for _ in range(3):
            adapter.search()
        assert adapter.breaker.is_open is False
        assert adapter.health()["breaker"]["state"] == "closed"

    def test_health_reports_breaker_and_auth_mode(self, tmp_path, policy):
        adapter = make_adapter(FakeTransport(), policy, tmp_path)
        health = adapter.health()
        assert health["auth_mode"] == "anonymous"
        assert health["requires_credential"] is False
        assert health["breaker"]["state"] == "closed"


class TestCacheFallback:
    def test_stale_cache_served_and_flagged_on_failure(self, tmp_path, policy):
        transport = FakeTransport(json_response([issue(1, "cached issue")]),
                                  json_response({}, status=500),
                                  json_response({}, status=500))
        adapter = make_adapter(transport, policy, tmp_path, clock=lambda: 0.0)
        first = adapter.search()
        assert first["cached"] is False
        adapter.breaker.record_success()
        second = adapter.search()
        assert second["ok"] is True
        assert second["cached"] is True
        assert second["degraded"] is True
        assert second["data"]["issues"][0]["title"] == "cached issue"
        assert second["fetched_at"] is not None

    def test_no_cache_means_plain_failure(self, tmp_path, policy):
        transport = FakeTransport(json_response({}, status=500),
                                  json_response({}, status=500))
        adapter = make_adapter(transport, policy, tmp_path)
        result = adapter.search()
        assert result["ok"] is False
        assert result["data"] is None


class TestSecretSafety:
    def test_token_is_sent_as_header_but_never_returned(self, tmp_path, policy):
        transport = FakeTransport(json_response([issue(1, "x")]))
        adapter = make_adapter(transport, policy, tmp_path, token=FAKE_TOKEN)
        result = adapter.search()
        assert transport.last_headers["Authorization"] == f"Bearer {FAKE_TOKEN}"
        blob = json.dumps(result)
        assert FAKE_TOKEN not in blob
        assert "Bearer" not in blob
        assert result["data"]["auth_mode"] == "token"

    def test_failure_envelope_never_contains_token(self, tmp_path, policy):
        transport = FakeTransport(forbidden_response())
        adapter = make_adapter(transport, policy, tmp_path, token=FAKE_TOKEN)
        blob = json.dumps(adapter.search())
        assert FAKE_TOKEN not in blob

    def test_health_never_contains_token(self, tmp_path, policy):
        adapter = make_adapter(FakeTransport(), policy, tmp_path,
                               token=FAKE_TOKEN)
        assert FAKE_TOKEN not in json.dumps(adapter.health())

    def test_token_resolution_prefers_environment(self, tmp_path, policy,
                                                  monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", FAKE_TOKEN)
        adapter = make_adapter(FakeTransport(), policy, tmp_path)
        token, source = adapter.token()
        assert token == FAKE_TOKEN
        assert source == "GITHUB_TOKEN"
