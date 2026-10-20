#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
curl --fail --silent --show-error --max-time 10 "${API_URL:-http://127.0.0.1:3000}/api/v1/health/live"
curl --fail --silent --show-error --max-time 10 "${API_URL:-http://127.0.0.1:3000}/api/v1/health/ready"
if [[ "${CHECK_SYSTEMD:-0}" == 1 ]]; then
  systemctl is-active --quiet postgresql redis-server quant-worker nginx pm2-quant
  systemctl is-enabled postgresql redis-server quant-worker nginx pm2-quant
fi
echo "Health checks passed."
