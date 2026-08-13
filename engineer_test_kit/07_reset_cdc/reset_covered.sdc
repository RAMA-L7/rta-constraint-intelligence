# Clean reset handling: a targeted false path on the reset tree, so
# SDC-151..153 must NOT fire. (SDC-020 confirm-genuine-false-path still
# appears - that is expected for any false path.)
set sdc_version 2.2
set_units -time ns -capacitance pF

create_clock -name clk -period 10.0 [get_ports clk]
create_generated_clock -name clk_div2 \
    -source [get_ports clk] -divide_by 2 \
    [get_pins u_div2/out]

# Async reset deassertion: rst_n drives all flops; cut the reset-to-data paths
set_false_path -from [get_ports rst_n] -to [all_registers]

set_input_delay -max 1.5 -min 0.2 -clock clk [get_ports apb_psel]
set_output_delay -max 2.0 -min 0.5 -clock clk [get_ports apb_pready]
