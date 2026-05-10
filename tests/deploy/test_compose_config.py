"""Tests for docker-compose.yml — verify it defines required services and healthchecks."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).parent.parent.parent
COMPOSE_FILE = PROJECT_ROOT / "docker-compose.yml"


class TestComposeConfig:
    """Verify docker-compose.yml exists and has required service definitions."""

    def test_compose_file_exists(self):
        """docker-compose.yml must exist in the project root."""
        assert COMPOSE_FILE.is_file(), f"docker-compose.yml not found at {COMPOSE_FILE}"

    def test_compose_is_valid_yaml(self):
        """docker-compose.yml must be valid YAML."""
        content = COMPOSE_FILE.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
        assert isinstance(data, dict)

    def test_has_services_key(self):
        """docker-compose.yml must define services."""
        content = COMPOSE_FILE.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
        assert "services" in data
        assert isinstance(data["services"], dict)

    def test_has_server_service(self):
        """docker-compose.yml must define a server service."""
        content = COMPOSE_FILE.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
        assert "server" in data["services"]

    def test_has_worker_service(self):
        """docker-compose.yml must define a worker service."""
        content = COMPOSE_FILE.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
        assert "worker" in data["services"]

    def test_server_has_healthcheck(self):
        """The server service must have a healthcheck definition."""
        content = COMPOSE_FILE.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
        server = data["services"]["server"]
        assert "healthcheck" in server, "Server service missing healthcheck"

    def test_worker_has_healthcheck(self):
        """The worker service must have a healthcheck definition."""
        content = COMPOSE_FILE.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
        worker = data["services"]["worker"]
        assert "healthcheck" in worker, "Worker service missing healthcheck"

    def test_server_exposes_port(self):
        """The server service should expose a port."""
        content = COMPOSE_FILE.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
        server = data["services"]["server"]
        assert "ports" in server, "Server service should expose ports"

    def test_services_use_env_file(self):
        """Both server and worker should reference env_file config."""
        content = COMPOSE_FILE.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
        for svc_name in ("server", "worker"):
            svc = data["services"][svc_name]
            assert "env_file" in svc, f"{svc_name} service should use env_file"

    def test_worker_command_starts_worker_daemon(self):
        """Worker service command must start 'harvester worker run'."""
        content = COMPOSE_FILE.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
        worker = data["services"]["worker"]
        cmd = worker.get("command", "")
        assert "harvester worker run" in cmd, (
            f"Worker command should contain 'harvester worker run', got: {cmd}"
        )

    def test_worker_healthcheck_checks_worker_run_process(self):
        """Worker healthcheck must pgrep for the worker run process."""
        content = COMPOSE_FILE.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
        worker = data["services"]["worker"]
        hc = worker.get("healthcheck", {})
        test_cmd = hc.get("test", [])
        if isinstance(test_cmd, list):
            test_str = " ".join(test_cmd)
        else:
            test_str = str(test_cmd)
        assert "[h]arvester worker run" in test_str, (
            f"Worker healthcheck should use '[h]arvester worker run' pattern, got: {test_str}"
        )
