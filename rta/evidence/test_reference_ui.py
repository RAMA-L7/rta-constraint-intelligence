#!/usr/bin/env python3
"""
Phase 6 — reference designs E2E (re-targeted to the Phase 17 workspace API).

The premium workspace is now a static frontend + stdlib API server, so the
original AppTest-driven checks (which targeted the pre-workspace Streamlit
structure) are re-targeted to the SAME capability through the current
interface: the workspace surface must report backend truth for the reference
designs, repeat analysis must be stable, A→B→A must be isolated, and HTML
reports must match backend findings.

Usage:
    python benchmarks/test_reference_ui.py
"""

import json
import re
import sys
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
RD = ROOT / "rta" / "evidence" / "reference_designs"
sys.path.insert(0, str(ROOT))

from http.server import ThreadingHTTPServer  # noqa: E402
from checker import check_sdc              # noqa: E402
from reporter import generate_check_report  # noqa: E402

_port = 8542
_server = None


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


def post(path, body):
    req = urllib.request.Request(
        f"http://127.0.0.1:{_port}{path}",
        data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req).read())


def backend_counts(text):
    r = check_sdc(text)
    return {
        "errors": sum(1 for i in r.issues if i.sev == "error"),
        "warnings": sum(1 for i in r.issues if i.sev == "warning"),
        "info": len(r.info),
        "clocks": r.stats["Clocks"],
    }


def ui_counts(text):
    """Analyze via the workspace API (the UI's data source) and read the exact
    values the UI surfaces: the Validate rail reports the checker's unique-clock
    count (stats.Clocks) with the parsed inventory as fallback (app.js)."""
    a = post("/api/analyze", {"sdc": text})
    issues = a.get("issues", [])
    stats = a.get("stats") or {}
    clocks = stats.get("Clocks")
    if clocks is None:
        clocks = len(a.get("clock_relations", {}).get("clocks", []))
    return {
        "errors": sum(1 for i in issues if i.get("sev") == "error"),
        "warnings": sum(1 for i in issues if i.get("sev") == "warning"),
        "info": sum(1 for i in issues if i.get("sev") == "info"),
        "clocks": clocks,
    }


def validate_report(text, filename):
    """Generate the HTML check report and verify it matches backend truth."""
    r = check_sdc(text)
    html = generate_check_report(r, filename)
    backend_errors = sorted({i.code for i in r.issues if i.sev == "error"})
    backend_warnings = sorted({i.code for i in r.issues if i.sev == "warning"})
    missing = []
    for code in backend_errors + backend_warnings:
        # HTML report must contain each rule ID
        if code not in html:
            missing.append(f"{code} missing from report")
    # Summary totals in the report must equal backend counts
    e_summary = re.search(r"(\d+)\s+errors?", html, re.I)
    w_summary = re.search(r"(\d+)\s+warnings?", html, re.I)
    ok_counts = True
    if e_summary and int(e_summary.group(1)) != sum(1 for i in r.issues if i.sev == "error"):
        ok_counts = False
    if w_summary and int(w_summary.group(1)) != sum(1 for i in r.issues if i.sev == "warning"):
        ok_counts = False
    return html, missing, ok_counts


def main():
    start_server()
    try:
        designs = ["rd01_single_clock", "rd07_broken"]
        checks = []
        for d in designs:
            files = sorted((RD / d).glob("*.sdc"))
            if not files:
                checks.append((f"{d}: no sdc found", False, ""))
                continue
            text = files[0].read_text(encoding="utf-8", errors="replace")
            b = backend_counts(text)
            print(f"  {d}: backend E={b['errors']} W={b['warnings']} C={b['clocks']}")
            ui = ui_counts(text)
            ui_ok = (ui["errors"] == b["errors"] and ui["warnings"] == b["warnings"]
                     and ui["clocks"] == b["clocks"])
            checks.append((f"{d}: UI metrics match backend "
                           f"(UI E={ui['errors']} W={ui['warnings']} C={ui['clocks']} "
                           f"vs backend E={b['errors']} W={b['warnings']} C={b['clocks']})",
                           ui_ok, ""))
            # Repeat analyze on same file → identical results
            ui2 = ui_counts(text)
            checks.append((f"{d}: repeat Analyze is stable", ui2 == ui,
                           f"first={ui} second={ui2}"))
            # Report validation
            html, missing, ok_counts = validate_report(text, files[0].name)
            checks.append((f"{d}: HTML report contains all rule IDs and correct totals",
                           not missing and ok_counts, f"missing={missing} counts_ok={ok_counts}"))

        # Stage 12: Design A → Design B → Design A must show no state leakage.
        d1, d2 = designs
        f1 = sorted((RD / d1).glob("*.sdc"))[0]
        f2 = sorted((RD / d2).glob("*.sdc"))[0]
        t1 = f1.read_text(encoding="utf-8", errors="replace")
        t2 = f2.read_text(encoding="utf-8", errors="replace")
        u_a = ui_counts(t1)
        ui_counts(t2)
        u_a_again = ui_counts(t1)
        checks.append((f"A→B→A: {d1} results identical before/after {d2}",
                       u_a == u_a_again, f"first={u_a} again={u_a_again}"))
    finally:
        stop_server()

    print("\n" + "=" * 70)
    passed = sum(1 for _, ok, _ in checks if ok)
    print(f"UI E2E + REPORT VALIDATION — {passed}/{len(checks)} checks passed")
    for name, ok, detail in checks:
        print(f"  {'✅' if ok else '❌'} {name}")
        if not ok and detail:
            print(f"      → {detail}")
    sys.exit(0 if passed == len(checks) else 1)


if __name__ == "__main__":
    main()
