# Unconstrained reset tree: rst_n drives every flop reset pin in the block
# but has no timing exception. Async reset deassertion and CDC paths are
# unconstrained - expect SDC-151.
set sdc_version 2.2
set_units -time ns -capacitance pF

create_clock -name clk -period 10.0 [get_ports clk]
create_generated_clock -name clk_div2 \
    -source [get_ports clk] -divide_by 2 \
    [get_pins u_div2/out]

set_input_delay -max 1.5 -min 0.2 -clock clk [get_ports apb_psel]
set_output_delay -max 2.0 -min 0.5 -clock clk [get_ports apb_pready]
