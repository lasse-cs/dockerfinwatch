from textual_dockerclustermon.commands import CommandResult


class DemoCommandRunner:
    def run(self, command: str, timeout_seconds: float) -> CommandResult:
        if command.startswith("docker stats"):
            return CommandResult(
                stdout=(
                    '{"ID":"abc123","CPUPerc":"1.23%","MemUsage":"10MiB / 1GiB","MemPerc":"0.98%","NetIO":"1kB / 2kB","BlockIO":"0B / 0B","PIDs":"4"}\n'
                    '{"ID":"def456","CPUPerc":"0.10%","MemUsage":"20MiB / 1GiB","MemPerc":"1.95%","NetIO":"3kB / 4kB","BlockIO":"5kB / 6kB","PIDs":"8"}\n'
                ),
                stderr="",
                exit_code=0,
            )

        return CommandResult(
            stdout=(
                '{"ID":"abc123","Image":"nginx:latest","Names":"web","Ports":"0.0.0.0:8080->80/tcp","Status":"Up 2 minutes"}\n'
                '{"ID":"def456","Image":"redis:7","Names":"cache","Ports":"6379/tcp","Status":"Up 1 hour"}\n'
            ),
            stderr="",
            exit_code=0,
        )
