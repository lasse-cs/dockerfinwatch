import paramiko
import pytest

from textual_dockerclustermon.commands import (
    CommandConnectionError,
    CommandResult,
    CommandTimeoutError,
)
from textual_dockerclustermon.config import SSHServerConfig
from textual_dockerclustermon.ssh import SSHCommandRunner


class FakeConnectedSSHClient:
    def __init__(self) -> None:
        self.active = True
        self.closed = False
        self.connect_calls = []
        self.run_calls = []
        self.result = CommandResult(stdout="out", stderr="err", exit_code=7)
        self.error: Exception | None = None

    def connect(self, config: SSHServerConfig, timeout: float) -> None:
        self.connect_calls.append({"config": config, "timeout": timeout})

    def is_active(self) -> bool:
        return self.active

    def run(self, command: str, timeout_seconds: float) -> CommandResult:
        self.run_calls.append({"command": command, "timeout_seconds": timeout_seconds})
        if self.error is not None:
            raise self.error
        return self.result

    def close(self) -> None:
        self.closed = True


def ssh_config() -> SSHServerConfig:
    return SSHServerConfig(
        name="prod",
        host="prod.example.com",
        username="deploy",
        port=2222,
        key_filename="/home/me/.ssh/id_ed25519",
        ssh_config_file=None,
    )


def test_ssh_command_runner_returns_command_result() -> None:
    client = FakeConnectedSSHClient()
    factory_calls = []
    config = ssh_config()

    def client_factory() -> FakeConnectedSSHClient:
        factory_calls.append(client)
        return client

    runner = SSHCommandRunner(config=config, client_factory=client_factory)

    result = runner.run("docker ps", 20)

    assert factory_calls == [client]
    assert client.connect_calls == [{"config": config, "timeout": 20}]
    assert client.run_calls == [{"command": "docker ps", "timeout_seconds": 20}]
    assert client.closed is False
    assert result == CommandResult(stdout="out", stderr="err", exit_code=7)


def test_ssh_command_runner_reuses_active_connection() -> None:
    client = FakeConnectedSSHClient()
    created_clients = []

    def client_factory() -> FakeConnectedSSHClient:
        created_clients.append(client)
        return client

    runner = SSHCommandRunner(config=ssh_config(), client_factory=client_factory)

    runner.run("docker ps", 20)
    runner.run("docker ps --all", 20)

    assert created_clients == [client]
    assert client.connect_calls == [{"config": ssh_config(), "timeout": 20}]
    assert client.run_calls == [
        {"command": "docker ps", "timeout_seconds": 20},
        {"command": "docker ps --all", "timeout_seconds": 20},
    ]
    assert client.closed is False


def test_ssh_command_runner_reconnects_inactive_connection() -> None:
    stale_client = FakeConnectedSSHClient()
    fresh_client = FakeConnectedSSHClient()
    clients = [stale_client, fresh_client]
    runner = SSHCommandRunner(
        config=ssh_config(),
        client_factory=lambda: clients.pop(0),
    )

    runner.run("docker ps", 20)
    stale_client.active = False
    runner.run("docker ps --all", 20)

    assert stale_client.closed is True
    assert stale_client.connect_calls == [{"config": ssh_config(), "timeout": 20}]
    assert fresh_client.connect_calls == [{"config": ssh_config(), "timeout": 20}]
    assert fresh_client.run_calls == [
        {"command": "docker ps --all", "timeout_seconds": 20}
    ]


def test_ssh_command_runner_closes_active_connection_on_exit() -> None:
    client = FakeConnectedSSHClient()

    with SSHCommandRunner(config=ssh_config(), client_factory=lambda: client) as runner:
        runner.run("docker ps", 20)

    assert client.closed is True


def test_ssh_command_runner_wraps_timeouts() -> None:
    client = FakeConnectedSSHClient()
    client.error = TimeoutError("timed out")
    runner = SSHCommandRunner(
        config=ssh_config(),
        client_factory=lambda: client,
    )

    with pytest.raises(CommandTimeoutError) as error:
        runner.run("docker ps", 20)

    assert str(error.value) == "command timed out: docker ps"
    assert isinstance(error.value.__cause__, TimeoutError)
    assert client.closed is False


def test_ssh_command_runner_wraps_connection_errors() -> None:
    def client_factory() -> FakeConnectedSSHClient:
        raise paramiko.SSHException("connection failed")

    runner = SSHCommandRunner(config=ssh_config(), client_factory=client_factory)

    with pytest.raises(CommandConnectionError) as error:
        runner.run("docker ps", 20)

    assert str(error.value) == "could not run SSH command: connection failed"
    assert isinstance(error.value.__cause__, paramiko.SSHException)
