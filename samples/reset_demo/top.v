// F2 demo — reset tree: rst_n drives 2 flip-flop reset pins (RESET-class).
// Pair with top.sdc (no timing exception on rst_n) to see SDC-151.
module top (
    input clk,
    input rst_n,
    input [7:0] din,
    output [7:0] dout
);
    flop u_reg0 ( .clk(clk), .rst(rst_n), .d(din), .q(dout) );
    flop u_reg1 ( .clk(clk), .rst(rst_n), .d(dout), .q() );
endmodule
module flop ( input clk, input rst, input [7:0] d, output [7:0] q );
    reg [7:0] r;
    always @(posedge clk or negedge rst) if (!rst) r <= 8'h0; else r <= d;
    assign q = r;
endmodule
