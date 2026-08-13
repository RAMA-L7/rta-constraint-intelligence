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
// Engineer Test Kit - canonical block: /2 divider cell
// Master point of the generated clock clk_div2 (SDC references the
// instance output pin u_div2/out).
module apb_div2 (
    input  clk,
    input  rst_n,
    input  scan_en,
    output out
);
    reg [1:0] div_reg;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) div_reg <= 2'b00;
        else if (scan_en) div_reg <= div_reg;
        else div_reg <= div_reg + 2'b01;
    end
    assign out = div_reg[1];
endmodule
// Engineer Test Kit - canonical block: APB slave + UART core (submodule)
// Two-clock block: primary clock clk (port) plus generated clock clk_div2
// (divider output net fanned in from the top). Async reset rst_n fans out
// to every flop, which is what the reset-tree rules (SDC-151..153) key on.
module apb_uart_core (
    input         clk,
    input         clk_div2,
    input         rst_n,
    input         psel,
    input         penable,
    input         pwrite,
    input  [11:0] paddr,
    input  [31:0] pwdata,
    output [31:0] prdata,
    output        pready,
    input         rxd,
    output        txd,
    input         scan_en,
    input         test_mode
);
    // APB register file - writes captured on the primary clock
    reg  [31:0] ctrl_reg;
    reg  [31:0] status_reg;
    reg  [31:0] baud_reg;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ctrl_reg   <= 32'h0;
            status_reg <= 32'h0;
            baud_reg   <= 32'h0;
        end else if (psel && penable && pwrite) begin
            if (paddr[3:2] == 2'b00) ctrl_reg <= pwdata;
            else if (paddr[3:2] == 2'b01) baud_reg <= pwdata;
            else status_reg <= pwdata;
        end
    end

    // UART transmitter - clocked by the divided clock
    reg  [7:0] tx_shift;
    reg  [3:0] tx_count;
    reg        tx_busy;
    always @(posedge clk_div2 or negedge rst_n) begin
        if (!rst_n) begin
            tx_shift <= 8'hFF;
            tx_count <= 4'h0;
            tx_busy  <= 1'b0;
        end else if (ctrl_reg[0] && !tx_busy) begin
            tx_shift <= ctrl_reg[15:8];
            tx_count <= 4'h8;
            tx_busy  <= 1'b1;
        end else if (tx_busy) begin
            tx_shift <= {1'b1, tx_shift[7:1]};
            tx_count <= tx_count - 4'h1;
            if (tx_count == 4'h1) tx_busy <= 1'b0;
        end
    end
    assign txd = tx_busy ? tx_shift[0] : 1'b1;

    // UART receiver - clocked by the divided clock
    reg  [7:0] rx_shift;
    reg  [3:0] rx_count;
    reg        rx_busy;
    always @(posedge clk_div2 or negedge rst_n) begin
        if (!rst_n) begin
            rx_shift <= 8'h0;
            rx_count <= 4'h0;
            rx_busy  <= 1'b0;
        end else if (!rxd && !rx_busy) begin
            rx_busy  <= 1'b1;
            rx_count <= 4'h8;
        end else if (rx_busy) begin
            rx_shift <= {rx_shift[6:0], rxd};
            rx_count <= rx_count - 4'h1;
        end
    end

    assign prdata = (psel && !pwrite) ? ctrl_reg : 32'h0;
    assign pready = 1'b1;
endmodule
