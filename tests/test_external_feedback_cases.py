"""
Regression tests for externally-reported real-world SDC feedback cases.

Source: external engineer field testing of Ṛta (6 reported cases). Each test
reproduces the reported input and pins the CONFIRMED current behavior:

  Case 1 — set_clock_uncertainty setup vs hold on the same clock written in
           value-first form ('0.08 -hold') must NOT be a duplicate/override
           (was a confirmed SDC-068 false positive).
  Case 2 — set_input_delay >= referenced clock period sanity check
           (SDC-008, already correct — pinned).
  Case 3 — set_multicycle_path -setup/-hold pairing must recognize an
           existing separate -hold command regardless of collection syntax,
           flag order, or intervening commands (brace-form was a confirmed
           false negative). Reversed/different scopes must NOT pair.
  Case 4 — set_max_delay without -datapath_only review warning
           (SDC-027, already correct — pinned).
  Case 5 — broad set_disable_timing review warning
           (SDC-036, already correct — pinned).
  Case 6 — undocumented set_case_analysis rationale lint
           (SDC-150, already correct — pinned).

These are analysis-level checks only: none of them claim STA equivalence,
signoff correctness, or complete SDC correctness.
"""

import pytest
from checker import check_sdc
from constraint_interactions import analyze_interactions


def _codes(result):
    return [i.code for i in result.issues]


def _warnings(result, code):
    return [i for i in result.warnings if i.code == code]


# ── Case 1: clock uncertainty setup vs hold ──────────────────────────────────

class TestCase1ClockUncertaintySetupHold:
    BASE = "create_clock -name bap1_tck -period 4.0 [get_ports bap1_tck]\n"

    def test_setup_hold_pair_not_override(self):
        """A. setup + hold pair → valid distinct constraints, no override."""
        text = self.BASE + (
            "set_clock_uncertainty 0.08 -hold [get_clocks {bap1_tck}]\n"
            "set_clock_uncertainty 0.1 -setup [get_clocks {bap1_tck}]\n"
        )
        ia = analyze_interactions(text)
        assert not any(f["code"] == "SDC-068" for f in ia.findings), \
            "setup and hold uncertainty are distinct analysis types — no override"
        assert not any(f["code"] == "SDC-067" for f in ia.findings)

    def test_two_setups_different_values_still_override(self):
        """B. two setup uncertainties with different values → still an override."""
        text = self.BASE + (
            "set_clock_uncertainty 0.08 -setup [get_clocks bap1_tck]\n"
            "set_clock_uncertainty 0.10 -setup [get_clocks bap1_tck]\n"
        )
        ia = analyze_interactions(text)
        assert any(f["code"] == "SDC-068" for f in ia.findings)

    def test_two_holds_different_values_still_override(self):
        """B. two hold uncertainties with different values → still an override."""
        text = self.BASE + (
            "set_clock_uncertainty 0.08 -hold [get_clocks bap1_tck]\n"
            "set_clock_uncertainty 0.12 -hold [get_clocks bap1_tck]\n"
        )
        ia = analyze_interactions(text)
        assert any(f["code"] == "SDC-068" for f in ia.findings)

    def test_exact_duplicate_hold_still_duplicate(self):
        """Identical restatement of the same hold uncertainty → duplicate."""
        text = self.BASE + (
            "set_clock_uncertainty 0.08 -hold [get_clocks bap1_tck]\n"
            "set_clock_uncertainty 0.08 -hold [get_clocks bap1_tck]\n"
        )
        ia = analyze_interactions(text)
        assert any(f["code"] == "SDC-067" for f in ia.findings)

    def test_flag_value_form_pair_unaffected(self):
        """Existing '-setup <v>' / '-hold <v>' style stays clean (no regression)."""
        text = self.BASE + (
            "set_clock_uncertainty -setup 0.15 [get_clocks bap1_tck]\n"
            "set_clock_uncertainty -hold 0.08 [get_clocks bap1_tck]\n"
        )
        ia = analyze_interactions(text)
        assert not ia.findings


