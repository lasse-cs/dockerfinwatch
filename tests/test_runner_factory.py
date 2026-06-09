from dataclasses import dataclass

import pytest

from dockerfinwatch.config import (
    DemoServerConfig,
    LocalServerConfig,
    ServerConfig,
    SSHServerConfig,
)
from dockerfinwatch.demo import DemoCommandRunner
from dockerfinwatch.local import LocalCommandRunner
from dockerfinwatch.runner_factory import create_command_runner
from dockerfinwatch.ssh import SSHCommandRunner


@dataclass(frozen=True)
class UnsupportedServerConfig(ServerConfig):
    pass


def test_create_command_runner_returns_demo_runner_for_demo_server() -> None:
    runner = create_command_runner(DemoServerConfig(name="demo"))

    assert isinstance(runner, DemoCommandRunner)


def test_create_command_runner_returns_local_runner_for_local_server() -> None:
    runner = create_command_runner(LocalServerConfig(name="local"))

    assert isinstance(runner, LocalCommandRunner)


def test_create_command_runner_returns_ssh_runner_for_ssh_server() -> None:
    runner = create_command_runner(
        SSHServerConfig(
            name="prod",
            host="prod.example.com",
            username="deploy",
            port=2222,
            key_filename="/home/me/.ssh/id_ed25519",
        )
    )

    assert isinstance(runner, SSHCommandRunner)


def test_create_command_runner_rejects_unsupported_server_config() -> None:
    with pytest.raises(ValueError) as error:
        create_command_runner(UnsupportedServerConfig(name="prod", kind="unsupported"))

    assert "Unsupported server kind: unsupported" in str(error.value)
