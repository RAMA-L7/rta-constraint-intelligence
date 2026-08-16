// Engineer Test Kit - realistic block: DMA engine with AHB slave + UART-ish
// serial stream, two primary clocks plus a /2 generated clock.
// Design : dma_engine_top (AHB slave + DMA core, two-clock block)
// Clocks : clk_ahb (primary, 10ns), clk_periph (primary, 8ns),
//          clk_div2 (generated, /2 from u_div2/out on clk_ahb)
// Reset  : rst_n async reset, fans out to every flop
// DFT    : scan_en, test_mode (functional mode via set_case_analysis)
//
// The SDC in this set (dma_engine.sdc) intentionally carries realistic
// constraint-quality issues; the netlist resolves every object reference so
// SDC-055..059 (object resolution) and SDC-064..066 (design-aware coverage)
// can actually prove or disprove the SDC's claims.
module dma_engine_top (
    input         clk_ahb,
    input         clk_periph,
    input         rst_n,
    input  [11:0] ahb_addr,
    input  [31:0] ahb_wdata,
    output [31:0] ahb_rdata,
    input         ahb_write,
    input         ahb_sel,
    input         dma_req,
    output        dma_ack,
    input  [7:0]  stream_in,
    output [7:0]  stream_out,
    output        irq,
    input         scan_en,
    input         test_mode
);
    wire clk_div2;

    // /2 divider on the AHB clock - master point of the generated clock.
    // The SDC must reference u_div2/out (SDC-003 tests this relationship).
    dma_div2 u_div2 (
        .clk     (clk_ahb),
        .rst_n   (rst_n),
        .scan_en (scan_en),
        .out     (clk_div2)
    );

    dma_core u_core (
        .clk_ahb    (clk_ahb),
        .clk_div2   (clk_div2),
        .clk_periph (clk_periph),
        .rst_n      (rst_n),
        .addr       (ahb_addr),
        .wdata      (ahb_wdata),
        .rdata      (ahb_rdata),
        .write      (ahb_write),
        .sel        (ahb_sel),
        .dma_req    (dma_req),
        .dma_ack    (dma_ack),
        .stream_in  (stream_in),
        .stream_out (stream_out),
        .irq        (irq),
        .scan_en    (scan_en),
        .test_mode  (test_mode)
    );
endmodule

// /2 divider cell - generated-clock source pin u_div2/out.
module dma_div2 (
    input  clk,
    input  rst_n,
    input  scan_en,
    output out
);
    reg [1:0] div_reg;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)      div_reg <= 2'b00;
        else if (scan_en) div_reg <= div_reg;
        else             div_reg <= div_reg + 2'b01;
    end
    assign out = div_reg[1];
endmodule

// DMA core - AHB slave register file on clk_ahb, stream engine on the
// divided clock, plus a small clk_periph domain (the async CDC path the
// SDC must either group or exception).
module dma_core (
    input         clk_ahb,
    input         clk_div2,
    input         clk_periph,
    input         rst_n,
    input  [11:0] addr,
    input  [31:0] wdata,
    output [31:0] rdata,
    input         write,
    input         sel,
    input         dma_req,
    output        dma_ack,
    input  [7:0]  stream_in,
    output [7:0]  stream_out,
    output        irq,
    input         scan_en,
    input         test_mode
);
    // AHB-visible register file (clk_ahb domain)
    reg  [31:0] ctrl_reg;
    reg  [31:0] status_reg;
    always @(posedge clk_ahb or negedge rst_n) begin
        if (!rst_n) begin
            ctrl_reg   <= 32'h0;
            status_reg <= 32'h0;
        end else if (sel && write) begin
            if (addr[3:2] == 2'b00) ctrl_reg <= wdata;
            else                    status_reg <= wdata;
        end
    end
    assign rdata = (sel && !write) ? ctrl_reg : 32'h0;

    // Stream engine on the divided clock
    reg  [7:0]  stream_reg;
    reg         busy;
    always @(posedge clk_div2 or negedge rst_n) begin
        if (!rst_n) begin
            stream_reg <= 8'h0;
            busy       <= 1'b0;
        end else if (ctrl_reg[0] && !busy) begin
            stream_reg <= stream_in;
            busy       <= 1'b1;
        end else if (busy) begin
            stream_reg <= {stream_reg[6:0], stream_reg[7]};
            if (stream_reg == 8'hFF) busy <= 1'b0;
        end
    end
    assign stream_out = busy ? stream_reg : 8'h00;

    // Peripheral-domain handshake + IRQ (async CDC into clk_ahb)
    reg  periph_ack;
    always @(posedge clk_periph or negedge rst_n) begin
        if (!rst_n) periph_ack <= 1'b0;
        else        periph_ack <= dma_req;
    end
    assign dma_ack = periph_ack;
    assign irq     = periph_ack;
endmodule
