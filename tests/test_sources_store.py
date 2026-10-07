"""
SQLite store adapter tests.

Two invariants matter most here and are asserted directly:

1. The store **records** engine verdicts; it never produces or accepts one.
   ``record_run`` derives every count from the engine payload.
2. The audit trail stores an argument **digest**, never the argument values —
   so a stored constraint file cannot leak into the audit table.
"""

from __future__ import annotations

import json
import sqlite3

import pytest

from rta.api.api_server import analyze
from rta.sources.base import CODE_DISABLED, CODE_LOCAL_IO
from rta.sources.store import (
    SCHEMA_VERSION,
    StoreAdapter,
    args_digest,
    connect,
    engine_facts,
    migrate,
)

MINIMAL_SDC = ("set sdc_version 2.2\n"
               "create_clock -name clk -period 5.0 [get_ports clk]\n")


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.delenv("RTA_STORE_DISABLE", raising=False)
    return StoreAdapter(path=tmp_path / "store.db", enabled=True)


class TestSchema:
    def test_migrate_is_idempotent(self, tmp_path):
        conn = connect(tmp_path / "s.db")
        migrate(conn)
        migrate(conn)
        row = conn.execute("SELECT COUNT(*) AS n FROM schema_version").fetchone()
        assert row["n"] == 1
        assert conn.execute("SELECT MAX(version) AS v FROM schema_version") \
            .fetchone()["v"] == SCHEMA_VERSION
        conn.close()

    def test_tables_exist(self, tmp_path):
        conn = connect(tmp_path / "s.db")
        migrate(conn)
        names = {r["name"] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"runs", "findings", "source_evidence", "tool_audit",
                "schema_version"} <= names
        conn.close()

    def test_connect_creates_parent_directory(self, tmp_path):
        target = tmp_path / "nested" / "deep" / "store.db"
        conn = connect(target)
        migrate(conn)
        conn.close()
        assert target.exists()


class TestEngineFacts:
    def test_reads_real_engine_payload(self):
        payload = analyze(sdc_text=MINIMAL_SDC)
        facts = engine_facts(payload)
        assert facts["verdict"] == payload["readiness"]["overall"]
        assert facts["rule_count"] == len({i["code"] for i in payload["issues"]})
        assert facts["blocker_count"] == sum(
            1 for i in payload["issues"] if i["sev"] == "error")
        assert facts["warning_count"] == sum(
            1 for i in payload["issues"] if i["sev"] == "warning")

    def test_handles_empty_and_garbage_payloads(self):
        for payload in ({}, None, {"issues": "nope", "readiness": []}):
            facts = engine_facts(payload)
            assert facts["verdict"] is None
            assert facts["issue_count"] == 0
            assert facts["rule_ids"] == []

    def test_rule_ids_are_sorted_and_unique(self):
        facts = engine_facts(analyze(sdc_text=MINIMAL_SDC))
        assert facts["rule_ids"] == sorted(set(facts["rule_ids"]))


class TestRecordRun:
    def test_records_engine_verdict_verbatim(self, store):
        payload = analyze(sdc_text=MINIMAL_SDC)
        result = store.record_run(run_id="run-1", sdc_text=MINIMAL_SDC,
                                  analysis=payload, tool="rta_source_store_record",
                                  role="maintainer")
        assert result["ok"] is True
        assert result["data"]["findings"] == len(payload["issues"])
        rows = store.query_runs(run_id="run-1")["data"]["runs"]
        assert rows[0]["verdict"] == payload["readiness"]["overall"]
        assert rows[0]["blocker_count"] == sum(
            1 for i in payload["issues"] if i["sev"] == "error")
        assert rows[0]["sdc_sha256"]

    def test_caller_cannot_inject_a_verdict(self, store):
        """record_run takes the payload; there is no verdict parameter."""
        import inspect
        params = inspect.signature(store.record_run).parameters
        assert "verdict" not in params
        assert "analysis" in params

    def test_findings_rows_match_issues(self, store):
        payload = analyze(sdc_text=MINIMAL_SDC)
        store.record_run(run_id="run-2", sdc_text=MINIMAL_SDC,
                         analysis=payload, tool="t", role="maintainer")
        conn = connect(store.path)
        count = conn.execute("SELECT COUNT(*) AS n FROM findings WHERE run_id=?",
                             ("run-2",)).fetchone()["n"]
        conn.close()
        assert count == len(payload["issues"])

    def test_evidence_rows_are_linked_to_run(self, store):
        payload = analyze(sdc_text=MINIMAL_SDC)
        store.record_run(run_id="run-3", sdc_text=MINIMAL_SDC,
                         analysis=payload, tool="t", role="maintainer")
        store.record_evidence(run_id="run-3", source="corpus",
                              ref="docs/features/README-16-mcp-server.md",
                              content_hash="abc123", freshness="fresh")
        data = store.query_runs(run_id="run-3")["data"]
        assert data["evidence"][0]["ref"].endswith("README-16-mcp-server.md")
        assert data["evidence"][0]["content_hash"] == "abc123"

    def test_record_run_failure_is_an_envelope_not_an_exception(self, store,
                                                                monkeypatch):
        def boom(*a, **kw):
            raise sqlite3.OperationalError("database is locked")
        monkeypatch.setattr("rta.sources.store.connect", boom)
        result = store.record_run(run_id="run-4", sdc_text=MINIMAL_SDC,
                                  analysis={}, tool="t", role="maintainer")
        assert result["ok"] is False
        assert result["error"]["code"] == CODE_LOCAL_IO


