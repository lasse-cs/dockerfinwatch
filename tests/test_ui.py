from datetime import UTC, datetime

import pytest
from textual.coordinate import Coordinate
from textual.widgets import DataTable, Static

from textual_dockerclustermon.docker import Container
from textual_dockerclustermon.monitor import MonitorSnapshot
from textual_dockerclustermon.ui import DockerClusterMonitorApp


class FakeMonitorService:
    def __init__(self, snapshot: MonitorSnapshot) -> None:
        self.snapshot = snapshot
        self.refresh_count = 0

    def refresh(self) -> MonitorSnapshot:
        self.refresh_count += 1
        return self.snapshot


@pytest.mark.asyncio
async def test_app_displays_monitor_snapshot_in_table() -> None:
    monitor = FakeMonitorService(
        MonitorSnapshot(
            server_name="prod",
            containers=[
                Container(
                    id="abc123",
                    name="web",
                    image="nginx:latest",
                    status="Up 2 minutes",
                    ports="80/tcp",
                )
            ],
            updated_at=datetime(2026, 6, 8, 12, 30, tzinfo=UTC),
        )
    )
    app = DockerClusterMonitorApp(monitor)

    async with app.run_test() as pilot:
        await pilot.pause()

        status = app.query_one("#status", Static)
        table = app.query_one("#containers", DataTable)

        assert monitor.refresh_count == 1
        assert status.content == "prod | last updated 12:30:00 UTC"
        assert table.row_count == 1
        assert table.get_cell_at(Coordinate(0, 0)) == "web"
        assert table.get_cell_at(Coordinate(0, 1)) == "nginx:latest"
        assert table.get_cell_at(Coordinate(0, 2)) == "Up 2 minutes"
        assert table.get_cell_at(Coordinate(0, 3)) == "80/tcp"
        assert table.get_cell_at(Coordinate(0, 4)) == "abc123"
