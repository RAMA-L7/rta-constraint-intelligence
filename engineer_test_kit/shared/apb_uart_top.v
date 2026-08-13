// Engineer Test Kit - canonical block top: APB slave + UART core
// Two-level hierarchy: apb_uart_top instantiates a /2 divider (u_div2)
// and the APB+UART core (u_core). The generated clock clk_div2 is the
// divider output net, fanned out to the core's serial logic.
module apb_uart_top (
    input         clk,
    input         rst_n,
    input         apb_psel,
    input         apb_penable,
    input         apb_pwrite,
    input  [11:0] apb_paddr,
    input  [31:0] apb_pwdata,
    output [31:0] apb_prdata,
    output        apb_pready,
    input         rxd,
    output        txd,
    input         scan_en,
    input         test_mode
);
    wire clk_div2;

    apb_div2 u_div2 (
        .clk     (clk),
        .rst_n   (rst_n),
        .scan_en (scan_en),
        .out     (clk_div2)
    );

    apb_uart_core u_core (
        .clk       (clk),
        .clk_div2  (clk_div2),
        .rst_n     (rst_n),
        .psel      (apb_psel),
        .penable   (apb_penable),
        .pwrite    (apb_pwrite),
        .paddr     (apb_paddr),
        .pwdata    (apb_pwdata),
        .prdata    (apb_prdata),
        .pready    (apb_pready),
        .rxd       (rxd),
        .txd       (txd),
        .scan_en   (scan_en),
        .test_mode (test_mode)
    );
endmodule
