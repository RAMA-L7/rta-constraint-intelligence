# RD03 — Generated clock hierarchy: primary → div2 → div4, plus a PLL x2.
# clk_ref 5.0ns (200MHz) → div2: divide_by 2 ⇒ period 10.0ns (100MHz)
#                          → div4: divide_by 2 ⇒ period 20.0ns (50MHz)
#                     pll_2x: multiply_by 2 ⇒ period 2.5ns (400MHz)
set sdc_version 2.1

create_clock -name clk_ref -period 5.0 [get_ports clk_ref]

create_generated_clock -name div2 \
    -master_clock clk_ref -source [get_ports clk_ref] \
    -divide_by 2 [get_pins U_DIV2/clkout]
create_generated_clock -name div4 \
    -master_clock div2 -source [get_pins U_DIV2/clkout] \
    -divide_by 2 [get_pins U_DIV4/clkout]
create_generated_clock -name pll_2x \
    -master_clock clk_ref -source [get_ports clk_ref] \
    -multiply_by 2 [get_pins U_PLL/clkout]

set_clock_uncertainty -setup 0.05 -hold 0.03 [get_clocks clk_ref]
set_clock_uncertainty -setup 0.1 -hold 0.05 [get_clocks {div2 div4 pll_2x}]

set_input_delay -max 0.7 -min 0.2 -clock clk_ref [get_ports {din*}]
set_output_delay -max 0.6 -min 0.15 -clock clk_ref [get_ports {dout*}]
set_input_delay -max 1.2 -min 0.3 -clock div4 [get_ports {slow_in*}]
set_output_delay -max 1.0 -min 0.25 -clock div4 [get_ports {slow_out*}]

# div2/div4/pll_2x are all derived from clk_ref → same domain, no groups needed.
set_false_path -from [get_ports rst_n] -to [all_registers]
set_operating_conditions WORST
