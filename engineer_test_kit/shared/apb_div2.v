// Engineer Test Kit - canonical block: /2 divider cell
// Master point of the generated clock clk_div2 (SDC references the
// instance output pin u_div2/out).
module apb_div2 (
    input  clk,
    input  rst_n,
    input  scan_en,
    output out
);
    reg [1:0] div_reg;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) div_reg <= 2'b00;
        else if (scan_en) div_reg <= div_reg;
        else div_reg <= div_reg + 2'b01;
    end
    assign out = div_reg[1];
endmodule
