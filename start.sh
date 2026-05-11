#!/usr/bin/env bash
set -euo pipefail

# Harvester - Start backend and frontend dev servers

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_PORT="${HARVESTER_PORT:-8001}"
FRONTEND_PORT="${HARVESTER_FRONTEND_PORT:-5173}"

cleanup() {
  echo ""
  echo "Stopping servers..."
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
  wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
  echo "Stopped."
}
trap cleanup EXIT INT TERM

# Load .env if present
if [ -f "$ROOT_DIR/.env" ]; then
  set -a
  # shellcheck disable=SC1090
  source "$ROOT_DIR/.env"
  set +a
fi

# Start backend
echo "Starting backend on :${BACKEND_PORT}..."
uv run uvicorn harvester.api.app:create_app --factory \
  --host 0.0.0.0 --port "$BACKEND_PORT" --reload &
BACKEND_PID=$!

# Start frontend
echo "Starting frontend on :${FRONTEND_PORT}..."
(cd "$ROOT_DIR/frontend" && npm run dev -- --port "$FRONTEND_PORT") &
FRONTEND_PID=$!

echo ""
echo "Harvester is running:"
echo "  Backend:  http://localhost:${BACKEND_PORT}"
echo "  Frontend: http://localhost:${FRONTEND_PORT}"
echo ""
echo "Press Ctrl+C to stop."
wait
