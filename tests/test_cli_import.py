"""Test CLI import and help command."""

import subprocess


def test_cli_help():
    """Assert python -m harvester.cli.main --help exits 0."""
    result = subprocess.run(
        ["uv", "run", "python", "-m", "harvester.cli.main", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    # Verify it's a Typer app by checking for Typer-like output
    assert "Usage" in result.stdout or "harvester" in result.stdout.lower()
