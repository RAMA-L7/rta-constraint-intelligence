# HR11 — an unsupported Tcl construct (foreach) among otherwise valid
# constraints → analysis trust: REVIEW_REQUIRED. The foreach is NOT executed;
# the validator must not claim full analysis. Not BLOCKED (no definite error).
set sdc_version 2.2
create_clock -name clk_core -period 10.0 [get_ports clk_core]
set_input_delay -max 2.0 -min 0.5 -clock clk_core [get_ports din]
set_output_delay -max 3.0 -min 1.0 -clock clk_core [get_ports dout]
foreach port {din_a din_b} {
    set_input_delay -max 1.0 -clock clk_core [get_ports $port]
}
