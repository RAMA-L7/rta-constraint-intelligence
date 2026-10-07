"""
Shared fakes for the source-adapter tests.

Nothing in the test suite may touch the network. Adapters accept an injected
transport, so these fakes let a test drive an exact upstream status, header set
or connection failure and assert the resulting envelope.
"""

from __future__ import annotations

import json

from rta.sources.base import (
    CODE_TIMEOUT,
    CODE_UNAVAILABLE,
    HttpResponse,
    TransportError,
)

FAKE_TOKEN = "ghp_TEST_TOKEN_SHOULD_NEVER_APPEAR_0000000000"


def json_response(payload, status: int = 200, headers: dict = None) -> HttpResponse:
    return HttpResponse(status=status,
                        headers=dict(headers or {}),
                        body=json.dumps(payload).encode("utf-8"))


class FakeTransport:
    """Scripted transport: returns or raises whatever the test queued."""

    def __init__(self, *responses) -> None:
        self._queue = list(responses)
        self.calls = []

    def push(self, *responses) -> "FakeTransport":
        self._queue.extend(responses)
        return self

    def get(self, url, headers=None, timeout=5.0) -> HttpResponse:
        self.calls.append({"url": url, "headers": dict(headers or {}),
                           "timeout": timeout})
        if not self._queue:
            raise TransportError(CODE_UNAVAILABLE, "fake transport exhausted")
        item = self._queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    @property
    def last_headers(self) -> dict:
        return self.calls[-1]["headers"] if self.calls else {}


def rate_limited_response(reset_epoch: int) -> HttpResponse:
    return json_response(
        {"message": "API rate limit exceeded"},
        status=403,
        headers={"x-ratelimit-remaining": "0",
                 "x-ratelimit-reset": str(reset_epoch)})


def forbidden_response() -> HttpResponse:
    return json_response(
        {"message": "Resource not accessible by integration"},
        status=403,
        headers={"x-ratelimit-remaining": "57"})


def issue(number: int, title: str, **overrides) -> dict:
    payload = {
        "number": number,
        "title": title,
        "state": "open",
        "labels": [{"name": "bug"}],
        "html_url": f"https://github.com/example/repo/issues/{number}",
        "updated_at": "2026-10-01T00:00:00Z",
        "comments": 2,
    }
    payload.update(overrides)
    return payload


def timeout_error() -> TransportError:
    return TransportError(CODE_TIMEOUT, "timeout after 5.0s")
