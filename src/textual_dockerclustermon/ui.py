from typing import Protocol

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

    def __init__(self, monitor: Monitor) -> None:
        super().__init__()
        self._monitor = monitor

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("Waiting for first refresh...", id="status")
        yield DataTable(id="containers")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#containers", DataTable)
        table.add_columns("Name", "Image", "Status", "Ports", "ID")
        self._refresh()

    def action_refresh(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        try:
            snapshot = self._monitor.refresh()
        except MonitorRefreshError as error:
            self._show_error(str(error))
            return

        self._show_snapshot(snapshot)

    def _show_error(self, message: str) -> None:
        status = self.query_one("#status", Static)
        status.update(message)

    def _show_snapshot(self, snapshot: MonitorSnapshot) -> None:
        status = self.query_one("#status", Static)
        table = self.query_one("#containers", DataTable)

        table.clear()
        table.add_rows(
            (
                (
                    container.name,
                    container.image,
                    container.status,
                    container.ports,
                    container.id,
                )
                for container in snapshot.containers
            )
        )
        status.update(
            f"{snapshot.server_name} | last updated "
            f"{snapshot.updated_at:%H:%M:%S %Z}"
        )
