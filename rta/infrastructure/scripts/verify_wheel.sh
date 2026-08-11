#!/usr/bin/env bash
# Phase 1 — clean wheel build + clean-room install verification.
cd "$(dirname "$0")/../../.." || exit 1
export PYTHONIOENCODING=utf-8

echo "=== [1] clean stale artifacts ==="
rm -rf build dist sdc_tools.egg-info
echo "cleaned"

echo "=== [2] build wheel ==="
python -m pip install --quiet build 2>/dev/null
python -m build --wheel > /tmp/build_wheel.log 2>&1
WHEEL=$(ls dist/*.whl 2>/dev/null | head -1)
if [ -z "$WHEEL" ]; then echo "BUILD FAILED"; tail -20 /tmp/build_wheel.log; exit 1; fi
echo "built: $WHEEL"

echo "=== [3] wheel contents: shims + static assets ==="
python - <<'PYEOF'
import zipfile, glob
w = glob.glob('dist/*.whl')[0]
names = zipfile.ZipFile(w).namelist()
root_shims = [n for n in names if n.count('/') == 0 and n.endswith('.py')]
print("root-level .py modules in wheel:", len(root_shims))
print("  sample:", sorted(root_shims)[:8])
for probe in ['rta/workspace/webui/index.html', 'rta/workspace/webui/assets/js/app.js',
              'rta/website/index.html', 'rta/website/assets/css/site.css',
              'rta/api/api_server.py', 'rta/cli/cli.py', 'rta/evidence/manifest/evidence.py']:
    print(("OK  " if probe in names else "MISS"), probe)
missing = [p for p in ['rta/workspace/webui/index.html','rta/website/index.html'] if p not in names]
print("MISSING STATIC:", missing if missing else "(none)")
PYEOF

echo "=== [4] clean-room install in temp venv ==="
TMPVENV=$(mktemp -d)
python -m venv "$TMPVENV/venv"
"$TMPVENV/venv/Scripts/python" -m pip install --quiet "$WHEEL" 2>&1 | tail -2
echo "--- CLI from clean install ---"
"$TMPVENV/venv/Scripts/python" -m cli --version 2>&1 | head -1
"$TMPVENV/venv/Scripts/python" -m cli check "$(pwd)/rta/examples/samples/example.sdc" 2>&1 | head -2
echo "--- API boot from clean install ---"
"$TMPVENV/venv/Scripts/python" -m api_server 8514 > /tmp/wheel_api.log 2>&1 &
APIPID=$!
sleep 3
curl -s -m 5 http://127.0.0.1:8514/api/health ; echo
curl -s -m 5 -o /dev/null -w "SPA: HTTP %{http_code}\n" http://127.0.0.1:8514/
curl -s -m 5 -o /dev/null -w "app.js: HTTP %{http_code}\n" http://127.0.0.1:8514/assets/js/app.js
kill $APIPID 2>/dev/null
rm -rf "$TMPVENV"
echo "=== DONE ==="
