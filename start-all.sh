#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/bilibili-hot100-backend"
FRONTEND_DIR="$PROJECT_DIR/bilibili-hot100-vue3-ts"
PID_DIR="$PROJECT_DIR/.pids"
DATA_DIR="$PROJECT_DIR/data"
MODE="all"
DETACHED=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --frontend-only) MODE="frontend"; shift ;;
    --backend-only) MODE="backend"; shift ;;
    --detached) DETACHED=true; shift ;;
    --data-dir)
      [[ $# -ge 2 ]] || { echo "Missing value for --data-dir" >&2; exit 2; }
      DATA_DIR="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

mkdir -p "$PID_DIR" "$DATA_DIR"

owned_pid() {
  local name="$1" needle="$2" pid_file="$PID_DIR/$name.pid" pid command
  [[ -f "$pid_file" ]] || return 1
  pid="$(tr -d '[:space:]' < "$pid_file")"
  [[ "$pid" =~ ^[0-9]+$ ]] || { rm -f "$pid_file"; return 1; }
  kill -0 "$pid" 2>/dev/null || { rm -f "$pid_file"; return 1; }
  command="$(ps -p "$pid" -o command= 2>/dev/null || true)"
  [[ "$command" == *"$PROJECT_DIR"* && "$command" == *"$needle"* ]] || {
    rm -f "$pid_file"
    return 1
  }
  printf '%s' "$pid"
}

assert_port_available() {
  local port="$1" owned="${2:-}" occupants
  command -v lsof >/dev/null 2>&1 || return 0
  occupants="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  [[ -z "$occupants" ]] && return 0
  [[ -n "$owned" && "$occupants" == *"$owned"* ]] && return 0
  echo "Port $port is already used by another process (PID: $occupants)." >&2
  exit 1
}

wait_for_url() {
  local name="$1" url="$2"
  for _ in {1..90}; do
    if curl --silent --fail --max-time 2 "$url" >/dev/null; then
      echo "  $name is ready: $url"
      return 0
    fi
    sleep 0.5
  done
  echo "$name did not become ready. Check logs in $PID_DIR." >&2
  exit 1
}

backend_pid="$(owned_pid backend 'uvicorn main:app' || true)"
frontend_pid="$(owned_pid frontend 'vite.js' || true)"

if [[ "$MODE" != "frontend" ]]; then
  assert_port_available 8000 "$backend_pid"
  if [[ -z "$backend_pid" ]]; then
    [[ -x "$BACKEND_DIR/.venv/bin/python" ]] || python3 -m venv "$BACKEND_DIR/.venv"
    requirements_hash="$(cksum < "$BACKEND_DIR/requirements.txt")"
    marker="$BACKEND_DIR/.venv/.requirements.cksum"
    installed_hash="$(cat "$marker" 2>/dev/null || true)"
    if [[ "$requirements_hash" != "$installed_hash" ]] || \
      ! "$BACKEND_DIR/.venv/bin/python" -c 'import aiofiles, aiohttp, fastapi, pydantic, uvicorn' 2>/dev/null; then
      "$BACKEND_DIR/.venv/bin/python" -m pip install -r "$BACKEND_DIR/requirements.txt"
      printf '%s' "$requirements_hash" > "$marker"
    fi
    BILIBILI_DATA_DIR="$DATA_DIR" nohup "$BACKEND_DIR/.venv/bin/python" \
      -m uvicorn main:app --host 127.0.0.1 --port 8000 \
      >"$PID_DIR/backend.out.log" 2>"$PID_DIR/backend.err.log" &
    backend_pid=$!
    printf '%s' "$backend_pid" > "$PID_DIR/backend.pid"
  else
    echo "  Backend already running (PID $backend_pid)."
  fi
  wait_for_url Backend http://127.0.0.1:8000/api/status
fi

if [[ "$MODE" != "backend" ]]; then
  assert_port_available 3000 "$frontend_pid"
  if [[ -z "$frontend_pid" ]]; then
    lock_hash="$(cksum < "$FRONTEND_DIR/package-lock.json")"
    frontend_marker="$FRONTEND_DIR/node_modules/.package-lock.cksum"
    installed_lock_hash="$(cat "$frontend_marker" 2>/dev/null || true)"
    if [[ ! -d "$FRONTEND_DIR/node_modules" || "$lock_hash" != "$installed_lock_hash" ]]; then
      (cd "$FRONTEND_DIR" && npm ci)
      printf '%s' "$lock_hash" > "$frontend_marker"
    fi
    nohup node "$FRONTEND_DIR/node_modules/vite/bin/vite.js" \
      --host 127.0.0.1 --port 3000 \
      >"$PID_DIR/frontend.out.log" 2>"$PID_DIR/frontend.err.log" &
    frontend_pid=$!
    printf '%s' "$frontend_pid" > "$PID_DIR/frontend.pid"
  else
    echo "  Frontend already running (PID $frontend_pid)."
  fi
  wait_for_url Frontend http://127.0.0.1:3000
fi

cat > "$PID_DIR/services.txt" <<EOF
Frontend=http://127.0.0.1:3000
Backend=http://127.0.0.1:8000
Docs=http://127.0.0.1:8000/docs
EOF

echo "Bilibili Hot100 services started successfully."
if [[ "$DETACHED" == false ]]; then
  if command -v open >/dev/null 2>&1; then open http://127.0.0.1:3000
  elif command -v xdg-open >/dev/null 2>&1; then xdg-open http://127.0.0.1:3000
  fi
  cleanup() { "$PROJECT_DIR/stop-all.sh"; }
  trap cleanup EXIT INT TERM
  wait
fi
