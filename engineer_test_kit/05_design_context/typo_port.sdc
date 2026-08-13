# Typo'd object reference: 'datat_in' does not exist in the netlist
# (the real port is 'apb_paddr'). Expect SDC-055 - the constraint silently
# applies to nothing and the real port stays unconstrained.
set sdc_version 2.2
set_units -time ns -capacitance pF

create_clock -name clk -period 10.0 [get_ports clk]
create_generated_clock -name clk_div2 \
    -source [get_ports clk] -divide_by 2 \
    [get_pins u_div2/out]

set_input_delay -max 1.5 -min 0.2 -clock clk [get_ports datat_in]
set_output_delay -max 2.0 -min 0.5 -clock clk [get_ports apb_pready]
