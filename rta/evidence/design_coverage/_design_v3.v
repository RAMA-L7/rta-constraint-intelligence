// Shared generated-clock design for DC08 — primary clk + divide-by-2 divider.
module top (
    input clk,
    input rst_n,
    input [7:0] data_in,
    output [7:0] data_out,
    output clk_div2_out
);
    wire clk_div2;
    wire [7:0] w;
    div2 u_div ( .clk_in(clk), .clk_out(clk_div2) );
    flop u1 ( .clk(clk_div2), .d(data_in), .q(w) );
    reg_out u2 ( .d(w), .q(data_out) );
    assign clk_div2_out = clk_div2;
endmodule

module div2 ( input clk_in, output clk_out );
    reg q;
    always @(posedge clk_in) q = ~q;
    assign clk_out = q;
endmodule

module flop ( input clk, input [7:0] d, output [7:0] q );
    reg [7:0] r;
    always @(posedge clk) r <= d;
    assign q = r;
endmodule

module reg_out ( input [7:0] d, output [7:0] q );
    reg [7:0] r;
    always @(*) r = d;
    assign q = r;
endmodule
