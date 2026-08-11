// NA06 — generated clock. SDC: create_generated_clock -source [get_ports clk]
// (valid port) and -source [get_ports pll_out] (missing port → SDC-055).
module top (
    input clk,
    output clk_div2
);
    div2 u_div ( .clk(clk), .out(clk_div2) );
endmodule

module div2 ( input clk, output out );
    reg q;
    always @(posedge clk) q <= ~q;
    assign out = q;
endmodule
