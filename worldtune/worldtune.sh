#!/usr/bin/env bash
# WorldTune -- start/stop the backend (FastAPI) and frontend (Next.js) as
# background processes.
#
# Usage:
#   ./worldtune.sh start      # start backend (uvicorn) + frontend (next dev)
#   ./worldtune.sh stop       # stop both
#   ./worldtune.sh restart    # stop, then start
#   ./worldtune.sh status     # show whether each is running, PID, port, URL
#   ./worldtune.sh logs       # tail both logs (Ctrl-C just stops tailing)
#
# Env overrides:
#   API_PORT=8091 WEB_PORT=3001 ./worldtune.sh start
#
# PIDs and logs live under ./.run/, next to this script. Nothing here is
# committed to git.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
RUN_DIR="$ROOT_DIR/.run"
API_PID_FILE="$RUN_DIR/api.pid"
WEB_PID_FILE="$RUN_DIR/web.pid"
API_LOG="$RUN_DIR/api.log"
WEB_LOG="$RUN_DIR/web.log"

API_PORT="${API_PORT:-8090}"
WEB_PORT="${WEB_PORT:-3000}"

mkdir -p "$RUN_DIR"

# Prefer a local venv if one exists (backend/.venv, created e.g. via
# `python3.12 -m venv .venv` inside backend/); otherwise fall back to
# whatever `python3` resolves to on PATH.
PYTHON="python3"
if [ -x "$BACKEND_DIR/.venv/bin/python" ]; then
  PYTHON="$BACKEND_DIR/.venv/bin/python"
fi

is_running() {
  local pid_file="$1"
  [ -f "$pid_file" ] || return 1
  local pid
  pid="$(cat "$pid_file" 2>/dev/null || true)"
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

port_in_use() {
  # $1 = port. True if something (anything, not just ours) is listening.
  lsof -i ":$1" -sTCP:LISTEN >/dev/null 2>&1
}

start_one() {
  local name="$1" pid_file="$2" log_file="$3" port="$4" dir="$5"; shift 5
  if is_running "$pid_file"; then
    echo "  $name already running (pid $(cat "$pid_file"))"
    return 0
  fi
  if port_in_use "$port"; then
    echo "  WARNING: port $port is already in use by something else."
    echo "           lsof -i :$port    # see what's using it"
    echo "           ${name^^}_PORT=<other-port> $0 start    # or use a different port"
    return 1
  fi
  echo "  starting $name on port $port -> $log_file"
  (
    cd "$dir"
    if command -v setsid >/dev/null 2>&1; then
      setsid "$@" >"$log_file" 2>&1 < /dev/null &
    else
      nohup "$@" >"$log_file" 2>&1 < /dev/null &
    fi
    echo $! > "$pid_file"
  )
  disown 2>/dev/null || true
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
  echo "  stopping $name (pid $pid, and its child process group)"
  # Backend/frontend dev servers spawn child processes (uvicorn reloader,
  # next's worker) -- kill the whole group, not just the top PID.
  kill -- "-$pid" 2>/dev/null || kill "$pid" 2>/dev/null || true
  for _ in $(seq 1 10); do
    kill -0 "$pid" 2>/dev/null || break
    sleep 0.5
  done
  kill -9 -- "-$pid" 2>/dev/null || kill -9 "$pid" 2>/dev/null || true
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

ensure_frontend_env() {
  # Keep the frontend pointed at whatever API_PORT this run is using, so a
  # `WEB_PORT=... API_PORT=... ./worldtune.sh start` doesn't silently talk
  # to a stale port from an old .env.local. NEXT_PUBLIC_* vars are baked in
  # at build time, so changing this requires a rebuild (handled below).
  local env_file="$FRONTEND_DIR/.env.local"
  local desired="NEXT_PUBLIC_API_BASE_URL=http://localhost:$API_PORT"
  if [ ! -f "$env_file" ] || [ "$(cat "$env_file")" != "$desired" ]; then
    echo "$desired" > "$env_file"
    # Force a rebuild below since the baked-in API URL just changed.
    rm -rf "$FRONTEND_DIR/.next"
  fi
}

ensure_frontend_build() {
  # `next dev` lazily fetches a platform-specific compiler binary on first
  # run, which fails with no network access. Building once and serving the
  # production build with `next start` avoids that and is what you want
  # for "just run it" anyway.
  if [ ! -d "$FRONTEND_DIR/.next" ]; then
    echo "  building frontend (first run, or API URL changed)..."
    (cd "$FRONTEND_DIR" && npm run build)
  fi
}

check_deps() {
  local ok=1
  if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo "  frontend/node_modules missing -- run: (cd frontend && npm install)"
    ok=0
  fi
  if ! "$PYTHON" -c "import fastapi" >/dev/null 2>&1; then
    echo "  backend deps missing -- run: (cd backend && pip install -e \".[dev]\")"
    ok=0
  fi
  [ "$ok" = 1 ]
}

cmd="${1:-}"
case "$cmd" in
  start)
    echo "Starting WorldTune..."
    check_deps || { echo "Install the missing dependencies above, then re-run."; exit 1; }
    ensure_frontend_env
    ensure_frontend_build
    start_one "api" "$API_PID_FILE" "$API_LOG" "$API_PORT" "$BACKEND_DIR" \
      "$PYTHON" -m uvicorn app.main:app --host 0.0.0.0 --port "$API_PORT"
    start_one "web" "$WEB_PID_FILE" "$WEB_LOG" "$WEB_PORT" "$FRONTEND_DIR" \
      npm run start -- -p "$WEB_PORT"
    echo "Waiting for them to come up..."
    sleep 3
    "$0" status
    ;;
  stop)
    echo "Stopping WorldTune..."
    stop_one "web" "$WEB_PID_FILE"
    stop_one "api" "$API_PID_FILE"
    ;;
  restart)
    "$0" stop
    "$0" start
    ;;
  status)
    echo "WorldTune status:"
    status_one "api" "$API_PID_FILE" "http://localhost:$API_PORT/api/dashboard"
    status_one "web" "$WEB_PID_FILE" "http://localhost:$WEB_PORT"
    ;;
  logs)
    tail -f "$API_LOG" "$WEB_LOG"
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|status|logs}"
    echo "Env overrides: API_PORT=8091 WEB_PORT=3001 $0 start"
    exit 1
    ;;
esac
