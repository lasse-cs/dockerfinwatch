import subprocess
from collections.abc import Sequence

import pytest

from textual_dockerclustermon.commands import (
    CommandConnectionError,
    CommandResult,
    CommandTimeoutError,
)
from textual_dockerclustermon.local import LocalCommandRunner


class FakeProcessRunner:
    def __init__(self) -> None:
        self.run_calls = []
        self.result = ("out", "err", 7)
        self.error: Exception | None = None

    def run(
        self,
        args: Sequence[str],
        timeout_seconds: float,
    ) -> tuple[str, str, int]:
        self.run_calls.append(
            {
                "args": list(args),
                "timeout_seconds": timeout_seconds,
            }
        )
        if self.error is not None:
            raise self.error
        return self.result


def test_local_command_runner_returns_subprocess_result() -> None:
    process_runner = FakeProcessRunner()

    result = LocalCommandRunner(process_runner=process_runner).run(
        ["docker", "ps", "--format", "{{json .}}"],
        20,
    )

    assert process_runner.run_calls == [
        {
            "args": ["docker", "ps", "--format", "{{json .}}"],
            "timeout_seconds": 20,
        }
    ]
    assert result == CommandResult(stdout="out", stderr="err", exit_code=7)


def test_local_command_runner_wraps_timeouts() -> None:
    process_runner = FakeProcessRunner()
    process_runner.error = subprocess.TimeoutExpired(["docker", "ps"], 20)

    with pytest.raises(CommandTimeoutError) as error:
        LocalCommandRunner(process_runner=process_runner).run(["docker", "ps"], 20)

    assert str(error.value) == "command timed out: ['docker', 'ps']"
    assert isinstance(error.value.__cause__, subprocess.TimeoutExpired)


def test_local_command_runner_wraps_os_errors() -> None:
    process_runner = FakeProcessRunner()
    process_runner.error = OSError("no docker")

    with pytest.raises(CommandConnectionError) as error:
        LocalCommandRunner(process_runner=process_runner).run(["docker", "ps"], 20)

    assert str(error.value) == "could not run command: no docker"
    assert isinstance(error.value.__cause__, OSError)
