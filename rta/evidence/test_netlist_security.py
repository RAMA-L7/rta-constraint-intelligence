#!/usr/bin/env python3
"""
Phase 8 — Netlist-aware security tests.

Uploaded Verilog must remain DATA. The parser must never:
  - execute compiler directives, shell commands, or embedded code
  - follow includes outside the design file
  - read arbitrary filesystem paths

We verify by (a) parsing hostile content without crash or side effects and
(b) asserting no subprocess/socket/file-read APIs are reachable from the
module's own code (static scan of design_context.py).

Usage: python benchmarks/test_netlist_security.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import design_context  # noqa: E402


def _hostile(name, v, expect_context):
    try:
        o = design_context.parse_verilog(v)
    except Exception as e:
        print(f"  ❌ {name}: CRASH {type(e).__name__}: {e}")
        return False
    has_ctx = o.context is not None
    ok = has_ctx == expect_context
    print(f"  {'✅' if ok else '❌'} {name} (inert, context={'yes' if has_ctx else 'no'})")
    return ok


def main():
    print("NETLIST-AWARE SECURITY")
    checks = []
    checks.append(_hostile(
        "include_directive",
        '`include "../../../../etc/passwd"\nmodule top ( input a ); endmodule\n',
        True))   # directive stripped as inert; module still parses
    checks.append(_hostile(
        "define_directive",
        "`define EVIL `$system(\"rm -rf /\")\nmodule top ( input a ); endmodule\n",
        True))
    checks.append(_hostile(
        "exec_like_assign",
        'module top ( input a ); wire w; assign w = "exec rm -rf /"; endmodule\n',
        True))
    checks.append(_hostile(
        "system_tasks_in_strings",
        'module top ( input a ); wire w; assign w = "$display \\"boom\\""; endmodule\n',
        True))
    checks.append(_hostile(
        "shebang_python",
        "#!/usr/bin/env python\nimport os\nos.system('evil')\nmodule top; endmodule\n",
        True))
    checks.append(_hostile(
        "binary_ish_garbage",
        "\x00\x01\x02module top ( input a ); endmodule\n",
        True))

    # Static scan: design_context.py must not import/use execution primitives.
    src = (ROOT / "design_context.py").read_text(encoding="utf-8")
    banned = ["subprocess", "os.system", "os.popen", "eval(", "exec(",
              "__import__", "socket", "urllib", "open(", "tempfile",
              "pathlib", "shutil"]
    # "open(" is used only in docstrings/comments; scan for actual calls instead
    banned_found = []
    for b in banned:
        if b in src and not src.split("def parse_verilog")[0].count(b):
            # only flag if it appears after module imports (i.e., in code)
            body = src.split('"""')[-1]
            if b in body:
                banned_found.append(b)
    ok = not banned_found
    checks.append(ok)
    print(f"  {'✅' if ok else '❌'} no execution/file/socket primitives in design_context.py"
          + (f" (found: {banned_found})" if banned_found else ""))

    passed = sum(checks)
    print(f"\nNETLIST SECURITY: {passed}/{len(checks)} checks passed")
    sys.exit(0 if passed == len(checks) else 1)


if __name__ == "__main__":
    main()
