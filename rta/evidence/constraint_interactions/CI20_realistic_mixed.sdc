# CI20 — realistic mixed design
# Legal: min/max, rise/fall, setup/hold uncertainty, MCP setup/hold pair.
# Defects: duplicate din_b delay, overridden dout_a delay, max<min conflict.
set sdc_version 2.1

create_clock -name clk_a -period 10.0 [get_ports clk_a]
create_clock -name clk_b -period 20.0 [get_ports clk_b]

set_input_delay -max 2.0 -clock clk_a [get_ports din_a]
set_input_delay -min 0.5 -clock clk_a [get_ports din_a]
set_input_delay -rise -max 1.5 -clock clk_a [get_ports din_a]
set_input_delay -fall -max 1.5 -clock clk_a [get_ports din_a]

set_input_delay -max 2.0 -clock clk_a [get_ports din_b]
set_input_delay -max 2.0 -clock clk_a [get_ports din_b]

set_output_delay -max 3.0 -clock clk_a [get_ports dout_a]
set_output_delay -max 4.0 -clock clk_a [get_ports dout_a]

set_clock_uncertainty -setup 0.1 -hold 0.05 [get_clocks clk_a]

set_multicycle_path 2 -setup -from [get_ports a] -to [get_ports b]
set_multicycle_path 1 -hold -from [get_ports a] -to [get_ports b]

set_max_delay 5 -from [get_ports a] -to [get_ports b]
set_min_delay 8 -from [get_ports a] -to [get_ports b]
