# EDGE CASE: Extremely large values, negatives, scientific notation
# Expected: No crashes, graceful handling of unusual numeric formats

# ═══════════════════════════════════════════════════════════════
#  SDC Lint — Reorganized Constraint File
# ═══════════════════════════════════════════════════════════════


# ── SDC Version ───────────────────────────────────────

set sdc_version 2.2

# ── Units ─────────────────────────────────────────────

set_units -time ns -capacitance pF

# ── Clock Definitions ─────────────────────────────────

create_clock -name clk_fast -period 0.05 [get_ports clk_fast]

# ── Clock Attributes ──────────────────────────────────

set_clock_uncertainty -setup 100 [get_clocks clk_fast]

# ── False Paths ───────────────────────────────────────

set_false_path \
  -from [get_ports x] \
  -to [get_pins very/deep/path/hierarchy/that/goes/on/and/on/and/on/and/on/and/on] \
  -through [get_pins {a b c d e f g h i j k l m n o p}]

# ── Design Rule Constraints ───────────────────────────

set_max_fanout 9999 [all_inputs]
