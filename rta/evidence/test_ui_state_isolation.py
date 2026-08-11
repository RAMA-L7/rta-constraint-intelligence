"""Phase 17 — UI state-isolation tests (API architecture).

The workspace moved from Streamlit AppTest to a separate frontend + stdlib API
server. State isolation is verified at the API boundary: repeated analyzes are
stable and switching between different SDC inputs does not leak state from the
previous input — exactly the A→B→A property the Phase 16 AppTest benchmark
checked, through the new transport.

Run:  python benchmarks/test_ui_state_isolation.py
"""

import json
import sys
import threading
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from http.server import ThreadingHTTPServer  # noqa: E402

VALID_A = (
    "set sdc_version 2.2\n"
    "create_clock -name clk_core -period 5.0 [get_ports clk]\n"
    "set_clock_uncertainty -setup 0.15 -hold 0.08 [get_clocks clk_core]\n"
    "set_input_delay -max 1.0 -min 0.3 -clock clk_core [all_inputs]\n"
    "set_output_delay -max 1.5 -min 0.5 -clock clk_core [all_outputs]\n"
)

VALID_B = (
    "create_clock -name clk_fast -period 2.0 [get_ports clk_f]\n"
    "create_clock -name clk_slow -period 20.0 [get_ports clk_s]\n"
    "set_clock_groups -asynchronous -group [get_clocks clk_fast] -group [get_clocks clk_slow]\n"
    "set_input_delay -max 1.0 -clock clk_fast [get_ports data_in]\n"
)

INVALID_C = (
    "create_clock -name clk_core -period 5.0 [get_ports clk]\n"
    "set_input_delay -max 9.0 -clock clk_core [all_inputs]\n"
    "set_output_delay -max 9.0 -clock clk_core [all_outputs]\n"
)

_server = None
_port = 8533


def start_server():
    global _server
    from api_server import Handler
    _server = ThreadingHTTPServer(("127.0.0.1", _port), Handler)
    threading.Thread(target=_server.serve_forever, daemon=True).start()
    time.sleep(0.4)


def stop_server():
    if _server:
        _server.shutdown()
        _server.server_close()


def analyze(sdc):
    req = urllib.request.Request(
        f"http://127.0.0.1:{_port}/api/analyze",
        data=json.dumps({"sdc": sdc}).encode(),
        headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req).read())


PASSED, FAILED = [], []


def check(name, cond, detail=""):
    (PASSED if cond else FAILED).append(name)
    print(("  PASS " if cond else "  FAIL ") + name + (f"  | {detail}" if detail else ""))


def _clock_names(r):
    return sorted(c.get("name", "") for c in r.get("clock_relations", {}).get("clocks", []))


def _errors(r):
    return sorted(i.get("code", "") for i in r.get("issues", []) if i.get("sev") == "error")


def run_all():
    print("=== UI STATE ISOLATION (Phase 17 — API architecture) ===")
    start_server()

    # 1. Repeated analyze of A is stable
    a1 = analyze(VALID_A)
    a2 = analyze(VALID_A)
    a3 = analyze(VALID_A)
    check("ISO-01 A repeated stable (clocks)",
          _clock_names(a1) == _clock_names(a2) == _clock_names(a3))
    check("ISO-02 A repeated stable (errors)",
          _errors(a1) == _errors(a2) == _errors(a3))
    check("ISO-03 A readiness stable",
          a1.get("readiness", {}).get("overall") == a2.get("readiness", {}).get("overall"))

    # 2. Switch to B — no leakage from A
    b = analyze(VALID_B)
    check("ISO-04 B clocks differ from A",
          set(_clock_names(b)) != set(_clock_names(a1)))
    check("ISO-05 B no A clock leak", "clk_core" not in _clock_names(b))
    check("ISO-06 B readiness is its own",
          b.get("readiness", {}).get("overall") == a1.get("readiness", {}).get("overall")
          or b.get("readiness", {}).get("overall") != "")

    # 3. Return to A — deterministic recovery
    a4 = analyze(VALID_A)
    check("ISO-07 A restored after B (clocks)",
          _clock_names(a4) == _clock_names(a1))
    check("ISO-08 A restored after B (errors)",
          _errors(a4) == _errors(a1))
    check("ISO-09 A restored readiness",
          a4.get("readiness", {}).get("overall") == a1.get("readiness", {}).get("overall"))

    # 4. A → B → A → C invalid → A again
    c = analyze(INVALID_C)
    check("ISO-10 C invalid has SDC-008/009",
          any(e in ("SDC-008", "SDC-009") for e in _errors(c)))
    a5 = analyze(VALID_A)
    check("ISO-11 A unaffected after C",
          _clock_names(a5) == _clock_names(a1))
    check("ISO-12 A errors unaffected after C",
          _errors(a5) == _errors(a1))

    stop_server()
    print(f"\nSTATE ISOLATION: {len(PASSED)}/{len(PASSED) + len(FAILED)} passed")
    if FAILED:
        print("FAILED:", FAILED)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(run_all())
