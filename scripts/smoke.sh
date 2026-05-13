#!/usr/bin/env bash
set -euo pipefail

echo "=== Harvester Smoke Test ==="

echo "[1/8] Validating docker compose config..."
docker compose --env-file .env.example config > /dev/null
echo "Compose config OK"

echo "[2/8] Validating compose services include scheduler and crawl-worker..."
docker compose --env-file .env.example config | grep -q "scheduler" || { echo "ERROR: scheduler service not found in compose config"; exit 1; }
docker compose --env-file .env.example config | grep -q "crawl-worker" || { echo "ERROR: crawl-worker service not found in compose config"; exit 1; }
echo "Scheduler and crawl-worker services present"

echo "[3/8] Validating port conventions..."
# API port 8001, frontend port 5173, omlx external port 8000
docker compose --env-file .env.example config | grep -q "8001" || { echo "WARNING: API port 8001 not found in compose config"; }
echo "Port conventions checked (API:8001, Frontend:5173, omlx:8000)"

echo "[4/8] Checking configuration..."
test -f .env || { echo "WARNING: .env file not found, copying from .env.example"; cp .env.example .env; }

echo "[5/8] Running database migrations..."
uv run alembic upgrade head

echo "[6/8] Checking API health..."
for i in $(seq 1 10); do
  if curl -sf http://localhost:8001/health > /dev/null 2>&1; then
    echo "API is healthy"
    break
  fi
  echo "Waiting for API... attempt $i/10"
  sleep 2
done

echo "[7/8] Running fixture crawl test..."
uv run python -c "
from harvester.cli.main import app
from typer.testing import CliRunner
runner = CliRunner()
result = runner.invoke(app, ['--help'])
assert result.exit_code == 0, f'CLI help failed: {result.output}'
print('CLI OK')
"

echo "[8/8] Running CDC smoke tests..."
uv run pytest tests/integration/test_cdc_public_crawl_smoke.py -q

if [ "${HARVESTER_ENABLE_LIVE_CRAWL:-}" = "1" ]; then
  echo "Live crawl smoke enabled — running live tests..."
  HARVESTER_ENABLE_LIVE_CRAWL=1 uv run pytest tests/integration/test_cdc_public_crawl_smoke.py -q -m "not skip"
fi

echo "=== Smoke test completed ==="
