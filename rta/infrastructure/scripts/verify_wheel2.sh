#!/usr/bin/env bash
# Phase 1 — post-review wheel rebuild + feedback endpoint verification.
cd "$(dirname "$0")/../../.." || exit 1
export PYTHONIOENCODING=utf-8

echo "=== [1] clean + rebuild ==="
rm -rf build dist sdc_tools.egg-info
python -m build --wheel > /tmp/build_wheel2.log 2>&1
WHEEL=$(ls dist/*.whl 2>/dev/null | head -1)
[ -z "$WHEEL" ] && { echo "BUILD FAILED"; tail -10 /tmp/build_wheel2.log; exit 1; }
echo "built: $WHEEL"

echo "=== [2] clean venv install ==="
TMPVENV=$(mktemp -d)
python -m venv "$TMPVENV/venv"
"$TMPVENV/venv/Scripts/python" -m pip install --quiet "$WHEEL" 2>&1 | tail -1

echo "=== [3] feedback data layer in clean install (no streamlit) ==="
"$TMPVENV/venv/Scripts/python" -c "from ui.feedback import FeedbackEntry, save_feedback, load_feedback; print('FEEDBACK-DATA-OK')" 2>&1 | tail -2

echo "=== [4] API boot + feedback endpoint in clean install ==="
"$TMPVENV/venv/Scripts/python" -m api_server 8515 > /tmp/wheel_api2.log 2>&1 &
APIPID=$!
sleep 3
curl -s -m 5 http://127.0.0.1:8515/api/health ; echo
curl -s -m 5 -X POST http://127.0.0.1:8515/api/feedback -H "Content-Type: application/json" -d '{"feature":"checker","rating":1,"comment":"clean wheel feedback test","sdc_file":"test.sdc","results_summary":"0 errors"}' ; echo
curl -s -m 5 http://127.0.0.1:8515/api/theme | head -c 80 ; echo
kill $APIPID 2>/dev/null

echo "=== [5] cleanup temp venv ==="
rm -rf "$TMPVENV"
echo "=== DONE ==="
