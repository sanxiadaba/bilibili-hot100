#!/usr/bin/env bash
# Thin wrapper: every platform-specific step lives in launcher.py.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3.11+ is required but python3 was not found on PATH." >&2
  exit 1
fi
exec python3 "$DIR/launcher.py" "$@"
