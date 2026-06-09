import subprocess
from collections.abc import Sequence
from types import TracebackType
from typing import Protocol, Self

from textual_dockerclustermon.commands import (
    CommandConnectionError,
    CommandResult,
    CommandTimeoutError,
)


class LocalProcessRunner(Protocol):
    def run(
        self,
        args: Sequence[str],
        timeout_seconds: float,
    ) -> tuple[str, str, int]: ...


class SubprocessProcessRunner:
    def run(
        self,
        args: Sequence[str],
        timeout_seconds: float,
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
        try:
            stdout, stderr, exit_code = self._process_runner.run(
                command,
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
