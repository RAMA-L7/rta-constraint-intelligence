// NA04 — bus handling. SDC references data_in[3] (valid), data_in[9]
// (out of range → SDC-055), and data_in[*] (valid wildcard bit).
module top (
    input clk,
    input [7:0] data_in,
    input [15:0] addr_in,
    output [7:0] data_out,
    output [15:0] addr_out
);
    wire [7:0] d;
    wire [15:0] a;
    mem u_mem ( .clk(clk), .din(data_in), .dout(d), .ain(addr_in), .aout(a) );
    buf u_buf ( .d(d), .q(data_out), .a(a), .aq(addr_out) );
endmodule

module mem (
    input clk,
    input [7:0] din,
    output [7:0] dout,
    input [15:0] ain,
    output [15:0] aout
);
    reg [7:0] m [0:255];
    always @(posedge clk) begin
        m[ain] <= din;
        dout <= m[ain];
        aout <= ain;
    end
endmodule

module buf ( input [7:0] d, output [7:0] q, input [15:0] a, output [15:0] aq );
    assign q = d;
    assign aq = a;
endmodule
