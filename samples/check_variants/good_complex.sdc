# VARIANT A: Well-formed complex SDC
set sdc_version 2.2
set_units -time ns -capacitance pF -resistance kOhm

create_clock -name clk_fast -period 2.0 [get_ports clk_fast]
create_clock -name clk_slow -period 10.0 [get_ports clk_slow]
create_generated_clock -name clk_div2 -source [get_ports clk_fast] -divide_by 2 [get_pins div_clk_reg]

set_clock_uncertainty -setup 0.15 -hold 0.075 [get_clocks clk_fast]
set_clock_uncertainty -setup 0.20 -hold 0.10 [get_clocks clk_slow]
set_clock_latency -source 0.30 [all_clocks]
set_clock_transition 0.10 [all_clocks]
set_propagated_clock [all_clocks]
set_clock_groups -asynchronous -group [get_clocks clk_fast] -group [get_clocks clk_slow]

set_input_delay -max 0.8 -clock clk_fast [get_ports {data_in data_addr}]
set_input_delay -min 0.2 -clock clk_fast [get_ports {data_in data_addr}]
set_output_delay -max 1.0 -clock clk_fast [get_ports data_out]
set_output_delay -min 0.3 -clock clk_fast [get_ports data_out]

set_false_path -from [get_ports rst_n]
set_false_path -from [get_pins async_sync_reg*]

set_max_fanout 16 [all_inputs]
set_max_transition 0.15 [all_nets]
set_max_capacitance 0.08 [all_nets]

set_operating_conditions -max SS_0p8V_125C
set_timing_derate -early -cell_delay 1.08 [all_nets]
set_timing_derate -late -cell_delay 0.92 [all_nets]

set_max_dynamic_power 50 mW
set_dont_use [get_lib_cells */SLOW_*]
