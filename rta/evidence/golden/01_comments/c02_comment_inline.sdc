# Golden: trailing '#' text on a command line must not create phantom constraints.
create_clock -name real_clk -period 10 [get_ports clk] # master clock
set_input_delay -max 1.0 -min 0.2 -clock real_clk [all_inputs] # setup
set_output_delay -max 1.0 -min 0.2 -clock real_clk [all_outputs] # load
