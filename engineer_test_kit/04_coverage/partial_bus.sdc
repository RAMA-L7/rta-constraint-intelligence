# Partial bus coverage: apb_paddr is a 12-bit bus but only [3:0] gets an
# input delay - expect a partial-coverage finding (SDC-065). apb_pwdata,
# apb_psel, apb_penable, apb_pwrite are unconstrained (SDC-064).
set sdc_version 2.2
set_units -time ns -capacitance pF

create_clock -name clk -period 10.0 [get_ports clk]
create_generated_clock -name clk_div2 \
    -source [get_ports clk] -divide_by 2 \
    [get_pins u_div2/out]

# Only the low nibble of the 12-bit address bus is constrained
set_input_delay -max 1.5 -min 0.2 -clock clk [get_ports apb_paddr[3:0]]

set_output_delay -max 2.0 -min 0.5 -clock clk [get_ports apb_pready]
