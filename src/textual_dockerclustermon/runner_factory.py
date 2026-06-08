from textual_dockerclustermon.commands import CommandRunner
from textual_dockerclustermon.config import ServerConfig, SSHServerConfig
from textual_dockerclustermon.demo import DemoCommandRunner
from textual_dockerclustermon.local import LocalCommandRunner
from textual_dockerclustermon.ssh import SSHCommandRunner


def create_command_runner(server: ServerConfig) -> CommandRunner:
    if server.kind == "demo":
        return DemoCommandRunner()

    if server.kind == "local":
        return LocalCommandRunner()

    if isinstance(server, SSHServerConfig):
        return SSHCommandRunner(config=server)

    raise ValueError(f"Unsupported server kind: {server.kind}")
