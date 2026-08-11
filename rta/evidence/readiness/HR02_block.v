// HR02 — clean single-clock block netlist (design-aware readiness case)
module block (
    input        clk_core,
    input        scan_en,
    input  [1:0] din_a,        // data input (bus, both bits covered by set_input_delay)
    input        din_b,
    output       dout_a,
    output       dout_b
);
    wire n1, n2;

    flop u_reg_a (.clk(clk_core), .d(din_a[0]), .q(dout_a));
    flop u_reg_b (.clk(clk_core), .d(din_b),   .q(dout_b));

    buf u_buf1 (.a(din_a[1]), .y(n1));
    buf u_buf2 (.a(n1),       .y(n2));
endmodule

module flop (input clk, input d, output reg q);
    always @(posedge clk) q <= d;
endmodule

module buf (input a, output y);
    assign y = a;
endmodule
