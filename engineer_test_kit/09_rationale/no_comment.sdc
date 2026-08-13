# Undocumented timing exception: this false path has no explanatory
# comment, so a later engineer cannot tell whether it is genuinely false
# or was silently exempted (SDC-150). SDC-020 also fires.
set sdc_version 2.2
set_units -time ns -capacitance pF

create_clock -name clk -period 10.0 [get_ports clk]

set_false_path -from [get_ports rxd] -to [get_ports txd]
