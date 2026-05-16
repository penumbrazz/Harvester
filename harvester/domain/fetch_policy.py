"""Public-web fetch policy for Harvester.

Validates that crawl targets are safe: only http/https, only public IPs,
no localhost, no private/link-local/multicast/reserved/unspecified addresses.
DNS resolution is required before allowing a target.

Reason strings are stable and machine-readable so that API, adapter,
audit, and CLI can all reference the same denial codes.
"""

from __future__ import annotations

import os
import socket
from dataclasses import dataclass
from ipaddress import IPv4Address, IPv6Address, ip_address
from urllib.parse import urlparse

# Stable reason strings for machine-readable denial codes.
REASON_NON_HTTP_PROTOCOL = "non_http_protocol"
REASON_LOCALHOST = "hostname_is_localhost"
REASON_LOOPBACK = "ip_is_loopback"
REASON_PRIVATE_IP = "ip_is_private"
REASON_LINK_LOCAL = "ip_is_link_local"
REASON_MULTICAST = "ip_is_multicast"
REASON_RESERVED = "ip_is_reserved"
REASON_UNSPECIFIED = "ip_is_unspecified"
REASON_DNS_FAILURE = "dns_resolution_failed"
REASON_REDIRECT_TO_NON_PUBLIC = "redirect_to_non_public"


@dataclass(frozen=True)
class FetchPolicyResult:
    """Result of a fetch policy check."""

    allowed: bool
    reason: str | None = None


def _resolve_host(hostname: str) -> list[IPv4Address | IPv6Address]:
    """Resolve a hostname to a list of IP addresses.

    Raises OSError on DNS failure.
    """
    infos = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
    return [ip_address(info[4][0]) for info in infos]


def _ip_is_public(addr: IPv4Address | IPv6Address) -> str | None:
    """Return a denial reason if the IP is not public, or None if allowed.

    Check order matters: more specific categories first, then the broad
    is_private catch-all. In CPython, is_private includes loopback,
    link-local, unspecified, and multicast, so we check those explicitly
    first to return the most precise reason.
    """
    if addr.is_unspecified:
        return REASON_UNSPECIFIED
    if addr.is_loopback:
        return REASON_LOOPBACK
    if addr.is_link_local:
        return REASON_LINK_LOCAL
    if addr.is_multicast:
        return REASON_MULTICAST
    if addr.is_reserved:
        return REASON_RESERVED
    if addr.is_private:
        return REASON_PRIVATE_IP
    return None


def check_fetch_policy(url: str) -> FetchPolicyResult:
    """Check whether a URL is allowed under the public-web fetch policy.

    Returns a FetchPolicyResult with allowed=True if the URL passes all
    checks, or allowed=False with a stable reason string otherwise.

    When HARVESTER_FETCH_POLICY_SKIP_DNS is set to "1", the DNS/IP check
    is bypassed entirely. This is intended for development and home-lab
    use behind a trusted proxy (e.g. Surge/ClashX in Fake-IP mode) where
    DNS returns RFC 2544 addresses that Python marks as private.
    """
    # Bypass all checks when running behind a trusted proxy.
    if os.environ.get("HARVESTER_FETCH_POLICY_SKIP_DNS", "").strip() == "1":
        return FetchPolicyResult(allowed=True, reason=None)

    parsed = urlparse(url)

    # Protocol check
    if parsed.scheme not in ("http", "https"):
        return FetchPolicyResult(allowed=False, reason=REASON_NON_HTTP_PROTOCOL)

    hostname = parsed.hostname
    if not hostname:
        return FetchPolicyResult(allowed=False, reason=REASON_NON_HTTP_PROTOCOL)

    # Localhost hostname check (before DNS)
    if hostname.lower() in ("localhost", "localhost.localdomain"):
        return FetchPolicyResult(allowed=False, reason=REASON_LOCALHOST)

    # DNS resolution
    try:
        addresses = _resolve_host(hostname)
    except OSError:
        return FetchPolicyResult(allowed=False, reason=REASON_DNS_FAILURE)

    if not addresses:
        return FetchPolicyResult(allowed=False, reason=REASON_DNS_FAILURE)

    # Check all resolved addresses
    for addr in addresses:
        denial = _ip_is_public(addr)
        if denial:
            return FetchPolicyResult(allowed=False, reason=denial)

    return FetchPolicyResult(allowed=True)
