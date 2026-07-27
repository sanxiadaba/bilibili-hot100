#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_DIR="$PROJECT_DIR/.pids"
MODE="all"
[[ "${1:-}" == "--frontend-only" ]] && MODE="frontend"
[[ "${1:-}" == "--backend-only" ]] && MODE="backend"

stop_owned() {
  local name="$1" needle="$2" pid_file="$PID_DIR/$name.pid" pid command
  if [[ ! -f "$pid_file" ]]; then echo "  $name is not running."; return; fi
  pid="$(tr -d '[:space:]' < "$pid_file")"
  command="$(ps -p "$pid" -o command= 2>/dev/null || true)"
  if [[ ! "$pid" =~ ^[0-9]+$ || "$command" != *"$PROJECT_DIR"* || "$command" != *"$needle"* ]]; then
    echo "  Refusing to stop unverified $name PID ${pid:-unknown}." >&2
    rm -f "$pid_file"
    return
  fi
  kill "$pid" 2>/dev/null || true
  for _ in {1..20}; do kill -0 "$pid" 2>/dev/null || break; sleep 0.25; done
  if kill -0 "$pid" 2>/dev/null; then kill -9 "$pid"; fi
  rm -f "$pid_file"
  echo "  Stopped $name (PID $pid)."
}

[[ "$MODE" == "frontend" ]] || stop_owned backend 'uvicorn main:app'
[[ "$MODE" == "backend" ]] || stop_owned frontend 'vite.js'
if [[ -d "$PID_DIR" ]] && ! find "$PID_DIR" -mindepth 1 -print -quit | grep -q .; then rmdir "$PID_DIR"; fi
