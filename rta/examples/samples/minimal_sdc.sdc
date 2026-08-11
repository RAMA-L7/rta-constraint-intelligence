set sdc_version 2.2
set_units -time ns -capacitance pF
create_clock -name clk -period 5.0 [get_ports clk]
set_input_delay -max 1.5 -clock clk [get_ports data_in]
set_output_delay -max 2.0 -clock clk [get_ports data_out]
