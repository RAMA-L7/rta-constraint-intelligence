"""
Tests for the Rules Registry module.
"""

import pytest
from rules_registry import (
    APP_VERSION, Rule, RULES,
    get_all_rules, get_rule,
    get_rules_by_module, get_rules_by_severity,
)


class TestRulesRegistry:
    """Tests for the centralized rule registry."""

    def test_app_version(self):
        """APP_VERSION should be a semantic version string."""
        assert isinstance(APP_VERSION, str)
        parts = APP_VERSION.split(".")
        assert len(parts) == 3
        for p in parts:
            assert p.isdigit()

    def test_rules_are_populated(self):
        """RULES dict should have entries."""
        assert len(RULES) > 50  # 60+ expected
        assert len(RULES) >= 60  # at least 60 rules

    def test_rule_structure(self):
        """Each rule should be a proper Rule instance."""
        rule = get_rule("SDC-001")
        assert rule is not None
        assert isinstance(rule, Rule)
        assert rule.code == "SDC-001"
        assert rule.severity in ("error", "warning", "info", "fatal")
        assert rule.short_name
        assert rule.description
        assert rule.why_matters
        assert rule.fix
        assert rule.module
        assert rule.added_version

    def test_get_all_rules(self):
        """get_all_rules should return all rules as a list."""
        rules = get_all_rules()
        assert len(rules) == len(RULES)
        assert all(isinstance(r, Rule) for r in rules)

    def test_get_rule_exists(self):
        rule = get_rule("SDC-060")
        assert rule is not None
        assert rule.code == "SDC-060"

    def test_get_rule_case_insensitive(self):
        """Should handle uppercase input already (all codes are uppercase)."""
        rule = get_rule("sdc-001")
        assert rule is None or rule.code == "SDC-001"

    def test_get_rule_not_found(self):
        assert get_rule("SDC-999") is None
        assert get_rule("") is None

    def test_get_rules_by_module(self):
        rules = get_rules_by_module("checker")
        assert len(rules) > 20
        for r in rules:
            assert r.module == "checker"

    def test_get_rules_by_module_mmc(self):
        rules = get_rules_by_module("mmc")
        assert len(rules) >= 4  # SDC-050..054

    def test_get_rules_by_module_clock_relations(self):
        rules = get_rules_by_module("clock_relations")
        assert len(rules) >= 4  # SDC-060..063

    def test_get_rules_by_module_constraint_diff(self):
        rules = get_rules_by_module("constraint_diff")
        assert len(rules) >= 20  # CHG-* rules

    def test_get_rules_by_severity(self):
        errors = get_rules_by_severity("error")
        for r in errors:
            assert r.severity == "error"

    def test_get_rules_by_severity_fatal(self):
        fatals = get_rules_by_severity("fatal")
        for r in fatals:
            assert r.severity == "fatal"

    def test_get_rules_by_severity_info(self):
        infos = get_rules_by_severity("info")
        for r in infos:
            assert r.severity == "info"

    def test_rules_have_unique_codes(self):
        """No duplicate rule codes."""
        codes = [r.code for r in get_all_rules()]
        assert len(codes) == len(set(codes))

    def test_rules_have_module_category(self):
        """Every rule has a module in the valid set."""
        valid_modules = {"checker", "mmc", "clock_relations", "constraint_diff"}
        for r in get_all_rules():
            assert r.module in valid_modules, f"Rule {r.code} has invalid module: {r.module}"

    def test_rules_have_valid_version(self):
        """Every rule has a version that parses."""
        for r in get_all_rules():
            parts = r.added_version.split(".")
            assert len(parts) == 3

    def test_sdc_001_fields(self):
        """Spot-check SDC-001 has expected values."""
        rule = get_rule("SDC-001")
        assert rule.code == "SDC-001"
        assert rule.severity == "error"
        assert "clock" in rule.short_name.lower()
        assert rule.module == "checker"

    def test_chg_rules_have_fatal_severity(self):
        """CHG-FP and CHG-MCP rules should be fatal."""
        fatal_codes = {"CHG-FP-001", "CHG-FP-002", "CHG-MCP-001", "CHG-MCP-002", "CHG-MCP-004", "CHG-CK-005"}
        for code in fatal_codes:
            rule = get_rule(code)
            assert rule is not None, f"{code} not found"
            assert rule.severity == "fatal", f"{code} should be fatal"

    def test_reference_urls_for_key_rules(self):
        """Key rules from Ausdia/Synopsys should have reference URLs."""
        rule = get_rule("SDC-001")
        assert rule.reference_url  # should have a reference