# ── Case 2: input delay vs clock period ──────────────────────────────────────

class TestCase2InputDelayVsPeriod:

    def test_delay_far_exceeding_period_warned(self):
        text = ("create_clock -name PLL0_CKOUT1 -period 0.8333 "
                "[get_ports PLL0_CKOUT1]\n"
                "set_input_delay 20.0 -clock PLL0_CKOUT1 [get_ports some_input]\n")
        result = check_sdc(text)
        sdc_008 = [i for i in result.errors if i.code == "SDC-008"]
        assert len(sdc_008) == 1
        # Evidence: both values and the referenced clock named in the finding.
        msg = sdc_008[0].msg
        assert "20.0" in msg and "0.8333" in msg and "PLL0_CKOUT1" in msg
        assert sdc_008[0].line == 2

    def test_reasonable_delay_not_flagged(self):
        text = ("create_clock -name CLK -period 10.0 [get_ports CLK]\n"
                "set_input_delay 2.0 -clock CLK [get_ports DATA_IN]\n")
        result = check_sdc(text)
        assert not any(i.code == "SDC-008" for i in result.errors)


# ── Case 3: multicycle setup / hold recognition ──────────────────────────────

class TestCase3MulticycleSetupHold:
    CLOCKS = ("create_clock -name CLK_A -period 10.0 [get_ports clk_a]\n"
              "create_clock -name CLK_B -period 12.0 [get_ports clk_b]\n")
    SETUP = ("set_multicycle_path 2 -setup "
             "-from [get_clocks CLK_A] -to [get_clocks CLK_B]\n")

    def test_setup_only_warns(self):
        result = check_sdc(self.CLOCKS + self.SETUP)
        assert len(_warnings(result, "SDC-021")) == 1

    def test_separate_hold_command_suppresses(self):
        """Hold fix in a SEPARATE command on identical endpoints is recognized
        (semantic pairing, NOT textual adjacency)."""
        hold = ("set_multicycle_path 1 -hold "
                "-from [get_clocks CLK_A] -to [get_clocks CLK_B]\n")
        result = check_sdc(self.CLOCKS + self.SETUP + hold)
        assert not _warnings(result, "SDC-021")

    def test_hold_recognized_with_unrelated_commands_between(self):
        """The externally-reported false-negative shape: unrelated commands
        between setup and hold must not break recognition."""
        text = (self.CLOCKS + self.SETUP +
                "# unrelated command\n"
                "set_clock_uncertainty 0.1 -setup [get_clocks CLK_A]\n\n"
                "# hold command appears later\n"
                "set_multicycle_path 1 -hold "
                "-from [get_clocks CLK_A] -to [get_clocks CLK_B]\n")
        result = check_sdc(text)
        assert not _warnings(result, "SDC-021")

    def test_hold_brace_collection_form_recognized(self):
        """Confirmed external false negative: '[get_clocks {CLK_A}]' is the
        same scope as '[get_clocks CLK_A]'. Must be recognized as the fix."""
        hold = ("set_multicycle_path 1 -hold "
                "-from [get_clocks {CLK_A}] -to [get_clocks {CLK_B}]\n")
        result = check_sdc(self.CLOCKS + self.SETUP + hold)
        assert not _warnings(result, "SDC-021"), \
            "brace-collection form of the same endpoints must count as the hold fix"

    def test_hold_reversed_flag_order_recognized(self):
        hold = ("set_multicycle_path 1 -hold "
                "-to [get_clocks CLK_B] -from [get_clocks CLK_A]\n")
        result = check_sdc(self.CLOCKS + self.SETUP + hold)
        assert not _warnings(result, "SDC-021")

    def test_four_cycle_with_three_hold(self):
        text = (self.CLOCKS +
                "set_multicycle_path 4 -setup "
                "-from [get_clocks CLK_A] -to [get_clocks CLK_B]\n"
                "set_multicycle_path 3 -hold "
                "-from [get_clocks CLK_A] -to [get_clocks CLK_B]\n")
        result = check_sdc(text)
        assert not _warnings(result, "SDC-021")

    def test_hierarchical_bit_select_names_brace_form(self):
        """Real-world hierarchical names containing bit selects
        (g_ca53_cpu[1].u_ca53_cpu/...) must pair across brace forms."""
        clocks = ("create_clock -name bap1_tck -period 4.0 "
                  "[get_ports bap1_tck]\n")
        setup = ("set_multicycle_path 2 -setup "
                 "-from [get_clocks g_ca53_cpu[1].u_ca53_cpu/clk_a] "
                 "-to [get_clocks g_ca53_cpu[1].u_ca53_cpu/clk_b]\n")
        hold = ("set_multicycle_path 1 -hold "
                "-from [get_clocks {g_ca53_cpu[1].u_ca53_cpu/clk_a}] "
                "-to [get_clocks g_ca53_cpu[1].u_ca53_cpu/clk_b]\n")
        result = check_sdc(clocks + setup + hold)
        assert not _warnings(result, "SDC-021"), \
            "bit-select hierarchical endpoint must pair with its brace form"

    def test_multi_member_different_set_does_not_credit(self):
        text = (self.CLOCKS +
                "set_multicycle_path 2 -setup "
                "-from [get_clocks {CLK_A CLK_B}] -to [get_clocks X]\n"
                "set_multicycle_path 1 -hold "
                "-from [get_clocks {B_CLK_A CLK_B}] -to [get_clocks X]\n")
        # Member SETS differ ({CLK_A, CLK_B} vs {B_CLK_A, CLK_B}) even though
        # both are written in brace form — must NOT count as the fix.
        result = check_sdc(text)
        assert len(_warnings(result, "SDC-021")) == 1

    def test_multi_member_equal_set_recognized(self):
        text = (self.CLOCKS +
                "set_multicycle_path 2 -setup "
                "-from [get_clocks {CLK_A CLK_B}] -to [get_clocks X]\n"
                "set_multicycle_path 1 -hold "
                "-from [get_clocks {CLK_B CLK_A}] -to [get_clocks X]\n")
        result = check_sdc(text)
        assert not _warnings(result, "SDC-021")

    def test_different_scope_does_not_credit(self):
        text = (self.CLOCKS +
                "create_clock -name CLK_C -period 15.0 [get_ports clk_c]\n" +
                self.SETUP +
                "set_multicycle_path 1 -hold "
                "-from [get_clocks CLK_C] -to [get_clocks CLK_B]\n")
        result = check_sdc(text)
        assert len(_warnings(result, "SDC-021")) == 1

    def test_reversed_scope_does_not_credit(self):
        text = (self.CLOCKS + self.SETUP +
                "set_multicycle_path 1 -hold "
                "-from [get_clocks CLK_B] -to [get_clocks CLK_A]\n")
        result = check_sdc(text)
        assert len(_warnings(result, "SDC-021")) == 1, \
            "source/destination reversal is a different path scope"

    def test_wildcard_scope_does_not_credit_concrete(self):
        text = (self.CLOCKS + self.SETUP +
                "set_multicycle_path 1 -hold "
                "-from [get_clocks *] -to [get_clocks CLK_B]\n")
        result = check_sdc(text)
        assert len(_warnings(result, "SDC-021")) == 1

    def test_incorrect_hold_value_still_credits_existence(self):
        """Documented product rule: SDC-021 is an EXISTENCE check — any -hold
        on provably identical endpoints counts as the fix. The hold VALUE is
        deliberately not second-guessed (multicycle hold semantics depend on
        launch/capture edge intent that static text cannot prove)."""
        text = (self.CLOCKS + self.SETUP +
                "set_multicycle_path 2 -hold "
                "-from [get_clocks CLK_A] -to [get_clocks CLK_B]\n")
        result = check_sdc(text)
        assert not _warnings(result, "SDC-021")


