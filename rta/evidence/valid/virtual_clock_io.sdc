# SDC with a virtual clock for an external interface (e.g. DDR controller I/O).
set sdc_version 2.1
set_units -time ns -capacitance pF

create_clock -name clk_core -period 4.0 [get_ports clk]
create_clock -name vclk_ddr -period 2.5

set_clock_uncertainty -setup 0.1 -hold 0.05 [get_clocks vclk_ddr]

set_input_delay -max 0.8 -min 0.2 -clock vclk_ddr [get_ports {ddr_din[*]}]
set_output_delay -max 1.0 -min 0.3 -clock vclk_ddr [get_ports {ddr_dout[*]}]

set_false_path -from [get_clocks clk_core] -to [get_clocks vclk_ddr] -to [get_ports ddr_dout[*]]
set_clock_groups -asynchronous -group [get_clocks clk_core] -group [get_clocks vclk_ddr]
