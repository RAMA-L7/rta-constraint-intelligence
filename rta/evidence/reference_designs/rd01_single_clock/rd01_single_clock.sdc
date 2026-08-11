# RD01 — Single-clock logic block (e.g. a CPU core sub-block)
# 1 primary clock, complete I/O constraint set, one reset false path.
set sdc_version 2.1
set_units -time ns -capacitance pF -resistance kohm -voltage V \
          -current mA

create_clock -name clk_core -period 5.0 \
    -waveform {0 2.5} [get_ports clk_core]

set_clock_uncertainty -setup 0.10 -hold 0.05 [get_clocks clk_core]
set_clock_transition 0.08 [get_clocks clk_core]

set_input_delay -max 0.8 -min 0.2 -clock clk_core \
    [get_ports {data_in* addr_bus* ctrl_in}]
set_output_delay -max 0.6 -min 0.15 -clock clk_core \
    [get_ports {data_out* result* flags*}]

set_driving_cell -lib_cell INV_X1 -clock clk_core [all_inputs]
set_input_transition 0.1 [get_ports {data_in*}]
set_load 0.4 [all_outputs]

set_false_path -from [get_ports rst_n] -to [all_registers]

set_max_transition 0.3 [get_clocks clk_core]
set_max_capacitance 0.9 [all_outputs]
set_max_fanout 16 [all_inputs]
set_operating_conditions SSG0P72V125C
