"""
Regression tests for the external-engineer-feedback SDC fixture.

Fixture: samples/external_feedback_regression.sdc

The fixture is a realistic multi-domain subsystem SDC (CPU core / bridge /
memory controller / safe domain / PLL interface) that permanently captures
the patterns reported by an external engineer during field testing:

  #1  set_clock_uncertainty value-first setup/hold pair  -> NOT an override
  #1b genuine same-type uncertainty re-specification     -> IS an override
  #2  input delay far exceeding referenced clock period  -> SDC-008 w/ evidence
  #2b reasonable input delay                             -> silent
  #3  multicycle hold fix in brace-form syntax after
      unrelated commands                                 -> recognized
  #3b multicycle setup with genuinely missing hold       -> SDC-021
  #3c multicycle hold fix on a DIFFERENT scope           -> never credits
  #3d engineer's 4-setup / 3-hold pair                   -> recognized
  #4  set_max_delay without vs with -datapath_only       -> SDC-027 only once
  #5  broad set_disable_timing                           -> SDC-036
  #6  undocumented set_case_analysis                     -> SDC-150

These tests execute the COMPLETE realistic fixture (not isolated toy
commands) and assert the exact expected finding profile. They prove Rta
handles the specific externally-reported patterns; they do NOT claim
complete SDC validation, STA equivalence, or signoff correctness.
"""

import pytest

from checker import check_sdc
from constraint_interactions import analyze_interactions

FIXTURE_PATH = (
    __import__("pathlib").Path(__file__).resolve().parent.parent
    / "samples" / "external_feedback_regression.sdc"
)


@pytest.fixture(scope="module")
def fixture_text():
    return FIXTURE_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def fixture_result(fixture_text):
    return check_sdc(fixture_text)


def _code_lines(result, code):
    return sorted(i.line for i in result.issues if i.code == code)


def _line_of(text, needle):
    """First 1-based line containing ``needle`` (must exist)."""
    for n, line in enumerate(text.splitlines(), start=1):
        if needle in line:
            return n
    raise AssertionError(f"fixture line not found: {needle!r}")


