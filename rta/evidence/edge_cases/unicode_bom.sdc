# SDC with UTF-8 BOM + unicode comment.
set sdc_version 2.2
set_units -time ns -capacitance pF
create_clock -name clk_core -period 5.0 [get_ports clk]
set_input_delay -max 1.0 -min 0.2 -clock clk_core [all_inputs]
set_output_delay -max 1.0 -min 0.2 -clock clk_core [all_outputs]
# émoji test 🧪 单位测试
