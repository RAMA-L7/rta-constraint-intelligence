# HR14 — realistic clean handoff candidate: 2 clocks + virtual interface
# clock, clock groups, uncertainty, min/max+rise/fall I/O delays, MCP
# setup/hold pair, legal max/min window, case analysis, electrical.
# Readiness: READY_WITH_ADVISORIES (a few heuristic advisories allowed) —
# must NOT be BLOCKED and must NOT be forced REVIEW_REQUIRED by harmless
# informational findings.
set sdc_version 2.2
set_units -time ns -capacitance pF
create_clock -name clk_core -period 5.0 [get_ports clk_core]
create_clock -name clk_io -period 10.0 [get_ports clk_io]
create_clock -name vclk_src -period 3.33
create_clock -name vclk_dst -period 6.66
set_clock_groups -asynchronous -group [get_clocks clk_core] \
                 -group [get_clocks clk_io] -group [get_clocks vclk_src] \
                 -group [get_clocks vclk_dst]
set_clock_uncertainty -setup 0.15 -hold 0.07 [get_clocks clk_core]
set_clock_uncertainty -setup 0.2 -hold 0.1 [get_clocks clk_io]
set_propagated_clock [get_clocks {clk_core clk_io}]
set_input_delay -max 2.0 -min 0.5 -clock clk_core [get_ports {d0 d1 d2 d3}]
set_input_delay -rise -max 2.2 -clock clk_core [get_ports d0]
set_input_delay -fall -max 2.2 -clock clk_core [get_ports d0]
set_input_delay -max 3.0 -min 1.0 -clock clk_io [get_ports {din_a din_b}]
set_input_delay -max 1.0 -clock vclk_src [get_ports data_in] -add_delay
set_input_delay -max 0.5 -clock vclk_src [get_ports data_in] -add_delay
set_output_delay -max 4.0 -min 1.0 -clock clk_core [get_ports {q0 q1}]
set_output_delay -max 5.0 -min 1.5 -clock clk_io [get_ports qout]
set_multicycle_path 2 -setup -from [get_clocks clk_io] -to [get_clocks clk_core]
set_multicycle_path 1 -hold -from [get_clocks clk_io] -to [get_clocks clk_core]
set_max_delay 12 -datapath_only -from [get_clocks clk_io] -to [get_clocks clk_core]
set_min_delay 3 -from [get_clocks clk_io] -to [get_clocks clk_core]
set_case_analysis 0 [get_ports mode]
set_load 0.05 [get_ports {q0 q1}]
set_input_transition 0.2 [get_ports {d0 d1 d2 d3 din_a din_b data_in}]
set_max_transition 0.3 [all_outputs]
set_max_capacitance 0.2 [all_outputs]
set_max_fanout 20 [all_outputs]
set_operating_conditions -max SSG
set_timing_derate -early -cell_delay 1.1 -late -cell_delay 0.9
set_clock_latency -source 0.5 [get_clocks {clk_core clk_io}]
set_clock_transition 0.1 [get_clocks {clk_core clk_io}]
set_clock_gating_check -setup 0.5 -hold 0.2 [get_clocks clk_core]
set_min_pulse_width 0.5 [get_clocks clk_core]
set_clock_jitter 0.02 [get_clocks clk_core]
set_wire_load_mode top
set_dont_use {INVD0}
group_path -name g_core -to [get_ports {q0 q1}]
