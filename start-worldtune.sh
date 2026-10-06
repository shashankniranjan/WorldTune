#!/usr/bin/env bash
# Starts the whole WorldTune platform (FastAPI backend + Next.js frontend).
#
# A fresh clone needs nothing else: on first run this script
#   * finds Python >= 3.10 and creates .venv, installs backend dependencies,
#   * installs frontend dependencies (pnpm, or `npx pnpm` if pnpm is missing),
#   * asks for your OpenRouter API key (optional), saves it to ./.env and to
#     your shell profile as OPENROUTER_API_KEY, so later runs never ask again,
#   * starts both services detached and waits until they answer.
#
# Usage:
#   ./start-worldtune.sh              # start (prompts for the key on first run)
#   ./start-worldtune.sh --set-key    # re-enter / replace the OpenRouter key
#   ./start-worldtune.sh --no-prompt  # never prompt (CI); uses key from env/.env if any
#   API_PORT=8091 WEB_PORT=3001 ./start-worldtune.sh
#
# Stop with ./stop-worldtune.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FE_DIR="$ROOT/frontend"
BE_DIR="$ROOT/worldtune/backend"
RUN_DIR="$ROOT/.worldtune-run"
VENV="$ROOT/.venv"
API_PORT="${API_PORT:-8090}"
WEB_PORT="${WEB_PORT:-3000}"
ENV_FILE="$ROOT/.env"
BE_PID_FILE="$RUN_DIR/backend.pid"
FE_PID_FILE="$RUN_DIR/frontend.pid"
BE_LOG="$RUN_DIR/backend.log"
FE_LOG="$RUN_DIR/frontend.log"

SET_KEY=0; PROMPT=1
for arg in "$@"; do
  case "$arg" in
    --set-key) SET_KEY=1 ;;
    --no-prompt) PROMPT=0 ;;
    -h|--help) sed -n '2,17p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Unknown option: $arg (try --help)" >&2; exit 2 ;;
  esac
done

mkdir -p "$RUN_DIR"
say() { printf '==> %s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

is_running() {
  [ -f "$1" ] || return 1
  local pid; pid="$(cat "$1" 2>/dev/null || true)"
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

port_in_use() { lsof -iTCP:"$1" -sTCP:LISTEN -t >/dev/null 2>&1; }

hash_of() { cat "$@" 2>/dev/null | shasum | cut -d' ' -f1; }

# ---------------------------------------------------------------- OpenRouter key
env_file_key() {
  [ -f "$ENV_FILE" ] || return 0
  grep -E '^(OPENROUTER_API_KEY|LLM_API_KEY)=.+' "$ENV_FILE" | head -1 | cut -d= -f2- | tr -d "\"'" || true
}

save_key_to_env_file() {
  local key="$1" tmp="$ENV_FILE.tmp"
  { [ -f "$ENV_FILE" ] && grep -vE '^(OPENROUTER_API_KEY|LLM_API_KEY)=' "$ENV_FILE" || true; } > "$tmp"
  printf 'OPENROUTER_API_KEY=%s\n' "$key" >> "$tmp"
  mv "$tmp" "$ENV_FILE"; chmod 600 "$ENV_FILE"
}

save_key_to_shell_profile() {
  local key="$1" profile
  case "$(basename "${SHELL:-/bin/zsh}")" in
    zsh)  profile="$HOME/.zshrc" ;;
    bash) if [ "$(uname)" = Darwin ]; then profile="$HOME/.bash_profile"; else profile="$HOME/.bashrc"; fi ;;
    *)    say "Unrecognised shell; add this to your profile yourself:  export OPENROUTER_API_KEY=..."; return 0 ;;
  esac
  touch "$profile"
  local tmp="$profile.worldtune.tmp"
  # Replace our marked block if present, otherwise append one.
  awk '/^# >>> worldtune >>>$/{skip=1} !skip{print} /^# <<< worldtune <<<$/{skip=0}' "$profile" > "$tmp"
  local q="${key//\'/\'\\\'\'}"
  { cat "$tmp"
    printf '# >>> worldtune >>>\nexport OPENROUTER_API_KEY='"'"'%s'"'"'\n# <<< worldtune <<<\n' "$q"
  } > "$profile"
  rm -f "$tmp"
  say "Saved OPENROUTER_API_KEY to $profile (open a new terminal to pick it up)."
}

