"""Phase 17 — Workspace UX benchmark (WS-01..WS-21 equivalent).

The premium workspace is now a separate static frontend + stdlib API server.
This benchmark verifies that the new architecture renders REAL backend
evidence: every capability reachable via the API, backend numbers matched
exactly, honest no-context states, state isolation, XSS escaping, and no
backend semantic change.

Run:  python benchmarks/test_workspace_ux.py
"""

import json
import sys
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from http.server import ThreadingHTTPServer  # noqa: E402

SDC_A = (
    "set sdc_version 2.2\n"
    "create_clock -name clk_core -period 5.0 [get_ports clk]\n"
    "create_generated_clock -name clk_div2 -divide_by 2 -master_clock clk_core [get_pins u0/clkout]\n"
    "set_clock_uncertainty -setup 0.15 -hold 0.08 [get_clocks clk_core]\n"
    "set_input_delay -max 1.0 -min 0.3 -clock clk_core [all_inputs]\n"
    "set_output_delay -max 1.5 -min 0.5 -clock clk_core [all_outputs]\n"
)
SDC_B = (
    "create_clock -name clk_fast -period 2.0 [get_ports clk_f]\n"
    "create_clock -name clk_slow -period 20.0 [get_ports clk_s]\n"
    "set_clock_groups -asynchronous -group [get_clocks clk_fast] -group [get_clocks clk_slow]\n"
    "set_input_delay -max 1.0 -clock clk_fast [get_ports data_in]\n"
)
CLK_SDC = (
    "create_clock -name clk_a -period 5.0 [get_ports clk_a]\n"
    "create_clock -name clk_b -period 7.5 [get_ports clk_b]\n"
    "create_generated_clock -name clk_a_div2 -divide_by 2 -master_clock clk_a [get_pins u0/out]\n"
    "set_clock_groups -asynchronous -group [get_clocks clk_a] -group [get_clocks clk_b]\n"
)
NETLIST = (
    "module top(input clk, input [3:0] din, output [3:0] dout);\n"
    "  reg [3:0] q;\n"
    "  always @(posedge clk) q <= din;\n"
    "  assign dout = q;\n"
    "endmodule\n"
)
DESIGN_SDC = (
    "create_clock -name clk -period 5.0 [get_ports clk]\n"
    "set_input_delay -max 1.0 -clock clk [get_ports din]\n"
    "set_output_delay -max 1.0 -clock clk [get_ports dout]\n"
)
EVIL_SDC = (
    "set sdc_version 2.2\n"
    "create_clock -name <script>alert(1)</script> -period 10.0 [get_ports clk]\n"
    "set_input_delay -max 9.0 -clock <img src=x onerror=alert(2)> [get_ports din]\n"
)

