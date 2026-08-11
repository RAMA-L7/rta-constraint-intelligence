# Golden: backslash-newline joins lines into ONE logical command (Tcl rule 9).
create_clock \
    -name sys_clk \
    -period 10.0 \
    [get_ports clk]
set_input_delay -max 1.0 -min 0.2 -clock sys_clk [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock sys_clk [all_outputs]
