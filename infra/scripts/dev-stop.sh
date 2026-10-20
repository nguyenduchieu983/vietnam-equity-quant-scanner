#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
for service in api worker web; do
  pidfile="$ROOT/.runtime/$service.pid"
  [[ -f "$pidfile" ]] || continue
  pid="$(cat "$pidfile")"
  [[ "$pid" =~ ^[0-9]+$ ]] || { echo "Invalid PID file: $pidfile" >&2; exit 1; }
  # Refuse to signal a recycled PID belonging to a different checkout.
  if [[ -d "/proc/$pid" ]]; then
    cwd="$(readlink -f "/proc/$pid/cwd")"
    [[ "$cwd" == "$ROOT" || "$cwd" == "$ROOT/"* ]] || { echo "PID $pid belongs to another workspace; not stopped" >&2; continue; }
    kill -TERM "$pid"
  fi
  rm -- "$pidfile"
done
