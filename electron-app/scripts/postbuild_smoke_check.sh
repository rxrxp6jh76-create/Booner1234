#!/usr/bin/env bash
set -euo pipefail

# postbuild_smoke_check.sh
# - Finds the built .app
# - Starts the packaged backend inside the .app bundle
# - Polls /api/health up to a timeout
# - Exits non-zero if the check fails

APP_DIR="$(pwd)/dist"
APP_PATH=""

# Find the first .app in dist (supports dist/mac and dist/mac-arm64)
while IFS= read -r -d '' app; do
  APP_PATH="$app"
  break
done < <(find "$APP_DIR" -maxdepth 3 -name "*.app" -print0 2>/dev/null)

if [ -z "$APP_PATH" ]; then
  echo "❌ No .app artifact found under $APP_DIR"
  exit 2
fi

echo "ℹ️ Found app: $APP_PATH"

# Determine backend directory inside the app (common electron layout)
# Try several plausible locations
CANDIDATES=(
  "$APP_PATH/Contents/Resources/app/resources/backend"
  "$APP_PATH/Contents/Resources/app/backend"
  "$APP_PATH/Contents/Resources/app.asar.unpacked/resources/backend"
  "$APP_PATH/Contents/Resources/app.asar.unpacked/backend"
)

BACKEND_DIR=""
for c in "${CANDIDATES[@]}"; do
  if [ -d "$c" ]; then
    BACKEND_DIR="$c"
    break
  fi
done

if [ -z "$BACKEND_DIR" ]; then
  echo "❌ Cannot find packaged backend directory in $APP_PATH"
  exit 3
fi

echo "ℹ️ Using backend dir: $BACKEND_DIR"

LOGFILE="/tmp/booner_pack_backend.log"
PIDFILE="/tmp/booner_pack_backend.pid"

# Start backend using its start script if present
if [ -x "$BACKEND_DIR/start-backend.sh" ]; then
  echo "ℹ️ Starting packaged backend via start-backend.sh"
  (cd "$BACKEND_DIR" && ./start-backend.sh > "$LOGFILE" 2>&1 &) || true
  # give it a moment to create pid via our script conventions
  sleep 1
  # try to capture the child python process if present
  ps aux | grep -E "server.py|uvicorn" | grep -v grep || true
else
  echo "❌ No start-backend.sh executable found in $BACKEND_DIR"
  exit 4
fi

# Poll /api/health
MAX_TRIES=15
SLEEP_SECS=2
SUCCESS=1
for i in $(seq 1 $MAX_TRIES); do
  echo "Checking /api/health (attempt $i/$MAX_TRIES)..."
  if curl -sS -m 3 http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
    echo "✅ Packaged backend responded to /api/health"
    SUCCESS=0
    break
  fi
  sleep $SLEEP_SECS
done

if [ "$SUCCESS" -ne 0 ]; then
  echo "❌ Smoke check failed. Last 200 lines of backend log (if present):"
  if [ -f "$LOGFILE" ]; then
    tail -n 200 "$LOGFILE" || true
  else
    echo "(no log file found at $LOGFILE)"
  fi
  echo "Exiting with failure."
  exit 5
fi

# Cleanup: attempt to stop the backend if it was started by this script
# Try to find a uvicorn/python process with server.py
PK_PID="$(pgrep -f "server.py" || true)"
if [ -n "$PK_PID" ]; then
  echo "Stopping backend processes: $PK_PID"
  pkill -f "server.py" || true
  sleep 1
fi

echo "✅ Post-build smoke check passed."
exit 0
