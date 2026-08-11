# Realistic SoC SDC with EXACTLY ONE semantic defect: set_input_delay
# references clk_ddr which is never defined (line 27 in this file).
set sdc_version 2.1
set_units -time ns -capacitance pF -resistance kohm -voltage V \
          -current mA

set CLK_PERIOD_CPU 2.0
set CLK_PERIOD_IO  10.0

create_clock -name clk_cpu -period $CLK_PERIOD_CPU \
    -waveform {0 1.0} [get_ports clk_cpu]
create_clock -name clk_io -period $CLK_PERIOD_IO \
    -waveform {0 5.0} [get_ports clk_io]

create_generated_clock -name pll_2x -source [get_ports clk_cpu] \
    -multiply_by 2 [get_pins U_PLL/CLKOUT]
create_generated_clock -name div_4 -master_clock pll_2x \
    -source [get_pins U_PLL/CLKOUT] -divide_by 4 [get_pins U_DIV/CLK]

set_clock_uncertainty -setup 0.05 -hold 0.03 [get_clocks clk_cpu]
set_clock_groups -asynchronous \
    -group [get_clocks {clk_cpu pll_2x div_4}] \
    -group [get_clocks clk_io]

set_input_delay -max 0.5 -min 0.1 -clock clk_cpu \
    [get_ports {data_in*}]
set_input_delay -max 1.5 -min 0.3 -clock clk_ddr [get_ports rst_n]
set_output_delay -max 0.4 -min 0.05 -clock clk_cpu \
    [get_ports {data_out*}]
set_output_delay -max 2.0 -min 0.5 -clock clk_io [get_ports irq*]

set_driving_cell -lib_cell INV_X1 -clock clk_cpu [all_inputs]
set_input_transition 0.08 [get_ports {data_in*}]
set_load 0.5 [all_outputs]

set_false_path -from [get_clocks clk_io] -to [get_clocks clk_cpu]
set_multicycle_path -setup 3 -from [get_ports data_in*] \
    -to [get_pins U_DIV/*/D]
set_multicycle_path -hold 2 -from [get_ports data_in*] \
    -to [get_pins U_DIV/*/D]
set_max_delay 2.5 -datapath_only -from [get_ports data_in*] \
    -to [get_pins U_DIV/*/D]

set_case_analysis 1 [get_ports test_mode]
set_max_transition 0.3 [get_clocks clk_cpu]
set_max_capacitance 1.0 [all_outputs]
set_max_fanout 20 [all_inputs]
set_operating_conditions SSG0P72V125C
