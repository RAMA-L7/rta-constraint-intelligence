# RD04 — DDR / source-synchronous style interface (simplified)
# Virtual clocks model the off-chip read/write capture; real PLL clock feeds
# the controller. dqs/dq buses use -max/-min and -rise/-fall delays.
set sdc_version 2.1
set_units -time ns -capacitance pF -resistance kohm -voltage V \
          -current mA

# On-chip controller clock (PLL-derived real clock)
create_clock -name ck_pll -period 1.875 -waveform {0 0.9375} [get_ports ck_pll]

# Virtual clocks for the DDR interface (no physical source)
create_clock -name vclk_ddr_read -period 3.75 -waveform {0 1.875}
create_clock -name vclk_ddr_write -period 3.75 -waveform {0 1.875}

set_clock_uncertainty -setup 0.09 -hold 0.06 [get_clocks ck_pll]
set_clock_uncertainty -setup 0.12 -hold 0.08 [get_clocks {vclk_ddr_read vclk_ddr_write}]

# Output delays (write path) — DQS/DQ to the DRAM, capture by virtual write clock
set_output_delay -max 0.6 -min 0.2 -rise -clock vclk_ddr_write \
    [get_ports {dqs[*]}]
set_output_delay -max 0.6 -min 0.2 -fall -clock vclk_ddr_write \
    [get_ports {dqs[*]}]
set_output_delay -max 0.55 -min 0.18 -clock vclk_ddr_write \
    [get_ports {dq[*]}]

# Input delays (read path) — data from DRAM captured by virtual read clock
set_input_delay -max 0.5 -min 0.15 -clock vclk_ddr_read \
    [get_ports {dq[*]}]
set_input_delay -max 0.5 -min 0.15 -clock vclk_ddr_read \
    [get_ports {dm[*]}]

# Address/command bus to the DRAM, clocked by the real PLL output
set_output_delay -max 1.0 -min 0.3 -clock ck_pll \
    [get_ports {addr[*] bank[*] cmd_* cs_n ras_n cas_n we_n}]

set_load 0.05 [get_ports {dq[*] dqs[*] dm[*]}]

# Clock groups: virtual read/write clocks are synchronous with each other;
# keep them separate from nothing else (only interface clocks here).
set_false_path -from [get_clocks vclk_ddr_read] -to [get_clocks vclk_ddr_write]
set_operating_conditions TT
