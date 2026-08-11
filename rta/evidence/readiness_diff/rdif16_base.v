// RDIF16 baseline — din_c does NOT exist yet.
module rdif16 ( input clk, input din_a, input din_b, input din_c,
                output dout_a );
  reg r;
  always @(posedge clk) begin
    r <= din_a & din_b & din_c;
  end
  assign dout_a = r;
endmodule
