import asyncio
import threading
from datetime import UTC, datetime

import pytest
from textual.coordinate import Coordinate
from textual.widgets import DataTable, Static

from textual_dockerclustermon.docker import Container, ContainerMetadata, ContainerStats
from textual_dockerclustermon.monitor import MonitorRefreshError, MonitorSnapshot
from textual_dockerclustermon.ui import DockerClusterMonitorApp
from helpers import wait_until


class FakeMonitorService:
    def __init__(self, snapshot: MonitorSnapshot) -> None:
        self.snapshot = snapshot
        self.refresh_count = 0

    @property
    def server_name(self) -> str:
        return self.snapshot.server_name

    def refresh(self) -> MonitorSnapshot:
        self.refresh_count += 1
        return self.snapshot


class BlockingMonitorService:
    def __init__(self, snapshot: MonitorSnapshot) -> None:
        self.snapshot = snapshot
        self.refresh_count = 0
        self.thread_id: int | None = None
        self.started = threading.Event()
        self.release = threading.Event()

    @property
    def server_name(self) -> str:
        return self.snapshot.server_name

    def refresh(self) -> MonitorSnapshot:
        self.refresh_count += 1
        self.thread_id = threading.get_ident()
        self.started.set()
        self.release.wait(timeout=1)
        return self.snapshot


class FailingMonitorService:
    server_name = "prod"

    def refresh(self) -> MonitorSnapshot:
        raise MonitorRefreshError("docker ps failed: permission denied")


class SequenceMonitorService:
    def __init__(
        self,
        results: list[MonitorSnapshot | MonitorRefreshError],
        server_name: str = "prod",
    ) -> None:
        self.results = results
        self.server_name = server_name

    def refresh(self) -> MonitorSnapshot:
        result = self.results.pop(0)
        if isinstance(result, MonitorRefreshError):
            raise result
        return result


def snapshot_with_container(name: str, server_name: str = "prod") -> MonitorSnapshot:
    return MonitorSnapshot(
        server_name=server_name,
        containers=[
            container(name=name),
        ],
        updated_at=datetime(2026, 6, 8, 12, 30, tzinfo=UTC),
    )


def container(name: str = "web", stats: ContainerStats | None = None) -> Container:
    return Container(
        metadata=ContainerMetadata(
            id="abc123",
            name=name,
            image="nginx:latest",
            status="Up 2 minutes",
            ports="80/tcp",
        ),
        stats=stats,
    )


def container_stats() -> ContainerStats:
    return ContainerStats(
        cpu_percent="1.23%",
        memory_usage="10MiB / 1GiB",
        memory_percent="0.98%",
        network_io="1kB / 2kB",
        block_io="0B / 0B",
        pids="4",
    )


@pytest.mark.asyncio
async def test_app_displays_monitor_snapshot_in_table() -> None:
    monitor = FakeMonitorService(
        MonitorSnapshot(
            server_name="prod",
            containers=[container(stats=container_stats())],
            updated_at=datetime(2026, 6, 8, 12, 30, tzinfo=UTC),
        )
    )
    app = DockerClusterMonitorApp([monitor])

    async with app.run_test() as pilot:
        await pilot.pause()

        status = app.query_one("#server-status-0", Static)
        table = app.query_one("#containers-0", DataTable)
        await wait_until(lambda: status.content == "prod | last updated 12:30:00 UTC")

        assert monitor.refresh_count == 1
        assert status.content == "prod | last updated 12:30:00 UTC"
        assert table.row_count == 1
        assert table.get_cell_at(Coordinate(0, 0)) == "web"
        assert table.get_cell_at(Coordinate(0, 1)) == "nginx:latest"
        assert table.get_cell_at(Coordinate(0, 2)) == "Up 2 minutes"
        assert table.get_cell_at(Coordinate(0, 3)) == "1.23%"
        assert table.get_cell_at(Coordinate(0, 4)) == "10MiB / 1GiB"
        assert table.get_cell_at(Coordinate(0, 5)) == "0.98%"
        assert table.get_cell_at(Coordinate(0, 6)) == "1kB / 2kB"
        assert table.get_cell_at(Coordinate(0, 7)) == "0B / 0B"
        assert table.get_cell_at(Coordinate(0, 8)) == "4"
        assert table.get_cell_at(Coordinate(0, 9)) == "80/tcp"
        assert table.get_cell_at(Coordinate(0, 10)) == "abc123"


