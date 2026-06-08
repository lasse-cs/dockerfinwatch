import subprocess

import pytest

from textual_dockerclustermon.commands import (
    CommandConnectionError,
    CommandResult,
    CommandTimeoutError,
)
from textual_dockerclustermon.local import LocalCommandRunner


def test_local_command_runner_returns_subprocess_result(monkeypatch) -> None:
    calls = []

    def fake_run(
        args,
        capture_output: bool,
        text: bool,
        timeout: int,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(
            {
                "args": args,
                "capture_output": capture_output,
                "text": text,
                "timeout": timeout,
                "check": check,
            }
        )
        return subprocess.CompletedProcess(args, 7, stdout="out", stderr="err")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = LocalCommandRunner().run("docker ps --format '{{json .}}'", 20)

    assert calls == [
        {
            "args": ["docker", "ps", "--format", "{{json .}}"],
            "capture_output": True,
            "text": True,
            "timeout": 20,
            "check": False,
        }
    ]
    assert result == CommandResult(stdout="out", stderr="err", exit_code=7)


def test_local_command_runner_wraps_timeouts(monkeypatch) -> None:
    def fake_run(
        args,
        capture_output: bool,
        text: bool,
        timeout: int,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(args, timeout)

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(CommandTimeoutError) as error:
        LocalCommandRunner().run("docker ps", 20)

    assert str(error.value) == "command timed out: docker ps"
    assert isinstance(error.value.__cause__, subprocess.TimeoutExpired)


def test_local_command_runner_wraps_os_errors(monkeypatch) -> None:
    def fake_run(
        args,
        capture_output: bool,
        text: bool,
        timeout: int,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        raise OSError("no docker")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(CommandConnectionError) as error:
        LocalCommandRunner().run("docker ps", 20)

    assert str(error.value) == "could not run command: no docker"
    assert isinstance(error.value.__cause__, OSError)
