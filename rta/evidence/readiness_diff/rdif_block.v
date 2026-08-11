// RDIF08/RDIF09 — same netlist for both revisions (input-coverage delta only).
module rdif_block ( input clk, input din_a, input din_b, output dout_a );
  reg r;
  always @(posedge clk) begin
    r <= din_a & din_b;
  end
  assign dout_a = r;
endmodule
