// NA09 — MULTIPLE candidate top modules: 'chip_a' and 'chip_b' are both
// never instantiated. Design context must NOT be silently built — expect an
// explicit ambiguity error and empty top_candidates [chip_a, chip_b].
module chip_a (
    input clk
);
endmodule

module chip_b (
    input clk
);
endmodule
