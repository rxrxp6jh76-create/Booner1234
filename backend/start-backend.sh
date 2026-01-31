#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Activate packaged venv if available
if [ -f "venv/bin/activate" ]; then
  # shellcheck source=/dev/null
  source venv/bin/activate
  PYTHON="${VIRTUAL_ENV}/bin/python"
else
  PYTHON="$(command -v python3 || command -v python)"
fi

# Wrapper loop with exponential backoff, PID file and log rotation
PIDFILE="$SCRIPT_DIR/logs/backend.pid"
LOGFILE="$SCRIPT_DIR/logs/start-backend.out"

# Ensure file descriptor limit is sufficient and log it
ulimit -n 4096 2>/dev/null || true
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) ulimit -n=$(ulimit -n)" >> "$LOGFILE" || true

backoff=1
max_backoff=60

rotate_log() {
  if [ -f "$LOGFILE" ] && [ $(stat -f%z "$LOGFILE") -gt $((5 * 1024 * 1024)) ]; then
    mv "$LOGFILE" "$LOGFILE.$(date -u +%Y%m%dT%H%M%SZ).rot" || true
  fi
}

is_port_in_use() {
  # Prefer lsof (macOS), fallback to netstat
  if command -v lsof >/dev/null 2>&1; then
    lsof -iTCP:8000 -sTCP:LISTEN -Pn >/dev/null 2>&1 && return 0 || return 1
  else
    netstat -an | grep -E "LISTEN" | grep -q ":8000" && return 0 || return 1
  fi
}

# Forward TERM/INT to child and log
forward_term() {
  echo "$(date): Received termination signal, forwarding to child $child_pid" | tee -a "$LOGFILE"
  if [ -n "${child_pid:-}" ]; then
    kill -TERM "$child_pid" 2>/dev/null || true
    wait "$child_pid" 2>/dev/null || true
  fi
  exit 0
}
trap forward_term SIGTERM SIGINT

while true; do
    rotate_log

    if is_port_in_use; then
      echo "$(date): Port 8000 already in use; sleeping ${backoff}s" | tee -a "$LOGFILE"
      sleep "$backoff"
      backoff=$((backoff * 2))
      if [ "$backoff" -gt "$max_backoff" ]; then
        backoff=$max_backoff
      fi
      continue
    fi

    echo "$(date): Starting backend..." | tee -a "$LOGFILE"

    # Run server in foreground and capture its pid
    "$PYTHON" server.py >>"$LOGFILE" 2>&1 &
    child_pid=$!
    echo "$child_pid" > "$PIDFILE"

    # reset backoff on successful start
    backoff=1

    # wait for child to finish
    wait $child_pid || true

    echo "$(date): Backend process $child_pid stopped" | tee -a "$LOGFILE"

    # Exponential backoff before restart
    echo "$(date): Restarting in ${backoff}s..." | tee -a "$LOGFILE"
    sleep "$backoff"
    backoff=$((backoff * 2))
    if [ "$backoff" -gt "$max_backoff" ]; then
      backoff=$max_backoff
    fi

    # loop
done
