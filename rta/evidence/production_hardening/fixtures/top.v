// Phase 13 PH13 fixture: structural netlist for design-aware cases
module dff (input c, input d, output q);
endmodule

module top (
    input clk,
    input [3:0] din,
    output [1:0] dout
);
    wire [3:0] din_q;
    dff u0 (.c(clk), .d(din[0]), .q(din_q[0]));
    dff u1 (.c(clk), .d(din[1]), .q(din_q[1]));
    assign dout[0] = din_q[0];
    assign dout[1] = din_q[1];
endmodule
