#!/usr/bin/env bash
# Starts the WorldTune backend (FastAPI, :8090) and frontend (Next.js, :3000)
# together, as detached background processes. Stop both with
# ./stop-worldtune.sh (same directory).
#
# Usage: ./start-worldtune.sh
set -euo pipefail

BE_DIR="/Users/shashankniranjan/IdeaProjects/WorldTune-BE"
FE_DIR="/Users/shashankniranjan/IdeaProjects/WorldTune-FE"
RUN_DIR="$BE_DIR/.worldtune-run"
mkdir -p "$RUN_DIR"

BE_PID_FILE="$RUN_DIR/backend.pid"
FE_PID_FILE="$RUN_DIR/frontend.pid"
BE_LOG="$RUN_DIR/backend.log"
FE_LOG="$RUN_DIR/frontend.log"

is_running() {
  local pid_file="$1"
  [ -f "$pid_file" ] || return 1
  local pid; pid="$(cat "$pid_file" 2>/dev/null || true)"
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

# Detach fully (setsid where available, else nohup) so each process survives
# this script exiting, and record its PID for stop-worldtune.sh.
start_detached() {
  local pid_file="$1" log_file="$2"; shift 2
  if command -v setsid >/dev/null 2>&1; then
    setsid "$@" >"$log_file" 2>&1 < /dev/null &
  else
    nohup "$@" >"$log_file" 2>&1 < /dev/null &
  fi
  local pid=$!
  disown "$pid" 2>/dev/null || true
  echo "$pid" > "$pid_file"
}

# --- Backend ---------------------------------------------------------------
if is_running "$BE_PID_FILE"; then
  echo "Backend already running (PID $(cat "$BE_PID_FILE")) - skipping."
else
  echo "Starting backend (FastAPI) on http://127.0.0.1:8090 ..."
  BE_PYTHON="$BE_DIR/.venv/bin/python"
  [ -x "$BE_PYTHON" ] || BE_PYTHON="python3"
  (
    cd "$BE_DIR"
    export PYTHONPATH="worldtune/backend"
    start_detached "$BE_PID_FILE" "$BE_LOG" \
      "$BE_PYTHON" -m uvicorn app.main:app --host 127.0.0.1 --port 8090
  )
  echo "  backend PID: $(cat "$BE_PID_FILE")   log: $BE_LOG"
fi

# --- Frontend ---------------------------------------------------------------
if is_running "$FE_PID_FILE"; then
  echo "Frontend already running (PID $(cat "$FE_PID_FILE")) - skipping."
else
  echo "Starting frontend (Next.js) on http://localhost:3000 ..."
  DEV_CMD=(pnpm dev)
  command -v pnpm >/dev/null 2>&1 || DEV_CMD=(npm run dev)
  (
    cd "$FE_DIR"
    export NEXT_PUBLIC_WORLDTUNE_DATA_SOURCE=api
    export NEXT_PUBLIC_WORLDTUNE_API_URL=http://localhost:8090
    start_detached "$FE_PID_FILE" "$FE_LOG" "${DEV_CMD[@]}"
  )
  echo "  frontend PID: $(cat "$FE_PID_FILE")   log: $FE_LOG"
fi

cat <<EOF

WorldTune is starting up (give it a few seconds for Next.js to compile).
  Frontend: http://localhost:3000
  Backend:  http://localhost:8090   (health: http://localhost:8090/health)

Logs:
  $BE_LOG
  $FE_LOG

Stop both with: $BE_DIR/stop-worldtune.sh
EOF
