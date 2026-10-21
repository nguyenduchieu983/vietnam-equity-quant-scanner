#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
load_env
cd "$ROOT"
export PYTHONPATH="$ROOT/apps/quant-worker"
py="${QUANT_LOCAL_PYTHON:-$ROOT/.runtime/linux-venv/bin/python}"
"$py" -m quant migrate
"$py" -m quant.paper "$1"
"$py" -m quant.real_import
