// Engineer Test Kit - high-coverage fixture netlist
// Design : ahb_spi_ctrl_top (AHB-slave SPI master controller)
// Clocks : clk_ahb (primary, 10ns), clk_spi (primary, 40ns),
//          clk_ahb_div2 (generated, /2 from u_div2/out on clk_ahb)
// Reset  : rst_n async reset, fans out to every flop
// DFT    : scan_en, test_mode (functional mode via set_case_analysis)
//
// Every object referenced by ahb_spi_ctrl.sdc exists here so SDC-055..059
// (object resolution) and SDC-064..066 (design-aware coverage) can actually
// prove or disprove the SDC's claims.
module ahb_spi_ctrl_top (
    input         clk_ahb,
    input         clk_spi,
    input         rst_n,
    input  [11:0] haddr,
    input  [31:0] hwdata,
    output [31:0] hrdata,
    input         hwrite,
    input         hsel,
    input         hready,
    output        hready_out,
    input         spi_miso,
    output        spi_sclk,
    output        spi_mosi,
    output        spi_cs_n,
    output        irq,
    input         scan_en,
    input         test_mode
);
    wire clk_div2;

    // /2 divider on the AHB clock - generated-clock source pin u_div2/out
    ahb_spi_div2 u_div2 (
        .clk     (clk_ahb),
        .rst_n   (rst_n),
        .scan_en (scan_en),
        .out     (clk_div2)
    );

    // AHB slave register file + SPI master engine
    ahb_spi_core u_core (
        .clk_ahb    (clk_ahb),
        .clk_div2   (clk_div2),
        .clk_spi    (clk_spi),
        .rst_n      (rst_n),
        .haddr      (haddr),
        .hwdata     (hwdata),
        .hrdata     (hrdata),
        .hwrite     (hwrite),
        .hsel       (hsel),
        .hready     (hready),
        .hready_out (hready_out),
        .miso       (spi_miso),
        .sclk       (spi_sclk),
        .mosi       (spi_mosi),
        .cs_n       (spi_cs_n),
        .irq        (irq),
        .scan_en    (scan_en),
        .test_mode  (test_mode)
    );

    // Two-flop CDC synchronizer for spi_miso -> AHB domain (async false path)
    ahb_spi_sync u_async (
        .clk   (clk_ahb),
        .rst_n (rst_n),
        .din   (spi_miso),
        .dout  (miso_sync)
    );

    // Multicycle-path endpoints: multiply -> accumulate on the divided clock
    ahb_spi_mul u_mul (
        .clk   (clk_div2),
        .rst_n (rst_n),
        .a     (hwdata[7:0]),
        .p     (mul_out)
    );
    ahb_spi_acc u_acc (
        .clk   (clk_div2),
        .rst_n (rst_n),
        .d     (mul_out),
        .q     (acc_out)
    );

    // Hold-fix buffer - timing arc disabled in the SDC
    ahb_spi_hold_buf u_hold_buf (
        .a (acc_out),
        .z (hold_out)
    );
endmodule


// /2 divider cell - generated-clock source pin u_div2/out.
module ahb_spi_div2 (
    input  clk,
    input  rst_n,
    input  scan_en,
    output out
);
    reg [1:0] div_reg;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)       div_reg <= 2'b00;
        else if (scan_en) div_reg <= div_reg;
        else              div_reg <= div_reg + 2'b01;
    end
    assign out = div_reg[1];
endmodule

// Core - AHB slave register file on clk_ahb, SPI master engine on clk_div2,
// SPI bit clock from clk_spi, plus the async MISO synchronizer input.
module ahb_spi_core (
    input         clk_ahb,
    input         clk_div2,
    input         clk_spi,
    input         rst_n,
    input  [11:0] haddr,
    input  [31:0] hwdata,
    output [31:0] hrdata,
    input         hwrite,
    input         hsel,
    input         hready,
    output        hready_out,
    input         miso,
    output        sclk,
    output        mosi,
    output        cs_n,
    output        irq,
    input         scan_en,
    input         test_mode
);
    reg  [31:0] ctrl_reg;
    reg  [31:0] status_reg;
    always @(posedge clk_ahb or negedge rst_n) begin
        if (!rst_n) begin
            ctrl_reg   <= 32'h0;
            status_reg <= 32'h0;
        end else if (hsel && hwrite && hready) begin
            if (haddr[3:2] == 2'b00) ctrl_reg   <= hwdata;
            else                     status_reg <= hwdata;
        end
    end
    assign hrdata    = (hsel && !hwrite) ? ctrl_reg : 32'h0;
    assign hready_out = hready;

    // SPI master engine on the divided clock
    reg  [7:0]  tx_reg;
    reg  [2:0]  bit_cnt;
    reg         busy;
    always @(posedge clk_div2 or negedge rst_n) begin
        if (!rst_n) begin
            tx_reg  <= 8'h0;
            bit_cnt <= 3'b000;
            busy    <= 1'b0;
        end else if (ctrl_reg[0] && !busy) begin
            tx_reg  <= hwdata[7:0];
            bit_cnt <= 3'b000;
            busy    <= 1'b1;
        end else if (busy) begin
            if (bit_cnt == 3'b111) busy <= 1'b0;
            else bit_cnt <= bit_cnt + 3'b001;
        end
    end
    assign sclk = clk_spi;
    assign mosi = tx_reg[7];
    assign cs_n = ~busy;
    assign irq  = busy;
endmodule

// Two-flop CDC synchronizer.
module ahb_spi_sync (
    input  clk,
    input  rst_n,
    input  din,
    output dout
);
    reg sync_ff1;
    reg sync_ff2;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sync_ff1 <= 1'b0;
            sync_ff2 <= 1'b0;
        end else begin
            sync_ff1 <= din;
            sync_ff2 <= sync_ff1;
        end
    end
    assign dout = sync_ff2;
endmodule

// Multiply stage (multicycle -setup 2 from u_mul).
module ahb_spi_mul (
    input  clk,
    input  rst_n,
    input  [7:0] a,
    output [15:0] p
);
    reg [15:0] mul_reg;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) mul_reg <= 16'h0;
        else        mul_reg <= {8'h0, a} * 16'h0002;
    end
    assign p = mul_reg;
endmodule

// Accumulate stage (multicycle -hold 1 to u_acc).
module ahb_spi_acc (
    input        clk,
    input        rst_n,
    input  [15:0] d,
    output [15:0] q
);
    reg [15:0] acc_reg;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) acc_reg <= 16'h0;
        else        acc_reg <= acc_reg + d;
    end
    assign q = acc_reg;
endmodule

// Hold-fix buffer - disable-timing target.
module ahb_spi_hold_buf (
    input  a,
    output z
);
    assign z = a;
endmodule
