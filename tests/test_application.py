from pathlib import Path
from types import TracebackType
from typing import Self

import pytest
from textual.coordinate import Coordinate
from textual.widgets import DataTable, Static

from helpers import wait_until
from textual_dockerclustermon.application import (
    CONFIG_ENV_VAR,
    config_path_from_args,
    create_app,
    resolve_config_path,
)
from textual_dockerclustermon.commands import CommandResult


class SequenceCommandRunner:
    def __init__(self, container_names: list[str]) -> None:
        self._container_names = container_names
        self.closed = False

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.closed = True

    def run(self, command: str, timeout_seconds: float) -> CommandResult:
        if command.startswith("docker stats"):
            return CommandResult(
                stdout=(
                    '{"ID":"abc123","CPUPerc":"1.23%","MemUsage":"10MiB / 1GiB","MemPerc":"0.98%","NetIO":"1kB / 2kB","BlockIO":"0B / 0B","PIDs":"4"}\n'
                ),
                stderr="",
                exit_code=0,
            )

        name = self._container_names.pop(0) if self._container_names else "api"
        return CommandResult(
            stdout=(
                f'{{"ID":"abc123","Image":"nginx:latest","Names":"{name}",'
                '"Ports":"80/tcp","Status":"Up 2 minutes"}\n'
            ),
            stderr="",
            exit_code=0,
        )


def test_resolve_config_path_uses_explicit_path() -> None:
    assert resolve_config_path(
        Path("~/custom.toml"),
        environ={CONFIG_ENV_VAR: "/env/dockerclustermon.toml", "XDG_CONFIG_HOME": "/xdg"},
        home=Path("/home/test-user"),
    ) == Path("/home/test-user/custom.toml")


def test_resolve_config_path_uses_environment_path() -> None:
    assert resolve_config_path(
        environ={CONFIG_ENV_VAR: "~/env-config.toml", "XDG_CONFIG_HOME": "/xdg"},
        home=Path("/home/test-user"),
    ) == Path("/home/test-user/env-config.toml")


def test_resolve_config_path_uses_xdg_config_home() -> None:
    assert resolve_config_path(environ={"XDG_CONFIG_HOME": "/xdg"}) == Path(
        "/xdg/dockerclustermon/dockerclustermon.toml"
    )


def test_resolve_config_path_uses_home_config_fallback() -> None:
    assert resolve_config_path(environ={}, home=Path("/home/test-user")) == Path(
        "/home/test-user/.config/dockerclustermon/dockerclustermon.toml"
    )


def test_config_path_from_args_uses_config_option(tmp_path) -> None:
    config_path = tmp_path / "custom.toml"

    assert config_path_from_args(["--config", str(config_path)], environ={}) == config_path


@pytest.mark.asyncio
async def test_create_app_wires_demo_server_from_config(tmp_path) -> None:
    config_path = tmp_path / "dockerclustermon.toml"
    config_path.write_text(
        """
[[servers]]
name = "demo-prod"
kind = "demo"
""".strip(),
        encoding="utf-8",
    )

    app = create_app(config_path)

    async with app.run_test() as pilot:
        await pilot.pause()

        status = app.query_one("#server-status-0", Static)
        table = app.query_one("#containers-0", DataTable)
        await wait_until(lambda: table.row_count == 2)

        assert str(status.content).startswith("demo-prod | last updated ")
        assert table.row_count == 2
        assert table.get_cell_at(Coordinate(0, 0)) == "web"
        assert table.get_cell_at(Coordinate(1, 0)) == "cache"
        assert table.get_cell_at(Coordinate(0, 3)) == "1.23%"


@pytest.mark.asyncio
async def test_create_app_wires_multiple_servers_from_config(tmp_path) -> None:
    config_path = tmp_path / "dockerclustermon.toml"
    config_path.write_text(
        """
[[servers]]
name = "demo-a"
kind = "demo"

[[servers]]
name = "demo-b"
kind = "demo"
""".strip(),
        encoding="utf-8",
    )

    app = create_app(config_path)

    async with app.run_test() as pilot:
        await pilot.pause()

        first_status = app.query_one("#server-status-0", Static)
        second_status = app.query_one("#server-status-1", Static)
        first_table = app.query_one("#containers-0", DataTable)
        second_table = app.query_one("#containers-1", DataTable)
        await wait_until(
            lambda: first_table.row_count == 2 and second_table.row_count == 2
        )

        assert str(first_status.content).startswith("demo-a | last updated ")
        assert str(second_status.content).startswith("demo-b | last updated ")
        assert first_table.get_cell_at(Coordinate(0, 0)) == "web"
        assert second_table.get_cell_at(Coordinate(0, 0)) == "web"


@pytest.mark.asyncio
async def test_create_app_uses_configured_refresh_interval(tmp_path) -> None:
    config_path = tmp_path / "dockerclustermon.toml"
    config_path.write_text(
        """
[defaults]
refresh_seconds = 0.05

[[servers]]
name = "demo-prod"
kind = "demo"
""".strip(),
        encoding="utf-8",
    )
    runner = SequenceCommandRunner(["web", "api"])

    app = create_app(config_path, command_runner_factory=lambda server: runner)

    async with app.run_test() as pilot:
        await pilot.pause()

        table = app.query_one("#containers-0", DataTable)
        await wait_until(
            lambda: (
                table.row_count == 1 and table.get_cell_at(Coordinate(0, 0)) == "api"
            )
        )

    assert runner.closed is True