class TestQueries:
    def test_filter_by_rule_id_and_verdict(self, store):
        payload = analyze(sdc_text=MINIMAL_SDC)
        store.record_run(run_id="run-a", sdc_text=MINIMAL_SDC, analysis=payload,
                         tool="t", role="maintainer")
        rule = payload["issues"][0]["code"]
        assert store.query_runs(rule_id=rule)["data"]["returned"] == 1
        assert store.query_runs(verdict="NOPE")["data"]["returned"] == 0

    def test_limit_is_applied(self, store):
        payload = analyze(sdc_text=MINIMAL_SDC)
        for index in range(3):
            store.record_run(run_id=f"run-{index}", sdc_text=MINIMAL_SDC,
                             analysis=payload, tool="t", role="maintainer")
        assert store.query_runs(limit=2)["data"]["returned"] == 2

    def test_missing_store_is_disabled_envelope(self, tmp_path, monkeypatch):
        adapter = StoreAdapter(path=tmp_path / "s.db", enabled=False)
        assert adapter.query_runs()["error"]["code"] == CODE_DISABLED
        assert adapter.query_audit()["error"]["code"] == CODE_DISABLED

    def test_env_can_disable_the_store(self, tmp_path, monkeypatch):
        monkeypatch.setenv("RTA_STORE_DISABLE", "1")
        assert StoreAdapter(path=tmp_path / "s.db").enabled is False


class TestAuditPrivacy:
    def test_digest_is_stable_and_hides_values(self):
        digest_a, keys = args_digest({"sdc": MINIMAL_SDC, "limit": 3})
        digest_b, _ = args_digest({"limit": 3, "sdc": MINIMAL_SDC})
        assert digest_a == digest_b                    # key order irrelevant
        assert keys == "limit,sdc"
        assert MINIMAL_SDC not in digest_a

    def test_audit_stores_no_argument_values(self, store):
        secret_sdc = "create_clock -name SECRET_CLOCK_NAME -period 1.0 [get_ports c]"
        store.audit(tool="rta_analyze", role="reader", args={"sdc": secret_sdc},
                    outcome="OK", duration_ms=1.5)
        blob = store.path.read_bytes()
        assert b"SECRET_CLOCK_NAME" not in blob

    def test_audit_row_fields(self, store):
        store.audit(tool="rta_investigate", role="engineer",
                    args={"sdc": "x", "issue_limit": 2}, outcome="OK",
                    duration_ms=4.0, degraded=True, sources_used=["corpus"])
        entry = store.query_audit(limit=1)["data"]["entries"][0]
        assert entry["tool"] == "rta_investigate"
        assert entry["role"] == "engineer"
        assert entry["degraded"] == 1
        assert json.loads(entry["sources_used"]) == ["corpus"]
        assert len(entry["args_digest"]) == 64

    def test_audit_never_raises_on_broken_store(self, tmp_path, monkeypatch):
        adapter = StoreAdapter(path=tmp_path / "s.db", enabled=True)

        def boom(*a, **kw):
            raise sqlite3.OperationalError("locked")
        monkeypatch.setattr("rta.sources.store.connect", boom)
        adapter.audit(tool="t", role="reader", args={}, outcome="OK")  # no raise

    def test_audit_filtered_by_tool(self, store):
        store.audit(tool="rta_analyze", role="reader", args={}, outcome="OK")
        store.audit(tool="rta_rules", role="reader", args={}, outcome="OK")
        assert store.query_audit(tool="rta_rules")["data"]["returned"] == 1

    def test_health_reports_row_counts(self, store):
        store.audit(tool="t", role="reader", args={}, outcome="OK")
        health = store.health()
        assert health["tool_audit_rows"] == 1
        assert health["schema_version"] == SCHEMA_VERSION
        assert health["requires_network"] is False
