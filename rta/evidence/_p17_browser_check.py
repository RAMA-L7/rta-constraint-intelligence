"""Phase 17 interactive browser check — drives real Chrome via CDP.

Verifies the rebuilt workspace SPA (shell, navigation, real analysis flow,
inspector, clocks, coverage, interactions, readiness, diff, reports, CI,
tools) and the marketing site (hero, silicon-graph animation, shared nav,
CTA) in an actual browser: console errors, horizontal overflow, animation
advance, reduced-motion behavior, and screenshots.

This is a verification harness, not part of the shipped product.
"""
import base64
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

import websocket

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
DBG_PORT = 9333
WS_URL = "http://127.0.0.1:8501/"
SITE_URL = "http://127.0.0.1:8100/index.html"
SHOT_DIR = os.path.join(tempfile.gettempdir(), "p17_shots")
os.makedirs(SHOT_DIR, exist_ok=True)

SDC = (
    "set sdc_version 2.2\n"
    "create_clock -name clk_core -period 5.0 [get_ports clk]\n"
    "create_generated_clock -name clk_div2 -divide_by 2 -source [get_ports clk] [get_pins u0/clkout]\n"
    "create_clock -name clk_uart -period 8.0 [get_ports uart_clk]\n"
    "set_clock_uncertainty -setup 0.15 [get_clocks clk_core]\n"
    "set_input_delay -max 6.0 -clock clk_core [get_ports data_in]\n"
    "set_output_delay -max 1.0 -clock clk_core [get_ports data_out]\n"
    "set_false_path -from [get_clocks clk_core] -to [get_clocks clk_uart]\n"
)
NET = (
    "module top(input clk, input uart_clk, input [7:0] data_in, output [7:0] data_out);\n"
    "  reg [7:0] q;\n"
    "  always @(posedge clk) q <= data_in;\n"
    "  assign data_out = q;\n"
    "endmodule\n"
)

PASS, FAIL = [], []


def report(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(f"  {'PASS' if ok else 'FAIL'} {name}{(' — ' + detail) if detail else ''}")


class CDP:
    def __init__(self, ws_url):
        self.ws = websocket.create_connection(ws_url, timeout=30)
        self.ws.settimeout(0.05)
        self._id = 0
        self.events = []
        self.console_errors = []

    def send(self, method, params=None):
        self._id += 1
        mid = self._id
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        self.ws.settimeout(5.0)
        deadline = time.time() + 90
        while True:
            try:
                msg = json.loads(self.ws.recv())
            except (socket.timeout, websocket.WebSocketTimeoutException):
                if time.time() > deadline:
                    raise RuntimeError(f"{method} timed out")
                continue
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})
            self._collect(msg)

    def _collect(self, msg):
        self.events.append(msg)
        m = msg.get("method")
        if m == "Runtime.exceptionThrown":
            d = msg.get("params", {}).get("exceptionDetails", {})
            self.console_errors.append("exception: " + (d.get("text") or ""))
        elif m == "Log.entryAdded":
            e = msg["params"]["entry"]
            if e.get("level") == "error":
                self.console_errors.append("log: " + (e.get("text") or ""))
        elif m == "Runtime.consoleAPICalled" and msg.get("params", {}).get("type") == "error":
            args = msg["params"].get("args", [])
            self.console_errors.append("console: " + " ".join(a.get("value", "") for a in args))

    def pump(self, seconds):
        self.ws.settimeout(0.5)
        end = time.time() + seconds
        while time.time() < end:
            try:
                self._collect(json.loads(self.ws.recv()))
            except (socket.timeout, websocket.WebSocketTimeoutException, Exception):
                continue

    def eval(self, expr, await_promise=False):
        r = self.send("Runtime.evaluate", {
            "expression": expr, "returnByValue": True, "awaitPromise": await_promise,
        })
        if "exceptionDetails" in r:
            return None
        res = r.get("result", {})
        if res.get("type") == "undefined":
            return None
        return res.get("value")

    def wait_for(self, expr, timeout=20):
        end = time.time() + timeout
        while time.time() < end:
            v = self.eval(expr)
            if v:
                return v
            time.sleep(0.25)
        return None

    def screenshot(self, name):
        r = self.send("Page.captureScreenshot", {"format": "png"})
        with open(os.path.join(SHOT_DIR, name), "wb") as f:
            f.write(base64.b64decode(r["data"]))
        return os.path.join(SHOT_DIR, name)


