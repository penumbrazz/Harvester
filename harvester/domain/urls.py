"""URL normalization utilities for the Harvester pipeline.

Provides deterministic URL normalization so that equivalent URLs (varying only
in tracking parameters, fragment identifiers, case, or query order) collapse
to a single canonical form.
"""

from __future__ import annotations

import hashlib
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

# Tracking query parameters that should be stripped during normalization.
TRACKING_PARAMS: set[str] = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_content",
    "utm_term",
    "fbclid",
    "gclid",
    "ref",
    "ref_src",
    "source",
}


def normalize_url(url: str) -> str:
    """Return a canonical normalized form of *url*.

    Normalization steps:
    1. Lowercase the scheme and hostname.
    2. Remove the fragment identifier.
    3. Strip known tracking query parameters.
    4. Sort remaining query parameters for deterministic ordering.
    5. Remove trailing ``?`` if no query params remain.

    Parameters
    ----------
    url : str
        Absolute URL to normalize.

    Returns
    -------
    str
        The normalized URL.

    Raises
    ------
    ValueError
        If *url* is empty or does not contain a valid scheme.
    """
    if not url or not url.strip():
        raise ValueError("URL must not be empty")

    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Invalid URL (missing scheme or host): {url!r}")

    # Lowercase scheme and host.
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    # Strip tracking parameters and sort the rest.
    params = parse_qs(parsed.query, keep_blank_values=True)
    cleaned = {k: v for k, v in params.items() if k not in TRACKING_PARAMS}
    # Sort by key for deterministic output; use flat value for single-item lists.
    sorted_query = urlencode(
        sorted(cleaned.items(), key=lambda pair: pair[0]),
        doseq=True,
    )

    # Reassemble without fragment.
    return urlunparse((scheme, netloc, parsed.path, parsed.params, sorted_query, ""))


def compute_canonical_url_hash(url: str) -> str:
    """Return the SHA-256 hex digest of the normalized URL.

    Parameters
    ----------
    url : str
        Absolute URL to hash.

    Returns
    -------
    str
        64-character lowercase hex string.
    """
    normalized = normalize_url(url)
    return hashlib.sha256(normalized.encode()).hexdigest()
