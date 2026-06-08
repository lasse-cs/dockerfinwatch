from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class CommandResult:
    stdout: str
    stderr: str
    exit_code: int


class CommandRunner(Protocol):
    def run(self, command: str, timeout_seconds: int) -> CommandResult: ...
