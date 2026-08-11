"""Capture JS exceptions with location from the workspace SPA via CDP."""
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request

import websocket

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 9340
URL = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:8501/"


def main():
    prof = os.path.join(tempfile.gettempdir(), f"p17_dbg_{PORT}")
    subprocess.Popen([
        CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
        f"--remote-debugging-port={PORT}", "--remote-allow-origins=*",
        f"--user-data-dir={prof}", "about:blank",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(30):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version", timeout=2)
            break
        except Exception:
            time.sleep(0.5)

    req = urllib.request.Request(
        f"http://127.0.0.1:{PORT}/json/new?{URL}", method="PUT", data=b"")
    info = json.loads(urllib.request.urlopen(req, timeout=5).read())
    ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=30)
    ws.settimeout(0.5)
    mid = 0
    events = []

    def send(m, p=None):
        nonlocal mid
        mid += 1
        ws.send(json.dumps({"id": mid, "method": m, "params": p or {}}))
        while True:
            try:
                msg = json.loads(ws.recv())
            except Exception:
                continue
            if msg.get("id") == mid:
                return msg.get("result", {})
            events.append(msg)

    def drain(sec):
        end = time.time() + sec
        while time.time() < end:
            try:
                events.append(json.loads(ws.recv()))
            except Exception:
                continue

    def ev(expr):
        r = send("Runtime.evaluate", {"expression": expr, "returnByValue": True})
        if "exceptionDetails" in r:
            return "EXC: " + (r["exceptionDetails"].get("exception", {}).get("description", "?")[:400])
        return r.get("result", {}).get("value")

    send("Page.enable")
    send("Runtime.enable")
    send("Log.enable")
    send("Page.navigate", {"url": URL})
    drain(8)

    print("nav groups:", ev("document.querySelectorAll('#nav-groups .nav-group').length"))
    print("main len:", ev("document.getElementById('main')?.innerHTML.length"))
    for m in events:
        if m.get("method") == "Runtime.exceptionThrown":
            d = m["params"]["exceptionDetails"]
            print("URL:", d.get("url"))
            print("LINE:", d.get("lineNumber"), "COL:", d.get("columnNumber"))
            print("TEXT:", d.get("text"))
            print("EXC:", d.get("exception", {}).get("description", "?")[:1200])
            print("====")


if __name__ == "__main__":
    main()
