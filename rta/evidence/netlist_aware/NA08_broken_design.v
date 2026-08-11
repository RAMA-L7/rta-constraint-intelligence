// NA08 — INTENTIONALLY BROKEN design.
// Injected defects (see manifest):
//   D1: SDC references get_ports nonexistent_clk (port not in netlist)      → SDC-055
//   D2: SDC get_pins u_core/u_bad_reg/D — invalid hierarchy path             → SDC-055/057
//   D3: SDC get_ports stray_* wildcard matches nothing                       → SDC-056
//   D4: input port data_in never constrained by set_input_delay              → SDC-059
// Valid: clk port + data_out constrained.
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
