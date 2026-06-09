from collections.abc import Callable
from pathlib import Path
from typing import Protocol

import paramiko

from textual_dockerclustermon.commands import (
    CommandConnectionError,
    CommandResult,
    CommandTimeoutError,
)
from textual_dockerclustermon.config import SSHServerConfig


class SSHClientError(Exception):
    pass


class SSHClient(Protocol):
    def connect(self, config: SSHServerConfig, timeout: int) -> None: ...

    def is_active(self) -> bool: ...

    def run(self, command: str, timeout_seconds: int) -> CommandResult: ...

    def close(self) -> None: ...


class ParamikoSSHClient:
    def __init__(self, client: paramiko.SSHClient) -> None:
        self.client = client

    def is_active(self) -> bool:
        transport = self.client.get_transport()
        return transport is not None and transport.is_active()

    def run(self, command: str, timeout_seconds: int) -> CommandResult:
        try:
            _, stdout, stderr = self.client.exec_command(
                command,
                timeout=timeout_seconds,
            )
        except paramiko.SSHException as e:
            raise SSHClientError(f"ssh exception: {str(e)}") from e
        return CommandResult(
            stdout=stdout.read().decode(),
            stderr=stderr.read().decode(),
            exit_code=stdout.channel.recv_exit_status(),
        )

    def connect(self, config: SSHServerConfig, timeout: int) -> None:
        ssh_config = _lookup_ssh_config(config)
        try:
            self.client.load_system_host_keys()
            self.client.connect(
                hostname=_hostname(config, ssh_config),
                port=_port(config, ssh_config),
                username=_username(config, ssh_config),
                key_filename=_key_filename(config, ssh_config),
                timeout=timeout,
                banner_timeout=timeout,
                auth_timeout=timeout,
            )
        except paramiko.SSHException as e:
            raise SSHClientError(f"ssh exception: {str(e)}") from e

    def close(self) -> None:
        self.client.close()


class SSHCommandRunner:
    def __init__(
        self,
        config: SSHServerConfig,
        client_factory: Callable[[], SSHClient]
    ) -> None:
        self._config = config
        self._client_factory = client_factory
        self._client: SSHClient | None = None

    def run(self, command: str, timeout_seconds: int) -> CommandResult:
        try:
            client = self._connected_client(timeout_seconds)
            return client.run(command, timeout_seconds)
        except TimeoutError as error:
            raise CommandTimeoutError(f"command timed out: {command}") from error
        except (OSError, paramiko.SSHException, SSHClientError) as error:
            raise CommandConnectionError(
                f"could not run SSH command: {error}"
            ) from error

    def _connected_client(self, timeout_seconds: int) -> SSHClient:
        if self._client is not None:
            if self._client.is_active():
                return self._client
            self._client.close()
            self._client = None

        self._client = self._client_factory()
        self._client.connect(self._config, timeout_seconds)
        return self._client


def _lookup_ssh_config(config: SSHServerConfig) -> dict[str, object]:
    if config.ssh_config_file is None:
        return {}

    path = Path(config.ssh_config_file).expanduser()
    if not path.exists():
        return {}

    return paramiko.SSHConfig.from_path(str(path)).lookup(config.host)


def _hostname(config: SSHServerConfig, ssh_config: dict[str, object]) -> str:
    return str(ssh_config.get("hostname", config.host))


def _username(config: SSHServerConfig, ssh_config: dict[str, object]) -> str | None:
    if config.username is not None:
        return config.username
    value = ssh_config.get("user")
    if value is None:
        return None
    return str(value)


def _port(config: SSHServerConfig, ssh_config: dict[str, object]) -> int:
    if config.port is not None:
        return config.port
    return int(ssh_config.get("port", 22))


def _key_filename(
    config: SSHServerConfig,
    ssh_config: dict[str, object],
) -> str | list[str] | None:
    if config.key_filename is not None:
        return config.key_filename

    value = ssh_config.get("identityfile")
    if value is None:
        return None
    if isinstance(value, list):
        return [str(Path(str(item)).expanduser()) for item in value]
    return str(Path(str(value)).expanduser())
