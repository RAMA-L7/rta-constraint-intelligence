"""Phase 17 — UI/API benchmark for the Ṛta workspace.

The application moved from Streamlit (AppTest) to a separate static frontend +
stdlib-only API server (docs/product/PHASE17_FRONTEND_ARCHITECTURE_DECISION.md).
This benchmark drives the SAME capabilities through the NEW architecture via
real HTTP: the frontend surface is verified to be served, and every analysis
endpoint returns REAL backend evidence (same fixtures, same assertions as the
Phase 16 AppTest benchmark — behavioral coverage preserved, not reduced).

Usage:
    python benchmarks/test_ui_app.py            # run all UI/API checks
"""

import io
import json
import subprocess
import sys
import threading
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from http.server import ThreadingHTTPServer  # noqa: E402

VALID_SDC = (
    "set sdc_version 2.2\n"
    "create_clock -name clk_core -period 5.0 [get_ports clk]\n"
    "set_clock_uncertainty -setup 0.15 -hold 0.08 [get_clocks clk_core]\n"
    "set_input_delay -max 1.0 -min 0.3 -clock clk_core [all_inputs]\n"
    "set_output_delay -max 1.5 -min 0.5 -clock clk_core [all_outputs]\n"
)

INVALID_SDC = (
    "set sdc_version 2.2\n"
    "create_clock -name clk_core -period 5.0 [get_ports clk]\n"
    "create_clock -name clk_core -period 10.0 [get_ports clk2]\n"
    "set_input_delay 6.0 -clock clk_core [all_inputs]\n"
    "set_output_delay -max 1.0 -clock clk_core [all_outputs]\n"
)

MULTICLK_SDC = (
    "create_clock -name clk_a -period 5.0 [get_ports clk_a]\n"
    "create_clock -name clk_b -period 7.5 [get_ports clk_b]\n"
    "set_clock_groups -asynchronous -group [get_clocks clk_a] -group [get_clocks clk_b]\n"
)

NETLIST = (
    "module top(input clk, input [3:0] din, output [3:0] dout);\n"
    "  reg [3:0] q;\n"
    "  always @(posedge clk) q <= din;\n"
    "  assign dout = q;\n"
    "endmodule\n"
)

# ── Server harness ────────────────────────────────────────────────────────
_server = None
_port = 8531


def start_server():
    global _server
    from api_server import Handler
    _server = ThreadingHTTPServer(("127.0.0.1", _port), Handler)
    t = threading.Thread(target=_server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.4)


def stop_server():
    if _server:
        _server.shutdown()
        _server.server_close()


def post(path, body):
    req = urllib.request.Request(
        f"http://127.0.0.1:{_port}{path}",
        data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req).read())


def get(path):
    return json.loads(urllib.request.urlopen(f"http://127.0.0.1:{_port}{path}").read())


def status(path):
    try:
        return urllib.request.urlopen(f"http://127.0.0.1:{_port}{path}").status
    except Exception:
        return 0


