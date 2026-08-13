# messy constraint file - deliberately unformatted to exercise the linter
# Wrong section order, mixed case, irregular spacing, trailing spaces.
CREATE_CLOCK -name clk -period 10.0 [get_ports clk]
set_false_path -from [get_ports rxd] -to [get_ports txd]
create_generated_clock -name clk_div2 -source [get_ports clk] -divide_by 2 [get_pins u_div2/out]
set_input_delay -max 1.5 -min 0.2 -clock clk [get_ports {apb_psel apb_penable apb_pwrite apb_paddr[*] apb_pwdata[*]}]   
set_output_delay -max 2.0 -min 0.5 -clock clk [get_ports {apb_prdata[*] apb_pready}]
set_clock_uncertainty -setup 0.15 -hold 0.08 [get_clocks clk]
set_propagated_clock [get_clocks {clk clk_div2}]
