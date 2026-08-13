# Documented exception - the comment within 3 lines explains why this path
# is false, so SDC-150 must NOT fire.
set sdc_version 2.2
set_units -time ns -capacitance pF

create_clock -name clk -period 10.0 [get_ports clk]

# Async serial loopback between UART rx and tx: no timing path in this block
set_false_path -from [get_ports rxd] -to [get_ports txd]
