// RDIF17 baseline — top module is "top_a".
module top_a ( input clk, input din_a, output dout_a );
  reg r;
  always @(posedge clk) begin
    r <= din_a;
  end
  assign dout_a = r;
endmodule
