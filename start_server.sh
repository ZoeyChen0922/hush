#!/bin/bash
set -e
cd "$(dirname "$0")"
# hush_backend.py loads .env itself; never expand its contents in the shell.
for hush_python in "$PWD/.venv/bin/python" "$PWD/../Hush图/.venv/bin/python" "$(command -v python3)"; do
  if [ -x "$hush_python" ] && "$hush_python" -c 'import fastapi, uvicorn, requests' 2>/dev/null; then
    echo 'Hush: http://127.0.0.1:8000/hush_app.html?v=journey-2'
    exec "$hush_python" hush_backend.py
  fi
done
echo 'No Hush Python environment found. Install fastapi, uvicorn and requests in a project .venv.' >&2
exit 1
