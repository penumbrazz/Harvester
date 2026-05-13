"""Tests for docker-compose.yml — verify it defines required services and healthchecks."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).parent.parent.parent
COMPOSE_FILE = PROJECT_ROOT / "docker-compose.yml"


def _load_compose() -> dict:
    """Load and parse docker-compose.yml once per test session."""
    return yaml.safe_load(COMPOSE_FILE.read_text(encoding="utf-8"))


def _healthcheck_str(hc: dict) -> str:
    """Extract a comparable string from a healthcheck test field."""
    test_cmd = hc.get("test", [])
    if isinstance(test_cmd, list):
        return " ".join(test_cmd)
    return str(test_cmd)


@pytest.fixture(scope="class")
def compose_data():
    """Parse docker-compose.yml once for all tests in a class."""
    assert COMPOSE_FILE.is_file(), f"docker-compose.yml not found at {COMPOSE_FILE}"
    return _load_compose()


class TestComposeConfig:
    """Verify docker-compose.yml exists and has required service definitions."""

    def test_compose_file_exists(self):
        """docker-compose.yml must exist in the project root."""
        assert COMPOSE_FILE.is_file(), f"docker-compose.yml not found at {COMPOSE_FILE}"

    def test_compose_is_valid_yaml(self, compose_data):
        """docker-compose.yml must be valid YAML."""
        assert isinstance(compose_data, dict)

    def test_has_services_key(self, compose_data):
        """docker-compose.yml must define services."""
        assert "services" in compose_data
        assert isinstance(compose_data["services"], dict)

    def test_has_server_service(self, compose_data):
        """docker-compose.yml must define a server service."""
        assert "server" in compose_data["services"]

    def test_has_worker_service(self, compose_data):
        """docker-compose.yml must define a worker service."""
        assert "worker" in compose_data["services"]

    def test_server_has_healthcheck(self, compose_data):
        """The server service must have a healthcheck definition."""
        server = compose_data["services"]["server"]
        assert "healthcheck" in server, "Server service missing healthcheck"

    def test_worker_has_healthcheck(self, compose_data):
        """The worker service must have a healthcheck definition."""
        worker = compose_data["services"]["worker"]
        assert "healthcheck" in worker, "Worker service missing healthcheck"

    def test_server_exposes_port(self, compose_data):
        """The server service should expose a port."""
        server = compose_data["services"]["server"]
        assert "ports" in server, "Server service should expose ports"

    def test_services_use_env_file(self, compose_data):
        """Both server and worker should reference env_file config."""
        for svc_name in ("server", "worker"):
            svc = compose_data["services"][svc_name]
            assert "env_file" in svc, f"{svc_name} service should use env_file"

    def test_worker_command_starts_worker_daemon(self, compose_data):
        """Worker service command must start 'harvester worker run'."""
        worker = compose_data["services"]["worker"]
        cmd = worker.get("command", "")
        assert "harvester worker run" in cmd, (
            f"Worker command should contain 'harvester worker run', got: {cmd}"
        )

    def test_worker_healthcheck_checks_worker_run_process(self, compose_data):
        """Worker healthcheck must pgrep for the worker run process."""
        worker = compose_data["services"]["worker"]
        hc = worker.get("healthcheck", {})
        test_str = _healthcheck_str(hc)
        assert "[h]arvester worker run" in test_str, (
            f"Worker healthcheck should use '[h]arvester worker run' pattern, got: {test_str}"
        )

    def test_has_scheduler_service(self, compose_data):
        """docker-compose.yml must define a scheduler service."""
        assert "scheduler" in compose_data["services"]

    def test_has_crawl_worker_service(self, compose_data):
        """docker-compose.yml must define a crawl-worker service."""
        assert "crawl-worker" in compose_data["services"]

    def test_scheduler_command_starts_scheduler_daemon(self, compose_data):
        """Scheduler service command must start 'harvester scheduler daemon'."""
        scheduler = compose_data["services"]["scheduler"]
        cmd = scheduler.get("command", "")
        assert "harvester scheduler daemon" in cmd, (
            f"Scheduler command should contain 'harvester scheduler daemon', got: {cmd}"
        )

    def test_crawl_worker_command_starts_crawl_worker(self, compose_data):
        """Crawl-worker service command must start 'harvester worker run --job-type crawl'."""
        crawl_worker = compose_data["services"]["crawl-worker"]
        cmd = crawl_worker.get("command", "")
        assert "harvester worker run --job-type crawl" in cmd, (
            f"Crawl-worker command should contain 'harvester worker run --job-type crawl', got: {cmd}"
        )

    def test_scheduler_has_env_file(self, compose_data):
        """Scheduler service should use env_file config."""
        scheduler = compose_data["services"]["scheduler"]
        assert "env_file" in scheduler

    def test_crawl_worker_has_env_file(self, compose_data):
        """Crawl-worker service should use env_file config."""
        crawl_worker = compose_data["services"]["crawl-worker"]
        assert "env_file" in crawl_worker

    def test_scheduler_depends_on_server(self, compose_data):
        """Scheduler service should depend on the server service."""
        scheduler = compose_data["services"]["scheduler"]
        depends = scheduler.get("depends_on", {})
        assert "server" in depends

    def test_crawl_worker_depends_on_server(self, compose_data):
        """Crawl-worker service should depend on the server service."""
        crawl_worker = compose_data["services"]["crawl-worker"]
        depends = crawl_worker.get("depends_on", {})
        assert "server" in depends

    def test_scheduler_has_healthcheck(self, compose_data):
        """Scheduler service must have a healthcheck definition."""
        scheduler = compose_data["services"]["scheduler"]
        assert "healthcheck" in scheduler

    def test_crawl_worker_has_healthcheck(self, compose_data):
        """Crawl-worker service must have a healthcheck definition."""
        crawl_worker = compose_data["services"]["crawl-worker"]
        assert "healthcheck" in crawl_worker

    def test_scheduler_healthcheck_checks_scheduler_daemon(self, compose_data):
        """Scheduler healthcheck must pgrep for scheduler daemon process."""
        scheduler = compose_data["services"]["scheduler"]
        hc = scheduler.get("healthcheck", {})
        test_str = _healthcheck_str(hc)
        assert "scheduler" in test_str, (
            f"Scheduler healthcheck should reference 'scheduler', got: {test_str}"
        )

    def test_crawl_worker_healthcheck_checks_crawl_worker(self, compose_data):
        """Crawl-worker healthcheck must pgrep for crawl worker process."""
        crawl_worker = compose_data["services"]["crawl-worker"]
        hc = crawl_worker.get("healthcheck", {})
        test_str = _healthcheck_str(hc)
        assert "crawl" in test_str, (
            f"Crawl-worker healthcheck should reference 'crawl', got: {test_str}"
        )

    def test_services_have_distinct_healthchecks(self, compose_data):
        """scheduler, crawl-worker and worker healthchecks must be distinct."""
        hcs = {}
        for svc_name in ("scheduler", "crawl-worker", "worker"):
            svc = compose_data["services"][svc_name]
            hc = svc.get("healthcheck", {})
            hcs[svc_name] = _healthcheck_str(hc)
        assert hcs["scheduler"] != hcs["worker"]
        assert hcs["crawl-worker"] != hcs["worker"]
        assert hcs["scheduler"] != hcs["crawl-worker"]
