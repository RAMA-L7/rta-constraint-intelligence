# RD06 — Timing exceptions (legitimate set)
# Includes a multicycle WITHOUT hold fix (SDC-021 should fire — it is a real
# best-practice issue), false paths, max/min delay.
set sdc_version 2.1

create_clock -name clk_a -period 4.0 [get_ports clk_a]
create_clock -name clk_b -period 6.0 [get_ports clk_b]

set_input_delay -max 0.8 -min 0.2 -clock clk_a [get_ports {din*}]
set_output_delay -max 0.6 -min 0.15 -clock clk_a [get_ports {dout*}]
set_input_delay -max 1.0 -min 0.3 -clock clk_b [get_ports {bin*}]
set_output_delay -max 0.8 -min 0.2 -clock clk_b [get_ports {bout*}]

set_clock_groups -asynchronous \
    -group [get_clocks clk_a] \
    -group [get_clocks clk_b]

# Legitimate async false path (CDC)
set_false_path -from [get_clocks clk_a] -to [get_clocks clk_b]

# Multicycle on a registered multiplier: setup 2 but NO hold fix → SDC-021
set_multicycle_path -setup 2 -from [get_pins U_MUL/A] -to [get_pins U_MUL/Z]

# A correctly-fixed multicycle pair
set_multicycle_path -setup 2 -from [get_ports din*] -to [get_pins U_PIPE/D]
set_multicycle_path -hold 1 -from [get_ports din*] -to [get_pins U_PIPE/D]

# Max delay with datapath_only (SDC-027 must NOT fire)
set_max_delay 3.5 -datapath_only -from [get_ports din*] -to [get_pins U_DP/D]
# Min delay
set_min_delay 0.5 -from [get_ports bin*] -to [get_pins U_MUL/A]

set_operating_conditions WORST