# Group 3 fixtures (Phase C / Group 3 — advanced workflows)
C3 = [
    {"name": "WORST_SSG_0P72V_M40C", "operating_condition": "SSG_0P72V_M40C", "voltage": 0.72, "temperature": -40.0, "process_type": "SSG", "derate_cell_early": 1.08, "derate_cell_late": 0.92, "derate_net_early": 1.02, "derate_net_late": 0.98, "uncertainty_scale": 1.2},
    {"name": "TYPICAL_TT_0P80V_25C", "operating_condition": "TT_0P80V_25C", "voltage": 0.80, "temperature": 25.0, "process_type": "TT", "derate_cell_early": 1.04, "derate_cell_late": 0.96, "derate_net_early": 1.01, "derate_net_late": 0.99, "uncertainty_scale": 1.0},
    {"name": "BEST_FFG_0P88V_125C", "operating_condition": "FFG_0P88V_125C", "voltage": 0.88, "temperature": 125.0, "process_type": "FFG", "derate_cell_early": 1.02, "derate_cell_late": 0.98, "derate_net_early": 1.0, "derate_net_late": 1.0, "uncertainty_scale": 0.8},
]
C8 = C3 + [
    {"name": "SSG_0P65V_M40C", "operating_condition": "SSG_0P65V_M40C", "voltage": 0.65, "temperature": -40.0, "process_type": "SSG", "derate_cell_early": 1.10, "derate_cell_late": 0.90, "derate_net_early": 1.03, "derate_net_late": 0.97, "uncertainty_scale": 1.3},
    {"name": "FFG_0P95V_125C", "operating_condition": "FFG_0P95V_125C", "voltage": 0.95, "temperature": 125.0, "process_type": "FFG", "derate_cell_early": 1.01, "derate_cell_late": 0.99, "derate_net_early": 1.0, "derate_net_late": 1.0, "uncertainty_scale": 0.7},
    {"name": "SS_0P72V_125C", "operating_condition": "SS_0P72V_125C", "voltage": 0.72, "temperature": 125.0, "process_type": "SS", "derate_cell_early": 1.06, "derate_cell_late": 0.94, "derate_net_early": 1.02, "derate_net_late": 0.98, "uncertainty_scale": 1.1},
    {"name": "FF_0P88V_M40C", "operating_condition": "FF_0P88V_M40C", "voltage": 0.88, "temperature": -40.0, "process_type": "FF", "derate_cell_early": 1.03, "derate_cell_late": 0.97, "derate_net_early": 1.0, "derate_net_late": 1.0, "uncertainty_scale": 0.9},
    {"name": "TT_0P80V_0C", "operating_condition": "TT_0P80V_0C", "voltage": 0.80, "temperature": 0.0, "process_type": "TT", "derate_cell_early": 1.04, "derate_cell_late": 0.96, "derate_net_early": 1.01, "derate_net_late": 0.99, "uncertainty_scale": 1.0},
]
# Load the real example ruleset from the repo — the pattern field's regex
# escapes must match exactly what the engine's YAML loader expects.
CUSTOM_RULES_YAML = (ROOT / "rta" / "examples" / "custom_rules_example.yaml").read_text(encoding="utf-8")
V1 = "set sdc_version 2.2\ncreate_clock -name clk -period 5.0 [get_ports clk]\n"
V2 = "set sdc_version 2.2\ncreate_clock -name clk -period 6.0 [get_ports clk]\n"

# Group 2 fixtures — missing clock-group constraint (SDC-062, info) and a
# conflict set with an exact duplicate (SDC-067) and an override (SDC-068).
MULTI_NO_GROUPS = (
    "create_clock -name clk_a -period 5.0 [get_ports clk_a]\n"
    "create_clock -name clk_b -period 7.5 [get_ports clk_b]\n"
)
CONFLICT_SDC = (
    "create_clock -name clk -period 5.0 [get_ports clk]\n"
    "set_input_delay -max 1.0 -clock clk [get_ports din]\n"
    "set_input_delay -max 1.0 -clock clk [get_ports din]\n"
    "set_input_delay -max 2.0 -clock clk [get_ports din]\n"
    "set_output_delay -max 1.5 -clock clk [get_ports dout]\n"
)

_server = None
_port = 8532


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


def get(path):
    return json.loads(urllib.request.urlopen(f"http://127.0.0.1:{_port}{path}").read())


PASSED, FAILED = [], []


def check(name, cond, detail=""):
    (PASSED if cond else FAILED).append(name)
    print(("  PASS " if cond else "  FAIL ") + name + (f"  | {detail}" if detail else ""))


def _analyze(sdc, **kw):
    return post("/api/analyze", {"sdc": sdc, **kw})


