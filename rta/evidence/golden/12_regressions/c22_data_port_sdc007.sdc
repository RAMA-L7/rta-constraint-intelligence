# Golden regression target (currently FAILS): 'data_in' is a data port —
# create_clock on it must produce SDC-007.
create_clock -name c -period 5.0 [get_ports data_in]
set_input_delay -max 1.0 -min 0.2 -clock c [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock c [all_outputs]
