"""
MCP multi-source integration tests (``rta/api/mcp_server.py``).

Four properties are pinned here:

1. **The engine contract is frozen** — the eight engine tools keep their names,
   order and required parameters, and each still returns byte-identical output
   to a direct ``rta/api/api_server`` call.
2. **Sources are advisory** — ``rta_investigate`` returns the engine payload
   verbatim, and a failing source changes only the ``context`` block and the
   ``degraded`` flag, never the verdict.
3. **The capability boundary holds** — a denied tool returns ``FORBIDDEN`` and
   never reaches its implementation.
4. **Every call is audited** — including denied ones, storing digests only.

No test in this file touches the network.
"""

from __future__ import annotations

import json

import pytest

from rta.api import mcp_server as M
from rta.api.api_server import analyze, lint_sdc_json, rules_json
from rta.sources import get_sources, reset_sources
from rta.sources.base import CircuitBreaker, DiskCache, SourcePolicy
from rta.sources.github_issues import GithubIssuesAdapter
from rta.sources.store import StoreAdapter

from tests.source_fakes import FakeTransport, json_response

MINIMAL_SDC = ("set sdc_version 2.2\n"
               "create_clock -name clk -period 5.0 [get_ports clk]\n")

ENGINE_TOOL_NAMES = [
    "rta_analyze", "rta_lint", "rta_convert", "rta_generate",
    "rta_snapshot", "rta_diff", "rta_corners", "rta_rules",
]

SOURCE_TOOL_NAMES = [
    "rta_sources_health", "rta_source_docs_search", "rta_source_issues_search",
    "rta_source_store_query", "rta_source_store_record", "rta_investigate",
]

ENGINE_REQUIRED = {
    "rta_analyze": ["sdc"],
    "rta_lint": ["sdc"],
    "rta_convert": ["sdc"],
    "rta_generate": [],
    "rta_snapshot": ["sdc"],
    "rta_diff": ["v1", "v2"],
    "rta_corners": ["corners"],
    "rta_rules": [],
}


# ── harness ────────────────────────────────────────────────────────────────────

def tools_list():
    resp = M.handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    return resp["result"]["tools"]


def call_raw(name, args=None):
    return M.handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                             "params": {"name": name,
                                        "arguments": args or {}}})


def call(name, args=None):
    resp = call_raw(name, args)
    if "error" in resp:
        return {"rpc_error": resp["error"]}
    payload = json.loads(resp["result"]["content"][0]["text"])
    if resp["result"].get("isError"):
        payload["_isError"] = True
    return payload


def install_github(tmp_path, responses) -> FakeTransport:
    """Replace the registry's GitHub adapter with a scripted one.

    Tests must never reach api.github.com: the adapter is injected instead, so
    success, rate limiting and outages are all deterministic.
    """
    transport = FakeTransport(*responses)
    policy = SourcePolicy(timeout_s=1.0, retries=0, breaker_threshold=99,
                          breaker_cooldown_s=1.0, cache_ttl_s=1.0)
    get_sources()["github"] = GithubIssuesAdapter(
        repo="example/repo", transport=transport, policy=policy,
        cache=DiskCache(tmp_path / "cache-gh"),
        breaker=CircuitBreaker(99, 1.0))
    return transport


def install_failing_github(tmp_path, status=500) -> FakeTransport:
    """Upstream that always fails (no cache, so no fallback is available)."""
    return install_github(tmp_path, [json_response({}, status=status)] * 4)


def install_healthy_github(tmp_path) -> FakeTransport:
    """Upstream that answers with an empty, well-formed issue list."""
    return install_github(tmp_path, [json_response([])] * 4)


