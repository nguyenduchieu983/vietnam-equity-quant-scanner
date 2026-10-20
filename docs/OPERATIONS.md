# Native Linux operations — M0 draft, deployment not certified

Supported clean-host target: Ubuntu 24.04, Node 22, Python 3.12, PostgreSQL 16+, Redis 7+. No orchestration images or isolated OS runtime are required. PostgreSQL/Redis must bind loopback; verify before exposing any service.

## Install Node 22

Use an existing supported installation or review the [NodeSource signed repository instructions](https://github.com/nodesource/distributions). Example explicit repository setup (review host changes first):

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -d -m 0755 /etc/apt/keyrings
curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key -o /tmp/nodesource.key
gpg --show-keys --fingerprint /tmp/nodesource.key
# Verify fingerprint against the vendor before importing.
sudo gpg --dearmor --yes -o /etc/apt/keyrings/nodesource.gpg /tmp/nodesource.key
printf '%s\n' 'deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_22.x nodistro main' | sudo tee /etc/apt/sources.list.d/nodesource.list
sudo apt-get update
sudo apt-get install -y nodejs
node --version
```

## Development

```bash
sudo bash infra/scripts/install-native.sh
node infra/scripts/init-demo-env.mjs
# Creates .env once, with random secrets. Never commit it.
sudo python3 infra/scripts/provision-demo-db.py
bash infra/scripts/dev-start.sh
bash infra/scripts/smoke-test.sh
bash infra/scripts/dev-stop.sh
```

The provisioning helper refuses existing quant_m0 objects. Read the locally generated `SMOKE_ADMIN_PASSWORD` from `.env` to sign in, never paste it into logs. The database stays after dev-stop; only workspace process PIDs are stopped.

## Production preparation

Copy the reviewed checkout to `/opt/quant-vn`, owned by `quant:quant`. Do not copy Windows node_modules or virtualenvs. Create dedicated production DB/role through `sudo -u postgres createuser --pwprompt quant` and `sudo -u postgres createdb --owner=quant quant_vn`. Use a separate database from DEMO.

Prepare `/etc/quant-vn.env` from `.env.example` with shell-compatible values and real random secrets. Use `root:quant`, mode `0640`. Set production NODE_ENV. Real-data mode deliberately cannot ingest until a provider is implemented and authorized. The PM2 saved environment contains secrets; restrict `/var/lib/quant/.pm2` to the quant user.

```bash
sudo chown root:quant /etc/quant-vn.env
sudo chmod 640 /etc/quant-vn.env
sudo bash /opt/quant-vn/infra/scripts/deploy.sh
sudo systemctl status postgresql redis-server quant-worker nginx pm2-quant
sudo -u quant env PM2_HOME=/var/lib/quant/.pm2 pm2 status
sudo -u quant env PM2_HOME=/var/lib/quant/.pm2 pm2 logs quant-api --lines 100
sudo journalctl -u quant-worker -n 100
sudo nginx -t
sudo systemctl reload nginx
CHECK_SYSTEMD=1 bash /opt/quant-vn/infra/scripts/healthcheck.sh
```

Deployment initially listens only on `127.0.0.1:8080` for Nginx and `127.0.0.1:3000` for API. To publish: obtain a DNS hostname, configure certificate lifecycle with Certbot/Nginx, redirect HTTP to HTTPS and allow only SSH/80/443 in the host firewall. Do not open DB/Redis ports. A real hostname/certificate was not supplied; public TLS has not been deployed or tested. `deploy.sh` preserves operator-modified Nginx config.

PM2 startup uses the explicit fixed command in deploy.sh; no generated privileged shell output is evaluated. Systemd enables worker and backup timer. PostgreSQL/Redis/Nginx and PM2 startup are enabled. **Enablement is not proof of recovery after reboot.**

## Backup / restore

```bash
sudo -u quant env QUANT_ENV_FILE=/etc/quant-vn.env bash /opt/quant-vn/infra/scripts/backup-postgres.sh
sudo systemctl list-timers quant-backup.timer
# Create a separate empty DB first; restore refuses a nonempty public schema.
RESTORE_DATABASE_URL='postgresql://user:password@127.0.0.1/restore_test' bash infra/scripts/restore-postgres.sh /path/to/backup.dump
```

Use a protected environment file instead of putting real credentials in shell history. Backups are custom pg_dump format; 14-day local retention, mode 0600. Off-host copies and encryption at rest need operator storage configuration. Restore testing is outstanding.

## Restart and reboot verification

```bash
sudo systemctl restart quant-worker
sudo -u quant env PM2_HOME=/var/lib/quant/.pm2 pm2 restart quant-api
cat /proc/sys/kernel/random/boot_id
# Reboot ONLY in an approved maintenance window.
sudo reboot
# After reconnect: save the new boot ID and these outputs.
cat /proc/sys/kernel/random/boot_id
systemctl is-active postgresql redis-server quant-worker nginx pm2-quant
CHECK_SYSTEMD=1 bash /opt/quant-vn/infra/scripts/healthcheck.sh
```

Verify an interrupted job resumes once after its two-minute lease, then inspect ingestion counts and audit. AC17 remains NOT RUN until this evidence exists. Do not reboot a user's workstation automatically.

Log rotation: journald handles worker logs; configure bounded journald retention. PM2 stdout/stderr require log rotation before production acceptance (not yet configured). Monitor disk usage, backup failures and provider freshness in M4.
