#!/usr/bin/env bash
# Phase 1 migration — packaging + final gates (runs from repo root).
cd "$(dirname "$0")/../../.." || exit 1
export PYTHONIOENCODING=utf-8

echo "=== [1/5] release packaging probe ==="
python rta/evidence/release_packaging_probe.py 2>&1 | tail -6

echo ""
echo "=== [2/5] release clean-room ==="
python rta/evidence/release_cleanroom.py 2>&1 | tail -6

echo ""
echo "=== [3/5] release CLI audit ==="
python rta/evidence/release_cli_audit.py 2>&1 | tail -4

echo ""
echo "=== [4/5] full pytest reconfirmation ==="
python -m pytest rta/tests/ -q 2>&1 | tail -2

echo ""
echo "=== [5/5] evidence check + smoke ==="
python rta/evidence/build_evidence.py --check 2>&1 | tail -1
python -m pytest rta/evidence/test_release_smoke.py -q 2>&1 | tail -1
echo "=== DONE ==="
