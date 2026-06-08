import shlex
import subprocess

from textual_dockerclustermon.commands import (
    CommandConnectionError,
    CommandResult,
    CommandTimeoutError,
)


class LocalCommandRunner:
    def run(self, command: str, timeout_seconds: int) -> CommandResult:
        try:
            result = subprocess.run(
                shlex.split(command),
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            raise CommandTimeoutError(f"command timed out: {command}") from error
        except OSError as error:
            raise CommandConnectionError(f"could not run command: {error}") from error

        return CommandResult(
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.returncode,
        )
