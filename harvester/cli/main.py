"""Harvester CLI application."""

import os

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
    ctx: typer.Context,
    base_url: str = typer.Option(
        None,
        "--base-url",
        help="Base URL of the Harvester API",
    ),
) -> None:
    """Check the health of the Harvester API."""
    if ctx.invoked_subcommand is not None:
        return
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
            typer.echo(
                f"Source proposed: {data['id']} ({data['name']}) status={data['status']}"
            )
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
            typer.echo(
                f"Topic created: {data['id']} ({data['name']}) status={data['status']}"
            )
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


# --- Search command ---


@app.command("search")
def search_items(
    query: str = typer.Argument(..., help="Search query keyword"),
    mode: str = typer.Option(
        "keyword", "--mode", help="Search mode: keyword or vector", case_sensitive=False
    ),
    source_id: str = typer.Option(None, "--source-id", help="Filter by source ID"),
    topic_watch_id: str = typer.Option(
        None, "--topic-watch-id", help="Filter by topic watch ID"
    ),
    limit: int = typer.Option(20, "--limit", help="Max results"),
    offset: int = typer.Option(0, "--offset", help="Pagination offset"),
) -> None:
    """Search content items by keyword or vector similarity."""
    valid_modes = ("keyword", "vector")
    mode = mode.lower()
    if mode not in valid_modes:
        typer.echo(
            f"Error: Invalid mode '{mode}'. Must be one of: {', '.join(valid_modes)}"
        )
        raise typer.Exit(code=1)
    if mode == "vector" and offset > 0:
        typer.echo("Error: --offset is not supported in vector mode")
        raise typer.Exit(code=1)
    params: dict = {"q": query, "mode": mode}
    if source_id:
        params["source_id"] = source_id
    if topic_watch_id:
        params["topic_watch_id"] = topic_watch_id
    params["limit"] = limit
    params["offset"] = offset

    try:
        response = httpx.get(
            f"{_get_base_url()}/items/search",
            params=params,
            headers=_api_headers(),
            timeout=10.0,
        )
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            if not items:
                typer.echo("No results found.")
                return
            for item in items:
                if item.get("mode") == "vector":
                    typer.echo(
                        f"  {item['title']}\n"
                        f"    chunk_id={item['chunk_id']} "
                        f"item_version_id={item['item_version_id']} "
                        f"distance={item['distance']}"
                    )
                else:
                    typer.echo(
                        f"  {item['title']}\n"
                        f"    item_id={item['item_id']} "
                        f"version_id={item['version_id']} "
                        f"source_id={item['source_id']}"
                    )
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


# --- Worker subcommands ---

worker_app = typer.Typer(help="Worker daemon commands")
app.add_typer(worker_app, name="worker")


@worker_app.command("once")
def worker_once(
    limit: int = typer.Option(10, "--limit", help="Max jobs to process"),
) -> None:
    """Run the embedding worker once and exit."""
    from harvester.adapters.stub_model import StubModelAdapter
    from harvester.workers.daemon import _make_session, run_once

    session = _make_session()
    adapter = StubModelAdapter()
    try:
        stats = run_once(session, adapter, "stub-embedding-1536", limit=limit)
        typer.echo(
            f"Worker one-shot complete: "
            f"claimed={stats['claimed']} "
            f"completed={stats['completed']} "
            f"failed={stats['failed']}"
        )
    finally:
        session.close()


@worker_app.command("run")
def worker_run(
    poll_interval: int = typer.Option(
        10, "--poll-interval", help="Seconds between polls"
    ),
    limit: int = typer.Option(10, "--limit", help="Max jobs per iteration"),
) -> None:
    """Run the embedding worker daemon in a loop."""
    from harvester.adapters.stub_model import StubModelAdapter
    from harvester.workers.daemon import _make_session, run_loop

    adapter = StubModelAdapter()
    typer.echo(
        f"Starting embedding worker daemon (poll={poll_interval}s, limit={limit})"
    )
    run_loop(
        _make_session,
        adapter,
        "stub-embedding-1536",
        poll_interval=poll_interval,
        limit=limit,
    )


if __name__ == "__main__":
    app()
