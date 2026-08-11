# Multi-line SDC where the -min/-clock flags live on CONTINUATION lines.
# The checker's grab regexes stop at the newline, so continuation content
# may be silently dropped → wrong counts / false warnings.
set sdc_version 2.2

create_clock -name clk_core \
    -period 5.0 \
    [get_ports clk]

set_input_delay \
    -max 1.0 \
    -min 0.2 \
    -clock clk_core \
    [all_inputs]

set_output_delay \
    -max 1.0 \
    -min 0.2 \
    -clock clk_core \
    [all_outputs]
