# Input delay (12.0ns) exceeds the clock period (10.0ns) - expect SDC-008.
set sdc_version 2.2
set_units -time ns -capacitance pF

create_clock -name clk -period 10.0 [get_ports clk]

set_input_delay -max 12.0 -clock clk [get_ports apb_psel]
set_output_delay -max 2.0 -clock clk [get_ports apb_pready]
