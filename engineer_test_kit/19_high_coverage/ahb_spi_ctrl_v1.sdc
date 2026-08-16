# ============================================================================
# SDC Constraints for AHB_SPI_CTRL — AHB-slave SPI master controller
# Design : ahb_spi_ctrl_top  |  Tech: 40nm LP  |  Target: 100MHz AHB / 25MHz SPI
# Netlist: ahb_spi_ctrl_top.v (design-aware validation)
# Corner : WORST (SS_0P8V_125C)  |  Pre-CTS, pre-RC-extraction flow
#
# V1 — earlier reviewed revision of ahb_spi_ctrl.sdc. Missing the jitter,
# gating-check, min-delay, path-group, wire-load, ideal-network and min-pulse
# categories that V2 adds. Used to demonstrate `rta diff` semantics.

# ============================================================================

# ── SDC Version ───────────────────────────────────────────────

set sdc_version 2.2

# ── Units ─────────────────────────────────────────────────────

set_units -time ns -capacitance pF -resistance kOhm -voltage V

# ── Clock Definitions ─────────────────────────────────────────

# 100MHz AHB bus clock entering the block from the SoC clock tree
create_clock -name clk_ahb -period 10.0 [get_ports clk_ahb]
# 25MHz SPI reference clock from the SPI PLL (async to the AHB domain)
create_clock -name clk_spi -period 40.0 [get_ports clk_spi]
# Virtual AHB clock — external master timing reference for the AHB I/O
create_clock -name vclk_ahb -period 10.0 -virtual

# ── Generated Clock Definitions ───────────────────────────────

# /2 divider on the AHB clock — drives the internal SPI baud/tx engine.
# -source is the AHB clock port; the generated clock is observed at the
# divider output pin u_div2/out.
create_generated_clock -name clk_ahb_div2 \
  -source [get_ports clk_ahb] -divide_by 2 \
  -master_clock clk_ahb \
  [get_pins u_div2/out]

# ── Clock Attributes ──────────────────────────────────────────

set_clock_uncertainty -setup 0.15 -hold 0.075 [get_clocks clk_ahb]
set_clock_uncertainty -setup 0.30 -hold 0.15  [get_clocks clk_spi]
set_clock_uncertainty -setup 0.15 -hold 0.075 [get_clocks clk_ahb_div2]
set_clock_latency -source 0.40 [get_clocks {clk_ahb clk_spi clk_ahb_div2}]
set_clock_transition 0.10 [all_clocks]
set_propagated_clock [get_clocks {clk_ahb clk_spi clk_ahb_div2}]

# ── Clock Groups (CDC) ────────────────────────────────────────

# AHB domain (and its /2) is asynchronous to the SPI domain and to the
# virtual AHB reference clock — no deterministic phase relationship.
set_clock_groups -asynchronous \
  -group [get_clocks {clk_ahb clk_ahb_div2}] \
  -group [get_clocks clk_spi] \
  -group [get_clocks vclk_ahb]

# ── I/O Constraints ───────────────────────────────────────────

# AHB slave interface — input setup/hold vs the external AHB master (vclk_ahb)
set_input_delay -max 1.5 -min 0.3 -clock vclk_ahb \
  [get_ports {haddr hwdata hwrite hsel hready}]
# AHB read-data path — output setup/hold back to the external master
set_output_delay -max 1.8 -min 0.4 -clock vclk_ahb \
  [get_ports {hrdata hready_out}]
# SPI interface — input delay on MISO (async domain, vs clk_spi)
set_input_delay -max 2.0 -min 0.5 -clock clk_spi [get_ports spi_miso]
# SPI outputs — load timing vs clk_spi
set_output_delay -max 2.5 -min 0.6 -clock clk_spi \
  [get_ports {spi_sclk spi_mosi spi_cs_n}]
# Interrupt output — driven from the clk_ahb domain, timed vs vclk_ahb
set_output_delay -max 1.5 -min 0.3 -clock vclk_ahb [get_ports irq]
# Input slew model — BUF_X4 drive on all non-clock inputs
set_driving_cell -lib_cell BUF_X4 -pin Z \
  [remove_from_collection [all_inputs] [get_ports {clk_ahb clk_spi}]]
# Output load — 0.05pF on every output
set_load 0.05 [all_outputs]

# ── False Paths ───────────────────────────────────────────────

# Async reset deassertion — rst_n fans out to every flop; cut the
# reset-to-data paths (recovery/removal handled by reset synchronizer)
set_false_path -from [get_ports rst_n]

# SPI MISO -> AHB synchronizer: two-flop CDC synchronizer, no timing path
set_false_path -through [get_pins u_async/*]

# ── Multicycle Paths ──────────────────────────────────────────

# Multiply -> accumulate path in the core takes 2 cycles (setup), so the
# hold check must be relaxed to cycle 1 on the identical endpoints
set_multicycle_path -setup 2 -from [get_cells u_mul] -to [get_cells u_acc]
set_multicycle_path -hold  1 -from [get_cells u_mul] -to [get_cells u_acc]

# ── Max / Min Delay ───────────────────────────────────────────

# Datapath-only max delay on the SPI input -> sync stage: constrain the
# data path while leaving hold analysis on the same path untouched
set_max_delay -datapath_only 8.0 -from [get_ports spi_miso] -to [get_pins u_async/din]

# ── Path Groups ────────────────────────────────────────────────


# ── Case Analysis ─────────────────────────────────────────────

# Functional mode: scan and test inputs held inactive
set_case_analysis 0 [get_ports scan_en]
set_case_analysis 0 [get_ports test_mode]

# ── Disable Timing Arcs ───────────────────────────────────────

# Hold-fix buffer is not a real timing path — disable its arc
set_disable_timing -from A -to Z [get_cells u_hold_buf]

# ── Design Rule Constraints ───────────────────────────────────

set_max_fanout      16 [all_inputs]
set_max_transition  0.20 [all_nets]
set_max_capacitance 0.08 [all_nets]
set_max_area        50000

# ── Operating Conditions ──────────────────────────────────────

# WORST corner (SS_0P8V_125C) — setup-critical analysis corner
set_operating_conditions -max WORST

# ── Timing Derate (AOCV) ──────────────────────────────────────

set_timing_derate -late  -cell_delay 0.92 [all_nets]
set_timing_derate -early -cell_delay 1.08 [all_nets]
set_timing_derate -late  -net_delay  0.95 [all_nets]
set_timing_derate -early -net_delay  1.05 [all_nets]

# ── Wire Load Models ──────────────────────────────────────────


# ── Ideal Networks / Reset ────────────────────────────────────


# ── Power Constraints ─────────────────────────────────────────

set_max_dynamic_power 100 mW
set_max_leakage_power  10 mW

# ── Don't-Use Cells ───────────────────────────────────────────

set_dont_use [get_lib_cells */SLOW_*]
set_dont_use [get_lib_cells */WEAK_*]
