# V2 - changed constraints (period 10->12, txd delay 3.0->2.5, new input
# delay on apb_penable, and the reset exception added)
set sdc_version 2.2
set_units -time ns -capacitance pF

create_clock -name clk -period $CLK_PERIOD [get_ports clk]
create_generated_clock -name clk_div2 \
    -source [get_ports clk] -divide_by 2 \
    [get_pins u_div2/out]

set_input_delay -max 1.5 -min 0.2 -clock clk \
    [get_ports {apb_psel apb_penable apb_pwdata[*]}]
set_output_delay -max $TXD_DELAY -min 0.5 -clock clk [get_ports txd]

# Async reset deassertion: rst_n drives all flops; cut the reset-to-data paths
set_false_path -from [get_ports rst_n] -to [all_registers]
# Async serial loopback between UART rx and tx: no timing path in this block
set_false_path -from [get_ports rxd] -to [get_ports txd]
