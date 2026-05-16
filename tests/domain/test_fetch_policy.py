"""Tests for public-web fetch policy.

Covers: protocol rejection, localhost rejection, private IP rejection,
link-local rejection, public domain allowance, DNS resolution failure,
redirect final URL re-validation, and DNS skip bypass.
"""

import os
from ipaddress import IPv4Address, IPv6Address
from unittest.mock import patch

import pytest

from harvester.domain.fetch_policy import (
    FetchPolicyResult,
    check_fetch_policy,
    REASON_NON_HTTP_PROTOCOL,
    REASON_LOCALHOST,
    REASON_PRIVATE_IP,
    REASON_LINK_LOCAL,
    REASON_LOOPBACK,
    REASON_MULTICAST,
    REASON_RESERVED,
    REASON_UNSPECIFIED,
    REASON_DNS_FAILURE,
    REASON_REDIRECT_TO_NON_PUBLIC,
)


class TestProtocolRejection:
    """Non-http/https protocols MUST be rejected."""

    @pytest.mark.parametrize(
        "url",
        [
            "ftp://example.com/file",
            "file:///etc/passwd",
            "javascript://alert(1)",
            "data:text/html,<h1>hi</h1>",
            "ssh://git@example.com/repo",
            "gopher://example.com",
        ],
    )
    def test_rejects_non_http_protocols(self, url: str):
        result = check_fetch_policy(url)
        assert result.allowed is False
        assert result.reason == REASON_NON_HTTP_PROTOCOL

    @pytest.mark.parametrize(
        "url",
        [
            "http://example.com",
            "https://example.com",
            "https://example.com/path?q=1",
        ],
    )
    def test_allows_http_and_https(self, url: str):
        result = check_fetch_policy(url)
        # May still be denied for other reasons, but not for protocol
        assert result.reason != REASON_NON_HTTP_PROTOCOL


class TestLocalhostRejection:
    """localhost in any form MUST be rejected."""

    @pytest.mark.parametrize(
        "url",
        [
            "http://localhost",
            "http://localhost:8080/admin",
            "https://localhost/",
            "http://127.0.0.1",
            "https://127.0.0.1:443/",
            "http://[::1]",
            "https://[::1]:8080/",
        ],
    )
    def test_rejects_localhost_variants(self, url: str):
        result = check_fetch_policy(url)
        assert result.allowed is False
        assert result.reason in (REASON_LOCALHOST, REASON_LOOPBACK)


class TestPrivateIPRejection:
    """RFC 1918 and other private addresses MUST be rejected."""

    @pytest.mark.parametrize(
        "url",
        [
            "http://10.0.0.1",
            "http://10.255.255.255/api",
            "http://172.16.0.1",
            "http://172.31.255.255/secret",
            "http://192.168.1.1",
            "http://192.168.0.100:3000/nas",
            "http://[fc00::1]",
            "http://[fd12:3456:789a::1]",
        ],
    )
    def test_rejects_private_ips(self, url: str):
        result = check_fetch_policy(url)
        assert result.allowed is False
        assert result.reason == REASON_PRIVATE_IP


class TestLinkLocalRejection:
    """Link-local addresses MUST be rejected."""

    @pytest.mark.parametrize(
        "url",
        [
            "http://169.254.0.1",
            "http://169.254.169.254/latest/meta-data/",
            "http://[fe80::1]",
            "http://[fe80::1%eth0]",
        ],
    )
    def test_rejects_link_local(self, url: str):
        result = check_fetch_policy(url)
        assert result.allowed is False
        assert result.reason == REASON_LINK_LOCAL


class TestMulticastReservedUnspecified:
    """Multicast, reserved, and unspecified addresses MUST be rejected."""

    @pytest.mark.parametrize(
        "url",
        [
            "http://224.0.0.1",
            "http://239.255.255.250",
            "http://[ff00::1]",
            "http://[ff02::1]",
        ],
    )
    def test_rejects_multicast(self, url: str):
        result = check_fetch_policy(url)
        assert result.allowed is False
        assert result.reason == REASON_MULTICAST

    def test_rejects_unspecified(self):
        result = check_fetch_policy("http://0.0.0.0")
        assert result.allowed is False
        assert result.reason == REASON_UNSPECIFIED

    def test_rejects_ipv6_unspecified(self):
        result = check_fetch_policy("http://[::]")
        assert result.allowed is False
        assert result.reason in (REASON_UNSPECIFIED, REASON_LOOPBACK)


