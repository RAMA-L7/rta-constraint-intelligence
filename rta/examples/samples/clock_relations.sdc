# ============================================================
# clock_relations.sdc — Blog post quiz example
# Source: Ausdia "Seemingly Simple Clock Relations Quiz"
# https://www.ausdia.com/blog/5/seemingly-simple-clock-relations-quiz/filter/0
#
# CLKA and CLKB share port CLKAB (physically exclusive)
# CLKC is on a separate port (asynchronous to CLKA/CLKB)
# CLKA_DIV2 and CLKB_DIV2 are generated from CLKA and CLKB
#
# The set_clock_groups below contain INCORRECT constraints
# for the analyzer to detect.
# ============================================================

# ═══════════════════════════════════════════════════════════════
#  SDC Lint — Reorganized Constraint File
# ═══════════════════════════════════════════════════════════════


# ── SDC Version ───────────────────────────────────────

set sdc_version 2.2

# ── Units ─────────────────────────────────────────────

set_units -time ns -capacitance pF

# ── Clock Definitions ─────────────────────────────────

create_clock -name CLKA  -period 1.00 [get_ports CLKAB]
create_clock -name CLKB  -period 1.50 [get_ports CLKAB] -add
create_clock -name CLKC  -period 2.30 [get_ports CLKC]

# ── Generated Clock Definitions ───────────────────────

create_generated_clock -name CLKA_DIV2 -divide_by 2 \ -source [get_ports CLKAB] -master_clock CLKA \
create_generated_clock -name CLKB_DIV2 -divide_by 2 \ -source [get_ports CLKAB] -master_clock CLKB \

# ── Clock Groups (CDC) ────────────────────────────────

set_clock_groups -asynchronous \ -group [get_clocks CLKA] \
set_clock_groups -logically_exclusive \ -group [get_clocks CLKB] \
set_clock_groups -asynchronous \ -group [get_clocks CLKB] \
set_clock_groups -asynchronous \ -group [get_clocks CLKC] \
