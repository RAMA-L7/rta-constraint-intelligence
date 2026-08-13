# Changed constraints - regression introduced: the output delays on
# apb_prdata/apb_pready/txd were removed. Baseline comparison must flag
# NEW findings and the gate must FAIL under STRICT.
set sdc_version 2.2
set_units -time ns -capacitance pF

create_clock -name clk -period 10.0 [get_ports clk]
create_generated_clock -name clk_div2 \
    -source [get_ports clk] -divide_by 2 \
    [get_pins u_div2/out]

set_clock_uncertainty -setup 0.15 -hold 0.08 [get_clocks clk]
set_clock_transition 0.10 [get_clocks clk]
set_propagated_clock [get_clocks {clk clk_div2}]

# DFT: scan disabled in functional mode
set_case_analysis 0 [get_ports scan_en]
# DFT: test mode off
set_case_analysis 0 [get_ports test_mode]

set_input_delay -max 1.5 -min 0.2 -clock clk \
    [get_ports {apb_psel apb_penable apb_pwrite apb_paddr[*] apb_pwdata[*]}]

# Async reset deassertion: rst_n drives all flops; cut the reset-to-data paths
set_false_path -from [get_ports rst_n] -to [all_registers]
# Async serial loopback between UART rx and tx: no timing path in this block
set_false_path -from [get_ports rxd] -to [get_ports txd]
