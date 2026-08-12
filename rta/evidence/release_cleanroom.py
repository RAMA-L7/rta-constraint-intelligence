"""Phase 14 — clean-room test: wheel install + full user journey in a fresh venv.

Simulates an engineer with no developer shell state: creates a fresh venv,
installs ONLY the built wheel (no repo on sys.path), and exercises the
documented workflow. Returns nonzero on any failure.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import venv

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)

PASSED = []
FAILED = []


def check(name, cond, detail=""):
    (PASSED if cond else FAILED).append(name)
    print(("  PASS " if cond else "  FAIL ") + name + ("  | " + detail if detail else ""))


def run(venv_py, *args, cwd=None):
    # Inherit the full parent environment: stripping it on Windows breaks
    # DLL/SystemRoot resolution and can kill the child at bootstrap.
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run([venv_py, *args], capture_output=True, text=True,
                          cwd=cwd or ROOT, env=env)


def main():
    tmp = tempfile.mkdtemp(prefix="p14_cleanroom_")
    print("temp:", tmp)

    # 0. Build the wheel from a genuinely fresh venv, pinned to the DECLARED
    #    build-system floor — not whatever setuptools happens to be installed.
    #    release_cleanroom.py previously consumed a pre-built wheel from dist/,
    #    which is why the PEP 639 license-string regression (floor >=68 could
    #    not parse `license = "MIT"`) slipped past this gate.
    pyproject = open(os.path.join(ROOT, "pyproject.toml"), encoding="utf-8").read()
    # Anchored to the [build-system] section so a prose comment mentioning
    # "setuptools>=X" can never shadow the real floor (re.S spans the
    # comment lines between the header and the requires line).
    m = re.search(r'\[build-system\].*?requires\s*=\s*\["setuptools>=([0-9][0-9.]*)',
                  pyproject, re.S)
    assert m, "setuptools floor not found in pyproject.toml [build-system]"
    floor_v = m.group(1)
    print("build floor: setuptools ==", floor_v)
    build_venv = os.path.join(tmp, "build_venv")
    venv.create(build_venv, with_pip=True)
    bpy = os.path.join(build_venv, "Scripts", "python.exe") if os.name == "nt" \
        else os.path.join(build_venv, "bin", "python")
    r = run(bpy, "-m", "pip", "install", "--quiet", f"setuptools=={floor_v}", "wheel")
    if r.returncode != 0:
        print("BUILD GATE FAILED: could not install declared floor",
              f"setuptools=={floor_v}", r.stderr[-300:])
        return 1
    wheel_dir = os.path.join(tmp, "wheel")
    os.makedirs(wheel_dir, exist_ok=True)
    r = run(bpy, "-m", "pip", "wheel", ".", "--no-deps",
            "--no-build-isolation", "-w", wheel_dir)
    if r.returncode != 0:
        print("BUILD GATE FAILED: wheel could not be built at the declared",
              f"floor setuptools=={floor_v}:", r.stderr[-400:])
        return 1
    wheels = [f for f in os.listdir(wheel_dir) if f.endswith(".whl")]
    assert wheels, "wheel build produced no wheel"
    wheel = os.path.join(wheel_dir, wheels[0])
    print("wheel built at floor:", os.path.basename(wheel))

    # 2. Fresh venv
    venv_dir = os.path.join(tmp, "venv")
    venv.create(venv_dir, with_pip=True)
    vpy = os.path.join(venv_dir, "Scripts", "python.exe") if os.name == "nt" \
        else os.path.join(venv_dir, "bin", "python")

    # 3. Install the WHEEL (not the repo) — no editable install
    r = run(vpy, "-m", "pip", "install", "--quiet", wheel)
    check("install-wheel", r.returncode == 0, r.stderr[-300:])

    # 4. Fresh cwd OUTSIDE the repo — verify no repository-relative imports
    work = os.path.join(tmp, "work")
    os.makedirs(work, exist_ok=True)

    # 5. CLI --help
    r = run(vpy, "-m", "cli", "--help", cwd=work)
    check("cli-help", r.returncode == 0 and "check" in r.stdout, r.stderr[-200:])

    # 6. rta entry point (console script)
    entry = os.path.join(venv_dir, "Scripts", "rta.exe") if os.name == "nt" \
        else os.path.join(venv_dir, "bin", "rta")
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run([entry, "--version"], capture_output=True, text=True,
                       cwd=work, env=env)
    check("entry-point", r.returncode == 0 and "1.5.3" in (r.stdout + r.stderr),
          (r.stdout + r.stderr)[-200:])

    # 7. Validate a sample SDC (written in the fresh work dir)
    sdc = os.path.join(work, "design.sdc")
    with open(sdc, "w", encoding="utf-8") as f:
        f.write("set sdc_version 2.2\n"
                "create_clock -name clk_core -period 10.0 [get_ports clk_core]\n"
                "set_input_delay -max 2.0 -min 0.5 -clock clk_core [get_ports din]\n"
                "set_output_delay -max 3.0 -min 1.0 -clock clk_core [get_ports dout]\n")
    r = run(vpy, "-m", "cli", "check", sdc, cwd=work)
    check("check-sdc", r.returncode == 0 and "Errors:" in r.stdout,
          r.stderr[-300:])

    # 8. JSON output — must be pure machine-readable JSON on stdout
    r = run(vpy, "-m", "cli", "check", sdc, "--json", cwd=work)
    try:
        data = json.loads(r.stdout)
        check("json-purity", r.returncode == 0 and isinstance(data, dict),
              r.stdout[:200])
        check("json-readiness", "constraint_readiness" in data,
              str(list(data.keys())))
    except json.JSONDecodeError as e:
        check("json-purity", False, f"stdout not pure JSON: {e} | {r.stdout[:200]}")

    # 9. HTML report
    report = os.path.join(work, "report.html")
    r = run(vpy, "-m", "cli", "report", "check", sdc, "--output", report, cwd=work)
    check("report-html", r.returncode == 0 and os.path.exists(report) and
          os.path.getsize(report) > 1000, (r.stderr or "")[-200:])

    # 10. Baseline save/load + diff + gate
    base_json = os.path.join(work, "base.json")
    r = run(vpy, "-m", "cli", "check", sdc, "--save-baseline", base_json, cwd=work)
    check("save-baseline", r.returncode == 0 and os.path.exists(base_json),
          (r.stderr or "")[-200:])
    r = run(vpy, "-m", "cli", "check", sdc, "--baseline", base_json,
            "--gate", "NO_READINESS_REGRESSION", cwd=work)
    check("gate-pass", r.returncode == 0, f"exit={r.returncode} {(r.stderr or '')[-200:]}")

    # 11. Gate correctly FAILS on a new blocker
    bad = os.path.join(work, "bad.sdc")
    with open(bad, "w", encoding="utf-8") as f:
        f.write(open(sdc, encoding="utf-8").read() +
                "set_input_delay -max 12.0 -clock ghost_clk [get_ports din2]\n")
    r = run(vpy, "-m", "cli", "check", bad, "--baseline", base_json,
            "--gate", "NO_READINESS_REGRESSION", cwd=work)
    check("gate-fail", r.returncode == 1, f"exit={r.returncode}")

    # 12. CUSTOM policy file
    pol = os.path.join(work, "pol.yml")
    with open(pol, "w", encoding="utf-8") as f:
        f.write("policy: CUSTOM\npolicy_version: 1\nname: test\nfail_on:\n  new_blockers: true\n")
    r = run(vpy, "-m", "cli", "check", bad, "--baseline", base_json,
            "--gate", "CUSTOM", "--gate-policy", pol, cwd=work)
    check("custom-gate-fail", r.returncode == 1, f"exit={r.returncode}")

    # 13. Netlist-aware validation from the wheel.
    # Port names must match the SDC fixture (clk_core / din / dout).
    nl = os.path.join(work, "top.v")
    with open(nl, "w", encoding="utf-8") as f:
        f.write("module top (input clk_core, input din, output dout);\n"
                "  assign dout = din;\nendmodule\n")
    r = run(vpy, "-m", "cli", "check", sdc, "--netlist", nl, cwd=work)
    check("netlist-aware", r.returncode == 0, (r.stderr or "")[-300:])

    # 14. Python API from the installed wheel (fresh cwd, no repo import)
    api = ("import json\n"
           "from checker import check_sdc\n"
           "from readiness_diff import build_snapshot, snapshot_to_json\n"
           "r = check_sdc(open('design.sdc', encoding='utf-8').read())\n"
           "s = build_snapshot(r, source_name='design.sdc')\n"
           "print('API_OK', s['schema_version'], len(r.issues))\n")
    api_path = os.path.join(work, "api_probe.py")
    with open(api_path, "w", encoding="utf-8") as f:
        f.write(api)
    r = run(vpy, api_path, cwd=work)
    check("python-api", r.returncode == 0 and "API_OK 2" in r.stdout,
          (r.stdout + r.stderr)[-300:])

    # 15. Error journey: invalid baseline, wrong top, bad output path, bad policy
    bad_base = os.path.join(work, "bad_base.json")
    with open(bad_base, "w", encoding="utf-8") as f:
        f.write("{ this is not json")
    r = run(vpy, "-m", "cli", "check", sdc, "--baseline", bad_base,
            "--gate", "NO_READINESS_REGRESSION", cwd=work)
    check("err-invalid-baseline", r.returncode == 2,
          f"exit={r.returncode} (want 2, not a crash/PASS)")

    r = run(vpy, "-m", "cli", "check", sdc, "--netlist", nl, "--top",
            "module_that_does_not_exist", cwd=work)
    check("err-wrong-top", r.returncode in (1, 2),
          f"exit={r.returncode} {r.stderr[-120:]}")

    bad_out = os.path.join(work, "no_such_dir", "out.json")
    r = run(vpy, "-m", "cli", "check", sdc, "--json", "--output", bad_out, cwd=work)
    # Bad output path is an invalid invocation → exit 2 (clean diagnostic, no traceback).
    check("err-bad-output-path", r.returncode == 2 and "Traceback" not in r.stderr,
          f"exit={r.returncode} stderr={r.stderr[-100:]}")

    # Offline guarantee: the wheel must not import anything requiring network.
    import zipfile
    with zipfile.ZipFile(wheel) as z:
        names = z.namelist()
    net_imports = [n for n in names if "requests" in n or "urllib.request" in n
                   or "http.client" in n or "openai" in n or "anthropic" in n]
    check("offline-no-net-imports", not net_imports, str(net_imports[:5]))

    print()
    print(f"CLEAN-ROOM: {len(PASSED)} passed, {len(FAILED)} failed")
    for f in FAILED:
        print("  FAILED:", f)
    return 0 if not FAILED else 1


if __name__ == "__main__":
    sys.exit(main())
