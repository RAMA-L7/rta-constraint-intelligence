// NA07 — timing exceptions. Valid pin refs u_core/u_reg0/D and one invalid
// pin path u_core/u_nope/Q → SDC-055 + SDC-057.
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
    wire [7:0] x;
    flop u_reg0 ( .CLK(clk), .D(din), .Q(x) );
    assign dout = x;
endmodule

module flop ( input CLK, input [7:0] D, output [7:0] Q );
    reg [7:0] r;
    always @(posedge CLK) r <= D;
    assign Q = r;
endmodule

module io ( input [7:0] d, output [7:0] q );
    assign q = d;
endmodule
