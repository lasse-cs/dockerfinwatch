from collections.abc import Sequence
from types import TracebackType
from typing import Self

import pytest

from textual_dockerclustermon.commands import CommandConnectionError, CommandResult
from textual_dockerclustermon.docker import (
    DockerContainerQuery,
    DockerPsError,
    DockerPsQuery,
    DockerStatsQuery,
)


class FakeRunner:
    def __init__(self, result: CommandResult) -> None:
        self.result = result
        self.commands: list[list[str]] = []

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        pass

    def run(self, command: Sequence[str], timeout_seconds: float) -> CommandResult:
        self.commands.append(list(command))
        return self.result


class SequenceRunner:
    def __init__(self, results: list[CommandResult]) -> None:
        self.results = results
        self.commands: list[list[str]] = []

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        pass

    def run(self, command: Sequence[str], timeout_seconds: float) -> CommandResult:
        self.commands.append(list(command))
        return self.results.pop(0)


class FailingRunner:
    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        pass

    def run(self, command: Sequence[str], timeout_seconds: float) -> CommandResult:
        raise CommandConnectionError("authentication failed")


def test_docker_ps_query_returns_containers_from_json_lines() -> None:
    runner = FakeRunner(
        CommandResult(
            stdout=(
                '{"ID":"abc123","Image":"nginx:latest","Names":"web","Ports":"80/tcp","Status":"Up 2 minutes"}\n'
                '{"ID":"def456","Image":"redis:7","Names":"cache","Ports":"6379/tcp","Status":"Up 1 hour"}\n'
            ),
            stderr="",
            exit_code=0,
        )
    )

    metadata_by_id = DockerPsQuery(runner).fetch()

    assert runner.commands == [["docker", "ps", "--format", "{{json .}}"]]
    assert metadata_by_id["abc123"].id == "abc123"
    assert metadata_by_id["abc123"].name == "web"
    assert metadata_by_id["abc123"].image == "nginx:latest"
    assert metadata_by_id["abc123"].ports == "80/tcp"
    assert metadata_by_id["abc123"].status == "Up 2 minutes"
    assert metadata_by_id["def456"].id == "def456"
    assert metadata_by_id["def456"].name == "cache"


def test_docker_container_query_enriches_ps_containers_with_stats() -> None:
    runner = SequenceRunner(
        [
            CommandResult(
                stdout=(
                    '{"ID":"abc123","Image":"nginx:latest","Names":"web","Ports":"80/tcp","Status":"Up 2 minutes"}\n'
                    '{"ID":"def456","Image":"redis:7","Names":"cache","Ports":"6379/tcp","Status":"Up 1 hour"}\n'
                ),
                stderr="",
                exit_code=0,
            ),
            CommandResult(
                stdout=(
                    '{"ID":"abc123","CPUPerc":"1.23%","MemUsage":"10MiB / 1GiB","MemPerc":"0.98%","NetIO":"1kB / 2kB","BlockIO":"0B / 0B","PIDs":"4"}\n'
                    '{"ID":"def456","CPUPerc":"0.10%","MemUsage":"20MiB / 1GiB","MemPerc":"1.95%","NetIO":"3kB / 4kB","BlockIO":"5kB / 6kB","PIDs":"8"}\n'
                ),
                stderr="",
                exit_code=0,
            ),
        ]
    )

    containers = DockerContainerQuery(
        DockerPsQuery(runner),
        [DockerStatsQuery(runner)],
    ).fetch()

    assert runner.commands == [
        ["docker", "ps", "--format", "{{json .}}"],
        [
            "docker",
            "stats",
            "--no-stream",
            "--format",
            "{{json .}}",
            "abc123",
            "def456",
        ],
    ]
    assert containers[0].metadata.name == "web"
    assert containers[0].metadata.image == "nginx:latest"
    assert containers[0].stats is not None
    assert containers[0].stats.cpu_percent == "1.23%"
    assert containers[0].stats.memory_usage == "10MiB / 1GiB"
    assert containers[0].stats.memory_percent == "0.98%"
    assert containers[0].stats.network_io == "1kB / 2kB"
    assert containers[0].stats.block_io == "0B / 0B"
    assert containers[0].stats.pids == "4"


def test_docker_container_query_skips_stats_when_no_containers_exist() -> None:
    runner = SequenceRunner([CommandResult(stdout="", stderr="", exit_code=0)])

    containers = DockerContainerQuery(
        DockerPsQuery(runner),
        [DockerStatsQuery(runner)],
    ).fetch()

    assert containers == []
    assert runner.commands == [["docker", "ps", "--format", "{{json .}}"]]


def test_docker_ps_query_raises_when_docker_ps_fails() -> None:
    runner = FakeRunner(
        CommandResult(
            stdout="",
            stderr="permission denied while trying to connect to the Docker daemon",
            exit_code=1,
        )
    )

    with pytest.raises(DockerPsError) as error:
        DockerPsQuery(runner).fetch()

    assert "permission denied" in str(error.value)


def test_docker_ps_query_wraps_command_runner_failures() -> None:
    with pytest.raises(DockerPsError) as error:
        DockerPsQuery(FailingRunner()).fetch()

    assert "could not run docker ps" in str(error.value)
    assert isinstance(error.value.__cause__, CommandConnectionError)
