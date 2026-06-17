from datetime import UTC, datetime

import pytest

from dockerfinwatch.docker import Container, ContainerMetadata, DockerLogsError, DockerPsError
from dockerfinwatch.monitor import MonitorLogsError, MonitorRefreshError, MonitorService


class FakeDockerPsQuery:
    def __init__(self, containers: list[Container]) -> None:
        self.containers = containers
        self.fetch_count = 0

    def fetch(self) -> list[Container]:
        self.fetch_count += 1
        return self.containers


class FailingDockerPsQuery:
    def fetch(self) -> list[Container]:
        raise DockerPsError("permission denied")


class FakeLogsQuery:
    def __init__(self, logs: str = "") -> None:
        self.logs = logs
        self.calls: list[tuple[str, int]] = []

    def fetch(self, container_id: str, tail: int) -> str:
        self.calls.append((container_id, tail))
        return self.logs


class FailingLogsQuery:
    def fetch(self, container_id: str, tail: int) -> str:
        raise DockerLogsError("permission denied")


def test_monitor_service_returns_server_snapshot() -> None:
    containers = [
        Container(
            metadata=ContainerMetadata(
                id="abc123",
                name="web",
                image="nginx:latest",
                status="Up 2 minutes",
                ports="80/tcp",
            ),
            stats=None,
        )
    ]
    query = FakeDockerPsQuery(containers)
    updated_at = datetime(2026, 6, 8, 12, 30, tzinfo=UTC)

    snapshot = MonitorService(
        server_name="prod",
        docker_query=query,
        clock=lambda: updated_at,
    ).refresh()

    assert query.fetch_count == 1
    assert snapshot.server_name == "prod"
    assert snapshot.containers == containers
    assert snapshot.updated_at == updated_at


def test_monitor_service_wraps_docker_ps_errors() -> None:
    with pytest.raises(MonitorRefreshError) as error:
        MonitorService(
            server_name="prod",
            docker_query=FailingDockerPsQuery(),
        ).refresh()

    assert str(error.value) == "docker query failed: permission denied"
    assert isinstance(error.value.__cause__, DockerPsError)


def test_monitor_service_closes_cleanup_once() -> None:
    cleanup_calls = []
    monitor = MonitorService(
        server_name="prod",
        docker_query=FakeDockerPsQuery([]),
        cleanup=lambda: cleanup_calls.append("closed"),
    )

    monitor.close()
    monitor.close()

    assert cleanup_calls == ["closed"]


def test_monitor_service_fetch_logs_delegates_to_logs_query() -> None:
    logs_query = FakeLogsQuery(logs="line 1\nline 2\n")
    monitor = MonitorService(
        server_name="prod",
        docker_query=FakeDockerPsQuery([]),
        logs_query=logs_query,
    )

    result = monitor.fetch_logs("abc123", tail=50)

    assert logs_query.calls == [("abc123", 50)]
    assert result == "line 1\nline 2\n"


def test_monitor_service_wraps_logs_errors() -> None:
    monitor = MonitorService(
        server_name="prod",
        docker_query=FakeDockerPsQuery([]),
        logs_query=FailingLogsQuery(),
    )

    with pytest.raises(MonitorLogsError) as error:
        monitor.fetch_logs("abc123", tail=100)

    assert isinstance(error.value.__cause__, DockerLogsError)
