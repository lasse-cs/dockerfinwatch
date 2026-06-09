import paramiko
import pytest

from textual_dockerclustermon.commands import (
    CommandConnectionError,
    CommandResult,
    CommandTimeoutError,
)
from textual_dockerclustermon.config import SSHServerConfig
from textual_dockerclustermon.ssh import ParamikoSSHClient, SSHCommandRunner


class FakeConnectedSSHClient:
    def __init__(self) -> None:
        self.active = True
        self.closed = False
        self.connect_calls = []
        self.run_calls = []
        self.result = CommandResult(stdout="out", stderr="err", exit_code=7)
        self.error: Exception | None = None

    def connect(self, config: SSHServerConfig, timeout: int) -> None:
        self.connect_calls.append({"config": config, "timeout": timeout})

    def is_active(self) -> bool:
        return self.active

    def run(self, command: str, timeout_seconds: int) -> CommandResult:
        self.run_calls.append({"command": command, "timeout_seconds": timeout_seconds})
        if self.error is not None:
            raise self.error
        return self.result

    def close(self) -> None:
        self.closed = True


class FakeChannel:
    def __init__(self, exit_status: int) -> None:
        self.exit_status = exit_status

    def recv_exit_status(self) -> int:
        return self.exit_status


class FakeStream:
    def __init__(self, data: bytes, exit_status: int = 0) -> None:
        self._data = data
        self.channel = FakeChannel(exit_status)

    def read(self) -> bytes:
        return self._data


class FakeTransport:
    def __init__(self, active: bool) -> None:
        self._active = active

    def is_active(self) -> bool:
        return self._active


class FakeParamikoSSHClient:
    def __init__(self) -> None:
        self.loaded_system_host_keys = False
        self.connect_calls = []
        self.exec_command_calls = []
        self.closed = False
        self.stdout = FakeStream(b"out", exit_status=7)
        self.stderr = FakeStream(b"err")
        self.transport = FakeTransport(active=True)

    def load_system_host_keys(self) -> None:
        self.loaded_system_host_keys = True

    def connect(self, **kwargs) -> None:
        self.connect_calls.append(kwargs)

    def get_transport(self) -> FakeTransport | None:
        return self.transport

    def exec_command(self, command: str, timeout: int):
        self.exec_command_calls.append({"command": command, "timeout": timeout})
        return None, self.stdout, self.stderr

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


def test_paramiko_ssh_client_loads_keys_connects_and_runs_command() -> None:
    paramiko_client = FakeParamikoSSHClient()

    client = ParamikoSSHClient(paramiko_client)
    client.connect(ssh_config(), 20)
    result = client.run("docker ps", 10)

    assert paramiko_client.loaded_system_host_keys is True
    assert paramiko_client.connect_calls == [
        {
            "hostname": "prod.example.com",
            "port": 2222,
            "username": "deploy",
            "key_filename": "/home/me/.ssh/id_ed25519",
            "timeout": 20,
            "banner_timeout": 20,
            "auth_timeout": 20,
        }
    ]
    assert paramiko_client.exec_command_calls == [
        {"command": "docker ps", "timeout": 10}
    ]
    assert client.is_active() is True
    assert result == CommandResult(stdout="out", stderr="err", exit_code=7)


def test_paramiko_ssh_client_uses_ssh_config_file(
    tmp_path,
) -> None:
    ssh_config_path = tmp_path / "ssh_config"
    key_path = tmp_path / "id_ed25519"
    ssh_config_path.write_text(
        f"""
Host prod-alias
  HostName prod.example.com
  User deploy
  Port 2222
  IdentityFile {key_path}
""".strip(),
        encoding="utf-8",
    )
    paramiko_client = FakeParamikoSSHClient()

    ParamikoSSHClient(paramiko_client).connect(
        SSHServerConfig(
            name="prod",
            host="prod-alias",
            ssh_config_file=str(ssh_config_path),
        ),
        20,
    )

    assert paramiko_client.connect_calls == [
        {
            "hostname": "prod.example.com",
            "port": 2222,
            "username": "deploy",
            "key_filename": [str(key_path)],
            "timeout": 20,
            "banner_timeout": 20,
            "auth_timeout": 20,
        }
    ]


def test_paramiko_ssh_client_prefers_explicit_config_values(
    tmp_path,
) -> None:
    ssh_config_path = tmp_path / "ssh_config"
    key_path = tmp_path / "id_ed25519"
    ssh_config_path.write_text(
        f"""
Host prod-alias
  HostName prod.example.com
  User deploy
  Port 2222
  IdentityFile {key_path}
""".strip(),
        encoding="utf-8",
    )
    paramiko_client = FakeParamikoSSHClient()

    ParamikoSSHClient(paramiko_client).connect(
        SSHServerConfig(
            name="prod",
            host="prod-alias",
            username="override-user",
            port=2200,
            key_filename="/explicit/key",
            ssh_config_file=str(ssh_config_path),
        ),
        20,
    )

    assert paramiko_client.connect_calls == [
        {
            "hostname": "prod.example.com",
            "port": 2200,
            "username": "override-user",
            "key_filename": "/explicit/key",
            "timeout": 20,
            "banner_timeout": 20,
            "auth_timeout": 20,
        }
    ]


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
