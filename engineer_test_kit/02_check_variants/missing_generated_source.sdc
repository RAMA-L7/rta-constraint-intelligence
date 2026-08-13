# Generated clock without -source - expect SDC-003.
set sdc_version 2.2
set_units -time ns -capacitance pF

create_clock -name clk -period 10.0 [get_ports clk]
create_generated_clock -name clk_div2 -divide_by 2 [get_pins u_div2/out]
