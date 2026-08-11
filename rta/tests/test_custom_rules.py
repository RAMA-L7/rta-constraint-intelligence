"""
Tests for the Custom Rules Engine module.
"""

import pytest

from custom_rules import (
    CustomRule, CustomRuleResult, CustomRuleset,
    load_ruleset, apply_rules, apply_rulesets, integrate_with_check,
    _CONDITIONS,
)


class TestCustomRule:
    """Tests for the CustomRule dataclass."""

    def test_create_rule(self):
        rule = CustomRule(
            id="TST-001",
            name="Test Rule",
            severity="warning",
            description="Test",
            command="create_clock",
            condition="present",
        )
        assert rule.id == "TST-001"
        assert rule.severity == "warning"
        assert rule.enabled is True

    def test_disabled_rule(self):
        rule = CustomRule(
            id="TST-002",
            name="Disabled",
            severity="error",
            description="",
            command="set_false_path",
            condition="absent",
            enabled=False,
        )
        assert rule.enabled is False

    def test_rule_with_threshold(self):
        rule = CustomRule(
            id="TST-003",
            name="Count Check",
            severity="warning",
            description="",
            command="set_false_path",
            condition="count_above",
            threshold=10,
        )
        assert rule.threshold == 10.0


class TestConditionHandlers:
    """Tests for each of the 9 condition types."""

    def test_present_found(self):
        rule = CustomRule(id="P1", name="", severity="", description="", command="create_clock", condition="present")
        handler = _CONDITIONS["present"]
        passed, msg = handler(["create_clock -name clk -period 5.0"], rule, "")
        assert passed is True

    def test_present_not_found(self):
        rule = CustomRule(id="P2", name="", severity="", description="", command="set_propagated_clock", condition="present")
        handler = _CONDITIONS["present"]
        passed, msg = handler([], rule, "")
        assert passed is False
        assert "no" in msg.lower()

    def test_absent_found(self):
        rule = CustomRule(id="A1", name="", severity="", description="", command="set_dont_use", condition="absent")
        handler = _CONDITIONS["absent"]
        passed, msg = handler(["set_dont_use [get_lib_cells *]"], rule, "")
        assert passed is False

    def test_absent_not_found(self):
        rule = CustomRule(id="A2", name="", severity="", description="", command="set_dont_use", condition="absent")
        handler = _CONDITIONS["absent"]
        passed, msg = handler([], rule, "")
        assert passed is True

    def test_count_above_exceeds(self):
        rule = CustomRule(id="CA1", name="", severity="", description="", command="set_false_path",
                          condition="count_above", threshold=5)
        handler = _CONDITIONS["count_above"]
        passed, msg = handler(["set_false_path" for _ in range(10)], rule, "")
        assert passed is False

    def test_count_above_ok(self):
        rule = CustomRule(id="CA2", name="", severity="", description="", command="set_false_path",
                          condition="count_above", threshold=5)
        handler = _CONDITIONS["count_above"]
        passed, msg = handler(["set_false_path" for _ in range(3)], rule, "")
        assert passed is True

    def test_count_below_exceeds(self):
        rule = CustomRule(id="CB1", name="", severity="", description="", command="set_false_path",
                          condition="count_below", threshold=3)
        handler = _CONDITIONS["count_below"]
        passed, msg = handler(["set_false_path"], rule, "")
        assert passed is False

    def test_count_below_ok(self):
        rule = CustomRule(id="CB2", name="", severity="", description="", command="set_false_path",
                          condition="count_below", threshold=3)
        handler = _CONDITIONS["count_below"]
        passed, msg = handler(["set_false_path" for _ in range(5)], rule, "")
        assert passed is True

    def test_count_exactly_matches(self):
        rule = CustomRule(id="CE1", name="", severity="", description="", command="create_clock",
                          condition="count_exactly", threshold=2)
        handler = _CONDITIONS["count_exactly"]
        passed, msg = handler(["create_clock -name a", "create_clock -name b"], rule, "")
        assert passed is True

    def test_count_exactly_mismatch(self):
        rule = CustomRule(id="CE2", name="", severity="", description="", command="create_clock",
                          condition="count_exactly", threshold=2)
        handler = _CONDITIONS["count_exactly"]
        passed, msg = handler(["create_clock -name a", "create_clock -name b", "create_clock -name c"], rule, "")
        assert passed is False

    def test_value_above_exceeds(self):
        rule = CustomRule(id="VA1", name="", severity="", description="", command="create_clock",
                          condition="value_above", field_name="period", threshold=10.0,
                          pattern=r"-period\s+([\d.]+)")
        handler = _CONDITIONS["value_above"]
        passed, msg = handler(["create_clock -period 12.0 -name clk"], rule, "")
        assert passed is False

    def test_value_above_ok(self):
        rule = CustomRule(id="VA2", name="", severity="", description="", command="create_clock",
                          condition="value_above", field_name="period", threshold=10.0,
                          pattern=r"-period\s+([\d.]+)")
        handler = _CONDITIONS["value_above"]
        passed, msg = handler(["create_clock -period 5.0 -name clk"], rule, "")
        assert passed is True

    def test_value_below_exceeds(self):
        rule = CustomRule(id="VB1", name="", severity="", description="", command="create_clock",
                          condition="value_below", field_name="period", threshold=2.0,
                          pattern=r"-period\s+([\d.]+)")
        handler = _CONDITIONS["value_below"]
        passed, msg = handler(["create_clock -period 1.0 -name clk"], rule, "")
        assert passed is False

    def test_value_below_ok(self):
        rule = CustomRule(id="VB2", name="", severity="", description="", command="create_clock",
                          condition="value_below", field_name="period", threshold=2.0)
        handler = _CONDITIONS["value_below"]
        passed, msg = handler(["create_clock -period 5.0 -name clk"], rule, "")
        assert passed is True

    def test_regex_match_found(self):
        rule = CustomRule(id="RM1", name="", severity="", description="", command="create_clock",
                          condition="regex_match", pattern=r"-period\s+(\d+\.?\d*)")
        handler = _CONDITIONS["regex_match"]
        passed, msg = handler(["create_clock -period 5.0 -name clk"], rule, "")
        assert passed is False

    def test_regex_match_not_found(self):
        rule = CustomRule(id="RM2", name="", severity="", description="", command="create_clock",
                          condition="regex_match", pattern=r"BADPATTERN")
        handler = _CONDITIONS["regex_match"]
        passed, msg = handler(["create_clock -period 5.0 -name clk"], rule, "")
        assert passed is True

    def test_regex_absent_found(self):
        rule = CustomRule(id="RA1", name="", severity="", description="", command="create_clock",
                          condition="regex_absent", pattern=r"-period\s+(\d+)")
        handler = _CONDITIONS["regex_absent"]
        passed, msg = handler(["create_clock -period 5.0 -name clk"], rule, "")
        assert passed is False

    def test_regex_absent_not_found(self):
        rule = CustomRule(id="RA2", name="", severity="", description="", command="create_clock",
                          condition="regex_absent", pattern=r"BADPATTERN")
        handler = _CONDITIONS["regex_absent"]
        passed, msg = handler(["create_clock -period 5.0 -name clk"], rule, "")
        assert passed is True


