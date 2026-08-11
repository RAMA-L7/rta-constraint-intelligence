# SDC with common errors — missing clocks, missing delays, bad case analysis
# Purpose: Test checker catches SDC-001, SDC-005, SDC-006, SDC-011

# ═══════════════════════════════════════════════════════════════
#  SDC Lint — Reorganized Constraint File
# ═══════════════════════════════════════════════════════════════


# ── SDC Version ───────────────────────────────────────

set sdc_version 2.2

# ── Units ─────────────────────────────────────────────

set_units -time ns -capacitance pF

# ── I/O Constraints ───────────────────────────────────

set_input_delay -max 1.5 -clock ref_clk [get_ports data_in]

# ── Max / Min Delay ───────────────────────────────────

set_max_delay 10.0 -from [get_ports a] -to [get_ports b]

# ── Case Analysis ─────────────────────────────────────

set_case_analysis invalid_val [get_ports test_mode]
