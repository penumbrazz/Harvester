"""Direct binary HTTP fetch for non-HTML assets (e.g. PDF).

Bypasses Firecrawl and downloads raw bytes via httpx.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class BinaryFetchResult:
    """Result of a direct binary HTTP fetch."""

    payload_bytes: bytes | None = None
    content_type: str | None = None
    status_code: int | None = None
    final_url: str | None = None
    error: str | None = None


def fetch_binary(url: str, *, timeout: float = 30.0) -> BinaryFetchResult:
    """Fetch raw bytes from a URL using a direct HTTP GET.

    Returns a BinaryFetchResult regardless of success or failure.
    """
    try:
        response = httpx.get(url, timeout=timeout, follow_redirects=True)
    except httpx.TimeoutException as exc:
        return BinaryFetchResult(error=f"Request timed out: {exc}")
    except httpx.HTTPError as exc:
        return BinaryFetchResult(error=f"HTTP error: {exc}")

    if response.status_code >= 400:
        return BinaryFetchResult(
            status_code=response.status_code,
            error=f"HTTP {response.status_code}",
        )

    content_type = response.headers.get("content-type", "application/octet-stream")
    # Strip parameters (e.g. "application/pdf; charset=utf-8")
    content_type = content_type.split(";", 1)[0].strip()

    return BinaryFetchResult(
        payload_bytes=response.content,
        content_type=content_type,
        status_code=response.status_code,
        final_url=str(response.url),
    )
