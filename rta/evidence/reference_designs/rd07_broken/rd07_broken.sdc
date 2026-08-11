# RD07 — INTENTIONALLY BROKEN design (derived from RD01)
# Injected defects (see manifest.json):
#   D1: set_input_delay -clock nonexistent_clock  (undefined clock → SDC-046)
#   D2: create_generated_clock -master_clock ghost_master  (SDC-047)
#   D3: set_case_analysis 0 then 1 on same port  (SDC-049)
#   D4: set_clock_groups references undefined clock  (SDC-048)
#   D5: duplicate clock name  (SDC-002)
#   D6: input delay >= period  (SDC-008)
set sdc_version 2.1
set_units -time ns -capacitance pF -resistance kohm -voltage V \
          -current mA

create_clock -name clk_core -period 5.0 \
    -waveform {0 2.5} [get_ports clk_core]
create_clock -name clk_core -period 4.0 \
    -waveform {0 2.0} [get_ports clk_core]        # D5 duplicate name

create_generated_clock -name div2 \
    -master_clock ghost_master -source [get_ports clk_core] \
    -divide_by 2 [get_pins U_DIV/clkout]          # D2 undefined master

set_clock_uncertainty -setup 0.10 -hold 0.05 [get_clocks clk_core]

set_input_delay -max 0.8 -min 0.2 -clock clk_core \
    [get_ports {data_in* addr_bus*}]
set_input_delay -max 6.0 -min 2.0 -clock clk_core \
    [get_ports {slow_in*}]                        # D6 6.0 >= 5.0 → SDC-008
set_input_delay -max 0.5 -min 0.1 -clock nonexistent_clock \
    [get_ports {bad_in*}]                         # D1 undefined clock
set_output_delay -max 0.6 -min 0.15 -clock clk_core \
    [get_ports {data_out*}]

set_clock_groups -asynchronous \
    -group [get_clocks clk_core] \
    -group [get_clocks ghost_group_clock]         # D4 undefined in group

set_case_analysis 0 [get_ports test_mode]         # D3 conflicting values
set_case_analysis 1 [get_ports test_mode]

set_false_path -from [get_ports rst_n] -to [all_registers]
set_operating_conditions WORST
