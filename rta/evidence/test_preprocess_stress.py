#!/usr/bin/env python3
"""
Phase 4 — Preprocessor stress test.

Aggressively exercises sdc_preprocess.preprocess_sdc() with adversarial input
combinations: comments + multiline, multiline + scientific notation, variables
+ multiline, variables + comments, braces + comments, brackets + braces,
quoted strings containing '#', multiple commands, blank lines, CRLF, LF, tabs,
large whitespace, Unicode BOM, no trailing newline, very long logical commands,
and large SDC files.

Assertions (raises on failure):
  - no crash
  - no command loss
  - no command duplication
  - correct source provenance (start_line/end_line monotonic, in-range)
  - deterministic output (same input -> same result)
"""

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from sdc_preprocess import preprocess_sdc  # noqa: E402

PASS = 0
FAIL = 0


def check(name, fn):
    global PASS, FAIL
    try:
        fn()
        PASS += 1
        print(f"  ✅ {name}")
    except AssertionError as exc:
        FAIL += 1
        print(f"  ❌ {name}: {exc}")
    except Exception as exc:  # noqa: BLE001
        FAIL += 1
        print(f"  💥 {name}: {type(exc).__name__}: {exc}")


def assert_provenance(cmds, n_lines):
    prev_end = 0
    for c in cmds:
        assert 1 <= c.start_line <= c.end_line <= n_lines, \
            f"bad provenance {c.start_line}..{c.end_line} for {n_lines} lines"
        assert c.start_line >= prev_end, "start_line went backwards"
        prev_end = max(prev_end, c.end_line)


# ── Adversarial combinations ────────────────────────────────────────────────

CASES = {
    "comments + multiline": (
        "# create_clock -name ghost -period 1.0 [get_ports ghost]\n"
        "create_clock \\\n"
        "    -name sys_clk \\\n"
        "    -period 10.0 # trailing comment\n"
        "    [get_ports clk]\n"
    ),
    "multiline + scientific notation": (
        "create_clock \\\n"
        "    -name c \\\n"
        "    -period 2.5e-1 \\\n"
        "    [get_ports clk]\n"
    ),
    "variables + multiline": (
        "set CLK_PERIOD 2.5\n"
        "create_clock \\\n"
        "    -name core_clk \\\n"
        "    -period $CLK_PERIOD \\\n"
        "    [get_ports clk]\n"
    ),
    "variables + comments": (
        "set CLK_PERIOD 2.5 # period in ns\n"
        "create_clock -name c -period $CLK_PERIOD [get_ports clk] # master\n"
    ),
    "braces + comments": (
        "set_clock_groups -asynchronous \\\n"
        "    -group [get_clocks {clk_a clk_b}] \\\n"
        "    -group [get_clocks clk_c]  # comment\n"
    ),
    "brackets + braces": (
        "set_false_path -from [get_ports {data_in data_out}] -to [get_pins {U1/A U1/B}]\n"
    ),
    "quoted #": (
        'set_dont_use -lib_cell "BUF#X2"\n'
        'set_dont_touch -lib_cell "AND2X1 # special"\n'
    ),
    "multiple commands one line each": (
        "create_clock -name a -period 5.0 [get_ports a]\n"
        "create_clock -name b -period 7.5 [get_ports b]\n"
        "set_input_delay -max 1.0 -min 0.2 -clock a [all_inputs]\n"
    ),
    "blank lines + comments": (
        "\n\n# comment 1\n\ncreate_clock -name c -period 5.0 [get_ports clk]\n\n\n"
        "# comment 2\nset_input_delay -max 1.0 -clock c [all_inputs]\n\n"
    ),
    "CRLF line endings": (
        "create_clock -name c -period 5.0 [get_ports clk]\r\n"
        "set_input_delay -max 1.0 -min 0.2 -clock c [all_inputs]\r\n"
    ),
    "tabs + large whitespace": (
        "\tcreate_clock   -name   c   -period   5.0   [get_ports clk]\t\n"
        "    set_input_delay\t-max 1.0\t-min 0.2  -clock c [all_inputs]\n"
    ),
    "no trailing newline": (
        "create_clock -name c -period 5.0 [get_ports clk]\n"
        "set_input_delay -max 1.0 -min 0.2 -clock c [all_inputs]"
    ),
    "trailing backslash (unterminated continuation)": (
        "create_clock -name c -period 5.0 \\\n"
    ),
    "semicolon separated": (
        "create_clock -name c -period 5.0 [get_ports clk]; set_input_delay -max 1.0 -clock c [all_inputs]\n"
    ),
    "backslash inside quotes": (
        'set_propagated_clock "clk\\n" [get_clocks c]\n'
    ),
}


