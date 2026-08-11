// NA01 — valid single-module design (no defects)
// Expectation: parse OK, top=top, all SDC references resolve, no SDC-055..059.
module top (
    input clk,
    input rst_n,
    input [7:0] data_in,
    output [7:0] data_out,
    output [3:0] status
);
    wire [7:0] dbus;
    wire clk_div;

    div2 u_div (
        .clk(clk),
        .out(clk_div)
    );
    core u_core (
        .clk(clk_div),
        .rst(rst_n),
        .din(data_in),
        .dout(dbus)
    );
    io u_io (
        .d(dbus),
        .q(data_out),
        .s(status)
    );
endmodule

module div2 ( input clk, output out );
    reg q;
    always @(posedge clk) q <= ~q;
    assign out = q;
endmodule

module core ( input clk, input rst, input [7:0] din, output [7:0] dout );
    wire [7:0] t0, t1;
    flop u_reg0 ( .clk(clk), .rst(rst), .d(din), .q(t0) );
    flop u_reg1 ( .clk(clk), .rst(rst), .d(t0), .q(t1) );
    assign dout = t1;
endmodule

module flop ( input clk, input rst, input [7:0] d, output [7:0] q );
    reg [7:0] r;
    always @(posedge clk or negedge rst) begin
        if (!rst) r <= 8'h0;
        else r <= d;
    end
    assign q = r;
endmodule

module io ( input [7:0] d, output [7:0] q, output [3:0] s );
    assign q = d;
    assign s = 4'b0;
endmodule
