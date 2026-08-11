# RD05 — Multi-mode style constraints (static subset)
# Functional clock + test clock, mode pins via case analysis, and
# logically-exclusive clock groups for muxed functional/test modes.
set sdc_version 2.1
set_units -time ns -capacitance pF -resistance kohm -voltage V \
          -current mA

create_clock -name clk_func -period 4.0 -waveform {0 2.0} [get_ports clk_func]
create_clock -name clk_test -period 20.0 -waveform {0 10.0} [get_ports clk_test]

# The functional and test clocks are mux-selected → logically exclusive.
set_clock_groups -logically_exclusive \
    -group [get_clocks clk_func] \
    -group [get_clocks clk_test]

set_clock_uncertainty -setup 0.10 -hold 0.05 [get_clocks clk_func]
set_clock_uncertainty -setup 0.50 -hold 0.25 [get_clocks clk_test]

# Mode pins fixed per mode via case analysis
set_case_analysis 0 [get_ports test_mode]
set_case_analysis 0 [get_ports scan_en]

set_input_delay -max 0.8 -min 0.2 -clock clk_func \
    [get_ports {func_data_in*}]
set_output_delay -max 0.6 -min 0.15 -clock clk_func \
    [get_ports {func_data_out*}]
set_input_delay -max 2.0 -min 0.5 -clock clk_test [get_ports scan_in]
set_output_delay -max 2.0 -min 0.5 -clock clk_test [get_ports scan_out]

# Functional false paths (test-only paths don't matter in functional mode)
set_false_path -from [get_ports scan_in] -to [all_registers]
set_false_path -from [get_ports scan_en] -to [all_registers]

set_driving_cell -lib_cell INV_X1 [all_inputs]
set_load 0.5 [all_outputs]
set_operating_conditions TYP
