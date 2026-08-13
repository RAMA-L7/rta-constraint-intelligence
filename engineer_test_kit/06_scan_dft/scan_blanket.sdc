# DFT design (scan_en has a case analysis) with a fully-blanket cut
# -from [all_inputs] -to [all_registers]. The wildcard cannot distinguish
# scan-chain-present flops from non-scan flops (SDC-155), and it also
# silently covers the rst_n reset tree (SDC-152).
set sdc_version 2.2
set_units -time ns -capacitance pF

create_clock -name clk -period 10.0 [get_ports clk]
create_generated_clock -name clk_div2 \
    -source [get_ports clk] -divide_by 2 \
    [get_pins u_div2/out]

# DFT: scan disabled in functional mode
set_case_analysis 0 [get_ports scan_en]
set_false_path -from [all_inputs] -to [all_registers]
