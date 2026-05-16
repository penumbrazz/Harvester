"""Tests for recipe-scoped target discovery validation."""

from harvester.domain.discovery_scope import (
    parse_discovery_scope,
    validate_discovered_target,
)


def _config() -> dict:
    return {
        "discovery": {
            "enabled": True,
            "max_depth": 2,
            "max_targets_per_run": 2,
            "allowed_hosts": ["www.chinacdc.cn"],
            "allowed_path_prefixes": ["/jksj/jksj04_14249/"],
            "allowed_content_types": ["text/html", "application/pdf"],
        }
    }


class TestDiscoveryScope:
    """Tests for discovery scope parsing and URL validation."""

    def test_allows_url_inside_scope(self):
        """A URL that matches host, path, content type, depth and limit is allowed."""
        # Arrange
        scope = parse_discovery_scope(_config())

        # Act
        decision = validate_discovered_target(
            scope,
            target_url="https://www.chinacdc.cn/jksj/jksj04_14249/202605/t.html",
            content_type="text/html; charset=utf-8",
            depth=1,
            targets_seen=1,
        )

        # Assert
        assert decision.allowed is True
        assert decision.reason is None

    def test_rejects_when_discovery_disabled(self):
        """Missing or disabled discovery config should reject targets."""
        # Arrange
        scope = parse_discovery_scope({})

        # Act
        decision = validate_discovered_target(
            scope,
            target_url="https://www.chinacdc.cn/jksj/jksj04_14249/202605/t.html",
            content_type="text/html",
            depth=1,
            targets_seen=0,
        )

        # Assert
        assert decision.allowed is False
        assert decision.reason == "discovery_disabled"

    def test_rejects_host_outside_allowlist(self):
        """A target host must match recipe allowed_hosts."""
        # Arrange
        scope = parse_discovery_scope(_config())

        # Act
        decision = validate_discovered_target(
            scope,
            target_url="https://evil.example/jksj/jksj04_14249/202605/t.html",
            content_type="text/html",
            depth=1,
            targets_seen=0,
        )

        # Assert
        assert decision.allowed is False
        assert decision.reason == "host_not_allowed"

    def test_rejects_path_outside_allowlist(self):
        """A target path must match at least one allowed path prefix."""
        # Arrange
        scope = parse_discovery_scope(_config())

        # Act
        decision = validate_discovered_target(
            scope,
            target_url="https://www.chinacdc.cn/other/t.html",
            content_type="text/html",
            depth=1,
            targets_seen=0,
        )

        # Assert
        assert decision.allowed is False
        assert decision.reason == "path_not_allowed"

    def test_rejects_content_type_outside_allowlist(self):
        """A target content type must match recipe allowed_content_types."""
        # Arrange
        scope = parse_discovery_scope(_config())

        # Act
        decision = validate_discovered_target(
            scope,
            target_url="https://www.chinacdc.cn/jksj/jksj04_14249/file.zip",
            content_type="application/zip",
            depth=1,
            targets_seen=0,
        )

        # Assert
        assert decision.allowed is False
        assert decision.reason == "content_type_not_allowed"

    def test_rejects_depth_above_max_depth(self):
        """A target deeper than max_depth should be rejected."""
        # Arrange
        scope = parse_discovery_scope(_config())

        # Act
        decision = validate_discovered_target(
            scope,
            target_url="https://www.chinacdc.cn/jksj/jksj04_14249/202605/t.html",
            content_type="text/html",
            depth=3,
            targets_seen=0,
        )

        # Assert
        assert decision.allowed is False
        assert decision.reason == "depth_exceeded"

    def test_rejects_after_max_targets_per_run(self):
        """A run should not admit more discovered targets than configured."""
        # Arrange
        scope = parse_discovery_scope(_config())

        # Act
        decision = validate_discovered_target(
            scope,
            target_url="https://www.chinacdc.cn/jksj/jksj04_14249/202605/t.html",
            content_type="text/html",
            depth=1,
            targets_seen=2,
        )

        # Assert
        assert decision.allowed is False
        assert decision.reason == "target_limit_exceeded"
