"""Harvester CLI application."""

import typer

app = typer.Typer(
    name="harvester",
    help="Personal home lab information collection control plane",
    add_completion=False,
)


@app.command()
def health(
    base_url: str = typer.Option(
        "http://localhost:8000",
        "--base-url",
        help="Base URL of the Harvester API",
    ),
) -> None:
    """Check the health of the Harvester API.

    Args:
        base_url: Base URL of the Harvester API.
    """
    import httpx

    try:
        response = httpx.get(f"{base_url}/health", timeout=5.0)
        if response.status_code == 200:
            typer.echo(f"✓ API is healthy: {response.json()}")
        else:
            typer.echo(f"✗ API returned status {response.status_code}")
            raise typer.Exit(code=1)
    except httpx.ConnectError as e:
        typer.echo(f"✗ Failed to connect to API at {base_url}: {e}")
        raise typer.Exit(code=1) from None
    except Exception as e:
        typer.echo(f"✗ Error checking API health: {e}")
        raise typer.Exit(code=1) from None


if __name__ == "__main__":
    app()
