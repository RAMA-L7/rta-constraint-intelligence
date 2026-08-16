"""
Regression tests for the realistic high-coverage fixture
(``engineer_test_kit/19_high_coverage/``).

Protects the semantic contract of ``ahb_spi_ctrl.sdc``:

  - 100% SDC constraint coverage (39/39 items) — every category the coverage
    engine can legitimately recognize is represented by a real constraint.
  - 0 checker errors / 0 warnings (the fixture is genuinely well-constructed).
  - 4 clocks / 6 pairs / 0 mismatches / 0 missing clock-group constraints.
  - The 7 categories that the older ``real_design_full.sdc`` (82.1%) lacks
    are each covered by a dedicated construct; removing any ONE drops the
    score to exactly 38/39 and flags that category — proving coverage is real,
    not hard-coded.
  - Design-aware mode resolves every object reference against the netlist.

These are SEMANTIC assertions (counts, scores, rule IDs, relationships) — not
raw output formatting. No engine behavior is modified to make them pass; the
fixture succeeds because the SDC is genuinely complete and coherent.
"""

import io
import os
import re

import pytest

from coverage import parse_sdc_coverage
from checker import check_sdc
from clock_relations import analyze_clock_relations

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "..", "engineer_test_kit",
                           "19_high_coverage")
SDC_PATH = os.path.join(FIXTURE_DIR, "ahb_spi_ctrl.sdc")
V1_PATH = os.path.join(FIXTURE_DIR, "ahb_spi_ctrl_v1.sdc")
NETLIST_PATH = os.path.join(FIXTURE_DIR, "ahb_spi_ctrl_top.v")


