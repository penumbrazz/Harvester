"""Harvester CLI application."""

import os
from unittest.mock import patch

import httpx
import typer

app = typer.Typer(
    name="harvester",
    help="Personal home lab information collection control plane",
    add_completion=False,
)


def _get_base_url() -> str:
    return os.environ.get("HARVESTER_API_URL", "http://localhost:8000")


def _get_token() -> str:
    return os.environ.get("HARVESTER_API_TOKEN", "")


def _api_headers() -> dict[str, str]:
    token = _get_token()
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


@app.callback(invoke_without_command=True)
def health(
    base_url: str = typer.Option(
        None,
        "--base-url",
        help="Base URL of the Harvester API",
    ),
) -> None:
    """Check the health of the Harvester API."""
    url = (base_url or _get_base_url()) + "/health"
    try:
        response = httpx.get(url, timeout=5.0)
        if response.status_code == 200:
            typer.echo(f"API is healthy: {response.json()}")
        else:
            typer.echo(f"API returned status {response.status_code}")
            raise typer.Exit(code=1)
    except httpx.ConnectError as e:
        typer.echo(f"Failed to connect to API at {url}: {e}")
        raise typer.Exit(code=1) from None
    except Exception as e:
        typer.echo(f"Error checking API health: {e}")
        raise typer.Exit(code=1) from None


# --- Source subcommands ---

source_app = typer.Typer(help="Source management")
app.add_typer(source_app, name="source")


@source_app.command("propose")
def source_propose(
    name: str = typer.Option(..., "--name", help="Source name"),
    kind: str = typer.Option("web", "--kind", help="Source kind"),
    url: str = typer.Option(None, "--url", help="Source URL"),
) -> None:
    """Propose a new candidate source."""
    payload = {"name": name, "kind": kind}
    if url:
        payload["url"] = url
    try:
        response = httpx.post(
            f"{_get_base_url()}/sources/propose",
            json=payload,
            headers=_api_headers(),
            timeout=10.0,
        )
        if response.status_code == 201:
            data = response.json()
            typer.echo(f"Source proposed: {data['id']} ({data['name']}) status={data['status']}")
        else:
            typer.echo(f"Error: {response.status_code} {response.text}")
            raise typer.Exit(code=1)
    except httpx.ConnectError as e:
        typer.echo(f"Failed to connect to API: {e}")
        raise typer.Exit(code=1) from None


@source_app.command("promote")
def source_promote(
    source_id: str = typer.Argument(..., help="Source ID to promote"),
) -> None:
    """Promote a candidate source."""
    try:
        response = httpx.post(
            f"{_get_base_url()}/sources/{source_id}/promote",
            headers=_api_headers(),
            timeout=10.0,
        )
        if response.status_code == 200:
            data = response.json()
            typer.echo(f"Source promoted: {data['id']} status={data['status']}")
        else:
            typer.echo(f"Error: {response.status_code} {response.text}")
            raise typer.Exit(code=1)
    except httpx.ConnectError as e:
        typer.echo(f"Failed to connect to API: {e}")
        raise typer.Exit(code=1) from None


# --- Topic subcommands ---

topic_app = typer.Typer(help="Topic watch management")
app.add_typer(topic_app, name="topic")


@topic_app.command("create")
def topic_create(
    name: str = typer.Option(..., "--name", help="Topic name"),
    query: str = typer.Option(None, "--query", help="Search query"),
    ttl: int = typer.Option(None, "--ttl", help="TTL in seconds"),
) -> None:
    """Create a new topic watch."""
    payload = {"name": name}
    if query:
        payload["query"] = query
    if ttl:
        payload["ttl_seconds"] = ttl
    try:
        response = httpx.post(
            f"{_get_base_url()}/topics",
            json=payload,
            headers=_api_headers(),
            timeout=10.0,
        )
        if response.status_code == 201:
            data = response.json()
            typer.echo(f"Topic created: {data['id']} ({data['name']}) status={data['status']}")
        else:
            typer.echo(f"Error: {response.status_code} {response.text}")
            raise typer.Exit(code=1)
    except httpx.ConnectError as e:
        typer.echo(f"Failed to connect to API: {e}")
        raise typer.Exit(code=1) from None


# --- Failures subcommands ---

failures_app = typer.Typer(help="Failure inspection")
app.add_typer(failures_app, name="failures")


@failures_app.command("recent")
def failures_recent(
    limit: int = typer.Option(20, "--limit", help="Max items per category"),
) -> None:
    """Show recent failed crawl runs and jobs."""
    try:
        response = httpx.get(
            f"{_get_base_url()}/failures/recent",
            params={"limit": limit},
            headers=_api_headers(),
            timeout=10.0,
        )
        if response.status_code == 200:
            data = response.json()
            crawls = data.get("crawl_runs", [])
            jobs = data.get("jobs", [])
            if not crawls and not jobs:
                typer.echo("No recent failures.")
                return
            if crawls:
                typer.echo(f"Failed crawl runs ({len(crawls)}):")
                for c in crawls:
                    typer.echo(f"  {c['id']} {c['error_message'] or ''}")
            if jobs:
                typer.echo(f"Failed jobs ({len(jobs)}):")
                for j in jobs:
                    typer.echo(f"  {j['id']} {j['error_message'] or ''}")
        else:
            typer.echo(f"Error: {response.status_code} {response.text}")
            raise typer.Exit(code=1)
    except httpx.ConnectError as e:
        typer.echo(f"Failed to connect to API: {e}")
        raise typer.Exit(code=1) from None


# --- Crawl subcommands ---

crawl_app = typer.Typer(help="Crawl execution")
app.add_typer(crawl_app, name="crawl")


@crawl_app.command("run")
def crawl_run(
    source_id: str = typer.Option(..., "--source-id", help="Source ID to crawl"),
    recipe_id: str = typer.Option(..., "--recipe-id", help="Recipe ID to use"),
) -> None:
    """Execute a crawl run via the API."""
    try:
        response = httpx.post(
            f"{_get_base_url()}/crawl/run",
            json={"source_id": source_id, "recipe_id": recipe_id},
            headers=_api_headers(),
            timeout=60.0,
        )
        if response.status_code == 200:
            data = response.json()
            typer.echo(
                f"Crawl run: {data['crawl_run_id']} "
                f"status={data['status']} "
                f"raw_object_id={data.get('raw_object_id', 'N/A')}"
            )
        else:
            typer.echo(f"Error: {response.status_code} {response.text}")
            raise typer.Exit(code=1)
    except httpx.ConnectError as e:
        typer.echo(f"Failed to connect to API: {e}")
        raise typer.Exit(code=1) from None


if __name__ == "__main__":
    app()
