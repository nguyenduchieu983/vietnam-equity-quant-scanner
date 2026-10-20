#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
load_env
umask 077
destination="${BACKUP_DIR:-/var/backups/quant-vn}"
[[ -d "$destination" ]] || { echo "Create backup directory with restricted permissions" >&2; exit 1; }
target="$destination/quant-$(date -u +%Y%m%dT%H%M%SZ).dump"
# libpq accepts connection URI through PGDATABASE; avoid credential-bearing process arguments.
export PGDATABASE="$DATABASE_URL"
pg_dump --format=custom --file="$target.partial"
mv -- "$target.partial" "$target"
find "$destination" -maxdepth 1 -type f -name 'quant-*.dump' -mtime +14 -delete
echo "Backup written: $target"
