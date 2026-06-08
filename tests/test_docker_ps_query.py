import pytest

from textual_dockerclustermon.commands import CommandConnectionError, CommandResult
from textual_dockerclustermon.docker import DockerPsError, DockerPsQuery


class FakeRunner:
    def __init__(self, result: CommandResult) -> None:
        self.result = result
        self.commands: list[str] = []

    def run(self, command: str, timeout_seconds: int) -> CommandResult:
        self.commands.append(command)
        return self.result


class FailingRunner:
    def run(self, command: str, timeout_seconds: int) -> CommandResult:
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

    containers = DockerPsQuery(runner).fetch()

    assert runner.commands == ["docker ps --format '{{json .}}'"]
    assert containers[0].id == "abc123"
    assert containers[0].name == "web"
    assert containers[0].image == "nginx:latest"
    assert containers[0].ports == "80/tcp"
    assert containers[0].status == "Up 2 minutes"
    assert containers[1].id == "def456"
    assert containers[1].name == "cache"


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
