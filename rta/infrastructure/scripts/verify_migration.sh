#!/usr/bin/env bash
# Phase 1 migration — full verification battery (runs from repo root).
cd "$(dirname "$0")/../../.." || exit 1
ROOT="$(pwd)"
export PYTHONIOENCODING=utf-8

echo "=== [1/7] rerun 6 previously-failing evidence checks ==="
PASS=0; FAIL=0; FAILED=""
for f in run_production_hardening.py test_ph13_adversarial.py test_ph13_ci_workflow.py \
         test_ph13_perf.py test_ph13_security.py test_ui_state_isolation.py; do
  python "rta/evidence/$f" > "/tmp/refix_$f.log" 2>&1 && PASS=$((PASS+1)) || { FAIL=$((FAIL+1)); FAILED="$FAILED $f"; }
done
echo "refix: pass=$PASS fail=$FAIL"
for f in $FAILED; do echo "--- $f ---"; tail -4 "/tmp/refix_$f.log"; done

echo ""
echo "=== [2/7] full pytest ==="
python -m pytest rta/tests/ -q 2>&1 | tail -2

echo ""
echo "=== [3/7] all benchmark runners ==="
PASS=0; FAIL=0; FAILED=""
for f in run_golden.py run_golden_semantic.py run_reference_designs.py run_netlist_aware.py \
         run_design_coverage.py run_constraint_interactions.py run_readiness.py run_readiness_diff.py \
         run_production_hardening.py reference_coverage_matrix.py generate_support_matrix.py verify_findings.py; do
  python "rta/evidence/$f" > "/tmp/run_$f.log" 2>&1 && PASS=$((PASS+1)) || { FAIL=$((FAIL+1)); FAILED="$FAILED $f"; }
done
echo "runners: pass=$PASS fail=$FAIL"
for f in $FAILED; do echo "--- $f ---"; tail -5 "/tmp/run_$f.log"; done

echo ""
echo "=== [4/7] all benchmark suites (28) ==="
PASS=0; FAIL=0; FAILED=""
for f in rta/evidence/test_*.py; do
  python "$f" > "/tmp/suite_$(basename "$f").log" 2>&1 && PASS=$((PASS+1)) || { FAIL=$((FAIL+1)); FAILED="$FAILED $(basename "$f")"; }
done
echo "suites: pass=$PASS fail=$FAIL"
for f in $FAILED; do echo "--- $f ---"; tail -5 "/tmp/suite_$f.log"; done

echo ""
echo "=== [5/7] evidence check + release smoke ==="
python rta/evidence/build_evidence.py --check 2>&1 | tail -1
python -m pytest rta/evidence/test_release_smoke.py -q 2>&1 | tail -1

echo ""
echo "=== [6/7] CLI contract ==="
python -m cli --version 2>/dev/null | head -1
python cli.py check rta/examples/samples/example.sdc 2>&1 | head -3

echo ""
echo "=== [7/7] API boot + website static ==="
python rta/api/api_server.py 8512 > /tmp/api.log 2>&1 &
APIPID=$!
sleep 3
curl -s -m 5 http://127.0.0.1:8512/api/health ; echo
curl -s -m 5 http://127.0.0.1:8512/api/rules | head -c 60 ; echo
kill $APIPID 2>/dev/null
ls rta/website/assets/css/ | head -3
echo "=== DONE ==="
