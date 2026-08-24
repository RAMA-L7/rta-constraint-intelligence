# =============================================================================
# External-engineer-feedback regression benchmark
# Design : rama_soc_top  |  Tech: 28nm CMOS
# Purpose: Permanent regression benchmark capturing real-world SDC patterns
#          reported by an external engineer during field testing of Rta.
#
# This is NOT a proof of complete SDC validation. It exercises the specific
# externally-reported patterns so their handling stays correct:
#   1. set_clock_uncertainty setup/hold as separate analysis types (value-first)
#   2. input-delay sanity vs referenced clock period
#   3. multicycle setup/hold pairing across equivalent endpoint syntaxes
#   4. set_max_delay without -datapath_only review
#   5. broad set_disable_timing scope review
#   6. undocumented set_case_analysis rationale lint
#
# Architecture:
#   u_core    - CPU core domain        (CLK_A, 250 MHz)
#   u_bridge  - peripheral bridge      (CLK_B, 83 MHz)
#   u_mem     - memory controller      (CLK_C, ~303 MHz)
#   SAFE_CLK  - test/safe domain       (10 ns)
#   PLL0_CKOUT1 - PLL output           (1.2 GHz DDR PHY interface)
# =============================================================================

set sdc_version 2.2
set_units -time ns -capacitance pF -resistance kOhm -voltage V

# -----------------------------------------------------------------------------
# Clock definitions - one per functional domain
# -----------------------------------------------------------------------------

# CPU core domain
create_clock -name CLK_A -period 4.0 [get_ports clk_a]

# Peripheral bridge domain (slow async domain)
create_clock -name CLK_B -period 12.0 [get_ports clk_b]

# Memory controller domain
create_clock -name CLK_C -period 3.3 [get_ports clk_mem]

# Safe/test clock domain
create_clock -name CLK_SAFE -period 10.0 [get_ports SAFE_CLK]

# PLL output feeding the DDR PHY - intentionally fast
create_clock -name PLL0_CKOUT1 -period 0.8333 [get_ports PLL0_CKOUT1]

# Divided PLL copy used inside the core
create_generated_clock -name PLL_DIV2 -divide_by 2 \
    -source [get_ports PLL0_CKOUT1] [get_pins u_core/gen_div/q]

# All domains are asynchronous to each other (per-clock groups)
set_clock_groups -asynchronous \
    -group [get_clocks CLK_A] \
    -group [get_clocks CLK_B] \
    -group [get_clocks CLK_C] \
    -group [get_clocks CLK_SAFE] \
    -group [get_clocks PLL0_CKOUT1]

# -----------------------------------------------------------------------------
# Clock attributes
# -----------------------------------------------------------------------------

# CPU core: uncertainty written in value-first form (external pattern #1).
# Setup and hold are DIFFERENT analysis types - never duplicates/overrides.
set_clock_uncertainty 0.08 -hold [get_clocks {CLK_A}]
set_clock_uncertainty 0.1 -setup [get_clocks {CLK_A}]

# Bridge: genuine same-type re-specification (tightened after post-CTS).
# The later setup value replaces the earlier one - this IS an override.
set_clock_uncertainty 0.10 -setup [get_clocks {CLK_B}]
set_clock_uncertainty 0.20 -setup [get_clocks {CLK_B}]

# Memory controller: classic flag-value form for reference
set_clock_uncertainty -setup 0.15 [get_clocks CLK_C]
set_clock_uncertainty -hold 0.08 [get_clocks CLK_C]

set_clock_latency -source 0.40 [get_clocks CLK_A]
set_clock_latency -source 0.60 [get_clocks CLK_B]
set_propagated_clock [all_clocks]
set_clock_transition 0.10 [all_clocks]
set_clock_jitter -clock [get_clocks CLK_A] -cycle 0.05

# -----------------------------------------------------------------------------
# I/O constraints
# -----------------------------------------------------------------------------

# DDR PHY capture: external delay dominates the 0.8333 ns period
# (external pattern #2 - sanity check must fire WITH evidence).
set_input_delay 20.0 \
    -clock PLL0_CKOUT1 \
    [get_ports DATA_IN]
set_input_delay -min 0.2 -clock PLL0_CKOUT1 [get_ports DATA_IN]

# Safe-domain inputs: comfortable relationship to the 10 ns period
set_input_delay 2.0 \
    -clock CLK_SAFE \
    [get_ports SAFE_DATA]
set_input_delay -min 0.5 -clock CLK_SAFE [get_ports SAFE_DATA]

