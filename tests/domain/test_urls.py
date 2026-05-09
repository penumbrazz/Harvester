"""Tests for URL normalization — harvester.domain.urls."""

import hashlib

import pytest

from harvester.domain.urls import TRACKING_PARAMS, compute_canonical_url_hash, normalize_url


# ---------------------------------------------------------------------------
# normalize_url
# ---------------------------------------------------------------------------


class TestNormalizeUrl:
    """Test suite for normalize_url()."""

    def test_lowercase_scheme_and_host(self):
        """Scheme and host must be lowercased."""
        result = normalize_url("HTTPS://EXAMPLE.COM/path")
        assert result.startswith("https://example.com/path")

    def test_fragment_removed(self):
        """Fragment identifiers must be stripped."""
        result = normalize_url("https://example.com/page#section-1")
        assert "#" not in result
        assert result == "https://example.com/page"

    def test_tracking_params_removed(self):
        """Known tracking query parameters must be stripped."""
        url = (
            "https://example.com/article?"
            "utm_source=twitter&utm_medium=social&"
            "utm_campaign=spring&fbclid=abc123&"
            "key=value"
        )
        result = normalize_url(url)
        assert "utm_source" not in result
        assert "utm_medium" not in result
        assert "utm_campaign" not in result
        assert "fbclid" not in result
        assert "key=value" in result

    def test_all_tracking_params_recognized(self):
        """Every entry in TRACKING_PARAMS must be stripped."""
        params = "&".join(f"{p}=1" for p in TRACKING_PARAMS)
        url = f"https://example.com/page?{params}&keep=yes"
        result = normalize_url(url)
        for p in TRACKING_PARAMS:
            assert f"{p}=" not in result
        assert "keep=yes" in result

    def test_query_params_sorted(self):
        """Query parameters must appear in sorted (deterministic) order."""
        url = "https://example.com/search?zebra=1&alpha=2&middle=3"
        result = normalize_url(url)
        # alpha should come before middle, middle before zebra
        idx_alpha = result.index("alpha=")
        idx_middle = result.index("middle=")
        idx_zebra = result.index("zebra=")
        assert idx_alpha < idx_middle < idx_zebra

    def test_no_query_or_fragment_unchanged(self):
        """URLs without query params or fragments stay the same (except lowercasing)."""
        url = "https://example.com/simple/path"
        assert normalize_url(url) == url

    def test_empty_query_string_removed(self):
        """A trailing '?' with no params should be removed."""
        result = normalize_url("https://example.com/page?")
        assert not result.endswith("?")

    def test_all_params_are_tracking_params_removed(self):
        """If all query params are tracking params, the query string is fully removed."""
        url = "https://example.com/page?utm_source=rss"
        result = normalize_url(url)
        assert "?" not in result

    def test_path_preserved(self):
        """URL path must not be altered."""
        url = "https://example.com/deep/nested/path.html"
        assert normalize_url(url) == url

    def test_mixed_case_host_normalized(self):
        """Mixed-case hosts are fully lowercased."""
        result = normalize_url("https://Example.Co.UK/article")
        assert result.startswith("https://example.co.uk/article")

    def test_port_preserved(self):
        """Port numbers should be preserved."""
        result = normalize_url("https://example.com:8443/path")
        assert ":8443" in result

    def test_invalid_url_raises_value_error(self):
        """Malformed URLs must raise ValueError."""
        with pytest.raises(ValueError):
            normalize_url("")

    def test_no_scheme_raises_value_error(self):
        """URLs without a scheme must raise ValueError."""
        with pytest.raises(ValueError):
            normalize_url("example.com/path")


# ---------------------------------------------------------------------------
# compute_canonical_url_hash
# ---------------------------------------------------------------------------


class TestComputeCanonicalUrlHash:
    """Test suite for compute_canonical_url_hash()."""

    def test_returns_sha256_hex(self):
        """Must return a 64-char hex string (SHA-256)."""
        h = compute_canonical_url_hash("https://example.com/page")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_deterministic(self):
        """Same input always produces the same hash."""
        url = "https://example.com/page?a=1&b=2"
        assert compute_canonical_url_hash(url) == compute_canonical_url_hash(url)

    def test_normalizes_before_hashing(self):
        """URLs that normalize to the same value must produce the same hash."""
        url1 = "https://EXAMPLE.COM/page?b=2&a=1#frag"
        url2 = "https://example.com/page?a=1&b=2"
        assert compute_canonical_url_hash(url1) == compute_canonical_url_hash(url2)

    def test_different_urls_different_hash(self):
        """Different URLs must produce different hashes."""
        h1 = compute_canonical_url_hash("https://example.com/a")
        h2 = compute_canonical_url_hash("https://example.com/b")
        assert h1 != h2

    def test_matches_manual_hash(self):
        """Hash must match a manually computed SHA-256 of the normalized URL."""
        url = "https://example.com/page"
        normalized = normalize_url(url)
        expected = hashlib.sha256(normalized.encode()).hexdigest()
        assert compute_canonical_url_hash(url) == expected


# ---------------------------------------------------------------------------
# TRACKING_PARAMS constant
# ---------------------------------------------------------------------------


class TestTrackingParams:
    """Verify the TRACKING_PARAMS set contains all expected entries."""

    EXPECTED = {
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

    def test_contains_all_expected(self):
        """TRACKING_PARAMS must include all required tracking parameter names."""
        assert self.EXPECTED.issubset(TRACKING_PARAMS)
