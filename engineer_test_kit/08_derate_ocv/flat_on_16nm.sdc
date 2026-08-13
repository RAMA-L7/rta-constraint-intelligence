# Flat-only derate on an advanced (<=16nm) flow: the corner name
# SS_0P72V_16C signals a small-node methodology, yet only flat
# set_timing_derate values are used. Advisory (SDC-156) - flat OCV can be
# legitimate, hence info severity.
set sdc_version 2.2
set_units -time ns -capacitance pF

set_operating_conditions SS_0P72V_16C
create_clock -name clk -period 10.0 [get_ports clk]

set_timing_derate -early -cell_delay 1.04 -late -cell_delay 0.96