def new_target(url):
    """Create a page target and return its webSocketDebuggerUrl."""
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{DBG_PORT}/json/new?{urllib.parse.quote(url, safe='')}",
            method="PUT", data=b"")
        with urllib.request.urlopen(req, timeout=5) as r:
            info = json.loads(r.read())
    except Exception:
        with urllib.request.urlopen(f"http://127.0.0.1:{DBG_PORT}/json/new?{url}", timeout=5) as r:
            info = json.loads(r.read())
    return info["webSocketDebuggerUrl"]


def main():
    # ── launch chrome headless ─────────────────────────────────────────────
    prof = os.path.join(tempfile.gettempdir(), "p17_cdp_profile")
    subprocess.Popen([
        CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
        f"--remote-debugging-port={DBG_PORT}",
        "--remote-allow-origins=*",
        f"--user-data-dir={prof}", "about:blank",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(30):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{DBG_PORT}/json/version", timeout=2)
            break
        except Exception:
            time.sleep(0.5)
    else:
        print("FAIL chrome did not start")
        sys.exit(1)

    # ═══════════════════════ WORKSPACE ═══════════════════════
    print("== WORKSPACE ==")
    c = CDP(new_target(WS_URL))
    c.send("Page.enable"); c.send("Runtime.enable"); c.send("Log.enable")
    c.send("Emulation.setDeviceMetricsOverride",
           {"width": 1440, "height": 900, "deviceScaleFactor": 1, "mobile": False})
    c.send("Page.navigate", {"url": WS_URL})
    c.pump(2)

    # shell
    ngroups = c.wait_for("document.querySelectorAll('#nav-groups .nav-group').length", 10) or 0
    report("WS shell renders", int(ngroups) == 6, f"groups={ngroups}")
    report("topbar context", bool(c.eval("!!document.getElementById('topbar-context')")))
    report("bg canvas present", bool(c.eval("!!document.getElementById('bg')")))

    # animation advances (two samples of canvas differ)
    t0 = c.eval("document.getElementById('bg').toDataURL()")
    time.sleep(0.8)
    t1 = c.eval("document.getElementById('bg').toDataURL()")
    report("bg animation advances", t0 != t1)

    # overview empty state (no analysis yet)
    report("overview renders", bool(c.eval("!!document.getElementById('main')")))
    c.screenshot("01_overview.png")

    # ── Validator: real analysis ────────────────────────────────────────────
    c.eval("location.hash = '#/validator'")
    c.pump(0.6)
    report("validator page renders", bool(c.eval("!!document.getElementById('val-sdc')")))
    setv = ("const el=document.getElementById('val-sdc');"
            "const set=Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set;"
            "set.call(el, arguments[0]); el.dispatchEvent(new Event('input',{bubbles:true})); true")
    c.eval(f"({setv})({json.dumps(SDC)})")
    c.eval(f"({setv.replace('val-sdc', 'val-netlist')})({json.dumps(NET)})")
    c.screenshot("02_validator_input.png")
    c.eval("document.getElementById('val-analyze').click()")

    rows = c.wait_for("document.querySelectorAll('.finding-row').length > 0", 25)
    nrows = c.eval("document.querySelectorAll('.finding-row').length")
    report("analyze renders findings", bool(rows), f"rows={nrows}")
    errs = c.eval("Array.from(document.querySelectorAll('.finding-row')).filter(r=>r.textContent.includes('error')).length")
    report("error severity present (SDC-008 input delay)", errs and errs >= 1, f"error-rows={errs}")
    sdc008 = c.eval("document.body.textContent.includes('SDC-008')")
    report("SDC-008 rule shown", bool(sdc008))
    c.screenshot("03_validator_findings.png")

    # summary rail
    report("summary rail renders", bool(c.eval("document.body.textContent.includes('Errors')")))

    # finding inspector
    c.eval("(document.querySelector('.finding-row')||document.querySelector('[data-idx]')||document.querySelector('tr')).click()")
    insp = c.wait_for(
        "(()=>{const i=document.getElementById('inspector');"
        "return i && getComputedStyle(i).display!=='none' && "
        "document.getElementById('inspector-title').textContent.trim().length>0;})()", 8)
    report("finding inspector opens", bool(insp))
    c.screenshot("04_inspector.png")

    # filter (severity chip) — presentation only, counts unchanged
    c.eval("location.hash = '#/validator'")
    c.pump(0.5)
    n_all = c.eval("document.querySelectorAll('.finding-row').length")
    c.eval("Array.from(document.querySelectorAll('[data-seg]')).find(b=>b.dataset.seg==='error').click()")
    c.pump(0.5)
    n_err = c.eval("document.querySelectorAll('.finding-row').length")
    report("severity filter works", n_all > 0 and 0 < n_err <= n_all, f"{n_err}/{n_all}")
    c.eval("document.getElementById('f-clear').click()")
    c.pump(0.5)
    report("clear filters restores", c.eval("document.querySelectorAll('.finding-row').length") == n_all)

    # ── Clocks ──────────────────────────────────────────────────────────────
    c.eval("location.hash = '#/clocks'")
    c.pump(0.8)
    ck = c.wait_for("document.body.textContent.includes('clk_core')", 8)
    report("clock inventory renders", bool(ck))
    c.screenshot("05_clocks.png")
    report("hierarchy/matrix present", bool(
        c.eval("document.querySelectorAll('.clock-node, svg, .rel-matrix, table').length > 0")))

    # ── Coverage ────────────────────────────────────────────────────────────
    c.eval("location.hash = '#/coverage'")
    c.pump(0.8)
    report("coverage renders", bool(c.eval("document.body.textContent.includes('Coverage')")))
    c.screenshot("06_coverage.png")

    # ── Interactions ────────────────────────────────────────────────────────
    c.eval("location.hash = '#/interactions'")
    c.pump(0.8)
    report("interactions renders", bool(c.eval("document.body.textContent.includes('Interaction')")))
    c.screenshot("07_interactions.png")

    # ── Readiness ───────────────────────────────────────────────────────────
    c.eval("location.hash = '#/readiness'")
    c.pump(0.8)
    dims = c.eval("document.querySelectorAll('.rail-dim, [class*=dim], [class*=rail]').length")
    report("readiness dimension rail renders", dims and dims >= 3, f"dims={dims}")
    c.screenshot("08_readiness.png")

    # ── Diff ────────────────────────────────────────────────────────────────
    c.eval("location.hash = '#/diff'")
    c.pump(0.8)
    report("diff page renders", bool(c.eval("!!document.getElementById('diff-run')")))
    dset = ("const el=document.getElementById(arguments[0]);"
            "const set=Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set;"
            "set.call(el, arguments[1]); el.dispatchEvent(new Event('input',{bubbles:true})); true")
    c.eval(f"({dset})('diff-v1', {json.dumps(SDC)})")
    c.eval(f"({dset})('diff-v2', {json.dumps(SDC.replace('-period 5.0', '-period 6.0'))})")
    c.eval("document.getElementById('diff-run').click()")
    delta = c.wait_for("document.body.textContent.includes('CHANGED') || document.querySelectorAll('.diff-row, [class*=diff]').length > 3", 20)
    report("diff comparison renders", bool(delta))
    c.screenshot("09_diff.png")

    # ── CI + Reports ────────────────────────────────────────────────────────
    c.eval("location.hash = '#/ci'")
    c.pump(0.8)
    report("CI page renders", bool(c.eval("!!document.getElementById('ci-policy')")))
    c.screenshot("10_ci.png")
    c.eval("location.hash = '#/reports'")
    c.pump(0.8)
    report("reports page renders", bool(c.eval("!!document.getElementById('rep-json')")))
    c.screenshot("11_reports.png")

    # ── Tools: reachable + functional ───────────────────────────────────────
    tools = {
        "generator": "gen-run", "linter": "lint-run", "converter": "conv-run",
        "corners": "corner-preset", "mmc": "mmc-run", "rules": None,
        "test_drive": "td-run", "feedback": "fb-submit",
    }
    for name, hook in tools.items():
        c.eval(f"location.hash = '#/{name}'")
        c.pump(0.6)
        ok = bool(c.eval(f"!!document.getElementById('{hook}')")) if hook else bool(
            c.eval("document.getElementById('main').textContent.trim().length > 50"))
        report(f"tool reachable: {name}", ok)

    # generator actually runs
    c.eval("location.hash = '#/generator'")
    c.pump(0.5)
    c.eval("document.getElementById('gen-design').value = 'chip'")
    c.eval("document.getElementById('gen-clock').value = 'clk=10.0'")
    c.eval("document.getElementById('gen-run').click()")
    out = c.wait_for("(document.getElementById('gen-out')||document.getElementById('gen-out-area')).value.length > 50", 15)
    report("generator produces SDC", bool(out))

    # linter actually runs
    c.eval("location.hash = '#/linter'")
    c.pump(0.5)
    lint_sdc = "create_clock -name clk -period 5.0 [get_ports clk]\nset_false_path -from [get_clocks clk] -to [get_clocks uart]\n"
    c.eval("(" + dset + ")(" + json.dumps('lint-in') + ", " + json.dumps(lint_sdc) + ")")
    c.eval("document.getElementById('lint-run').click()")
    lout = c.wait_for("document.getElementById('lint-out').textContent.trim().length > 0", 15)
    report("linter produces results", bool(lout))

    # overflow at 1440
    ov = c.eval("document.documentElement.scrollWidth > window.innerWidth + 2")
    report("no horizontal overflow @1440", not ov)

    # responsive @1024
    c.send("Emulation.setDeviceMetricsOverride",
           {"width": 1024, "height": 768, "deviceScaleFactor": 1, "mobile": False})
    c.pump(0.5)
    ov1024 = c.eval("document.documentElement.scrollWidth > window.innerWidth + 2")
    report("no horizontal overflow @1024", not ov1024)
    c.send("Emulation.setDeviceMetricsOverride",
           {"width": 1440, "height": 900, "deviceScaleFactor": 1, "mobile": False})

    # reduced motion
    c.send("Emulation.setEmulatedMedia", {
        "features": [{"name": "prefers-reduced-motion", "value": "reduce"}]})
    c.pump(0.6)
    rm = c.eval("matchMedia('(prefers-reduced-motion: reduce)').matches")
    b0 = c.eval("document.getElementById('bg').toDataURL()")
    time.sleep(0.8)
    b1 = c.eval("document.getElementById('bg').toDataURL()")
    report("reduced-motion honored", bool(rm) and b0 == b1)
    c.send("Emulation.setEmulatedMedia", {"features": []})
    c.pump(0.3)

    report("workspace console clean", not c.console_errors, "; ".join(c.console_errors[:4]))
    c.ws.close()

    # ═══════════════════════ SITE ═══════════════════════
    print("== SITE ==")
    s = CDP(new_target(SITE_URL))
    s.send("Page.enable"); s.send("Runtime.enable"); s.send("Log.enable")
    s.send("Emulation.setDeviceMetricsOverride",
           {"width": 1440, "height": 900, "deviceScaleFactor": 1, "mobile": False})
    s.send("Page.navigate", {"url": SITE_URL})
    s.pump(3)

    report("hero headline", bool(s.eval("document.querySelector('.display-hero')?.textContent.includes('Constraint quality')")))
    report("terminal animation element", bool(s.eval("!!document.getElementById('hero-terminal-body')")))
    report("silicon canvas present", bool(s.eval("!!document.getElementById('silicon-canvas')")))
    t0 = s.eval("document.getElementById('silicon-canvas').innerHTML.length")
    time.sleep(1.2)
    t1 = s.eval("document.querySelector('#silicon-canvas .pulse') ? document.getElementById('silicon-canvas').innerHTML.length : document.getElementById('silicon-canvas').innerHTML.length")
    # pulse position changes over time
    p0 = s.eval("document.querySelector('#silicon-canvas .pulse')?.getAttribute('cx')")
    time.sleep(0.7)
    p1 = s.eval("document.querySelector('#silicon-canvas .pulse')?.getAttribute('cx')")
    report("site pulse moves", bool(p0) and p0 != p1, f"cx {p0} → {p1}")
    report("site pulse-halo/flow present", bool(s.eval("document.querySelectorAll('#silicon-canvas .pulse-halo, #silicon-canvas .edge-path.flow').length > 0")))
    s.screenshot("12_site_home.png")

    cta = s.eval("document.querySelector('.nav-cta')?.getAttribute('href')")
    report("nav CTA → workspace", cta == "http://localhost:8501/", str(cta))

    # capabilities subpage with shared header
    s.eval("location.href = 'http://127.0.0.1:8100/capabilities/clocks.html'")
    s.pump(2)
    report("capability subpage header", bool(s.wait_for("document.querySelector('.nav-links a') !== null", 8)))
    s.screenshot("13_capability_subpage.png")

    # benchmarks + trust pages render scorecards
    s.eval("location.href = 'http://127.0.0.1:8100/benchmarks.html'")
    s.pump(2)
    report("benchmarks scorecards", bool(s.eval("document.body.textContent.includes('710/710')")))
    s.screenshot("14_site_benchmarks.png")
    s.eval("location.href = 'http://127.0.0.1:8100/trust.html'")
    s.pump(2)
    report("trust page renders", bool(s.eval("document.body.textContent.includes('Trust')")))
    s.screenshot("15_site_trust.png")

    # site console + overflow
    ovs = s.eval("document.documentElement.scrollWidth > window.innerWidth + 2")
    report("site no overflow", not ovs)
    report("site console clean", not s.console_errors, "; ".join(s.console_errors[:4]))
    s.ws.close()

    # ═══════════════════════ summary ═══════════════════════
    print(f"\nP17 BROWSER CHECK: {len(PASS)}/{len(PASS)+len(FAIL)} passed")
    if FAIL:
        print("FAILED:", FAIL)
        sys.exit(1)
    print("Screenshots:", sorted(os.listdir(SHOT_DIR)))


if __name__ == "__main__":
    main()
