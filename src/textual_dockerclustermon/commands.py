from dataclasses import dataclass
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
    def run(self, command: str, timeout_seconds: float) -> CommandResult: ...
