from typing import Protocol

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widgets import DataTable, Footer, Header, Static

from dockerfinwatch.monitor import MonitorRefreshError, MonitorSnapshot


class Monitor(Protocol):
    @property
    def server_name(self) -> str: ...

    def refresh(self) -> MonitorSnapshot: ...

    def close(self) -> None: ...


class ServerMonitorView(Vertical):
    def __init__(
        self,
        monitor: Monitor,
        index: int,
        refresh_seconds: float,
    ) -> None:
        super().__init__(id=f"server-{index}", classes="server-view")
        self._monitor = monitor
        self._index = index
        self._refresh_seconds = refresh_seconds
        self._refresh_in_progress = False
        self._ready = False

    def compose(self) -> ComposeResult:
        yield Static(
            f"{self._monitor.server_name} | waiting for first refresh...",
            id=f"server-status-{self._index}",
            classes="server-status",
        )
        yield DataTable(
            id=f"containers-{self._index}",
            classes="server-containers",
        )

    def on_mount(self) -> None:
        table = self.query_one(f"#containers-{self._index}", DataTable)
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
        self._ready = True
        self.set_interval(self._refresh_seconds, self.refresh_monitor)
        self.refresh_monitor()

    def refresh_monitor(self) -> None:
        if not self._ready:
            return

        if self._refresh_in_progress:
            return

        self._refresh_in_progress = True
        self._show_status(f"{self._monitor.server_name} | refreshing...")
        self._refresh_in_background()

    @work(thread=True)
    def _refresh_in_background(self) -> None:
        try:
            snapshot = self._monitor.refresh()
        except MonitorRefreshError as error:
            self.app.call_from_thread(self._complete_refresh_error, str(error))
        except Exception as error:
            self.app.call_from_thread(self._raise_fatal, error)
        else:
            self.app.call_from_thread(self._complete_refresh_success, snapshot)

    def _complete_refresh_error(self, message: str) -> None:
        self._refresh_in_progress = False
        self._show_status(f"{self._monitor.server_name} | {message}")

    def _complete_refresh_success(self, snapshot: MonitorSnapshot) -> None:
        self._refresh_in_progress = False
        self._show_snapshot(snapshot)

    def _raise_fatal(self, error: Exception) -> None:
        raise error

    def _show_status(self, message: str) -> None:
        status = self.query_one(f"#server-status-{self._index}", Static)
        status.update(message)

    def _show_snapshot(self, snapshot: MonitorSnapshot) -> None:
        table = self.query_one(f"#containers-{self._index}", DataTable)

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
        local_time = snapshot.updated_at.astimezone()
        self._show_status(
            f"{snapshot.server_name} | last updated {local_time:%H:%M:%S %Z}"
        )


class DockerFinWatchApp(App[None]):
    CSS_PATH = "ui.tcss"

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, monitors: list[Monitor], refresh_seconds: float = 60) -> None:
        super().__init__()
        self._monitors = monitors
        self._refresh_seconds = refresh_seconds

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(self._server_count_status(), id="status")
        with VerticalScroll(id="servers"):
            for index, monitor in enumerate(self._monitors):
                yield ServerMonitorView(monitor, index, self._refresh_seconds)
        yield Footer()

    def action_refresh(self) -> None:
        self._refresh()

    def on_unmount(self) -> None:
        for monitor in self._monitors:
            monitor.close()

    def _refresh(self) -> None:
        for server_view in self.query(ServerMonitorView):
            server_view.refresh_monitor()

    def _server_count_status(self) -> str:
        server_count = len(self._monitors)
        label = "server" if server_count == 1 else "servers"
        return f"{server_count} {label}"