# ── Case 4: set_max_delay without -datapath_only ─────────────────────────────

class TestCase4MaxDelayDatapathOnly:
    BASE = "create_clock -name CLK -period 10.0 [get_ports CLK]\n"

    def test_without_datapath_only_review_warning(self):
        text = self.BASE + "set_max_delay 5.0 -from [get_ports A] -to [get_ports B]\n"
        result = check_sdc(text)
        sdc_027 = _warnings(result, "SDC-027")
        assert len(sdc_027) == 1
        assert "hold" in sdc_027[0].msg.lower()   # review-oriented wording

    def test_with_datapath_only_no_warning(self):
        text = self.BASE + ("set_max_delay 5.0 -datapath_only "
                            "-from [get_ports A] -to [get_ports B]\n")
        result = check_sdc(text)
        assert not _warnings(result, "SDC-027")


# ── Case 5: broad set_disable_timing ─────────────────────────────────────────

class TestCase5BroadDisableTiming:
    BASE = "create_clock -name CLK -period 10.0 [get_ports CLK]\n"

    def test_broad_disable_warns(self):
        text = self.BASE + "set_disable_timing [get_cells u_some_cell]\n"
        result = check_sdc(text)
        sdc_036 = _warnings(result, "SDC-036")
        assert len(sdc_036) == 1
        assert "all arcs" in sdc_036[0].msg.lower()
        assert sdc_036[0].line == 2

    def test_scoped_disable_clean(self):
        text = self.BASE + \
            "set_disable_timing -from A -to B [get_cells u_some_cell]\n"
        result = check_sdc(text)
        assert not _warnings(result, "SDC-036")


