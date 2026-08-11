// NA02 — design with NO 'clk' port. The SDC's create_clock [get_ports clk]
// references a port that does not exist in this netlist → SDC-055.
// Expected design objects: ports = {sysclk, data_in, data_out} only.
module top (
    input sysclk,
    input [7:0] data_in,
    output [7:0] data_out
);
    wire [7:0] dbus;
    flop u1 ( .clk(sysclk), .d(data_in), .q(dbus) );
    flop u2 ( .clk(sysclk), .d(dbus), .q(data_out) );
endmodule

module flop ( input clk, input [7:0] d, output [7:0] q );
    reg [7:0] r;
    always @(posedge clk) r <= d;
    assign q = r;
endmodule