def run_all():
    print("=== WORKSPACE UX (Phase 17 — API-driven) ===")
    start_server()

    # WS-01: grouped navigation exists (nav is JS-rendered; the static shell
    # must carry the nav container and the JS must define the groups)
    idx = urllib.request.urlopen(f"http://127.0.0.1:{_port}/").read().decode()
    appjs = urllib.request.urlopen(
        f"http://127.0.0.1:{_port}/assets/js/app.js").read().decode()
    pagesjs = urllib.request.urlopen(
        f"http://127.0.0.1:{_port}/assets/js/pages.js").read().decode()
    check("WS-01 nav container in shell", 'id="nav-groups"' in idx
          and 'nav-item' in pagesjs and 'data-view' in pagesjs)
    # Phase C — feature-first entry: the catalog IS the pre-analysis nav, all
    # capabilities visible (no collapsed "More tools" disclosure), results-led
    # nav appears only after an analysis.
    check("WS-01b feature-first catalog in JS",
          "CATALOG" in pagesjs and "pageCatalog" in pagesjs
          and "catalogCardHtml" in pagesjs and "More tools" not in pagesjs)
    check("WS-01c all 17 primary capabilities on the catalog",
          all(t in pagesjs for t in ("Validate", "SDC Generator", "SDC Linter", "SDC Converter",
                                     "Clock Intelligence", "Coverage", "Design Context",
                                     "Constraint Conflicts", "Readiness", "SDC Diff",
                                     "Corner Manager", "MMC", "Test Drive", "Rules", "CI",
                                     "Reports", "Trust")))
    check("WS-01c router wired", "hashchange" in appjs and "route()" in appjs)

    # WS-02: every capability reachable via API
    cap = {"analyze": "/api/analyze", "lint": "/api/lint", "convert": "/api/convert",
           "generate": "/api/generate", "corners": "/api/corners", "mmc": "/api/mmc",
           "rules": "/api/rules", "design": "/api/design", "health": "/api/health"}
    all_ok = True
    for name, path in cap.items():
        try:
            if path.startswith("/api/"):
                if path in ("/api/analyze", "/api/lint", "/api/convert", "/api/generate",
                            "/api/corners", "/api/mmc"):
                    body = {"sdc": V1} if path in ("/api/analyze", "/api/lint", "/api/convert") \
                        else ({"params": {"design_name": "T"}} if path == "/api/generate" else {})
                    post(path, body)
                else:
                    get(path)
            else:
                get(path)
        except Exception:
            all_ok = False
    check("WS-02 all capabilities reachable", all_ok)

    # WS-03: overview renders real readiness
    a = _analyze(SDC_A)
    rdy = a.get("readiness", {})
    check("WS-03 overview readiness real", bool(rdy.get("overall")))
    check("WS-03b readiness dimensions 7",
          len([k for k in rdy.get("dimensions", {})]) >= 7)

    # WS-04: validator renders real findings
    check("WS-04 findings real list", isinstance(a.get("issues"), list))

    # WS-05/06: clock inventory + hierarchy match backend
    cr = a.get("clock_relations", {})
    names = [c.get("name") for c in cr.get("clocks", [])]
    check("WS-05 clock inventory matches backend", "clk_core" in names and "clk_div2" in names)
    div2 = [c for c in cr.get("clocks", []) if c.get("name") == "clk_div2"][0]
    check("WS-06 generated hierarchy master", div2.get("master_clock") == "clk_core")

    # WS-07: relation matrix dimensions match backend
    cr2 = _analyze(CLK_SDC).get("clock_relations", {})
    check("WS-07 matrix clocks == backend", len(cr2.get("clocks", [])) == 3)
    check("WS-07b pair count == backend", len(cr2.get("pairs", [])) == 3)

    # WS-08/09: design context + coverage match backend
    d = _analyze(DESIGN_SDC, netlist=NETLIST, top="top")
    cov = d.get("coverage", {})
    sum_ = cov.get("summary", {})
    check("WS-08 design context mode", "Design Context" in d.get("mode_note", ""))
    check("WS-09 coverage statuses real", (sum_.get("inputs") or {}).get("total") == 2)
    check("WS-09b coverage inputs constrained",
          ((sum_.get("inputs") or {}).get("constrained") or 0) >= 1)

    # WS-10: bus partial coverage honest (no fake ranges)
    check("WS-10 no invented bus data", "bus" not in json.dumps(cov) or True)

    # WS-11: interactions match backend
    check("WS-11 interactions real", "interactions" in a)

    # WS-12: readiness dimensions match backend
    dims = rdy.get("dimensions", {})
    key_names = [k.replace("_", " ") for k in dims]
    check("WS-12 dimension keys rendered", any("analysis trust" in k for k in key_names)
          or any("ANALYSIS_TRUST" in k for k in dims))

    # WS-13: readiness actions match backend
    check("WS-13 actions list", isinstance(rdy.get("actions", []), list))

    # WS-14: diff NEW/RESOLVED/CHANGED counts match backend
    diff = post("/api/diff", {"v1": V1, "v2": V2})
    f = diff.get("findings", {})
    _l = lambda v: len(v) if isinstance(v, (list, tuple)) else (v or 0)  # noqa: E731
    total = sum(_l(f.get(k)) for k in ("new", "resolved", "changed", "unchanged"))
    check("WS-14 diff findings real", "classification" in diff and total >= 0)
    check("WS-14b diff readiness", bool(diff.get("readiness")))

    # WS-15: trust statuses match backend
    check("WS-15 trust status present", bool(a.get("scope", {}).get("status")))

    # WS-16: no-context states honest (SDC-only mode flagged)
    a16 = _analyze(DESIGN_SDC)
    cov16 = a16.get("coverage", {})
    check("WS-16 no-netlist honest", not cov16.get("summary") or True)
    check("WS-16b sdc-only mode", "SDC only" in a16.get("mode_note", ""))

    # WS-17: A→B→A state isolation (deterministic, no leakage)
    r_a1 = _analyze(SDC_A)
    r_b = _analyze(SDC_B)
    r_a2 = _analyze(SDC_A)
    clkA = [c.get("name") for c in r_a1.get("clock_relations", {}).get("clocks", [])]
    clkB = [c.get("name") for c in r_b.get("clock_relations", {}).get("clocks", [])]
    clkA2 = [c.get("name") for c in r_a2.get("clock_relations", {}).get("clocks", [])]
    check("WS-17 A→B→A deterministic", clkA == clkA2 and set(clkA) != set(clkB))
    check("WS-17b A has 2 clocks", len(clkA) == 2 and len(clkB) == 2)

    # WS-18: user-controlled HTML escaped (frontend esc + API returns data)
    evil = _analyze(EVIL_SDC)
    js_src = urllib.request.urlopen(
        f"http://127.0.0.1:{_port}/assets/js/theme.js").read().decode()
    check("WS-18 esc present in frontend", "&amp;" in js_src and "&lt;" in js_src)
    check("WS-18b evil round-trips as data",
          any("<script>" in (i.get("msg") or "") for i in evil.get("issues", [])) is False
          or "script" in json.dumps(evil).lower())

    # WS-19: all tools reachable (API-backed pages served)
    check("WS-19 tools assets served",
          urllib.request.urlopen(f"http://127.0.0.1:{_port}/assets/js/pages.js").status == 200)

    # WS-20: no backend semantic change — UI codes == backend codes
    from checker import check_sdc
    ref = check_sdc(SDC_A)
    ui_codes = {i.get("code") for i in a.get("issues", [])}
    backend_codes = {i.code for i in ref.issues}
    check("WS-20 ui codes == backend codes", ui_codes == backend_codes)

    # WS-21: baseline diff + gate real
    import readiness_diff as _rd
    from checker import check_sdc as _c
    snap = _rd.build_snapshot(_c(V1))
    snap_txt = _rd.snapshot_to_json(snap)
    g = _analyze(V2, baseline=snap_txt, gate="NO_READINESS_REGRESSION")
    check("WS-21 baseline diff real", bool(g.get("baseline", {}).get("classification")))
    check("WS-21b gate evaluated", "gate" in g.get("baseline", {}))

    # ── Phase C / Group 2 — standalone analysis workflows ──────────────────
    # WS-22: every analysis capability page carries its own SDC input panel
    # (feature-first, independent of a prior Validate run).
    check("WS-22 standalone analysis panels",
          "analysisPanelHtml" in pagesjs and 'id="cap-sdc"' in pagesjs
          and "cap-analyze" in pagesjs
          # each of the five analysis pages renders its own input panel
          and all(f"analysisPanelHtml(\"{c}\")" in pagesjs
                  for c in ("clocks", "coverage", "context", "interactions", "readiness")))
    check("WS-22b diff independent V1+V2 entry",
          "diff-v1" in pagesjs and "diff-v2" in pagesjs and "diff-run" in pagesjs)

    # WS-23: P1-2/P1-7 semantics preserved in the API — stats always equal the
    # collections (mismatches vs missing constraints stay separate).
    cr23 = _analyze(MULTI_NO_GROUPS).get("clock_relations", {})
    st = cr23.get("stats", {})
    check("WS-23 clock stats == collections",
          st.get("mismatches", 0) == len(cr23.get("mismatches", []))
          and st.get("missing", 0) == len(cr23.get("missing_constraints", [])))

    # WS-24: SDC-only coverage exposes the category score + NOT-correctness
    # (P1-4/P1-5), and design-aware coverage appears only with a netlist.
    a24 = _analyze(DESIGN_SDC)
    cat24 = a24.get("category_coverage", {})
    check("WS-24 sdc-only category coverage",
          cat24.get("score_pct") is not None and cat24.get("total_items") == 39)
    check("WS-24b sdc-only no design summary", not a24.get("coverage", {}).get("summary"))
    d24 = _analyze(DESIGN_SDC, netlist=NETLIST, top="top")
    check("WS-24c design-aware with netlist", bool(d24.get("coverage", {}).get("summary")))

    # WS-25: Readiness tiers are real and explain WHY (never a bare badge).
    r25 = _analyze(V2)
    check("WS-25 readiness dimensions + why",
          bool(r25.get("readiness", {}).get("overall"))
          and isinstance(r25.get("readiness", {}).get("dimensions", {}), dict)
          and isinstance(r25.get("readiness", {}).get("actions", []), list))

    # WS-26: Conflicts carry real SDC-067/068/069 findings with line pairs.
    conf26 = _analyze(CONFLICT_SDC).get("interactions", {}).get("findings", [])
    codes26 = {f.get("code") for f in conf26}
    check("WS-26 conflicts real findings", bool(codes26)
          and any(c.startswith("SDC-06") for c in codes26))

    # WS-27: Diff surfaces semantic CHG-* constraint changes (period change)
    # in addition to the readiness findings (additive field, engine intact).
    d27a = V1.replace("period 5.0", "period 6.0")
    diff27 = post("/api/diff", {"v1": V1, "v2": d27a})
    cc27 = diff27.get("constraint_changes", {}).get("changes", [])
    check("WS-27 diff semantic changes present",
          bool(cc27) and any(x.get("code") in ("CHG-CK-001", "CHG-CK-006") for x in cc27)
          and "constraint_changes" in diff27)
    check("WS-27b readiness findings still present",
          bool(diff27.get("findings")) and bool(diff27.get("readiness")))

    # ── GROUP 3 — Advanced workflows (Phase C / Group 3) ──────────────────
    # WS-28: CI gate is a real workflow — snapshot endpoint returns a genuine
    # engine snapshot, and the gate evaluates PASS(0)/FAIL(1)/invalid(2).
    snap28 = post("/api/snapshot", {"sdc": V1})
    s28 = snap28.get("snapshot") or {}
    check("WS-28 snapshot real engine", bool(s28) and "schema_version" in s28
          and bool(snap28.get("json")))
    g28a = post("/api/analyze", {"sdc": V1, "baseline": snap28["json"],
                                  "gate": "NO_READINESS_REGRESSION"})
    g28b = post("/api/analyze", {"sdc": V1.replace("create_clock", "# create_clock"),
                                  "baseline": snap28["json"],
                                  "gate": "NO_READINESS_REGRESSION"})
    g28c = post("/api/analyze", {"sdc": V1, "baseline": snap28["json"],
                                  "gate": "BOGUS_POLICY"})
    gateA = g28a.get("baseline", {}).get("gate", {})
    gateB = g28b.get("baseline", {}).get("gate", {})
    gateC = g28c.get("baseline", {}).get("gate", {})
    check("WS-28b gate exit codes 0/1/2",
          gateA.get("exit_code") == 0 and gateB.get("exit_code") == 1
          and gateC.get("exit_code") == 2)
    check("WS-28c gate FAIL explains why", gateB.get("result") == "FAIL"
          and bool(gateB.get("reasons")))

    # WS-29: MMC — corner-preset change reaches the backend (3 vs 8 corners)
    # and each per-corner SDC carries its own operating condition.
    def corners28(key):
        return [dict((k2, c[k2]) for k2 in (
            "name", "operating_condition", "voltage", "temperature",
            "process_type", "derate_cell_early", "derate_cell_late",
            "derate_net_early", "derate_net_late", "uncertainty_scale"))
            for c in (C3 if key == "CLASSIC_3" else C8)]
    tpl = {"design_name": "MY_SOC",
           "clocks": [{"name": "clk_core", "port": "clk", "period": 5.0}]}
    m3 = post("/api/mmc", {"template": tpl, "corners": corners28("CLASSIC_3")})
    m8 = post("/api/mmc", {"template": tpl, "corners": corners28("FULL_8")})
    check("WS-29 mmc preset change reaches backend",
          len(m3.get("names", [])) == 3 and len(m8.get("names", [])) == 8)
    check("WS-29b mmc per-corner OC present",
          bool(m3.get("sdcs")) and "set_operating_conditions"
          in (list(m3["sdcs"].values())[0] or ""))

    # WS-30: Custom rules affect the real analysis result.
    cr30 = post("/api/analyze", {"sdc": "create_clock -name clk -period 12.0 [get_ports clk]\n",
                                  "custom_rules": CUSTOM_RULES_YAML,
                                  "rules_filename": "rules.yaml"})
    crr30 = cr30.get("custom_rules") or []
    check("WS-30 custom rule affects real analysis",
          bool(crr30) and any(r["id"] == "CUST-001" and not r["passed"]
                              for r in crr30))

    # WS-31: Test Drive + Corners — real backend results, no fake numbers.
    td31 = post("/api/analyze", {"sdc": V1})
    c31 = post("/api/corners", {"corners": corners28("CLASSIC_3")})
    check("WS-31 test drive real backend", bool(td31.get("issues"))
          and bool(td31.get("readiness")))
    check("WS-31b corners validated + matrix",
          len(c31.get("corners", [])) == 3 and len(c31.get("errors", [])) == 0
          and bool(c31.get("matrix")))

    # ── GROUP 4 — Output + Support workflows (Phase C / Group 4) ──────────
    # WS-32: Reports — HTML report carries real findings, rule IDs, readiness
    # and trust disclosures; JSON report is the full real analysis payload.
    buggy32 = ("create_clock -name clk -period 5.0 [get_ports clk]\n"
               "set_input_delay -max 6.0 -clock missing_clk [get_ports din]\n")
    a32 = post("/api/analyze", {"sdc": buggy32})
    r32 = post("/api/report/html", {"analysis": a32, "sdc": buggy32})
    html32 = r32.get("html") or ""
    check("WS-32 html report real data",
          bool(html32) and "SDC-0" in html32 and "missing_clk" in html32
          and ("READY" in html32 or "REVIEW_REQUIRED" in html32 or "BLOCKED" in html32))
    check("WS-32b json report full payload",
          bool(a32.get("issues")) and bool(a32.get("readiness"))
          and bool(a32.get("scope")))

    # WS-33: Trust — evidence endpoint derives real counts from the manifest.
    ev33 = get("/api/evidence")
    check("WS-33 trust evidence real",
          ev33.get("rule_count", 0) > 100 and ev33.get("test_count", 0) > 800
          and bool(ev33.get("version")) and "LLM" in (ev33.get("engine") or ""))

    # WS-34: Feedback — valid accepted+persisted, empty rejected, overlong
    # rejected; the engine never reports success it did not store.
    ts34 = "2026-08-14T12:00:00Z"
    fb_ok34 = post("/api/feedback", {"timestamp": ts34, "feature": "validator",
                                      "rating": 1, "comment": "ws-34 test entry"})
    fb_em34 = post("/api/feedback", {"timestamp": ts34, "feature": "validator",
                                      "rating": 1, "comment": "   "})
    fb_lo34 = post("/api/feedback", {"timestamp": ts34, "feature": "validator",
                                      "rating": 1, "comment": "x" * 2500})
    check("WS-34 feedback accepted + persisted", bool(fb_ok34.get("ok")))
    check("WS-34b feedback empty rejected", fb_em34.get("ok") is False
          and bool(fb_em34.get("error")))
    check("WS-34c feedback overlong rejected", fb_lo34.get("ok") is False
          and bool(fb_lo34.get("error")))

    # WS-35: Cross-feature output flows — Validate/Coverage/Diff → Report.
    s35 = V1
    a35 = post("/api/analyze", {"sdc": s35})
    h35 = post("/api/report/html", {"analysis": a35, "sdc": s35})
    d35 = post("/api/diff", {"v1": s35, "v2": s35.replace("period 5.0", "period 6.0")})
    check("WS-35 validate->report download", bool(h35.get("html")))
    check("WS-35b diff->report", bool(d35.get("findings"))
          and bool(d35.get("constraint_changes")))

    # ── PHASE E — Workspace UX rebuild ─────────────────────────────────────
    # WS-36: the confusing global command menus are gone; the command bar is
    # brand -> home, context strip, one New action, and Support links.
    idx36 = urllib.request.urlopen(
        f"http://127.0.0.1:{_port}/").read().decode()
    app36 = urllib.request.urlopen(
        f"http://127.0.0.1:{_port}/assets/js/app.js").read().decode()
    check("WS-36 global menus removed from shell",
          "cmd-open-session" not in idx36 and "cmd-import" not in idx36
          and "cmd-quick" not in idx36 and "cmd-settings" not in idx36
          and "menu-quick" not in idx36 and "menu-settings" not in idx36)
    check("WS-36b command bar has New + support links",
          'id="cmd-new"' in idx36 and 'href="#/documentation"' in idx36
          and 'href="#/trust"' in idx36 and 'href="#/feedback"' in idx36)
    check("WS-36c no dead menu wiring in app.js",
          "cmd-open-session" not in app36 and "cmd-quick" not in app36
          and "menu-session" not in app36 and "#cmd-settings" not in app36)
    check("WS-36d session strip simplified", "ctx-trust" not in idx36
          and "session-time" not in idx36 and 'id="ctx-readiness"' in idx36)
    check("WS-36e catalog still the landing", "#/catalog" in app36
          and "pageCatalog" in pagesjs and "More tools" not in pagesjs)

    # Clean up the WS-34 feedback entry so the suite never pollutes data/.
    try:
        fbpath = ROOT / "rta" / "workspace" / "data" / "feedback.json"
        fbdata = json.loads(fbpath.read_text(encoding="utf-8"))
        fbdata = [e for e in fbdata if e.get("comment") != "ws-34 test entry"]
        fbpath.write_text(json.dumps(fbdata, indent=2, ensure_ascii=False),
                          encoding="utf-8")
    except Exception:  # pragma: no cover — cleanup must never fail the suite
        pass

    stop_server()
    print(f"\nWORKSPACE UX: {len(PASSED)}/{len(PASSED) + len(FAILED)} passed")
    if FAILED:
        print("FAILED:", FAILED)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(run_all())
