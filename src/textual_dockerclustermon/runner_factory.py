from textual_dockerclustermon.commands import CommandRunner
from textual_dockerclustermon.config import ServerConfig
from textual_dockerclustermon.demo import DemoCommandRunner
from textual_dockerclustermon.local import LocalCommandRunner


def create_command_runner(server: ServerConfig) -> CommandRunner:
    if server.kind == "demo":
        return DemoCommandRunner()

    if server.kind == "local":
        return LocalCommandRunner()

    raise ValueError(f"Unsupported server kind: {server.kind}")
