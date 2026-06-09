import pytest
from textual.coordinate import Coordinate
from textual.widgets import DataTable, Static

from helpers import wait_until
from textual_dockerclustermon.application import create_app
from textual_dockerclustermon.commands import CommandResult


class SequenceCommandRunner:
    def __init__(self, container_names: list[str]) -> None:
        self._container_names = container_names

    def run(self, command: str, timeout_seconds: int) -> CommandResult:
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


@pytest.mark.asyncio
async def test_create_app_wires_demo_server_from_config(tmp_path) -> None:
    config_path = tmp_path / "dockerclustermon.toml"
    config_path.write_text(
        """
[server]
name = "demo-prod"
kind = "demo"
""".strip(),
        encoding="utf-8",
    )

    app = create_app(config_path)

    async with app.run_test() as pilot:
        await pilot.pause()

        status = app.query_one("#status", Static)
        table = app.query_one("#containers", DataTable)
        await wait_until(lambda: table.row_count == 2)

        assert status.content.startswith("demo-prod | last updated ")
        assert table.row_count == 2
        assert table.get_cell_at(Coordinate(0, 0)) == "web"
        assert table.get_cell_at(Coordinate(1, 0)) == "cache"
        assert table.get_cell_at(Coordinate(0, 3)) == "1.23%"


@pytest.mark.asyncio
async def test_create_app_uses_configured_refresh_interval(tmp_path) -> None:
    config_path = tmp_path / "dockerclustermon.toml"
    config_path.write_text(
        """
[defaults]
refresh_seconds = 0.05

[server]
name = "demo-prod"
kind = "demo"
""".strip(),
        encoding="utf-8",
    )
    runner = SequenceCommandRunner(["web", "api"])

    app = create_app(config_path, command_runner_factory=lambda server: runner)

    async with app.run_test() as pilot:
        await pilot.pause()

        table = app.query_one("#containers", DataTable)
        await wait_until(
            lambda: (
                table.row_count == 1 and table.get_cell_at(Coordinate(0, 0)) == "api"
            )
        )
