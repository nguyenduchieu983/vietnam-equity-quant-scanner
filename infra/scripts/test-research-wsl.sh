#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
load_env
cd "$ROOT"
py="${QUANT_LOCAL_PYTHON:-$ROOT/.runtime/linux-venv/bin/python}"
export PYTHONPATH="$ROOT/apps/quant-worker" QUANT_INTEGRATION=1
"$py" -m quant migrate
"$py" -m unittest discover -s apps/quant-worker/tests -v
"$(dirname "$py")/ruff" check apps/quant-worker/quant apps/quant-worker/tests
"$(dirname "$py")/mypy" apps/quant-worker/quant
