#!/usr/bin/env bash
# Target: dedicated Ubuntu 24.04 host. Does not alter existing databases or bind addresses.
set -Eeuo pipefail
[[ "$EUID" == 0 ]] || { echo "Run with sudo" >&2; exit 1; }
source /etc/os-release
[[ "$ID" == ubuntu && "$VERSION_ID" == 24.04 ]] || { echo "Supported target: Ubuntu 24.04 (Python 3.12/PostgreSQL 16)" >&2; exit 1; }
apt-get update
apt-get install -y ca-certificates curl gnupg python3.12 python3.12-venv postgresql-16 postgresql-client-16 redis-server nginx
if ! command -v node >/dev/null || [[ "$(node -p 'process.versions.node.split(`.`)[0]')" != 22 ]]; then
  echo "Install Node 22 from the reviewed NodeSource signed repository first; see OPERATIONS.md. Existing Node is not replaced automatically." >&2
  exit 1
fi
npm install --global pm2@6.0.13
id quant >/dev/null 2>&1 || useradd --system --create-home --home-dir /var/lib/quant --shell /bin/bash quant
install -d -o quant -g quant -m 0755 /opt/quant-vn
install -d -o quant -g quant -m 0700 /var/backups/quant-vn
systemctl enable --now postgresql redis-server nginx
echo "Native dependencies ready. Provision dedicated database and /etc/quant-vn.env per runbook."
