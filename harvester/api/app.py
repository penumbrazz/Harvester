"""Harvester FastAPI application."""

from fastapi import FastAPI


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    app = FastAPI(
        title="Harvester",
        description="Personal home lab information collection control plane",
        version="0.1.0",
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Health check endpoint.

        Returns:
            Dictionary with status key.
        """
        return {"status": "ok"}

    return app
