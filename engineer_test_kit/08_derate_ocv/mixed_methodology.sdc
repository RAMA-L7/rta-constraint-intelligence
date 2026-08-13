# Derate methodology mix: flat set_timing_derate values sit alongside a
# sigma-based form in the same file. Flat and statistical/table derates are
# not meant to be mixed - pick one methodology per corner (SDC-157, info).
set sdc_version 2.2
set_units -time ns -capacitance pF

create_clock -name clk -period 10.0 [get_ports clk]

set_timing_derate -early -cell_delay 1.04 -late -cell_delay 0.96
set_timing_derate -early -cell_delay 1.10 -late -cell_delay 0.90 -sigma 0.35
