#!/usr/bin/env bash
# WorldPulse -- start/stop the API and dashboard as background processes.
#
# Usage:
#   ./worldpulse.sh start      # start API (uvicorn) + dashboard (streamlit)
#   ./worldpulse.sh stop       # stop both
#   ./worldpulse.sh restart    # stop, then start
#   ./worldpulse.sh status     # show whether each is running, PID, port, URL
#   ./worldpulse.sh logs       # tail both logs (Ctrl-C to stop tailing; processes keep running)
#
# Env overrides:
#   API_PORT=8000 DASHBOARD_PORT=8501 ./worldpulse.sh start
#
# PIDs and logs live under ./.run/, next to this script. Nothing here is
# committed to git (see .gitignore).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="$ROOT_DIR/.run"
API_PID_FILE="$RUN_DIR/api.pid"
DASH_PID_FILE="$RUN_DIR/dashboard.pid"
API_LOG="$RUN_DIR/api.log"
DASH_LOG="$RUN_DIR/dashboard.log"

API_PORT="${API_PORT:-8000}"
DASHBOARD_PORT="${DASHBOARD_PORT:-8501}"

mkdir -p "$RUN_DIR"
cd "$ROOT_DIR"

# Prefer a local venv if one exists (.venv, created e.g. via
# `python3.12 -m venv .venv`); otherwise fall back to whatever `python3`
# resolves to on PATH.
PYTHON="python3"
if [ -x "$ROOT_DIR/.venv/bin/python" ]; then
  PYTHON="$ROOT_DIR/.venv/bin/python"
fi

is_running() {
  # $1 = pid file. Returns 0 (true) if the PID in it is a live process.
  local pid_file="$1"
  [ -f "$pid_file" ] || return 1
  local pid
  pid="$(cat "$pid_file" 2>/dev/null || true)"
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

start_one() {
  local name="$1" pid_file="$2" log_file="$3"; shift 3
  if is_running "$pid_file"; then
    echo "  $name already running (pid $(cat "$pid_file"))"
    return 0
  fi
  echo "  starting $name -> $log_file"
  # Detach fully (setsid where available) so it survives this script exiting.
  if command -v setsid >/dev/null 2>&1; then
    setsid "$@" >"$log_file" 2>&1 < /dev/null &
  else
    nohup "$@" >"$log_file" 2>&1 < /dev/null &
  fi
  local pid=$!
  disown "$pid" 2>/dev/null || true
  echo "$pid" > "$pid_file"
}

stop_one() {
  local name="$1" pid_file="$2"
  if ! is_running "$pid_file"; then
    echo "  $name not running"
    rm -f "$pid_file"
    return 0
  fi
  local pid
  pid="$(cat "$pid_file")"
  echo "  stopping $name (pid $pid)"
  kill "$pid" 2>/dev/null || true
  for _ in $(seq 1 10); do
    kill -0 "$pid" 2>/dev/null || break
    sleep 0.5
  done
  kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null || true
  rm -f "$pid_file"
}

status_one() {
  local name="$1" pid_file="$2" url="$3"
  if is_running "$pid_file"; then
    echo "  $name: RUNNING  pid=$(cat "$pid_file")  $url"
  else
    echo "  $name: STOPPED"
  fi
}

cmd="${1:-}"
case "$cmd" in
  start)
    echo "Starting WorldPulse..."
    start_one "api" "$API_PID_FILE" "$API_LOG" \
      "$PYTHON" -m uvicorn apps.api.main:app --host 0.0.0.0 --port "$API_PORT"
    start_one "dashboard" "$DASH_PID_FILE" "$DASH_LOG" \
      "$PYTHON" -m streamlit run apps/dashboard/app.py \
        --server.port "$DASHBOARD_PORT" --server.headless true
    echo "Waiting for them to come up..."
    sleep 3
    "$0" status
    ;;
  stop)
    echo "Stopping WorldPulse..."
    stop_one "dashboard" "$DASH_PID_FILE"
    stop_one "api" "$API_PID_FILE"
    ;;
  restart)
    "$0" stop
    "$0" start
    ;;
  status)
    echo "WorldPulse status:"
    status_one "api" "$API_PID_FILE" "http://localhost:$API_PORT/docs"
    status_one "dashboard" "$DASH_PID_FILE" "http://localhost:$DASHBOARD_PORT"
    ;;
  logs)
    tail -f "$API_LOG" "$DASH_LOG"
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|status|logs}"
    exit 1
    ;;
esac
