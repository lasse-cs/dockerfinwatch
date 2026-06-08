from textual_dockerclustermon.commands import CommandResult


class DemoCommandRunner:
    def run(self, command: str, timeout_seconds: int) -> CommandResult:
        return CommandResult(
            stdout=(
                '{"ID":"abc123","Image":"nginx:latest","Names":"web","Ports":"0.0.0.0:8080->80/tcp","Status":"Up 2 minutes"}\n'
                '{"ID":"def456","Image":"redis:7","Names":"cache","Ports":"6379/tcp","Status":"Up 1 hour"}\n'
            ),
            stderr="",
            exit_code=0,
        )