@pytest.fixture(autouse=True)
def isolated_runtime(tmp_path, monkeypatch):
    """Temp store/cache, neutral role, and a scripted (offline) GitHub source."""
    monkeypatch.setenv("RTA_STORE_DB", str(tmp_path / "store.db"))
    monkeypatch.setenv("RTA_SOURCE_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.delenv("RTA_MCP_ROLE", raising=False)
    monkeypatch.delenv("RTA_MCP_ALLOW_MUTATIONS", raising=False)
    reset_sources()
    install_healthy_github(tmp_path)
    yield
    reset_sources()


# ── 1. frozen engine contract ──────────────────────────────────────────────────

class TestEngineContractFrozen:
    def test_engine_tools_are_first_and_unchanged(self):
        names = [t["name"] for t in tools_list()]
        assert names[:8] == ENGINE_TOOL_NAMES

    def test_engine_tool_required_params_unchanged(self):
        by_name = {t["name"]: t for t in tools_list()}
        for name, required in ENGINE_REQUIRED.items():
            schema = by_name[name]["inputSchema"]
            assert schema.get("required", []) == required, name

    def test_engine_tools_still_have_descriptions(self):
        for tool in tools_list()[:8]:
            assert tool["description"].strip()

    def test_source_tools_are_appended_after_engine_tools(self):
        names = [t["name"] for t in tools_list()]
        assert names[8:] == SOURCE_TOOL_NAMES
        assert len(names) == 14

    @pytest.mark.parametrize("tool,args,impl", [
        ("rta_analyze", {"sdc": MINIMAL_SDC},
         lambda: analyze(sdc_text=MINIMAL_SDC)),
        ("rta_lint", {"sdc": MINIMAL_SDC},
         lambda: lint_sdc_json(MINIMAL_SDC, fix=True)),
        ("rta_rules", {}, rules_json),
        ("rta_snapshot", {"sdc": MINIMAL_SDC},
         lambda: __import__("rta.api.api_server", fromlist=["x"])
         .snapshot_sdc_json(MINIMAL_SDC)),
    ])
    def test_engine_tool_output_matches_direct_api(self, tool, args, impl):
        via_mcp = call(tool, args)
        direct = impl()
        assert json.dumps(via_mcp, sort_keys=True, default=str) == \
            json.dumps(direct, sort_keys=True, default=str)


# ── 2. sources are advisory ────────────────────────────────────────────────────

class TestInvestigateComposite:
    @pytest.fixture(autouse=True)
    def _engineer(self, monkeypatch):
        # rta_investigate reaches the network, so the access matrix puts it
        # behind the engineer role. Gating itself is covered separately.
        monkeypatch.setenv("RTA_MCP_ROLE", "engineer")

    def test_returns_engine_payload_verbatim(self):
        via_mcp = call("rta_investigate", {"sdc": MINIMAL_SDC,
                                           "context_limit": 1,
                                           "issue_limit": 1})
        direct = analyze(sdc_text=MINIMAL_SDC)
        assert via_mcp["authority"] == "engine"
        assert json.dumps(via_mcp["engine"], sort_keys=True, default=str) == \
            json.dumps(direct, sort_keys=True, default=str)

    def test_verdict_is_engine_derived(self):
        payload = call("rta_investigate", {"sdc": MINIMAL_SDC,
                                           "context_limit": 1})
        assert payload["engine_facts"]["verdict"] == \
            payload["engine"]["readiness"]["overall"]

    def test_corpus_context_is_present_and_local(self):
        payload = call("rta_investigate", {"sdc": MINIMAL_SDC,
                                           "context_limit": 2})
        docs = payload["context"]["docs"]
        assert docs["ok"] is True
        assert docs["source"] == "corpus"
        assert "corpus" in payload["sources_used"]

    def test_context_has_no_verdict_channel(self):
        payload = call("rta_investigate", {"sdc": MINIMAL_SDC,
                                           "context_limit": 1,
                                           "issue_limit": 1})
        # The context block carries references only. There is no field through
        # which a source could assert or override a verdict.
        assert set(payload["context"]) == {"docs", "issues"}
        assert payload["engine_facts"]["verdict"] == \
            payload["engine"]["readiness"]["overall"]

    def test_missing_sdc_is_rejected_before_engine_runs(self):
        payload = call("rta_investigate", {})
        assert payload.get("error")
        assert payload.get("code")

    def test_degraded_composite_still_returns_engine_and_docs(self, tmp_path):
        install_failing_github(tmp_path)
        payload = call("rta_investigate", {"sdc": MINIMAL_SDC,
                                           "context_limit": 1,
                                           "issue_limit": 1})
        assert payload["authority"] == "engine"
        assert payload["degraded"] is True
        assert payload["context"]["issues"]["ok"] is False
        assert payload["context"]["docs"]["ok"] is True
        assert json.dumps(payload["engine"], sort_keys=True, default=str) == \
            json.dumps(analyze(sdc_text=MINIMAL_SDC), sort_keys=True,
                       default=str)

    def test_degraded_flag_is_false_when_all_sources_answer(self):
        # The autouse fixture injects a healthy, scripted GitHub source.
        payload = call("rta_investigate", {"sdc": MINIMAL_SDC,
                                           "context_limit": 1,
                                           "issue_limit": 1})
        assert payload["context"]["issues"]["ok"] is True
        assert payload["degraded"] is False


# ── 3. capability boundary ─────────────────────────────────────────────────────

class TestToolGating:
    def test_reader_is_denied_network_sources(self):
        payload = call("rta_source_issues_search", {"query": "SDC"})
        assert payload["code"] == "FORBIDDEN"
        assert payload["decision"]["reason"] == "DENY_ROLE_LACKS_TOOL"

    def test_denied_call_does_not_reach_the_adapter(self, tmp_path):
        transport = install_failing_github(tmp_path)
        call("rta_source_issues_search", {"query": "SDC"})
        assert transport.calls == []

    def test_engineer_can_reach_network_sources(self, monkeypatch, tmp_path):
        monkeypatch.setenv("RTA_MCP_ROLE", "engineer")
        install_github(tmp_path, [json_response({}, status=503)])
        payload = call("rta_source_issues_search", {"query": "SDC"})
        assert payload.get("_isError") is not True
        assert payload["source"] == "github"

    def test_mutating_tool_requires_the_explicit_switch(self, monkeypatch):
        monkeypatch.setenv("RTA_MCP_ROLE", "maintainer")
        payload = call("rta_source_store_record", {"sdc": MINIMAL_SDC})
        assert payload["code"] == "FORBIDDEN"
        assert payload["decision"]["reason"] == "DENY_MUTATIONS_DISABLED"

    def test_maintainer_with_switch_can_record(self, monkeypatch):
        monkeypatch.setenv("RTA_MCP_ROLE", "maintainer")
        monkeypatch.setenv("RTA_MCP_ALLOW_MUTATIONS", "1")
        payload = call("rta_source_store_record", {"sdc": MINIMAL_SDC})
        assert payload["recorded"]["ok"] is True
        assert payload["authority"] == "engine"
        assert payload["engine_facts"]["verdict"] == \
            analyze(sdc_text=MINIMAL_SDC)["readiness"]["overall"]

    def test_unknown_tool_is_a_protocol_error(self):
        resp = call_raw("rta_does_not_exist", {})
        assert resp["error"]["code"] == -32602


# ── 4. auditing ────────────────────────────────────────────────────────────────

class TestAuditTrail:
    @pytest.fixture(autouse=True)
    def _engineer(self, monkeypatch):
        # Reading the audit trail is itself a gated tool (engineer and above).
        monkeypatch.setenv("RTA_MCP_ROLE", "engineer")

    def test_successful_call_is_audited(self):
        call("rta_rules", {})
        entries = call("rta_source_store_query",
                       {"audit": True, "limit": 5})["data"]["entries"]
        assert any(e["tool"] == "rta_rules" and e["outcome"] == "OK"
                   for e in entries)

    def test_denied_call_is_audited_as_forbidden(self, monkeypatch):
        # Drop to reader so the call is denied, then read the trail as engineer.
        monkeypatch.setenv("RTA_MCP_ROLE", "reader")
        denied = call("rta_source_issues_search", {"query": "SDC"})
        assert denied["code"] == "FORBIDDEN"
        monkeypatch.setenv("RTA_MCP_ROLE", "engineer")
        entries = call("rta_source_store_query",
                       {"audit": True, "limit": 5})["data"]["entries"]
        assert any(e["tool"] == "rta_source_issues_search"
                   and e["outcome"] == "FORBIDDEN" for e in entries)

    def test_audit_never_stores_sdc_text(self, monkeypatch, tmp_path):
        secret = "create_clock -name AUDIT_SECRET_CLK -period 1 [get_ports c]"
        call("rta_analyze", {"sdc": secret})
        db = StoreAdapter(path=tmp_path / "store.db", enabled=True).path
        assert b"AUDIT_SECRET_CLK" not in db.read_bytes()


# ── diagnostics ────────────────────────────────────────────────────────────────

class TestSourcesHealthTool:
    def test_health_makes_no_network_call(self, tmp_path):
        transport = install_failing_github(tmp_path)
        payload = call("rta_sources_health")
        assert transport.calls == []
        assert payload["network_used"] is False
        assert set(payload["sources"]) == {"corpus", "github", "store"}

    def test_health_reports_active_role(self, monkeypatch):
        monkeypatch.setenv("RTA_MCP_ROLE", "engineer")
        payload = call("rta_sources_health")
        assert payload["access"]["role"] == "engineer"
        assert payload["access"]["mutations_allowed"] is False

    def test_health_carries_the_authority_note(self):
        payload = call("rta_sources_health")
        assert "advisory" in payload["authority_note"].lower()


class TestDocsSearchTool:
    def test_missing_query_is_a_structured_error(self):
        payload = call("rta_source_docs_search", {})
        assert payload["code"] == "MISSING_QUERY"

    def test_search_returns_matches_for_a_real_rule_id(self):
        payload = call("rta_source_docs_search", {"query": "SDC-", "limit": 3})
        assert payload["ok"] is True
        assert payload["data"]["matches"]
        assert payload["source"] == "corpus"
