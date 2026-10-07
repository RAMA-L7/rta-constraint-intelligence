"""
Access-control tests for the MCP capability boundary (``rta/api/access.py``).

The security property being pinned: **deny by default**. A tool that appears in
no role is allowed for nobody, an unknown role never escalates, and the single
mutating tool additionally requires an explicit opt-in.
"""

from __future__ import annotations

import pytest

from rta.api import access


ENGINE_TOOL = "rta_analyze"
DOCS_TOOL = "rta_source_docs_search"
ISSUES_TOOL = "rta_source_issues_search"
INVESTIGATE_TOOL = "rta_investigate"
MUTATING_TOOL = "rta_source_store_record"


class TestRoleResolution:
    def test_default_is_reader(self, monkeypatch):
        monkeypatch.delenv("RTA_MCP_ROLE", raising=False)
        assert access.resolve_role() == access.ROLE_READER

    def test_unknown_role_falls_back_to_reader(self, monkeypatch):
        monkeypatch.setenv("RTA_MCP_ROLE", "superuser")
        assert access.resolve_role() == access.ROLE_READER
        assert access.role_is_explicit() is False

    @pytest.mark.parametrize("role", list(access.ROLE_ORDER))
    def test_known_roles_are_honoured(self, monkeypatch, role):
        monkeypatch.setenv("RTA_MCP_ROLE", role.upper())
        assert access.resolve_role() == role
        assert access.role_is_explicit() is True


class TestRoleMatrix:
    @pytest.mark.parametrize("role", list(access.ROLE_ORDER))
    def test_every_role_gets_the_engine_tools(self, role):
        for tool in access.ENGINE_TOOLS:
            assert access.check(role, tool)["allowed"] is True

    def test_reader_cannot_reach_network_sources(self):
        assert access.check("reader", ISSUES_TOOL)["allowed"] is False
        assert access.check("reader", INVESTIGATE_TOOL)["allowed"] is False
        assert access.check("reader", DOCS_TOOL)["allowed"] is True

    def test_engineer_can_reach_network_sources(self):
        assert access.check("engineer", ISSUES_TOOL)["allowed"] is True
        assert access.check("engineer", INVESTIGATE_TOOL)["allowed"] is True

    def test_role_ladder_is_monotonic(self):
        for lower, higher in zip(access.ROLE_ORDER, access.ROLE_ORDER[1:]):
            assert access.allowed_tools(lower) < access.allowed_tools(higher)

    def test_denied_call_names_the_required_role(self):
        decision = access.check("reader", ISSUES_TOOL)
        assert decision["reason"] == "DENY_ROLE_LACKS_TOOL"
        assert decision["required_role"] == "engineer"

    def test_role_matrix_reports_no_orphan_tools(self):
        matrix = access.role_matrix()
        assert matrix["denied_for_all_roles"] == []
        assert matrix["default_role"] == "reader"


class TestDenyByDefault:
    def test_unknown_tool_denied_for_every_role(self):
        for role in access.ROLE_ORDER:
            decision = access.check(role, "rta_execute_arbitrary_code")
            assert decision["allowed"] is False
            assert decision["reason"] == "DENY_UNKNOWN_TOOL"

    def test_unknown_role_object_denied(self):
        decision = access.check("", ISSUES_TOOL)
        assert decision["allowed"] is False
        assert decision["role"] == "reader"


class TestMutationGate:
    def test_mutations_off_by_default(self, monkeypatch):
        monkeypatch.delenv("RTA_MCP_ALLOW_MUTATIONS", raising=False)
        decision = access.check("maintainer", MUTATING_TOOL)
        assert decision["allowed"] is False
        assert decision["reason"] == "DENY_MUTATIONS_DISABLED"

    @pytest.mark.parametrize("value", ["1", "true", "YES", "on"])
    def test_mutation_switch_accepts_truthy_values(self, monkeypatch, value):
        monkeypatch.setenv("RTA_MCP_ALLOW_MUTATIONS", value)
        assert access.check("maintainer", MUTATING_TOOL)["allowed"] is True

    @pytest.mark.parametrize("value", ["0", "false", "no", "maybe", ""])
    def test_mutation_switch_rejects_everything_else(self, monkeypatch, value):
        monkeypatch.setenv("RTA_MCP_ALLOW_MUTATIONS", value)
        assert access.check("maintainer", MUTATING_TOOL)["allowed"] is False

    def test_reader_and_engineer_still_denied_with_mutations_on(self, monkeypatch):
        monkeypatch.setenv("RTA_MCP_ALLOW_MUTATIONS", "1")
        for role in ("reader", "engineer"):
            decision = access.check(role, MUTATING_TOOL)
            assert decision["allowed"] is False
            assert decision["required_role"] == "maintainer"


class TestDescribeRole:
    def test_describe_role_reports_tools_and_flags(self, monkeypatch):
        monkeypatch.setenv("RTA_MCP_ROLE", "engineer")
        monkeypatch.delenv("RTA_MCP_ALLOW_MUTATIONS", raising=False)
        described = access.describe_role("engineer")
        assert described["role"] == "engineer"
        assert described["explicit"] is True
        assert described["mutations_allowed"] is False
        assert ENGINE_TOOL in described["tools"]
        assert MUTATING_TOOL not in described["tools"]


class TestAuditHook:
    def test_audit_writes_digest_only(self, tmp_path, monkeypatch):
        from rta.sources.store import StoreAdapter

        store = StoreAdapter(path=tmp_path / "audit.db", enabled=True)
        access.audit("rta_analyze", "reader",
                     {"sdc": "create_clock -name SECRET_NAME -period 1 [get_ports c]"},
                     outcome="OK", store=store)
        entry = store.query_audit(limit=1)["data"]["entries"][0]
        assert entry["tool"] == "rta_analyze"
        assert "SECRET_NAME" not in (tmp_path / "audit.db").read_bytes().decode(
            "utf-8", errors="replace")

    def test_audit_never_raises_without_a_store(self, monkeypatch):
        monkeypatch.setenv("RTA_STORE_DISABLE", "1")
        access.audit("rta_analyze", "reader", {}, outcome="OK")  # no raise