resolve_openrouter_key() {
  local key="${OPENROUTER_API_KEY:-}"
  [ -n "$key" ] || key="$(env_file_key)"
  if [ "$SET_KEY" = 1 ] || [ -z "$key" ]; then
    if [ "$PROMPT" = 1 ] && [ -t 0 ]; then
      echo
      echo "WorldTune uses OpenRouter for AI-written briefings."
      echo "Get a key at https://openrouter.ai/keys. Press Enter to skip; the platform still"
      echo "runs, using built-in deterministic briefings instead of AI ones."
      local entered=""
      read -r -s -p "OpenRouter API key: " entered || true
      echo
      if [ -n "$entered" ]; then
        key="$entered"
        save_key_to_env_file "$key"
        save_key_to_shell_profile "$key"
      elif [ "$SET_KEY" = 1 ]; then
        say "No key entered; keeping the existing configuration."
      fi
    fi
  fi
  if [ -n "$key" ]; then
    export OPENROUTER_API_KEY="$key"
    # Keep .env in sync when the key came from the environment only.
    [ -n "$(env_file_key)" ] || save_key_to_env_file "$key"
    say "OpenRouter key: configured (AI briefings enabled)."
  else
    say "OpenRouter key: not set (deterministic briefings only; run ./start-worldtune.sh --set-key later)."
  fi
}

# ---------------------------------------------------------------- Backend setup
find_python() {
  local c v
  for c in python3.13 python3.12 python3.11 python3.10 python3; do
    command -v "$c" >/dev/null 2>&1 || continue
    v="$("$c" -c 'import sys; print(1 if sys.version_info >= (3, 10) else 0)' 2>/dev/null || echo 0)"
    [ "$v" = 1 ] && { command -v "$c"; return 0; }
  done
  return 1
}

setup_backend() {
  if [ -x "$VENV/bin/python" ] && ! "$VENV/bin/python" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
    say "Existing .venv uses Python < 3.10; recreating it."
    rm -rf "$VENV"
  fi
  if [ ! -x "$VENV/bin/python" ]; then
    local py; py="$(find_python)" || die "Python 3.10+ is required. Install it (macOS: 'brew install python@3.12') and re-run."
    say "Creating virtualenv with $("$py" --version) ..."
    "$py" -m venv "$VENV"
  fi
  local want have_file="$VENV/.worldtune-deps"
  want="$(hash_of "$BE_DIR/pyproject.toml")"
  if [ "$(cat "$have_file" 2>/dev/null || true)" != "$want" ]; then
    say "Installing backend dependencies (first run takes a minute or two) ..."
    "$VENV/bin/python" -m pip install --quiet --upgrade pip
    "$VENV/bin/python" -m pip install --quiet -e "$BE_DIR"
    echo "$want" > "$have_file"
  fi
  [ -f "$ROOT/data/processed/worldtune/world_shifts/gold_world_shifts.parquet" ] \
    || say "WARNING: data/processed/worldtune/world_shifts/gold_world_shifts.parquet is missing; the API will have no World Shifts to serve."
}

# ---------------------------------------------------------------- Frontend setup
PNPM=()
pick_pnpm() {
  if command -v pnpm >/dev/null 2>&1; then PNPM=(pnpm)
  elif command -v npx >/dev/null 2>&1; then PNPM=(npx --yes pnpm@10)
  else die "Node.js 18+ (with npm) is required. Install it (macOS: 'brew install node') and re-run."; fi
}

