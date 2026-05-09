"""Stub Firecrawl adapter that returns fixture content instead of making network calls."""

from __future__ import annotations

from pathlib import Path


class StubFirecrawlAdapter:
    """Stub adapter for testing — returns pre-configured fixture content.

    This adapter never makes network calls. Instead, it serves content from
    an in-memory fixture map populated at construction time.
    """

    def __init__(self, fixtures: dict[str, str] | None = None) -> None:
        self._fixtures: dict[str, str] = fixtures or {}

    def crawl(self, url: str) -> str | None:
        """Return fixture content for *url*, or ``None`` if unknown.

        Parameters
        ----------
        url : str
            The URL to "crawl".

        Returns
        -------
        str or None
            The fixture content for the URL, or ``None``.
        """
        return self._fixtures.get(url)

    @classmethod
    def from_fixture_dir(cls, fixture_dir: str) -> StubFirecrawlAdapter:
        """Load all .html and .json files from *fixture_dir* as fixtures.

        Each file is loaded with its absolute path as the key (without
        extension) and the file contents as the value.  The key format is
        ``file://<absolute-path-stem>`` so tests can look up content by
        a deterministic URL-like key.

        Parameters
        ----------
        fixture_dir : str
            Path to the directory containing fixture files.

        Returns
        -------
        StubFirecrawlAdapter
            Adapter populated with file contents keyed by ``file://`` URLs.
        """
        base = Path(fixture_dir)
        if not base.is_dir():
            return cls()

        fixtures: dict[str, str] = {}
        for path in sorted(base.iterdir()):
            if path.suffix in (".html", ".json") and path.is_file():
                key = f"file://{path.resolve()}"
                fixtures[key] = path.read_text(encoding="utf-8")

        return cls(fixtures=fixtures)
