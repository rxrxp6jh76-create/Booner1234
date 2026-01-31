#!/usr/bin/env bash
set -euo pipefail

# health_watchdog.sh
# Polls http://127.0.0.1:8000/api/health every few seconds
# On status change (up->down or down->up) it records diagnostic snapshots:
# - last 1000 lines of backend logs
# - ps aux | grep server.py
# - lsof -p <pid> (if available)
# - timestamped archive under resources/backend/logs/diagnostics

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_LOG_DIR="$BASE_DIR/electron-app/resources/backend/logs"
DIAG_DIR="$BACKEND_LOG_DIR/diagnostics"
mkdir -p "$DIAG_DIR"

API_URL="http://127.0.0.1:8000/api/health"
INTERVAL=${INTERVAL:-5}
MAX_FAILURES_BEFORE_SNAPSHOT=1

last_status="unknown"

echo "Starting health watchdog for $API_URL (interval=${INTERVAL}s). Diagnostics at $DIAG_DIR"

while true; do
  timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
  if curl -sS -m 3 "$API_URL" >/dev/null 2>&1; then
    status="up"
  else
    status="down"
  fi

  if [ "$status" != "$last_status" ]; then
    echo "[$(date)]: Status changed: $last_status -> $status"
    snap="$DIAG_DIR/snapshot_${timestamp}_$status"
    mkdir -p "$snap"

    # copy last lines of logs
    if [ -f "$BACKEND_LOG_DIR/start-backend.out" ]; then
      tail -n 1000 "$BACKEND_LOG_DIR/start-backend.out" > "$snap/start-backend.out.tail" || true
    fi
    if [ -f "$BACKEND_LOG_DIR/backend.log" ]; then
      tail -n 1000 "$BACKEND_LOG_DIR/backend.log" > "$snap/backend.log.tail" || true
    fi

    # process list
    ps aux | egrep "server.py|uvicorn|python" > "$snap/ps.txt" || true

    # try to get pid
    pid="$(pgrep -f "server.py" || true)"
    if [ -n "$pid" ]; then
      echo "Found server.py pid: $pid" > "$snap/pid.txt"
      if command -v lsof >/dev/null 2>&1; then
        lsof -p "$pid" > "$snap/lsof.txt" || true
      fi
    fi

    # collect environment snapshot
    uname -a > "$snap/uname.txt" || true
    echo "DATE: $(date)" > "$snap/date.txt"

    # rotate previous 'last' link
    ln -sfn "$snap" "$DIAG_DIR/last_snapshot"
  fi

  last_status="$status"
  sleep "$INTERVAL"
done
