#!/usr/bin/env bash
# Stops the WorldTune backend and frontend started by start-worldtune.sh.
#
# Usage: ./stop-worldtune.sh
set -uo pipefail

BE_DIR="/Users/shashankniranjan/IdeaProjects/WorldTune-BE"
RUN_DIR="$BE_DIR/.worldtune-run"
BE_PID_FILE="$RUN_DIR/backend.pid"
FE_PID_FILE="$RUN_DIR/frontend.pid"

stop_one() {
  local name="$1" pid_file="$2"
  if [ ! -f "$pid_file" ]; then
    echo "$name: not running (no PID file)."
    return
  fi
  local pid; pid="$(cat "$pid_file" 2>/dev/null || true)"
  if [ -z "$pid" ] || ! kill -0 "$pid" 2>/dev/null; then
    echo "$name: not running."
    rm -f "$pid_file"
    return
  fi
  echo "$name: stopping PID $pid ..."
  # pnpm/npm fork the real dev-server process, so kill children first.
  pkill -TERM -P "$pid" 2>/dev/null
  kill -TERM "$pid" 2>/dev/null
  for _ in $(seq 1 10); do
    kill -0 "$pid" 2>/dev/null || break
    sleep 0.5
  done
  if kill -0 "$pid" 2>/dev/null; then
    echo "$name: still running after SIGTERM, sending SIGKILL."
    pkill -KILL -P "$pid" 2>/dev/null
    kill -KILL "$pid" 2>/dev/null
  fi
  rm -f "$pid_file"
  echo "$name: stopped."
}

stop_one "Backend" "$BE_PID_FILE"
stop_one "Frontend" "$FE_PID_FILE"

# Fallback safety net in case a PID file was lost (e.g. after a machine
# restart) and a process is still lingering.
pkill -f "uvicorn app.main:app" 2>/dev/null && echo "Killed a stray backend (uvicorn) process."
pkill -f "next-server \(v" 2>/dev/null && echo "Killed a stray frontend (next-server) process."

echo "Done."
