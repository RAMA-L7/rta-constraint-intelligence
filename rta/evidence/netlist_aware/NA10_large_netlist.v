// NA10 — larger structural netlist (60 instances, 3-level hierarchy).
// Deterministic facts (see manifest):
//   top ports:  clk, rst_n, data_in[7:0], data_out[7:0]          = 4 ports
//   top instances:  u_core, u_io, u_pll                         = 3 direct
//   u_core children:  u_reg0..u_reg9 (10 flops)                  = 10
//   u_core/u_reg*/ children: none (leaf flops)
//   u_io children:  u_out0..u_out3 (4 buffers)                  = 4
//   total instances: 3 + 10 + 4 = 17
//   pins:  flop CLK/D/Q per child + io DIN/DOUT per child
// SDC references resolvable: u_core/u_reg0/D, u_io/u_out0/DOUT, u_core/*
module top (
    input clk,
    input rst_n,
    input [7:0] data_in,
    output [7:0] data_out
);
    wire [7:0] core_out;
    wire clk_pll;

    pll u_pll ( .clk_in(clk), .clk_out(clk_pll) );
    core u_core ( .clk(clk_pll), .rst(rst_n), .din(data_in), .dout(core_out) );
    io u_io ( .din(core_out), .dout(data_out) );
endmodule

module pll ( input clk_in, output clk_out );
    assign clk_out = clk_in;
endmodule

module core ( input clk, input rst, input [7:0] din, output [7:0] dout );
    wire [7:0] t0, t1, t2, t3, t4, t5, t6, t7, t8, t9;
    flop u_reg0  ( .CLK(clk), .D(din), .Q(t0) );
    flop u_reg1  ( .CLK(clk), .D(t0),  .Q(t1) );
    flop u_reg2  ( .CLK(clk), .D(t1),  .Q(t2) );
    flop u_reg3  ( .CLK(clk), .D(t2),  .Q(t3) );
    flop u_reg4  ( .CLK(clk), .D(t3),  .Q(t4) );
    flop u_reg5  ( .CLK(clk), .D(t4),  .Q(t5) );
    flop u_reg6  ( .CLK(clk), .D(t5),  .Q(t6) );
    flop u_reg7  ( .CLK(clk), .D(t6),  .Q(t7) );
    flop u_reg8  ( .CLK(clk), .D(t7),  .Q(t8) );
    flop u_reg9  ( .CLK(clk), .D(t8),  .Q(t9) );
    assign dout = t9;
endmodule

module flop ( input CLK, input [7:0] D, output [7:0] Q );
    reg [7:0] r;
    always @(posedge CLK) r <= D;
    assign Q = r;
endmodule

module io ( input [7:0] din, output [7:0] dout );
    wire [7:0] o0, o1, o2, o3;
    buf u_out0 ( .DIN(din), .DOUT(o0) );
    buf u_out1 ( .DIN(o0),  .DOUT(o1) );
    buf u_out2 ( .DIN(o1),  .DOUT(o2) );
    buf u_out3 ( .DIN(o2),  .DOUT(o3) );
    assign dout = o3;
endmodule

module buf ( input [7:0] DIN, output [7:0] DOUT );
    assign DOUT = DIN;
endmodule
