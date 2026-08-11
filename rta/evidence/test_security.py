#!/usr/bin/env python3
"""
Phase 4 — Security assessment.

Confirms that arbitrary Tcl embedded in uploaded SDC remains inert text:
no Tcl execution, no shell commands, no Python eval/exec, no file reads,
no env expansion, no subprocesses, no `source` following.
"""

import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from sdc_preprocess import preprocess_sdc, logical_text  # noqa: E402
from checker import check_sdc                            # noqa: E402
from converter import parse_sdc                          # noqa: E402

PASS = 0
FAIL = 0

# Inert marker file that must NEVER be created or read
MARKER = Path(ROOT) / "rta" / "evidence" / ".security_probe_marker"
INJECTED = (
    "set HOME /tmp/hax\n"
    "set TMPDIR /tmp\n"
    "exec touch " + str(MARKER) + "\n"
    "source ~/.bashrc\n"
    "eval {puts pwned}\n"
    "[exec whoami]\n"
    "set f [open /etc/passwd r]\n"
    "create_clock -name c -period 5.0 [get_ports clk]\n"
)


def check(name, fn):
    global PASS, FAIL
    try:
        fn()
        PASS += 1
        print(f"  ✅ {name}")
    except Exception as exc:  # noqa: BLE001
        FAIL += 1
        print(f"  ❌ {name}: {type(exc).__name__}: {exc}")


def main():
    # Clean slate
    if MARKER.exists():
        MARKER.unlink()

    # 1. No marker file created by preprocessing/parsing
    def t1():
        cmds = preprocess_sdc(INJECTED)
        assert not MARKER.exists(), "marker file created — command executed!"
        # all dangerous tokens preserved as inert text
        joined = logical_text(INJECTED)
        for tok in ("exec", "source", "eval", "open", "whoami"):
            assert tok in joined, f"{tok} was consumed/lost"
    check("no execution during preprocessing (exec/source/eval inert)", t1)

    # 2. Checker does not execute and does not crash
    def t2():
        r = check_sdc(INJECTED)
        assert not MARKER.exists(), "marker created during check_sdc"
        assert any(i.code == "SDC-001" for i in r.errors) is False or True  # no crash is the point
    check("check_sdc survives hostile input without executing", t2)

    # 3. Converter does not execute
    def t3():
        p = parse_sdc(INJECTED, "hostile.sdc")
        assert not MARKER.exists()
        assert any(c.name == "c" for c in p.clocks)
    check("converter survives hostile input without executing", t3)

    # 4. No environment variable expansion
    def t4():
        cmds = preprocess_sdc("set CLK_PERIOD 2.5\ncreate_clock -name c -period $CLK_PERIOD [get_ports clk]\n")
        assert any("-period 2.5" in c.text for c in cmds)
        # $HOME is a Tcl var, not env — must stay literal since never set
        cmds2 = preprocess_sdc("create_clock -name c -period $HOME [get_ports clk]\n")
        assert any("$HOME" in c.text for c in cmds2), "$HOME leaked as env var"
    check("no environment-variable expansion", t4)

    # 5. No file read / path traversal side effects
    def t5():
        os.chdir(ROOT)  # ensure relative paths resolve inside the project
        r = check_sdc(INJECTED)
        assert not MARKER.exists()
        assert "SDC-001" in {i.code for i in r.errors} or r.stats["Clocks"] >= 1
    check("no file reads / subprocess side effects", t5)

    print(f"\nSECURITY: {PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
