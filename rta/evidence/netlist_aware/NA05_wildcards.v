// NA05 — wildcards. debug_* ports DO exist; bogus_* do NOT.
module top (
    input clk,
    input debug_sel,
    input [7:0] debug_bus,
    input [7:0] data_in,
    output [7:0] data_out
);
    wire [7:0] d;
    flop u1 ( .clk(clk), .d(data_in), .q(d) );
    flop u2 ( .clk(clk), .d(d), .q(data_out) );
endmodule

module flop ( input clk, input [7:0] d, output [7:0] q );
    reg [7:0] r;
    always @(posedge clk) r <= d;
    assign q = r;
endmodule
