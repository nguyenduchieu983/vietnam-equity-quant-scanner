#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
[[ "$EUID" == 0 ]] || { echo "Run with sudo" >&2; exit 1; }
[[ "$ROOT" == /opt/quant-vn ]] || { echo "Deploy the reviewed checkout to /opt/quant-vn first" >&2; exit 1; }
export QUANT_ENV_FILE=/etc/quant-vn.env
load_env
require_native
[[ "$(stat -c '%a' /etc/quant-vn.env)" == 640 ]] || { echo "Require chmod 640 /etc/quant-vn.env" >&2; exit 1; }
[[ "$(stat -c '%U:%G' /etc/quant-vn.env)" == root:quant ]] || { echo "Require chown root:quant /etc/quant-vn.env" >&2; exit 1; }
runuser -u quant -- bash -ec 'cd /opt/quant-vn; npm ci; npm run build; python3.12 -m venv apps/quant-worker/.venv; apps/quant-worker/.venv/bin/python -m pip install --require-hashes -r apps/quant-worker/requirements.lock'
runuser -u quant -- bash -ec 'set -a; source /etc/quant-vn.env; set +a; cd /opt/quant-vn/apps/quant-worker; .venv/bin/python -m quant migrate'
install -m 0644 "$ROOT/infra/systemd/quant-worker.service" /etc/systemd/system/
install -m 0644 "$ROOT/infra/systemd/quant-backup.service" /etc/systemd/system/
install -m 0644 "$ROOT/infra/systemd/quant-backup.timer" /etc/systemd/system/
# Refuse to silently replace an operator-customized TLS configuration.
if [[ -f /etc/nginx/sites-available/quant-vn ]] && ! cmp -s "$ROOT/infra/nginx/quant-vn.conf" /etc/nginx/sites-available/quant-vn; then
  echo "Keeping existing Nginx site; review differences manually."
else
  install -m 0644 "$ROOT/infra/nginx/quant-vn.conf" /etc/nginx/sites-available/quant-vn
fi
ln -sfn /etc/nginx/sites-available/quant-vn /etc/nginx/sites-enabled/quant-vn
nginx -t
systemctl daemon-reload
systemctl enable --now postgresql redis-server nginx quant-worker quant-backup.timer
systemctl restart quant-worker
runuser -u quant -- bash -ec 'set -a; source /etc/quant-vn.env; set +a; export PM2_HOME=/var/lib/quant/.pm2; cd /opt/quant-vn; pm2 startOrReload ecosystem.config.cjs --env production --update-env; pm2 save'
# Explicit reviewed startup command; never evaluate PM2-generated shell output.
env PM2_HOME=/var/lib/quant/.pm2 PATH=/usr/bin:/bin pm2 startup systemd -u quant --hp /var/lib/quant
systemctl enable pm2-quant
systemctl reload nginx
for attempt in {1..30}; do
  if bash "$ROOT/infra/scripts/healthcheck.sh"; then exit 0; fi
  sleep 2
done
echo "Deployment started but readiness failed; inspect service logs" >&2
exit 1
