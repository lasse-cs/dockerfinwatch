from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from textual_dockerclustermon.docker import Container, DockerQueryError


@dataclass(frozen=True)
class MonitorSnapshot:
    server_name: str
    containers: list[Container]
    updated_at: datetime


class MonitorRefreshError(Exception):
    pass


class DockerQuery(Protocol):
    def fetch(self) -> list[Container]: ...


def utc_now() -> datetime:
    return datetime.now(UTC)


class MonitorService:
    def __init__(
        self,
        server_name: str,
        docker_query: DockerQuery,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._server_name = server_name
        self._docker_query = docker_query
        self._clock = clock

    def refresh(self) -> MonitorSnapshot:
        try:
            containers = self._docker_query.fetch()
        except DockerQueryError as error:
            raise MonitorRefreshError(f"docker query failed: {error}") from error

        return MonitorSnapshot(
            server_name=self._server_name,
            containers=containers,
            updated_at=self._clock(),
        )
