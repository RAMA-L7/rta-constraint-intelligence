# HR13 — multiple simultaneous blockers: undefined clock reference (SDC-046),
# contradictory case analysis (SDC-049), max<min window (SDC-069). All must
# appear in blockers; overall BLOCKED.
set sdc_version 2.2
create_clock -name clk_core -period 10.0 [get_ports clk_core]
set_input_delay -max 2.0 -clock ghost_clk [get_ports din]
set_case_analysis 0 [get_ports mode]
set_case_analysis 1 [get_ports mode]
set_max_delay 5 -from [get_ports a] -to [get_ports b]
set_min_delay 8 -from [get_ports a] -to [get_ports b]