@pytest.mark.asyncio
async def test_app_displays_one_table_per_monitor() -> None:
    first_monitor = FakeMonitorService(snapshot_with_container("web", "prod-a"))
    second_monitor = FakeMonitorService(snapshot_with_container("api", "prod-b"))
    app = DockerClusterMonitorApp([first_monitor, second_monitor])

    async with app.run_test() as pilot:
        await pilot.pause()

        first_status = app.query_one("#server-status-0", Static)
        second_status = app.query_one("#server-status-1", Static)
        first_table = app.query_one("#containers-0", DataTable)
        second_table = app.query_one("#containers-1", DataTable)
        await wait_until(
            lambda: first_table.row_count == 1 and second_table.row_count == 1
        )

        assert first_status.content == "prod-a | last updated 12:30:00 UTC"
        assert second_status.content == "prod-b | last updated 12:30:00 UTC"
        assert first_table.get_cell_at(Coordinate(0, 0)) == "web"
        assert second_table.get_cell_at(Coordinate(0, 0)) == "api"


@pytest.mark.asyncio
async def test_app_refreshes_on_configured_interval() -> None:
    monitor = FakeMonitorService(snapshot_with_container("web"))
    app = DockerClusterMonitorApp([monitor], refresh_seconds=0.05)

    async with app.run_test() as pilot:
        await pilot.pause()

        await wait_until(lambda: monitor.refresh_count >= 2)

        assert monitor.refresh_count >= 2


@pytest.mark.asyncio
async def test_app_runs_refresh_in_worker_thread() -> None:
    main_thread_id = threading.get_ident()
    monitor = BlockingMonitorService(snapshot_with_container("web"))
    app = DockerClusterMonitorApp([monitor])

    async with app.run_test() as pilot:
        await pilot.pause()

        status = app.query_one("#server-status-0", Static)
        assert status.content == "prod | refreshing..."
        assert await asyncio.to_thread(monitor.started.wait, 1)
        assert monitor.thread_id != main_thread_id

        await pilot.press("r")
        await pilot.pause()
        assert monitor.refresh_count == 1

        monitor.release.set()
        await wait_until(lambda: status.content == "prod | last updated 12:30:00 UTC")


@pytest.mark.asyncio
async def test_app_refreshes_servers_independently() -> None:
    slow_monitor = BlockingMonitorService(snapshot_with_container("web", "slow"))
    fast_monitor = FakeMonitorService(snapshot_with_container("api", "fast"))
    app = DockerClusterMonitorApp([slow_monitor, fast_monitor])

    async with app.run_test() as pilot:
        await pilot.pause()

        slow_status = app.query_one("#server-status-0", Static)
        fast_table = app.query_one("#containers-1", DataTable)

        assert await asyncio.to_thread(slow_monitor.started.wait, 1)
        assert slow_status.content == "slow | refreshing..."
        await wait_until(lambda: fast_table.row_count == 1)

        assert fast_monitor.refresh_count == 1
        assert fast_table.get_cell_at(Coordinate(0, 0)) == "api"

        slow_monitor.release.set()


@pytest.mark.asyncio
async def test_app_shows_status_when_docker_ps_refresh_fails() -> None:
    app = DockerClusterMonitorApp([FailingMonitorService()])

    async with app.run_test() as pilot:
        await pilot.pause()

        status = app.query_one("#server-status-0", Static)
        table = app.query_one("#containers-0", DataTable)
        await wait_until(
            lambda: status.content == "prod | docker ps failed: permission denied"
        )

        assert status.content == "prod | docker ps failed: permission denied"
        assert table.row_count == 0


@pytest.mark.asyncio
async def test_app_preserves_table_when_manual_refresh_fails() -> None:
    app = DockerClusterMonitorApp(
        [
            SequenceMonitorService(
                [
                    snapshot_with_container("web"),
                    MonitorRefreshError("docker ps failed: permission denied"),
                ]
            )
        ]
    )

    async with app.run_test() as pilot:
        await pilot.pause()
        status = app.query_one("#server-status-0", Static)
        table = app.query_one("#containers-0", DataTable)
        await wait_until(lambda: table.row_count == 1)

        await pilot.press("r")
        await wait_until(
            lambda: status.content == "prod | docker ps failed: permission denied"
        )

        assert status.content == "prod | docker ps failed: permission denied"
        assert table.row_count == 1
        assert table.get_cell_at(Coordinate(0, 0)) == "web"
