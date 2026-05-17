#!/usr/bin/env bash
set -euo pipefail

# Harvester - Start all services (backend, frontend, daemons)
# Set HARVESTER_START_DAEMONS=0 to skip daemon processes

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_PORT="${HARVESTER_PORT:-8001}"
FRONTEND_PORT="${HARVESTER_FRONTEND_PORT:-5173}"

PIDS=()

cleanup() {
  echo ""
  echo "Stopping servers..."
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  for pid in "${PIDS[@]}"; do
    wait "$pid" 2>/dev/null || true
  done
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
PIDS+=($!)

# Start frontend
echo "Starting frontend on :${FRONTEND_PORT}..."
(cd "$ROOT_DIR/frontend" && npm run dev -- --port "$FRONTEND_PORT") &
PIDS+=($!)

echo ""
echo "Harvester is running:"
echo "  Backend:  http://localhost:${BACKEND_PORT}"
echo "  Frontend: http://localhost:${FRONTEND_PORT}"

# Optionally start daemon processes
if [ "${HARVESTER_START_DAEMONS:-1}" = "1" ]; then
  echo ""
  echo "Starting scheduler daemon..."
  uv run harvester scheduler daemon &
  PIDS+=($!)

  echo "Starting crawl worker daemon..."
  uv run harvester worker run --job-type crawl &
  PIDS+=($!)

  echo "Starting extract worker daemon..."
  uv run harvester worker run --job-type extract &
  PIDS+=($!)

  echo "Starting embedding worker daemon..."
  uv run harvester worker run --job-type embed_chunks &
  PIDS+=($!)

  echo "  Scheduler daemon: active"
  echo "  Crawl worker daemon: active"
  echo "  Extract worker daemon: active"
  echo "  Embedding worker daemon: active"
fi

echo ""
echo "Press Ctrl+C to stop."
wait
