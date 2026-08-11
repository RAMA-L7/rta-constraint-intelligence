#!/usr/bin/env bash
# Phase 1 — start workspace API + website static server for browser verification.
cd "$(dirname "$0")/../../.." || exit 1
export PYTHONIOENCODING=utf-8

# Kill any stale servers on our ports
for port in 8512 8513; do
  for pid in $(netstat -ano 2>/dev/null | grep ":$port" | grep LISTENING | awk '{print $5}' | sort -u); do
    taskkill //F //PID "$pid" >/dev/null 2>&1
  done
done
sleep 1

# Workspace API
python rta/api/api_server.py 8512 > /tmp/rta_api.log 2>&1 &
echo $! > /tmp/rta_api.pid

# Website static server
(cd rta/website && python -m http.server 8513 --bind 127.0.0.1 > /tmp/rta_site.log 2>&1 & echo $! > /tmp/rta_site.pid)

sleep 3

echo "=== workspace API ==="
curl -s -m 5 http://127.0.0.1:8512/api/health ; echo
curl -s -m 5 -o /dev/null -w "SPA index: HTTP %{http_code}\n" http://127.0.0.1:8512/
curl -s -m 5 -o /dev/null -w "app.js: HTTP %{http_code}\n" http://127.0.0.1:8512/assets/js/app.js

echo "=== website ==="
curl -s -m 5 -o /dev/null -w "index.html: HTTP %{http_code}\n" http://127.0.0.1:8513/index.html
curl -s -m 5 -o /dev/null -w "site.css: HTTP %{http_code}\n" http://127.0.0.1:8513/assets/css/site.css

echo "=== api errors (if any) ==="
grep -i "error\|traceback" /tmp/rta_api.log | head -5 || echo "(none)"
echo "READY ports: 8512 (workspace) 8513 (website)"
