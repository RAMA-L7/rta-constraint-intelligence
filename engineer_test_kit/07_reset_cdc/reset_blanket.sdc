# Blanket wildcard false path covers the reset tree: no targeted exception
# exists for rst_n, so the sync-input vs deassertion distinction is hidden
# (SDC-152). Also triggers the confirm-genuine-false-path review (SDC-020).
set sdc_version 2.2
set_units -time ns -capacitance pF

create_clock -name clk -period 10.0 [get_ports clk]
create_generated_clock -name clk_div2 \
    -source [get_ports clk] -divide_by 2 \
    [get_pins u_div2/out]

set_false_path -from [all_inputs] -to [all_registers]