def post_bytes(path, body):
    """POST returning raw bytes (for binary endpoints like /api/mmc/zip)."""
    req = urllib.request.Request(
        f"http://127.0.0.1:{_port}{path}",
        data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return r.status, r.headers.get("Content-Type", ""), r.read()


# ── Checks ────────────────────────────────────────────────────────────────
PASSED, FAILED = [], []


def check(name, cond, detail=""):
    (PASSED if cond else FAILED).append(name)
    print(("  PASS " if cond else "  FAIL ") + name + (f"  | {detail}" if detail else ""))


def _analyze(sdc, **kw):
    body = {"sdc": sdc, **kw}
    return post("/api/analyze", body)


def run_all():
    print("=== UI/API BENCHMARK (Phase 17 — separate frontend + API) ===")
    start_server()

    # ── Surface ───────────────────────────────────────────────────────────
    check("UI-01 health endpoint", get("/api/health").get("ok") is True)
    check("UI-02 design tokens endpoint", len(get("/api/design").get("colors", {})) > 10)
    check("UI-03 rules endpoint", get("/api/rules").get("count", 0) >= 100)
    check("UI-04 index served", status("/") == 200)
    check("UI-05 css served", status("/assets/css/app.css") == 200)
    check("UI-06 app js served", status("/assets/js/app.js") == 200)
    check("UI-07 pages js served", status("/assets/js/pages.js") == 200)
    check("UI-08 theme js served", status("/assets/js/theme.js") == 200)
    check("UI-09 viz js served", status("/assets/js/viz.js") == 200)
    check("UI-10 spa fallback", status("/some/route") == 200)

    # ── Analysis: valid SDC ───────────────────────────────────────────────
    a = _analyze(VALID_SDC)
    check("UI-11 valid analyze ok", a.get("ok") is True)
    check("UI-12 valid has readiness", bool(a.get("readiness", {}).get("overall")))
    check("UI-13 valid has scope", bool(a.get("scope", {}).get("status")))
    check("UI-14 valid issues list", isinstance(a.get("issues"), list))
    check("UI-15 valid info list", isinstance(a.get("info"), list))
    check("UI-16 valid stats clocks", a.get("stats", {}).get("Clocks") == 1)
    check("UI-17 valid clock relations", len(a.get("clock_relations", {}).get("clocks", [])) >= 1)
    check("UI-18 valid no mock data", all(isinstance(i.get("msg"), str) for i in a.get("issues", [])))

    # ── Analysis: invalid SDC ─────────────────────────────────────────────
    b = _analyze(INVALID_SDC)
    errs = [i for i in b.get("issues", []) if i["sev"] == "error"]
    check("UI-19 invalid has errors", len(errs) >= 1)
    check("UI-20 duplicate clock detected",
          any(i["code"] == "SDC-002" for i in errs))
    check("UI-21 delay-vs-period detected",
          any(i["code"] in ("SDC-008", "SDC-009") for i in errs))
    check("UI-22 invalid readiness not READY",
          b.get("readiness", {}).get("overall") != "READY")

    # ── Analysis: multi-clock + relations ─────────────────────────────────
    c = _analyze(MULTICLK_SDC)
    cr = c.get("clock_relations", {})
    check("UI-23 multiclk clocks", len(cr.get("clocks", [])) == 2)
    check("UI-24 multiclk pairs", len(cr.get("pairs", [])) == 1)
    check("UI-25 multiclk async pair",
          cr.get("pairs", [{}])[0].get("inferred_relation") == "asynchronous")
    check("UI-26 multiclk groups parsed", len(cr.get("existing_groups", [])) == 1)
    check("UI-27 multiclk mismatch list", isinstance(cr.get("mismatches", []), list))

    # ── Analysis: design-aware (netlist) ──────────────────────────────────
    d = _analyze(VALID_SDC, netlist=NETLIST, top="top")
    check("UI-28 netlist mode", "Design Context" in d.get("mode_note", ""))
    check("UI-29 netlist no parse error", d.get("nl_error") is None)
    check("UI-30 netlist coverage summary", bool(d.get("coverage", {}).get("summary")))
    check("UI-31 coverage buckets", "inputs" in d.get("coverage", {}).get("summary", {}))
    check("UI-32 coverage-not-correctness flag",
          d.get("coverage", {}).get("summary", {}).get("coverage_is_not_correctness") is True)

    # ── Tools ─────────────────────────────────────────────────────────────
    li = post("/api/lint", {"sdc": VALID_SDC})
    check("UI-33 lint returns formatted", isinstance(li.get("formatted_text"), str))
    cv = post("/api/convert", {"sdc": VALID_SDC, "format": "json"})
    check("UI-34 convert json", cv.get("format") == "json" and "data" in cv)
    gn = post("/api/generate", {"params": {"design_name": "T",
                                           "clocks": [{"name": "clk", "port": "clk", "period": 5.0}]}})
    check("UI-35 generate sdc", "create_clock" in gn.get("sdc", ""))

    # ── MMC download (per-corner SDC ZIP archive) ─────────────────────────
    mz_status, mz_type, mz_bytes = post_bytes("/api/mmc/zip", {
        "template": {"design_name": "MY_DESIGN",
                     "clocks": [{"name": "clk_core", "port": "clk", "period": 5.0}]},
        "corners": [{"name": "C1", "operating_condition": "TT", "voltage": 0.8,
                      "temperature": 25.0, "process_type": "TT"},
                     {"name": "C2", "operating_condition": "SS", "voltage": 0.72,
                      "temperature": -40.0, "process_type": "SS"}]})
    check("UI-36 mmc zip returns zip", mz_status == 200 and "application/zip" in mz_type)
    try:
        zf = zipfile.ZipFile(io.BytesIO(mz_bytes))
        entries = sorted(zf.namelist())
        ok_zip = entries == ["C1.sdc", "C2.sdc"] and all(zf.read(n).strip() for n in entries)
    except Exception:
        ok_zip = False
    check("UI-37 mmc zip archive valid", ok_zip)

    stop_server()
    print(f"\nUI/API BENCHMARK: {len(PASSED)}/{len(PASSED) + len(FAILED)} passed")
    if FAILED:
        print("FAILED:", FAILED)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(run_all())
