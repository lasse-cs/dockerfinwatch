import paramiko

from dockerfinwatch.commands import CommandRunner
from dockerfinwatch.config import ServerConfig, SSHServerConfig
from dockerfinwatch.demo import DemoCommandRunner
from dockerfinwatch.local import LocalCommandRunner, SubprocessProcessRunner
from dockerfinwatch.ssh import ParamikoSSHClient, SSHCommandRunner


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
