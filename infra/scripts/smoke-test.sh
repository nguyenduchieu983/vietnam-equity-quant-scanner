#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
load_env
[[ "$DATA_MODE" == demo ]] || { echo "Smoke fixtures require DATA_MODE=demo" >&2; exit 1; }
export PYTHONPATH="$ROOT/apps/quant-worker"
export QUANT_INTEGRATION=1
"$(python_bin)" -m unittest discover -s "$ROOT/apps/quant-worker/tests" -v
node "$ROOT/tests/e2e/m0-smoke.mjs"
