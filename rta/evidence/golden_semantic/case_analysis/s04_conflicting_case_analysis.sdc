# Golden: same pin assigned 0 then 1 → SDC-049 with both source lines.
create_clock -name c -period 10.0 [get_ports clk]
set_case_analysis 0 [get_ports mode]
set_case_analysis 1 [get_ports mode]