setup_frontend() {
  command -v node >/dev/null 2>&1 || die "Node.js 18+ is required. Install it (macOS: 'brew install node') and re-run."
  pick_pnpm
  local want have_file="$FE_DIR/node_modules/.worldtune-install"
  want="$(hash_of "$FE_DIR/package.json" "$FE_DIR/pnpm-lock.yaml")"
  if [ ! -d "$FE_DIR/node_modules" ] || [ "$(cat "$have_file" 2>/dev/null || true)" != "$want" ]; then
    say "Installing frontend dependencies (first run takes a minute or two) ..."
    ( cd "$FE_DIR" && "${PNPM[@]}" install --frozen-lockfile ) >"$RUN_DIR/frontend-install.log" 2>&1 \
      || { tail -20 "$RUN_DIR/frontend-install.log" >&2; die "Frontend install failed (full log: $RUN_DIR/frontend-install.log)."; }
    echo "$want" > "$have_file"
  fi
}

# ---------------------------------------------------------------- Process control
start_detached() { # pid_file log_file cmd...
  local pid_file="$1" log_file="$2"; shift 2
  nohup "$@" >"$log_file" 2>&1 < /dev/null &
  local pid=$!
  disown "$pid" 2>/dev/null || true
  echo "$pid" > "$pid_file"
}

wait_for_url() { # name url pid_file log timeout
  local name="$1" url="$2" pid_file="$3" log="$4" timeout="$5" i=0
  while [ "$i" -lt "$timeout" ]; do
    if curl -fsS -o /dev/null --max-time 2 "$url" 2>/dev/null; then return 0; fi
    is_running "$pid_file" || { tail -20 "$log" >&2; die "$name exited during startup (log: $log)."; }
    sleep 1; i=$((i + 1))
  done
  tail -20 "$log" >&2; die "$name did not become ready within ${timeout}s (log: $log)."
}

start_backend() {
  if is_running "$BE_PID_FILE"; then say "Backend already running (PID $(cat "$BE_PID_FILE"))."; return; fi
  port_in_use "$API_PORT" && die "Port $API_PORT is already in use. Free it or set API_PORT=<other>."
  say "Starting backend on http://127.0.0.1:$API_PORT ..."
  ( cd "$ROOT"
    export PYTHONPATH="worldtune/backend"
    export WORLDTUNE_CORS_ORIGINS="http://localhost:$WEB_PORT,http://127.0.0.1:$WEB_PORT"
    start_detached "$BE_PID_FILE" "$BE_LOG" "$VENV/bin/python" -m uvicorn app.main:app --host 127.0.0.1 --port "$API_PORT" )
  wait_for_url "Backend" "http://127.0.0.1:$API_PORT/health" "$BE_PID_FILE" "$BE_LOG" 90
}

start_frontend() {
  if is_running "$FE_PID_FILE"; then say "Frontend already running (PID $(cat "$FE_PID_FILE"))."; return; fi
  port_in_use "$WEB_PORT" && die "Port $WEB_PORT is already in use. Free it or set WEB_PORT=<other>."
  say "Starting frontend on http://localhost:$WEB_PORT (first compile can take ~30s) ..."
  ( cd "$FE_DIR"
    export NEXT_PUBLIC_WORLDTUNE_DATA_SOURCE=api
    export NEXT_PUBLIC_WORLDTUNE_API_URL="http://localhost:$API_PORT"
    start_detached "$FE_PID_FILE" "$FE_LOG" "${PNPM[@]}" exec next dev -p "$WEB_PORT" )
  wait_for_url "Frontend" "http://localhost:$WEB_PORT" "$FE_PID_FILE" "$FE_LOG" 180
}

# ---------------------------------------------------------------- Main
resolve_openrouter_key
setup_backend
setup_frontend
printf 'API_PORT=%s\nWEB_PORT=%s\n' "$API_PORT" "$WEB_PORT" > "$RUN_DIR/ports.env"
start_backend
start_frontend

cat <<MSG

WorldTune is running.
  App:      http://localhost:$WEB_PORT
  API:      http://localhost:$API_PORT   (health: /health, docs: /docs)
  Logs:     $RUN_DIR/backend.log, $RUN_DIR/frontend.log
  Stop:     $ROOT/stop-worldtune.sh
MSG