def test_cases():
    for name, text in CASES.items():
        def run(t=text):
            cmds1 = preprocess_sdc(t)
            cmds2 = preprocess_sdc(t)
            # deterministic
            assert [c.text for c in cmds1] == [c.text for c in cmds2], "non-deterministic"
            assert [c.start_line for c in cmds1] == [c.start_line for c in cmds2]
            assert [c.end_line for c in cmds1] == [c.end_line for c in cmds2]
            assert_provenance(cmds1, t.count("\n") + 1)
            # no command loss for the multi-command cases
            n_cmd = len(cmds1)
            if name in ("multiple commands one line each",):
                assert n_cmd == 3, f"expected 3 commands, got {n_cmd}"
            if name in ("no trailing newline", "CRLF line endings"):
                assert n_cmd == 2, f"expected 2 commands, got {n_cmd}"
        check(name, run)


def test_bom_and_encodings():
    def run():
        text = "\ufeffcreate_clock -name c -period 5.0 [get_ports clk]\n"
        cmds = preprocess_sdc(text)
        # BOM may or may not survive; command must still be found
        assert any("create_clock" in c.text for c in cmds)
        # mixed LF/CRLF
        mixed = "create_clock -name a -period 5.0 [get_ports a]\r\ncreate_clock -name b -period 6.0 [get_ports b]\n"
        assert len([c for c in preprocess_sdc(mixed) if "create_clock" in c.text]) == 2
    check("BOM + mixed line endings", run)


def test_very_long_logical_command():
    def run():
        port_list = " ".join(f"p{i}" for i in range(500))
        text = f"set_false_path -from [get_ports {{{port_list}}}] -to [get_pins U/A]\n"
        cmds = preprocess_sdc(text)
        assert len(cmds) == 1
        assert len(cmds[0].text) > 2000
        assert_provenance(cmds, 1)
    check("very long logical command (1 line, 5k chars)", run)


def test_large_file_no_loss():
    def run():
        n = 500
        lines = ["# header comment"]
        for i in range(n):
            lines.append(f"create_clock -name c{i} -period 5.0 [get_ports p{i}]")
            lines.append(f"set_input_delay -max 1.0 -min 0.2 -clock c{i} [get_ports in{i}]")
        text = "\n".join(lines) + "\n"
        cmds = preprocess_sdc(text)
        clocks = [c for c in cmds if c.text.startswith("create_clock")]
        delays = [c for c in cmds if c.text.startswith("set_input_delay")]
        assert len(clocks) == n, f"lost clocks: {len(clocks)} != {n}"
        assert len(delays) == n, f"lost delays: {len(delays)} != {n}"
        assert len(cmds) == 2 * n, f"duplicates/loss: {len(cmds)} != {2 * n}"
        assert_provenance(cmds, len(lines))
    check("large file (1000 commands) — no loss/duplication", run)


def test_brace_depth_spanning():
    def run():
        # open brace spanning lines must not break provenance
        text = "set_clock_groups -asynchronous \\\n    -group [get_clocks {\\\n        clk_a clk_b}] \n"
        cmds = preprocess_sdc(text)
        assert len(cmds) == 1
        assert "clk_a clk_b" in cmds[0].text
    check("braces spanning physical lines", run)


def test_variable_order_and_undefined():
    def run():
        text = (
            "set P 10\n"
            "create_clock -name a -period $P [get_ports a]\n"
            "set P 5\n"
            "create_clock -name b -period $P [get_ports b]\n"
            "create_clock -name u -period $UNKNOWN [get_ports u]\n"
        )
        cmds = preprocess_sdc(text)
        joined = [c.text for c in cmds]
        assert any("-period 10" in t for t in joined), "first clock must use 10"
        assert any("-period 5" in t for t in joined), "second clock must use 5"
        assert any("$UNKNOWN" in t for t in joined), "undefined var must be preserved"
    check("order-aware reassignment + undefined preserved", run)


def test_brace_suppresses_substitution():
    def run():
        text = "set X 5\nset_clock_groups -asynchronous -group [get_clocks {$X}]\n"
        cmds = preprocess_sdc(text)
        assert any("$X" in c.text for c in cmds), "braces must suppress substitution"
    check("$ inside braces stays literal (Tcl rule)", run)


def main():
    print("PHASE 4 PREPROCESSOR STRESS TEST")
    test_cases()
    test_bom_and_encodings()
    test_very_long_logical_command()
    test_large_file_no_loss()
    test_brace_depth_spanning()
    test_variable_order_and_undefined()
    test_brace_suppresses_substitution()
    print(f"\nSTRESS: {PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