class TestFixtureProfile:
    """The complete-fixture finding profile must match expectations."""

    def test_uncertainty_setup_hold_pair_not_flagged(self, fixture_result):
        """Pattern #1: no duplicate/override between setup and hold."""
        assert not any(i.code == "SDC-067" for i in fixture_result.issues)

    def test_genuine_same_type_override_still_fires(self, fixture_text,
                                                     fixture_result):
        """Pattern #1b: the CLK_B setup->setup re-specification is an override,
        proving the Case-1 fix is selective."""
        ia = analyze_interactions(fixture_text)
        ovr = [f for f in ia.findings if f["code"] == "SDC-068"]
        assert len(ovr) == 1
        assert ovr[0]["category"] == "OVERRIDE"
        # Both values of the genuine override appear in the evidence.
        msg = ovr[0]["msg"]
        assert "0.1" in msg and "0.2" in msg

    def test_huge_input_delay_with_evidence(self, fixture_text, fixture_result):
        """Pattern #2: SDC-008 fires once, naming delay, period and clock."""
        sdc_008 = [i for i in fixture_result.errors if i.code == "SDC-008"]
        assert len(sdc_008) == 1
        msg = sdc_008[0].msg
        assert "20.0" in msg          # the delay
        assert "0.8333" in msg        # the referenced clock period
        assert "PLL0_CKOUT1" in msg   # the referenced clock
        assert sdc_008[0].line == _line_of(fixture_text,
                                           "set_input_delay 20.0")

    def test_reasonable_input_delay_not_flagged(self, fixture_result):
        """Pattern #2b: SAFE_DATA delay (2.0 ns vs 10 ns period) is silent."""
        # The only SDC-008 must be the PLL one (asserted elsewhere); here we
        # additionally confirm no error references CLK_SAFE.
        for i in fixture_result.errors:
            assert "CLK_SAFE" not in i.msg

    def test_multicycle_equivalent_syntax_recognized(self, fixture_result,
                                                     fixture_text):
        """Pattern #3: the A->B hold fix written '[get_clocks {CLK_A}]'
        (after unrelated commands) suppresses SDC-021 for its setup."""
        a_to_b_setup = _line_of(fixture_text,
                                "-to [get_clocks {CLK_B}]") - 1
        assert a_to_b_setup not in _code_lines(fixture_result, "SDC-021")

    def test_multicycle_missing_hold_fires(self, fixture_text, fixture_result):
        """Pattern #3b: B->C setup has no hold fix anywhere."""
        expected = _line_of(fixture_text, "set_multicycle_path 3 -setup")
        assert expected in _code_lines(fixture_result, "SDC-021")

    def test_multicycle_wrong_scope_never_credits(self, fixture_text,
                                                  fixture_result):
        """Pattern #3c: C->B hold must not satisfy the C->A setup."""
        # Locate the wrong-scope setup: the '-setup' block whose continuation
        # puts CLK_A in -to position (flag order deliberately varied).
        lines = fixture_text.splitlines()
        wrong_scope_line = None
        for n, line in enumerate(lines, start=1):
            if line.strip().startswith("set_multicycle_path 2 -setup"):
                block = " ".join(lines[n - 1:n + 2])
                if "-to [get_clocks CLK_A]" in block \
                        and "-from [get_clocks CLK_C]" in block:
                    wrong_scope_line = n
                    break
        assert wrong_scope_line is not None, "wrong-scope setup not found"
        assert wrong_scope_line in _code_lines(fixture_result, "SDC-021")
        # And the total count proves nothing else fired spuriously.
        assert len(_code_lines(fixture_result, "SDC-021")) == 2

    def test_multicycle_four_three_pair_recognized(self, fixture_text,
                                                   fixture_result):
        """Pattern #3d: SAFE->A 4-setup / 3-hold pair is complete."""
        safe_setup = _line_of(fixture_text, "set_multicycle_path 4 -setup")
        assert safe_setup not in _code_lines(fixture_result, "SDC-021")

    def test_max_delay_advisory_is_selective(self, fixture_text,
                                             fixture_result):
        """Pattern #4: SDC-027 fires only for the non-datapath_only command."""
        sdc_027 = [i for i in fixture_result.warnings
                   if i.code == "SDC-027"]
        assert len(sdc_027) == 1
        assert sdc_027[0].line == _line_of(
            fixture_text, "set_max_delay 5.0 -from [get_ports DATA_IN]")

    def test_broad_disable_timing_only(self, fixture_text, fixture_result):
        """Pattern #5: SDC-036 for u_core; scoped u_bridge disable clean."""
        sdc_036 = [i for i in fixture_result.warnings if i.code == "SDC-036"]
        assert len(sdc_036) == 1
        assert sdc_036[0].line == _line_of(
            fixture_text, "set_disable_timing [get_cells u_core]")

    def test_undocumented_case_analysis_only(self, fixture_text,
                                             fixture_result):
        """Pattern #6: SDC-150 for bare test_mode only."""
        sdc_150 = [i for i in fixture_result.warnings if i.code == "SDC-150"]
        assert len(sdc_150) == 1
        # Exact line equality distinguishes it from the documented
        # test_mode_2 command (same prefix).
        undocumented = _line_of(fixture_text,
                                "set_case_analysis 0 [get_ports test_mode]")
        assert "test_mode_2" not in fixture_text.splitlines()[undocumented - 1]
        assert sdc_150[0].line == undocumented


class TestFixtureDeterminism:
    """Same fixture input must produce byte-identical analysis output."""

    def _fingerprint(self, result):
        return tuple(sorted((i.sev, i.code, i.msg, i.line, i.line2)
                            for i in result.issues)), \
            tuple(sorted((n.code, n.msg) for n in result.info))

    def test_repeated_runs_identical(self, fixture_text):
        r1 = self._fingerprint(check_sdc(fixture_text))
        r2 = self._fingerprint(check_sdc(fixture_text))
        assert r1 == r2

    def test_interaction_analysis_identical(self, fixture_text):
        s1 = analyze_interactions(fixture_text).summary()
        s2 = analyze_interactions(fixture_text).summary()
        assert s1 == s2
