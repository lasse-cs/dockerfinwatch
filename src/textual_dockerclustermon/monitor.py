from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from textual_dockerclustermon.docker import Container


@dataclass(frozen=True)
class DockerPsSnapshot:
    server_name: str
    containers: list[Container]
    updated_at: datetime


class DockerPsQuery(Protocol):
    def fetch(self) -> list[Container]: ...


def utc_now() -> datetime:
    return datetime.now(UTC)


class MonitorService:
    def __init__(
        self,
        server_name: str,
        docker_ps_query: DockerPsQuery,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._server_name = server_name
        self._docker_ps_query = docker_ps_query
        self._clock = clock

    def refresh(self) -> DockerPsSnapshot:
        return DockerPsSnapshot(
            server_name=self._server_name,
            containers=self._docker_ps_query.fetch(),
            updated_at=self._clock(),
        )
