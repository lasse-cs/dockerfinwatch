import shlex
import subprocess
from typing import Protocol

from textual_dockerclustermon.commands import (
    CommandConnectionError,
    CommandResult,
    CommandTimeoutError,
)


class LocalProcessRunner(Protocol):
    def run(
        self,
        args: list[str],
        timeout_seconds: int,
    ) -> tuple[str, str, int]: ...


class SubprocessProcessRunner:
    def run(
        self,
        args: list[str],
        timeout_seconds: int,
    ) -> tuple[str, str, int]:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        return result.stdout, result.stderr, result.returncode


class LocalCommandRunner:
    def __init__(self, process_runner: LocalProcessRunner) -> None:
        self._process_runner = process_runner

    def run(self, command: str, timeout_seconds: int) -> CommandResult:
        try:
            stdout, stderr, exit_code = self._process_runner.run(
                shlex.split(command),
                timeout_seconds,
            )
        except subprocess.TimeoutExpired as error:
            raise CommandTimeoutError(f"command timed out: {command}") from error
        except OSError as error:
            raise CommandConnectionError(f"could not run command: {error}") from error

        return CommandResult(
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
        )
