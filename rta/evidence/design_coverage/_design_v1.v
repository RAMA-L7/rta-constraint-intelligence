// Shared design for design-coverage cases DC01-DC10/DC12.
// Ports: clk (CLOCK), rst_n (RESET), scan_en (SCAN), data_in[7:0] (DATA in),
//        data_out[7:0] (DATA out), status[3:0] (DATA out).
module top (
    input clk,
    input rst_n,
    input scan_en,
    input [7:0] data_in,
    output [7:0] data_out,
    output [3:0] status
);
    wire [7:0] w;
    flop u1 ( .clk(clk), .d(data_in), .q(w), .rstn(rst_n), .se(scan_en) );
    reg_out u2 ( .d(w), .q(data_out) );
    reg_out u3 ( .d(w[3:0]), .q(status) );
endmodule

module flop ( input clk, input [7:0] d, output [7:0] q, input rstn, input se );
    reg [7:0] r;
    always @(posedge clk) r <= d;
    assign q = r;
endmodule

module reg_out ( input [7:0] d, output [7:0] q );
    reg [7:0] r;
    always @(*) r = d;
    assign q = r;
endmodule
