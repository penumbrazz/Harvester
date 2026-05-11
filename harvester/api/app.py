"""Harvester FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Harvester",
        description="Personal home lab information collection control plane",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    from harvester.api.routers import (
        audit,
        content_items,
        crawl,
        dashboard,
        failures,
        queue,
        recipes,
        schedules,
        search,
        sources,
        topics,
    )

    app.include_router(sources.router)
    app.include_router(topics.router)
    app.include_router(recipes.router)
    app.include_router(failures.router)
    app.include_router(crawl.router)
    app.include_router(search.router)
    app.include_router(content_items.router)
    app.include_router(schedules.router)
    app.include_router(queue.router)
    app.include_router(dashboard.router)
    app.include_router(audit.router)

    return app
