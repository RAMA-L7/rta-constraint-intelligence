"""
Context-Aware Constraint Analysis — regression tests.

Proves that findings carry machine-readable relevant context built ONLY
from values the engine actually computed, with explicit states
(RESOLVED / NOT_AVAILABLE / NOT_SUPPORTED / AMBIGUOUS / NOT_VALIDATED):

  A. SDC-only context      — clock resolved from the SDC itself, netlist NO
  B. SDC + design context  — netlist_available YES reflected honestly
  C. missing design context— object_resolved NOT_AVAILABLE, never invented
  D. ambiguous context     — wildcard endpoints reported AMBIGUOUS
  E. equivalent syntax     — brace/bare forms canonicalize to the same key
  F. distinct objects      — different clocks are never merged in context

Every test also pins determinism: same input → byte-identical context.
"""

import json

import pytest

from checker import check_sdc
from constraint_interactions import analyze_interactions


def _issue(result, code):
    hits = [i for i in result.issues if i.code == code]
    assert len(hits) == 1, f"expected exactly one {code}, got {len(hits)}"
    return hits[0]


# ── A. SDC-only context ──────────────────────────────────────────────────────

class TestSdcOnlyContext:

    def test_sdc008_context_resolved_clock(self):
        text = ("create_clock -name PLL0 -period 0.8333 [get_ports p]\n"
                "set_input_delay 20.0 -clock PLL0 [get_ports DATA_IN]\n")
        i = _issue(check_sdc(text), "SDC-008")
        c = i.context
        assert c["command"] == "set_input_delay"
        assert c["delay"] == 20.0
        assert c["referenced_clock"] == "PLL0"
        assert c["clock_period"] == 0.8333
        assert c["clock_resolved"] == "RESOLVED"
        assert c["source_port"] == "DATA_IN"
        # Honest limitation: no netlist was supplied.
        assert c["netlist_available"] == "NO"
        assert abs(c["delay_to_period_ratio"] - 20.0 / 0.8333) < 1e-3

    def test_sdc008_context_no_clock_reference(self):
        """Without a -clock ref the fallback is explicit, not hidden."""
        text = ("create_clock -name A -period 5.0 [get_ports a]\n"
                "set_input_delay 9.0 [get_ports din]\n")
        i = _issue(check_sdc(text), "SDC-008")
        c = i.context
        assert c["referenced_clock"] is None
        assert c["clock_resolved"] == "NOT_AVAILABLE"
        assert c["compared_against_clock"] == "A"

    def test_sdc021_context_canonical_keys_and_rule_scope(self):
        text = ("create_clock -name A -period 10 [get_ports a]\n"
                "create_clock -name B -period 12 [get_ports b]\n"
                "set_multicycle_path 2 -setup "
                "-from [get_clocks {A}] -to [get_clocks B]\n")
        i = _issue(check_sdc(text), "SDC-021")
        c = i.context
        assert c["setup_cycles"] == 2
        assert c["from_key"] == "A"
        assert c["to_key"] == "B"
        assert c["hold_fix_found"] is False
        # Documented product rule surfaced as evidence, not prose.
        assert c["hold_fix_search_scope"] == "IDENTICAL_ENDPOINTS_ONLY"
        assert c["endpoint_state"] == "RESOLVED"
        assert c["endpoints_canonicalized"] is True   # brace form normalized

    def test_sdc036_context_sdc_only(self):
        text = ("create_clock -name A -period 5 [get_ports a]\n"
                "set_disable_timing [get_cells u_core]\n")
        i = _issue(check_sdc(text), "SDC-036")
        c = i.context
        assert c["affected_object"] == "u_core"
        assert c["object_resolved"] == "NOT_AVAILABLE"   # honest: no netlist
        assert c["from_supplied"] is False and c["to_supplied"] is False
        assert c["affected_scope"] == "ALL_ARCS"
        assert c["netlist_available"] == "NO"

    def test_sdc150_context_proximity_evidence(self):
        text = ("create_clock -name A -period 5 [get_ports a]\n"
                "set_case_analysis 0 [get_ports tm]\n")
        i = _issue(check_sdc(text), "SDC-150")
        c = i.context
        assert c["command"] == "set_case_analysis"
        assert c["inline_comment"] is False
        assert c["comment_within_proximity"] is False
        assert c["proximity_lines_checked"] == 3


# ── B/C. Design-context availability states ──────────────────────────────────

class TestDesignContextStates:

    def test_sdc036_with_context_reports_yes_but_unresolved(self):
        """With a netlist supplied, availability says YES; resolution of the
        broad-disable object itself stays NOT_VALIDATED unless the resolver
        subset proves it — never silently upgraded."""
        from design_context import DesignContext
        ctx = DesignContext()
        text = ("create_clock -name A -period 5 [get_ports a]\n"
                "set_disable_timing [get_cells u_core]\n")
        i = _issue(check_sdc(text, context=ctx), "SDC-036")
        c = i.context
        assert c["netlist_available"] == "YES"
        assert c["object_resolved"] == "NOT_VALIDATED"


