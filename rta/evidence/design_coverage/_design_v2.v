// Shared multi-clock design for DC11 — two clock domains.
module top (
    input clk_a,
    input clk_b,
    input rst_n,
    input [7:0] data_in,
    output [7:0] data_out_a,
    output [7:0] data_out_b
);
    wire [7:0] wa;
    wire [7:0] wb;
    flop ua ( .clk(clk_a), .d(data_in), .q(wa) );
    flop ub ( .clk(clk_b), .d(wa), .q(wb) );
    reg_out u2a ( .d(wa), .q(data_out_a) );
    reg_out u2b ( .d(wb), .q(data_out_b) );
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
