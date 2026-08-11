# HR15 — realistic NOT-ready design: several genuine handoff problems.
#  - undefined master clock on a generated clock (SDC-047, warning, BLOCKED)
#  - exception overlap fp vs mcp (SDC-070, review)
#  - no set_propagated_clock / derate / latency (heuristic reviews)
#  - contradictory max/min delay (SDC-069, BLOCKED)
# Overall readiness: BLOCKED (definite problems exist), with review items
# clearly separated so the engineer knows what blocks vs what to review.
set sdc_version 2.2
create_clock -name clk_core -period 10.0 [get_ports clk_core]
create_generated_clock -name div2 -source [get_ports clk_core] \
    -master_clock missing_master -divide_by 2 [get_pins u_a/q]
set_input_delay -max 2.0 -min 0.5 -clock clk_core [get_ports din]
set_output_delay -max 3.0 -min 1.0 -clock clk_core [get_ports dout]
set_false_path -from [get_ports a] -to [get_ports b]
set_multicycle_path 2 -from [get_ports a] -to [get_ports b]
set_max_delay 5 -from [get_ports a] -to [get_ports b]
set_min_delay 8 -from [get_ports a] -to [get_ports b]