class TestApplyRules:
    """Tests for the apply_rules function."""

    def test_rule_passes(self, minimal_sdc):
        ruleset = CustomRuleset(name="Test", rules=[
            CustomRule(id="T1", name="", severity="", description="", command="create_clock", condition="present"),
        ])
        results = apply_rules(minimal_sdc, ruleset)
        assert len(results) == 1
        assert results[0].passed is True

    def test_rule_fails(self):
        ruleset = CustomRuleset(name="Test", rules=[
            CustomRule(id="F1", name="", severity="error", description="", command="set_propagated_clock", condition="present"),
        ])
        results = apply_rules("create_clock -name clk -period 5.0", ruleset)
        assert len(results) == 1
        assert results[0].passed is False
        assert results[0].rule.severity == "error"

    def test_disabled_rule_skipped(self):
        ruleset = CustomRuleset(name="Test", rules=[
            CustomRule(id="D1", name="", severity="", description="", command="create_clock",
                       condition="present", enabled=False),
            CustomRule(id="D2", name="", severity="", description="", command="create_clock", condition="absent"),
        ])
        results = apply_rules("create_clock -name clk -period 5.0", ruleset)
        assert len(results) == 1
        assert results[0].rule.id == "D2"

    def test_message_template_replacement(self):
        ruleset = CustomRuleset(name="Msg", rules=[
            CustomRule(id="MG1", name="", severity="error", description="", command="set_false_path",
                       condition="count_above", threshold=2,
                       message="Found {count} false paths"),
        ])
        results = apply_rules("set_false_path -from [get_ports a]\nset_false_path -from [get_ports b]\nset_false_path -from [get_ports c]", ruleset)
        assert results[0].passed is False
        assert "Found 3" in results[0].msg

    def test_empty_ruleset(self):
        ruleset = CustomRuleset(name="Empty")
        results = apply_rules("create_clock -name clk -period 5.0", ruleset)
        assert results == []


class TestApplyRulesets:
    """Tests for apply_rulesets function."""

    def test_multiple_rulesets(self):
        rs1 = CustomRuleset(name="RS1", rules=[
            CustomRule(id="A", name="", severity="", description="", command="create_clock", condition="present"),
        ])
        rs2 = CustomRuleset(name="RS2", rules=[
            CustomRule(id="B", name="", severity="", description="", command="set_false_path", condition="absent"),
        ])
        results = apply_rulesets("create_clock -name clk -period 5.0", [rs1, rs2])
        assert "RS1" in results
        assert "RS2" in results
        assert len(results["RS1"]) == 1
        assert results["RS1"][0].passed is True


class TestYamlLoading:
    """Tests for YAML-based ruleset loading (requires PyYAML)."""

    def test_load_ruleset_from_yaml(self, yaml_rules_path):
        try:
            ruleset = load_ruleset(yaml_rules_path)
            assert ruleset.name == "Test Rules"
            assert len(ruleset.rules) == 2
            assert ruleset.rules[0].id == "TST-001"
            assert ruleset.rules[0].condition == "value_above"
            assert ruleset.rules[0].threshold == 10.0
        except ImportError:
            pytest.skip("PyYAML not installed")

    def test_load_ruleset_source_file(self, yaml_rules_path):
        try:
            ruleset = load_ruleset(yaml_rules_path)
            assert ruleset.source_file == yaml_rules_path
        except ImportError:
            pytest.skip("PyYAML not installed")
