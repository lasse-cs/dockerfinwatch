import paramiko

from textual_dockerclustermon.commands import CommandRunner
from textual_dockerclustermon.config import ServerConfig, SSHServerConfig
from textual_dockerclustermon.demo import DemoCommandRunner
from textual_dockerclustermon.local import LocalCommandRunner, SubprocessProcessRunner
from textual_dockerclustermon.ssh import ParamikoSSHClient, SSHCommandRunner


def create_command_runner(server: ServerConfig) -> CommandRunner:
    if server.kind == "demo":
        return DemoCommandRunner()

    if server.kind == "local":
        return LocalCommandRunner(process_runner=SubprocessProcessRunner())

    if server.kind == "ssh":
        if not isinstance(server, SSHServerConfig):
            raise ValueError(f"Expected an SSHServerConfig for: {server}")
        return SSHCommandRunner(
            config=server,
            client_factory=lambda: ParamikoSSHClient(paramiko.SSHClient()),
        )

    raise ValueError(f"Unsupported server kind: {server.kind}")