# ── Case 6: undocumented set_case_analysis ───────────────────────────────────

class TestCase6CaseAnalysisRationale:
    BASE = "create_clock -name CLK -period 10.0 [get_ports CLK]\n"

    def test_undocumented_warns(self):
        text = self.BASE + "set_case_analysis 0 [get_ports test_mode]\n"
        result = check_sdc(text)
        assert len(_warnings(result, "SDC-150")) == 1

    def test_preceding_comment_accepted(self):
        text = (self.BASE +
                "# async CDC - two-flop synchronizer, no timing path\n"
                "set_case_analysis 0 [get_ports test_mode]\n")
        result = check_sdc(text)
        assert not _warnings(result, "SDC-150")

    def test_inline_comment_accepted(self):
        text = (self.BASE +
                "set_case_analysis 0 [get_ports test_mode] "
                ";# test mode disabled for functional timing\n")
        result = check_sdc(text)
        assert not _warnings(result, "SDC-150")


# ── Determinism ───────────────────────────────────────────────────────────────

class TestDeterministicOutput:
    CASE1 = ("create_clock -name bap1_tck -period 4.0 [get_ports bap1_tck]\n"
             "set_clock_uncertainty 0.08 -hold [get_clocks {bap1_tck}]\n"
             "set_clock_uncertainty 0.1 -setup [get_clocks {bap1_tck}]\n")
    CASE3 = ("create_clock -name CLK_A -period 10.0 [get_ports clk_a]\n"
             "create_clock -name CLK_B -period 12.0 [get_ports clk_b]\n"
             "set_multicycle_path 2 -setup "
             "-from [get_clocks CLK_A] -to [get_clocks CLK_B]\n"
             "set_multicycle_path 1 -hold "
             "-from [get_clocks {CLK_A}] -to [get_clocks {CLK_B}]\n")

    def _fingerprint(self, text):
        r = check_sdc(text)
        return tuple(sorted((i.sev, i.code, i.line) for i in r.issues))

    @pytest.mark.parametrize("text", [CASE1, CASE3])
    def test_same_input_same_findings(self, text):
        assert self._fingerprint(text) == self._fingerprint(text)

    def test_interaction_summary_deterministic(self):
        s1 = analyze_interactions(self.CASE1).summary()
        s2 = analyze_interactions(self.CASE1).summary()
        assert s1 == s2
