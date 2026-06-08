import pytest
from textual.coordinate import Coordinate
from textual.widgets import DataTable, Static

from textual_dockerclustermon.application import create_app


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

        assert status.content.startswith("demo-prod | last updated ")
        assert table.row_count == 2
        assert table.get_cell_at(Coordinate(0, 0)) == "web"
        assert table.get_cell_at(Coordinate(1, 0)) == "cache"
