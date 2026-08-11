"""Regenerate or verify RELEASE_EVIDENCE.json — Ṛta's evidence manifest.

Usage::

    python rta/evidence/build_evidence.py          # recompute and write
    python rta/evidence/build_evidence.py --check  # verify; exit 1 on drift

The manifest is the single source of truth for the public evidence numbers
(test count, rule count, golden runners, benchmark suites, version, release
status, phase count). README, the website, CONTRIBUTING and the evidence tests
all consume it. ``--check`` is wired into CI so any drift fails the pipeline.
"""

import argparse
import datetime as _dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import evidence  # noqa: E402


def collect_test_stats() -> tuple[int, dict[str, int]]:
    """Run one pytest collection and return (total, per-file counts)."""
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "rta/tests/", "--collect-only", "-q"],
        cwd=ROOT, capture_output=True, text=True, env=env,
    )
    out = proc.stdout + proc.stderr
    match = re.search(r"(\d+)\s+test(?:s)? collected(?:,\s*(\d+)\s+errors?)?", out)
    if not match:
        raise SystemExit(f"could not parse pytest collection output:\n{out[-2000:]}")
    total = int(match.group(1))
    errors = int(match.group(2) or 0)
    if proc.returncode != 0 or errors:
        raise SystemExit(
            f"pytest collection reported {errors} error(s) — fix before recording "
            f"evidence:\n{out[-2000:]}")
    per_file: dict[str, int] = {}
    for line in out.splitlines():
        m = re.match(r"rta/tests/(test_[^:]+)\.py::", line.strip())
        if m:
            per_file[f"{m.group(1)}.py"] = per_file.get(f"{m.group(1)}.py", 0) + 1
    return total, dict(sorted(per_file.items()))


def build_record() -> dict:
    """Recompute the full evidence record from live truth."""
    total, per_file = collect_test_stats()
    return {
        "product": evidence.PRODUCT,
        "tagline": evidence.TAGLINE,
        "version": evidence.version(),
        "release_status": evidence.RELEASE_STATUS,
        "license": evidence.LICENSE,
        "python_requirement": ">=3.10",
        "test_count": total,
        "test_files": len(per_file),
        "test_files_detail": per_file,
        "rule_count": evidence.rule_count(),
        "golden_runners": evidence.golden_runner_files(),
        "golden_runner_count": len(evidence.golden_runner_files()),
        "benchmark_suites": len(evidence.benchmark_suite_files()),
        "phase_count": evidence.phase_report_count(),
        "evidence_updated": _dt.date.today().isoformat(),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Ṛta evidence manifest tool")
    ap.add_argument("--check", action="store_true",
                    help="verify the manifest matches live truth; write nothing")
    args = ap.parse_args()

    if args.check:
        if not evidence.MANIFEST_PATH.is_file():
            raise SystemExit(
                "RELEASE_EVIDENCE.json missing — run without --check to generate it")
        live = build_record()
        recorded = evidence.load_manifest()
        mismatches = evidence.verify()
        if live["test_count"] != recorded.get("test_count"):
            mismatches.append(
                f"test_count: live={live['test_count']} manifest={recorded.get('test_count')}")
        if live["test_files_detail"] != recorded.get("test_files_detail"):
            mismatches.append(
                "test_files_detail differs — add/remove/rename a test and regenerate "
                "(python rta/evidence/build_evidence.py)")
        if mismatches:
            print("EVIDENCE DRIFT:")
            for msg in mismatches:
                print(" -", msg)
            return 1
        print(f"evidence OK: {live['test_count']} tests, {live['rule_count']} rules, "
              f"{live['benchmark_suites']} suites, v{live['version']}")
        return 0

    live = build_record()
    evidence.MANIFEST_PATH.write_text(
        json.dumps(live, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {evidence.MANIFEST_PATH.name}: {live['test_count']} tests, "
          f"{live['rule_count']} rules, {live['benchmark_suites']} suites, "
          f"v{live['version']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
