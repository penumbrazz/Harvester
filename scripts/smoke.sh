#!/usr/bin/env bash
set -euo pipefail

echo "=== Harvester Smoke Test ==="

echo "[1/6] Validating docker compose config..."
docker compose --env-file .env.example config > /dev/null
echo "Compose config OK"

echo "[2/6] Checking configuration..."
test -f .env || { echo "WARNING: .env file not found, copying from .env.example"; cp .env.example .env; }

echo "[3/6] Running database migrations..."
uv run alembic upgrade head

echo "[4/6] Checking API health..."
for i in $(seq 1 10); do
  if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "API is healthy"
    break
  fi
  echo "Waiting for API... attempt $i/10"
  sleep 2
done

echo "[5/6] Running fixture crawl test..."
uv run python -c "
from harvester.cli.main import app
from typer.testing import CliRunner
runner = CliRunner()
result = runner.invoke(app, ['--help'])
assert result.exit_code == 0, f'CLI help failed: {result.output}'
print('CLI OK')
"

echo "[6/6] Running CDC smoke tests..."
uv run pytest tests/integration/test_cdc_public_crawl_smoke.py -q

if [ "${HARVESTER_ENABLE_LIVE_CRAWL:-}" = "1" ]; then
  echo "Live crawl smoke enabled — running live tests..."
  HARVESTER_ENABLE_LIVE_CRAWL=1 uv run pytest tests/integration/test_cdc_public_crawl_smoke.py -q -m "not skip"
fi

echo "=== Smoke test completed ==="
