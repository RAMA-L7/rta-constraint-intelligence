# ============================================================================
# APB UART block constraints - reference (good) state
# Design : apb_uart_top (APB slave + UART core, two-clock block)
# Netlist: apb_uart_top.v + apb_uart_core.v (shared/)
# Expected: 0 errors; a few review warnings (SDC-020 confirm false path,
# SDC-151-153 should NOT fire because rst_n and scan are constrained).
# ============================================================================
set sdc_version 2.2
set_units -time ns -capacitance pF -resistance kohm -voltage V

# --- Primary clock (PLL output entering the block) ---
create_clock -name clk -period 10.0 -waveform {0 5.0} [get_ports clk]

# --- Generated clock from the on-chip /2 divider ---
create_generated_clock -name clk_div2 \
    -source [get_ports clk] -divide_by 2 \
    [get_pins u_div2/out]

# --- Clock modeling ---
set_clock_uncertainty -setup 0.15 -hold 0.08 [get_clocks clk]
set_clock_transition 0.10 [get_clocks clk]
set_propagated_clock [get_clocks {clk clk_div2}]

# --- DFT mode pins: functional mode only ---
# DFT: scan disabled in functional mode
set_case_analysis 0 [get_ports scan_en]
# DFT: test mode off
set_case_analysis 0 [get_ports test_mode]

# --- APB slave interface (inputs) ---
set_input_delay -max 1.5 -min 0.2 -clock clk \
    [get_ports {apb_psel apb_penable apb_pwrite apb_paddr[*] apb_pwdata[*]}]

# --- APB read data + ready (outputs) ---
set_output_delay -max 2.0 -min 0.5 -clock clk \
    [get_ports {apb_prdata[*] apb_pready}]

# --- UART serial output ---
set_output_delay -max 3.0 -min 0.5 -clock clk_div2 [get_ports txd]

# Async reset deassertion: rst_n drives all flops; cut the reset-to-data paths
set_false_path -from [get_ports rst_n] -to [all_registers]

# Async serial loopback between UART rx and tx: no timing path in this block
set_false_path -from [get_ports rxd] -to [get_ports txd]
