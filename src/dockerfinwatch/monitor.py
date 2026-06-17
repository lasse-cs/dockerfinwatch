from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from dockerfinwatch.docker import Container, DockerLogsError, DockerQueryError


@dataclass(frozen=True)
class MonitorSnapshot:
    server_name: str
    containers: list[Container]
    updated_at: datetime


class MonitorRefreshError(Exception):
    pass


class MonitorLogsError(Exception):
    pass


class DockerQuery(Protocol):
    def fetch(self) -> list[Container]: ...


class LogsQuery(Protocol):
    def fetch(self, container_id: str, tail: int) -> str: ...


def utc_now() -> datetime:
    return datetime.now(UTC)


class MonitorService:
    def __init__(
        self,
        server_name: str,
        docker_query: DockerQuery,
        logs_query: LogsQuery | None = None,
        cleanup: Callable[[], None] | None = None,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._server_name = server_name
        self._docker_query = docker_query
        self._logs_query = logs_query
        self._cleanup = cleanup
        self._clock = clock

    @property
    def server_name(self) -> str:
        return self._server_name

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

    def fetch_logs(self, container_id: str, tail: int) -> str:
        if self._logs_query is None:
            raise MonitorLogsError("no logs query configured")
        try:
            return self._logs_query.fetch(container_id, tail=tail)
        except DockerLogsError as error:
            raise MonitorLogsError(f"docker logs failed: {error}") from error

    def close(self) -> None:
        if self._cleanup is None:
            return
        cleanup = self._cleanup
        self._cleanup = None
        cleanup()
