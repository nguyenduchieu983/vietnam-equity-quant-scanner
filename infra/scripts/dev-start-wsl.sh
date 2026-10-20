#!/usr/bin/env bash
# Backend half of the Windows-local launcher, using already prepared native WSL dependencies.
source "$(dirname "$0")/common.sh"
load_env
cd "$ROOT"
mkdir -p .runtime
export PYTHONPATH="$ROOT/apps/quant-worker"
node_bin="${QUANT_LOCAL_NODE:-$ROOT/.runtime/node-v22.19.0-linux-x64/bin/node}"
py="${QUANT_LOCAL_PYTHON:-$ROOT/.runtime/linux-venv/bin/python}"
[[ -x "$node_bin" && -x "$py" ]] || { echo "Local WSL runtimes missing; see docs/LOCAL_WINDOWS.md" >&2; exit 1; }
"$py" -m quant migrate
if [[ "$DATA_MODE" == demo ]]; then "$py" -m quant seed-demo; fi
start_one() {
  local name="$1"
  shift
  local pidfile="$ROOT/.runtime/$name.pid"
  if [[ -f "$pidfile" ]]; then
    local previous
    previous="$(cat "$pidfile")"
    if [[ "$previous" =~ ^[0-9]+$ ]] && kill -0 "$previous" 2>/dev/null; then
      [[ "$(readlink -f "/proc/$previous/cwd")" == "$ROOT" ]] || { echo "PID belongs to another project" >&2; exit 1; }
      return
    fi
  fi
  nohup "$@" >"$ROOT/.runtime/$name.log" 2>&1 </dev/null &
  echo "$!" >"$pidfile"
}
start_one worker "$py" -m quant worker
start_one api "$node_bin" apps/api/dist/main.js
for attempt in {1..40}; do
  if curl -fsS http://127.0.0.1:3000/api/v1/health/ready >/dev/null 2>&1; then
    echo "WSL API + worker ready"
    if [[ "${1:-}" == --hold ]]; then
      # Keep the Windows WSL client alive; this host closes user processes when its last client exits.
      while kill -0 "$(cat .runtime/api.pid)" 2>/dev/null; do sleep 5; done
    fi
    exit 0
  fi
  sleep 1
done
echo "Readiness failed; inspect .runtime/api.log and worker.log" >&2
exit 1
