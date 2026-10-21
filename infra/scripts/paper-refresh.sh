#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
load_env
cd "$ROOT"
cutoff="${1:-$(TZ=Asia/Ho_Chi_Minh date -d yesterday +%F)}"
[[ "$cutoff" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || exit 1
node infra/scripts/fetch-vndirect-research.mjs "$cutoff"
export PYTHONPATH="$ROOT/apps/quant-worker"
"${QUANT_LOCAL_PYTHON:-$ROOT/apps/quant-worker/.venv/bin/python}" -m quant.paper "$ROOT/.runtime/vndirect-s1-${cutoff//-/}"
