# DFT gap: scan_en is referenced in an exception but has NO set_case_analysis.
# Without a case value for function/capture (0) and scan shift (1), STA
# blends shift-timing and capture-timing paths into one report (SDC-154).
set sdc_version 2.2
set_units -time ns -capacitance pF

create_clock -name clk -period 10.0 [get_ports clk]
create_generated_clock -name clk_div2 \
    -source [get_ports clk] -divide_by 2 \
    [get_pins u_div2/out]

set_false_path -from [get_ports scan_en] -to [get_ports txd]
