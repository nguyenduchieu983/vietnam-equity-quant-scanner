#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
export ROOT
load_env() {
  local env_file="${QUANT_ENV_FILE:-$ROOT/.env}"
  [[ -f "$env_file" ]] || { echo "Missing environment file: $env_file" >&2; exit 1; }
  # Only load an operator-controlled shell-compatible env file.
  set -a
  source "$env_file"
  set +a
  : "${DATABASE_URL:?}" "${REDIS_URL:?}" "${DATA_MODE:?}"
}
python_bin() { printf '%s' "$ROOT/apps/quant-worker/.venv/bin/python"; }
require_native() {
  [[ "$(uname -s)" == Linux ]] || { echo "Linux required" >&2; exit 1; }
  for bin in node npm python3.12 psql redis-cli; do command -v "$bin" >/dev/null || { echo "Missing $bin" >&2; exit 1; }; done
  [[ "$(node -p 'process.versions.node.split(`.`)[0]')" == 22 ]] || { echo "Node 22 required" >&2; exit 1; }
}
