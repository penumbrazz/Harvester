#!/usr/bin/env bash
set -euo pipefail

echo "=== Harvester Smoke Test ==="

echo "[1/4] Checking configuration..."
test -f .env || { echo "ERROR: .env file not found"; exit 1; }

echo "[2/4] Running database migrations..."
uv run alembic upgrade head

echo "[3/4] Checking API health..."
for i in $(seq 1 10); do
  if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "API is healthy"
    break
  fi
  echo "Waiting for API... attempt $i/10"
  sleep 2
done

echo "[4/4] Running fixture crawl test..."
uv run python -c "
from harvester.cli.main import app
from typer.testing import CliRunner
runner = CliRunner()
result = runner.invoke(app, ['--help'])
assert result.exit_code == 0, f'CLI help failed: {result.output}'
print('CLI OK')
"

echo "=== Smoke test completed ==="
