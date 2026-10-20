#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
[[ $# == 1 && -f "$1" ]] || { echo "Usage: RESTORE_DATABASE_URL=... restore-postgres.sh backup.dump" >&2; exit 1; }
: "${RESTORE_DATABASE_URL:?Set a separate empty restore database URL}"
export PGDATABASE="$RESTORE_DATABASE_URL"
count="$(psql -Atc "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")"
[[ "$count" == 0 ]] || { echo "Refusing restore into a nonempty database" >&2; exit 1; }
pg_restore --exit-on-error --single-transaction --no-owner --no-privileges --dbname="$PGDATABASE" "$1"
echo "Restore complete; validate counts and provenance before use."
