# RD02 — Multi-clock SoC block: CPU, IO, memory, UART, SD interfaces.
# 5 primary clocks with explicit async clock groups.
set sdc_version 2.1
set_units -time ns -capacitance pF -resistance kohm -voltage V \
          -current mA

create_clock -name clk_cpu -period 2.0 -waveform {0 1.0} [get_ports clk_cpu]
create_clock -name clk_io  -period 10.0 -waveform {0 5.0} [get_ports clk_io]
create_clock -name clk_mem -period 3.3 -waveform {0 1.65} [get_ports clk_mem]
create_clock -name clk_uart -period 16.67 -waveform {0 8.33} [get_ports clk_uart]
create_clock -name clk_sd  -period 6.25 -waveform {0 3.125} [get_ports clk_sd]

# Clock uncertainty per domain
set_clock_uncertainty -setup 0.05 -hold 0.03 [get_clocks clk_cpu]
set_clock_uncertainty -setup 0.20 -hold 0.10 [get_clocks clk_io]
set_clock_uncertainty -setup 0.08 -hold 0.04 [get_clocks clk_mem]
set_clock_uncertainty -setup 0.30 -hold 0.15 [get_clocks clk_uart]
set_clock_uncertainty -setup 0.10 -hold 0.05 [get_clocks clk_sd]

# CDC: cpu/mem/sd synchronous-ish; io and uart asynchronous to everything.
set_clock_groups -asynchronous \
    -group [get_clocks {clk_cpu clk_mem clk_sd}] \
    -group [get_clocks clk_io] \
    -group [get_clocks clk_uart]

# I/O interfaces
set_input_delay -max 0.6 -min 0.1 -clock clk_cpu \
    [get_ports {core_data_in* core_ctl_in*}]
set_output_delay -max 0.5 -min 0.1 -clock clk_cpu \
    [get_ports {core_data_out* core_ack*}]
set_input_delay -max 1.2 -min 0.3 -clock clk_io [get_ports {pio_in*}]
set_output_delay -max 1.0 -min 0.25 -clock clk_io [get_ports {pio_out*}]
set_input_delay -max 1.0 -min 0.2 -clock clk_mem [get_ports {mem_addr* mem_wrdata*}]
set_output_delay -max 1.1 -min 0.2 -clock clk_mem [get_ports {mem_rddata*}]
set_input_delay -max 2.0 -min 0.4 -clock clk_uart [get_ports uart_rx]
set_output_delay -max 2.0 -min 0.4 -clock clk_uart [get_ports uart_tx]
set_input_delay -max 1.5 -min 0.3 -clock clk_sd [get_ports {sd_cmd_in sd_dat_in*}]
set_output_delay -max 1.4 -min 0.3 -clock clk_sd [get_ports {sd_cmd_out sd_dat_out*}]

# Drive/load
set_driving_cell -lib_cell INV_X1 -clock clk_cpu [all_inputs]
set_load 0.5 [all_outputs]

# Exceptions
set_false_path -from [get_clocks clk_uart] -to [get_clocks clk_cpu]
set_multicycle_path -setup 2 -hold 1 -from [get_ports mem_addr*] -to [all_registers]

set_operating_conditions TT0P80V25C
