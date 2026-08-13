# Nonexistent hierarchy path: u_core/u_nope does not exist (the real
# instance under u_core does not exist - only u_core itself). Expect a
# hierarchy finding (SDC-057).
set sdc_version 2.2
set_units -time ns -capacitance pF

create_clock -name clk -period 10.0 [get_ports clk]
create_generated_clock -name clk_div2 \
    -source [get_ports clk] -divide_by 2 \
    [get_pins u_div2/out]

# The parent instance u_core/u_nope does not exist in the hierarchy
set_false_path -from [get_pins u_core/u_nope/D] -to [get_ports txd]
