# ============================================================================
# DMA engine block constraints - V1 (known-good baseline)
# Design : dma_engine_top (AHB slave + stream engine, two-clock block)
# Netlist: dma_engine_top.v
# State  : the previous, reviewed revision. Every port is constrained, the
#          CDC domains are grouped, and each exception carries a rationale.
# Expected (STRICT gate vs this baseline): 0 errors, PASS.
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

# --- Clock groups: AHB (and its /2) is asynchronous to the peripheral clock ---
set_clock_groups -asynchronous \
    -group [get_clocks {clk_ahb clk_div2}] \
    -group [get_clocks clk_periph]

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
set_output_delay -max 1.5 -min 0.3 -clock clk_div2 [get_ports stream_out]

# --- Peripheral-domain handshake (async CDC into clk_ahb) ---
set_input_delay -max 1.2 -min 0.2 -clock clk_periph [get_ports dma_req]
set_output_delay -max 1.8 -min 0.4 -clock clk_periph [get_ports dma_ack]
set_output_delay -max 1.8 -min 0.4 -clock clk_periph [get_ports irq]

# Async reset deassertion: rst_n drives all flops; cut the reset-to-data paths
set_false_path -from [get_ports rst_n] -to [all_registers]

# DMA request/ack handshake is source-synchronous across the async domain;
# the clock group already cuts it, the explicit path documents the intent.
set_false_path -from [get_ports dma_req] -to [get_ports dma_ack]
