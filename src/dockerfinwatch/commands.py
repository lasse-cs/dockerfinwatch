from collections.abc import Sequence
from dataclasses import dataclass
from types import TracebackType
from typing import Protocol


@dataclass(frozen=True)
class CommandResult:
    stdout: str
    stderr: str
    exit_code: int


class CommandError(Exception):
    pass


class CommandConnectionError(CommandError):
    pass


class CommandTimeoutError(CommandError):
    pass


class CommandRunner(Protocol):
    def __enter__(self) -> "CommandRunner": ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    def run(self, command: Sequence[str], timeout_seconds: float) -> CommandResult: ...