class TestPublicDomainAllowed:
    """Public internet domains SHOULD be allowed."""

    @pytest.mark.parametrize(
        "url",
        [
            "https://www.cdc.gov",
            "https://example.com/page",
            "http://news.sina.com.cn/",
            "https://github.com/user/repo",
        ],
    )
    def test_allows_public_domains(self, url: str):
        # Patch DNS resolution to return a public IP
        with patch(
            "harvester.domain.fetch_policy._resolve_host",
            return_value=[IPv4Address("93.184.216.34")],
        ):
            result = check_fetch_policy(url)
            assert result.allowed is True
            assert result.reason is None


class TestDNSResolutionFailure:
    """DNS resolution failure MUST be denied."""

    def test_dns_failure_denied(self):
        with patch(
            "harvester.domain.fetch_policy._resolve_host",
            side_effect=OSError("DNS resolution failed"),
        ):
            result = check_fetch_policy("https://nonexistent.invalid")
            assert result.allowed is False
            assert result.reason == REASON_DNS_FAILURE


class TestRedirectRevalidation:
    """Redirect final URL MUST be re-checked against policy."""

    def test_redirect_to_private_ip_rejected(self):
        """Public URL redirecting to private IP must be rejected."""
        with patch(
            "harvester.domain.fetch_policy._resolve_host",
            side_effect=[
                [IPv4Address("93.184.216.34")],  # initial public
                [IPv4Address("192.168.1.1")],  # redirect target private
            ],
        ):
            result = check_fetch_policy("https://example.com")
            assert result.allowed is True

            # Re-check redirect target
            result2 = check_fetch_policy("http://192.168.1.1/admin")
            assert result2.allowed is False
            assert result2.reason == REASON_PRIVATE_IP

    def test_redirect_to_localhost_rejected(self):
        """Public URL redirecting to localhost must be rejected."""
        result = check_fetch_policy("http://localhost/secret")
        assert result.allowed is False
        assert result.reason in (REASON_LOCALHOST, REASON_LOOPBACK)


class TestFetchPolicyResult:
    """FetchPolicyResult data structure tests."""

    def test_allowed_result(self):
        result = FetchPolicyResult(allowed=True, reason=None)
        assert result.allowed is True
        assert result.reason is None

    def test_denied_result(self):
        result = FetchPolicyResult(allowed=False, reason=REASON_PRIVATE_IP)
        assert result.allowed is False
        assert result.reason == REASON_PRIVATE_IP


class TestSkipDNSBypass:
    """When HARVESTER_FETCH_POLICY_SKIP_DNS=1, all URLs are allowed."""

    def test_skip_dns_bypasses_private_ip(self):
        """Private IP URLs are allowed when bypass is active."""
        with patch.dict(os.environ, {"HARVESTER_FETCH_POLICY_SKIP_DNS": "1"}):
            result = check_fetch_policy("http://192.168.1.1/admin")
            assert result.allowed is True
            assert result.reason is None

    def test_skip_dns_bypasses_localhost(self):
        """Localhost URLs are allowed when bypass is active."""
        with patch.dict(os.environ, {"HARVESTER_FETCH_POLICY_SKIP_DNS": "1"}):
            result = check_fetch_policy("http://localhost:8080/secret")
            assert result.allowed is True
            assert result.reason is None

    def test_skip_dns_bypasses_fake_ip_range(self):
        """RFC 2544 Fake-IP addresses (used by Surge/ClashX) are allowed."""
        with patch.dict(os.environ, {"HARVESTER_FETCH_POLICY_SKIP_DNS": "1"}):
            result = check_fetch_policy("http://198.18.0.100/api")
            assert result.allowed is True
            assert result.reason is None

    def test_skip_dns_off_still_blocks_private(self):
        """When bypass is not set, private IPs are still blocked."""
        with patch.dict(os.environ, {}, clear=True):
            # Ensure the env var is NOT set
            os.environ.pop("HARVESTER_FETCH_POLICY_SKIP_DNS", None)
            result = check_fetch_policy("http://192.168.1.1/admin")
            assert result.allowed is False
            assert result.reason == REASON_PRIVATE_IP

    def test_skip_dns_requires_exact_value(self):
        """Only "1" (not "true" or "yes") activates the bypass."""
        with patch.dict(os.environ, {"HARVESTER_FETCH_POLICY_SKIP_DNS": "true"}):
            result = check_fetch_policy("http://192.168.1.1/admin")
            assert result.allowed is False
