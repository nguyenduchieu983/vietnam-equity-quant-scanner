#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
load_env
require_native
cd "$ROOT"
mkdir -p .runtime
[[ ! -f .runtime/api.pid ]] || { echo "Already started; run dev-stop.sh first" >&2; exit 1; }
pg_isready -q || { echo "Native PostgreSQL unavailable" >&2; exit 1; }
redis-cli ping | grep -qx PONG
npm ci
python3.12 -m venv apps/quant-worker/.venv
"$(python_bin)" -m pip install --require-hashes -r apps/quant-worker/requirements-dev.lock
export PYTHONPATH="$ROOT/apps/quant-worker"
"$(python_bin)" -m quant migrate
if [[ "$DATA_MODE" == demo ]]; then "$(python_bin)" -m quant seed-demo; fi
npm run build
cleanup_on_error() { bash "$ROOT/infra/scripts/dev-stop.sh"; }
trap cleanup_on_error ERR
nohup node apps/api/dist/main.js >.runtime/api.log 2>&1 & echo "$!" >.runtime/api.pid
nohup "$(python_bin)" -m quant worker >.runtime/worker.log 2>&1 & echo "$!" >.runtime/worker.pid
nohup node node_modules/vite/bin/vite.js --config apps/web/vite.config.ts apps/web --host 127.0.0.1 >.runtime/web.log 2>&1 & echo "$!" >.runtime/web.pid
for attempt in {1..30}; do
  if curl -fsS http://127.0.0.1:3000/api/v1/health/ready >/dev/null; then
    echo "Native development services ready: http://127.0.0.1:5173"
    exit 0
  fi
  sleep 1
done
echo "Readiness failed; see .runtime/*.log" >&2
exit 1