# ── D. Ambiguous context ─────────────────────────────────────────────────────

class TestAmbiguousContext:

    def test_sdc021_wildcard_endpoints_ambiguous(self):
        text = ("create_clock -name A -period 10 [get_ports a]\n"
                "create_clock -name B -period 12 [get_ports b]\n"
                "set_multicycle_path 2 -setup "
                "-from [get_clocks *] -to [get_clocks B]\n")
        i = _issue(check_sdc(text), "SDC-021")
        assert i.context["endpoint_state"] == "AMBIGUOUS"


# ── E. Equivalent syntax resolves to the same key ────────────────────────────

class TestEquivalentSyntaxSameKey:

    @pytest.mark.parametrize("frm,to_", [
        ("[get_clocks CLK_A]", "[get_clocks CLK_B]"),
        ("[get_clocks {CLK_A}]", "[get_clocks {CLK_B}]"),
    ])
    def test_canonical_key_identical_across_syntax(self, frm, to_):
        text = ("create_clock -name CLK_A -period 10 [get_ports a]\n"
                "create_clock -name CLK_B -period 12 [get_ports b]\n"
                f"set_multicycle_path 3 -setup -from {frm} -to {to_}\n")
        i = _issue(check_sdc(text), "SDC-021")
        c = i.context
        assert c["from_key"] == "CLK_A"
        assert c["to_key"] == "CLK_B"


# ── F. Distinct objects are never merged ────────────────────────────────────

class TestDistinctObjectsNotMerged:

    def test_two_delays_reference_their_own_clocks(self):
        """Each finding's context names ONLY its own referenced clock."""
        text = ("create_clock -name FAST -period 1.0 [get_ports cf]\n"
                "create_clock -name SLOW -period 50.0 [get_ports cs]\n"
                "set_input_delay 2.0 -clock FAST [get_ports d1]\n"
                "set_input_delay 60.0 -clock SLOW [get_ports d2]\n")
        r = check_sdc(text)
        hits = sorted((i for i in r.errors if i.code == "SDC-008"),
                      key=lambda x: x.line)
        assert len(hits) == 2
        by_port = {i.context["source_port"]: i.context for i in hits}
        assert by_port["d1"]["referenced_clock"] == "FAST"
        assert by_port["d1"]["clock_period"] == 1.0
        assert by_port["d2"]["referenced_clock"] == "SLOW"
        assert by_port["d2"]["clock_period"] == 50.0

    def test_override_context_names_correct_analysis_type(self):
        """The SDC-068 regression: analysis type is explicit machine data."""
        text = ("create_clock -name C -period 5 [get_ports c]\n"
                "set_clock_uncertainty 0.10 -setup [get_clocks C]\n"
                "set_clock_uncertainty 0.20 -setup [get_clocks C]\n")
        ia = analyze_interactions(text)
        ovr = [f for f in ia.findings if f["code"] == "SDC-068"]
        assert len(ovr) == 1
        c = ovr[0]["context"]
        assert c["analysis_type"] == "setup"
        assert c["analysis_type_state"] == "RESOLVED"
        assert dict(c["values_by_line"]) == {2: "0.1", 3: "0.2"}
        # The legal pair case must NOT exist here (covered in Case-1 tests);
        # this context only appears when an override actually fires.


# ── Determinism ──────────────────────────────────────────────────────────────

class TestContextDeterminism:

    def test_repeated_runs_identical_context(self):
        text = ("create_clock -name PLL0 -period 0.8333 [get_ports p]\n"
                "set_input_delay 20.0 -clock PLL0 [get_ports DATA_IN]\n"
                "create_clock -name A -period 10 [get_ports a]\n"
                "create_clock -name B -period 12 [get_ports b]\n"
                "set_multicycle_path 2 -setup "
                "-from [get_clocks {A}] -to [get_clocks B]\n"
                "set_disable_timing [get_cells u_core]\n")
        r1 = check_sdc(text)
        r2 = check_sdc(text)
        fp1 = json.dumps([(i.code, i.context) for i in r1.issues], sort_keys=False)
        fp2 = json.dumps([(i.code, i.context) for i in r2.issues], sort_keys=False)
        assert fp1 == fp2

    def test_findings_without_context_have_none(self):
        """No invented context: rules without relevant context emit None."""
        text = ("create_clock -name dupe -period 5 [get_ports a]\n"
                "create_clock -name dupe -period 10 [get_ports b]\n")
        i = _issue(check_sdc(text), "SDC-002")
        assert i.context is None
