from datetime import UTC, datetime

import pytest

from textual_dockerclustermon.docker import Container, ContainerMetadata, DockerPsError
from textual_dockerclustermon.monitor import MonitorRefreshError, MonitorService


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