@pytest.fixture(scope="module")
def fixture_sdc() -> str:
    with io.open(SDC_PATH, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture(scope="module")
def v1_sdc() -> str:
    with io.open(V1_PATH, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture(scope="module")
def fixture_netlist() -> str:
    with io.open(NETLIST_PATH, "r", encoding="utf-8") as f:
        return f.read()


# ── Coverage contract ─────────────────────────────────────────────────────────

class TestHighCoverageContract:
    """The fixture must hit 100% on every legitimate coverage category."""

    def test_total_denominator_is_39(self, fixture_sdc):
        result = parse_sdc_coverage(fixture_sdc, SDC_PATH)
        assert result.total_items == 39

    def test_full_coverage_100(self, fixture_sdc):
        result = parse_sdc_coverage(fixture_sdc, SDC_PATH)
        assert result.total_present == 39
        assert result.total_missing == 0
        assert result.score == 100.0

    def test_all_six_categories_full(self, fixture_sdc):
        result = parse_sdc_coverage(fixture_sdc, SDC_PATH)
        assert len(result.categories) == 6
        for cat in result.categories:
            assert cat.covered == cat.total, f"{cat.name} not fully covered"

    def test_every_covered_item_has_a_real_construct(self, fixture_sdc):
        """Every 'present' item must trace to an actual SDC command line —
        coverage is real, not derived from a hard-coded score."""
        result = parse_sdc_coverage(fixture_sdc, SDC_PATH)
        for cat in result.categories:
            for item in cat.items:
                if not item.present:
                    continue
                cmd = item.cmd
                # Multi-flag items are satisfied by a flag inside a command
                # (e.g. 'set_input_delay -min' lives in '-max 1.5 -min 0.3').
                if re.match(r'^set_(input|output)_delay -min$', cmd):
                    base = cmd.rsplit(' ', 1)[0]
                    assert re.search(re.escape(base) + r'[^\n]* -min\b',
                                     fixture_sdc), (
                        f"item '{item.name}' needs {cmd} inside {base}")
                    continue
                if '/' in cmd:
                    # compound items (e.g. '-early/-late') need each flag
                    for part in cmd.split('/'):
                        flag = part.split()[-1]
                        assert re.search(
                            r'set_timing_derate[^\n]* ' + re.escape(flag) + r'\b',
                            fixture_sdc), (
                            f"item '{item.name}' needs {flag} in set_timing_derate")
                    continue
                assert re.search(re.escape(cmd), fixture_sdc), (
                    f"item '{item.name}' claims {cmd} but the command "
                    f"is absent from the fixture")

    def test_stats_equal_collections(self, fixture_sdc):
        result = parse_sdc_coverage(fixture_sdc, SDC_PATH)
        assert result.stats["total_items"] == 39
        assert result.stats["present"] == 39
        assert result.stats["missing"] == 0
        assert result.stats["score_pct"] == 100.0


class TestCoverageIsReal:
    """Removal tests: deleting one constraint must flip exactly its category."""

    def _remove(self, text: str, cmd: str) -> str:
        text = re.sub(r"(?m)^#.*\n", "", text)  # strip comments
        out = re.sub(r"(?m)^" + re.escape(cmd) + r".*\n", "", text)
        assert cmd in text, f"command {cmd} not found in fixture"
        assert cmd not in out
        return out

    @pytest.mark.parametrize("cmd,category", [
        ("set_clock_jitter", "Clocks"),
        ("set_clock_gating_check", "Clocks"),
        ("set_min_delay", "Timing Exceptions"),
        ("group_path", "Timing Exceptions"),
        ("set_wire_load_mode", "AOCV / Derate"),
        ("set_ideal_network", "Power / DFT"),
        ("set_min_pulse_width", "Power / DFT"),
    ])
    def test_removing_one_constraint_flips_its_category(self, fixture_sdc,
                                                        cmd, category):
        text = self._remove(fixture_sdc, cmd)
        result = parse_sdc_coverage(text, "x.sdc")
        assert result.total_present == 38, f"removing {cmd} should drop 39->38"
        cat = next(c for c in result.categories if c.name == category)
        missing = [i.name for i in cat.items if not i.present]
        assert missing, f"{category} should now have a missing item"

    def test_removing_all_seven_matches_v1_821(self, fixture_sdc):
        text = fixture_sdc
        for cmd in ("set_clock_jitter", "set_clock_gating_check",
                    "set_min_delay", "group_path", "set_wire_load_mode",
                    "set_ideal_network", "set_min_pulse_width"):
            text = self._remove(text, cmd)
        result = parse_sdc_coverage(text, "x.sdc")
        assert result.total_present == 32
        assert round(result.score, 1) == 82.1


class TestV1V2Relationship:
    """V1 is the earlier 82.1% revision; V2 (the fixture) is 100%."""

    def test_v1_coverage_is_821(self, v1_sdc):
        result = parse_sdc_coverage(v1_sdc, V1_PATH)
        assert result.total_present == 32
        assert result.total_missing == 7
        assert round(result.score, 1) == 82.1

    def test_v1_missing_categories_are_the_seven(self, v1_sdc):
        result = parse_sdc_coverage(v1_sdc, V1_PATH)
        missing = sorted(i.name for c in result.categories
                         for i in c.items if not i.present)
        assert missing == sorted([
            "Clock jitter", "Clock gating check", "Min delay", "Group paths",
            "Wire load mode", "Ideal network", "Min pulse width",
        ])


# ── Checker / clock-relations contract ───────────────────────────────────────

class TestCheckerContract:
    def test_fixture_is_clean(self, fixture_sdc):
        """0 errors AND 0 warnings — a genuinely well-constructed SDC."""
        result = check_sdc(fixture_sdc)
        assert result.errors == [], [f"{e.code}: {e.msg}" for e in result.errors]
        assert result.warnings == [], [f"{w.code}: {w.msg}" for w in result.warnings]

    def test_rule_ids_and_counts(self, fixture_sdc):
        result = check_sdc(fixture_sdc)
        stats = result.stats
        assert stats["Clocks"] == 3            # 2 primary + 1 virtual
        assert stats["Generated clocks"] == 1  # clk_ahb_div2
        assert stats["Virtual clocks"] == 1    # vclk_ahb
        assert stats["Input delays"] == 2
        assert stats["Output delays"] == 3
        assert stats["False paths"] == 2
        assert stats["Multicycle paths"] == 2
        assert stats["Clock groups"] == 1
        assert stats["Case analysis"] == 2
        assert stats["Timing derate"] == 4
        assert stats["Group paths"] == 2

    def test_clock_relations_fully_declared(self, fixture_sdc):
        """All 5 async pairs are declared in set_clock_groups — 0 mismatches
        and 0 missing-constraint findings (P1-2 semantics preserved)."""
        rel = analyze_clock_relations(fixture_sdc)
        assert rel.stats["clocks"] == 4
        assert rel.stats["pairs"] == 6
        assert rel.stats["mismatches"] == 0
        assert rel.stats["missing"] == 0
        assert rel.stats["advisories"] == 0
        assert rel.stats["synchronous"] == 1      # clk_ahb / clk_ahb_div2
        assert rel.stats["asynchronous"] == 5
        # stats keys must equal their collections (P1-2/P1-7 contract)
        assert rel.stats["mismatches"] == len(rel.mismatches)
        assert rel.stats["missing"] == len(rel.missing_constraints)


# ── Design-aware contract ─────────────────────────────────────────────────────

class TestDesignAwareContract:
    def test_all_references_resolve(self, fixture_sdc, fixture_netlist):
        from design_context import parse_verilog
        from design_coverage import analyze_coverage

        outcome = parse_verilog(fixture_netlist, top="ahb_spi_ctrl_top")
        assert outcome.errors == []
        ctx = outcome.context
        assert ctx is not None
        assert ctx.top_module == "ahb_spi_ctrl_top"

        result = check_sdc(fixture_sdc, context=ctx)
        # No SDC-055/056/057 (object resolution) findings in design-aware mode
        codes = [f.code for f in result.errors + result.warnings]
        assert "SDC-055" not in codes, codes
        assert "SDC-056" not in codes, codes
        assert "SDC-057" not in codes, codes

        cov = analyze_coverage(fixture_sdc, ctx)
        summ = cov.summary()
        # every data port constrained; no unconstrained outputs
        assert summ["inputs"]["unconstrained"] == 0
        assert summ["outputs"]["unconstrained"] == 0
        # every timing exception resolves to real objects
        exc = summ["exceptions"]
        assert exc["objects_resolved"] == exc["total"] > 0
        assert exc["empty_collection"] == 0
