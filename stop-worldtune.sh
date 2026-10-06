#!/usr/bin/env bash
# Stops the WorldTune backend and frontend started by start-worldtune.sh.
#
# Usage: ./stop-worldtune.sh
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="$ROOT/.worldtune-run"
API_PORT=8090; WEB_PORT=3000
# shellcheck disable=SC1091
[ -f "$RUN_DIR/ports.env" ] && . "$RUN_DIR/ports.env"

descendants() { # prints pid and all its descendants, deepest first
  local pid="$1" child
  for child in $(pgrep -P "$pid" 2>/dev/null); do descendants "$child"; done
  echo "$pid"
}

kill_tree() { # pid
  local pids; pids="$(descendants "$1")"
  # shellcheck disable=SC2086
  kill -TERM $pids 2>/dev/null
  for _ in $(seq 1 10); do
    local alive=0 p
    for p in $pids; do kill -0 "$p" 2>/dev/null && alive=1; done
    [ "$alive" = 0 ] && return 0
    sleep 0.5
  done
  # shellcheck disable=SC2086
  kill -KILL $pids 2>/dev/null
}

stop_one() { # name pid_file
  local name="$1" pid_file="$2" pid
  if [ ! -f "$pid_file" ]; then echo "$name: not running (no PID file)."; return; fi
  pid="$(cat "$pid_file" 2>/dev/null || true)"
  if [ -z "$pid" ] || ! kill -0 "$pid" 2>/dev/null; then
    echo "$name: not running."; rm -f "$pid_file"; return
  fi
  echo "$name: stopping PID $pid ..."
  kill_tree "$pid"
  rm -f "$pid_file"
  echo "$name: stopped."
}

# Safety net: a process still listening on our port whose working directory is
# inside this checkout (e.g. a lost PID file) is ours; anything else is left alone.
stop_stray() { # name port
  local name="$1" port="$2" pid cwd
  for pid in $(lsof -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null); do
    cwd="$(lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' | head -1)"
    case "$cwd" in
      "$ROOT"|"$ROOT"/*) echo "$name: stopping stray process $pid on port $port ..."; kill_tree "$pid" ;;
    esac
  done
}

stop_one "Frontend" "$RUN_DIR/frontend.pid"
stop_one "Backend" "$RUN_DIR/backend.pid"
stop_stray "Frontend" "$WEB_PORT"
stop_stray "Backend" "$API_PORT"
echo "Done."
