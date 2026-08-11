# HR04 — one data input left unconstrained (design-aware)
# din_b has structural data evidence but no set_input_delay → SDC-064 warning
# → REVIEW_REQUIRED (likely handoff issue: external timing at that boundary
# is unconstrained). data_in[7:0] and data_out[7:0] are fully covered.
set sdc_version 2.2
create_clock -name clk_core -period 10.0 [get_ports clk_core]
set_input_delay -max 2.0 -min 0.5 -clock clk_core [get_ports {data_in}]
set_output_delay -max 3.0 -min 1.0 -clock clk_core [get_ports {data_out}]
