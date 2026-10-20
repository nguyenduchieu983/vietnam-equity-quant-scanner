#!/usr/bin/env bash
# M0 integration runner. Native dependencies and migrated demo DB must already exist.
source "$(dirname "$0")/common.sh"
load_env
cd "$ROOT"
export PYTHONPATH="$ROOT/apps/quant-worker"
py="${QUANT_TEST_PYTHON:-$(python_bin)}"
node_bin="${QUANT_TEST_NODE:-node}"
mkdir -p .runtime
"$py" -m quant migrate
"$py" -m quant seed-demo
"$py" -m quant worker >.runtime/test-worker.log 2>&1 &
worker_pid=$!
"$node_bin" apps/api/dist/main.js >.runtime/test-api.log 2>&1 &
api_pid=$!
cleanup() { kill "$worker_pid" "$api_pid" 2>/dev/null || true; }
trap cleanup EXIT
ready=0
for attempt in {1..30}; do
  if curl -fsS http://127.0.0.1:3000/api/v1/health/ready >/dev/null; then ready=1; break; fi
  sleep 1
done
[[ "$ready" == 1 ]] || { echo "API readiness failed; inspect .runtime/test-api.log"; exit 1; }
QUANT_INTEGRATION=1 "$py" -m unittest discover -s apps/quant-worker/tests -v
"$node_bin" tests/e2e/m0-smoke.mjs
