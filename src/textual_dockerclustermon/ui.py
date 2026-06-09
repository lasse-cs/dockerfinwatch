from typing import Protocol

from textual import work
from textual.app import App, ComposeResult
from textual.widgets import DataTable, Footer, Header, Static

from textual_dockerclustermon.monitor import MonitorRefreshError, MonitorSnapshot


class Monitor(Protocol):
    def refresh(self) -> MonitorSnapshot: ...


class DockerClusterMonitorApp(App[None]):
    CSS_PATH = "ui.tcss"

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, monitor: Monitor, refresh_seconds: float = 60) -> None:
        super().__init__()
        self._monitor = monitor
        self._refresh_seconds = refresh_seconds
        self._refresh_in_progress = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("Waiting for first refresh...", id="status")
        yield DataTable(id="containers")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#containers", DataTable)
        table.add_columns(
            "Name",
            "Image",
            "Status",
            "CPU",
            "Memory",
            "Mem %",
            "Net I/O",
            "Block I/O",
            "PIDs",
            "Ports",
            "ID",
        )
        self.set_interval(self._refresh_seconds, self._refresh)
        self._refresh()

    def action_refresh(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        if self._refresh_in_progress:
            return

        self._refresh_in_progress = True
        self._show_status("Refreshing...")
        self._refresh_in_background()

    @work(thread=True)
    def _refresh_in_background(self) -> None:
        try:
            snapshot = self._monitor.refresh()
        except MonitorRefreshError as error:
            self.call_from_thread(self._complete_refresh_error, str(error))
        except Exception as error:
            self.call_from_thread(self._raise_fatal, error)
        else:
            self.call_from_thread(self._complete_refresh_success, snapshot)

    def _complete_refresh_error(self, message: str) -> None:
        self._refresh_in_progress = False
        self._show_status(message)

    def _complete_refresh_success(self, snapshot: MonitorSnapshot) -> None:
        self._refresh_in_progress = False
        self._show_snapshot(snapshot)

    def _raise_fatal(self, error: Exception) -> None:
        raise error

    def _show_status(self, message: str) -> None:
        status = self.query_one("#status", Static)
        status.update(message)

    def _show_snapshot(self, snapshot: MonitorSnapshot) -> None:
        status = self.query_one("#status", Static)
        table = self.query_one("#containers", DataTable)

        table.clear()
        table.add_rows(
            (
                (
                    container.metadata.name,
                    container.metadata.image,
                    container.metadata.status,
                    container.stats.cpu_percent if container.stats else "-",
                    container.stats.memory_usage if container.stats else "-",
                    container.stats.memory_percent if container.stats else "-",
                    container.stats.network_io if container.stats else "-",
                    container.stats.block_io if container.stats else "-",
                    container.stats.pids if container.stats else "-",
                    container.metadata.ports,
                    container.metadata.id,
                )
                for container in snapshot.containers
            )
        )
        status.update(
            f"{snapshot.server_name} | last updated {snapshot.updated_at:%H:%M:%S %Z}"
        )