set_output_delay -max 0.5 -clock PLL0_CKOUT1 [get_ports DATA_OUT]
set_output_delay -min 0.2 -clock PLL0_CKOUT1 [get_ports DATA_OUT]
set_output_delay -max 1.0 -clock CLK_SAFE [get_ports SAFE_DATA_OUT]
set_output_delay -min 0.3 -clock CLK_SAFE [get_ports SAFE_DATA_OUT]

set_driving_cell -lib_cell BUF_X8 -pin Z [all_inputs]
set_load 0.05 [all_outputs]

# -----------------------------------------------------------------------------
# Multicycle paths (external pattern #3 - the critical regression)
# -----------------------------------------------------------------------------

# CPU -> Bridge CDC crossing: 2-cycle setup, 1-cycle hold correction.
# The hold fix uses DIFFERENT-but-equivalent endpoint syntax and comes AFTER
# unrelated commands - semantic pairing, never textual adjacency.
set_multicycle_path 2 -setup \
    -from [get_clocks CLK_A] \
    -to [get_clocks {CLK_B}]

# (unrelated commands deliberately placed between the setup and its hold fix)

set_max_delay 5.0 -from [get_ports DATA_IN] -to [get_ports DATA_OUT]

# Hold correction for the CPU->Bridge CDC crossing (capture edge moved one
# cycle later); endpoints deliberately re-written in brace form
set_multicycle_path 1 -hold \
    -from [get_clocks {CLK_A}] \
    -to [get_clocks CLK_B]

# Bridge -> Memory: engineer FORGOT the hold correction entirely.
# SDC-021 must fire for this path.
set_multicycle_path 3 -setup \
    -from [get_clocks CLK_B] \
    -to [get_clocks CLK_C]

# Memory -> CPU read return: hold correction exists but was written against
# the WRONG destination (typo: CLK_B instead of CLK_A). A hold on a different
# scope must NEVER satisfy this setup - SDC-021 must still fire.
# (Flag order deliberately varied here, as engineers do in practice.)
set_multicycle_path 2 -setup \
    -to [get_clocks CLK_A] \
    -from [get_clocks CLK_C]
# Hold correction - but note the destination typo below (kept intentionally)
set_multicycle_path 1 -hold \
    -from [get_clocks CLK_C] \
    -to [get_clocks CLK_B]

# Safe -> Core configuration crossing: the engineer's 4-setup / 3-hold pair.
set_multicycle_path 4 -setup \
    -from [get_clocks CLK_SAFE] \
    -to [get_clocks CLK_A]
# Safe-domain crossing hold correction matching the 4-cycle setup above
set_multicycle_path 3 -hold \
    -from [get_clocks CLK_SAFE] \
    -to [get_clocks CLK_A]

# Async reset synchronizer inside the core (documented exception)
set_false_path -from [get_cells u_core/cdc_async/meta_ff] \
               -to   [get_cells u_core/rst_sync/ff_meta]

# Datapath-only limiter on the PHY crossing (scoped variant of the above
# max-delay intent - must NOT raise the missing-datapath_only advisory)
set_max_delay 5.0 \
    -datapath_only \
    -from [get_ports DATA_IN] \
    -to [get_ports DATA_OUT]

# -----------------------------------------------------------------------------
# Design rules and electrical constraints
# -----------------------------------------------------------------------------

set_max_fanout 20 [all_inputs]
set_max_transition 0.25 [all_nets]
set_max_capacitance 0.15 [all_nets]
set_operating_conditions -max WORST
set_timing_derate -late -cell_delay 0.95 [all_nets]

# External pattern #6: an undocumented mode constant hides in this file.
set_timing_derate -early -cell_delay 1.05 [all_nets]


set_case_analysis 0 [get_ports test_mode]

# -----------------------------------------------------------------------------
# Timing disables (external pattern #5)
# -----------------------------------------------------------------------------

# Intended ONLY for the divided-clock arc - but written without -from/-to,
# which silently disables ALL arcs through the cell. Review required.
set_disable_timing [get_cells u_core]

# Properly scoped disable on the bridge clock gate
set_disable_timing \
    -from CLK \
    -to Q \
    [get_cells u_bridge/clk_gate]

# -----------------------------------------------------------------------------
# Functional / test mode (external pattern #6)
# -----------------------------------------------------------------------------

set_case_analysis 0 [get_ports test_mode]

# Functional mode: test_mode_2 forced inactive for normal timing analysis
set_case_analysis 0 [get_ports test_mode_2]

set_case_analysis 1 [get_ports scan_mode] ;# scan mode constraint

set_ideal_network [get_ports rst_n]
