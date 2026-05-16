"""Recipe-scoped validation for discovered crawl targets."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class DiscoveryScope:
    """Allowed discovery bounds parsed from recipe config."""

    enabled: bool
    allowed_hosts: tuple[str, ...]
    allowed_path_prefixes: tuple[str, ...]
    allowed_content_types: tuple[str, ...]
    max_depth: int
    max_targets_per_run: int


@dataclass(frozen=True)
class DiscoveryDecision:
    """Result of validating a discovered target."""

    allowed: bool
    reason: str | None = None


def parse_discovery_scope(config: dict | None) -> DiscoveryScope:
    """Parse discovery configuration into a strict validation scope."""
    raw = (config or {}).get("discovery") or {}
    enabled = bool(raw.get("enabled", False))
    allowed_hosts = tuple(
        str(host).lower() for host in raw.get("allowed_hosts", []) if str(host).strip()
    )
    allowed_path_prefixes = tuple(
        str(prefix)
        for prefix in raw.get("allowed_path_prefixes", [])
        if str(prefix).strip()
    )
    allowed_content_types = tuple(
        _normalize_content_type(str(content_type))
        for content_type in raw.get("allowed_content_types", [])
        if str(content_type).strip()
    )
    return DiscoveryScope(
        enabled=enabled,
        allowed_hosts=allowed_hosts,
        allowed_path_prefixes=allowed_path_prefixes,
        allowed_content_types=allowed_content_types,
        max_depth=int(raw.get("max_depth", 0)),
        max_targets_per_run=int(raw.get("max_targets_per_run", 0)),
    )


def validate_discovered_target(
    scope: DiscoveryScope,
    *,
    target_url: str,
    content_type: str,
    depth: int,
    targets_seen: int,
) -> DiscoveryDecision:
    """Validate a discovered URL against the parsed recipe discovery scope."""
    if not scope.enabled:
        return DiscoveryDecision(False, "discovery_disabled")

    parsed = urlparse(target_url)
    host = (parsed.hostname or "").lower()
    if not host or host not in scope.allowed_hosts:
        return DiscoveryDecision(False, "host_not_allowed")

    if not any(
        parsed.path.startswith(prefix) for prefix in scope.allowed_path_prefixes
    ):
        return DiscoveryDecision(False, "path_not_allowed")

    normalized_content_type = _normalize_content_type(content_type)
    if normalized_content_type not in scope.allowed_content_types:
        return DiscoveryDecision(False, "content_type_not_allowed")

    if depth > scope.max_depth:
        return DiscoveryDecision(False, "depth_exceeded")

    if targets_seen >= scope.max_targets_per_run:
        return DiscoveryDecision(False, "target_limit_exceeded")

    return DiscoveryDecision(True)


def _normalize_content_type(content_type: str) -> str:
    """Return the lowercase media type without optional parameters."""
    return content_type.split(";", 1)[0].strip().lower()
