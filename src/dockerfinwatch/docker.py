import json
from dataclasses import dataclass

from dockerfinwatch.commands import CommandError, CommandRunner


DOCKER_PS_COMMAND = ["docker", "ps", "--format", "{{json .}}"]
DOCKER_STATS_COMMAND = ["docker", "stats", "--no-stream", "--format", "{{json .}}"]


@dataclass(frozen=True)
class ContainerMetadata:
    id: str
    name: str
    image: str
    status: str
    ports: str


@dataclass(frozen=True)
class ContainerStats:
    cpu_percent: str
    memory_usage: str
    memory_percent: str
    network_io: str
    block_io: str
    pids: str


@dataclass(frozen=True)
class Container:
    metadata: ContainerMetadata
    stats: ContainerStats | None


class DockerQueryError(Exception):
    pass


class DockerPsError(DockerQueryError):
    pass


class DockerStatsError(DockerQueryError):
    pass


class DockerLogsError(DockerQueryError):
    pass


class DockerPsQuery:
    def __init__(self, runner: CommandRunner, timeout_seconds: float = 20) -> None:
        self._runner = runner
        self._timeout_seconds = timeout_seconds

    def fetch(self) -> dict[str, ContainerMetadata]:
        try:
            result = self._runner.run(DOCKER_PS_COMMAND, self._timeout_seconds)
        except CommandError as error:
            raise DockerPsError(f"could not run docker ps: {error}") from error

        if result.exit_code != 0:
            raise DockerPsError(
                result.stderr or f"docker ps exited with {result.exit_code}"
            )

        containers = [
            self._container_from_line(line) for line in result.stdout.splitlines()
        ]
        return {container.id: container for container in containers}

    def _container_from_line(self, line: str) -> ContainerMetadata:
        data = json.loads(line)
        return ContainerMetadata(
            id=data["ID"],
            name=data["Names"],
            image=data["Image"],
            status=data["Status"],
            ports=data["Ports"],
        )


class DockerStatsQuery:
    def __init__(self, runner: CommandRunner, timeout_seconds: float = 20) -> None:
        self._runner = runner
        self._timeout_seconds = timeout_seconds

    def fetch(self, container_ids: list[str]) -> dict[str, ContainerStats]:
        if not container_ids:
            return {}

        command = [*DOCKER_STATS_COMMAND, *container_ids]
        try:
            result = self._runner.run(command, self._timeout_seconds)
        except CommandError as error:
            raise DockerStatsError(f"could not run docker stats: {error}") from error

        if result.exit_code != 0:
            raise DockerStatsError(
                result.stderr or f"docker stats exited with {result.exit_code}"
            )

        stats = [self._stats_from_line(line) for line in result.stdout.splitlines()]
        return {
            container_stats_id: container_stats
            for container_stats_id, container_stats in stats
        }

    def _stats_from_line(self, line: str) -> tuple[str, ContainerStats]:
        data = json.loads(line)
        return (
            data["ID"],
            ContainerStats(
                cpu_percent=data["CPUPerc"],
                memory_usage=data["MemUsage"],
                memory_percent=data["MemPerc"],
                network_io=data["NetIO"],
                block_io=data["BlockIO"],
                pids=data["PIDs"],
            ),
        )


DOCKER_LOGS_COMMAND = ["docker", "logs", "--timestamps", "--tail"]


@dataclass(frozen=True)
class DockerLogEntry:
    timestamp: str
    message: str
    stream_order: int
    line_order: int

    @property
    def rendered(self) -> str:
        if not self.timestamp:
            return self.message
        return f"{self.timestamp} {self.message}"

    @property
    def sort_key(self) -> tuple[int, str, int, int]:
        if not self.timestamp:
            return (1, self.timestamp, self.stream_order, self.line_order)
        return (0, self.timestamp, self.stream_order, self.line_order)


class DockerLogsQuery:
    def __init__(self, runner: CommandRunner, timeout_seconds: float = 20) -> None:
        self._runner = runner
        self._timeout_seconds = timeout_seconds

    def fetch(self, container_id: str, tail: int) -> str:
        command = [*DOCKER_LOGS_COMMAND, str(tail), container_id]
        try:
            result = self._runner.run(command, self._timeout_seconds)
        except CommandError as error:
            raise DockerLogsError(f"could not run docker logs: {error}") from error

        if result.exit_code != 0:
            raise DockerLogsError(
                result.stderr or f"docker logs exited with {result.exit_code}"
            )

        entries = [
            *self._log_entries(result.stdout, stream_order=0),
            *self._log_entries(result.stderr, stream_order=1),
        ]
        if not entries:
            return ""

        return (
            "\n".join(
                entry.rendered for entry in sorted(entries, key=lambda e: e.sort_key)
            )
            + "\n"
        )

    def _log_entries(self, output: str, stream_order: int) -> list[DockerLogEntry]:
        entries = []
        for line_order, line in enumerate(output.splitlines()):
            timestamp, separator, message = line.partition(" ")
            if not separator:
                timestamp = ""
                message = line
            entries.append(
                DockerLogEntry(
                    timestamp=timestamp,
                    message=message,
                    stream_order=stream_order,
                    line_order=line_order,
                )
            )
        return entries


class DockerContainerQuery:
    def __init__(
        self,
        ps_query: DockerPsQuery,
        enrichment_queries: list[DockerStatsQuery],
    ) -> None:
        self._ps_query = ps_query
        self._enrichment_queries = enrichment_queries

    def fetch(self) -> list[Container]:
        metadata_by_id = self._ps_query.fetch()
        container_ids = list(metadata_by_id)
        stats_by_id: dict[str, ContainerStats] = {}

        for query in self._enrichment_queries:
            stats_by_id.update(query.fetch(container_ids))

        return [
            Container(metadata=metadata, stats=stats_by_id.get(container_id))
            for container_id, metadata in metadata_by_id.items()
        ]
