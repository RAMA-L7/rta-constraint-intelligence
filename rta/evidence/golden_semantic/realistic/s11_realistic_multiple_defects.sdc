# Realistic SDC with THREE injected semantic defects:
#  1) set_input_delay -clock nonexistent_fast (line 14)
#  2) create_generated_clock -master_clock ghost_master (line 8)
#  3) set_case_analysis 0 then 1 on same test_mode pin (lines 22-23)
set sdc_version 2.1
create_clock -name clk_a -period 10.0 [get_ports clk_a]
create_clock -name clk_b -period 5.0 [get_ports clk_b]
create_generated_clock -name div2 -master_clock ghost_master \
    -source [get_ports clk_a] -divide_by 2 [get_pins U_DIV/CLK]

set_input_delay -max 2.0 -min 0.5 -clock clk_a [get_ports din]
set_input_delay -max 3.0 -min 0.8 -clock nonexistent_fast [get_ports dout]
set_output_delay -max 1.0 -min 0.2 -clock clk_b [get_ports dq]

set_clock_groups -asynchronous -group [get_clocks clk_a] -group [get_clocks clk_b]
set_false_path -from [get_clocks clk_a] -to [get_clocks clk_b]
set_multicycle_path -setup 2 -hold 1 -from [get_ports din] -to [get_ports dq]

set_case_analysis 0 [get_ports test_mode]
set_case_analysis 1 [get_ports test_mode]
set_load 0.3 [all_outputs]
set_max_transition 0.2 [all_nets]
