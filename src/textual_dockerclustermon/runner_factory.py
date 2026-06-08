from textual_dockerclustermon.commands import CommandRunner
from textual_dockerclustermon.config import ServerConfig
from textual_dockerclustermon.demo import DemoCommandRunner


def create_command_runner(server: ServerConfig) -> CommandRunner:
    if server.kind == "demo":
        return DemoCommandRunner()

    raise ValueError(f"Unsupported server kind: {server.kind}")
