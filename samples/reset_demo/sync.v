// F2 demo — reset synchronizer sync-stage shape: rst_n also feeds a flop's
// data pin (u_sync/d = rst_n). Pair with top.sdc to see SDC-153.
module top (
    input clk,
    input rst_n,
    input [7:0] din,
    output [7:0] dout
);
    flop u_sync ( .clk(clk), .rst(rst_n), .d(rst_n), .q(dout) );
    flop u_reg1 ( .clk(clk), .rst(rst_n), .d(dout), .q() );
endmodule
module flop ( input clk, input rst, input [7:0] d, output [7:0] q );
    reg [7:0] r;
    always @(posedge clk or negedge rst) if (!rst) r <= 8'h0; else r <= d;
    assign q = r;
endmodule
