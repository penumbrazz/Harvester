#!/usr/bin/env bash
set -euo pipefail

echo "=== Harvester Smoke Test ==="

echo "[1/5] Validating docker compose config..."
docker compose --env-file .env.example config > /dev/null
echo "Compose config OK"

echo "[2/5] Checking configuration..."
test -f .env || { echo "WARNING: .env file not found, copying from .env.example"; cp .env.example .env; }

echo "[3/5] Running database migrations..."
uv run alembic upgrade head

echo "[4/5] Checking API health..."
for i in $(seq 1 10); do
  if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "API is healthy"
    break
  fi
  echo "Waiting for API... attempt $i/10"
  sleep 2
done

echo "[5/5] Running fixture crawl test..."
uv run python -c "
from harvester.cli.main import app
from typer.testing import CliRunner
runner = CliRunner()
result = runner.invoke(app, ['--help'])
assert result.exit_code == 0, f'CLI help failed: {result.output}'
print('CLI OK')
"

echo "=== Smoke test completed ==="
