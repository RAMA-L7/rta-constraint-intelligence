// RDIF17 current — top module is "top_b" (renamed design).
module top_b ( input clk, input din_a, output dout_a );
  reg r;
  always @(posedge clk) begin
    r <= din_a;
  end
  assign dout_a = r;
endmodule
