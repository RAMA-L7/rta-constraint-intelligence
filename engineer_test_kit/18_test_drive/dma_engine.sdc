# ============================================================================
# DMA engine block constraints - V2 (current, under review)
# Design : dma_engine_top (AHB slave + stream engine, two-clock block)
# Netlist: dma_engine_top.v
# State  : an engineer's change to add the peripheral-domain handshake. The
#          change dropped the stream_out output delay and left the new
#          dma_req/dma_ack exception without a rationale comment.
# What Ṛta should find (the teaching points):
#   1. SDC-059 / SDC-065 — stream_out[*] lost its output delay: a data
#      output port is now unconstrained. This is the regression vs V1 and
#      what the CI gate must block.
#   2. SDC-020 / SDC-150 — the dma_req -> dma_ack false path has no rationale
#      comment: a reviewer cannot tell if it is genuinely false.
#   3. SDC-024 / SDC-062 — clk_periph is a third clock domain; the async
#      clock group covers only clk_ahb/clk_div2, so the peripheral-domain
#      CDC paths are un-flagged.
# ============================================================================
set sdc_version 2.2
set_units -time ns -capacitance pF -resistance kohm -voltage V

# --- Primary clocks (PLL outputs entering the block) ---
create_clock -name clk_ahb    -period 10.0 -waveform {0 5.0} [get_ports clk_ahb]
create_clock -name clk_periph -period 8.0  -waveform {0 4.0} [get_ports clk_periph]

# --- Generated clock from the on-chip /2 divider (AHB domain) ---
create_generated_clock -name clk_div2 \
    -source [get_ports clk_ahb] -divide_by 2 \
    [get_pins u_div2/out]

# --- Clock modeling ---
set_clock_uncertainty -setup 0.15 -hold 0.08 [get_clocks clk_ahb]
set_clock_transition 0.10 [get_clocks clk_ahb]
set_propagated_clock [get_clocks {clk_ahb clk_div2}]

# --- Clock groups: AHB (and its /2) is asynchronous to the peripheral clock.
# NOTE: clk_periph was added this revision but the group was not extended to
# cover it — the peripheral-domain CDC paths are now un-flagged (SDC-024). ---
set_clock_groups -asynchronous \
    -group [get_clocks {clk_ahb clk_div2}]

# --- DFT mode pins: functional mode only ---
set_case_analysis 0 [get_ports scan_en]
set_case_analysis 0 [get_ports test_mode]

# --- AHB slave interface (inputs) ---
set_input_delay -max 1.5 -min 0.2 -clock clk_ahb \
    [get_ports {ahb_addr ahb_wdata ahb_write ahb_sel}]

# --- AHB read data (outputs) ---
set_output_delay -max 2.0 -min 0.5 -clock clk_ahb \
    [get_ports ahb_rdata]

# --- Stream engine + DMA handshake (divided-clock domain) ---
set_input_delay -max 1.0 -min 0.1 -clock clk_div2 [get_ports stream_in]
# stream_out[*] has NO output delay in this revision — regression vs V1.

# --- Peripheral-domain handshake (async CDC into clk_ahb) ---
set_input_delay -max 1.2 -min 0.2 -clock clk_periph [get_ports dma_req]
set_output_delay -max 1.8 -min 0.4 -clock clk_periph [get_ports dma_ack]
set_output_delay -max 1.8 -min 0.4 -clock clk_periph [get_ports irq]

# Async reset deassertion: rst_n drives all flops; cut the reset-to-data paths
set_false_path -from [get_ports rst_n] -to [all_registers]

# NOTE: this path was added to cover the peripheral-domain handshake, but the
# clock group no longer covers clk_periph and this exception has no rationale
# comment (SDC-150) — it reads as a blanket async cut (SDC-020).
set_false_path -from [get_ports dma_req] -to [get_ports dma_ack]
