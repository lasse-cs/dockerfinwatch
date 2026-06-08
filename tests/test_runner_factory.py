from dataclasses import dataclass

import pytest

from textual_dockerclustermon.config import DemoServerConfig, LocalServerConfig, ServerConfig
from textual_dockerclustermon.demo import DemoCommandRunner
from textual_dockerclustermon.local import LocalCommandRunner
from textual_dockerclustermon.runner_factory import create_command_runner


@dataclass(frozen=True)
class UnsupportedServerConfig(ServerConfig):
    pass


def test_create_command_runner_returns_demo_runner_for_demo_server() -> None:
    runner = create_command_runner(DemoServerConfig(name="demo"))

    assert isinstance(runner, DemoCommandRunner)


def test_create_command_runner_returns_local_runner_for_local_server() -> None:
    runner = create_command_runner(LocalServerConfig(name="local"))

    assert isinstance(runner, LocalCommandRunner)


def test_create_command_runner_rejects_unsupported_server_config() -> None:
    with pytest.raises(ValueError) as error:
        create_command_runner(UnsupportedServerConfig(name="prod", kind="unsupported"))

    assert "Unsupported server kind: unsupported" in str(error.value)
