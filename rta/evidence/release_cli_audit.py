"""Phase 14 — CLI contract, error journey, encoding, state isolation, HTML safety.

Runs against the *repository* code (fine for contract checks; the wheel path is
covered by _p14_cleanroom.py). Returns nonzero on any failure.
"""
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)

PASSED = []
FAILED = []


def check(name, cond, detail=""):
    (PASSED if cond else FAILED).append(name)
    print(("  PASS " if cond else "  FAIL ") + name + (("  | " + str(detail)[:200]) if detail else ""))


def run(*args, cwd=None, env_extra=None):
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    if env_extra:
        env.update(env_extra)
    return subprocess.run([sys.executable, "-m", "cli", *args],
                          capture_output=True, text=True, cwd=cwd or ROOT, env=env)


GOOD = ("set sdc_version 2.2\n"
        "create_clock -name clk_core -period 10.0 [get_ports clk_core]\n"
        "set_input_delay -max 2.0 -min 0.5 -clock clk_core [get_ports din]\n"
        "set_output_delay -max 3.0 -min 1.0 -clock clk_core [get_ports dout]\n")


def main():
    tmp = tempfile.mkdtemp(prefix="p14_cli_")
    work = os.path.join(tmp, "work")
    os.makedirs(work)

    good = os.path.join(work, "good.sdc")
    with open(good, "w", encoding="utf-8") as f:
        f.write(GOOD)

    # ── 1. Exit-code contract ────────────────────────────────────────────────
    # 0 = clean success
    r = run("check", good)
    check("exit-0-clean", r.returncode == 0, f"exit={r.returncode}")

    # 1 = analysis failure (errors present, no --gate)
    bad = os.path.join(work, "bad.sdc")
    with open(bad, "w", encoding="utf-8") as f:
        f.write("create_clock -name clk_core -period 0.0 [get_ports clk_core]\n")
    r = run("check", bad)
    check("exit-1-errors", r.returncode == 1, f"exit={r.returncode}")

    # 2 = invalid invocation: missing file
    r = run("check", os.path.join(work, "nope.sdc"))
    check("exit-2-missing-file", r.returncode == 2, f"exit={r.returncode}")

    # 2 = invalid invocation: gate requires baseline
    r = run("check", good, "--gate", "NO_READINESS_REGRESSION")
    check("exit-2-gate-no-baseline", r.returncode == 2, f"exit={r.returncode}")

    # 2 = CUSTOM gate requires policy file
    r = run("check", good, "--gate", "CUSTOM")
    check("exit-2-custom-no-policy", r.returncode == 2, f"exit={r.returncode}")

    # 2 = invalid CUSTOM policy file content
    pol_bad = os.path.join(work, "bad_pol.yml")
    with open(pol_bad, "w", encoding="utf-8") as f:
        f.write("policy: CUSTOM\nfail_on:\n  not_a_real_field: true\n")
    r = run("check", good, "--gate", "CUSTOM", "--gate-policy", pol_bad)
    check("exit-2-invalid-policy", r.returncode == 2, f"exit={r.returncode}")

    # 3 = engine failure is never masked as success (SDC-140 path is in-process;
    # simulate via a policy file that is not a policy at all)
    pol_garbage = os.path.join(work, "garbage.json")
    with open(pol_garbage, "w", encoding="utf-8") as f:
        f.write("{ this is not json")
    r = run("check", good, "--gate", "CUSTOM", "--gate-policy", pol_garbage)
    check("exit-2-malformed-policy", r.returncode == 2, f"exit={r.returncode}")

    # ── 2. JSON purity: stdout must be parseable, no banner/progress mixed in ─
    r = run("check", good, "--json")
    try:
        data = json.loads(r.stdout)
        ok = r.returncode == 0 and isinstance(data, dict)
    except json.JSONDecodeError as e:
        ok = False
        data = str(e)
    check("json-stdout-pure", ok, data if not isinstance(data, dict) else "OK")

    # JSON to file (--output): Phase 13 fixed clobbering — verify content round-trips
    out_json = os.path.join(work, "out.json")
    r = run("check", good, "--json", "--output", out_json)
    if os.path.exists(out_json) and os.path.getsize(out_json) > 0:
        with open(out_json, encoding="utf-8") as f:
            data = json.load(f)
        check("json-output-file", r.returncode == 0 and data.get("version"), "OK")
    else:
        check("json-output-file", False, f"empty/missing: {os.path.getsize(out_json) if os.path.exists(out_json) else 'missing'}")

    # ── 3. Error journey: understandable stderr/stdout on bad inputs ─────────
    # invalid SDC (unparseable binary-ish) must not traceback
    weird = os.path.join(work, "weird.sdc")
    with open(weird, "w", encoding="utf-8") as f:
        f.write("\x00\x01\x02broken\xff\xfe\n")
    r = run("check", weird)
    tb = "Traceback" in (r.stdout + r.stderr)
    check("error-no-traceback-sdc", not tb and r.returncode in (0, 1),
          f"exit={r.returncode} tb={tb}")

    # invalid netlist path
    r = run("check", good, "--netlist", os.path.join(work, "no.v"))
    check("error-missing-netlist", r.returncode in (1, 2),
          f"exit={r.returncode} {r.stderr[-100:]}")

    # malformed netlist content
    bad_v = os.path.join(work, "bad.v")
    with open(bad_v, "w", encoding="utf-8") as f:
        f.write("module top ( input a ; ; ; garbage === \n")
    r = run("check", good, "--netlist", bad_v)
    tb = "Traceback" in (r.stdout + r.stderr)
    check("error-malformed-netlist", not tb and r.returncode in (0, 1, 2),
          f"exit={r.returncode} tb={tb}")

    # ── 4. State isolation: A B A stable results ─────────────────────────────
    def run_sdc(text):
        p = os.path.join(work, "iso.sdc")
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
        r = run("check", p, "--json")
        d = json.loads(r.stdout)
        return json.dumps(d["errors"] + d["warnings"], sort_keys=True)

    a = run_sdc(GOOD)
    run_sdc(GOOD + "set_input_delay -max 12.0 -clock ghost_clk [get_ports din2]\n")
    a2 = run_sdc(GOOD)
    check("state-isolation-a-b-a", a == a2, "OK" if a == a2 else f"{a} != {a2}")

    # ── 5. Encoding: BOM, CRLF, no-final-newline, non-ASCII comments ─────────
    enc = os.path.join(work, "enc.sdc")
    with open(enc, "wb") as f:
        f.write(b"\xef\xbb\xbf" + GOOD.replace("\n", "\r\n").encode("utf-8") + b"# \xc3\xbcber clock comment")
    r = run("check", enc)
    check("encoding-bom-crlf-unicode", r.returncode == 0,
          f"exit={r.returncode} {r.stderr[-150:]}")

    # ── 6. HTML report safety: object/comment content escapes as data ────────
    evil = os.path.join(work, "evil.sdc")
    with open(evil, "w", encoding="utf-8") as f:
        # SDC-046 embeds the referenced (script-carrying) clock name in its
        # message — the strongest reachable injection path into the report.
        f.write("set sdc_version 2.2\n"
                "create_clock -name clk_good -period 10.0 [get_ports clk_core]\n"
                "set_input_delay -max 2.0 -clock <script>alert(1)</script> [get_ports din]\n"
                "# <img src=x onerror=alert(2)> \"quoted\" & ampersand\n")
    rpt = os.path.join(work, "evil.html")
    r = run("report", "check", evil, "--output", rpt)
    if os.path.exists(rpt):
        html = open(rpt, encoding="utf-8").read()
        raw_script = "<script>alert(1)</script>" in html
        escaped = "&lt;script&gt;" in html
        check("html-escaped", r.returncode in (0, 1) and escaped and not raw_script,
              f"escaped={escaped} raw_script={raw_script}")
    else:
        check("html-escaped", False, "report not written")

    # ── 7. Version consistency: CLI, JSON, snapshot agree ────────────────────
    r = run("--version")
    cli_ver = (r.stdout + r.stderr).strip()
    # CLI prints "Ṛta v1.3.0"; JSON/snapshot store bare "1.3.0".
    cli_ver_bare = cli_ver.split("v")[-1].strip()
    r = run("check", good, "--json")
    json_ver = json.loads(r.stdout).get("version")
    base_json = os.path.join(work, "base.json")
    r = run("check", good, "--save-baseline", base_json)
    snap_ver = ""
    if os.path.exists(base_json):
        snap_ver = json.load(open(base_json, encoding="utf-8")).get("tool_version", "")
    check("version-consistency", cli_ver_bare == json_ver and json_ver == snap_ver,
          f"cli={cli_ver_bare} json={json_ver} snap={snap_ver}")

    print()
    print(f"CLI AUDIT: {len(PASSED)} passed, {len(FAILED)} failed")
    for f in FAILED:
        print("  FAILED:", f)
    return 0 if not FAILED else 1


if __name__ == "__main__":
    sys.exit(main())
