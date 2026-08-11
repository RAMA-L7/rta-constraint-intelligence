# Golden: -max/-min/-clock on continuation lines must still be seen (no SDC-028).
create_clock -name sys_clk -period 10.0 [get_ports clk]
set_input_delay \
    -max 2.0 \
    -min 0.3 \
    -clock sys_clk \
    [get_ports data_in]
set_output_delay -max 1.0 -min 0.2 -clock sys_clk [all_outputs]
