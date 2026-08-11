// HR04/HR05 — netlist with a data input missing its delay, plus a bus
module busblock (
    input        clk_core,
    input  [7:0] data_in,      // bus — HR05 constrains only data[3:0]
    input        din_b,        // HR04 leaves this one unconstrained
    output [7:0] data_out
);
    reg [7:0] r_out;
    always @(posedge clk_core) r_out <= data_in;
    assign data_out = r_out;
endmodule
