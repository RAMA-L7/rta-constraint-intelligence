// NA03 — hierarchical design. SDC uses get_pins u_core/u_reg0/D and
// get_cells u_core/u_reg1. Both must resolve.
module top (
    input clk,
    input [7:0] data_in,
    output [7:0] data_out
);
    wire [7:0] t;
    core u_core ( .clk(clk), .din(data_in), .dout(t) );
    io u_io ( .d(t), .q(data_out) );
endmodule

module core ( input clk, input [7:0] din, output [7:0] dout );
    wire [7:0] x, y;
    flop u_reg0 ( .CLK(clk), .D(din), .Q(x) );
    flop u_reg1 ( .CLK(clk), .D(x), .Q(y) );
    assign dout = y;
endmodule

module flop ( input CLK, input [7:0] D, output [7:0] Q );
    reg [7:0] r;
    always @(posedge CLK) r <= D;
    assign Q = r;
endmodule

module io ( input [7:0] d, output [7:0] q );
    assign q = d;
endmodule
